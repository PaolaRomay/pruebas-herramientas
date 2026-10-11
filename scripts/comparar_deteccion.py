#!/usr/bin/env python3
"""Evaluador común de las pruebas de detección (A*): compara todas las herramientas contra la
misma lista de referencia y con las mismas métricas.

Cada prueba deja un `resultados/<id>_columnas.csv` en el formato común (ver pruebas/README.md):

  prueba, variante, corrida, tabla, columna, marcada, entidad   (+ columnas extra, se ignoran)

Una fila por columna analizada. Si la herramienta no analizó una columna, la fila no está (no
cuenta como FN). Los formatos anteriores de A1 y A7 se leen con adaptadores, sin tocarlos.

Métricas (mismo criterio que `metricas()` de pruebas/A1-presidio/a1_presidio.py):
  - solo columnas con verdad "si"/"no" en la lista; las "dudoso" no cuentan;
  - se excluyen las no evaluables (--excluir; por defecto address.address2, vacía en toda la
    base, y staff.picture, binaria);
  - TP, FP, FN, TN, precisión, recall y F1 por prueba + variante (+ corrida);
  - etiqueta correcta: de las sensibles con categoría nombre/apellido/correo/teléfono/dirección,
    cuántas quedaron marcadas con una entidad compatible (PREFIJOS_ESPERADOS);
  - estabilidad, si una variante tiene más de una corrida: columnas que cambian de `marcada` o de
    entidad entre corridas y % de acuerdo.

Uso (desde la raíz del repo):
    python scripts/comparar_deteccion.py
    python scripts/comparar_deteccion.py --referencia data/otra_lista.csv --excluir staff.picture
    python scripts/comparar_deteccion.py --pruebas /tmp/pruebas --salida /tmp/comparados  # ensayo

Salidas en resultados_comparados/: deteccion_metricas.csv, deteccion_por_columna.csv y
deteccion_resumen.md. Misma entrada, misma salida: los CSV son idénticos byte a byte; el resumen
solo cambia en la fecha, que se puede fijar con --fecha.
"""
import argparse
import datetime
import hashlib
import re
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
REFERENCIA = RAIZ / "data" / "columnas_sensibles_borrador.csv"
EXCLUIR = "address.address2,staff.picture"

COMUNES = ["prueba", "variante", "corrida", "tabla", "columna", "marcada", "entidad"]

# Etiqueta compatible con cada categoría de la lista: la entidad (en mayúsculas, espacios y
# guiones como "_") tiene que empezar con alguno de estos prefijos. Cada herramienta nombra
# distinto (PERSON, NAME_GIVEN, EMAIL_ADDRESS, PHONE_NUMBER, LOCATION_ADDRESS...): para una
# herramienta nueva, agregar acá sus prefijos.
PREFIJOS_ESPERADOS = {
    "nombre": ("PERSON", "NAME", "FIRST_NAME", "GIVEN_NAME"),
    "apellido": ("PERSON", "NAME", "LAST_NAME", "SURNAME", "FAMILY_NAME"),
    "correo electronico": ("EMAIL", "E_MAIL", "CORREO"),
    "telefono": ("PHONE", "TELEPHONE", "TELEFONO"),
    "direccion": ("LOCATION", "ADDRESS", "STREET", "DIRECCION"),
}

VERDADEROS = {"true", "1", "si", "sí", "yes"}
FALSOS = {"false", "0", "no"}  # vacío = sin completar: error, no FN


# ----------------------------------------------------------------------------- entrada

def sha256(ruta):
    return hashlib.sha256(Path(ruta).read_bytes()).hexdigest()


def leer_referencia(ruta):
    df = pd.read_csv(ruta, dtype=str, keep_default_na=False)
    df["verdad"] = df["sensible"].str.strip().str.lower()
    df["categoria"] = df["categoria"].str.strip().str.lower()
    return df[["tabla", "columna", "verdad", "categoria"]]


def a_bool(v):
    s = str(v).strip().lower()
    if s in VERDADEROS:
        return True
    if s in FALSOS:
        return False
    raise ValueError(f"valor de `marcada` no reconocido: {v!r}")


