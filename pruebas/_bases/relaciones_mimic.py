#!/usr/bin/env python3
"""Relaciones de la demo de MIMIC-IV: declaradas como FK y no declaradas, verificadas contra los datos.

Para cada columna que por su nombre apunta a la tabla «dueña» de un identificador (subject_id → patients,
hadm_id → admissions, etc.) cuenta filas, valores distintos y huérfanas (valores que no existen en la tabla
dueña). Marca si la relación está declarada como FK en el catálogo.

Solo imprime y guarda conteos agregados, nunca valores de filas (regla de manejo de datos del plan de MIMIC).

Uso:  .venv/bin/python pruebas/_bases/relaciones_mimic.py [--base mimic_demo]
Salida: pruebas/_bases/evidencia/mimic-demo/relaciones.csv
"""
import argparse
import csv
from pathlib import Path

import psycopg2

AQUI = Path(__file__).resolve().parent
H, I = "mimiciv_hosp", "mimiciv_icu"

# columna (o sufijo) → tabla dueña. itemid depende del módulo: en hosp lo usa labevents (d_labitems);
# en icu, las tablas de eventos (d_items).
DUENOS = [
    ("subject_id", None, (H, "patients", "subject_id")),
    ("hadm_id", None, (H, "admissions", "hadm_id")),
    ("stay_id", None, (I, "icustays", "stay_id")),
    ("emar_id", None, (H, "emar", "emar_id")),
    ("poe_id", None, (H, "poe", "poe_id")),
    ("pharmacy_id", None, (H, "pharmacy", "pharmacy_id")),
    ("caregiver_id", None, (I, "caregiver", "caregiver_id")),
    ("provider_id", "sufijo", (H, "provider", "provider_id")),   # admit_provider_id, order_provider_id…
    ("itemid", H, (H, "d_labitems", "itemid")),
    ("itemid", I, (I, "d_items", "itemid")),
    ("hcpcs_cd", None, (H, "d_hcpcs", "code")),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="mimic_demo")
    ap.add_argument("--salida", default=str(AQUI / "evidencia" / "mimic-demo" / "relaciones.csv"))
    a = ap.parse_args()
    con = psycopg2.connect(host="127.0.0.1", port=55432, user="postgres", password="postgres", dbname=a.base)
    cur = con.cursor()
    cur.execute("""select n.nspname, c.relname, a.attname
                   from pg_attribute a join pg_class c on c.oid=a.attrelid join pg_namespace n on n.oid=c.relnamespace
                   where n.nspname in (%s, %s) and c.relkind='r' and a.attnum>0 and not a.attisdropped""", (H, I))
    columnas = cur.fetchall()
    cur.execute("""select n.nspname, rel.relname, a.attname, rn.nspname, ref.relname
                   from pg_constraint con join pg_class rel on rel.oid=con.conrelid
                   join pg_namespace n on n.oid=rel.relnamespace
                   join pg_class ref on ref.oid=con.confrelid join pg_namespace rn on rn.oid=ref.relnamespace
                   join pg_attribute a on a.attrelid=con.conrelid and a.attnum=any(con.conkey)
                   where con.contype='f' and n.nspname in (%s, %s)""", (H, I))
    declaradas = {(s, t, c): (rs, rt) for s, t, c, rs, rt in cur.fetchall()}

    filas = []
    for esq, tabla, col in columnas:
        for nombre, modo, (ds, dt, dc) in DUENOS:
            coincide = col.endswith(nombre) if modo == "sufijo" else col == nombre
            if not coincide or (modo in (H, I) and modo != esq) or (esq, tabla, col) == (ds, dt, dc):
                continue
            cur.execute(f"""select count(*), count(distinct t.{col}),
                                   count(*) filter (where t.{col} is not null and d.{dc} is null)
                            from {esq}.{tabla} t left join {ds}.{dt} d on d.{dc} = t.{col}""")
            n, dist, huer = cur.fetchone()
            cur.execute(f"select count(*) from {esq}.{tabla} where {col} is null")
            nulos = cur.fetchone()[0]
            filas.append(dict(tabla=f"{esq}.{tabla}", columna=col, apunta_a=f"{ds}.{dt}.{dc}",
                              declarada="sí" if (esq, tabla, col) in declaradas else "no",
                              filas=n, nulos=nulos, distintos=dist, huerfanas=huer,
                              se_cumple="sí" if huer == 0 else "no"))
            break
    Path(a.salida).parent.mkdir(parents=True, exist_ok=True)
    with open(a.salida, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]))
        w.writeheader(); w.writerows(filas)
    nd = [r for r in filas if r["declarada"] == "no"]
    print(f"{len(filas)} relaciones candidatas: {len(filas) - len(nd)} declaradas, {len(nd)} no declaradas "
          f"({sum(r['se_cumple'] == 'sí' for r in nd)} se cumplen en los datos)")
    for r in nd:
        print(f"  {r['tabla']}.{r['columna']} -> {r['apunta_a']}: {r['huerfanas']} huérfanas de "
              f"{r['filas'] - r['nulos']} no nulas")
    print(f"Guardado en {a.salida}")


if __name__ == "__main__":
    main()
