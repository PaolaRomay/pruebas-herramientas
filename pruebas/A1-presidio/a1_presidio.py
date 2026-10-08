#!/usr/bin/env python3
"""Prueba A1: ¿puede Presidio detectar qué columnas de Pagila son sensibles?

Compara tres variantes contra la lista de referencia (data/columnas_sensibles_borrador.csv):
  manual           Presidio sobre cada valor de la columna, sin contexto.
  manual_contexto  Idem, pero cada valor lleva delante el nombre de la columna ("email: ...").
  structured:<estrategia>  presidio-structured, que asigna a cada columna una entidad. La estrategia
                   define cómo elige: most_common (la más frecuente), highest_confidence
                   (la de mayor score) o mixed.

Una columna se marca como sensible si Presidio detecta algo en al menos --min-fraccion de sus
valores (manual) o si presidio-structured le asigna una entidad. Se repite para varios umbrales
de score. Las columnas con verdad "dudoso" se muestran pero no entran en las métricas.

Uso (desde la raíz del repo, con el entorno activado y la base levantada):
    python pruebas/A1-presidio/a1_presidio.py
    python pruebas/A1-presidio/a1_presidio.py --n 50 --umbrales 0.4   # corrida rápida de prueba
"""
import argparse
import datetime
import platform
import sys
import time
from collections import Counter
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import pandas as pd
import sqlalchemy as sa
from presidio_analyzer import AnalyzerEngine, BatchAnalyzerEngine
from presidio_structured import PandasAnalysisBuilder

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
URL_DB = "postgresql+psycopg2://postgres:postgres@127.0.0.1:55432/pagila"

# Entidad que se espera de cada categoría del CSV (para medir si la etiqueta es la correcta,
# además de si la columna se marcó). Presidio no tiene una entidad "dirección postal":
# LOCATION es lo más cercano, y las demás categorías no tienen equivalente directo.
ESTRATEGIAS = ("most_common", "highest_confidence", "mixed")

ENTIDAD_ESPERADA = {
    "nombre": "PERSON",
    "apellido": "PERSON",
    "correo electronico": "EMAIL_ADDRESS",
    "telefono": "PHONE_NUMBER",
    "direccion": "LOCATION",
}


def leer_verdad(ruta):
    df = pd.read_csv(ruta, dtype=str).fillna("")
    df["sensible"] = df["sensible"].str.strip().str.lower()
    return df


def tipo_columna(conn, tabla, columna):
    q = sa.text("select data_type from information_schema.columns "
                "where table_schema='public' and table_name=:t and column_name=:c")
    return conn.execute(q, {"t": tabla, "c": columna}).scalar()


def citar(conn, nombre):
    return conn.dialect.identifier_preparer.quote(nombre)


def muestra_columna(conn, tabla, columna, n, semilla):
    """Hasta n valores no vacíos, elegidos de forma determinista (mismo resultado en cada corrida)."""
    t, c = citar(conn, tabla), citar(conn, columna)
    q = sa.text(f"select {c}::text from public.{t} where {c} is not null and {c}::text <> '' "
                f"order by md5({c}::text || :s) limit :n")
    return [r[0] for r in conn.execute(q, {"s": semilla, "n": n})]


def muestra_tabla(conn, tabla, columnas, n, semilla):
    """n filas de la tabla con las columnas indicadas, todo como texto."""
    t = citar(conn, tabla)
    cols = ", ".join(f"coalesce({citar(conn, c)}::text, '') as {citar(conn, c)}" for c in columnas)
    q = sa.text(f"select {cols} from public.{t} order by md5(ctid::text || :s) limit :n")
    return pd.DataFrame(conn.execute(q, {"s": semilla, "n": n}).fetchall(), columns=columnas)


def analizar_valores(batch, textos, idioma):
    """Una lista de [(entidad, score)] por texto, sin filtrar por umbral."""
    resultados = batch.analyze_iterator(textos, language=idioma, batch_size=32)
    return [[(r.entity_type, r.score) for r in rs] for rs in resultados]


def resumir_columna(detecciones, umbral):
    """Fracción de valores con alguna detección >= umbral y la entidad dominante."""
    if not detecciones:
        return 0.0, ""
    con, mejores = 0, Counter()
    for rs in detecciones:
        ok = [(e, s) for e, s in rs if s >= umbral]
        if ok:
            con += 1
            mejores[max(ok, key=lambda x: x[1])[0]] += 1
    dominante = mejores.most_common(1)[0][0] if mejores else ""
    return con / len(detecciones), dominante


