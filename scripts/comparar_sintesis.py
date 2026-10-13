#!/usr/bin/env python3
"""Comparador de las pruebas de síntesis (D*): pone lado a lado las métricas mínimas de
«Sintetizar» de todas las herramientas, medidas con la misma vara.

No vuelve a medir nada: junta lo que ya dejó cada prueba.
  - E3 (pruebas/E3-chequeos-propios/resultados/<base>/): integridad fila por fila, calidad
    (SDMetrics), privacidad (Anonymeter y copias exactas) y filas por tabla.
  - La propia prueba: tiempos y memoria (si corrió en la máquina), y la carga estricta
    (sentencias rechazadas y FK que se pudieron volver a crear).

Para sumar una prueba nueva (D3, D4...): evaluarla con E3 y agregarla a REGISTRO.

Uso (desde la raíz del repo):
    python scripts/comparar_sintesis.py
Salidas en resultados_comparados/: sintesis_metricas.csv y sintesis_resumen.md.
"""
import argparse
import csv
import datetime
import json
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
E3 = RAIZ / "pruebas" / "E3-chequeos-propios" / "resultados"

REGISTRO = [
    {"prueba": "D2", "herramienta": "MOSTLY AI (SDK local 6.1.4)", "carpeta": "pruebas/D2-mostlyai",
     "base": "d2_auditoria", "aprende_de": "e3_entrenamiento (Pagila sin el control)",
     "tiempos": "pruebas/D2-mostlyai/resultados/d2_tiempos.json",
     "errores_carga": "pruebas/D2-mostlyai/evidencia/d2_errores_carga.csv",
     "resumen": "pruebas/D2-mostlyai/resultados/d2_resumen.md",
     "notas": "Entrena por CPU (no usa MPS). La asignación de FK no-contexto de payment falló y fue al azar."},
    {"prueba": "D5", "herramienta": "Tonic Fabricate (web, versión de prueba)", "carpeta": "pruebas/D5-tonic-fabricate",
     "base": "d5_auditoria", "aprende_de": "solo el esquema (no ve datos)",
     "tiempos": None,
     "errores_carga": "pruebas/D5-tonic-fabricate/evidencia/d5_errores_carga.csv",
     "resumen": "pruebas/D5-tonic-fabricate/resultados/d5_resumen.md",
     "notas": "Se pidió el 20 % de las filas. Los 3210 pagos (año 2005) no entraron: payment queda vacía "
              "y eso baja la calidad (Cardinality) por razones ajenas a la forma de los datos."},
]