def id_prueba(ruta):
    """pruebas/A7-tonic-textual/resultados/x.csv -> "A7"."""
    return ruta.parents[1].name.split("-", 1)[0]


def adaptar_a1(df, prueba):
    """A1 (Presidio): cada variante + umbral es una configuración. Determinista: corrida 1."""
    df = df.copy()
    df["variante"] = df["variante"] + " umbral " + df["umbral"]
    df["prueba"], df["corrida"] = prueba, 1
    return df


def adaptar_a7(df, prueba):
    """A7 (Tonic Textual) antes del formato común: las filas no comparables no se analizaron."""
    df = df[df["comparable"].map(a_bool)].copy()
    df["prueba"], df["variante"], df["corrida"] = prueba, "textual", 1
    return df


ADAPTADORES = {"A1": adaptar_a1, "A7": adaptar_a7}


def leer_salida(ruta):
    """Lee un *_columnas.csv y lo devuelve en el formato común (y el nombre del adaptador usado)."""
    df = pd.read_csv(ruta, dtype=str, keep_default_na=False)
    prueba = id_prueba(ruta)
    adaptador = "formato común"
    if not {"prueba", "variante", "corrida"} <= set(df.columns):
        if prueba not in ADAPTADORES:
            raise ValueError(f"{ruta}: no tiene prueba/variante/corrida y no hay adaptador para {prueba}")
        df = ADAPTADORES[prueba](df, prueba)
        adaptador = f"adaptador {prueba}"
    faltan = [c for c in COMUNES if c not in df.columns]
    if faltan:
        raise ValueError(f"{ruta}: faltan columnas {faltan}")
    df = df[COMUNES].copy()
    df["corrida"] = df["corrida"].astype(int)
    df["marcada"] = df["marcada"].map(a_bool)
    df["entidad"] = df["entidad"].fillna("").astype(str).str.strip()
    clave = ["prueba", "variante", "corrida", "tabla", "columna"]
    dup = df[df.duplicated(clave, keep=False)]
    if len(dup):
        raise ValueError(f"{ruta}: filas repetidas para {dup[clave].drop_duplicates().values.tolist()[:5]}")
    return df, adaptador


def descubrir(carpeta_pruebas):
    """Solo pruebas/A*/resultados/*_columnas.csv, en orden alfabético."""
    return sorted(Path(carpeta_pruebas).glob("A*/resultados/*_columnas.csv"))


# ----------------------------------------------------------------------------- métricas

def normalizar_entidad(e):
    return re.sub(r"[\s\-]+", "_", str(e).strip().upper())


def etiqueta_ok(categoria, marcada, entidad):
    pref = PREFIJOS_ESPERADOS.get(categoria)
    return bool(pref and marcada and normalizar_entidad(entidad).startswith(pref))


def evaluables(df):
    """Filas que entran en las métricas: verdad si/no y no excluidas."""
    return df[df["verdad"].isin(["si", "no"]) & ~df["excluida"]]


def metricas(df):
    d = evaluables(df)
    tp = int(((d.verdad == "si") & d.marcada).sum())
    fn = int(((d.verdad == "si") & ~d.marcada).sum())
    fp = int(((d.verdad == "no") & d.marcada).sum())
    tn = int(((d.verdad == "no") & ~d.marcada).sum())
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    con_esp = d[(d.verdad == "si") & d.categoria.isin(PREFIJOS_ESPERADOS)]
    return dict(TP=tp, FP=fp, FN=fn, TN=tn, precision=p, recall=r, F1=f1,
                etiqueta_ok=int(con_esp.etiqueta_ok.sum()), etiqueta_total=len(con_esp), n_evaluadas=len(d))


def nombres(df):
    return ", ".join(f"{t}.{c}" for t, c in df[["tabla", "columna"]].values)


