#!/usr/bin/env python3
"""Perfil de cada columna de una base: ayuda a etiquetar la lista de referencia sin clasificar nada.

Por columna: tipo, filas, % de nulos, valores distintos, si es única entre los no nulos, largo promedio y máximo
(si es texto), y si es PK o FK declarada. Solo agregados: nunca escribe valores de filas.

Uso:
  .venv/bin/python pruebas/_bases/referencia/perfilar_columnas.py --base mimic_demo --esquemas mimiciv_hosp,mimiciv_icu
  .venv/bin/python pruebas/_bases/referencia/perfilar_columnas.py --base synthea_p100 --esquemas synthea
Salida: pruebas/_bases/referencia/perfil_<base>.csv
"""
import argparse
import csv
from pathlib import Path

import psycopg2
from psycopg2 import sql

AQUI = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--esquemas", required=True, help="lista separada por comas")
    a = ap.parse_args()
    esquemas = a.esquemas.split(",")
    con = psycopg2.connect(host="127.0.0.1", port=55432, user="postgres", password="postgres", dbname=a.base)
    cur = con.cursor()
    cur.execute("""select c.table_schema, c.table_name, c.column_name, c.data_type
                   from information_schema.columns c join information_schema.tables t using (table_schema, table_name)
                   where c.table_schema = any(%s) and t.table_type = 'BASE TABLE'
                   order by 1, 2, c.ordinal_position""", (esquemas,))
    columnas = cur.fetchall()
    cur.execute("""select n.nspname, rel.relname, a.attname, con.contype
                   from pg_constraint con join pg_class rel on rel.oid = con.conrelid
                   join pg_namespace n on n.oid = rel.relnamespace
                   join pg_attribute a on a.attrelid = con.conrelid and a.attnum = any(con.conkey)
                   where con.contype in ('p', 'f') and n.nspname = any(%s)""", (esquemas,))
    claves = {}
    for s, t, c, k in cur.fetchall():
        claves.setdefault((s, t, c), set()).add(k)

    filas = []
    for s, t, c, tipo in columnas:
        col, tab = sql.Identifier(c), sql.Identifier(s, t)
        texto = tipo in ("text", "character varying", "character")
        largo = (sql.SQL(", avg(length({0}))::numeric(10,1), max(length({0}))").format(col) if texto
                 else sql.SQL(", null, null"))
        cur.execute(sql.SQL("select count(*), count({0}), count(distinct {0}){1} from {2}").format(col, largo, tab))
        n, no_nulos, distintos, largo_prom, largo_max = cur.fetchone()
        k = claves.get((s, t, c), set())
        filas.append(dict(
            base=a.base, esquema=s, tabla=t, columna=c, tipo=tipo, filas=n,
            nulos_pct=round(100 * (n - no_nulos) / n, 1) if n else "",
            distintos=distintos, unica="sí" if no_nulos and distintos == no_nulos else "no",
            largo_prom=largo_prom if largo_prom is not None else "", largo_max=largo_max if largo_max is not None else "",
            pk="sí" if "p" in k else "", fk_declarada="sí" if "f" in k else ""))
    salida = AQUI / f"perfil_{a.base}.csv"
    with open(salida, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]))
        w.writeheader(); w.writerows(filas)
    print(f"{len(filas)} columnas de {len({(r['esquema'], r['tabla']) for r in filas})} tablas → {salida}")


if __name__ == "__main__":
    main()
