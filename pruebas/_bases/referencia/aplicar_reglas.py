#!/usr/bin/env python3
"""Aplica reglas.csv al perfil de una base y deja la propuesta de lista de referencia.

Cada columna toma la PRIMERA regla que coincide (base, tabla y columna son expresiones regulares completas).
Las columnas sin regla quedan como SIN_REGLA, para etiquetar a mano. El script no decide nada: ejecuta las reglas
que escribieron las personas.

Uso:  .venv/bin/python pruebas/_bases/referencia/aplicar_reglas.py perfil_mimic_demo.csv --base-reglas mimic
Salida: pruebas/_bases/referencia/propuesta_<base>.csv y un resumen por categoría y por regla.
"""
import argparse
import csv
import re
from collections import Counter
from pathlib import Path

AQUI = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("perfil")
    ap.add_argument("--base-reglas", required=True, help="valor de la columna base de reglas.csv (mimic, synthea)")
    a = ap.parse_args()
    reglas = [r for r in csv.DictReader(open(AQUI / "reglas.csv", encoding="utf-8"))
              if re.fullmatch(r["base"], a.base_reglas)]
    perfil = list(csv.DictReader(open(AQUI / a.perfil, encoding="utf-8")))
    # Regla general, antes que las demás (DEC-6): una columna vacía en toda la base no tiene qué detectar y queda
    # fuera de las métricas, como address.address2 en Pagila.
    vacia = {"id": "v00", "categoria": "NO_EVALUABLE", "sensible": "dudoso", "entidad": "", "fuente": "DEC-6"}
    salida, uso = [], Counter()
    for p in perfil:
        r = vacia if p["nulos_pct"] == "100.0" else next(
            (r for r in reglas if re.fullmatch(r["tabla"], p["tabla"]) and re.fullmatch(r["columna"], p["columna"])),
            None)
        uso[r["id"] if r else "SIN_REGLA"] += 1
        salida.append({"tabla": p["tabla"], "columna": p["columna"],
                       "sensible": r["sensible"] if r else "", "categoria": r["categoria"] if r else "SIN_REGLA",
                       "entidad_esperada": r["entidad"] if r else "", "regla": r["id"] if r else "",
                       "fuente": r["fuente"] if r else "", "tipo": p["tipo"], "nulos_pct": p["nulos_pct"],
                       "distintos": p["distintos"], "unica": p["unica"], "esquema": p["esquema"]})
    base = perfil[0]["base"]
    destino = AQUI / f"propuesta_{base}.csv"
    with open(destino, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(salida[0]))
        w.writeheader(); w.writerows(salida)
    print(f"{base}: {len(salida)} columnas → {destino.name}")
    print("  por sensible:", dict(Counter(s["sensible"] or "SIN_REGLA" for s in salida)))
    print("  por categoría:", dict(Counter(s["categoria"] for s in salida).most_common()))
    sin_uso = [r["id"] for r in reglas if uso[r["id"]] == 0]
    if sin_uso:
        print("  reglas que no se usaron:", sin_uso)
    sin = [f"{s['tabla']}.{s['columna']}" for s in salida if s["categoria"] == "SIN_REGLA"]
    if sin:
        print(f"  SIN_REGLA ({len(sin)}):", ", ".join(sin))


if __name__ == "__main__":
    main()
