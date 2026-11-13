#!/usr/bin/env python3
"""D2m / D2s: MOSTLY AI (SDK local) genera versiones sintéticas multitabla de MIMIC-IV demo y Synthea.

Conjuntos de entrenamiento:
  mimic_47      subconjunto mimic_c1_50 (C1m): 47 pacientes, 5 tablas.
  synthea_85    subconjunto synthea_c1_10 (C1s): 85 pacientes, 4 tablas.
  synthea_925   synthea_p1000 sin los pacientes de control: 925 pacientes, ~1,8 millones de filas (escala).
Escalones de generación (solo mimic_47): 47, 1 000, 5 000 y 10 000 pacientes sintéticos, para ver dónde se acaba la
memoria en 16 GB al generar.

Pasos, en dos entornos de Python (mostlyai 6.1 y el lock del repo no pueden convivir, ver D2 sobre Pagila):
  exportar  [.venv del repo]          lee la base y deja un Parquet por tabla en salidas_grandes/<conjunto>/entrada
  entrenar  [../.venv, el de MOSTLY]  entrena, genera cada escalón, guarda Parquet sintéticos y métricas de MOSTLY
  evaluar   [.venv del repo]          integridad, reglas de coherencia y distribuciones, real contra sintético

Los Parquet (reales y sintéticos) quedan en salidas_grandes/, fuera del repo. Al repo van solo métricas.
Uso:
  .venv/bin/python pruebas/salud/D2-mostlyai/d2_mostly_salud.py exportar --conjunto mimic_47
  ../.venv/bin/python pruebas/salud/D2-mostlyai/d2_mostly_salud.py entrenar --conjunto mimic_47
  .venv/bin/python pruebas/salud/D2-mostlyai/d2_mostly_salud.py evaluar --conjunto mimic_47
"""
import argparse
import datetime
import json
import os
import platform
import sys
import threading
import time
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

AQUI = Path(__file__).resolve().parent
GRANDES = AQUI / "salidas_grandes"
RESULTADOS = AQUI / "resultados"
CONTROL = "hashtext('control' || {k}::text) % 5 = 0"

MIMIC = {   # tabla: (esquema, pk, [(fk, tabla_padre, contexto)], columnas, filtro)
    "patients": ("mimiciv_hosp", "subject_id", [], ["subject_id", "gender", "anchor_age", "anchor_year",
                                                    "anchor_year_group", "dod"], None),
    "admissions": ("mimiciv_hosp", "hadm_id", [("subject_id", "patients", True)],
                   ["hadm_id", "subject_id", "admittime", "dischtime", "deathtime", "admission_type",
                    "admission_location", "discharge_location", "insurance", "language", "marital_status", "race",
                    "edregtime", "edouttime", "hospital_expire_flag"], None),
    "diagnoses_icd": ("mimiciv_hosp", None, [("hadm_id", "admissions", True)],
                      ["hadm_id", "seq_num", "icd_code", "icd_version"], None),
    "icustays": ("mimiciv_icu", "stay_id", [("hadm_id", "admissions", True)],
                 ["stay_id", "hadm_id", "first_careunit", "last_careunit", "intime", "outtime", "los"], None),
    "labevents": ("mimiciv_hosp", None, [("subject_id", "patients", True)],
                  ["subject_id", "itemid", "charttime", "valuenum", "valueuom", "flag"], None),
}
SYNTHEA = {
    "patients": ("synthea", "id", [], ["id", "birthdate", "deathdate", "gender", "race", "ethnicity", "marital",
                                       "county", "income"], None),
    "encounters": ("synthea", "id", [("patient", "patients", True)],
                   ["id", "patient", "start", "stop", "encounterclass", "code", "description", "base_encounter_cost",
                    "reasoncode"], None),
    "conditions": ("synthea", None, [("encounter", "encounters", True)],
                   ["encounter", "start", "stop", "code", "description"], None),
    "observations": ("synthea", None, [("encounter", "encounters", True)],
                     ["encounter", "date", "category", "code", "description", "value", "units", "type"],
                     "encounter is not null"),
}
CONJUNTOS = {
    "mimic_47": dict(base="mimic_c1_50", tablas=MIMIC, raiz="patients", escalones=[47, 1000, 5000, 10000]),
    "synthea_85": dict(base="synthea_c1_10", tablas=SYNTHEA, raiz="patients", escalones=[85]),
    "synthea_925": dict(base="synthea_p1000", tablas=SYNTHEA, raiz="patients", escalones=[925],
                        sin_control="id"),
}