def estabilidad(g):
    """Para una prueba+variante con varias corridas: qué columnas cambian entre corridas."""
    n_corridas = g.corrida.nunique()
    cols = g.groupby(["tabla", "columna"])
    presentes = cols.corrida.nunique() == n_corridas
    marc = cols.marcada.nunique() > 1
    ent_norm = g.assign(e=g.entidad.map(normalizar_entidad))
    siempre_marcada = cols.marcada.all()
    ent = ent_norm.groupby(["tabla", "columna"]).e.nunique() > 1
    cambia_ent = ent & siempre_marcada
    base = presentes[presentes].index
    cambia = (marc | cambia_ent).loc[base]
    return dict(corridas=n_corridas, columnas=len(base), cambian_marcada=int(marc.loc[base].sum()),
                cambian_entidad=int(cambia_ent.loc[base].sum()),
                acuerdo=(1 - cambia.mean()) if len(base) else 1.0,
                inestables=", ".join(f"{t}.{c}" for t, c in cambia[cambia].index),
                incompletas=int((~presentes).sum()))


def calcular(det):
    """Una fila por prueba+variante+corrida y, si hay varias corridas, una fila `promedio`."""
    filas, estab = [], {}
    for (prueba, variante), g in det.groupby(["prueba", "variante"], sort=True):
        por_corrida = []
        for corrida, gc in g.groupby("corrida", sort=True):
            m = dict(prueba=prueba, variante=variante, corrida=str(corrida), **metricas(gc))
            d = evaluables(gc)
            m["fn_columnas"] = nombres(d[(d.verdad == "si") & ~d.marcada])
            m["fp_columnas"] = nombres(d[(d.verdad == "no") & d.marcada])
            por_corrida.append(m)
        filas += por_corrida
        if len(por_corrida) > 1:
            num = ["TP", "FP", "FN", "TN", "precision", "recall", "F1", "etiqueta_ok", "etiqueta_total", "n_evaluadas"]
            prom = {k: sum(m[k] for m in por_corrida) / len(por_corrida) for k in num}
            filas.append(dict(prueba=prueba, variante=variante, corrida="promedio", **prom,
                              fn_columnas="", fp_columnas=""))
            estab[(prueba, variante)] = estabilidad(g)
    return pd.DataFrame(filas), estab


# ----------------------------------------------------------------------------- salidas

def numero(x):
    if pd.isna(x):
        return ""
    return str(int(x)) if float(x).is_integer() else str(round(float(x), 4))


def fmt(x, dec=2):
    return f"{x:.{dec}f}" if isinstance(x, float) and not float(x).is_integer() else str(int(x))


def tabla_metricas(met, estab):
    out = met.copy()
    for (p, v), e in estab.items():
        sel = (out.prueba == p) & (out.variante == v)
        out.loc[sel, "acuerdo_corridas"] = round(e["acuerdo"], 4)
        out.loc[sel, "cambian_marcada"] = e["cambian_marcada"]
        out.loc[sel, "cambian_entidad"] = e["cambian_entidad"]
    # como texto, para que los conteos no salgan como "7.0": enteros tal cual, el resto con 4 decimales
    for c in ("TP", "FP", "FN", "TN", "precision", "recall", "F1", "etiqueta_ok", "etiqueta_total",
              "n_evaluadas", "acuerdo_corridas", "cambian_marcada", "cambian_entidad"):
        if c in out:
            out[c] = out[c].map(numero)
    return out


def matriz(det, ref):
    """Columna × configuración. Celda: entidad si se marcó (o "SI" sin entidad), "no" si se
    analizó y no se marcó, vacía si no se analizó."""
    d = det.copy()
    d["config"] = d.prueba + " | " + d.variante + " | c" + d.corrida.astype(str)
    d["celda"] = [(e or "SI") if m else "no" for m, e in zip(d.marcada, d.entidad)]
    piv = d.pivot(index=["tabla", "columna"], columns="config", values="celda")
    piv = piv[sorted(piv.columns)]
    out = ref.set_index(["tabla", "columna"]).join(piv, how="outer").reset_index()
    orden = {"si": 0, "dudoso": 1, "no": 2}
    out["_o"] = out["verdad"].map(orden).fillna(3)
    return out.sort_values(["_o", "tabla", "columna"]).drop(columns="_o").fillna("")


