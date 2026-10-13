#!/usr/bin/env python3
"""Prueba E3: evaluador común de una base generada por cualquier herramienta (sintética,
anonimizada o subconjunto), medida siempre con la misma vara contra Pagila.

Tres bloques en una sola corrida:

  1. Integridad   scripts/integridad.py (PK, UNIQUE, FK, NOT NULL y CHECK de la base común) más dos
                  relaciones que ese script no ve porque no están declaradas donde las busca:
                  - las FK de payment, que en Pagila solo están declaradas en 6 de sus 55 particiones:
                    acá se chequean sobre la tabla padre, así cubren todas las filas (y siguen
                    sirviendo si la herramienta genera payment sin particionar);
                  - store.manager_staff_id -> staff, que no tiene FK en el catálogo (solo un índice único).
  2. Calidad      reporte de calidad y diagnóstico multi-tabla de SDMetrics (vía SDV), con la metadata
                  armada desde el catálogo de Pagila (claves y relaciones declaradas).
  3. Privacidad   Anonymeter (singling out, linkability, inference) y distancia al registro más cercano
                  (DCR) sobre el registro «persona» (customer + address + city + country), frente a un
                  conjunto de control de clientes que la herramienta no tiene que haber visto.

Subcomandos:
  preparar   crea la base de entrenamiento: copia de pagila sin los clientes de control (ni sus
             alquileres, pagos y direcciones). Las herramientas que aprenden de los datos (D2, D3, ...)
             se entrenan con ESA base; si no, el control no sirve y el riesgo sale subestimado.
  evaluar    evalúa una base candidata que ya está cargada en el contenedor.

Uso (desde la raíz del repo, con el entorno activado y la base levantada):
    python pruebas/E3-chequeos-propios/evaluar_bd.py preparar
    python pruebas/E3-chequeos-propios/evaluar_bd.py evaluar --candidata d2_sintetica --tipo sintetica \\
        --entrenada-con e3_entrenamiento
    python pruebas/E3-chequeos-propios/evaluar_bd.py evaluar --candidata b1_anon --tipo anonimizada \\
        --bloques integridad,privacidad

Para que la integridad cuente filas, la candidata tiene que estar cargada sin restricciones
(scripts/integridad.py, preparar_base(..., sin_restricciones=True)). Si las tiene puestas, la carga ya
rechazó lo que las violaba y los conteos dan 0; el resumen dice cuántas restricciones tiene declaradas.
Ojo: las dos relaciones agregadas no son restricciones de PostgreSQL, así que se violan sin error
aunque la candidata tenga todas las restricciones de Pagila.
"""
import argparse
import datetime
import hashlib
import os
import platform
import sys
import time
import warnings
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import numpy as np
import pandas as pd
import sqlalchemy as sa
from psycopg2 import sql

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import integridad as ig  # noqa: E402

BASE_ENTRENAMIENTO = "e3_entrenamiento"
PROTEGIDAS = {"pagila", "postgres", "template0", "template1"}
BLOQUES = ("integridad", "calidad", "privacidad")

# Relaciones lógicas de Pagila sin FK en el catálogo (verificado con pg_constraint).
NO_DECLARADAS = [("store", ["manager_staff_id"], "staff", ["staff_id"])]

# Calidad: tipos que SDMetrics no compara y columnas técnicas que solo agregan ruido.
TIPOS_EXCLUIDOS = {"tsvector", "ARRAY", "bytea"}
COLUMNAS_EXCLUIDAS = {"last_update"}

# Privacidad: el registro de una persona tal como lo vería un atacante.
PERSONA_SQL = """
    select c.customer_id, c.first_name, c.last_name, c.email, c.activebool, c.active, c.create_date,
           a.district, a.postal_code, a.phone, ci.city, co.country
    from public.customer c
    left join public.address a on a.address_id = c.address_id
    left join public.city ci on ci.city_id = a.city_id
    left join public.country co on co.country_id = ci.country_id"""
PERSONA_NUMERICAS = ["activebool", "active", "create_date"]   # create_date pasa a días
# Configuración de los ataques (elección propia, P): el atacante conoce la identidad (nombre, correo)
# y quiere la ubicación, o al revés.
LINK_AUX = (["first_name", "last_name", "email"], ["district", "postal_code", "phone", "city", "country"])
INFER_AUX = ["first_name", "last_name", "email", "create_date", "active"]
INFER_SECRETOS = ["district", "city", "country", "postal_code"]


# ----------------------------------------------------------------------------- utilidades

