#!/usr/bin/env python3
"""Prueba D6 (de descarte): REaLTabFormer sobre la cadena customer -> rental -> payment de Pagila.

El informe la descarta porque «soporta una relación padre-hijo entre dos tablas, no esquemas
relacionales arbitrarios». Esta prueba lo mide:

  Exp. 1  dos niveles, como dice el README: customer (modelo tabular) -> rental (modelo relacional,
          join_on=customer_id).
  Exp. 2  tres niveles nativos: la API acepta un solo `in_df` y un solo `join_on` (se registra la
          firma; no hay nada que correr).
  Exp. 3  encadenado a mano: un segundo modelo relacional rental -> payment (join_on=rental_id), que
          genera los pagos a partir de los alquileres SINTÉTICOS del exp. 1. payment.customer_id
          queda como una columna más: ¿coincide con el cliente de su alquiler?
  Exp. 4  varios padres: las otras FK (customer.address_id/store_id, rental.inventory_id/staff_id,
          payment.staff_id) entran como números comunes. ¿Apuntan a filas que existen?

Se entrena con una muestra de clientes de `e3_entrenamiento` (Pagila sin el control de E3), con
todos sus alquileres y pagos, para poder medir la privacidad después con E3.

Subcomandos (desde la raíz del repo, con la base levantada; todo en .venv-rtf salvo E3):
  exportar   [.venv-rtf]  muestra de clientes + sus alquileres y pagos -> Parquet
  entrenar   [.venv-rtf]  entrena los 3 modelos y genera; guarda modelos y sintéticos
  cargar     [.venv-rtf]  arma `d6_auditoria` (copia de e3_entrenamiento sin restricciones, con
                          customer, rental y payment reemplazadas) y mide coherencia y FK
Después:
    .venv/bin/python pruebas/E3-chequeos-propios/evaluar_bd.py evaluar --candidata d6_auditoria \\
        --tipo sintetica --entrenada-con e3_entrenamiento --tablas customer,rental,payment
"""
import argparse
import datetime
import hashlib
import json
import os
import platform
import sys
import threading
import time
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
GRANDES = AQUI / "salidas_grandes"
ENTRADA, SINTETICO, MODELOS = GRANDES / "entrada", GRANDES / "sintetico", GRANDES / "modelos"
RESULTADOS, EVIDENCIA = AQUI / "resultados", AQUI / "evidencia"
TIEMPOS = RESULTADOS / "d6_tiempos.json"
BASE_ENTRENAMIENTO = "e3_entrenamiento"
CANDIDATA = "d6_auditoria"

# Columnas que entran a cada modelo (sin last_update ni uuid, que rellena el DEFAULT al cargar).
COLUMNAS = {
    "customer": ["customer_id", "store_id", "first_name", "last_name", "email", "address_id",
                 "activebool", "create_date", "active"],
    "rental": ["rental_id", "customer_id", "rental_date", "inventory_id", "return_date", "staff_id"],
    "payment": ["payment_id", "rental_id", "customer_id", "staff_id", "amount", "payment_date"],
}
FECHAS = {("customer", "create_date"), ("rental", "rental_date"), ("rental", "return_date"),
          ("payment", "payment_date")}
# FK que REaLTabFormer no puede declarar (exp. 4): tabla.columna -> tabla padre.columna
OTRAS_FK = [("customer", "address_id", "address", "address_id"), ("customer", "store_id", "store", "store_id"),
            ("rental", "inventory_id", "inventory", "inventory_id"), ("rental", "staff_id", "staff", "staff_id"),
            ("payment", "staff_id", "staff", "staff_id"), ("payment", "customer_id", "customer", "customer_id")]


# ----------------------------------------------------------------------------- medición

