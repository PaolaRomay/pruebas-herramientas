#!/usr/bin/env python3
"""D3m / D3s: SDV (HMASynthesizer, multitabla) sobre los mismos conjuntos que D2 (MOSTLY AI), como comparación.

Usa los Parquet que exporta pruebas/salud/D2-mostlyai/d2_mostly_salud.py (paso `exportar`) y la misma evaluación
(integridad, reglas de coherencia, estadísticas, copias exactas), para que las dos herramientas se midan igual.

Variantes por cantidad de tablas:
  mimic_47:   3 tablas (patients, admissions, diagnoses_icd) y 5 (+ icustays, labevents)
  synthea_85: 3 tablas (patients, encounters, conditions) y 4 (+ observations)

Uso:  .venv/bin/python pruebas/salud/D3-sdv/d3_sdv_salud.py --conjunto mimic_47 --tablas 3
Salida: resultados/<conjunto>_<n>t.json; sintéticos en salidas_grandes/ (fuera del repo).
"""
import argparse
import datetime
import json
import platform
import sys
import threading
import time
import warnings
from importlib.metadata import version
from pathlib import Path

AQUI = Path(__file__).resolve().parent
D2 = AQUI.parent / "D2-mostlyai"
sys.path.insert(0, str(D2))
import d2_mostly_salud as d2  # noqa: E402

ORDEN = {"mimic_47": ["patients", "admissions", "diagnoses_icd", "icustays", "labevents"],
         "synthea_85": ["patients", "encounters", "conditions", "observations"]}
FECHAS = {"admittime", "dischtime", "deathtime", "edregtime", "edouttime", "intime", "outtime", "charttime", "dod",
          "birthdate", "deathdate", "start", "stop", "date"}


class Medidor:
    """Tiempo y memoria máxima del proceso (getrusage; SDV corre en el mismo proceso)."""

    def __enter__(self):
        self.t0 = time.perf_counter()
        return self

    def __exit__(self, *exc):
        import resource
        self.segundos = time.perf_counter() - self.t0
        self.mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2**20
        return False

    def dict(self):
        return {"segundos": round(self.segundos, 1), "memoria_max_proceso_mb": round(self.mb)}


def metadata(cfg, tablas, datos):
    from sdv.metadata import Metadata
    md = Metadata()
    for t in tablas:
        esq, pk, fks, cols, filtro = cfg["tablas"][t]
        md.add_table(t)
        for c in datos[t].columns:
            if c == pk or any(c == f for f, _, _ in fks):
                md.add_column(c, table_name=t, sdtype="id")
            elif c in FECHAS:
                md.add_column(c, table_name=t, sdtype="datetime", datetime_format="%Y-%m-%d %H:%M:%S")
            elif datos[t][c].dtype.kind in "if" and c not in ("icd_version", "hospital_expire_flag", "itemid",
                                                              "seq_num", "anchor_year"):
                md.add_column(c, table_name=t, sdtype="numerical")
            else:
                md.add_column(c, table_name=t, sdtype="categorical")
        if pk:
            md.set_primary_key(pk, table_name=t)
    for t in tablas:
        for c, ref, _ in cfg["tablas"][t][2]:
            if ref in tablas:
                md.add_relationship(parent_table_name=ref, child_table_name=t,
                                    parent_primary_key=cfg["tablas"][ref][1], child_foreign_key=c)
    md.validate()
    return md