def url(base):
    """Misma conexión que scripts/integridad.py (variables PG*), para pandas vía SQLAlchemy."""
    e = os.environ.get
    return (f"postgresql+psycopg2://{e('PGUSER', 'postgres')}:{e('PGPASSWORD', 'postgres')}"
            f"@{e('PGHOST', '127.0.0.1')}:{e('PGPORT', '55432')}/{base}")


def ver(paquete):
    try:
        return version(paquete)
    except PackageNotFoundError:
        return "no instalado"


def tabla_md(filas, columnas):
    out = ["| " + " | ".join(columnas) + " |", "|" + "---|" * len(columnas)]
    out += ["| " + " | ".join(str(f.get(c, "")) for c in columnas) + " |" for f in filas]
    return "\n".join(out)


def r3(x):
    return "" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.3f}"


def ids_control(conn, fraccion, semilla):
    """Clientes de control: siempre los mismos para la misma semilla (orden por md5, como en A1)."""
    with conn.cursor() as cur:
        cur.execute("select count(*) from public.customer")
        k = round(cur.fetchone()[0] * fraccion)
        cur.execute("select customer_id from public.customer order by md5(customer_id::text || %s) limit %s",
                    (semilla, k))
        return sorted(r[0] for r in cur.fetchall())


def existe_base(nombre):
    with ig.conexion("postgres") as c, c.cursor() as cur:
        cur.execute("select 1 from pg_database where datname = %s", (nombre,))
        return cur.fetchone() is not None


# ----------------------------------------------------------------------------- preparar

