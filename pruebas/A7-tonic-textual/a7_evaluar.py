#!/usr/bin/env python3
"""Prueba A7: mide qué columnas marcó Tonic Textual, con el mismo criterio que A1.

Entrada: los archivos que generó a7_exportar.py (entrada/valores/) y los mismos archivos ya
redactados por Textual, descargados en salida/valores/ con el MISMO nombre. En Textual hay que usar
el modo «Redaction» (reemplazar por etiqueta, no por valores sintéticos) para todas las entidades:
así cada valor detectado queda como [NAME_GIVEN_xxxx], [EMAIL_ADDRESS_xxxx], etc.

Una línea cuenta como detectada si cambió. Una columna queda marcada como sensible si se detectó
algo en al menos --min-fraccion de sus valores (A1 usó 0,5). La entidad de la columna es la etiqueta
más frecuente. Las métricas se calculan contra data/columnas_sensibles_borrador.csv, sin las dudosas,
igual que en A1, y se ponen al lado del resultado de A1 (variante manual, umbral 0).

resultados/a7_columnas.csv sigue el formato común de detección (ver pruebas/README.md): lleva
prueba/variante/corrida y solo las columnas que Textual efectivamente procesó; así lo lee
scripts/comparar_deteccion.py junto con las demás pruebas A*.

Uso: python pruebas/A7-tonic-textual/a7_evaluar.py
"""
import argparse
import csv
import re
from collections import Counter
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
PRUEBA, VARIANTE, CORRIDA = "A7", "textual", 1  # formato común de detección
ETIQUETA = re.compile(r"\[([A-Z][A-Z_]*?)(?:_[A-Za-z0-9]{3,})?\]")

# Etiqueta correcta según la categoría de la lista (prefijos, para no depender del nombre exacto).
ESPERADA = {
    "nombre": ("NAME", "PERSON"),
    "apellido": ("NAME", "PERSON"),
    "correo electronico": ("EMAIL",),
    "telefono": ("PHONE",),
    "direccion": ("LOCATION", "ADDRESS"),
}


def leer_verdad(ruta):
    with open(ruta, encoding="utf-8") as f:
        return {(r["tabla"], r["columna"]): r for r in csv.DictReader(f)}


