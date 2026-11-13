#!/usr/bin/env python3
"""F1m / F1s: utilidad para testing y análisis. Consultas de referencia sobre la base real, la anonimizada (B1) y las
sintéticas (D2 MOSTLY AI, D3 SDV); se compara el resultado de cada consulta con el de la real.

Métrica por consulta:
  - escalar (un número): error relativo |candidata - real| / |real|;
  - ranking (top 10): solapamiento del top 10 con el de la real (cuántos de los 10 coinciden);
  - distribución (proporciones por categoría): distancia de variación total (0 = igual, 1 = disjuntas);
  - ¿la consulta corre? (si la candidata rompe algo, por ejemplo fechas, la consulta da un resultado absurdo).
Una consulta «se conserva» si: error relativo <= 20 %, solapamiento >= 5 de 10, o variación total <= 0,2.

Uso:  .venv/bin/python pruebas/salud/F1-utilidad/f1_utilidad.py --entrenamiento mimic_47
Salida: resultados/<entrenamiento>.json y .md (solo resultados agregados de las consultas, nunca filas).
"""
import argparse
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
SALUD = AQUI.parent
sys.path.insert(0, str(SALUD / "D2-mostlyai"))
sys.path.insert(0, str(SALUD / "E3-evaluador"))
import d2_mostly_salud as d2  # noqa: E402
import e3_salud as e3  # noqa: E402

UMBRAL = {"escalar": 0.2, "ranking": 5, "distribucion": 0.2}


def dias(a, b):
    return (b - a).dt.total_seconds() / 86400


def consultas_mimic(d):
    p, a, dx, icu, lab = d["patients"], d["admissions"], d["diagnoses_icd"], d["icustays"], d["labevents"]
    pa = a.merge(p[["subject_id", "anchor_age", "gender"]], on="subject_id")
    grupo = pd.cut(pa.anchor_age, [0, 40, 60, 80, 200], labels=["<40", "40-59", "60-79", "80+"], right=False)
    muere = pa.deathtime.notna()
    return {
        "Pacientes por diagnóstico (top 10 códigos CIE)": ("ranking",
            dx.merge(a[["hadm_id", "subject_id"]], on="hadm_id").groupby("icd_code").subject_id.nunique()
              .sort_values(ascending=False).head(10).index.tolist()),
        "Diagnóstico principal más frecuente (top 10, seq_num = 1)": ("ranking",
            dx[dx.seq_num == 1].icd_code.value_counts().head(10).index.tolist()),
        "Estadía media en UCI (días)": ("escalar", float(icu.los.mean())),
        "Estadía media en UCI calculada con las fechas (días)": ("escalar", float(dias(icu.intime, icu.outtime).mean())),
        "Duración mediana de la internación (días)": ("escalar", float(dias(a.admittime, a.dischtime).median())),
        "Mortalidad hospitalaria (% de internaciones)": ("escalar", float(100 * muere.mean())),
        "Mortalidad por grupo de edad": ("distribucion",
            (pa.assign(g=grupo, m=muere).groupby("g", observed=False).m.mean().fillna(0) /
             max(pa.assign(g=grupo, m=muere).groupby("g", observed=False).m.mean().fillna(0).sum(), 1e-9)).to_dict()),
        "Internaciones por tipo de admisión": ("distribucion", a.admission_type.value_counts(normalize=True).to_dict()),
        "Internaciones por seguro": ("distribucion", a.insurance.value_counts(normalize=True).to_dict()),
        "Pacientes por sexo": ("distribucion", p.gender.value_counts(normalize=True).to_dict()),
        "Pacientes por grupo de edad": ("distribucion",
            pd.cut(p.anchor_age, [0, 40, 60, 80, 200], right=False).astype(str).value_counts(normalize=True).to_dict()),
        "Internaciones por paciente (media)": ("escalar", float(len(a) / max(len(p), 1))),
        "% de internaciones con estadía en UCI": ("escalar", float(100 * a.hadm_id.isin(icu.hadm_id).mean())),
        "Reinternación a 30 días (% de internaciones)": ("escalar", float(100 * reinternacion(a))),
        "Estudios de laboratorio más pedidos (top 10 itemid)": ("ranking", lab.itemid.value_counts().head(10).index.tolist()),
        "% de laboratorios anormales (flag)": ("escalar", float(100 * lab.flag.notna().mean())),
        "Primera unidad de UCI": ("distribucion", icu.first_careunit.value_counts(normalize=True).to_dict()),
    }


def reinternacion(a):
    x = a.sort_values(["subject_id", "admittime"])
    sig = x.groupby("subject_id").admittime.shift(-1)
    return float(((sig - x.dischtime).dt.days.between(0, 30)).mean())