class Medidor:
    """Tiempo y memoria máxima (proceso + subprocesos, con psutil cada 0,25 s)."""

    def __init__(self):
        import psutil
        self.psutil, self.pico, self._parar = psutil, 0, threading.Event()

    def _rss(self):
        p = self.psutil.Process()
        total = p.memory_info().rss
        for h in p.children(recursive=True):
            try:
                total += h.memory_info().rss
            except Exception:
                pass
        return total

    def _bucle(self):
        while not self._parar.is_set():
            try:
                self.pico = max(self.pico, self._rss())
            except Exception:
                pass
            self._parar.wait(0.25)

    def __enter__(self):
        self.t0 = time.perf_counter()
        self._hilo = threading.Thread(target=self._bucle, daemon=True)
        self._hilo.start()
        return self

    def __exit__(self, *exc):
        self._parar.set()
        self._hilo.join()
        self.segundos = time.perf_counter() - self.t0
        return False

    def dict(self):
        return {"segundos": round(self.segundos, 1), "memoria_max_mb": round(self.pico / 2**20)}


def ver(p):
    try:
        return version(p)
    except PackageNotFoundError:
        return None


def entorno():
    return {"equipo": f"{platform.machine()}, macOS {platform.mac_ver()[0]}", "python": platform.python_version(),
            "paquetes": {p: ver(p) for p in ("mostlyai", "mostlyai-engine", "torch", "pandas", "numpy")
                         if ver(p)}}