def metricas(filas):
    d = [f for f in filas if f["verdad"] in ("si", "no") and f["comparable"]]
    tp = sum(f["verdad"] == "si" and f["marcada"] for f in d)
    fn = sum(f["verdad"] == "si" and not f["marcada"] for f in d)
    fp = sum(f["verdad"] == "no" and f["marcada"] for f in d)
    tn = sum(f["verdad"] == "no" and not f["marcada"] for f in d)
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    return dict(TP=tp, FP=fp, FN=fn, TN=tn, precision=round(p, 2), recall=round(r, 2), F1=round(f1, 2))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--entrada", default=str(AQUI / "entrada" / "valores"))
    ap.add_argument("--salida-textual", default=str(AQUI / "salida" / "valores"))
    ap.add_argument("--csv", default=str(RAIZ / "data" / "columnas_sensibles_borrador.csv"))
    ap.add_argument("--a1", default=str(RAIZ / "pruebas" / "A1-presidio" / "resultados" / "a1_columnas.csv"))
    ap.add_argument("--min-fraccion", type=float, default=0.5)
    a = ap.parse_args()

    verdad = leer_verdad(a.csv)
    filas, avisos = [], []
    for orig in sorted(Path(a.entrada).glob("*.txt")):
        tabla, columna = orig.stem.split(".", 1)
        red = Path(a.salida_textual) / orig.name
        v = verdad.get((tabla, columna), {})
        fila = {"tabla": tabla, "columna": columna, "verdad": v.get("sensible", "").strip().lower(),
                "categoria": v.get("categoria", ""), "comparable": False, "marcada": False,
                "fraccion": "", "entidad": "", "n_valores": 0}
        if not red.exists():
            avisos.append(f"falta la salida de Textual para {orig.name}")
            filas.append(fila)
            continue
        lo = orig.read_text(encoding="utf-8").splitlines()
        lr = red.read_text(encoding="utf-8").splitlines()
        if len(lo) != len(lr):
            avisos.append(f"{orig.name}: {len(lo)} líneas originales y {len(lr)} redactadas; no se puede comparar")
            filas.append(fila)
            continue
        cambiadas = [r for o, r in zip(lo, lr) if o != r]
        etiquetas = Counter(e for r in cambiadas for e in ETIQUETA.findall(r))
        frac = len(cambiadas) / len(lo) if lo else 0.0
        fila.update(comparable=True, n_valores=len(lo), fraccion=round(frac, 2),
                    marcada=frac >= a.min_fraccion,
                    entidad=etiquetas.most_common(1)[0][0] if etiquetas else "")
        pref = ESPERADA.get(fila["categoria"])
        fila["etiqueta_ok"] = (fila["entidad"].startswith(pref) if pref and fila["marcada"] else "")
        filas.append(fila)

    # A1 (Presidio, variante manual, umbral 0) al lado, para comparar columna por columna
    a1 = {}
    if Path(a.a1).exists():
        with open(a.a1, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["variante"] == "manual" and float(r["umbral"]) == 0.0:
                    a1[(r["tabla"], r["columna"])] = r
    for f in filas:
        r = a1.get((f["tabla"], f["columna"]), {})
        f["a1_marcada"], f["a1_entidad"] = r.get("marcada", ""), r.get("entidad", "")

    res = AQUI / "resultados"
    res.mkdir(exist_ok=True)
    campos = ["prueba", "variante", "corrida", "tabla", "columna", "marcada", "entidad", "verdad", "categoria",
              "n_valores", "fraccion", "etiqueta_ok", "a1_marcada", "a1_entidad", "comparable"]
    with open(res / "a7_columnas.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore")
        w.writeheader()
        # las columnas sin salida de Textual no se analizaron: quedan fuera (no son FN); van en Avisos
        w.writerows({"prueba": PRUEBA, "variante": VARIANTE, "corrida": CORRIDA, **f} for f in filas if f["comparable"])

    m = metricas(filas)
    a1_filas = [{"verdad": f["verdad"], "comparable": f["a1_marcada"] != "", "marcada": f["a1_marcada"] == "True"}
                for f in filas]
    m1 = metricas(a1_filas)
    eval_ = [f for f in filas if f["verdad"] in ("si", "no") and f["comparable"]]
    con_esp = [f for f in eval_ if f["verdad"] == "si" and f["categoria"] in ESPERADA]
    et_ok = sum(1 for f in con_esp if f.get("etiqueta_ok") is True)
    fallos_fn = [f"{f['tabla']}.{f['columna']}" for f in eval_ if f["verdad"] == "si" and not f["marcada"]]
    fallos_fp = [f"{f['tabla']}.{f['columna']}" for f in eval_ if f["verdad"] == "no" and f["marcada"]]

    md = ["# A7: Tonic Textual, detección de columnas sensibles en Pagila", "",
          f"Mismos valores que A1 (hasta 200 por columna, semilla `a1`). Criterio: columna marcada si se "
          f"detectó algo en al menos {a.min_fraccion:.0%} de sus valores. Columnas evaluables: {len(eval_)}.", "",
          "| Herramienta | TP | FP | FN | TN | Precisión | Recall | F1 |", "|---|---|---|---|---|---|---|---|",
          f"| Tonic Textual (A7) | {m['TP']} | {m['FP']} | {m['FN']} | {m['TN']} | {m['precision']} | {m['recall']} | {m['F1']} |",
          f"| Presidio manual, umbral 0 (A1) | {m1['TP']} | {m1['FP']} | {m1['FN']} | {m1['TN']} | {m1['precision']} | {m1['recall']} | {m1['F1']} |",
          "", f"Etiqueta correcta (Textual): {et_ok}/{len(con_esp)}", "",
          f"- Falsos negativos: {', '.join(fallos_fn) or 'ninguno'}",
          f"- Falsos positivos: {', '.join(fallos_fp) or 'ninguno'}", "",
          "## Por columna", "",
          "| Columna | Verdad | Fracción | Marcada | Entidad Textual | A1 marcada | Entidad A1 |", "|---|---|---|---|---|---|---|"]
    for f in filas:
        md.append(f"| {f['tabla']}.{f['columna']} | {f['verdad']} | {f['fraccion']} | {f['marcada']} | "
                  f"{f['entidad']} | {f['a1_marcada']} | {f['a1_entidad']} |")
    if avisos:
        md += ["", "## Avisos", ""] + [f"- {x}" for x in avisos]
    (res / "a7_resumen.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md[4:8]))
    if avisos:
        print("Avisos:", *avisos, sep="\n  ")


if __name__ == "__main__":
    main()
