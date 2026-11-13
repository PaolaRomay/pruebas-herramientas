#!/usr/bin/env python3
"""Carga una salida CSV de Synthea en PostgreSQL (contenedor pagila-db) y declara sus claves.

Synthea no trae DDL para PostgreSQL. Este script:
  1. crea la base (la borra si existe) y carga cada CSV en el esquema `synthea`, con tipos inferidos por pandas
     y nombres de columna en minúscula;
  2. declara PRIMARY KEY en `id` cuando la tabla lo tiene y es único;
  3. propone FK por nombre de columna (patient → patients, encounter → encounters, …, según el diccionario de
     datos de Synthea) y **declara solo las que se cumplen en los datos**. Las que no se cumplen quedan en el
     reporte, sin declarar.

Solo imprime conteos, nunca valores de filas.

Uso:  .venv/bin/python scripts/cargar_synthea.py data/synthea/p100_s12345/csv --base synthea_p100
Salida: pruebas/_bases/evidencia/<base>/claves.csv y tiempos.txt
"""
import argparse
import csv
import subprocess
import time
from pathlib import Path

import pandas as pd
import sqlalchemy as sa

RAIZ = Path(__file__).resolve().parents[1]
ESQ = "synthea"

# columna → tabla dueña (diccionario de datos de Synthea: «Foreign key to …»)
DUENOS = {
    "patient": "patients", "patientid": "patients",
    "encounter": "encounters", "appointmentid": "encounters",
    "provider": "providers", "providerid": "providers", "supervisingproviderid": "providers",
    "referringproviderid": "providers",
    "organization": "organizations",
    "payer": "payers", "primary_payer": "payers", "secondary_payer": "payers",
    "primarypatientinsuranceid": "payers", "secondarypatientinsuranceid": "payers",
    "claimid": "claims",
}


def psql(base, sql):
    return subprocess.run(["docker", "exec", "pagila-db", "psql", "-U", "postgres", "-d", base, "-Atc", sql],
                          capture_output=True, text=True, check=True).stdout.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_dir")
    ap.add_argument("--base", required=True)
    a = ap.parse_args()
    carpeta = Path(a.csv_dir)
    salida = RAIZ / "pruebas" / "_bases" / "evidencia" / a.base
    salida.mkdir(parents=True, exist_ok=True)

    subprocess.run(["docker", "exec", "pagila-db", "dropdb", "-U", "postgres", "--if-exists", a.base], check=True)
    subprocess.run(["docker", "exec", "pagila-db", "createdb", "-U", "postgres", a.base], check=True)
    eng = sa.create_engine(f"postgresql+psycopg2://postgres:postgres@127.0.0.1:55432/{a.base}")

    t0 = time.time()
    tablas = {}
    with eng.begin() as c:
        c.execute(sa.text(f"create schema {ESQ}"))
    for f in sorted(carpeta.glob("*.csv")):
        df = pd.read_csv(f, low_memory=False)
        df.columns = [x.lower() for x in df.columns]
        for col in df.columns:  # fechas ISO a timestamp
            if col in ("birthdate", "deathdate", "date", "start", "stop", "fromdate", "todate",
                       "currentillnessdate", "servicedate", "lastbilleddate1", "lastbilleddate2",
                       "lastbilleddatep") and df[col].dtype == object:
                df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)
        df.to_sql(f.stem, eng, schema=ESQ, index=False, chunksize=10000, method="multi")
        tablas[f.stem] = list(df.columns)
    t_carga = time.time() - t0

    filas = []
    with eng.begin() as c:
        for t, cols in tablas.items():
            if "id" in cols:
                n, d = c.execute(sa.text(f'select count(*), count(distinct id) from {ESQ}."{t}"')).one()
                if n == d:
                    c.execute(sa.text(f'alter table {ESQ}."{t}" add primary key (id)'))
                filas.append(dict(tabla=t, columna="id", apunta_a="", tipo="PK",
                                  declarada="sí" if n == d else "no", filas=n, huerfanas=n - d))
        for t, cols in tablas.items():
            for col in cols:
                dueno = DUENOS.get(col)
                if not dueno or dueno not in tablas or dueno == t:
                    continue
                n, nn, h = c.execute(sa.text(
                    f'select count(*), count(x.{col}), count(*) filter (where x.{col} is not null and d.id is null) '
                    f'from {ESQ}."{t}" x left join {ESQ}."{dueno}" d on d.id::text = x.{col}::text')).one()
                ok = h == 0 and nn > 0
                if ok:
                    c.execute(sa.text(f'alter table {ESQ}."{t}" add foreign key ({col}) references {ESQ}."{dueno}" (id)'))
                filas.append(dict(tabla=t, columna=col, apunta_a=f"{dueno}.id", tipo="FK",
                                  declarada="sí" if ok else "no", filas=nn, huerfanas=h))
    t_total = time.time() - t0

    with open(salida / "claves.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]))
        w.writeheader(); w.writerows(filas)
    tam = psql(a.base, f"select pg_size_pretty(pg_database_size('{a.base}'))")
    n_filas = sum(int(psql(a.base, f'select count(*) from {ESQ}."{t}"')) for t in tablas)
    resumen = (f"tablas: {len(tablas)}\nfilas: {n_filas}\ntamaño: {tam}\n"
               f"carga: {t_carga:.1f} s\ncarga + claves: {t_total:.1f} s\n")
    (salida / "tiempos.txt").write_text(resumen, encoding="utf-8")
    print(resumen, end="")
    fk = [r for r in filas if r["tipo"] == "FK"]
    print(f"PK: {sum(r['declarada'] == 'sí' for r in filas if r['tipo'] == 'PK')} | "
          f"FK propuestas: {len(fk)}, declaradas (se cumplen): {sum(r['declarada'] == 'sí' for r in fk)}")
    for r in fk:
        if r["declarada"] == "no":
            print(f"  no se cumple: {r['tabla']}.{r['columna']} -> {r['apunta_a']} ({r['huerfanas']} huérfanas de {r['filas']})")


if __name__ == "__main__":
    main()