def metricas(df):
    d = df[df["verdad"].isin(["si", "no"]) & df["evaluable"]]
    tp = int(((d.verdad == "si") & d.marcada).sum())
    fn = int(((d.verdad == "si") & ~d.marcada).sum())
    fp = int(((d.verdad == "no") & d.marcada).sum())
    tn = int(((d.verdad == "no") & ~d.marcada).sum())
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    return tp, fp, fn, tn, p, r, f1


def ver(paquete):
    try:
        return version(paquete)
    except PackageNotFoundError:
        return "no instalado"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", default=str(RAIZ / "data" / "columnas_sensibles_borrador.csv"))
    ap.add_argument("--n", type=int, default=200, help="valores por columna en las variantes manuales")
    ap.add_argument("--n-estructurado", type=int, default=100, help="filas por tabla en presidio-structured")
    ap.add_argument("--umbrales", default="0,0.4,0.6")
    ap.add_argument("--min-fraccion", type=float, default=0.5,
                    help="fracción de valores con detección para marcar la columna (variantes manuales)")
    ap.add_argument("--semilla", default="a1")
    ap.add_argument("--idioma", default="en")
    ap.add_argument("--salida", default=str(AQUI / "resultados"))
    args = ap.parse_args()
    umbrales = [float(x) for x in args.umbrales.split(",")]
    salida = Path(args.salida)
    salida.mkdir(parents=True, exist_ok=True)

    verdad = leer_verdad(args.csv)
    engine = sa.create_engine(URL_DB)
    analizador = AnalyzerEngine()
    batch = BatchAnalyzerEngine(analyzer_engine=analizador)

    filas, tiempos, avisos = [], {}, []
    muestras, evaluables = {}, {}
    with engine.connect() as conn:
        for _, f in verdad.iterrows():
            tabla, col = f["tabla"], f["columna"]
            tipo = tipo_columna(conn, tabla, col)
            if tipo is None:
                avisos.append(f"{tabla}.{col}: no existe en la base, se ignora")
                continue
            if tipo == "bytea":
                avisos.append(f"{tabla}.{col}: binaria (bytea), Presidio no la analiza; queda fuera de las métricas")
                evaluables[(tabla, col)] = False
                continue
            vals = muestra_columna(conn, tabla, col, args.n, args.semilla)
            if not vals:
                avisos.append(f"{tabla}.{col}: sin ningún valor no vacío en la base; no hay qué detectar, "
                              "queda fuera de las métricas")
                evaluables[(tabla, col)] = False
                continue
            evaluables[(tabla, col)] = True
            muestras[(tabla, col)] = vals
            if len(vals) < 10:
                avisos.append(f"{tabla}.{col}: solo {len(vals)} valores distintos no vacíos; resultado poco fiable")

        # Variantes manuales: se analiza una vez con umbral 0 y se filtra después por umbral
        for variante in ("manual", "manual_contexto"):
            t0 = time.time()
            print(f"[{variante}] analizando {len(muestras)} columnas...", flush=True)
            for (tabla, col), vals in muestras.items():
                textos = vals if variante == "manual" else [f"{col.replace('_', ' ')}: {v}" for v in vals]
                det = analizar_valores(batch, textos, args.idioma)
                for u in umbrales:
                    frac, ent = resumir_columna(det, u)
                    filas.append(dict(variante=variante, umbral=u, tabla=tabla, columna=col,
                                      fraccion=round(frac, 3), entidad=ent,
                                      marcada=frac >= args.min_fraccion, n_valores=len(vals)))
            tiempos[variante] = time.time() - t0

        # presidio-structured: un constructor por umbral. Ojo: si se le pasa un analizador ya
        # creado, ignora analyzer_score_threshold; hay que dejar que cree el suyo.
        t0 = time.time()
        print("[structured] analizando por tabla...", flush=True)
        por_tabla = {}
        for (tabla, col), ok in evaluables.items():
            if ok:
                por_tabla.setdefault(tabla, []).append(col)
        dfs = {t: muestra_tabla(conn, t, cols, args.n_estructurado, args.semilla) for t, cols in por_tabla.items()}
        for u in umbrales:
            b = PandasAnalysisBuilder(analyzer_score_threshold=u)
            for est in ESTRATEGIAS:
                for tabla, cols in por_tabla.items():
                    df = dfs[tabla]
                    try:
                        mapa = b.generate_analysis(df, n=args.n_estructurado, language=args.idioma,
                                                   selection_strategy=est).entity_mapping
                    except Exception as e:  # se registra y se sigue con el resto
                        avisos.append(f"structured:{est} {tabla} umbral {u}: {type(e).__name__}: {str(e)[:120]}")
                        mapa = {}
                    for col in cols:
                        filas.append(dict(variante=f"structured:{est}", umbral=u, tabla=tabla, columna=col,
                                          fraccion=float("nan"), entidad=mapa.get(col, ""),
                                          marcada=col in mapa, n_valores=len(df)))
        tiempos["structured"] = time.time() - t0

    res = pd.DataFrame(filas)
    info = verdad.rename(columns={"sensible": "verdad"})[["tabla", "columna", "verdad", "categoria"]]
    res = res.merge(info, on=["tabla", "columna"], how="left")
    res["evaluable"] = [evaluables.get((t, c), False) for t, c in zip(res.tabla, res.columna)]
    res["entidad_esperada"] = res["categoria"].map(ENTIDAD_ESPERADA).fillna("")
    res["etiqueta_ok"] = (res["verdad"] == "si") & res["marcada"] & (res["entidad_esperada"] != "") \
        & (res["entidad"] == res["entidad_esperada"])
    res.to_csv(salida / "a1_columnas.csv", index=False)

    # Resumen de métricas
    lineas = []
    for (v, u), g in res.groupby(["variante", "umbral"]):
        tp, fp, fn, tn, p, r, f1 = metricas(g)
        con_esperada = g[(g.verdad == "si") & (g.entidad_esperada != "") & g.evaluable]
        et = f"{int(con_esperada.etiqueta_ok.sum())}/{len(con_esperada)}"
        fn_l = ", ".join(f"{a}.{b}" for a, b in g[(g.verdad == "si") & ~g.marcada & g.evaluable][["tabla", "columna"]].values)
        fp_l = ", ".join(f"{a}.{b}" for a, b in g[(g.verdad == "no") & g.marcada & g.evaluable][["tabla", "columna"]].values)
        lineas.append((v, u, tp, fp, fn, tn, p, r, f1, et, fn_l, fp_l))

    n_si = int(((verdad.sensible == "si")).sum())
    n_no = int(((verdad.sensible == "no")).sum())
    n_du = int(((verdad.sensible == "dudoso")).sum())
    md = []
    md.append("# A1: Presidio, detección de columnas sensibles en Pagila\n")
    md.append(f"Corrida: {datetime.datetime.now():%Y-%m-%d %H:%M}\n")
    md.append("## Entorno\n")
    md.append(f"- Equipo: {platform.machine()}, macOS {platform.mac_ver()[0]}, Python {platform.python_version()}")
    md.append(f"- presidio-analyzer {ver('presidio-analyzer')}, presidio-structured {ver('presidio-structured')}, "
              f"spaCy {ver('spacy')}, modelo en_core_web_lg {ver('en-core-web-lg')}, pandas {ver('pandas')}")
    md.append(f"- Base: Pagila (pagila-v4.0.0) en PostgreSQL, puerto 55432")
    md.append(f"- Lista de referencia: `{Path(args.csv).name}` ({n_si} sensibles, {n_no} no sensibles, "
              f"{n_du} dudosas que no entran en las métricas)")
    md.append(f"- Parámetros: {args.n} valores por columna (manual), {args.n_estructurado} filas por tabla "
              f"(structured), marcar con ≥{args.min_fraccion:.0%} de valores detectados, idioma `{args.idioma}`, "
              f"semilla `{args.semilla}`")
    md.append("- Tiempo: " + ", ".join(f"{k} {v:.0f} s" for k, v in tiempos.items()) + "\n")
    md.append("## Resultados\n")
    md.append("TP = sensibles bien marcadas, FP = no sensibles marcadas, FN = sensibles no marcadas. "
              "«Etiqueta» = columnas sensibles con entidad esperada cuya entidad dominante coincide.\n")
    md.append("| Variante | Umbral | TP | FP | FN | TN | Precisión | Recall | F1 | Etiqueta |")
    md.append("|---|---|---|---|---|---|---|---|---|---|")
    for v, u, tp, fp, fn, tn, p, r, f1, et, _, _ in lineas:
        md.append(f"| {v} | {u} | {tp} | {fp} | {fn} | {tn} | {p:.2f} | {r:.2f} | {f1:.2f} | {et} |")
    md.append("\n## Qué falló en cada configuración\n")
    for v, u, *_, fn_l, fp_l in lineas:
        md.append(f"- **{v}, umbral {u}**. FN: {fn_l or '-'}. FP: {fp_l or '-'}")
    if avisos:
        md.append("\n## Avisos\n")
        md += [f"- {a}" for a in avisos]
    md.append("\nDetalle por columna en `a1_columnas.csv`. Falta completar a mano la ficha "
              "(esfuerzo, hallazgos y evidencia).")
    (salida / "a1_resumen.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    print(f"\nGuardado en {salida}")


if __name__ == "__main__":
    sys.exit(main())
