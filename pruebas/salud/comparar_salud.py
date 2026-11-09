#!/usr/bin/env python3
"""Comparador de detección (función A) para las bases de salud: MIMIC-IV demo y Synthea.

Reutiliza scripts/comparar_deteccion.py sin modificarlo, con tres cambios:
  - busca resultados en pruebas/salud/A*/resultados/<base>/*_columnas.csv (no se mezclan con Pagila);
  - usa la lista congelada de la base (data/columnas_sensibles_<base>.csv) y no excluye columnas a mano (las vacías ya
    son «dudoso» en la lista);
  - mide la etiqueta contra `entidad_esperada` de la lista (PERSON, DATE_TIME, LOCATION, US_SSN…), en vez de las
    categorías de Pagila. En el resumen, la columna «categoría» muestra esa entidad esperada.

Uso:  .venv/bin/python pruebas/salud/comparar_salud.py --base mimic   (o synthea)
Salida: resultados_comparados/salud/<base>/
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import comparar_deteccion as cd  # noqa: E402

PREFIJOS = {
    "person": ("PERSON", "NAME", "FIRST_NAME", "LAST_NAME", "GIVEN_NAME", "SURNAME"),
    "date_time": ("DATE_TIME", "DATE", "TIME"),
    "location": ("LOCATION", "ADDRESS", "GPE", "CITY", "STREET"),
    "us_ssn": ("US_SSN", "SSN"),
    "us_driver_license": ("US_DRIVER_LICENSE", "DRIVER"),
    "us_passport": ("US_PASSPORT", "PASSPORT"),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", choices=["mimic", "synthea"], required=True)
    a = ap.parse_args()

    def leer_referencia(ruta):
        df = pd.read_csv(ruta, dtype=str).fillna("")
        df["verdad"] = df["sensible"].str.strip().str.lower()
        df["categoria"] = df["entidad_esperada"].str.strip().str.lower()
        return df[["tabla", "columna", "verdad", "categoria"]]

    cd.leer_referencia = leer_referencia
    cd.descubrir = lambda carpeta: sorted(Path(carpeta).glob(f"A*/resultados/{a.base}/*_columnas.csv"))
    cd.PREFIJOS_ESPERADOS = PREFIJOS
    sys.argv = ["comparar_deteccion.py", "--referencia", str(RAIZ / "data" / f"columnas_sensibles_{a.base}.csv"),
                "--excluir", "", "--pruebas", str(AQUI),
                "--salida", str(RAIZ / "resultados_comparados" / "salud" / a.base)]
    cd.main()


if __name__ == "__main__":
    main()