class Medidor:
    """Tiempo de reloj, RSS máximo del proceso (psutil, muestreo cada 0,25 s) y, si hay MPS, el pico
    de memoria que el driver de Metal reservó (memoria unificada: no siempre aparece en el RSS)."""

    def __init__(self, cada=0.25):
        import psutil
        self.proc, self.cada, self.pico, self.pico_mps = psutil.Process(), cada, 0, 0
        self._parar = threading.Event()
        try:
            import torch
            self._mps = torch.mps.driver_allocated_memory if torch.backends.mps.is_available() else None
        except Exception:
            self._mps = None

    def _leer(self):
        try:
            self.pico = max(self.pico, self.proc.memory_info().rss)
            if self._mps:
                self.pico_mps = max(self.pico_mps, self._mps())
        except Exception:
            pass

    def _bucle(self):
        while not self._parar.is_set():
            self._leer()
            self._parar.wait(self.cada)

    def __enter__(self):
        self.t0 = time.perf_counter()
        self._hilo = threading.Thread(target=self._bucle, daemon=True)
        self._hilo.start()
        return self

    def __exit__(self, *exc):
        self._parar.set()
        self._hilo.join()
        self._leer()
        self.segundos = time.perf_counter() - self.t0
        return False

    def dict(self):
        d = {"segundos": round(self.segundos, 1), "memoria_max_mb": round(self.pico / 2**20)}
        if self._mps:
            d["mps_max_mb"] = round(self.pico_mps / 2**20)
        return d


