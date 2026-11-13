#!/usr/bin/env python3
"""E3m / E3s: el evaluador de E3 adaptado a las bases de salud, para comparar las salidas de B (anonimizada) y D
(sintéticas) con la misma vara.

Cambios respecto de pruebas/E3-chequeos-propios/evaluar_bd.py (que no se toca):
  - registro «paciente» en lugar de «persona» (MIMIC: sexo, edad, raza, seguro, idioma, estado civil; Synthea:
    sexo, edad, raza, etnia, estado civil, condado); el secreto de Anonymeter es el diagnóstico (MIMIC: grupo del
    diagnóstico principal; Synthea: primera condición);
  - bloque de reglas de negocio (las de la etapa 3) y de códigos válidos (CIE o SNOMED que existen en el catálogo);
  - lee Parquet (la entrada y las salidas de D2/D3) y exporta de PostgreSQL las anonimizadas (B1) y el control;
  - modo sin valores: todo lo que escribe son conteos, métricas y nombres de columnas; ninguna fila.

Bloques (con su tiempo):
  1. integridad, reglas y códigos válidos;
  2. calidad: SDMetrics QualityReport multitabla (formas de columnas, tendencias de pares, cardinalidad);
  3. privacidad del registro «paciente»: Anonymeter (singling out, linkability, inference) contra los pacientes de
     control, y DCR (distancia de Gower al registro real más cercano, con el control como referencia);
  4. riesgo con ARX: pacientes únicos y riesgo máximo por los cuasi-identificadores (modelo del fiscal).

Uso:  .venv/bin/python pruebas/salud/E3-evaluador/e3_salud.py --entrenamiento mimic_47
Salida: resultados/<entrenamiento>.json y .md
"""
import argparse
import datetime
import json
import subprocess
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import sqlalchemy as sa

AQUI = Path(__file__).resolve().parent
SALUD = AQUI.parent
sys.path.insert(0, str(SALUD / "D2-mostlyai"))
sys.path.insert(0, str(SALUD / "D3-sdv"))
sys.path.insert(0, str(SALUD / "B3-arx"))
import d2_mostly_salud as d2  # noqa: E402

PG = "postgresql+psycopg2://postgres:postgres@127.0.0.1:{puerto}/{db}"
CONTROL = "hashtext('control' || {k}::text) % 5 = 0"
ENTRENAMIENTOS = {
    "mimic_47": dict(origen="mimic_demo", candidatas={
        "B1 anonimizada (PostgreSQL Anonymizer)": ("pg", 55434, "b1m_consistentes"),
        "D2 sintética (MOSTLY AI)": ("parquet", SALUD / "D2-mostlyai/salidas_grandes/mimic_47/sintetico_47"),
        "D3 sintética (SDV HMA, 5 tablas)": ("parquet", SALUD / "D3-sdv/salidas_grandes/mimic_47_5t")}),
    "synthea_85": dict(origen="synthea_p1000", candidatas={
        "B1 anonimizada (PostgreSQL Anonymizer)": ("pg", 55434, "b1s_consistentes"),
        "D2 sintética (MOSTLY AI)": ("parquet", SALUD / "D2-mostlyai/salidas_grandes/synthea_85/sintetico_85"),
        "D3 sintética (SDV HMA, 4 tablas)": ("parquet", SALUD / "D3-sdv/salidas_grandes/synthea_85_4t")}),
    "synthea_925": dict(origen="synthea_p1000", candidatas={
        "D2 sintética (MOSTLY AI)": ("parquet", SALUD / "D2-mostlyai/salidas_grandes/synthea_925/sintetico_925")}),
}
CUASI = {"mimic": ["sexo", "edad", "raza", "seguro", "idioma", "estado_civil"],
         "synthea": ["sexo", "edad", "raza", "etnia", "estado_civil", "condado"]}
SECRETO = {"mimic": "diagnostico", "synthea": "condicion"}


# ----------------------------------------------------------------------------- datos

def de_pg(puerto, db, tablas, filtro_control=None, solo_control=False):
    """Lee las tablas (mismas columnas que la exportación de D2) de una base. Con solo_control, solo los pacientes de
    control (para el conjunto de control de Anonymeter)."""
    eng = sa.create_engine(PG.format(puerto=puerto, db=db))
    d = {}
    with eng.connect() as c:
        for t, (esq, pk, fks, cols, filtro) in tablas.items():
            cond = [filtro] if filtro else []
            if solo_control:
                cond.append(filtro_control[t])
            where = (" where " + " and ".join(cond)) if cond else ""
            d[t] = pd.read_sql(sa.text(f"select {', '.join(cols)} from {esq}.{t}{where}"), c)
    for df in d.values():
        for col in df.columns:
            if col in ("admittime", "dischtime", "deathtime", "edregtime", "edouttime", "intime", "outtime",
                       "charttime", "dod", "birthdate", "deathdate", "start", "stop", "date"):
                df[col] = pd.to_datetime(df[col].replace("", None), utc=True).dt.tz_localize(None)
            elif df[col].dtype == object or str(df[col].dtype).startswith(("string", "str")):
                # char(n) de MIMIC: códigos con espacios a la derecha (igual que d2.leer)
                df[col] = df[col].astype(object).where(df[col].isna(), df[col].astype(str).str.strip())
    return d


