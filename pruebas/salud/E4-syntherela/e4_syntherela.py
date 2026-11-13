#!/usr/bin/env python3
"""E4m / E4s: SyntheRela (benchmark de datos sintéticos relacionales) sobre las salidas de D2 (MOSTLY AI) y D3 (SDV).

Métricas multitabla de SyntheRela 0.0.4:
  - CardinalityShapeSimilarity: ¿la cantidad de hijos por padre (internaciones por paciente, diagnósticos por
    internación…) tiene la misma distribución? 1 = igual.
  - AggregationDetection (XGBoost, C2ST): un clasificador intenta distinguir filas reales de sintéticas usando
    también agregados de sus tablas hijas. Exactitud 0,5 = indistinguible; 1 = las distingue siempre.
Además, por tabla, SingleTable MaximumMeanDiscrepancy (0 = misma distribución).

Corre en un entorno aparte (SyntheRela fija scikit-learn 1.3.1; el .venv del repo tiene 1.9.1):
  ../herramientas-externas/venv-syntherela/bin/python pruebas/salud/E4-syntherela/e4_syntherela.py
Salida: resultados/e4.json (solo métricas).
"""
import json
import sys

import numpy as np
import time
import warnings
from pathlib import Path

AQUI = Path(__file__).resolve().parent
SALUD = AQUI.parent
sys.path.insert(0, str(SALUD / "D2-mostlyai"))
import d2_mostly_salud as d2  # noqa: E402

CASOS = [
    ("mimic_47", "D2 MOSTLY AI", SALUD / "D2-mostlyai/salidas_grandes/mimic_47/sintetico_47"),
    ("mimic_47", "D3 SDV HMA", SALUD / "D3-sdv/salidas_grandes/mimic_47_5t"),
    ("synthea_85", "D2 MOSTLY AI", SALUD / "D2-mostlyai/salidas_grandes/synthea_85/sintetico_85"),
    ("synthea_85", "D3 SDV HMA", SALUD / "D3-sdv/salidas_grandes/synthea_85_4t"),
    ("synthea_925", "D2 MOSTLY AI", SALUD / "D2-mostlyai/salidas_grandes/synthea_925/sintetico_925"),
]
FECHAS = {"admittime", "dischtime", "deathtime", "edregtime", "edouttime", "intime", "outtime", "charttime", "dod",
          "birthdate", "deathdate", "start", "stop", "date"}
PADRES = {"mimic_47": ["patients", "admissions"], "synthea_85": ["patients", "encounters"],
          "synthea_925": ["patients", "encounters"]}
CATEGORICAS_NUMERICAS = {"icd_version", "hospital_expire_flag", "itemid", "seq_num", "anchor_year"}


def metadata(conjunto, datos):
    from syntherela.metadata import Metadata
    cfg = d2.CONJUNTOS[conjunto]["tablas"]
    tablas, rel = {}, []
    for t, (esq, pk, fks, cols, filtro) in cfg.items():
        columnas = {}
        for c in cols:
            if c == pk or any(c == f for f, _, _ in fks):
                columnas[c] = {"sdtype": "id"}
            elif c in FECHAS:
                columnas[c] = {"sdtype": "datetime", "datetime_format": "%Y-%m-%d %H:%M:%S"}
            elif datos[t][c].dtype.kind in "if" and c not in CATEGORICAS_NUMERICAS:
                columnas[c] = {"sdtype": "numerical"}
            else:
                columnas[c] = {"sdtype": "categorical"}
        tablas[t] = {"columns": columnas}
        if pk:
            tablas[t]["primary_key"] = pk
        for c, ref, _ in fks:
            rel.append({"parent_table_name": ref, "parent_primary_key": cfg[ref][1], "child_table_name": t,
                        "child_foreign_key": c})
    return Metadata.load_from_dict({"METADATA_SPEC_VERSION": "MULTI_TABLE_V1", "tables": tablas,
                                    "relationships": rel})


