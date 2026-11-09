#!/usr/bin/env python3
"""Anotación a ciegas de la lista de referencia y acuerdo entre anotadores.

  plantillas  Arma la muestra a anotar (65 columnas al azar entre las evaluables, con semilla fija) y una
              plantilla por persona SIN la propuesta de las reglas, para no influir. Las reglas de criterio del
              equipo ya se decidieron en grupo (DEC-1 a DEC-6): la anotación comprueba que las reglas coinciden con
              el criterio de cada persona.
  acuerdo     Compara las anotaciones entre sí y con las reglas: acuerdo observado y kappa de Cohen sobre
              «sensible» (sí / no / dudoso) y sobre «categoria». Lista los desacuerdos para discutirlos.

Uso:
  .venv/bin/python pruebas/_bases/referencia/anotacion.py plantillas --personas jero,paola
  .venv/bin/python pruebas/_bases/referencia/anotacion.py acuerdo --personas jero,paola
Archivos: anotacion/muestra.csv, anotacion/<persona>.csv (se completan a mano), anotacion/acuerdo.md
"""
import argparse
import csv
import random
from collections import Counter
from pathlib import Path

AQUI = Path(__file__).resolve().parent
DIR = AQUI / "anotacion"
PROPUESTAS = ["propuesta_mimic_demo.csv", "propuesta_synthea_p1000.csv"]
SEMILLA, TAMANO_MUESTRA = "referencia-2026", 65
CAMPOS_PERFIL = ["tipo", "nulos_pct", "distintos", "unica"]


def leer(p):
    return list(csv.DictReader(open(p, encoding="utf-8")))


def clave(r):
    return (r["base"], r["tabla"], r["columna"])


def propuestas():
    filas = []
    for p in PROPUESTAS:
        base = p.removeprefix("propuesta_").removesuffix(".csv")
        filas += [dict(r, base=base) for r in leer(AQUI / p)]
    return filas


def plantillas(personas):
    filas = propuestas()
    evaluables = [r for r in filas if r["categoria"] != "NO_EVALUABLE"]
    muestra = random.Random(SEMILLA).sample(evaluables, TAMANO_MUESTRA)
    muestra.sort(key=clave)
    DIR.mkdir(exist_ok=True)
    with open(DIR / "muestra.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["base", "tabla", "columna"])
        for r in muestra:
            w.writerow(clave(r))
    for p in personas:
        destino = DIR / f"{p}.csv"
        if destino.exists():
            print(f"{destino.name} ya existe: no se pisa")
            continue
        with open(destino, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["base", "tabla", "columna", *CAMPOS_PERFIL, "sensible", "categoria", "nota"])
            for r in muestra:
                w.writerow([*clave(r), *(r[c] for c in CAMPOS_PERFIL), "", "", ""])
    print(f"Muestra: {len(muestra)} columnas al azar de {len(evaluables)} evaluables (semilla {SEMILLA!r}). "
          f"Plantillas: {', '.join(f'{p}.csv' for p in personas)} en {DIR}")


def kappa(a, b):
    n = len(a)
    if not n:
        return float("nan"), float("nan")
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    return po, (po - pe) / (1 - pe) if pe < 1 else float("nan")


def acuerdo(personas):
    reglas = {clave(r): r for r in propuestas()}
    anot = {p: {clave(r): r for r in leer(DIR / f"{p}.csv")} for p in personas}
    comunes = sorted(set.intersection(*(set(k for k, r in anot[p].items() if r["sensible"].strip())
                                        for p in personas)))
    md = ["# Acuerdo entre anotadores", "", f"Columnas anotadas por todos: {len(comunes)}", "",
          "| Par | Campo | Acuerdo | Kappa |", "|---|---|---|---|"]
    fuentes = {p: lambda k, p=p: anot[p][k] for p in personas}
    fuentes["reglas"] = lambda k: reglas[k]
    nombres = list(fuentes)
    for i, x in enumerate(nombres):
        for y in nombres[i + 1:]:
            for campo in ("sensible", "categoria"):
                a = [fuentes[x](k)[campo].strip().lower() for k in comunes]
                b = [fuentes[y](k)[campo].strip().lower() for k in comunes]
                po, k = kappa(a, b)
                md.append(f"| {x} – {y} | {campo} | {po:.2f} | {k:.2f} |")
    md += ["", "## Desacuerdos en «sensible» (a discutir)", "", "| Columna | " + " | ".join(nombres) + " |",
           "|---|" + "---|" * len(nombres)]
    for k in comunes:
        vals = [fuentes[n](k)["sensible"].strip().lower() for n in nombres]
        if len(set(vals)) > 1:
            md.append(f"| {k[0]}: {k[1]}.{k[2]} | " + " | ".join(vals) + " |")
    (DIR / "acuerdo.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md[:6 + 3 * len(nombres)]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("accion", choices=["plantillas", "acuerdo"])
    ap.add_argument("--personas", default="jero,paola")
    a = ap.parse_args()
    personas = a.personas.split(",")
    plantillas(personas) if a.accion == "plantillas" else acuerdo(personas)


if __name__ == "__main__":
    main()
