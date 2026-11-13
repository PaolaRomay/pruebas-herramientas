#!/usr/bin/env python3
"""A4m / A4s: GLiNER2-PII sobre MIMIC-IV demo y Synthea, con la metodología de la variante manual de A1.

GLiNER2 es un modelo de extracción de entidades «a pedido»: se le pasa la lista de etiquetas a buscar (en lenguaje
natural) y devuelve los fragmentos de texto que corresponden a cada una, con su confianza. Se usa el checkpoint
fastino/gliner2-privacy-filter-PII-multi (ajustado para datos personales, multilingüe).

Variantes (etiquetas × contexto × umbral):
  pii           solo etiquetas de datos personales (nombre, fecha, dirección, SSN, teléfono…).
  pii_salud     las anteriores + salud y demográficos (condición médica, medicamento, procedimiento, sexo…):
                lo que Presidio no puede buscar porque no tiene reconocedores para eso.
  _contexto     el valor va precedido por el nombre de la columna («gender: F»), como manual_contexto en A1.
Umbrales de confianza 0,3, 0,5 y 0,7 (se calcula una vez con 0,3 y se filtra). Una columna se marca si GLiNER2 detecta
algo en al menos --min-fraccion de sus valores; la entidad es la más frecuente.

Muestra: la misma que A1 (orden md5 del valor con semilla `a1`), los primeros --n valores (100: la mitad que A1, por
tiempo). No guarda valores de filas.

Uso:  .venv/bin/python pruebas/salud/A4-gliner2/a4_gliner2_salud.py --base mimic   (o synthea)
Salida: resultados/<base>/a4<m|s>_columnas.csv y a4<m|s>_corrida.md
"""
import argparse
import csv
import datetime
import platform
import time
from collections import Counter
from importlib.metadata import version
from pathlib import Path

import pandas as pd
import sqlalchemy as sa
import torch
from gliner2 import GLiNER2

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[2]
BASES = {
    "mimic": dict(prueba="A4m", db="mimic_demo", referencia=RAIZ / "data" / "columnas_sensibles_mimic.csv"),
    "synthea": dict(prueba="A4s", db="synthea_p1000", referencia=RAIZ / "data" / "columnas_sensibles_synthea.csv"),
}
MODELO = "fastino/gliner2-privacy-filter-PII-multi"
# etiqueta para GLiNER2 -> entidad en el formato común (compatible con los prefijos de comparar_salud.py)
PII = {"person name": "PERSON", "date": "DATE_TIME", "location": "LOCATION", "street address": "LOCATION",
       "social security number": "US_SSN", "driver license number": "US_DRIVER_LICENSE",
       "passport number": "US_PASSPORT", "phone number": "PHONE_NUMBER", "email address": "EMAIL_ADDRESS",
       "identification number": "ID_NUMBER", "financial amount": "FINANCIAL"}
SALUD = {"medical condition": "MEDICAL_CONDITION", "medication": "MEDICATION", "medical procedure": "MEDICAL_PROCEDURE",
         "lab test": "LAB_TEST", "gender": "GENDER", "ethnicity": "ETHNICITY", "marital status": "MARITAL_STATUS",
         "language": "LANGUAGE", "health insurance": "INSURANCE"}
CONJUNTOS = {"pii": PII, "pii_salud": {**PII, **SALUD}}
UMBRAL_BASE = 0.3