def leer_csv(ruta):
    with open(ruta, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def fila_prueba(r):
    d = E3 / r["base"]
    out = {"prueba": r["prueba"], "herramienta": r["herramienta"], "aprende_de": r["aprende_de"]}

    # Filas generadas (las que quedaron cargadas en la base auditada)
    conteos = leer_csv(d / "e3_conteos.csv")
    total_real = sum(int(c["pagila"]) for c in conteos if c["pagila"])
    total_cand = sum(int(c["candidata"]) for c in conteos if c["candidata"])
    out["filas"] = total_cand
    out["filas_vs_pagila"] = f"{100 * total_cand / total_real:.0f} %"
    vacias = [c["tabla"] for c in conteos if c["candidata"] in ("0", "")]
    out["tablas_vacias"] = ", ".join(vacias) or "-"

    # Tiempos y memoria
    if r["tiempos"] and (RAIZ / r["tiempos"]).exists():
        t = json.loads((RAIZ / r["tiempos"]).read_text())["entrenar"]["fases"]
        out["entrenamiento_s"] = t["entrenamiento"]["segundos"]
        out["generacion_s"] = t["generacion"]["segundos"]
        out["memoria_max_gb"] = round(max(v["memoria_max_mb"] for v in t.values()) / 1024, 1)
    else:
        out["entrenamiento_s"] = out["generacion_s"] = out["memoria_max_gb"] = "nube (no medido)"

    # Carga estricta
    errores = leer_csv(RAIZ / r["errores_carga"])
    out["carga_estricta_rechazadas"] = sum(1 for e in errores if e["fase"] == "estricta")
    m = re.search(r"FK que se pudieron volver a crear[^*]*\*\*(\d+) de (\d+)\*\*", (RAIZ / r["resumen"]).read_text())
    out["fk_recreadas"] = f"{m.group(1)}/{m.group(2)}" if m else ""

    # Integridad fila por fila (catálogo + relaciones que agrega E3)
    viol = leer_csv(d / "e3_integridad.csv")
    suma = lambda tipos: sum(int(v["violaciones"] or 0) for v in viol if v["tipo"] in tipos and v["estado"] == "violada")
    out["fk_huerfanas"] = suma({"FK"})
    out["pk_unique_duplicadas"] = suma({"PK", "UNIQUE", "UNIQUE (índice)"})
    out["not_null_check"] = suma({"NOT NULL", "CHECK", "CHECK (dominio)"})

    # Calidad (SDMetrics vía E3)
    props = {(p["reporte"], p["Property"]): num(p["Score"]) for p in leer_csv(d / "e3_calidad_propiedades.csv")}
    calidad = [v for (rep, _), v in props.items() if rep == "calidad" and v is not None]
    diag = [v for (rep, _), v in props.items() if rep == "diagnóstico" and v is not None]
    out["calidad"] = round(sum(calidad) / len(calidad), 3) if calidad else ""
    out["diagnostico"] = round(sum(diag) / len(diag), 3) if diag else ""
    for prop in ("Column Shapes", "Column Pair Trends", "Cardinality", "Intertable Trends"):
        v = props.get(("calidad", prop))
        out[prop.lower().replace(" ", "_")] = round(v, 3) if v is not None else ""
    resumen_e3 = (d / "e3_resumen.md").read_text()
    m = re.search(r"Datos reales de comparación: `([^`]+)`", resumen_e3)
    out["calidad_contra"] = m.group(1) if m else ""

    # Privacidad
    priv = leer_csv(d / "e3_privacidad.csv")
    riesgos = [(num(p["riesgo"]), p["ataque"], p["detalle"]) for p in priv if num(p.get("riesgo")) is not None]
    peor = max(riesgos) if riesgos else (None, "", "")
    out["riesgo_max_anonymeter"] = round(peor[0], 3) if peor[0] is not None else ""
    out["riesgo_max_en"] = f"{peor[1]} ({peor[2]})" if peor[0] is not None else ""
    dcr = leer_csv(d / "e3_dcr.csv")[0]
    out["copias_exactas"] = f"{100 * float(dcr['copias_exactas']):.1f} %"
    out["notas"] = r["notas"]
    out["carpeta"] = r["carpeta"]
    return out


def tabla_md(filas, columnas, titulos):
    out = ["| " + " | ".join(titulos) + " |", "|" + "---|" * len(titulos)]
    out += ["| " + " | ".join(str(f.get(c, "")) for c in columnas) + " |" for f in filas]
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--salida", default=str(RAIZ / "resultados_comparados"))
    ap.add_argument("--fecha", help="fecha fija para el resumen (por defecto, ahora)")
    a = ap.parse_args()
    sal = Path(a.salida)
    sal.mkdir(parents=True, exist_ok=True)

    filas, faltan = [], []
    for r in REGISTRO:
        if not (E3 / r["base"] / "e3_resumen.md").exists():
            faltan.append(f"{r['prueba']}: no hay evaluación E3 de `{r['base']}`")
            continue
        filas.append(fila_prueba(r))
    campos = list(filas[0]) if filas else []
    with open(sal / "sintesis_metricas.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        w.writerows(filas)

    fecha = a.fecha or f"{datetime.datetime.now():%Y-%m-%d %H:%M}"
    md = ["# Síntesis de bases de datos: comparación entre pruebas", "", f"Generado: {fecha}", "",
          "Métricas mínimas de «Sintetizar» del plan: tiempo de entrenamiento y de generación, memoria máxima, "
          "claves huérfanas o duplicadas y un reporte de calidad. Se agregan la carga con todas las restricciones "
          "y la privacidad, medidas con el evaluador común E3. Cómo leer cada métrica: "
          "[docs/glosario-y-metodo.md](../docs/glosario-y-metodo.md).", "",
          "## Costo", "",
          tabla_md(filas, ["prueba", "herramienta", "aprende_de", "entrenamiento_s", "generacion_s", "memoria_max_gb",
                           "filas", "filas_vs_pagila"],
                   ["Prueba", "Herramienta", "Aprende de", "Entrenamiento (s)", "Generación (s)", "Memoria máx. (GB)",
                    "Filas cargadas", "vs. Pagila"]), "",
          "## Integridad", "",
          tabla_md(filas, ["prueba", "carga_estricta_rechazadas", "fk_recreadas", "fk_huerfanas",
                           "pk_unique_duplicadas", "not_null_check", "tablas_vacias"],
                   ["Prueba", "Sentencias rechazadas (carga estricta)", "FK recreadas", "Filas huérfanas",
                    "Filas duplicadas (PK/UNIQUE)", "NOT NULL / CHECK", "Tablas que quedaron vacías"]), "",
          "«Filas huérfanas» incluye las 4 relaciones que el catálogo no cubre (FK de `payment` en la tabla padre "
          "y `store.manager_staff_id`).", "",
          "## Calidad (SDMetrics, 0 a 1)", "",
          tabla_md(filas, ["prueba", "calidad", "column_shapes", "column_pair_trends", "cardinality",
                           "intertable_trends", "diagnostico", "calidad_contra"],
                   ["Prueba", "Calidad", "Column Shapes", "Column Pair Trends", "Cardinality", "Intertable Trends",
                    "Diagnóstico", "Comparada contra"]), "",
          "![Distribuciones: Pagila real contra cada base sintética](graficos/sintesis_distribuciones.png)", "",
          "## Privacidad", "",
          tabla_md(filas, ["prueba", "riesgo_max_anonymeter", "riesgo_max_en", "copias_exactas"],
                   ["Prueba", "Riesgo máximo (Anonymeter)", "En qué ataque", "Copias exactas de personas"]), "",
          "## Notas por prueba", ""]
    md += [f"- **{f['prueba']}** ([ficha]({'../' + f['carpeta']}/ficha.md)): {f['notas']}" for f in filas]
    if faltan:
        md += ["", "## Sin evaluar todavía", ""] + [f"- {x}" for x in faltan]
    md += ["", "Detalle por métrica en `sintesis_metricas.csv`. Se regenera con `python scripts/comparar_sintesis.py`."]
    (sal / "sintesis_resumen.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
