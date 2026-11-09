#!/usr/bin/env python3
"""A6m / A6s: combinación del LLM local (A2) y Presidio (A1) sobre MIMIC-IV demo y Synthea.

No vuelve a correr ninguna herramienta: combina, columna por columna, las salidas ya guardadas de
  - LLM: A2 `a2b` (esquema + valores) o `a2a` (solo esquema), corrida 1 (las corridas son idénticas);
  - Presidio: A1 `structured:most_common umbral 0.0` (la mejor configuración de A1m / A1s).

Reglas de combinación (variantes):
  interseccion   marcada si la marcan los dos (el LLM propone, Presidio confirma: la idea original de A6).
  union          marcada si la marca alguno.
  cascada        decide el LLM; Presidio solo agrega columnas cuando detecta un formato fuerte (SSN, correo,
                 teléfono, tarjeta, IP), que son los reconocedores con patrón y validación propios.
Etiqueta: la del LLM; si el LLM no marca y la agrega Presidio, la de Presidio.

Uso:  .venv/bin/python pruebas/salud/A6-llm-presidio/a6_combinar.py   (las dos bases)
Salida: resultados/<base>/a6<m|s>_columnas.csv
"""
from pathlib import Path

import pandas as pd

AQUI = Path(__file__).resolve().parent
SALUD = AQUI.parent
PRESIDIO = "structured:most_common umbral 0.0"
FUERTES = {"US_SSN", "EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD", "IP_ADDRESS"}


def main():
    for base, s in (("mimic", "m"), ("synthea", "s")):
        p = pd.read_csv(SALUD / "A1-presidio" / "resultados" / base / f"a1{s}_columnas.csv", keep_default_na=False)
        p = p[p.variante == PRESIDIO][["tabla", "columna", "marcada", "entidad"]]
        p["marcada"] = p.marcada.astype(str).str.lower() == "true"
        filas = []
        for llm in ("a2b", "a2a"):
            l = pd.read_csv(SALUD / "A2-llm-local" / "resultados" / base / f"a2{s}_{llm}_columnas.csv",
                            keep_default_na=False)
            l = l[l.corrida == 1][["tabla", "columna", "marcada", "entidad"]]
            l["marcada"] = l.marcada.astype(str).str.lower() == "true"
            x = l.merge(p, on=["tabla", "columna"], suffixes=("_llm", "_pre"))  # solo columnas que vieron los dos
            fuerte = x.entidad_pre.isin(FUERTES) & x.marcada_pre
            reglas = {"interseccion": x.marcada_llm & x.marcada_pre,
                      "union": x.marcada_llm | x.marcada_pre,
                      "cascada": x.marcada_llm | fuerte}
            for nombre, marc in reglas.items():
                ent = x.entidad_llm.where(x.marcada_llm, x.entidad_pre).where(marc, "")
                filas.append(pd.DataFrame(dict(prueba=f"A6{s}", variante=f"{nombre} ({llm} + presidio)", corrida=1,
                                               tabla=x.tabla, columna=x.columna, marcada=marc, entidad=ent,
                                               marcada_llm=x.marcada_llm, marcada_presidio=x.marcada_pre,
                                               entidad_presidio=x.entidad_pre)))
        out = AQUI / "resultados" / base
        out.mkdir(parents=True, exist_ok=True)
        pd.concat(filas).to_csv(out / f"a6{s}_columnas.csv", index=False)
        print(base, sum(len(f) for f in filas), "filas")


if __name__ == "__main__":
    main()