def resumen_md(met, estab, det, ref, args, entradas, excluidas, fecha):
    principal = met[(met.corrida == "promedio") | ~met.set_index(["prueba", "variante"]).index.isin(estab.keys())]
    principal = principal.sort_values(["F1", "recall", "prueba", "variante"], ascending=[False, False, True, True])
    n = ref.verdad.value_counts()
    md = ["# Detección de columnas sensibles: comparación entre pruebas", "",
          f"Generado: {fecha}", "",
          "## Entradas", "",
          f"- Lista de referencia: `{args.referencia_rel}` (sha256 `{sha256(args.referencia)}`): "
          f"{n.get('si', 0)} sensibles, {n.get('no', 0)} no sensibles, {n.get('dudoso', 0)} dudosas "
          "(las dudosas no entran en las métricas)",
          f"- Excluidas de las métricas (no evaluables): {', '.join(excluidas) or 'ninguna'}"]
    for ruta, adaptador, sha in entradas:
        md.append(f"- `{ruta}` ({adaptador}, sha256 `{sha[:12]}…`)")
    md += ["", "## Comparación", "",
           "Orden: F1 y, a igualdad, recall (en anonimización un FN es un dato que se filtra). "
           "«Eval.» = columnas que entraron en las métricas: si una herramienta no analizó alguna, "
           "su denominador es menor. Las variantes con varias corridas muestran el promedio.", "",
           "| Prueba | Variante | Corridas | Eval. | TP | FP | FN | TN | Precisión | Recall | F1 | Etiqueta |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for _, m in principal.iterrows():
        corr = str(estab[(m.prueba, m.variante)]["corridas"]) if (m.prueba, m.variante) in estab else "1"
        md.append(f"| {m.prueba} | {m.variante} | {corr} | {fmt(m.n_evaluadas)} | {fmt(m.TP)} | {fmt(m.FP)} | "
                  f"{fmt(m.FN)} | {fmt(m.TN)} | {m.precision:.2f} | {m.recall:.2f} | {m.F1:.2f} | "
                  f"{fmt(m.etiqueta_ok)}/{fmt(m.etiqueta_total)} |")
    if estab:
        md += ["", "## Estabilidad entre corridas", "",
               "Cambia la marca = la columna se marcó en unas corridas y en otras no. Cambia la entidad = "
               "marcada en todas, pero con distinta entidad. Acuerdo = columnas sin ningún cambio.", "",
               "| Prueba | Variante | Corridas | Columnas | Cambia marca | Cambia entidad | Acuerdo | F1 por corrida | Inestables |",
               "|---|---|---|---|---|---|---|---|---|"]
        for (p, v), e in sorted(estab.items()):
            f1s = met[(met.prueba == p) & (met.variante == v) & (met.corrida != "promedio")]
            f1s = ", ".join(f"{x:.2f}" for x in f1s.F1)
            md.append(f"| {p} | {v} | {e['corridas']} | {e['columnas']} | {e['cambian_marcada']} | "
                      f"{e['cambian_entidad']} | {e['acuerdo']:.0%} | {f1s} | {e['inestables'] or '-'} |")
            if e["incompletas"]:
                md.append(f"\n> {p} {v}: {e['incompletas']} columnas no están en todas las corridas; no entran en la estabilidad.\n")

    ev = evaluables(det)
    md += ["", "## Columnas sensibles que se escaparon", "",
           "Por prueba: configuraciones (variante × corrida) que no la marcaron / que la analizaron.", ""]
    sens = ev[ev.verdad == "si"]
    nunca = sens.groupby(["tabla", "columna"]).marcada.sum()
    md.append(f"- Ninguna herramienta la detectó: {', '.join(f'{t}.{c}' for t, c in nunca[nunca == 0].index) or 'ninguna'}")
    fallos = sens.assign(fn=~sens.marcada).groupby(["tabla", "columna", "prueba"]).fn.agg(["sum", "size"])
    con_fn = fallos[fallos["sum"] > 0].reset_index()
    orden = con_fn.groupby(["tabla", "columna"])["sum"].sum().sort_values(ascending=False, kind="stable")
    for (t, c), _ in orden.items():
        f = con_fn[(con_fn.tabla == t) & (con_fn.columna == c)]
        md.append(f"- {t}.{c}: " + ", ".join(f"{r.prueba} {r['sum']}/{r['size']}" for _, r in f.iterrows()))

    md += ["", "## Falsos positivos compartidos", "",
           "No sensibles marcadas por más de una prueba (herramienta distinta)."]
    fp = ev[(ev.verdad == "no") & ev.marcada].groupby(["tabla", "columna"]).prueba.unique()
    compartidos = [(f"{t}.{c}", sorted(p)) for (t, c), p in fp.items() if len(p) > 1]
    md.append("")
    md += [f"- {c}: {', '.join(p)}" for c, p in compartidos] or ["- ninguno"]
    solos = [(f"{t}.{c}", p[0]) for (t, c), p in fp.items() if len(p) == 1]
    if solos:
        md.append("\nFP de una sola prueba: " + ", ".join(f"{c} ({p})" for c, p in solos))

    fuera = det.merge(ref, on=["tabla", "columna"], how="left", indicator=True)
    fuera = fuera[fuera._merge == "left_only"][["tabla", "columna"]].drop_duplicates()
    if len(fuera):
        md += ["", "## Avisos", "", f"- Columnas analizadas que no están en la lista de referencia (se ignoran): {nombres(fuera)}"]
    md += ["", "Detalle en `deteccion_metricas.csv` (una fila por prueba + variante + corrida, con FN y FP) "
           "y `deteccion_por_columna.csv` (matriz columna × configuración)."]
    return "\n".join(md) + "\n"


def relativa(ruta):
    ruta = Path(ruta).resolve()
    try:
        return str(ruta.relative_to(RAIZ))
    except ValueError:
        return str(ruta)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--referencia", default=str(REFERENCIA), help="lista de referencia (tabla,columna,sensible,categoria,...)")
    ap.add_argument("--excluir", default=EXCLUIR,
                    help="columnas tabla.columna separadas por coma que no entran en las métricas ('' = ninguna)")
    ap.add_argument("--pruebas", default=str(RAIZ / "pruebas"), help="carpeta donde buscar A*/resultados/*_columnas.csv")
    ap.add_argument("--salida", default=str(RAIZ / "resultados_comparados"))
    ap.add_argument("--fecha", default=None, help="fecha a poner en el resumen (por defecto, ahora)")
    args = ap.parse_args()
    args.referencia_rel = relativa(args.referencia)
    fecha = args.fecha or f"{datetime.datetime.now():%Y-%m-%d %H:%M}"
    excluidas = sorted(x.strip() for x in args.excluir.split(",") if x.strip())

    ref = leer_referencia(args.referencia)
    archivos = descubrir(args.pruebas)
    if not archivos:
        raise SystemExit(f"no hay ningún A*/resultados/*_columnas.csv en {args.pruebas}")
    partes, entradas = [], []
    for ruta in archivos:
        df, adaptador = leer_salida(ruta)
        partes.append(df)
        entradas.append((relativa(ruta), adaptador, sha256(ruta)))
        print(f"{relativa(ruta)}: {len(df)} filas ({adaptador})")
    det = pd.concat(partes, ignore_index=True)
    det = det.merge(ref, on=["tabla", "columna"], how="left")
    det[["verdad", "categoria"]] = det[["verdad", "categoria"]].fillna("")
    det["excluida"] = (det.tabla + "." + det.columna).isin(excluidas)
    det["etiqueta_ok"] = [etiqueta_ok(c, m, e) for c, m, e in zip(det.categoria, det.marcada, det.entidad)]

    met, estab = calcular(det)
    salida = Path(args.salida)
    salida.mkdir(parents=True, exist_ok=True)
    tabla_metricas(met, estab).to_csv(salida / "deteccion_metricas.csv", index=False, lineterminator="\n")
    matriz(det, ref).to_csv(salida / "deteccion_por_columna.csv", index=False, lineterminator="\n")
    md = resumen_md(met, estab, det, ref, args, entradas, excluidas, fecha)
    (salida / "deteccion_resumen.md").write_text(md, encoding="utf-8")
    print(md)
    print(f"Guardado en {salida}")


if __name__ == "__main__":
    main()