def registrar(fase, datos):
    RESULTADOS.mkdir(parents=True, exist_ok=True)
    todo = json.loads(TIEMPOS.read_text()) if TIEMPOS.exists() else {}
    todo[fase] = {**datos, "registrado": f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S}"}
    TIEMPOS.write_text(json.dumps(todo, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def ver(paquete):
    try:
        return version(paquete)
    except PackageNotFoundError:
        return "no instalado"


def entorno():
    return {"equipo": f"{platform.machine()}, macOS {platform.mac_ver()[0]}", "python": platform.python_version(),
            "ejecutable": sys.executable,
            "paquetes": {p: ver(p) for p in ("realtabformer", "torch", "transformers", "datasets", "accelerate",
                                             "pandas", "numpy", "scikit-learn", "psycopg2-binary")}}


# ----------------------------------------------------------------------------- exportar

def exportar(a):
    import pandas as pd
    import sqlalchemy as sa
    with Medidor() as m:
        ENTRADA.mkdir(parents=True, exist_ok=True)
        eng = sa.create_engine(f"postgresql+psycopg2://postgres:postgres@127.0.0.1:55432/{a.base}")
        with eng.connect() as c:
            ids = pd.read_sql(sa.text("select customer_id from customer"), c)["customer_id"].tolist()
            # Muestra reproducible: orden por md5(semilla || id), como el control de E3.
            ids = sorted(ids, key=lambda i: hashlib.md5(f"{a.semilla}{i}".encode()).hexdigest())[:a.clientes]
            datos = {}
            for t, cols in COLUMNAS.items():
                filtro = "customer_id = any(:ids)"
                if t == "payment":   # pagos de los alquileres de la muestra (y solo de ellos)
                    filtro = "rental_id in (select rental_id from rental where customer_id = any(:ids))"
                df = pd.read_sql(sa.text(f"select {', '.join(cols)} from {t} where {filtro} order by 1"),
                                 c, params={"ids": ids})
                for col in cols:
                    if (t, col) in FECHAS:   # sin zona horaria, en UTC
                        df[col] = pd.to_datetime(df[col], utc=True).dt.tz_localize(None)
                if t == "payment":
                    df["amount"] = pd.to_numeric(df["amount"]).astype(float)
                df.to_parquet(ENTRADA / f"{t}.parquet", index=False)
                datos[t] = df
    filas = {t: len(d) for t, d in datos.items()}
    por_cliente = datos["rental"].groupby("customer_id").size()
    registrar("exportar", {**m.dict(), "base": a.base, "clientes": a.clientes, "semilla": a.semilla,
                           "filas": filas, "alquileres_por_cliente_max": int(por_cliente.max()),
                           "alquileres_por_cliente_prom": round(float(por_cliente.mean()), 1),
                           "entorno": entorno()})
    print(f"Exportado: {filas} en {m.segundos:.1f} s -> {ENTRADA}")


# ----------------------------------------------------------------------------- entrenar

def _id_dir(base):
    """`save` guarda en base/idXXXX/: devuelve ese subdirectorio (el más nuevo)."""
    return sorted(p for p in Path(base).iterdir() if p.is_dir() and p.name.startswith("id"))[-1]


def _guardar(mod, destino):
    """`save` de la 0.2.4 serializa a JSON todos los atributos y falla con `full_save_dir` (Path)."""
    mod.full_save_dir = Path(mod.full_save_dir).as_posix()
    mod.save(destino)
    mod.full_save_dir = Path(mod.full_save_dir)


def _atencion_eager(mod):
    """En MPS, la atención SDPA de torch no admite dropout al entrenar (NotImplementedError): el modelo
    relacional (EncoderDecoder con GPT-2) se arma con la atención «eager», que es la implementación
    clásica. No cambia el modelo, solo cómo se calcula la atención."""
    cfg = mod.relational_config
    for c in (cfg, cfg.encoder, cfg.decoder):
        c._attn_implementation = "eager"
    return mod


def _con_reintentos(fn, intentos=3):
    """La 0.2.4 rompe todo el sample si genera una fecha sin dígitos (`int('')` en
    rtf_sampler._recover_data_values). Se reintenta (el generador avanza, sale otra muestra).
    Devuelve (resultado o None, lista de errores)."""
    errores = []
    for _ in range(intentos):
        try:
            return fn(), errores
        except ValueError as e:
            errores.append(str(e)[:120])
    return None, errores


def _con_ids(df, join_on, unicos):
    """El sample relacional devuelve el id del padre en el índice; lo pasa a columna."""
    df = df.copy()
    if join_on not in df.columns:
        df.index.name = join_on
        df = df.reset_index()
    return df


def entrenar(a):
    import warnings
    warnings.filterwarnings("ignore")
    import pandas as pd
    import torch
    from realtabformer import REaLTabFormer

    torch.manual_seed(a.semilla_modelo)
    datos = {t: pd.read_parquet(ENTRADA / f"{t}.parquet") for t in COLUMNAS}
    # La librería pasa las fechas a segundos (int64 / 1e9) y exige que den enteras: supone nanosegundos
    # y no acepta fracciones de segundo. Pagila v4 tiene microsegundos, así que se recortan.
    for t, col in FECHAS:
        datos[t][col] = datos[t][col].astype("datetime64[ns]").dt.floor("s")
    cus, ren, pay = datos["customer"], datos["rental"], datos["payment"]
    fases, info = {}, {"parametros": vars(a).copy(), "entorno": entorno()}
    info["parametros"].pop("func", None)
    os.chdir(GRANDES)   # rtf_checkpoints/ y rtf_samples/ quedan dentro de salidas_grandes/
    MODELOS.mkdir(parents=True, exist_ok=True)
    comunes = dict(batch_size=a.batch_size, random_state=a.semilla_modelo)
    # rental: secuencias de ~2000 tokens por cliente; con batch 8 se pasa de los 20 GB de MPS (humo)
    relac = dict(comunes, batch_size=a.batch_rental)
    if a.gradient_checkpointing:   # va a TrainingArguments: recalcula activaciones en vez de guardarlas
        relac["gradient_checkpointing"] = True

    enCurso = {}   # el modelo que se está entrenando, para registrar el largo de secuencia si falla

    def correr(nombre, fn):
        print(f"\n===== {nombre} =====", flush=True)
        try:
            with Medidor() as m:
                out = fn()
        except Exception as e:
            fases[nombre] = {"error": f"{type(e).__name__}: {str(e)[:500]}",
                             "max_tokens_hijo": getattr(enCurso.get("mod"), "relational_max_length", None)}
            registrar("entrenar", {"fases": fases, **info})
            raise
        fases[nombre] = m.dict()
        print(f"[{nombre}] {m.segundos:.0f} s, RSS {m.pico / 2**30:.1f} GB"
              + (f", MPS {m.pico_mps / 2**30:.1f} GB" if m._mps else ""), flush=True)
        registrar("entrenar", {"fases": fases, **info})
        return out

    # --- Exp. 1: customer (tabular) -> rental (relacional) -------------------------------------
    def fit_customer():
        mod = REaLTabFormer(model_type="tabular", epochs=a.epocas_tabular, **comunes)
        mod.fit(cus.drop(columns=["customer_id"]), device=a.device, num_bootstrap=a.bootstrap,
                gen_kwargs={},   # con el default (None) la 0.2.4 falla: sample(**None)
                save_full_every_epoch=0)   # el guardado intermedio falla: experiment_id todavía es None
        _guardar(mod, MODELOS / "customer")
        return mod
    m_cus = correr("entrenar customer (tabular)", fit_customer)
    dir_cus = _id_dir(MODELOS / "customer")

    def fit_rental():
        mod = REaLTabFormer(model_type="relational", parent_realtabformer_path=dir_cus,
                            epochs=a.epocas_rental, output_max_length=None, train_size=0.8, **relac)
        enCurso["mod"] = _atencion_eager(mod)
        mod.fit(df=ren.drop(columns=["rental_id"]), in_df=cus, join_on="customer_id", device=a.device)
        _guardar(mod, MODELOS / "rental")
        return mod
    m_ren = correr("entrenar rental (relacional, padre customer)", fit_rental)
    info["rental_max_tokens"] = m_ren.relational_max_length

    # --- Exp. 3: rental -> payment (relacional), sin modelo padre ya entrenado --------------------
    #     El encoder no puede venir de un modelo tabular de rental entrenado con customer_id, porque
    #     los alquileres sintéticos llegan con ids nuevos: se entrena desde cero sobre las columnas
    #     de rental que sí genera el exp. 1.
    ren_feat = ren.drop(columns=["customer_id"])

    def fit_payment():
        mod = REaLTabFormer(model_type="relational", epochs=a.epocas_payment, output_max_length=None,
                            train_size=0.8, **comunes)
        enCurso["mod"] = _atencion_eager(mod)
        mod.fit(df=pay.drop(columns=["payment_id"]), in_df=ren_feat, join_on="rental_id", device=a.device)
        _guardar(mod, MODELOS / "payment")
        return mod
    m_pay = correr("entrenar payment (relacional, padre rental)", fit_payment)
    info["payment_max_tokens"] = m_pay.relational_max_length

    info["filas_entrada"] = {t: len(d) for t, d in datos.items()}
    info["dispositivo"] = str(next(m_ren.model.parameters()).device) if m_ren.model is not None else a.device
    registrar("entrenar", {"fases": fases, **info})


# ----------------------------------------------------------------------------- generar

def generar(a):
    """Carga los tres modelos guardados por `entrenar` y genera la cadena. Los alquileres se generan
    por lotes de `--lote` clientes y se registra el tiempo de cada lote: si la generación es demasiado
    lenta, lo generado hasta ahí queda medido."""
    import warnings
    warnings.filterwarnings("ignore")
    import pandas as pd
    import torch
    from realtabformer import REaLTabFormer

    torch.manual_seed(a.semilla_modelo)
    os.chdir(GRANDES)
    ren_cols = [c for c in COLUMNAS["rental"] if c not in ("rental_id", "customer_id")]
    fases, info = {}, {"parametros": {k: v for k, v in vars(a).items() if k != "func"}, "entorno": entorno()}
    with Medidor() as m:
        m_cus = REaLTabFormer.load_from_dir(_id_dir(MODELOS / "customer"))
        m_ren = _atencion_eager(REaLTabFormer.load_from_dir(_id_dir(MODELOS / "rental")))
        m_pay = _atencion_eager(REaLTabFormer.load_from_dir(_id_dir(MODELOS / "payment")))
    fases["cargar modelos"] = m.dict()

    SINTETICO.mkdir(parents=True, exist_ok=True)
    if a.reusar_alquileres:   # clientes y alquileres de una corrida anterior de `generar`
        s_cus = pd.read_parquet(SINTETICO / "customer.parquet")
        s_ren = pd.read_parquet(SINTETICO / "rental.parquet")
        previo = json.loads(TIEMPOS.read_text()).get("generar", {}).get("fases", {})
        fases.update({k: v for k, v in previo.items() if k in ("generar customer", "generar rental")})
    else:
        with Medidor() as m:
            s_cus = m_cus.sample(n_samples=a.clientes, device=a.device).head(a.clientes)
            s_cus.index = range(1, len(s_cus) + 1)
            s_cus.index.name = "customer_id"
            s_cus = s_cus.reset_index()
        fases["generar customer"] = m.dict()
        print(f"[generar customer] {m.segundos:.0f} s", flush=True)

        lotes, partes = [], []
        with Medidor() as m:
            for i in range(0, len(s_cus), a.lote):
                t0 = time.perf_counter()
                sub = s_cus.iloc[i:i + a.lote]
                rs, fallos = _con_reintentos(lambda: m_ren.sample(
                    input_unique_ids=sub["customer_id"], input_df=sub.drop(columns=["customer_id"]),
                    gen_batch=a.lote, device=a.device))
                if rs is not None:
                    partes.append(_con_ids(rs, "customer_id", sub["customer_id"]))
                seg = time.perf_counter() - t0
                n_alq = 0 if rs is None else len(rs)
                lotes.append({"clientes": len(sub), "alquileres": n_alq, "segundos": round(seg, 1),
                              "fallos": fallos, "descartado": rs is None})
                print(f"  lote {i // a.lote + 1}: {len(sub)} clientes, {n_alq} alquileres, {seg:.0f} s"
                      + (f", {len(fallos)} fallos" if fallos else "") + (" (DESCARTADO)" if rs is None else ""),
                      flush=True)
                registrar("generar", {"fases": {**fases, "generar rental (en curso)": {"lotes": lotes}}, **info})
            s_ren = pd.concat(partes, ignore_index=True)
            s_ren.insert(0, "rental_id", range(1, len(s_ren) + 1))
        fases["generar rental"] = {**m.dict(), "lotes": lotes}
        print(f"[generar rental] {m.segundos:.0f} s", flush=True)
        s_cus.to_parquet(SINTETICO / "customer.parquet", index=False)
        s_ren.to_parquet(SINTETICO / "rental.parquet", index=False)
        registrar("generar", {"fases": fases, **info})

    # Pagos por lotes: en la 0.2.4 una fecha generada sin dígitos rompe todo el sample
    # (`int('')` en rtf_sampler._recover_data_values). Se reintenta el lote; si sigue fallando, se descarta.
    partes, fallos, descartados = [], [], 0
    with Medidor() as m:
        for i in range(0, len(s_ren), a.gen_batch):
            sub = s_ren.iloc[i:i + a.gen_batch]
            ps, f = _con_reintentos(lambda: m_pay.sample(input_unique_ids=sub["rental_id"], input_df=sub[ren_cols],
                                                         gen_batch=a.gen_batch, device=a.device))
            fallos += [{"lote": i // a.gen_batch + 1, "error": x} for x in f]
            if ps is None:
                descartados += len(sub)
            else:
                partes.append(_con_ids(ps, "rental_id", sub["rental_id"]))
        ps = pd.concat(partes, ignore_index=True)
        ps.insert(0, "payment_id", range(1, len(ps) + 1))
    fases["generar payment"] = {**m.dict(), "fallos_sample": len(fallos),
                                "alquileres_sin_generar_pagos": descartados, "detalle_fallos": fallos[:20]}
    print(f"[generar payment] {m.segundos:.0f} s, {len(fallos)} fallos, {descartados} alquileres descartados",
          flush=True)

    for t, df in (("customer", s_cus), ("rental", s_ren), ("payment", ps)):
        df.to_parquet(SINTETICO / f"{t}.parquet", index=False)
    info["filas_sinteticas"] = {"customer": len(s_cus), "rental": len(s_ren), "payment": len(ps)}
    registrar("generar", {"fases": fases, **info})
    print(json.dumps(info["filas_sinteticas"]), flush=True)


# ----------------------------------------------------------------------------- cargar

def cargar(a):
    import pandas as pd
    from psycopg2 import sql
    from psycopg2.extras import execute_values
    sys.path.insert(0, str(RAIZ / "scripts"))
    import integridad as ig

    sint = {t: pd.read_parquet(SINTETICO / f"{t}.parquet") for t in COLUMNAS}
    real = {t: pd.read_parquet(ENTRADA / f"{t}.parquet") for t in COLUMNAS}
    with Medidor() as m:
        with ig.conexion("postgres") as c, c.cursor() as cur:
            cur.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(CANDIDATA)))
            cur.execute(sql.SQL("CREATE DATABASE {} TEMPLATE {}").format(sql.Identifier(CANDIDATA),
                                                                         sql.Identifier(BASE_ENTRENAMIENTO)))
        with ig.conexion(CANDIDATA) as c:
            ig.quitar_todo(c)
        conn = ig.conectar(CANDIDATA)
        fuera_de_particion = 0
        with conn, conn.cursor() as cur:
            cur.execute("truncate payment, rental, customer")
            cur.execute("select min(range_start), max(range_end) from (select "
                        "(regexp_match(pg_get_expr(c.relpartbound, c.oid), 'FROM \\(''([^'']+)''\\)'))[1]::timestamptz range_start, "
                        "(regexp_match(pg_get_expr(c.relpartbound, c.oid), 'TO \\(''([^'']+)''\\)'))[1]::timestamptz range_end "
                        "from pg_inherits i join pg_class c on c.oid = i.inhrelid "
                        "where i.inhparent = 'public.payment'::regclass) x")
            desde, hasta = cur.fetchone()
            for t in ("customer", "rental", "payment"):
                df = sint[t][COLUMNAS[t]].copy()
                for col in df.columns:
                    if (t, col) in FECHAS:
                        df[col] = pd.to_datetime(df[col]).dt.tz_localize("UTC")
                if t == "payment":   # una fila fuera de las particiones haría fallar el INSERT
                    dentro = (df["payment_date"] >= desde) & (df["payment_date"] < hasta)
                    fuera_de_particion = int((~dentro).sum())
                    df = df[dentro]
                filas = [tuple(None if pd.isna(v) else (v.to_pydatetime() if hasattr(v, "to_pydatetime") else
                                                         (v.item() if hasattr(v, "item") else v)) for v in r)
                         for r in df.itertuples(index=False)]
                execute_values(cur, sql.SQL("insert into {} ({}) values %s").format(
                    sql.Identifier(t), sql.SQL(", ").join(map(sql.Identifier, df.columns))).as_string(cur), filas)
            for t, pk in (("customer", "customer_id"), ("rental", "rental_id"), ("payment", "payment_id")):
                cur.execute(f"select setval(pg_get_serial_sequence('{t}', '{pk}'), coalesce(max({pk}), 1)) from {t}")
        # Coherencia y FK del exp. 3 y 4
        res = {"pagos_fuera_de_particion": fuera_de_particion, "rango_particiones": [str(desde), str(hasta)]}
        with conn.cursor() as cur:
            cur.execute("select count(*), count(*) filter (where p.customer_id <> r.customer_id) "
                        "from payment p join rental r using (rental_id)")
            res["pagos_con_alquiler"], res["pago_otro_cliente"] = cur.fetchone()
            cur.execute("select count(*) from payment p where not exists "
                        "(select 1 from rental r where r.rental_id = p.rental_id)")
            res["pagos_sin_alquiler"] = cur.fetchone()[0]
            cur.execute("select count(*) from rental r where not exists "
                        "(select 1 from customer c where c.customer_id = r.customer_id)")
            res["alquileres_sin_cliente"] = cur.fetchone()[0]
            fk = []
            for t, col, padre, pcol in OTRAS_FK:
                cur.execute(sql.SQL("select count(*), count(*) filter (where not exists (select 1 from {} p where "
                                    "p.{} = t.{})) from {} t").format(sql.Identifier(padre), sql.Identifier(pcol),
                                                                      sql.Identifier(col), sql.Identifier(t)))
                total, malas = cur.fetchone()
                fk.append({"fk": f"{t}.{col} -> {padre}", "filas": total, "sin_padre": malas,
                           "pct": round(100 * malas / total, 1) if total else ""})
            res["otras_fk"] = fk
            cur.execute("select count(*) from (select rental_date, inventory_id, customer_id from rental "
                        "group by 1, 2, 3 having count(*) > 1) x")
            res["rental_unique_duplicados"] = cur.fetchone()[0]
            cur.execute("select count(*) from rental where return_date < rental_date")
            res["devolucion_antes_del_alquiler"] = cur.fetchone()[0]
            cur.execute("select count(*) from payment p join rental r using (rental_id) "
                        "where p.payment_date < r.rental_date")
            res["pago_antes_del_alquiler"] = cur.fetchone()[0]
        conn.close()
    registrar("cargar", {**m.dict(), **{k: v for k, v in res.items() if k != "otras_fk"}})

    # Lo mismo en la muestra real, para comparar (los ids de padres sí existen por construcción).
    r_pay = real["payment"].merge(real["rental"][["rental_id", "customer_id"]], on="rental_id", suffixes=("", "_r"))
    res_real = {"pago_otro_cliente": int((r_pay["customer_id"] != r_pay["customer_id_r"]).sum()),
                "pagos_con_alquiler": len(r_pay),
                "devolucion_antes_del_alquiler": int((real["rental"]["return_date"] < real["rental"]["rental_date"]).sum())}

    # Alquileres por cliente y pagos por alquiler, real contra sintético
    def dist(df, clave, todos):
        return df.groupby(clave).size().reindex(todos, fill_value=0)
    a_r = dist(real["rental"], "customer_id", real["customer"]["customer_id"])
    a_s = dist(sint["rental"], "customer_id", sint["customer"]["customer_id"])
    p_r = dist(real["payment"], "rental_id", real["rental"]["rental_id"])
    p_s = dist(sint["payment"], "rental_id", sint["rental"]["rental_id"])
    dist_filas = [{"medida": nombre, "datos": d, "min": int(s.min()), "mediana": float(s.median()),
                   "promedio": round(float(s.mean()), 2), "max": int(s.max()), "ceros": int((s == 0).sum())}
                  for nombre, pares in (("alquileres por cliente", (("real", a_r), ("sintético", a_s))),
                                        ("pagos por alquiler", (("real", p_r), ("sintético", p_s))))
                  for d, s in pares]
    ig.guardar_csv(RESULTADOS / "d6_distribuciones.csv", dist_filas, list(dist_filas[0]))
    ig.guardar_csv(RESULTADOS / "d6_otras_fk.csv", res["otras_fk"], list(res["otras_fk"][0]))

    # Valores copiados tal cual (las columnas categóricas salen del vocabulario de entrenamiento)
    copias = {}
    rc, sc = real["customer"], sint["customer"]
    for col in ("first_name", "last_name", "email"):
        copias[col] = round(100 * sc[col].isin(set(rc[col])).mean(), 1)
    claves = ["first_name", "last_name", "email"]
    copias["persona_completa (nombre+apellido+email)"] = round(
        100 * sc[claves].merge(rc[claves].drop_duplicates(), on=claves, how="left", indicator=True)["_merge"]
        .eq("both").mean(), 1)
    res["pct_valores_copiados"] = copias
    (RESULTADOS / "d6_coherencia.json").write_text(json.dumps({"sintetico": res, "real_muestra": res_real},
                                                              indent=2, ensure_ascii=False, default=str),
                                                   encoding="utf-8")
    escribir_resumen(res, res_real, dist_filas, sint, real)
    print(f"Listo: {RESULTADOS / 'd6_resumen.md'}")


def tabla_md(filas, columnas):
    out = ["| " + " | ".join(columnas) + " |", "|" + "---|" * len(columnas)]
    out += ["| " + " | ".join(str(f.get(c, "")) for c in columnas) + " |" for f in filas]
    return "\n".join(out)


def escribir_resumen(res, res_real, dist_filas, sint, real):
    t = json.loads(TIEMPOS.read_text())
    ent = t.get("entrenar", {})
    paq = ent.get("entorno", {}).get("paquetes", {})
    p = ent.get("parametros", {})
    ex = t.get("exportar", {})
    lin_t = [{"fase": "exportar", **t.get("exportar", {})}]
    lin_t += [{"fase": k, **v} for k, v in ent.get("fases", {}).items() if k.startswith("entrenar")]
    gen = t.get("generar", {})
    lin_t += [{"fase": k, **v} for k, v in gen.get("fases", {}).items() if "segundos" in v]
    lin_t += [{"fase": "cargar y medir", **t.get("cargar", {})}]
    md = ["# D6: REaLTabFormer sobre customer -> rental -> payment", "",
          f"Corrida: {datetime.datetime.now():%Y-%m-%d %H:%M}", "",
          "## Entorno", "",
          f"- Equipo: {ent.get('entorno', {}).get('equipo')}. Dispositivo del modelo: {ent.get('dispositivo') or 'mps (memoria MPS ocupada al entrenar; ver tabla)'}",
          f"- realtabformer {paq.get('realtabformer')}, torch {paq.get('torch')}, transformers "
          f"{paq.get('transformers')}, pandas {paq.get('pandas')}, Python {ent.get('entorno', {}).get('python')}",
          f"- Muestra: {ex.get('clientes')} clientes de `{ex.get('base')}` (semilla `{ex.get('semilla')}`) con "
          f"sus alquileres y pagos: {ex.get('filas')}",
          f"- Épocas máx.: customer {p.get('epocas_tabular')}, rental {p.get('epocas_rental')}, payment "
          f"{p.get('epocas_payment')}; batch {p.get('batch_size')} (customer, payment) y {p.get('batch_rental')} "
          f"(rental); gradient checkpointing en rental: {'sí' if p.get('gradient_checkpointing') else 'no'}; semilla del modelo {p.get('semilla_modelo')}",
          f"- Largo máximo de la secuencia hija (tokens): rental {ent.get('rental_max_tokens')}, "
          f"payment {ent.get('payment_max_tokens')}", "",
          "## Tiempos y memoria", "",
          tabla_md(lin_t, ["fase", "segundos", "memoria_max_mb", "mps_max_mb"]), "",
          "## Filas", "",
          tabla_md([{"tabla": k, "muestra real": len(real[k]), "sintética": len(sint[k])} for k in COLUMNAS],
                   ["tabla", "muestra real", "sintética"]), "",
          tabla_md(dist_filas, ["medida", "datos", "min", "mediana", "promedio", "max", "ceros"]), "",
          "## Coherencia de la cadena (exp. 3)", "",
          f"- Alquileres sin cliente: {res['alquileres_sin_cliente']} · pagos sin alquiler: {res['pagos_sin_alquiler']}"
          " (las claves de la relación modelada las pone el script, así que tienen que dar 0)",
          f"- **Pagos cuyo cliente no es el de su alquiler: {res['pago_otro_cliente']} de {res['pagos_con_alquiler']}** "
          f"(muestra real: {res_real['pago_otro_cliente']} de {res_real['pagos_con_alquiler']})",
          f"- Pagos anteriores a su alquiler: {res['pago_antes_del_alquiler']}",
          f"- Alquileres devueltos antes de alquilarse: {res['devolucion_antes_del_alquiler']} "
          f"(muestra real: {res_real['devolucion_antes_del_alquiler']})",
          f"- Pagos fuera de las particiones de payment (no se pudieron cargar): {res['pagos_fuera_de_particion']}",
          f"- Duplicados de la UNIQUE (rental_date, inventory_id, customer_id): {res['rental_unique_duplicados']}", "",
          "## FK que no se pueden declarar (exp. 4)", "",
          tabla_md(res["otras_fk"], ["fk", "filas", "sin_padre", "pct"]), "",
          "## Valores copiados del entrenamiento (% de filas sintéticas)", "",
          tabla_md([{"columna": k, "pct": v} for k, v in res["pct_valores_copiados"].items()], ["columna", "pct"]),
          "", "Calidad y privacidad con la vara común: `pruebas/E3-chequeos-propios/resultados/d6_auditoria/`."]
    (RESULTADOS / "d6_resumen.md").write_text("\n".join(md) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("exportar")
    e.add_argument("--base", default=BASE_ENTRENAMIENTO)
    e.add_argument("--clientes", type=int, default=200)
    e.add_argument("--semilla", default="d6")
    t = sub.add_parser("entrenar")
    t.add_argument("--epocas-tabular", type=int, default=100)
    t.add_argument("--epocas-rental", type=int, default=5)
    t.add_argument("--epocas-payment", type=int, default=20)
    t.add_argument("--batch-size", type=int, default=8, help="batch de customer y payment (default de la librería)")
    t.add_argument("--batch-rental", type=int, default=1, help="batch del modelo relacional customer -> rental")
    t.add_argument("--bootstrap", type=int, default=500, help="num_bootstrap del criterio de parada del tabular")
    t.add_argument("--gradient-checkpointing", action="store_true",
                   help="en el modelo de rental: menos memoria a cambio de más cómputo")
    t.add_argument("--device", default="cuda", help="cuda cae a mps o cpu (lógica de la librería)")
    t.add_argument("--semilla-modelo", type=int, default=1029)
    g = sub.add_parser("generar")
    g.add_argument("--clientes", type=int, default=50, help="clientes sintéticos a generar")
    g.add_argument("--lote", type=int, default=5, help="clientes por lote al generar alquileres")
    g.add_argument("--gen-batch", type=int, default=64, help="lote al generar pagos")
    g.add_argument("--device", default="cuda")
    g.add_argument("--reusar-alquileres", action="store_true",
                   help="no regenerar clientes ni alquileres: usar los de salidas_grandes/sintetico/")
    g.add_argument("--semilla-modelo", type=int, default=1029)
    sub.add_parser("cargar")
    a = ap.parse_args()
    {"exportar": exportar, "entrenar": entrenar, "generar": generar, "cargar": cargar}[a.cmd](a)


if __name__ == "__main__":
    main()