def muestra_columna(conn, esq, tabla, col, n, semilla):
    q = sa.text(f'select "{col}"::text from "{esq}"."{tabla}" where "{col}" is not null and "{col}"::text <> \'\' '
                f'order by md5("{col}"::text || :s) limit :n')
    return [r[0][:300] for r in conn.execute(q, {"s": semilla, "n": n})]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", choices=BASES, required=True)
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--umbrales", default="0.3,0.5,0.7")
    ap.add_argument("--min-fraccion", type=float, default=0.5)
    ap.add_argument("--semilla", default="a1")
    ap.add_argument("--lote", type=int, default=32)
    a = ap.parse_args()
    cfg = BASES[a.base]
    umbrales = [float(x) for x in a.umbrales.split(",")]
    salida = AQUI / "resultados" / a.base
    salida.mkdir(parents=True, exist_ok=True)
    disp = "mps" if torch.backends.mps.is_available() else "cpu"
    modelo = GLiNER2.from_pretrained(MODELO)
    modelo.to(disp)

    ref = list(csv.DictReader(open(cfg["referencia"], encoding="utf-8")))
    eng = sa.create_engine(f"postgresql+psycopg2://postgres:postgres@127.0.0.1:55432/{cfg['db']}")
    muestras, avisos, tiempos = {}, [], {}
    t0 = time.time()
    with eng.connect() as conn:
        tipos = {(r[0], r[1], r[2]): r[3] for r in conn.execute(sa.text(
            "select table_schema, table_name, column_name, data_type from information_schema.columns"))}
        for r in ref:
            k = (r["esquema"], r["tabla"], r["columna"])
            if tipos.get(k) == "bytea":
                avisos.append(f"{r['tabla']}.{r['columna']}: binaria, no se analiza")
                continue
            vals = muestra_columna(conn, *k, a.n, a.semilla)
            if vals:
                muestras[k] = vals
    tiempos["muestreo"] = time.time() - t0
    print(f"[{a.base}] {len(muestras)} columnas con valores de {len(ref)}, dispositivo {disp}", flush=True)

    filas = []
    for conj, etiquetas in CONJUNTOS.items():
        for ctx in (False, True):
            variante = conj + ("_contexto" if ctx else "")
            t0 = time.time()
            for (esq, tabla, col), vals in muestras.items():
                textos = [f"{col.replace('_', ' ')}: {v}" for v in vals] if ctx else vals
                res = modelo.batch_extract_entities(textos, list(etiquetas), threshold=UMBRAL_BASE,
                                                    include_confidence=True, batch_size=a.lote)
                # por valor: lista de (etiqueta, confianza)
                det = [[(e, x["confidence"]) for e, xs in r["entities"].items() for x in xs] for r in res]
                for u in umbrales:
                    con, mejores = 0, Counter()
                    for d in det:
                        ok = [(e, c) for e, c in d if c >= u]
                        if ok:
                            con += 1
                            mejores[max(ok, key=lambda z: z[1])[0]] += 1
                    frac = con / len(det)
                    ent = etiquetas[mejores.most_common(1)[0][0]] if mejores else ""
                    filas.append(dict(variante=f"{variante} umbral {u}", tabla=tabla, columna=col,
                                      marcada=frac >= a.min_fraccion, entidad=ent if frac >= a.min_fraccion else "",
                                      entidad_mas_frecuente=ent, fraccion=round(frac, 3), n_valores=len(vals)))
            tiempos[variante] = time.time() - t0
            print(f"[{a.base}] {variante}: {tiempos[variante]:.0f} s", flush=True)

    df = pd.DataFrame(filas)
    df.insert(0, "corrida", 1)
    df.insert(0, "prueba", cfg["prueba"])
    nombre = cfg["prueba"].lower()
    df.to_csv(salida / f"{nombre}_columnas.csv", index=False)
    md = [f"# {cfg['prueba']}: GLiNER2-PII sobre {cfg['db']}", "",
          f"- Corrida: {datetime.datetime.now():%Y-%m-%d %H:%M}",
          f"- Equipo: {platform.machine()}, macOS {platform.mac_ver()[0]}, Python {platform.python_version()}, "
          f"dispositivo `{disp}`",
          f"- gliner2 {version('gliner2')}, transformers {version('transformers')}, torch {version('torch')}; "
          f"modelo `{MODELO}`",
          f"- Referencia: `{cfg['referencia'].relative_to(RAIZ)}`; columnas con valores: {len(muestras)} de {len(ref)}",
          f"- Parámetros: {a.n} valores por columna, marcar con ≥{a.min_fraccion:.0%}, umbrales {a.umbrales}, "
          f"semilla `{a.semilla}`, lote {a.lote}",
          "- Etiquetas `pii`: " + ", ".join(PII), "- Etiquetas agregadas en `pii_salud`: " + ", ".join(SALUD),
          "- Tiempos: " + ", ".join(f"{k} {v:.0f} s" for k, v in tiempos.items())]
    if avisos:
        md += ["", "## Avisos", ""] + [f"- {x}" for x in avisos]
    (salida / f"{nombre}_corrida.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
