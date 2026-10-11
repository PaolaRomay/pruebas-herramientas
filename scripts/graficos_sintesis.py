#!/usr/bin/env python3
"""Gráficos (PNG) de las pruebas de síntesis (D*), para leerlos directamente en GitHub.

GitHub no muestra los .html (enseña el código fuente), pero sí las imágenes enlazadas desde un .md.
Este script dibuja:

  resultados_comparados/graficos/sintesis_distribuciones.png
      Pagila real contra cada base sintética, en cuatro columnas que dicen mucho de la calidad:
      monto de los pagos, duración de las películas, clasificación (rating) y alquileres por mes.
  pruebas/D2-mostlyai/resultados/d2_tiempos_por_tabla.png
      segundos de entrenamiento y de generación de MOSTLY AI por tabla.

Lee las bases con `docker exec pagila-db psql` (no necesita psycopg2). Necesita matplotlib, que el
.venv común no trae: se corrió con el entorno de MOSTLY AI (`../.venv`). Cualquier Python con pandas
y matplotlib sirve.

Uso (desde la raíz del repo, con la base levantada):
    ../.venv/bin/python scripts/graficos_sintesis.py
"""
import io
import subprocess
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "resultados_comparados" / "graficos"

# Paleta de referencia de la guía de visualización (slots 1-3, validados por pares, modo claro).
SUPERFICIE, TEXTO, TEXTO_2, GRILLA = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
SERIES = [  # orden fijo: el color sigue a la base, nunca al ranking
    ("Pagila real", "pagila", "#2a78d6"),
    ("D2 · MOSTLY AI", "d2_auditoria", "#eb6834"),
    ("D5 · Tonic Fabricate", "d5_auditoria", "#1baf7a"),
]
# En D5 los pagos no entraron a la tabla (fechas de 2005, fuera de las particiones): se toman de la
# tabla auxiliar donde se cargaron para la ficha de D5.
TABLA_PAGOS = {"d5_auditoria": "aux.payment_rechazados"}


def consulta(base, sql):
    r = subprocess.run(["docker", "exec", "pagila-db", "psql", "-U", "postgres", "-d", base, "-Atc",
                        f"COPY ({sql}) TO STDOUT WITH CSV HEADER"], capture_output=True, text=True, check=True)
    return pd.read_csv(io.StringIO(r.stdout))


def estilo(ax, titulo, xlabel, ylabel="% de filas"):
    ax.set_facecolor(SUPERFICIE)
    ax.set_title(titulo, loc="left", fontsize=11, color=TEXTO, fontweight="bold", pad=8)
    ax.set_xlabel(xlabel, fontsize=9, color=TEXTO_2)
    ax.set_ylabel(ylabel, fontsize=9, color=TEXTO_2)
    ax.tick_params(colors=TEXTO_2, labelsize=8, length=0)
    ax.grid(axis="y", color=GRILLA, linewidth=0.8)
    ax.set_axisbelow(True)
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color("#b9b8b2")


def porcentaje(serie, bordes):
    cuentas = pd.cut(serie, bordes, right=False).value_counts(sort=False)
    return 100 * cuentas.values / max(len(serie), 1)


def linea(ax, x, y, nombre, color):
    ax.plot(x, y, color=color, linewidth=2, label=nombre, drawstyle="steps-mid", solid_joinstyle="round")