def guardar(conjunto, clave, datos):
    RESULTADOS.mkdir(parents=True, exist_ok=True)
    ruta = RESULTADOS / f"{conjunto}.json"
    todo = json.loads(ruta.read_text()) if ruta.exists() else {}
    todo[clave] = {**datos, "registrado": f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S}"}
    ruta.write_text(json.dumps(todo, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


# ----------------------------------------------------------------------------- exportar

def exportar(a):
    import pandas as pd
    import sqlalchemy as sa
    cfg = CONJUNTOS[a.conjunto]
    dest = GRANDES / a.conjunto / "entrada"
    dest.mkdir(parents=True, exist_ok=True)
    eng = sa.create_engine(f"postgresql+psycopg2://postgres:postgres@127.0.0.1:55432/{cfg['base']}")
    filas = {}
    t0 = time.time()
    with eng.connect() as c:
        for t, (esq, pk, fks, cols, filtro) in cfg["tablas"].items():
            cond = [filtro] if filtro else []
            if cfg.get("sin_control"):
                k = cfg["sin_control"]
                if t == cfg["raiz"]:
                    cond.append("not " + CONTROL.format(k=k))
                else:   # filas cuyo paciente no es de control (todas las tablas de Synthea llegan al paciente)
                    col_pac = "patient" if "patient" in cols else None
                    if col_pac:
                        cond.append("not " + CONTROL.format(k=col_pac))
                    else:
                        cond.append(f"encounter in (select id from {esq}.encounters where not "
                                    f"{CONTROL.format(k='patient')})")
            where = (" where " + " and ".join(cond)) if cond else ""
            df = pd.read_sql(sa.text(f"select {', '.join(cols)} from {esq}.{t}{where}"), c)
            for col in df.columns:   # fechas de Synthea como texto ISO -> datetime sin zona
                if df[col].dtype == object and col in ("birthdate", "deathdate", "start", "stop", "date"):
                    df[col] = pd.to_datetime(df[col].replace("", None), utc=True).dt.tz_localize(None)
            df.to_parquet(dest / f"{t}.parquet", index=False)
            filas[t] = len(df)
    guardar(a.conjunto, "exportar", {"base": cfg["base"], "filas": filas, "segundos": round(time.time() - t0, 1)})
    print(a.conjunto, filas)


# ----------------------------------------------------------------------------- entrenar

def entrenar(a):
    import shutil
    import warnings
    warnings.filterwarnings("ignore")
    import pandas as pd
    from mostlyai.sdk import MostlyAI
    cfg = CONJUNTOS[a.conjunto]
    base = GRANDES / a.conjunto
    datos = {t: pd.read_parquet(base / "entrada" / f"{t}.parquet") for t in cfg["tablas"]}
    local_dir = base / "mostly_local"
    if local_dir.exists():
        shutil.rmtree(local_dir)
    mostly = MostlyAI(local=True, local_dir=str(local_dir), quiet=True)
    tablas = []
    for t, (esq, pk, fks, cols, filtro) in cfg["tablas"].items():
        d = {"name": t, "data": datos[t], "tabular_model_configuration": {"max_training_time": a.max_minutos}}
        if pk:
            d["primary_key"] = pk
        if fks:
            d["foreign_keys"] = [{"column": c, "referenced_table": r, "is_context": ctx} for c, r, ctx in fks]
        tablas.append(d)
    with Medidor() as m:
        g = mostly.train(config={"name": f"d2-{a.conjunto}", "tables": tablas}, start=True, wait=True)
    metricas = {}
    for t in g.tables:
        mm = t.tabular_model_metrics
        if mm is not None:
            metricas[t.name] = {"accuracy": mm.accuracy.overall, "coherencia": mm.accuracy.coherence,
                                "dcr_share": mm.distances.dcr_share,
                                "discriminador_auc": mm.similarity.discriminator_auc_training_synthetic}
    guardar(a.conjunto, "entrenar", {**m.dict(), "max_minutos_por_tabla": a.max_minutos,
                                     "accuracy_global": getattr(g, "accuracy", None), "metricas_por_tabla": metricas,
                                     "filas_entrada": {t: len(d) for t, d in datos.items()}, "entorno": entorno()})
    print(f"[entrenar] {m.segundos:.0f} s, {m.pico / 2**30:.1f} GB", flush=True)

    for n in cfg["escalones"]:
        try:
            with Medidor() as m:
                sd = mostly.generate(g, size=n, start=True, wait=True)
                sint = sd.data()
            dest = base / f"sintetico_{n}"
            dest.mkdir(parents=True, exist_ok=True)
            for t, df in sint.items():
                df.to_parquet(dest / f"{t}.parquet", index=False)
            guardar(a.conjunto, f"generar_{n}", {**m.dict(), "filas": {t: len(df) for t, df in sint.items()}})
            print(f"[generar {n}] {m.segundos:.0f} s, {m.pico / 2**30:.1f} GB", flush=True)
        except Exception as e:
            guardar(a.conjunto, f"generar_{n}", {"error": f"{type(e).__name__}: {str(e)[:500]}"})
            print(f"[generar {n}] error {type(e).__name__}", flush=True)
    os._exit(0)


# ----------------------------------------------------------------------------- evaluar

def reglas(base_cfg, d):
    """Violaciones de reglas de negocio (las de la etapa 3 y las de B1). d: tabla -> DataFrame."""
    import pandas as pd
    r = {}
    un_dia = pd.Timedelta(days=1)
    if "admissions" in d:
        p, a, i = d["patients"], d["admissions"], d["icustays"]
        r["alta >= ingreso"] = int((a.dischtime < a.admittime).sum())
        m = a.deathtime.notna()
        r["muerte dentro de la internación"] = int((m & ((a.deathtime < a.admittime) |
                                                      (a.deathtime > a.dischtime + un_dia))).sum())
        r["muerte en el hospital <=> hospital_expire_flag"] = int(((a.hospital_expire_flag == 1) != m).sum())
        r["emergencia: salida >= registro"] = int((a.edouttime < a.edregtime).sum())
        x = i.merge(a[["hadm_id", "admittime", "dischtime"]], on="hadm_id")
        r["UCI dentro de la internación"] = int(((x.intime < x.admittime - un_dia) |
                                                 (x.outtime > x.dischtime + un_dia)).sum())
        r["UCI: salida >= entrada"] = int((i.outtime < i.intime).sum())
        y = a[m].merge(p[["subject_id", "dod"]], on="subject_id")
        r["dod = día de la muerte"] = int((pd.to_datetime(y.dod) != y.deathtime.dt.normalize()).sum())
        z = a.merge(p[["subject_id", "anchor_age", "anchor_year"]], on="subject_id")
        edad = z.anchor_age + (z.admittime.dt.year - z.anchor_year)
        r["edad en la internación >= 18"] = int((edad < 18).sum())
        r["estadía UCI: los = salida - entrada (±0,01 días)"] = int(
            (((i.outtime - i.intime).dt.total_seconds() / 86400 - i.los).abs() > 0.01).sum())
    else:
        p, e, c, o = d["patients"], d["encounters"], d["conditions"], d["observations"]
        r["encuentro: fin >= inicio"] = int((e.stop < e.start).sum())
        x = e.merge(p[["id", "birthdate", "deathdate"]], left_on="patient", right_on="id", suffixes=("", "_p"))
        r["encuentro después del nacimiento"] = int((x.start.dt.normalize() < x.birthdate).sum())
        r["encuentro antes de la muerte (+1 día)"] = int((x.deathdate.notna() &
                                                         (x.start.dt.normalize() > x.deathdate + un_dia)).sum())
        r["muerte >= nacimiento"] = int((p.deathdate < p.birthdate).sum())
        r["condición: fin >= inicio"] = int((c.stop.notna() & (c.stop < c.start)).sum())
        y = o.merge(e[["id", "start", "stop"]], left_on="encounter", right_on="id")
        r["observación dentro de su encuentro (±1 día)"] = int(((y.date < y.start - un_dia) |
                                                               (y.date > y.stop + un_dia)).sum())
    return r


def integridad(tablas, d):
    out = {}
    for t, (esq, pk, fks, cols, filtro) in tablas.items():
        if pk:
            out[f"{t}: PK repetidas"] = int(d[t][pk].duplicated().sum())
        for c, ref, _ in fks:
            out[f"{t}.{c} sin padre"] = int((~d[t][c].isin(d[ref][tablas[ref][1]]) & d[t][c].notna()).sum())
    return out


def estadisticas(cfg, d):
    import pandas as pd
    s = {}
    if "admissions" in d:
        p, a, dx, lab = d["patients"], d["admissions"], d["diagnoses_icd"], d["labevents"]
        s["pacientes"] = len(p)
        s["internaciones por paciente"] = round(len(a) / max(len(p), 1), 2)
        s["diagnósticos por internación"] = round(len(dx) / max(len(a), 1), 2)
        s["laboratorios por paciente"] = round(len(lab) / max(len(p), 1), 1)
        s["% mujeres"] = round(100 * (p.gender == "F").mean(), 1)
        s["edad (anchor_age) mediana"] = float(p.anchor_age.median())
        s["duración de la internación, mediana (días)"] = round(
            ((a.dischtime - a.admittime).dt.total_seconds() / 86400).median(), 2)
        s["% internaciones con muerte"] = round(100 * a.deathtime.notna().mean(), 1)
        s["códigos CIE distintos"] = int(dx.icd_code.nunique())
    else:
        p, e, c, o = d["patients"], d["encounters"], d["conditions"], d["observations"]
        s["pacientes"] = len(p)
        s["encuentros por paciente"] = round(len(e) / max(len(p), 1), 1)
        s["condiciones por paciente"] = round(len(c) / max(len(p), 1), 1)
        s["observaciones por encuentro"] = round(len(o) / max(len(e), 1), 2)
        s["% mujeres"] = round(100 * (p.gender == "F").mean(), 1)
        edad = (pd.Timestamp("2026-01-01") - p.birthdate).dt.days / 365.25
        s["edad mediana"] = round(float(edad.median()), 1)
        s["% fallecidos"] = round(100 * p.deathdate.notna().mean(), 1)
        s["duración del encuentro, mediana (horas)"] = round(
            ((e.stop - e.start).dt.total_seconds() / 3600).median(), 2)
        s["códigos de condición distintos"] = int(c.code.nunique())
    return s


def leer(carpeta, tablas):
    import pandas as pd
    d = {t: pd.read_parquet(carpeta / f"{t}.parquet") for t in tablas}
    for df in d.values():
        for col in df.columns:
            if col in ("admittime", "dischtime", "deathtime", "edregtime", "edouttime", "intime", "outtime",
                       "charttime", "dod", "birthdate", "deathdate", "start", "stop", "date"):
                # todo a UTC sin zona (MOSTLY a veces devuelve fechas con zona y otras sin)
                df[col] = pd.to_datetime(df[col], utc=True, errors="coerce").dt.tz_localize(None).astype("datetime64[ns]")
            elif df[col].dtype == object or str(df[col].dtype).startswith(("string", "str")):
                # MIMIC usa char(n) (códigos CIE con espacios a la derecha); los sintéticos vienen sin espacios
                df[col] = df[col].astype(object).where(df[col].isna(), df[col].astype(str).str.strip())
    return d


def evaluar(a):
    cfg = CONJUNTOS[a.conjunto]
    base = GRANDES / a.conjunto
    real = leer(base / "entrada", cfg["tablas"])
    res = {"real": {"reglas": reglas(cfg, real), "integridad": integridad(cfg["tablas"], real),
                    "estadisticas": estadisticas(cfg, real)}}
    for n in cfg["escalones"]:
        carpeta = base / f"sintetico_{n}"
        if not carpeta.exists():
            continue
        s = leer(carpeta, cfg["tablas"])
        res[f"sintetico_{n}"] = {"reglas": reglas(cfg, s), "integridad": integridad(cfg["tablas"], s),
                                 "estadisticas": estadisticas(cfg, s),
                                 "filas": {t: len(df) for t, df in s.items()}}
        if n == cfg["escalones"][0]:
            res[f"sintetico_{n}"]["copias_exactas"] = copias(cfg, real, s)
    guardar(a.conjunto, "evaluar", res)
    print(json.dumps(res, indent=1, ensure_ascii=False, default=str))


def copias(cfg, real, s):
    """Filas sintéticas idénticas a una real (sin contar ids generados), por tabla."""
    out = {}
    for t, (esq, pk, fks, cols, filtro) in cfg["tablas"].items():
        quitar = {pk} | {c for c, _, _ in fks}
        usar = [c for c in cols if c not in quitar]
        r = real[t][usar].drop_duplicates()
        m = s[t][usar].merge(r, on=usar, how="inner")
        out[t] = {"filas_sinteticas": len(s[t]), "identicas_a_una_real": len(m), "columnas_comparadas": len(usar)}
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paso", choices=["exportar", "entrenar", "evaluar"])
    ap.add_argument("--conjunto", choices=CONJUNTOS, required=True)
    ap.add_argument("--max-minutos", type=float, default=10)
    a = ap.parse_args()
    {"exportar": exportar, "entrenar": entrenar, "evaluar": evaluar}[a.paso](a)


if __name__ == "__main__":
    main()
