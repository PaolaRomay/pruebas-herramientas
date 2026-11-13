#!/usr/bin/env python3
"""A1m / A1s: Presidio sobre MIMIC-IV demo y Synthea, con la misma metodología que A1 (Pagila).

Variantes (iguales a A1):
  manual           Presidio sobre cada valor de la columna, sin contexto.
  manual_contexto  Ídem, con el nombre de la columna delante del valor.
  structured:<estrategia>  presidio-structured (most_common, highest_confidence, mixed).
Umbrales de score 0, 0,4 y 0,6. Una columna se marca si Presidio detecta algo en al menos --min-fraccion de sus
valores (manual) o si presidio-structured le asigna una entidad.

Diferencias con el script de A1 (pruebas/A1-presidio/a1_presidio.py, que no se toca):
  - analiza todas las columnas de la lista de referencia de la base (no solo 29);
  - la muestra de structured se ordena por md5 del contenido de la fila, no por ctid (observación de la validación de
    A1: ctid cambia si la base se reorganiza);
  - escribe el formato común de las pruebas A* (prueba, variante, corrida, tabla, columna, marcada, entidad);
  - no guarda valores de filas, solo entidades y fracciones.

Uso:
  .venv/bin/python pruebas/salud/A1-presidio/a1_presidio_salud.py --base mimic
  .venv/bin/python pruebas/salud/A1-presidio/a1_presidio_salud.py --base synthea
Salida: resultados/<base>/a1<m|s>_columnas.csv y a1<m|s>_corrida.md
"""
import argparse
import csv
import datetime
import platform
import time
from collections import Counter
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import pandas as pd
import sqlalchemy as sa
from presidio_analyzer import AnalyzerEngine, BatchAnalyzerEngine
from presidio_structured import PandasAnalysisBuilder

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[2]
BASES = {
    "mimic": dict(prueba="A1m", db="mimic_demo", referencia=RAIZ / "data" / "columnas_sensibles_mimic.csv"),
    "synthea": dict(prueba="A1s", db="synthea_p1000", referencia=RAIZ / "data" / "columnas_sensibles_synthea.csv"),
}
ESTRATEGIAS = ("most_common", "highest_confidence", "mixed")
NO_TEXTO = ("bytea",)


def ver(p):
    try:
        return version(p)
    except PackageNotFoundError:
        return "no instalado"


def muestra_columna(conn, esq, tabla, col, n, semilla):
    q = sa.text(f'select "{col}"::text from "{esq}"."{tabla}" where "{col}" is not null and "{col}"::text <> \'\' '
                f'order by md5("{col}"::text || :s) limit :n')
    return [r[0] for r in conn.execute(q, {"s": semilla, "n": n})]


def muestra_tabla(conn, esq, tabla, cols, n, semilla):
    sel = ", ".join(f'coalesce(t."{c}"::text, \'\') as "{c}"' for c in cols)
    q = sa.text(f'select {sel} from "{esq}"."{tabla}" t order by md5(t::text || :s) limit :n')
    return pd.DataFrame(conn.execute(q, {"s": semilla, "n": n}).fetchall(), columns=cols)