def distribuciones():
    datos = {}
    for nombre, base, color in SERIES:
        pagos = TABLA_PAGOS.get(base, "public.payment")
        datos[base] = {
            "monto": consulta(base, f"select amount::float as v from {pagos}")["v"],
            "duracion": consulta(base, "select length::float as v from film")["v"],
            "rating": consulta(base, "select rating::text as v from film")["v"],
            "meses": consulta(base, "select date_trunc('month', rental_date)::date as v, count(*) as n "
                                    "from rental group by 1 order by 1"),
        }

    fig, ejes = plt.subplots(2, 2, figsize=(12, 7.6), facecolor=SUPERFICIE)
    (a, b), (c, d) = ejes

    bordes = list(range(0, 13))
    for nombre, base, color in SERIES:
        linea(a, [x + 0.5 for x in bordes[:-1]], porcentaje(datos[base]["monto"], bordes), nombre, color)
    estilo(a, "Monto de los pagos", "monto (USD, tramos de 1)")

    bordes = list(range(40, 200, 10))
    for nombre, base, color in SERIES:
        linea(b, [x + 5 for x in bordes[:-1]], porcentaje(datos[base]["duracion"], bordes), nombre, color)
    estilo(b, "Duración de las películas", "minutos (tramos de 10)")

    categorias = ["G", "PG", "PG-13", "R", "NC-17"]
    ancho = 0.26
    for i, (nombre, base, color) in enumerate(SERIES):
        r = datos[base]["rating"]
        pct = [100 * (r == k).mean() for k in categorias]
        c.bar([j + (i - 1) * ancho for j in range(len(categorias))], pct, width=ancho - 0.03, color=color,
              label=nombre, edgecolor=SUPERFICIE, linewidth=1.5)
    c.set_xticks(range(len(categorias)), categorias)
    estilo(c, "Clasificación de las películas (rating)", "")

    for nombre, base, color in SERIES[:2]:
        m = datos[base]["meses"]
        x = pd.to_datetime(m["v"])
        d.plot(x, 100 * m["n"] / m["n"].sum(), color=color, linewidth=2, label=nombre)
    m5 = datos["d5_auditoria"]["meses"]
    anios = sorted({str(v)[:4] for v in m5["v"]})
    n5 = f"{int(m5['n'].sum()):,}".replace(",", ".")
    d.text(0.02, 0.95, f"D5 · Tonic Fabricate: los {n5} alquileres caen en {', '.join(anios)},\n"
                       "fuera de este eje (y de las particiones de payment).",
           transform=d.transAxes, fontsize=8.5, color=TEXTO_2, va="top")
    estilo(d, "Alquileres por mes", "mes de rental_date")

    manejadores, etiquetas = a.get_legend_handles_labels()
    fig.legend(manejadores, etiquetas, loc="upper center", ncol=3, frameon=False, fontsize=10,
               labelcolor=TEXTO, bbox_to_anchor=(0.5, 0.995))
    fig.text(0.01, 0.005, "Fuente: bases del contenedor pagila-db. Real = Pagila completa. En D5 los pagos son los "
                          "3210 que Fabricate generó y no entraron a la tabla (ver su ficha).",
             fontsize=8, color=TEXTO_2)
    fig.tight_layout(rect=(0, 0.02, 1, 0.95))
    SALIDA.mkdir(parents=True, exist_ok=True)
    ruta = SALIDA / "sintesis_distribuciones.png"
    fig.savefig(ruta, dpi=130, facecolor=SUPERFICIE)
    print(f"-> {ruta.relative_to(RAIZ)}")


def tiempos_d2():
    t = pd.read_csv(RAIZ / "pruebas/D2-mostlyai/resultados/d2_tiempos_por_tabla.csv")
    t = t[t.tabla != "(global)"].fillna(0)
    etapas = [c for c in t.columns if c not in ("trabajo", "tabla")]
    t["seg"] = t[etapas].sum(axis=1)
    p = t.pivot_table(index="tabla", columns="trabajo", values="seg", aggfunc="sum").fillna(0)
    p["total"] = p.sum(axis=1)
    p = p.sort_values("total")

    fig, ax = plt.subplots(figsize=(10, 6), facecolor=SUPERFICIE)
    izq = [0] * len(p)
    for col, nombre, color in (("entrenamiento", "Entrenamiento", "#2a78d6"), ("generacion", "Generación", "#eb6834")):
        ax.barh(p.index, p[col], left=izq, color=color, label=nombre, height=0.62, edgecolor=SUPERFICIE, linewidth=2)
        izq = [i + v for i, v in zip(izq, p[col])]
    for y, (tot, ent, gen) in enumerate(zip(p["total"], p["entrenamiento"], p["generacion"])):
        if tot >= 30:
            ax.text(tot + 6, y, f"{tot:.0f} s  (entren. {ent:.0f} · gen. {gen:.0f})", va="center", fontsize=8.5,
                    color=TEXTO_2)
    estilo(ax, "MOSTLY AI sobre Pagila: segundos por tabla", "segundos", "")
    ax.grid(axis="x", color=GRILLA, linewidth=0.8)
    ax.grid(axis="y", visible=False)
    ax.legend(loc="lower right", frameon=False, fontsize=9, labelcolor=TEXTO)
    fig.text(0.01, 0.01, "Incluye analizar, codificar y armar los reportes de cada tabla. payment: la asignación de "
                         "FK no-contexto falló y MOSTLY la hizo al azar\n(559 s del paso de generación, más ~5 s de reporte).", fontsize=8, color=TEXTO_2)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    ruta = RAIZ / "pruebas/D2-mostlyai/resultados/d2_tiempos_por_tabla.png"
    fig.savefig(ruta, dpi=130, facecolor=SUPERFICIE)
    print(f"-> {ruta.relative_to(RAIZ)}")


if __name__ == "__main__":
    distribuciones()
    tiempos_d2()