def preparar(a):
    if a.base in PROTEGIDAS:
        sys.exit(f"No se puede usar {a.base} como base de entrenamiento.")
    with ig.conexion("pagila") as c:
        ctrl = ids_control(c, a.fraccion_control, a.semilla)
    with ig.conexion("postgres") as c, c.cursor() as cur:
        cur.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(a.base)))
        # Falla si hay otra conexión abierta a pagila (ver README).
        cur.execute(sql.SQL("CREATE DATABASE {} TEMPLATE pagila").format(sql.Identifier(a.base)))

    conn = ig.conectar(a.base)
    conn.autocommit = False
    borradas = {}
    with conn, conn.cursor() as cur:   # una sola transacción
        cur.execute("create temp table ctrl as select unnest(%s::int[]) as customer_id", (ctrl,))
        cur.execute("create temp table ctrl_rental as select rental_id from public.rental "
                    "where customer_id in (select customer_id from ctrl)")
        cur.execute("create temp table ctrl_dir as select address_id from public.customer "
                    "where customer_id in (select customer_id from ctrl)")
        # Pagos del cliente y también los de otro cliente que apuntan a un alquiler del control.
        cur.execute("delete from public.payment where customer_id in (select customer_id from ctrl) "
                    "or rental_id in (select rental_id from ctrl_rental)")
        borradas["payment"] = cur.rowcount
        cur.execute("delete from public.rental where rental_id in (select rental_id from ctrl_rental)")
        borradas["rental"] = cur.rowcount
        cur.execute("delete from public.customer where customer_id in (select customer_id from ctrl)")
        borradas["customer"] = cur.rowcount
        # La dirección se borra solo si nadie más la usa (en Pagila v4 staff y store comparten direcciones).
        cur.execute("""delete from public.address a where a.address_id in (select address_id from ctrl_dir)
                         and not exists (select 1 from public.customer c where c.address_id = a.address_id)
                         and not exists (select 1 from public.staff s where s.address_id = a.address_id)
                         and not exists (select 1 from public.store s where s.address_id = a.address_id)""")
        borradas["address"] = cur.rowcount
        cur.execute("select count(*) from ctrl_dir")
        n_dir = cur.fetchone()[0]
    conn.close()

    sal = Path(a.salida)
    sal.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"customer_id": ctrl}).to_csv(sal / "e3_control.csv", index=False)
    with ig.conexion(a.base) as c:
        restantes = ig.conteos(c)
    md = ["# E3: base de entrenamiento sin el conjunto de control", "",
          f"Corrida: {datetime.datetime.now():%Y-%m-%d %H:%M}", "",
          f"- Base creada: `{a.base}` (copia de `pagila` con CREATE DATABASE ... TEMPLATE).",
          f"- Control: {len(ctrl)} clientes ({a.fraccion_control:.0%}), orden por md5 con semilla "
          f"`{a.semilla}`. Lista en `e3_control.csv`.",
          "- Filas borradas: " + ", ".join(f"{t} {n}" for t, n in borradas.items()) + ".",
          f"- Direcciones de clientes de control que se conservan porque las usa staff o store: "
          f"{n_dir - borradas['address']} de {n_dir}. Esas direcciones siguen en los datos de entrenamiento "
          "(es una particularidad de Pagila v4; anotarlo al interpretar linkability e inference).", "",
          tabla_md([{"tabla": t, "filas": n} for t, n in restantes.items()], ["tabla", "filas"])]
    (sal / "e3_preparar.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


# ----------------------------------------------------------------------------- 1. integridad

def restricciones_extra(conn):
    """FK de las particiones llevadas a la tabla padre, y relaciones no declaradas."""
    with conn.cursor() as cur:
        cur.execute("""
            select par.relname,
                   array(select a.attname from unnest(con.conkey) with ordinality k(n, o)
                         join pg_attribute a on a.attrelid = con.conrelid and a.attnum = k.n order by k.o),
                   fr.relname,
                   array(select a.attname from unnest(con.confkey) with ordinality k(n, o)
                         join pg_attribute a on a.attrelid = con.confrelid and a.attnum = k.n order by k.o),
                   count(distinct rel.oid),
                   (select count(*) from pg_inherits i2 where i2.inhparent = par.oid)
            from pg_constraint con
            join pg_class rel on rel.oid = con.conrelid and rel.relispartition
            join pg_inherits i on i.inhrelid = rel.oid
            join pg_class par on par.oid = i.inhparent
            join pg_class fr on fr.oid = con.confrelid
            where con.connamespace = 'public'::regnamespace and con.contype = 'f'
            group by 1, 2, 3, 4, par.oid order by 1, 2""")
        filas = cur.fetchall()
        cur.execute("""select rel.relname, array(select a.attname from unnest(con.conkey) k(n)
                                                 join pg_attribute a on a.attrelid = con.conrelid and a.attnum = k.n)
                       from pg_constraint con join pg_class rel on rel.oid = con.conrelid
                       where con.connamespace = 'public'::regnamespace and con.contype = 'f'""")
        declaradas = {(t, tuple(c)) for t, c in cur.fetchall()}
    extra = []
    for padre, cols, ref, rcols, con_fk, total in filas:
        extra.append({"tipo": "FK", "tabla": padre, "columnas": list(cols), "ref_tabla": ref,
                      "ref_columnas": list(rcols),
                      "nombre": f"{padre}.{','.join(cols)} -> {ref} (en la tabla padre)",
                      "definicion": f"FOREIGN KEY ({', '.join(cols)}) REFERENCES {ref}({', '.join(rcols)})",
                      "origen": f"declarada en {con_fk} de {total} particiones"})
    for tabla, cols, ref, rcols in NO_DECLARADAS:
        if (tabla, tuple(cols)) in declaradas:
            continue   # si algún día se declara, ya la chequea integridad.py
        extra.append({"tipo": "FK", "tabla": tabla, "columnas": cols, "ref_tabla": ref, "ref_columnas": rcols,
                      "nombre": f"{tabla}.{','.join(cols)} -> {ref}",
                      "definicion": f"(lógica) {tabla}({', '.join(cols)}) -> {ref}({', '.join(rcols)})",
                      "origen": "no declarada en el catálogo"})
    return extra


def clave(r):
    return (r["tipo"], r["tabla"], tuple(r["columnas"]), r.get("ref_tabla"))


def bloque_integridad(a, restr, extra, sal):
    with ig.conexion(a.candidata) as c:
        res = ig.contar_violaciones(c, restr + extra)
        conteo = ig.conteos(c)
        en_candidata = {clave(r) for r in ig.restricciones(c)}
    for r in res:
        r.setdefault("origen", "catálogo")
    ig.guardar_csv(sal / "e3_integridad.csv", res, ig.CAMPOS_RESTRICCIONES + ["origen"])

    catalogo = [r for r in res if r["origen"] == "catálogo"]
    agregadas = [r for r in res if r["origen"] != "catálogo"]
    declaradas = sum(clave(r) in en_candidata for r in restr)
    md = ["## 1. Integridad", "",
          f"Restricciones de Pagila declaradas en la candidata: **{declaradas} de {len(restr)}** "
          "(si están todas, la carga ya rechazó lo que las violaba).", "",
          "Restricciones del catálogo (`scripts/integridad.py`):", "",
          tabla_md([{"tipo": t, **d} for t, d in ig.resumen_por_tipo(catalogo).items()],
                   ["tipo", "restricciones", "violadas", "filas", "sin_comprobar"]), "",
          "Relaciones que el catálogo no cubre (agregadas por E3):", "",
          tabla_md(agregadas, ["nombre", "origen", "estado", "violaciones", "ejemplos"]), ""]
    violadas = [r for r in catalogo if r["estado"] == "violada"]
    if violadas:
        md += ["Restricciones del catálogo violadas:", "",
               tabla_md([{**v, "columnas": ", ".join(v["columnas"])} for v in violadas],
                        ["tipo", "tabla", "nombre", "columnas", "violaciones", "ejemplos"]), ""]
    otras = [r for r in res if r["estado"] not in ("ok", "violada")]
    if otras:
        md += ["Sin comprobar: " + ", ".join(f"`{r['nombre']}` ({r['estado']})" for r in otras), ""]
    total = {"violadas": sum(r["estado"] == "violada" for r in res),
             "filas": sum(r["violaciones"] or 0 for r in res if r["estado"] == "violada")}
    return md, conteo, total


# ----------------------------------------------------------------------------- 2. calidad

def columnas_info(conn, tabla):
    q = sa.text("select column_name, data_type from information_schema.columns "
                "where table_schema = 'public' and table_name = :t order by ordinal_position")
    return list(conn.execute(q, {"t": tabla}).fetchall())


def leer_tabla(conn, tabla, cols):
    """cols: [(nombre, data_type)]. Enums y uuid se leen como texto; fechas sin zona; todo número a float
    (una FK toda NULL, como film.original_language_id, llega como float y SDV exige el mismo tipo que la PK)."""
    prep = conn.dialect.identifier_preparer
    sel = ", ".join(f"{prep.quote(c)}::text as {prep.quote(c)}" if t in ("USER-DEFINED", "uuid")
                    else prep.quote(c) for c, t in cols)
    df = pd.read_sql(sa.text(f"select {sel} from public.{prep.quote(tabla)}"), conn)
    for c, t in cols:
        if t.startswith(("timestamp", "date")):
            df[c] = pd.to_datetime(df[c], utc=True, errors="coerce").dt.tz_localize(None)
        elif t in ("numeric", "real", "double precision", "smallint", "integer", "bigint"):
            df[c] = pd.to_numeric(df[c], errors="coerce").astype(float)
    return df


def armar_metadata(tablas, cols_tipo, datos_ref, restr, extra):
    pk = {}
    for r in restr:
        if r["tipo"] == "PK" and r["tabla"] in tablas:
            cs = [c for c in r["columnas"] if c in cols_tipo[r["tabla"]]]
            # PK compuesta (payment: payment_date + payment_id): SDV solo admite una columna;
            # se usa la que ya es única en los datos de referencia.
            unicas = [c for c in cs if datos_ref[r["tabla"]][c].is_unique
                      and not cols_tipo[r["tabla"]][c].startswith(("timestamp", "date"))]
            if len(cs) == 1 or unicas:
                pk[r["tabla"]] = cs[0] if len(cs) == 1 else unicas[0]
    fks = [r for r in restr + extra if r["tipo"] == "FK" and r.get("origen") != "no declarada en el catálogo"
           and r["tabla"] in tablas and r["ref_tabla"] in tablas and len(r["columnas"]) == 1]
    ids = {(t, c) for t, c in pk.items()} | {(r["tabla"], r["columnas"][0]) for r in fks}

    tablas_md = {}
    for t in tablas:
        cols = {}
        n = len(datos_ref[t])
        for c, tipo in cols_tipo[t].items():
            if (t, c) in ids or tipo == "uuid":
                st = "id"
            elif tipo == "boolean":
                st = "boolean"
            elif tipo.startswith(("timestamp", "date")):
                st = "datetime"
            elif tipo in ("numeric", "real", "double precision", "smallint", "integer", "bigint"):
                st = "numerical"
            else:   # texto y enums: categórica si tiene pocos valores distintos; si no, no se compara
                st = "categorical" if datos_ref[t][c].nunique() <= max(30, 0.05 * n) else "unknown"
            cols[c] = {"sdtype": st}
        tablas_md[t] = {"columns": cols, **({"primary_key": pk[t]} if t in pk else {})}
    rel = []
    for r in fks:
        padre, hija, col = r["ref_tabla"], r["tabla"], r["columnas"][0]
        if pk.get(padre) == r["ref_columnas"][0] and padre != hija:
            rel.append({"parent_table_name": padre, "parent_primary_key": pk[padre],
                        "child_table_name": hija, "child_foreign_key": col})
    # sin duplicados y en orden fijo (un set de texto cambia de orden entre ejecuciones de Python)
    rel = [dict(t) for t in sorted({tuple(sorted(x.items())) for x in rel})]
    return {"METADATA_SPEC_VERSION": "V1", "tables": tablas_md, "relationships": rel}


def bloque_calidad(a, restr, extra, sal, avisos):
    from sdv.evaluation.multi_table import evaluate_quality, run_diagnostic
    from sdv.metadata import Metadata

    ref_eng, cand_eng = sa.create_engine(url(a.referencia_datos)), sa.create_engine(url(a.candidata))
    excluidas = []
    with ref_eng.connect() as rc, cand_eng.connect() as cc:
        with ig.conexion(a.referencia_datos) as c:
            tablas = [t for t in ig.tablas_base(c) if not a.tablas or t in a.tablas]
        cols_tipo, real, sint = {}, {}, {}
        for t in tablas:
            cr = {c: tp for c, tp in columnas_info(rc, t)}
            cc_ = {c: tp for c, tp in columnas_info(cc, t)}
            if not cc_:
                avisos.append(f"calidad: la tabla {t} no está en la candidata; queda fuera")
                continue
            usar = {}
            for c, tp in cr.items():
                if tp in TIPOS_EXCLUIDOS or c in COLUMNAS_EXCLUIDAS:
                    excluidas.append(f"{t}.{c}")
                elif c not in cc_:
                    avisos.append(f"calidad: falta la columna {t}.{c} en la candidata; queda fuera")
                else:
                    usar[c] = tp
            cols_tipo[t] = usar
            real[t] = leer_tabla(rc, t, list(usar.items()))
            sint[t] = leer_tabla(cc, t, list(usar.items()))
    tablas = list(real)
    meta = armar_metadata(tablas, cols_tipo, real, restr, extra)
    md_sdv = Metadata.load_from_dict(meta)
    md_sdv.validate()

    t0 = time.time()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        q = evaluate_quality(real, sint, md_sdv, verbose=False)
        d = run_diagnostic(real, sint, md_sdv, verbose=False)
    seg = time.time() - t0

    props = pd.concat([q.get_properties().assign(reporte="calidad"),
                       d.get_properties().assign(reporte="diagnóstico")])
    props.to_csv(sal / "e3_calidad_propiedades.csv", index=False)
    detalles = []
    for rep, nombre in ((q, "calidad"), (d, "diagnóstico")):
        for p in rep.get_properties()["Property"]:
            try:
                detalles.append(rep.get_details(p).assign(reporte=nombre, propiedad=p))
            except Exception as e:   # alguna propiedad no tiene detalle por tabla
                avisos.append(f"calidad: sin detalle de {p}: {type(e).__name__}")
    if detalles:
        pd.concat(detalles, ignore_index=True).to_csv(sal / "e3_calidad_detalle.csv", index=False)
    cols_por_sdtype = pd.Series([c["sdtype"] for t in meta["tables"].values() for c in t["columns"].values()])

    peores = q.get_details("Column Shapes").sort_values("Score").head(8)
    md = ["## 2. Calidad (SDMetrics)", "",
          f"Datos reales de comparación: `{a.referencia_datos}`. Tablas: {len(tablas)}. "
          f"Relaciones en la metadata: {len(meta['relationships'])}. Tiempo: {seg:.0f} s.", "",
          f"**Calidad: {q.get_score():.3f}**, **diagnóstico: {d.get_score():.3f}** (0 a 1; 1 = igual a los datos reales).", "",
          tabla_md([{"reporte": r.reporte, "propiedad": r.Property, "score": r3(r.Score)} for r in props.itertuples()],
                   ["reporte", "propiedad", "score"]), "",
          "Columnas por tipo en la metadata: " + ", ".join(f"{k} {v}" for k, v in cols_por_sdtype.value_counts().items())
          + ". Las `unknown` (texto con muchos valores distintos: nombres, correos, direcciones) y las `id` no "
            "entran en Column Shapes.", "",
          "Columnas con peor forma (Column Shapes):", "",
          tabla_md([{"tabla": r.Table, "columna": r.Column, "métrica": r.Metric, "score": r3(r.Score)}
                    for r in peores.itertuples()], ["tabla", "columna", "métrica", "score"]), "",
          f"Excluidas de la comparación (tipo no soportado o columna técnica): {', '.join(excluidas) or '-'}.", ""]
    return md, {"calidad": q.get_score(), "diagnostico": d.get_score()}


# ----------------------------------------------------------------------------- 3. privacidad

def leer_persona(base):
    with sa.create_engine(url(base)).connect() as c:
        df = pd.read_sql(sa.text(PERSONA_SQL), c)
    df["create_date"] = (pd.to_datetime(df["create_date"], errors="coerce")
                         - pd.Timestamp("1970-01-01")).dt.days.astype(float)
    df["activebool"] = df["activebool"].astype(float)
    df["active"] = pd.to_numeric(df["active"], errors="coerce").astype(float)
    for c in df.columns:
        if c not in PERSONA_NUMERICAS and c != "customer_id":
            df[c] = df[c].astype(object).where(df[c].notna(), "<nulo>").astype(str)
    return df


def gower_min(A, B, num, cat, rangos, bloque=400):
    """Distancia de Gower de cada fila de A a la fila más cercana de B (0 = copia exacta, 1 = nada igual)."""
    An, Bn = A[num].to_numpy(float), B[num].to_numpy(float)
    Ac, Bc = A[cat].to_numpy(str), B[cat].to_numpy(str)
    out = np.empty(len(A))
    for i in range(0, len(A), bloque):
        j = slice(i, min(i + bloque, len(A)))
        d = np.zeros((j.stop - i, len(B)))
        for k in range(len(num)):
            d += np.nan_to_num(np.abs(An[j, k, None] - Bn[None, :, k]) / rangos[k], nan=1.0)
        for k in range(len(cat)):
            d += Ac[j, k, None] != Bc[None, :, k]
        out[j] = d.min(axis=1) / (len(num) + len(cat))
    return out


def correr_anonymeter(ori, syn, control, n_ataques, semilla, avisos):
    from anonymeter.evaluators import InferenceEvaluator, LinkabilityEvaluator, SinglingOutEvaluator
    n = min(n_ataques, len(control), len(ori), len(syn))
    pruebas = [("singling out", "univariado",
                lambda: SinglingOutEvaluator(ori=ori, syn=syn, control=control, n_attacks=n, seed=semilla)
                .evaluate(mode="univariate")),
               ("singling out", "multivariado (3 columnas)",
                lambda: SinglingOutEvaluator(ori=ori, syn=syn, control=control, n_attacks=n, n_cols=3, seed=semilla)
                .evaluate(mode="multivariate")),
               ("linkability", f"{'+'.join(LINK_AUX[0])} | {'+'.join(LINK_AUX[1])}",
                lambda: LinkabilityEvaluator(ori=ori, syn=syn, control=control, aux_cols=LINK_AUX, n_attacks=n)
                .evaluate(n_jobs=1))]
    for s in INFER_SECRETOS:
        pruebas.append(("inference", f"secreto {s}",
                        lambda s=s: InferenceEvaluator(ori=ori, syn=syn, control=control, aux_cols=INFER_AUX,
                                                       secret=s, n_attacks=n).evaluate(n_jobs=1)))
    filas = []
    for ataque, detalle, correr in pruebas:
        t0 = time.time()
        try:
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                ev = correr()
                riesgo, res = ev.risk(), ev.results()
            nota = "el ataque no supera al azar: no concluyente" \
                if res.attack_rate.value <= res.baseline_rate.value else ""
            if any("Attack is as good or worse" in str(x.message) for x in w) and not nota:
                nota = "Anonymeter avisa: ataque no mejor que el azar"
            filas.append({"ataque": ataque, "detalle": detalle, "n_ataques": n, "riesgo": r3(riesgo.value),
                          "ic95": f"{riesgo.ci[0]:.3f}–{riesgo.ci[1]:.3f}",
                          "tasa_ataque": r3(res.attack_rate.value), "tasa_azar": r3(res.baseline_rate.value),
                          "tasa_control": r3(res.control_rate.value), "segundos": f"{time.time() - t0:.0f}",
                          "nota": nota})
        except Exception as e:   # se registra y se sigue con el resto, como en A1
            avisos.append(f"anonymeter {ataque} ({detalle}): {type(e).__name__}: {str(e)[:150]}")
            filas.append({"ataque": ataque, "detalle": detalle, "n_ataques": n, "nota": f"falló: {type(e).__name__}"})
    return filas


def bloque_privacidad(a, ctrl, sal, avisos):
    ref = leer_persona("pagila")
    cand = leer_persona(a.candidata)
    es_ctrl = ref["customer_id"].isin(ctrl)
    ori, control = ref[~es_ctrl], ref[es_ctrl]
    if a.tipo == "anonimizada":
        # Anonimizada = mismas filas que la original. Se sacan las de control para que el control siga
        # siendo gente «no publicada» (supone que la herramienta conserva customer_id).
        en_cand = cand["customer_id"].isin(ctrl)
        if not en_cand.any():
            avisos.append("privacidad: ningún customer_id de control aparece en la candidata; si la herramienta "
                          "cambió las claves, el control no se pudo separar y el riesgo puede estar subestimado")
        cand = cand[~en_cand]
    elif a.entrenada_con:
        with ig.conexion(a.entrenada_con) as c, c.cursor() as cur:
            cur.execute("select count(*) from public.customer where customer_id = any(%s)", (ctrl,))
            if cur.fetchone()[0]:
                avisos.append(f"privacidad: `{a.entrenada_con}` contiene clientes de control: el control no es "
                              "independiente y el riesgo sale subestimado")
    else:
        avisos.append("privacidad: no se indicó --entrenada-con. Si la herramienta se entrenó con `pagila` "
                      "completa, vio el control y el riesgo sale subestimado")
    atrib = [c for c in ref.columns if c != "customer_id"]
    ori, control, syn = (x[atrib].reset_index(drop=True) for x in (ori, control, cand))

    semilla = int(hashlib.md5(a.semilla.encode()).hexdigest()[:8], 16)
    filas = correr_anonymeter(ori, syn, control, a.n_ataques, semilla, avisos)
    pd.DataFrame(filas).to_csv(sal / "e3_privacidad.csv", index=False)

    # DCR: distancia al registro más cercano, con el control como vara de lo «normal»
    num = [c for c in atrib if c in PERSONA_NUMERICAS]
    cat = [c for c in atrib if c not in PERSONA_NUMERICAS]
    rangos = [(ori[c].max() - ori[c].min()) or 1.0 for c in num]
    d_syn = gower_min(syn, ori, num, cat, rangos)
    d_ctrl = gower_min(control, ori, num, cat, rangos)
    sub = ori.sample(n=min(len(control), len(ori)), random_state=semilla % 2**32)
    dt, dh = gower_min(syn, sub, num, cat, rangos), gower_min(syn, control, num, cat, rangos)
    cuota = float(np.mean(dt < dh) + 0.5 * np.mean(dt == dh))
    # Si la candidata copiara todo el entrenamiento, solo las filas que caen en la submuestra (len(sub) de
    # len(ori)) ganarían seguro; el resto empata en promedio. Ese es el máximo posible de la cuota.
    cuota_max = 0.5 + 0.5 * len(sub) / len(ori)
    indice = (cuota - 0.5) / (cuota_max - 0.5) if cuota_max > 0.5 else float("nan")
    dcr = {"copias_exactas": float(np.mean(d_syn == 0)), "dcr_mediana_candidata": float(np.median(d_syn)),
           "dcr_p5_candidata": float(np.percentile(d_syn, 5)), "dcr_mediana_control": float(np.median(d_ctrl)),
           "cuota_mas_cerca_entrenamiento": cuota, "cuota_maxima": cuota_max, "indice_memorizacion": indice}
    pd.DataFrame([dcr]).to_csv(sal / "e3_dcr.csv", index=False)

    md = ["## 3. Privacidad", "",
          f"Registro «persona» (customer + address + city + country, {len(atrib)} atributos). "
          f"Original sin control: {len(ori)} filas; control: {len(control)}; candidata: {len(syn)}.", "",
          "**Anonymeter.** Riesgo = cuánto mejor le va al ataque contra los datos originales que contra el "
          "control (0 = nada, 1 = total). «Tasa azar» es un ataque que adivina sin mirar la candidata.", "",
          tabla_md(filas, ["ataque", "detalle", "n_ataques", "riesgo", "ic95", "tasa_ataque", "tasa_azar",
                           "tasa_control", "nota"]), "",
          "**Distancia al registro más cercano (Gower, 0 = copia exacta).**", "",
          f"- Filas de la candidata que son copia exacta de una persona real: **{dcr['copias_exactas']:.1%}**",
          f"- Mediana de la distancia candidata → original: {dcr['dcr_mediana_candidata']:.3f} (percentil 5: "
          f"{dcr['dcr_p5_candidata']:.3f}); control → original, como referencia: {dcr['dcr_mediana_control']:.3f}",
          f"- Cuota de filas más cerca del entrenamiento que del control (submuestra de {len(sub)}, mismo tamaño "
          f"que el control): {cuota:.3f}. Va de 0,50 (no memoriza) a {cuota_max:.3f} (copia todo el entrenamiento). "
          f"**Índice de memorización: {indice:.2f}** (0 = no memoriza, 1 = copia todo; negativo = más lejos que el "
          "control)", ""]
    return md, dcr


# ----------------------------------------------------------------------------- evaluar

def evaluar(a):
    if not existe_base(a.candidata):
        sys.exit(f"No existe la base {a.candidata} en el contenedor.")
    bloques = [b.strip() for b in a.bloques.split(",") if b.strip()]
    if set(bloques) - set(BLOQUES):
        sys.exit(f"Bloques válidos: {', '.join(BLOQUES)}")
    a.tablas = [t.strip() for t in a.tablas.split(",")] if a.tablas else []
    a.referencia_datos = a.referencia_datos or a.entrenada_con or "pagila"
    sal = Path(a.salida) / a.candidata
    sal.mkdir(parents=True, exist_ok=True)

    with ig.conexion("pagila") as ref:
        restr = ig.restricciones(ref)
        extra = restricciones_extra(ref)
        conteo_ref = ig.conteos(ref)
        ctrl = ids_control(ref, a.fraccion_control, a.semilla)
        with ref.cursor() as cur:
            cur.execute("show server_version")
            version_pg = cur.fetchone()[0]

    avisos, cuerpo, tiempos, resumen = [], [], {}, {}
    conteo = None
    for b in bloques:
        print(f"[{b}] ...", flush=True)
        t0 = time.time()
        try:
            if b == "integridad":
                md, conteo, resumen["integridad"] = bloque_integridad(a, restr, extra, sal)
            elif b == "calidad":
                md, resumen["calidad"] = bloque_calidad(a, restr, extra, sal, avisos)
            else:
                md, resumen["privacidad"] = bloque_privacidad(a, ctrl, sal, avisos)
        except Exception as e:   # un bloque roto no tira abajo a los otros
            md = [f"## {b.capitalize()}", "", f"**Falló:** `{type(e).__name__}: {str(e)[:300]}`", ""]
            avisos.append(f"{b}: {type(e).__name__}: {str(e)[:300]}")
        tiempos[b] = time.time() - t0
        cuerpo += md

    if conteo is None:
        with ig.conexion(a.candidata) as c:
            conteo = ig.conteos(c)
    filas_conteo = [{"tabla": t, "pagila": conteo_ref.get(t, ""), "candidata": conteo.get(t, "")}
                    for t in sorted(set(conteo_ref) | set(conteo))]
    ig.guardar_csv(sal / "e3_conteos.csv", filas_conteo, ["tabla", "pagila", "candidata"])

    md = [f"# E3: evaluación de `{a.candidata}` ({a.tipo})", "",
          f"Corrida: {datetime.datetime.now():%Y-%m-%d %H:%M}", "",
          "## Entorno", "",
          f"- Equipo: {platform.machine()}, macOS {platform.mac_ver()[0]}, Python {platform.python_version()}",
          f"- PostgreSQL {version_pg} (contenedor `pagila-db`). Restricciones: base común `pagila` (pagila-v4.0.0)",
          f"- sdv {ver('sdv')}, sdmetrics {ver('sdmetrics')}, anonymeter {ver('anonymeter')}, "
          f"pandas {ver('pandas')}, numpy {ver('numpy')}",
          f"- Candidata: `{a.candidata}`, tipo `{a.tipo}`"
          + (f", entrenada con `{a.entrenada_con}`" if a.entrenada_con else ""),
          f"- Control: {len(ctrl)} clientes ({a.fraccion_control:.0%}), semilla `{a.semilla}`; "
          f"ataques de Anonymeter: hasta {a.n_ataques}",
          "- Tiempo: " + ", ".join(f"{k} {v:.0f} s" for k, v in tiempos.items()), ""]
    md += cuerpo
    md += ["## Filas por tabla", "", tabla_md(filas_conteo, ["tabla", "pagila", "candidata"]), ""]
    if avisos:
        md += ["## Avisos", ""] + [f"- {x}" for x in avisos] + [""]
    md += ["Detalle en los CSV de esta carpeta (`e3_integridad.csv`, `e3_calidad_*.csv`, `e3_privacidad.csv`, "
           "`e3_dcr.csv`, `e3_conteos.csv`)."]
    (sal / "e3_resumen.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    print(f"\nGuardado en {sal}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    comunes = argparse.ArgumentParser(add_help=False)
    comunes.add_argument("--fraccion-control", type=float, default=0.2)
    comunes.add_argument("--semilla", default="e3")
    comunes.add_argument("--salida", default=str(AQUI / "resultados"))

    p = sub.add_parser("preparar", parents=[comunes], help="crear la base de entrenamiento sin el control")
    p.add_argument("--base", default=BASE_ENTRENAMIENTO)

    e = sub.add_parser("evaluar", parents=[comunes], help="evaluar una base candidata")
    e.add_argument("--candidata", required=True, help="base del contenedor a evaluar")
    e.add_argument("--tipo", required=True, choices=["sintetica", "anonimizada", "subconjunto"])
    e.add_argument("--entrenada-con", help="base con la que se entrenó la herramienta (p. ej. e3_entrenamiento)")
    e.add_argument("--referencia-datos", help="base real para comparar la calidad "
                                              "(por defecto --entrenada-con, o pagila)")
    e.add_argument("--bloques", default=",".join(BLOQUES))
    e.add_argument("--tablas", default="", help="limitar la calidad a estas tablas (separadas por coma)")
    e.add_argument("--n-ataques", type=int, default=500)
    a = ap.parse_args()
    preparar(a) if a.cmd == "preparar" else evaluar(a)


if __name__ == "__main__":
    sys.exit(main())
