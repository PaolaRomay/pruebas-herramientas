#!/usr/bin/env python3
"""Prueba D2: MOSTLY AI (SDK en modo local) genera una versión sintética multi-tabla de Pagila.

Se entrena con `e3_entrenamiento` (Pagila sin los clientes de control de E3, ver
pruebas/E3-chequeos-propios) para que después se pueda medir la privacidad contra ese control.

Tres pasos, en dos entornos de Python distintos (mostlyai 6.1 exige torch<2.14 y el lock del repo
trae torch 2.14.1, así que no pueden convivir):

  exportar  [.venv del repo]           lee e3_entrenamiento y deja un Parquet por tabla
  entrenar  [entorno de MOSTLY AI]     entrena el generador, genera la base sintética y guarda las
                                       métricas y los reportes HTML de MOSTLY
  cargar    [.venv del repo]           renumera las claves (MOSTLY las devuelve como texto), arma un
                                       .sql y lo carga dos veces, igual que D5: con todas las
                                       restricciones (d2_estricta) y sin restricciones (d2_auditoria)

Cada paso mide su tiempo y su memoria máxima (proceso + subprocesos) y los agrega a
resultados/d2_tiempos.json. Después se evalúa con E3:
    python pruebas/E3-chequeos-propios/evaluar_bd.py evaluar --candidata d2_auditoria \\
        --tipo sintetica --entrenada-con e3_entrenamiento

Uso (desde la raíz del repo, con la base levantada):
    .venv/bin/python pruebas/D2-mostlyai/d2_mostlyai.py exportar
    ../.venv/bin/python pruebas/D2-mostlyai/d2_mostlyai.py entrenar [--max-minutos 10]
    .venv/bin/python pruebas/D2-mostlyai/d2_mostlyai.py cargar
"""
import argparse
import datetime
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
ENTRADA, SINTETICO = GRANDES / "entrada", GRANDES / "sintetico"
RESULTADOS, EVIDENCIA = AQUI / "resultados", AQUI / "evidencia"
TIEMPOS = RESULTADOS / "d2_tiempos.json"
BASE_ENTRENAMIENTO = "e3_entrenamiento"

# Modelo de Pagila para MOSTLY: PK y FK por tabla. Una sola FK de contexto por tabla (regla de
# MOSTLY, D); se eligieron para conservar las correlaciones de las personas
# (country > city > address > customer > rental > payment) y de las películas
# (film > film_actor / film_category / inventory). El resto de las FK es no-contexto: según la
# documentación solo garantizan integridad referencial, no correlaciones.
TABLAS = {
    "country": {"pk": "country_id", "fks": []},
    "city": {"pk": "city_id", "fks": [("country_id", "country", True)]},
    "address": {"pk": "address_id", "fks": [("city_id", "city", True)]},
    "language": {"pk": "language_id", "fks": []},
    "category": {"pk": "category_id", "fks": []},
    "actor": {"pk": "actor_id", "fks": []},
    "film": {"pk": "film_id", "fks": [("language_id", "language", False)]},
    "film_actor": {"pk": None, "fks": [("film_id", "film", True), ("actor_id", "actor", False)]},
    "film_category": {"pk": None, "fks": [("film_id", "film", True), ("category_id", "category", False)]},
    "store": {"pk": "store_id", "fks": [("address_id", "address", False),
                                        ("manager_staff_id", "staff", False)]},   # no declarada en Pagila
    "staff": {"pk": "staff_id", "fks": [("store_id", "store", True), ("address_id", "address", False)]},
    "customer": {"pk": "customer_id", "fks": [("address_id", "address", True), ("store_id", "store", False)]},
    "inventory": {"pk": "inventory_id", "fks": [("film_id", "film", True), ("store_id", "store", False)]},
    "rental": {"pk": "rental_id", "fks": [("customer_id", "customer", True), ("inventory_id", "inventory", False),
                                          ("staff_id", "staff", False)]},
    # payment apunta a rental (padre) y a customer (abuelo). La documentación de MOSTLY recomienda
    # sacar la FK al abuelo del entrenamiento y reconstruirla después: customer_id se rearma desde
    # rental.customer_id en el paso «cargar».
    "payment": {"pk": "payment_id", "fks": [("rental_id", "rental", True), ("staff_id", "staff", False)]},
}
# Columnas que no se entrenan: técnicas, vacías en Pagila, binarias, tsvector (las rellena un
# trigger), uuid (las rellena el DEFAULT gen_random_uuid()) y la FK al abuelo de payment.
EXCLUIDAS = {("*", "last_update"), ("film", "fulltext"), ("film", "original_language_id"), ("staff", "picture"),
             ("customer", "uuid"), ("rental", "uuid"), ("payment", "uuid"), ("payment", "customer_id")}