def consultas_synthea(d):
    p, e, c, o = d["patients"], d["encounters"], d["conditions"], d["observations"]
    edad = (pd.Timestamp("2026-01-01") - p.birthdate).dt.days / 365.25
    return {
        "Pacientes por condición (top 10)": ("ranking",
            c.merge(e[["id", "patient"]], left_on="encounter", right_on="id").groupby("description").patient.nunique()
             .sort_values(ascending=False).head(10).index.tolist()),
        "Condiciones más frecuentes (top 10 códigos)": ("ranking", c.code.value_counts().head(10).index.tolist()),
        "Duración mediana del encuentro (horas)": ("escalar", float(dias(e.start, e.stop).median() * 24)),
        "Encuentros por paciente (media)": ("escalar", float(len(e) / max(len(p), 1))),
        "% de pacientes fallecidos": ("escalar", float(100 * p.deathdate.notna().mean())),
        "Edad mediana": ("escalar", float(edad.median())),
        "Encuentros por clase": ("distribucion", e.encounterclass.value_counts(normalize=True).to_dict()),
        "Pacientes por sexo": ("distribucion", p.gender.value_counts(normalize=True).to_dict()),
        "Pacientes por raza": ("distribucion", p.race.value_counts(normalize=True).to_dict()),
        "Costo medio del encuentro": ("escalar", float(e.base_encounter_cost.mean())),
        "Observaciones más frecuentes (top 10)": ("ranking", o.description.value_counts().head(10).index.tolist()),
        "Observaciones por encuentro (media)": ("escalar", float(len(o) / max(len(e), 1))),
        "Encuentros por año": ("distribucion", e.start.dt.year.value_counts(normalize=True).to_dict()),
        "% de condiciones resueltas (con fin)": ("escalar", float(100 * c.stop.notna().mean())),
    }


def comparar(tipo, real, cand):
    if tipo == "escalar":
        err = abs(cand - real) / abs(real) if real else (0.0 if cand == 0 else 1.0)
        return {"real": round(real, 3), "candidata": round(cand, 3) if np.isfinite(cand) else None,
                "error_relativo": round(float(err), 3) if np.isfinite(err) else None,
                "se_conserva": bool(np.isfinite(err) and err <= UMBRAL["escalar"])}
    if tipo == "ranking":
        n = len(set(map(str, real)) & set(map(str, cand)))
        return {"coinciden_del_top10": n, "se_conserva": n >= UMBRAL["ranking"]}
    claves = set(real) | set(cand)
    vt = 0.5 * sum(abs(real.get(k, 0) - cand.get(k, 0)) for k in claves)
    return {"variacion_total": round(float(vt), 3), "se_conserva": bool(vt <= UMBRAL["distribucion"])}


def main():
    warnings.filterwarnings("ignore")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--entrenamiento", choices=e3.ENTRENAMIENTOS, required=True)
    a = ap.parse_args()
    cfg = e3.ENTRENAMIENTOS[a.entrenamiento]
    base = a.entrenamiento.split("_")[0]
    tablas = d2.CONJUNTOS[a.entrenamiento]["tablas"]
    consultas = consultas_mimic if base == "mimic" else consultas_synthea
    real = consultas(d2.leer(d2.GRANDES / a.entrenamiento / "entrada", tablas))
    res = {"entrenamiento": a.entrenamiento, "umbrales": UMBRAL, "consultas": list(real), "candidatas": {}}
    for nombre, fuente in cfg["candidatas"].items():
        if fuente[0] == "parquet" and not fuente[1].exists():
            continue
        cand_d = d2.leer(fuente[1], tablas) if fuente[0] == "parquet" else e3.de_pg(fuente[1], fuente[2], tablas)
        try:
            cand = consultas(cand_d)
        except Exception as ex:
            res["candidatas"][nombre] = {"error": f"{type(ex).__name__}: {str(ex)[:200]}"}
            continue
        filas = {q: {"tipo": real[q][0], **comparar(real[q][0], real[q][1], cand[q][1])} for q in real}
        res["candidatas"][nombre] = {"por_consulta": filas,
                                     "se_conservan": sum(f["se_conserva"] for f in filas.values()),
                                     "de": len(filas)}
        print(f"[{a.entrenamiento}] {nombre}: {res['candidatas'][nombre]['se_conservan']} de {len(filas)}", flush=True)
    out = AQUI / "resultados"
    out.mkdir(exist_ok=True)
    (out / f"{a.entrenamiento}.json").write_text(json.dumps(res, indent=2, ensure_ascii=False, default=str),
                                                 encoding="utf-8")
    md = [f"# F1: utilidad — {a.entrenamiento}", "", "| Consulta | " + " | ".join(res["candidatas"]) + " |",
          "|---|" + "---|" * len(res["candidatas"])]
    for q in real:
        celdas = []
        for c in res["candidatas"].values():
            f = c.get("por_consulta", {}).get(q)
            if not f:
                celdas.append("error")
                continue
            v = (f"{f['error_relativo']:.0%}" if f.get("error_relativo") is not None else
                 f"{f['coinciden_del_top10']}/10" if "coinciden_del_top10" in f else
                 f"VT {f['variacion_total']:.2f}" if "variacion_total" in f else "—")
            celdas.append(("✓ " if f["se_conserva"] else "✗ ") + v)
        md.append(f"| {q} | " + " | ".join(celdas) + " |")
    md.append("| **Se conservan** | " + " | ".join(f"**{c.get('se_conservan', 0)} de {c.get('de', 0)}**"
                                                for c in res["candidatas"].values()) + " |")
    (out / f"{a.entrenamiento}.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