def resumir(detecciones, umbral):
    if not detecciones:
        return 0.0, ""
    con, mejores = 0, Counter()
    for rs in detecciones:
        ok = [(e, s) for e, s in rs if s >= umbral]
        if ok:
            con += 1
            mejores[max(ok, key=lambda x: x[1])[0]] += 1
    return con / len(detecciones), (mejores.most_common(1)[0][0] if mejores else "")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", choices=BASES, required=True)
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--n-estructurado", type=int, default=100)
    ap.add_argument("--umbrales", default="0,0.4,0.6")
    ap.add_argument("--min-fraccion", type=float, default=0.5)
    ap.add_argument("--semilla", default="a1")
    ap.add_argument("--idioma", default="en")
    a = ap.parse_args()
    cfg = BASES[a.base]
    umbrales = [float(x) for x in a.umbrales.split(",")]
    salida = AQUI / "resultados" / a.base
    salida.mkdir(parents=True, exist_ok=True)

    ref = list(csv.DictReader(open(cfg["referencia"], encoding="utf-8")))
    eng = sa.create_engine(f"postgresql+psycopg2://postgres:postgres@127.0.0.1:55432/{cfg['db']}")
    batch = BatchAnalyzerEngine(analyzer_engine=AnalyzerEngine())
    filas, tiempos, avisos, muestras = [], {}, [], {}

    t0 = time.time()
    with eng.connect() as conn:
        tipos = {(r[0], r[1], r[2]): r[3] for r in conn.execute(sa.text(
            "select table_schema, table_name, column_name, data_type from information_schema.columns"))}
        for r in ref:
            k = (r["esquema"], r["tabla"], r["columna"])
            if tipos.get(k) in NO_TEXTO:
                avisos.append(f"{r['tabla']}.{r['columna']}: binaria, no se analiza")
                continue
            vals = muestra_columna(conn, *k, a.n, a.semilla)
            if vals:
                muestras[k] = vals
        tiempos["muestreo"] = time.time() - t0
        print(f"[{a.base}] {len(muestras)} columnas con valores de {len(ref)}", flush=True)

        for variante in ("manual", "manual_contexto"):
            t0 = time.time()
            for (esq, tabla, col), vals in muestras.items():
                textos = vals if variante == "manual" else [f"{col.replace('_', ' ')}: {v}" for v in vals]
                det = [[(x.entity_type, x.score) for x in rs]
                       for rs in batch.analyze_iterator(textos, language=a.idioma, batch_size=64)]
                for u in umbrales:
                    frac, ent = resumir(det, u)
                    filas.append(dict(variante=f"{variante} umbral {u}", tabla=tabla, columna=col,
                                      marcada=frac >= a.min_fraccion, entidad=ent, fraccion=round(frac, 3),
                                      n_valores=len(vals)))
            tiempos[variante] = time.time() - t0
            print(f"[{a.base}] {variante}: {tiempos[variante]:.0f} s", flush=True)

        t0 = time.time()
        por_tabla = {}
        for (esq, tabla, col) in muestras:
            por_tabla.setdefault((esq, tabla), []).append(col)
        dfs = {k: muestra_tabla(conn, *k, cols, a.n_estructurado, a.semilla) for k, cols in por_tabla.items()}
        for u in umbrales:
            b = PandasAnalysisBuilder(analyzer_score_threshold=u)
            for est in ESTRATEGIAS:
                for (esq, tabla), cols in por_tabla.items():
                    try:
                        mapa = b.generate_analysis(dfs[(esq, tabla)], n=a.n_estructurado, language=a.idioma,
                                                   selection_strategy=est).entity_mapping
                    except Exception as e:
                        avisos.append(f"structured:{est} {tabla} umbral {u}: {type(e).__name__}: {str(e)[:120]}")
                        mapa = {}
                    for col in cols:
                        filas.append(dict(variante=f"structured:{est} umbral {u}", tabla=tabla, columna=col,
                                          marcada=col in mapa, entidad=mapa.get(col, ""), fraccion="",
                                          n_valores=len(dfs[(esq, tabla)])))
        tiempos["structured"] = time.time() - t0
        print(f"[{a.base}] structured: {tiempos['structured']:.0f} s", flush=True)

    df = pd.DataFrame(filas)
    df.insert(0, "corrida", 1)
    df.insert(0, "prueba", cfg["prueba"])
    nombre = cfg["prueba"].lower()
    df.to_csv(salida / f"{nombre}_columnas.csv", index=False)
    md = [f"# {cfg['prueba']}: Presidio sobre {cfg['db']}", "",
          f"- Corrida: {datetime.datetime.now():%Y-%m-%d %H:%M}",
          f"- Equipo: {platform.machine()}, macOS {platform.mac_ver()[0]}, Python {platform.python_version()}",
          f"- presidio-analyzer {ver('presidio-analyzer')}, presidio-structured {ver('presidio-structured')}, "
          f"spaCy {ver('spacy')}, en_core_web_lg {ver('en-core-web-lg')}",
          f"- Referencia: `{cfg['referencia'].relative_to(RAIZ)}`; columnas con valores: {len(muestras)} de {len(ref)}",
          f"- Parámetros: {a.n} valores por columna (manual), {a.n_estructurado} filas por tabla (structured), "
          f"marcar con ≥{a.min_fraccion:.0%}, umbrales {a.umbrales}, idioma `{a.idioma}`, semilla `{a.semilla}`",
          "- Tiempos: " + ", ".join(f"{k} {v:.0f} s" for k, v in tiempos.items())]
    if avisos:
        md += ["", "## Avisos", ""] + [f"- {x}" for x in avisos]
    (salida / f"{nombre}_corrida.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