COMO_TEXTO = {("film", "special_features"), ("film", "rating")}   # text[] y enum: se pasan como texto
# Orden de carga (padres antes que hijas; store antes que staff aunque store.manager_staff_id apunte
# a staff: esa relación no tiene FK en Pagila).
ORDEN = ["country", "city", "address", "language", "category", "actor", "film", "film_actor", "film_category",
         "store", "staff", "customer", "inventory", "rental", "payment"]


# ----------------------------------------------------------------------------- medición

class Medidor:
    """Tiempo de reloj y memoria máxima (RSS del proceso y de todos sus subprocesos), muestreada.
    Sin psutil (el .venv del repo no lo trae) usa getrusage: pico del proceso y, aparte, de sus hijos
    ya terminados; en macOS ru_maxrss viene en bytes."""

    def __init__(self, cada=0.25):
        try:
            import psutil
        except ImportError:
            psutil = None
        self.psutil, self.cada, self.pico, self._parar = psutil, cada, 0, threading.Event()

    def _rss(self):
        if self.psutil is None:
            import resource
            return max(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                       resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
        p = self.psutil.Process()
        total = p.memory_info().rss
        for h in p.children(recursive=True):
            try:
                total += h.memory_info().rss
            except Exception:
                pass
        return total

    def _bucle(self):
        while not self._parar.is_set():
            try:
                self.pico = max(self.pico, self._rss())
            except Exception:   # un subproceso que terminó entre la lista y la lectura
                pass
            self._parar.wait(self.cada)

    def __enter__(self):
        self.t0 = time.perf_counter()
        self._hilo = threading.Thread(target=self._bucle, daemon=True)
        self._hilo.start()
        return self

    def __exit__(self, *exc):
        self._parar.set()
        self._hilo.join()
        self.pico = max(self.pico, self._rss())
        self.segundos = time.perf_counter() - self.t0
        return False

    def dict(self):
        return {"segundos": round(self.segundos, 1), "memoria_max_mb": round(self.pico / 2**20),
                "medicion_memoria": "psutil (proceso + subprocesos, muestreo cada 0,25 s)" if self.psutil
                else "getrusage (pico del proceso o de sus hijos)"}


def registrar(fase, datos):
    RESULTADOS.mkdir(parents=True, exist_ok=True)
    todo = json.loads(TIEMPOS.read_text()) if TIEMPOS.exists() else {}
    todo[fase] = {**datos, "registrado": f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S}"}
    TIEMPOS.write_text(json.dumps(todo, indent=2, ensure_ascii=False), encoding="utf-8")


def ver(paquete):
    try:
        return version(paquete)
    except PackageNotFoundError:
        return "no instalado"


def entorno():
    return {"equipo": f"{platform.machine()}, macOS {platform.mac_ver()[0]}", "python": platform.python_version(),
            "ejecutable": sys.executable,
            "paquetes": {p: ver(p) for p in ("mostlyai", "mostlyai-engine", "mostlyai-qa", "torch", "pandas",
                                             "numpy", "pyarrow", "sqlalchemy", "psycopg2-binary")
                         if ver(p) != "no instalado"}}


def excluida(t, c):
    return ("*", c) in EXCLUIDAS or (t, c) in EXCLUIDAS


# ----------------------------------------------------------------------------- exportar

def exportar(a):
    import pandas as pd
    import sqlalchemy as sa
    with Medidor() as m:
        ENTRADA.mkdir(parents=True, exist_ok=True)
        eng = sa.create_engine(f"postgresql+psycopg2://postgres:postgres@127.0.0.1:55432/{a.base}")
        esquema, filas = {}, {}
        with eng.connect() as c:
            prep = c.dialect.identifier_preparer
            for t in ORDEN:
                cols = c.execute(sa.text("select column_name, data_type from information_schema.columns "
                                         "where table_schema='public' and table_name=:t order by ordinal_position"),
                                 {"t": t}).fetchall()
                usar = [(col, tipo) for col, tipo in cols if not excluida(t, col)]
                sel = ", ".join(f"{prep.quote(col)}::text as {prep.quote(col)}" if (t, col) in COMO_TEXTO
                                else prep.quote(col) for col, _ in usar)
                df = pd.read_sql(sa.text(f"select {sel} from public.{prep.quote(t)}"), c)
                for col, tipo in usar:
                    if tipo.startswith("timestamp"):   # sin zona, en UTC (MOSTLY no maneja zonas)
                        df[col] = pd.to_datetime(df[col], utc=True).dt.tz_localize(None)
                    elif tipo == "date":
                        df[col] = pd.to_datetime(df[col])
                    elif tipo == "numeric":
                        df[col] = pd.to_numeric(df[col]).astype(float)
                df.to_parquet(ENTRADA / f"{t}.parquet", index=False)
                esquema[t] = {col: tipo for col, tipo in usar}
                filas[t] = len(df)
        (ENTRADA / "esquema.json").write_text(json.dumps(esquema, indent=2), encoding="utf-8")
    registrar("exportar", {**m.dict(), "base": a.base, "filas": filas, "entorno": entorno()})
    print(f"Exportadas {len(filas)} tablas, {sum(filas.values())} filas, en {m.segundos:.1f} s -> {ENTRADA}")


# ----------------------------------------------------------------------------- entrenar

def config_generador(datos, max_minutos, con_gerente=True):
    tablas = []
    for t in ORDEN:
        spec = TABLAS[t]
        fks = [{"column": c, "referenced_table": r, "is_context": ctx} for c, r, ctx in spec["fks"]
               if c in datos[t].columns and (con_gerente or (t, c) != ("store", "manager_staff_id"))]
        tabla = {"name": t, "data": datos[t],
                 "tabular_model_configuration": {"max_training_time": max_minutos}}
        if spec["pk"]:
            tabla["primary_key"] = spec["pk"]
        if fks:
            tabla["foreign_keys"] = fks
        if not con_gerente and t == "store":
            tabla["data"] = datos[t].drop(columns=["manager_staff_id"])
        tablas.append(tabla)
    return {"name": "d2-pagila", "tables": tablas}


def metricas_modelo(g):
    out = {}
    for t in g.tables:
        mm = t.tabular_model_metrics
        if mm is None:
            continue
        out[t.name] = {
            "accuracy": mm.accuracy.overall, "accuracy_univariada": mm.accuracy.univariate,
            "accuracy_bivariada": mm.accuracy.bivariate, "accuracy_trivariada": mm.accuracy.trivariate,
            "coherencia": mm.accuracy.coherence, "accuracy_max_holdout": mm.accuracy.overall_max,
            "dcr_entrenamiento": mm.distances.dcr_training, "dcr_holdout": mm.distances.dcr_holdout,
            "dcr_share": mm.distances.dcr_share, "ims_entrenamiento": mm.distances.ims_training,
            "ims_holdout": mm.distances.ims_holdout,
            "discriminador_auc": mm.similarity.discriminator_auc_training_synthetic,
        }
    return out


def entrenar(a):
    import shutil
    import warnings
    warnings.filterwarnings("ignore")
    fases = {}
    with Medidor() as m_arranque:
        import pandas as pd
        from mostlyai.sdk import MostlyAI
        datos = {t: pd.read_parquet(ENTRADA / f"{t}.parquet") for t in ORDEN}
        local_dir = GRANDES / "mostly_local"
        if local_dir.exists() and not a.conservar:
            shutil.rmtree(local_dir)
        mostly = MostlyAI(local=True, local_dir=str(local_dir), quiet=True)
    fases["arranque"] = m_arranque.dict()
    print(f"[arranque] {m_arranque.segundos:.0f} s", flush=True)

    avisos, con_gerente = [], True
    with Medidor() as m_ent:
        try:
            g = mostly.train(config=config_generador(datos, a.max_minutos, True), start=True, wait=True)
        except Exception as e:   # p. ej. si MOSTLY rechaza el ciclo store <-> staff
            avisos.append(f"Con store.manager_staff_id como FK no-contexto, MOSTLY falló: "
                          f"{type(e).__name__}: {str(e)[:300]}. Se reintentó sin esa columna.")
            con_gerente = False
            g = mostly.train(config=config_generador(datos, a.max_minutos, False), start=True, wait=True)
    fases["entrenamiento"] = m_ent.dict()
    print(f"[entrenamiento] {m_ent.segundos:.0f} s, {m_ent.pico / 2**30:.1f} GB", flush=True)

    with Medidor() as m_gen:
        sd = mostly.generate(g, start=True, wait=True)
        sint = sd.data()
    fases["generacion"] = m_gen.dict()
    print(f"[generacion] {m_gen.segundos:.0f} s, {m_gen.pico / 2**30:.1f} GB", flush=True)

    SINTETICO.mkdir(parents=True, exist_ok=True)
    for t, df in sint.items():
        df.to_parquet(SINTETICO / f"{t}.parquet", index=False)

    # Reportes HTML de MOSTLY (modelo = calidad del generador; datos = calidad de lo generado).
    # Pesan ~6 MB cada uno (~170 MB en total): van a salidas_grandes/, que no se sube.
    dest = GRANDES / "reportes_mostly"
    if dest.exists():
        shutil.rmtree(dest)
    for sub in ("generators", "synthetic-datasets"):
        for html in (local_dir / sub).glob("*/*QAReports/*.html"):
            d = dest / ("modelo" if "Model" in html.parent.name else "datos")
            d.mkdir(parents=True, exist_ok=True)
            shutil.copy(html, d / html.name.replace(":", "_"))

    estados = {}
    try:
        estados = {"generador": str(g.training_status), "dataset": str(sd.generation_status)}
    except Exception:
        pass
    resumen = {"config": {t: {"pk": TABLAS[t]["pk"], "fks": TABLAS[t]["fks"]} for t in ORDEN},
               "max_minutos_por_tabla": a.max_minutos, "con_store_manager_fk": con_gerente,
               "accuracy_global": getattr(g, "accuracy", None), "metricas_por_tabla": metricas_modelo(g),
               "filas_entrada": {t: len(d) for t, d in datos.items()},
               "filas_sinteticas": {t: len(d) for t, d in sint.items()},
               "estados": estados, "avisos": avisos, "entorno": entorno(), "dispositivo": "cpu (ver ficha)"}
    (RESULTADOS / "d2_metricas_mostly.json").write_text(json.dumps(resumen, indent=2, ensure_ascii=False,
                                                                   default=str), encoding="utf-8")
    registrar("entrenar", {"fases": fases, "max_minutos_por_tabla": a.max_minutos, "entorno": entorno()})
    print(f"Listo. Accuracy global de MOSTLY: {resumen['accuracy_global']}")
    os._exit(0)   # evita el error de multiprocess al cerrar con Python 3.12.0 (no afecta resultados)


# ----------------------------------------------------------------------------- tiempos por tabla

ETAPAS = {"PULL_TRAINING_DATA": "leer", "ANALYZE_TRAINING_DATA": "analizar", "ENCODE_TRAINING_DATA": "codificar",
          "TRAIN_MODEL": "entrenar", "GENERATE_MODEL_REPORT_DATA": "reporte_modelo",
          "CREATE_MODEL_REPORT": "reporte_modelo", "GENERATE_DATA": "generar",
          "CREATE_DATA_REPORT": "reporte_datos", "GENERATE_DATA_REPORT_DATA": "reporte_datos",
          "GENERATE_DATA_TABULAR": "generar", "CREATE_DATA_REPORT_TABULAR": "reporte_datos",
          "FINALIZE_TRAINING": "finalizar", "FINALIZE_GENERATION": "finalizar", "DELIVER_DATA": "entregar"}


def tiempos_por_tabla():
    """Segundos por tabla y etapa, sacados de los job_progress.json que MOSTLY deja en modo local."""
    filas = {}
    for trabajo, carpeta in (("entrenamiento", "generators"), ("generacion", "synthetic-datasets")):
        for jp in (GRANDES / "mostly_local" / carpeta).glob("*/job_progress.json"):
            for s in json.loads(jp.read_text()).get("steps", []):
                if not (s.get("startDate") and s.get("endDate")):
                    continue
                seg = (datetime.datetime.fromisoformat(s["endDate"].replace("Z", "+00:00"))
                       - datetime.datetime.fromisoformat(s["startDate"].replace("Z", "+00:00"))).total_seconds()
                tabla = (s.get("modelLabel") or "(global)").split(":")[0]
                etapa = ETAPAS.get(s.get("stepCode"), (s.get("stepCode") or "otro").lower())
                f = filas.setdefault((trabajo, tabla), {"trabajo": trabajo, "tabla": tabla})
                f[etapa] = round(f.get(etapa, 0) + seg, 1)
    return [filas[k] for k in sorted(filas, key=lambda k: (k[0], ORDEN.index(k[1]) if k[1] in ORDEN else 99))]


# ----------------------------------------------------------------------------- cargar

def _valor_copy(v, tipo):
    import pandas as pd
    if v is None or (not isinstance(v, (list, dict)) and pd.isna(v)):
        return r"\N"
    if tipo.startswith("timestamp"):
        return pd.Timestamp(v).strftime("%Y-%m-%d %H:%M:%S") + "+00"
    if tipo == "date":
        return pd.Timestamp(v).strftime("%Y-%m-%d")
    if tipo == "boolean":
        return "t" if bool(v) else "f"
    if tipo in ("integer", "smallint", "bigint"):
        return str(int(v))
    s = str(v)
    return s.replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n").replace("\r", "\\r")


def cargar(a):
    import pandas as pd
    sys.path.insert(0, str(RAIZ / "scripts"))
    import integridad as ig

    esquema = json.loads((ENTRADA / "esquema.json").read_text())
    info = json.loads((RESULTADOS / "d2_metricas_mostly.json").read_text())
    with Medidor() as m_post:
        datos = {t: pd.read_parquet(SINTETICO / f"{t}.parquet") for t in ORDEN}
        if not info.get("con_store_manager_fk", True):
            esquema["store"].pop("manager_staff_id", None)
        # 1. Renumerar claves: MOSTLY devuelve PK/FK como texto. Cada PK pasa a 1..n y cada FK se
        #    traduce con el mapa de su tabla padre. Una FK que no está en el mapa queda en -1 (huérfana).
        mapas, sin_mapa = {}, {}
        for t in ORDEN:
            pk = TABLAS[t]["pk"]
            if pk and pk in datos[t]:
                claves = datos[t][pk].astype(str)
                mapas[t] = {k: i for i, k in enumerate(pd.unique(claves), start=1)}
                datos[t][pk] = claves.map(mapas[t]).astype("Int64")
        for t in ORDEN:
            for col, ref, _ in TABLAS[t]["fks"]:
                if col in datos[t]:
                    orig = datos[t][col]
                    nuevo = orig.astype("string").map(mapas[ref]).astype("Int64")
                    perdidas = int((orig.notna() & nuevo.isna()).sum())
                    if perdidas:
                        sin_mapa[f"{t}.{col}"] = perdidas
                    datos[t][col] = nuevo.where(orig.isna() | nuevo.notna(), -1)
        # 2. payment.customer_id se reconstruye desde su rental (recomendación de MOSTLY, D)
        cli = datos["rental"].set_index("rental_id")["customer_id"]
        datos["payment"]["customer_id"] = datos["payment"]["rental_id"].map(cli).astype("Int64")
        esquema["payment"]["customer_id"] = "integer"
        # 3. Un .sql con un COPY por tabla (las columnas que faltan toman su DEFAULT o trigger)
        GRANDES.mkdir(parents=True, exist_ok=True)
        archivo = GRANDES / "d2_sintetico.sql"
        with open(archivo, "w", encoding="utf-8") as f:
            for t in ORDEN:
                cols = [c for c in esquema[t] if c in datos[t].columns]
                f.write(f'COPY public."{t}" ({", ".join(chr(34) + c + chr(34) for c in cols)}) FROM stdin;\n')
                for fila in datos[t][cols].itertuples(index=False):
                    f.write("\t".join(_valor_copy(v, esquema[t][c]) for v, c in zip(fila, cols)) + "\n")
                f.write("\\.\n\n")
    registrar("postproceso", {**m_post.dict(), "claves_sin_padre": sin_mapa})
    print(f"[postproceso] {m_post.segundos:.1f} s -> {archivo.name}", flush=True)

    with ig.conexion("pagila") as ref:
        restr = ig.restricciones(ref)
        conteo_real = ig.conteos(ref)
    with ig.conexion(BASE_ENTRENAMIENTO) as c:
        conteo_ent = ig.conteos(c)

    with Medidor() as m_carga:
        err_esq, _ = ig.preparar_base("d2_estricta")
        if err_esq:
            sys.exit(f"El esquema de Pagila dio {len(err_esq)} errores; revisar.")
        with ig.conexion("d2_estricta") as c:
            fks = ig.quitar_fks(c)
        t0 = time.perf_counter()
        _, out = ig.cargar_sql("d2_estricta", archivo, GRANDES / "carga_estricta.log")
        seg_estricta = time.perf_counter() - t0
        err_estricta = ig.parsear_errores(out)
        with ig.conexion("d2_estricta") as c:
            fk_res = ig.poner_fks(c, fks)
            conteo_estricta = ig.conteos(c)
        _, avisos = ig.preparar_base("d2_auditoria", sin_restricciones=True)
        _, out = ig.cargar_sql("d2_auditoria", archivo, GRANDES / "carga_auditoria.log")
        err_aud = ig.parsear_errores(out)
        with ig.conexion("d2_auditoria") as c:
            conteo_aud = ig.conteos(c)
            viol = ig.contar_violaciones(c, restr)
    registrar("carga", {**m_carga.dict(), "segundos_carga_estricta": round(seg_estricta, 1)})

    # Coherencia transitiva: ¿el cliente del pago es el del alquiler? (por construcción, sí)
    with ig.conexion("d2_auditoria") as c, c.cursor() as cur:
        cur.execute("select count(*) from payment p join rental r using (rental_id) "
                    "where p.customer_id <> r.customer_id")
        pago_otro_cliente = cur.fetchone()[0]
        cur.execute("select count(*) from store s join staff st on st.staff_id = s.manager_staff_id "
                    "where st.store_id = s.store_id")
        gerente_de_su_tienda = cur.fetchone()[0]
        cur.execute("select min(payment_date)::date, max(payment_date)::date, "
                    "min(rental_date)::date, max(rental_date)::date from payment, rental")
        rangos = cur.fetchone()

    ig.guardar_csv(RESULTADOS / "d2_restricciones.csv", viol, ig.CAMPOS_RESTRICCIONES)
    filas = [{"tabla": t, "pagila": conteo_real.get(t, ""), "entrenamiento": conteo_ent.get(t, ""),
              "sintetica": len(datos[t]), "cargadas_auditoria": conteo_aud.get(t, 0),
              "cargadas_estricta": conteo_estricta.get(t, 0)} for t in ORDEN]
    ig.guardar_csv(RESULTADOS / "d2_conteos.csv", filas, list(filas[0]))
    errores = [dict(e, fase="estricta") for e in err_estricta] + [dict(e, fase="auditoria") for e in err_aud]
    ig.guardar_csv(EVIDENCIA / "d2_errores_carga.csv", errores,
                   ["fase", "linea", "sqlstate", "tipo", "tabla", "mensaje", "detalle", "contexto"])
    escribir_resumen(info, filas, err_estricta, fk_res, viol, avisos, sin_mapa, pago_otro_cliente,
                     gerente_de_su_tienda, rangos, ig)
    print(f"Listo: {RESULTADOS / 'd2_resumen.md'}")


def tabla_md(filas, columnas):
    out = ["| " + " | ".join(columnas) + " |", "|" + "---|" * len(columnas)]
    out += ["| " + " | ".join(str(f.get(c, "")) for c in columnas) + " |" for f in filas]
    return "\n".join(out)


def escribir_resumen(info, filas, err_estricta, fk_res, viol, avisos, sin_mapa, pago_otro_cliente,
                     gerente_de_su_tienda, rangos, ig):
    from collections import Counter
    tiempos = json.loads(TIEMPOS.read_text())
    ent = tiempos.get("entrenar", {}).get("fases", {})
    lin_t = [{"fase": "exportar (repo)", **tiempos.get("exportar", {})}]
    lin_t += [{"fase": f"{k} (MOSTLY)", **v} for k, v in ent.items()]
    lin_t += [{"fase": "post-proceso de claves y .sql (repo)", **tiempos.get("postproceso", {})},
              {"fase": "carga estricta + auditoría (repo)", **tiempos.get("carga", {})}]
    por_tabla = tiempos_por_tabla()
    if por_tabla:
        cols_t = ["trabajo", "tabla"] + [e for e in dict.fromkeys(ETAPAS.values())
                                         if any(e in f for f in por_tabla)]
        ig.guardar_csv(RESULTADOS / "d2_tiempos_por_tabla.csv", por_tabla, cols_t)
    met = info.get("metricas_por_tabla", {})
    lin_m = [{"tabla": t, **{k: (f"{v:.3f}" if isinstance(v, float) else v) for k, v in met[t].items()
                             if k in ("accuracy", "accuracy_max_holdout", "dcr_share", "discriminador_auc",
                                      "ims_entrenamiento")}} for t in ORDEN if t in met]
    por_tipo = ig.resumen_por_tipo(viol)
    fk_mal = [f for f in fk_res if not f[2]]
    paq = info["entorno"]["paquetes"]
    md = ["# D2: MOSTLY AI (SDK local) sobre Pagila", "",
          f"Corrida: {datetime.datetime.now():%Y-%m-%d %H:%M}", "",
          "## Entorno", "",
          f"- Equipo: {info['entorno']['equipo']}. Entrenamiento en CPU (el motor tabular no usa MPS).",
          f"- MOSTLY: mostlyai {paq.get('mostlyai')}, mostlyai-engine {paq.get('mostlyai-engine')}, "
          f"mostlyai-qa {paq.get('mostlyai-qa')}, torch {paq.get('torch')}, Python {info['entorno']['python']} "
          f"(`{info['entorno']['ejecutable']}`)",
          f"- Datos de entrenamiento: `{BASE_ENTRENAMIENTO}` (Pagila sin los 200 clientes de control de E3)",
          f"- Tope de entrenamiento: {info['max_minutos_por_tabla']} min por tabla; el resto, valores por defecto",
          f"- store.manager_staff_id como FK no-contexto: {'sí' if info['con_store_manager_fk'] else 'no (ver avisos)'}",
          "", "## Tiempos y memoria", "",
          tabla_md(lin_t, ["fase", "segundos", "memoria_max_mb"]), "",
          "Segundos por tabla y etapa, según los registros de MOSTLY (`d2_tiempos_por_tabla.csv`):", "",
          tabla_md(por_tabla, cols_t) if por_tabla else "(sin registros)", "",
          "## Métricas propias de MOSTLY (reporte de modelo, contra su holdout interno)", "",
          f"Accuracy global: **{info.get('accuracy_global')}**", "",
          tabla_md(lin_m, ["tabla", "accuracy", "accuracy_max_holdout", "dcr_share", "discriminador_auc",
                           "ims_entrenamiento"]), "",
          "## Filas", "", tabla_md(filas, list(filas[0])), "",
          "## Integridad", "",
          f"- Carga estricta: **{len(err_estricta)}** sentencias rechazadas; FK que se pudieron volver a crear: "
          f"**{len(fk_res) - len(fk_mal)} de {len(fk_res)}**"]
    if err_estricta:
        cnt = Counter((e["tipo"], e["tabla"]) for e in err_estricta)
        md += ["", tabla_md([{"tipo": t, "tabla": tb, "sentencias": n} for (t, tb), n in cnt.most_common()],
                            ["tipo", "tabla", "sentencias"])]
    if fk_mal:
        md += [""] + [f"- FK que falla: `{t}.{n}`: {e}" for t, n, _, e in fk_mal]
    md += ["", "Violaciones fila por fila (carga sin restricciones, `scripts/integridad.py`):", "",
           tabla_md([{"tipo": t, **d} for t, d in por_tipo.items()],
                    ["tipo", "restricciones", "violadas", "filas", "sin_comprobar"]), ""]
    violadas = [v for v in viol if v["estado"] == "violada"]
    if violadas:
        md += [tabla_md([{**v, "columnas": ", ".join(v["columnas"])} for v in violadas],
                        ["tipo", "tabla", "nombre", "columnas", "violaciones", "ejemplos"]), ""]
    md += [f"- Claves que MOSTLY generó sin fila padre (quedaron en -1): {sin_mapa or 'ninguna'}",
           f"- Pagos cuyo cliente no es el de su alquiler: {pago_otro_cliente} (customer_id se reconstruye "
           "desde rental, así que tiene que dar 0)",
           f"- Tiendas cuyo gerente trabaja en esa tienda: {gerente_de_su_tienda} (en Pagila real: 1 de 500)",
           f"- Rango de fechas: pagos {rangos[0]} a {rangos[1]}, alquileres {rangos[2]} a {rangos[3]} "
           "(particiones de payment: 2022-01 a 2026-07)", ""]
    if info.get("avisos") or avisos:
        md += ["## Avisos", ""] + [f"- {x}" for x in info.get("avisos", []) + avisos] + [""]
    md += ["Calidad y privacidad con la vara común: `pruebas/E3-chequeos-propios/resultados/d2_auditoria/`. "
           "Reportes HTML de MOSTLY en `salidas_grandes/reportes_mostly/` (no se suben: ~170 MB)."]
    (RESULTADOS / "d2_resumen.md").write_text("\n".join(md) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("exportar")
    e.add_argument("--base", default=BASE_ENTRENAMIENTO)
    t = sub.add_parser("entrenar")
    t.add_argument("--max-minutos", type=float, default=10, help="tope de entrenamiento por tabla (minutos)")
    t.add_argument("--conservar", action="store_true", help="no borrar el directorio local de MOSTLY")
    sub.add_parser("cargar")
    a = ap.parse_args()
    {"exportar": exportar, "entrenar": entrenar, "cargar": cargar}[a.cmd](a)


if __name__ == "__main__":
    main()