def preparar(conjunto, d):
    """Mismos tipos en real y sintético: ids como texto, categóricas como texto."""
    cfg = d2.CONJUNTOS[conjunto]["tablas"]
    for t, (esq, pk, fks, cols, filtro) in cfg.items():
        df = d[t][cols].copy()
        for c in cols:
            if c == pk or any(c == f for f, _, _ in fks) or c in CATEGORICAS_NUMERICAS:
                df[c] = df[c].astype(str)
            elif df[c].dtype == object or str(df[c].dtype).startswith(("string", "str")):
                # MOSTLY mezcla pd.NA y None: todo vacío pasa a NaN (los codificadores de sklearn lo exigen)
                df[c] = df[c].astype(object).where(df[c].notna(), np.nan)
            if str(df[c].dtype) in ("Int64", "Float64", "boolean"):
                df[c] = df[c].astype(float)
        d[t] = df
    return d


def main():
    warnings.filterwarnings("ignore")
    from xgboost import XGBClassifier
    from syntherela.metrics.multi_table.detection import AggregationDetection
    from syntherela.metrics.multi_table.statistical import CardinalityShapeSimilarity
    from syntherela.metrics.single_table.distance import MaximumMeanDiscrepancy
    res = []
    for conjunto, nombre, carpeta in CASOS:
        tablas = d2.CONJUNTOS[conjunto]["tablas"]
        real = preparar(conjunto, d2.leer(d2.GRANDES / conjunto / "entrada", tablas))
        sint = preparar(conjunto, d2.leer(carpeta, tablas))
        md = metadata(conjunto, real)
        fila = {"conjunto": conjunto, "generador": nombre}
        t0 = time.time()
        try:
            r = CardinalityShapeSimilarity().run(real, sint, metadata=md)
            fila["cardinalidad"] = {str(k): (round(float(v), 3) if isinstance(v, (int, float)) else v)
                                    for k, v in (r.items() if isinstance(r, dict) else [("valor", r)])}
        except Exception as e:
            fila["cardinalidad"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
        try:
            det = AggregationDetection(classifier_cls=XGBClassifier, classifier_args={"seed": 1}, random_state=1)
            fila["deteccion_agregada"] = {}
            for t in PADRES[conjunto]:   # tablas con hijas: la detección usa agregados de sus hijas
                r = det.run(real, sint, metadata=md, target_table=t)
                fila["deteccion_agregada"][t] = {k: round(float(v), 3) for k, v in r.items()
                                                 if isinstance(v, (int, float))} if isinstance(r, dict) else r
        except Exception as e:
            fila["deteccion_agregada"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
        try:
            mmd = MaximumMeanDiscrepancy()
            fila["mmd_por_tabla"] = {}
            for t in tablas:   # MMD es cuadrática en filas: muestra de hasta 5 000 por lado
                rr, ss = real[t].sample(min(5000, len(real[t])), random_state=1), \
                    sint[t].sample(min(5000, len(sint[t])), random_state=1)
                try:
                    r = mmd.run(rr, ss, metadata=md.get_table_meta(t, to_dict=True))
                    fila["mmd_por_tabla"][t] = round(float(r["value"] if isinstance(r, dict) else r), 4)
                except Exception as e:   # p. ej. una tabla sin columnas numéricas ni fechas
                    fila["mmd_por_tabla"][t] = f"no aplica: {type(e).__name__}"
        except Exception as e:
            fila["mmd_por_tabla"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
        fila["segundos"] = round(time.time() - t0, 1)
        res.append(fila)
        print(json.dumps(fila, ensure_ascii=False), flush=True)
    (AQUI / "resultados").mkdir(exist_ok=True)
    (AQUI / "resultados" / "e4.json").write_text(json.dumps(res, indent=2, ensure_ascii=False, default=str),
                                                 encoding="utf-8")


if __name__ == "__main__":
    main()