def main():
    warnings.filterwarnings("ignore")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--conjunto", choices=ORDEN, required=True)
    ap.add_argument("--tablas", type=int, required=True)
    a = ap.parse_args()
    import pandas as pd
    from sdv.multi_table import HMASynthesizer
    cfg = d2.CONJUNTOS[a.conjunto]
    tablas = ORDEN[a.conjunto][:a.tablas]
    sub = {t: cfg["tablas"][t] for t in tablas}
    real = d2.leer(d2.GRANDES / a.conjunto / "entrada", tablas)
    for df in real.values():   # SDV pide ids sin nulos y fechas como datetime
        for c in df.columns:
            if df[c].dtype == "datetime64[ns]":
                df[c] = df[c].dt.round("s")
    md = metadata(cfg, tablas, real)
    # RDT 1.19.0 (dentro de SDV) falla con OverflowError al codificar una categórica con nulos (UniformEncoder no
    # encuentra el intervalo de NaN). Se reemplazan por una marca para entrenar y se vuelven a nulos al generar.
    NULO = "__NULO__"
    entrenamiento = {}
    for t in tablas:
        df = real[t].copy()
        for c, info in md.tables[t].columns.items():
            if info["sdtype"] == "categorical" and df[c].isna().any():
                df[c] = df[c].astype(object).where(df[c].notna(), NULO)
        entrenamiento[t] = df
    res = {"prueba": f"D3{a.conjunto[0]}", "conjunto": a.conjunto, "tablas": tablas,
           "entorno": {"equipo": f"{platform.machine()}, macOS {platform.mac_ver()[0]}",
                       "python": platform.python_version(), "sdv": version("sdv"), "pandas": version("pandas")},
           "fecha": datetime.datetime.now().isoformat(timespec="seconds")}
    with Medidor() as m:
        s = HMASynthesizer(md)
        s.fit(entrenamiento)
    res["entrenar"] = m.dict()
    print("[entrenar]", res["entrenar"], flush=True)
    with Medidor() as m:
        sint = s.sample(scale=1.0)
    for t, df in sint.items():
        for c in df.columns:
            if df[c].dtype == object:
                df[c] = df[c].where(df[c] != NULO, None)
    res["generar"] = m.dict()
    print("[generar]", res["generar"], flush=True)
    dest = AQUI / "salidas_grandes" / f"{a.conjunto}_{a.tablas}t"
    dest.mkdir(parents=True, exist_ok=True)
    for t, df in sint.items():
        df.to_parquet(dest / f"{t}.parquet", index=False)
    res["filas"] = {"real": {t: len(real[t]) for t in tablas}, "sintetico": {t: len(sint[t]) for t in tablas}}
    res["integridad"] = d2.integridad(sub, sint)
    completo = len(tablas) == len(ORDEN[a.conjunto])
    if completo:   # las reglas cruzan todas las tablas
        res["reglas"] = {"real": d2.reglas(cfg, real), "sintetico": d2.reglas(cfg, sint)}
        res["estadisticas"] = {"real": d2.estadisticas(cfg, real), "sintetico": d2.estadisticas(cfg, sint)}
    else:
        res["reglas"] = {"real": reglas_parciales(real), "sintetico": reglas_parciales(sint)}
    res["copias_exactas"] = d2.copias({"tablas": sub}, real, sint)
    out = AQUI / "resultados"
    out.mkdir(exist_ok=True)
    (out / f"{a.conjunto}_{a.tablas}t.json").write_text(json.dumps(res, indent=2, ensure_ascii=False, default=str),
                                                         encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k not in ("entorno",)}, indent=1, ensure_ascii=False,
                     default=str))


def reglas_parciales(d):
    """Reglas que solo usan las 3 primeras tablas."""
    import pandas as pd
    r = {}
    if "admissions" in d:
        a = d["admissions"]
        r["alta >= ingreso"] = int((a.dischtime < a.admittime).sum())
        m = a.deathtime.notna()
        r["muerte dentro de la internación"] = int((m & ((a.deathtime < a.admittime) |
                                                      (a.deathtime > a.dischtime + pd.Timedelta(days=1)))).sum())
        r["muerte en el hospital <=> hospital_expire_flag"] = int(((a.hospital_expire_flag == 1) != m).sum())
    else:
        p, e, c = d["patients"], d["encounters"], d["conditions"]
        r["encuentro: fin >= inicio"] = int((e.stop < e.start).sum())
        x = e.merge(p[["id", "birthdate"]], left_on="patient", right_on="id", suffixes=("", "_p"))
        r["encuentro después del nacimiento"] = int((x.start.dt.normalize() < x.birthdate).sum())
        r["condición: fin >= inicio"] = int((c.stop.notna() & (c.stop < c.start)).sum())
    return r


if __name__ == "__main__":
    main()
