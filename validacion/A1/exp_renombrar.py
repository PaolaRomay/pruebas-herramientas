"""Validación A1: ¿presidio-structured da lo mismo con las columnas renombradas a nombres sin sentido?"""
import importlib.util, sys
from pathlib import Path
import sqlalchemy as sa
from presidio_structured import PandasAnalysisBuilder
spec = importlib.util.spec_from_file_location("a1", Path("pruebas/A1-presidio/a1_presidio.py"))
a1 = importlib.util.module_from_spec(spec); spec.loader.exec_module(a1)
verdad = a1.leer_verdad("data/columnas_sensibles_borrador.csv")
eng = sa.create_engine(a1.URL_DB)
por_tabla = {}
with eng.connect() as c:
    for _, f in verdad.iterrows():
        if a1.tipo_columna(c, f.tabla, f.columna) not in (None, "bytea") and a1.muestra_columna(c, f.tabla, f.columna, 1, "a1"):
            por_tabla.setdefault(f.tabla, []).append(f.columna)
    dfs = {t: a1.muestra_tabla(c, t, cols, 100, "a1") for t, cols in por_tabla.items()}
iguales = distintas = 0
for u in (0.0, 0.4, 0.6):
    b = PandasAnalysisBuilder(analyzer_score_threshold=u)
    for est in a1.ESTRATEGIAS:
        for t, df in dfs.items():
            orig = b.generate_analysis(df, n=100, language="en", selection_strategy=est).entity_mapping
            ren = df.copy(); ren.columns = [f"col_{i}" for i in range(len(df.columns))]
            m = b.generate_analysis(ren, n=100, language="en", selection_strategy=est).entity_mapping
            back = {df.columns[int(k.split("_")[1])]: v for k, v in m.items()}
            if back == orig: iguales += 1
            else:
                distintas += 1; print("DISTINTA", u, est, t, orig, back)
print(f"tablas×estrategia×umbral iguales: {iguales}, distintas: {distintas}")