def filtros_control(base):
    if base == "mimic":
        k = CONTROL.format(k="subject_id")
        return {"patients": k, "admissions": k, "labevents": k,
                "diagnoses_icd": f"hadm_id in (select hadm_id from mimiciv_hosp.admissions where {k})",
                "icustays": f"hadm_id in (select hadm_id from mimiciv_hosp.admissions where {k})"}
    k = CONTROL.format(k="patient")
    enc = f"encounter in (select id from synthea.encounters where {k})"
    return {"patients": CONTROL.format(k="id"), "encounters": k, "conditions": enc, "observations": enc}


def registro_paciente(base, d):
    """Una fila por paciente: cuasi-identificadores + secreto."""
    if base == "mimic":
        p, a, dx = d["patients"], d["admissions"], d["diagnoses_icd"]
        a1 = a.sort_values("admittime").groupby("subject_id").head(1)
        dx1 = dx.sort_values("seq_num").groupby("hadm_id").head(1)
        dx1 = dx1.assign(diagnostico=dx1.icd_version.astype(str) + "-" + dx1.icd_code.astype(str).str[:1])
        r = p.merge(a1, on="subject_id", how="left").merge(dx1[["hadm_id", "diagnostico"]], on="hadm_id", how="left")
        out = pd.DataFrame({"sexo": r.gender, "edad": r.anchor_age, "raza": r.race, "seguro": r.insurance,
                            "idioma": r.language, "estado_civil": r.marital_status, "diagnostico": r.diagnostico})
    else:
        p, e, c = d["patients"], d["encounters"], d["conditions"]
        ce = c.merge(e[["id", "patient"]], left_on="encounter", right_on="id")
        c1 = ce.sort_values(["start", "description"]).groupby("patient").head(1)
        r = p.merge(c1[["patient", "description"]], left_on="id", right_on="patient", how="left")
        edad = ((pd.Timestamp("2026-01-01") - r.birthdate).dt.days // 365.25)
        out = pd.DataFrame({"sexo": r.gender, "edad": edad, "raza": r.race, "etnia": r.ethnicity,
                            "estado_civil": r.marital, "condado": r.county, "condicion": r.description})
    out["edad"] = pd.to_numeric(out.edad, errors="coerce").astype(float)   # sin enteros con nulos (numba de anonymeter)
    for c in out.columns:
        if c != "edad":
            out[c] = out[c].fillna("NA").astype(str)
    return out.fillna({"edad": -1})


def catalogo(base):
    eng = sa.create_engine(PG.format(puerto=55432, db="mimic_demo" if base == "mimic" else "synthea_p1000"))
    with eng.connect() as c:
        if base == "mimic":
            return {(str(v), str(k).strip()) for k, v in c.execute(sa.text(
                "select icd_code, icd_version from mimiciv_hosp.d_icd_diagnoses"))}
        return {str(x[0]) for x in c.execute(sa.text("select distinct code from synthea.conditions"))}


def codigos_validos(base, d, cat):
    if base == "mimic":
        x = d["diagnoses_icd"]
        # la versión puede venir como decimal («9.0») en las sintéticas: se normaliza a entero
        ver = pd.to_numeric(x.icd_version, errors="coerce")
        ok = [(str(int(v)) if v == v else "", str(k).strip()) in cat for k, v in zip(x.icd_code, ver)]
        return {"filas": len(x), "codigos_validos": int(sum(ok)), "pct": round(100 * np.mean(ok), 1) if len(x) else None}
    x = d["conditions"]
    ok = x.code.astype(str).isin(cat)
    return {"filas": len(x), "codigos_validos": int(ok.sum()), "pct": round(100 * ok.mean(), 1) if len(x) else None}


# ----------------------------------------------------------------------------- bloques

def calidad(cfg_d2, real, cand):
    from sdmetrics.reports.multi_table import QualityReport
    import d3_sdv_salud as d3
    md = d3.metadata(cfg_d2, list(cfg_d2["tablas"]), real).to_dict()
    rep = QualityReport()
    r2 = {t: real[t].copy() for t in real}
    c2 = {t: cand[t][[c for c in real[t].columns if c in cand[t].columns]].copy() for t in real}
    rep.generate(r2, c2, md, verbose=False)
    props = rep.get_properties()
    return {"puntaje": round(rep.get_score(), 3),
            "propiedades": {r["Property"]: round(r["Score"], 3) for _, r in props.iterrows()}}


def gower_min(A, B, num, cat, rangos):
    out = np.empty(len(A))
    for i in range(0, len(A), 400):
        a = A.iloc[i:i + 400]
        dist = np.zeros((len(a), len(B)))
        for c in num:
            dist += np.abs(a[c].to_numpy()[:, None] - B[c].to_numpy()[None, :]) / (rangos[c] or 1)
        for c in cat:
            dist += (a[c].to_numpy()[:, None] != B[c].to_numpy()[None, :])
        out[i:i + 400] = (dist / (len(num) + len(cat))).min(axis=1)
    return out


def privacidad(base, ori, syn, ctrl, n_ataques, avisos):
    from anonymeter.evaluators import InferenceEvaluator, LinkabilityEvaluator, SinglingOutEvaluator
    cuasi, secreto = CUASI[base], SECRETO[base]
    cols = cuasi + [secreto]
    ori, syn, ctrl = ori[cols], syn[cols], ctrl[cols]
    n = int(min(n_ataques, len(ctrl), len(ori), len(syn)))
    out = {"n_ataques": n, "filas_original": len(ori), "filas_candidata": len(syn), "filas_control": len(ctrl)}
    # Misma forma de llamar que E3 sobre Pagila (anonymeter 1.1.0: argumentos por nombre, evaluate con modo).
    ataques = [("singling_out", lambda: SinglingOutEvaluator(ori=ori, syn=syn, control=ctrl, n_attacks=n, seed=1)
                .evaluate(mode="univariate")),
               ("linkability", lambda: LinkabilityEvaluator(ori=ori, syn=syn, control=ctrl, n_attacks=n,
                                                             aux_cols=(cuasi[:3], cuasi[3:])).evaluate(n_jobs=1)),
               ("inference", lambda: InferenceEvaluator(ori=ori, syn=syn, control=ctrl, aux_cols=cuasi,
                                                         secret=secreto, n_attacks=n).evaluate(n_jobs=1))]
    for nombre, f in ataques:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                ev = f()
                r, rr = ev.risk(), ev.results()
            out[nombre] = {"riesgo": round(r.value, 3), "ic95": [round(r.ci[0], 3), round(r.ci[1], 3)],
                           "tasa_ataque": round(rr.attack_rate.value, 3), "tasa_azar": round(rr.baseline_rate.value, 3),
                           "tasa_control": round(rr.control_rate.value, 3),
                           "concluyente": bool(rr.attack_rate.value > rr.baseline_rate.value)}
        except Exception as e:
            out[nombre] = {"error": f"{type(e).__name__}: {str(e)[:150]}"}
            avisos.append(f"anonymeter {nombre}: {type(e).__name__}")
    num, cat = ["edad"], [c for c in cols if c != "edad"]
    todo = pd.concat([ori, syn, ctrl])
    rangos = {"edad": float(todo.edad.max() - todo.edad.min())}
    d_syn, d_ctrl = gower_min(syn, ori, num, cat, rangos), gower_min(ctrl, ori, num, cat, rangos)
    out["dcr"] = {"copias_exactas_pct": round(100 * float(np.mean(d_syn == 0)), 1),
                  "mediana_candidata": round(float(np.median(d_syn)), 3),
                  "mediana_control": round(float(np.median(d_ctrl)), 3),
                  "pct_candidata_mas_cerca_que_p5_control": round(100 * float(np.mean(d_syn < np.percentile(d_ctrl, 5))), 1)}
    return out


def riesgo_arx(base, nombre, reg):
    """Mide con ARX (ArxMedidor de B3m/B3s) el riesgo del registro, sin generalizar: únicos y riesgo máximo."""
    import b3_arx_salud as b3
    cuasi = CUASI[base]
    d = SALUD / "B3-arx" / "salidas_grandes" / f"e3_{nombre}"
    d.mkdir(parents=True, exist_ok=True)
    reg = reg.copy()
    reg.insert(0, "id", range(len(reg)))
    reg["edad"] = reg.edad.astype(int).astype(str)
    reg = reg.replace(";", ",", regex=True)
    reg.to_csv(d / f"{nombre}.csv", sep=";", index=False)
    for c in cuasi:
        j = b3.jerarquia(c, reg[c].tolist()) if c in ("edad", "raza") else [[v, "*"] for v in sorted(set(reg[c]))]
        (d / f"jerarquia_{c}.csv").write_text("\n".join(";".join(x) for x in j) + "\n", encoding="utf-8")
    cmd = (f"java -Xmx2g -cp salidas_grandes/lib/libarx-3.9.2.jar:salidas_grandes/clases ArxMedidor "
           f"salidas_grandes/e3_{nombre} {nombre} 2 1 0.1 {','.join(cuasi)} {SECRETO[base]}")
    r = subprocess.run(["docker", "run", "--rm", "-v", f"{SALUD / 'B3-arx'}:/b3", "-w", "/b3", "eclipse-temurin:21-jdk",
                        "sh", "-c", cmd], capture_output=True, text=True)
    if r.returncode != 0:
        return {"error": r.stderr[-300:]}
    m = json.loads(r.stdout.strip().splitlines()[-1])
    return {"fraccion_unicos": round(m["riesgo_antes"]["fraccion_unicos"], 3),
            "riesgo_maximo": round(m["riesgo_antes"]["riesgo_maximo"], 3),
            "riesgo_promedio": round(m["riesgo_antes"]["riesgo_promedio"], 3),
            "k2_suprimidos": m.get("filas_suprimidas"), "k2_niveles": m.get("nivel_por_cuasi_identificador")}


# ----------------------------------------------------------------------------- principal

def main():
    warnings.filterwarnings("ignore")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--entrenamiento", choices=ENTRENAMIENTOS, required=True)
    ap.add_argument("--n-ataques", type=int, default=200)
    a = ap.parse_args()
    cfg = ENTRENAMIENTOS[a.entrenamiento]
    base = a.entrenamiento.split("_")[0]
    cfg_d2 = d2.CONJUNTOS[a.entrenamiento]
    tablas = cfg_d2["tablas"]
    real = d2.leer(d2.GRANDES / a.entrenamiento / "entrada", tablas)
    ctrl = de_pg(55432, cfg["origen"], tablas, filtros_control(base), solo_control=True)
    cat = catalogo(base)
    reg_real, reg_ctrl = registro_paciente(base, real), registro_paciente(base, ctrl)
    avisos = []
    res = {"entrenamiento": a.entrenamiento, "fecha": datetime.datetime.now().isoformat(timespec="minutes"),
           "pacientes_entrenamiento": len(reg_real), "pacientes_control": len(reg_ctrl),
           "real": {"reglas": d2.reglas(cfg_d2, real), "codigos": codigos_validos(base, real, cat),
                    "riesgo_arx": riesgo_arx(base, f"{a.entrenamiento}_real", reg_real)},
           "candidatas": {}}
    for nombre, fuente in cfg["candidatas"].items():
        if fuente[0] == "parquet" and not fuente[1].exists():
            avisos.append(f"{nombre}: no existe {fuente[1]}")
            continue
        t0 = time.time()
        cand = d2.leer(fuente[1], tablas) if fuente[0] == "parquet" else de_pg(fuente[1], fuente[2], tablas)
        r = {"filas": {t: len(df) for t, df in cand.items()}}
        t = time.time()
        r["integridad"] = d2.integridad(tablas, cand)
        r["reglas"] = d2.reglas(cfg_d2, cand)
        r["codigos"] = codigos_validos(base, cand, cat)
        r["segundos_bloque1"] = round(time.time() - t, 1)
        t = time.time()
        try:
            r["calidad"] = calidad(cfg_d2, real, cand)
        except Exception as e:
            r["calidad"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
        r["segundos_bloque2"] = round(time.time() - t, 1)
        t = time.time()
        reg = registro_paciente(base, cand)
        r["privacidad"] = privacidad(base, reg_real, reg, reg_ctrl, a.n_ataques, avisos)
        r["segundos_bloque3"] = round(time.time() - t, 1)
        t = time.time()
        corto = nombre.split()[0].lower()
        r["riesgo_arx"] = riesgo_arx(base, f"{a.entrenamiento}_{corto}", reg)
        r["segundos_bloque4"] = round(time.time() - t, 1)
        r["segundos_total"] = round(time.time() - t0, 1)
        res["candidatas"][nombre] = r
        print(f"[{a.entrenamiento}] {nombre}: {r['segundos_total']} s", flush=True)
    res["avisos"] = avisos
    out = AQUI / "resultados"
    out.mkdir(exist_ok=True)
    (out / f"{a.entrenamiento}.json").write_text(json.dumps(res, indent=2, ensure_ascii=False, default=str),
                                                 encoding="utf-8")
    print(json.dumps(res, indent=1, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
