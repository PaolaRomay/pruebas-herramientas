#!/usr/bin/env python3
"""A5m / A5s: `anon.detect()` de PostgreSQL Anonymizer sobre el esquema de MIMIC-IV demo y Synthea.

`anon.detect(idioma)` compara el nombre de cada columna (en minúscula, coincidencia exacta) con un diccionario de
nombres típicos (`anon.identifier`), cada uno asociado a una categoría (`anon.identifiers_category`) y a si es
identificador directo. No mira valores: alcanza con el esquema.

Requiere un contenedor con la extensión y el esquema de la base, sin filas (ver la ficha):
  docker run -d --name salud-anon --platform linux/amd64 -e POSTGRES_PASSWORD=postgres -p 127.0.0.1:55434:5432 \
    registry.gitlab.com/dalibo/postgresql_anonymizer:stable
  docker exec salud-anon psql -U postgres -c "create database mimic_demo"
  docker exec pagila-db pg_dump -U postgres --schema-only --no-owner --no-privileges mimic_demo \
    | docker exec -i salud-anon psql -U postgres -d mimic_demo
  docker exec salud-anon psql -U postgres -d mimic_demo -c "select anon.init()"

Variantes:
  en_US           marcada si el nombre está en el diccionario en inglés (cualquier categoría).
  en_US_directos  solo las categorías que el diccionario marca como identificador directo.

Uso:  .venv/bin/python pruebas/salud/A5-anon-detect/a5_anon_detect_salud.py --base mimic   (o synthea)
Salida: resultados/<base>/a5<m|s>_columnas.csv y a5<m|s>_corrida.md
"""
import argparse
import csv
import datetime
import subprocess
import time
from pathlib import Path

import pandas as pd
import sqlalchemy as sa

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[2]
BASES = {
    "mimic": dict(prueba="A5m", db="mimic_demo", referencia=RAIZ / "data" / "columnas_sensibles_mimic.csv"),
    "synthea": dict(prueba="A5s", db="synthea_p1000", referencia=RAIZ / "data" / "columnas_sensibles_synthea.csv"),
}
# categoría del diccionario -> entidad compatible con comparar_salud.py (el resto, en mayúsculas)
ENTIDAD = {"firstname": "PERSON", "lastname": "PERSON", "name": "PERSON", "medical_practionner_name": "PERSON",
           "study_participant_name": "PERSON", "birth_date": "DATE_TIME", "date": "DATE_TIME",
           "admission_date": "DATE_TIME", "discharge_date": "DATE_TIME", "death_date": "DATE_TIME",
           "city": "LOCATION", "street_address": "LOCATION", "zipcode": "LOCATION", "zipcode_us": "LOCATION",
           "country": "LOCATION", "geodata": "LOCATION", "social_security_id": "US_SSN"}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", choices=BASES, required=True)
    ap.add_argument("--puerto", default="55434")
    ap.add_argument("--idioma", default="en_US")
    a = ap.parse_args()
    cfg = BASES[a.base]
    salida = AQUI / "resultados" / a.base
    salida.mkdir(parents=True, exist_ok=True)
    eng = sa.create_engine(f"postgresql+psycopg2://postgres:postgres@127.0.0.1:{a.puerto}/{cfg['db']}")

    t0 = time.time()
    with eng.connect() as conn:
        version = conn.execute(sa.text("select anon.version()")).scalar()
        pg = conn.execute(sa.text("show server_version")).scalar()
        n_dic = conn.execute(sa.text("select count(*) from anon.identifier where lang = :l"), {"l": a.idioma}).scalar()
        det = conn.execute(sa.text(
            "select n.nspname, c.relname, d.column_name, d.identifiers_category, d.direct "
            "from anon.detect(:l) d join pg_class c on c.oid = d.table_name join pg_namespace n on n.oid = "
            "c.relnamespace"), {"l": a.idioma}).fetchall()
    dt = time.time() - t0
    encontradas = {(r[0], r[1], r[2]): (r[3], r[4]) for r in det}

    ref = list(csv.DictReader(open(cfg["referencia"], encoding="utf-8")))
    filas = []
    for variante in (a.idioma, f"{a.idioma}_directos"):
        for r in ref:
            cat, directo = encontradas.get((r["esquema"], r["tabla"], r["columna"]), ("", False))
            marc = bool(cat) and (directo or not variante.endswith("_directos"))
            filas.append(dict(prueba=cfg["prueba"], variante=variante, corrida=1, tabla=r["tabla"],
                              columna=r["columna"], marcada=marc,
                              entidad=ENTIDAD.get(cat, cat.upper()) if marc else "",
                              categoria_anon=cat, directo=directo if cat else ""))
    nombre = cfg["prueba"].lower()
    pd.DataFrame(filas).to_csv(salida / f"{nombre}_columnas.csv", index=False)

    imagen = subprocess.run(["docker", "inspect", "salud-anon", "--format", "{{.Image}}"],
                            capture_output=True, text=True).stdout.strip()
    md = [f"# {cfg['prueba']}: anon.detect sobre el esquema de {cfg['db']}", "",
          f"- Corrida: {datetime.datetime.now():%Y-%m-%d %H:%M}",
          f"- PostgreSQL Anonymizer {version} sobre PostgreSQL {pg} (contenedor `salud-anon`, imagen `{imagen[:19]}…`)",
          f"- Diccionario `{a.idioma}`: {n_dic} nombres de columna",
          f"- Referencia: `{cfg['referencia'].relative_to(RAIZ)}`; {len(ref)} columnas",
          f"- Columnas detectadas: {len(encontradas)}; tiempo de `anon.detect`: {dt:.2f} s", "",
          "| Columna | Categoría | Directo |", "|---|---|---|"]
    md += [f"| {k[1]}.{k[2]} | {v[0]} | {'sí' if v[1] else 'no'} |" for k, v in sorted(encontradas.items())]
    (salida / f"{nombre}_corrida.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
