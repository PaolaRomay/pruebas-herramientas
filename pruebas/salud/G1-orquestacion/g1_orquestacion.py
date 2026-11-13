#!/usr/bin/env python3
"""G1m: orquestación con el LLM local. Un pedido en lenguaje natural sobre MIMIC-IV demo -> plan JSON con las
herramientas del proyecto y sus parámetros -> validación y, donde se puede, ejecución.

Herramientas que conoce el LLM (las que se probaron en las etapas anteriores):
  detectar     clasificar columnas sensibles (A2: LLM local por esquema y muestra)
  subconjunto  extraer pacientes y todo lo que depende de ellos (C1: subconjunto_salud.py)
  anonimizar   enmascarar en el lugar (B1: PostgreSQL Anonymizer con las reglas de masc.sql)
  sintetizar   generar datos sintéticos (D2: MOSTLY AI)

Casos (los cinco de G1 sobre Pagila, adaptados a MIMIC; el pedido va textual) y criterio de «lo hizo bien»:
  1 detectar     plan = detectar sobre todas las tablas.
  2 anonimizar   plan = anonimizar con ids seudonimizados y fechas desplazadas POR PACIENTE (no ruido por fila).
  3 subconjunto  plan = subconjunto con ancla patients y un filtro SQL de sepsis que, ejecutado, da los 17 pacientes
                 con sepsis de la demo (verdad: CIE-10 A40, A41, R65.2; CIE-9 038, 995.91, 995.92, 785.52); el
                 subconjunto se extrae de verdad con C1 y tiene que cargar con todas las FK.
  4 sintetizar   plan = sintetizar ~200 pacientes con internaciones y diagnósticos.
  5 ambiguo      combinación razonable (anonimizar o sintetizar, con o sin subconjunto) y supuestos explícitos o
                 preguntas.
Tres corridas por caso (temperatura 0,7, semillas 1 a 3) para medir la variabilidad.

Uso:  .venv/bin/python pruebas/salud/G1-orquestacion/g1_orquestacion.py
Salida: resultados/g1m.json y g1m.md; planes crudos en resultados/crudo/.
"""
import json
import subprocess
import time
from pathlib import Path

import requests
import sqlalchemy as sa

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[2]
OLLAMA = "http://127.0.0.1:11434"
MODELO = "gemma4:12b-it-qat"
SEPSIS = ("(icd_version = 10 and (icd_code like 'A40%' or icd_code like 'A41%' or icd_code like 'R652%')) or "
          "(icd_version = 9 and (icd_code like '038%' or icd_code in ('99591', '99592', '78552')))")

CASOS = {
    1: ("detectar", "¿Qué columnas de esta base tienen datos personales o datos de salud? Listalas con el tipo de "
                    "dato de cada una."),
    2: ("anonimizar", "Anonimizá los identificadores de los pacientes y de los profesionales y las fechas. Las fechas "
                      "de cada paciente tienen que seguir siendo coherentes entre sí (un alta no puede quedar antes "
                      "del ingreso) y la base tiene que seguir cargando sin errores."),
    3: ("subconjunto", "Sacame un subconjunto con los pacientes que tuvieron sepsis y todo lo que dependa de ellos "
                       "(internaciones, diagnósticos, laboratorios, UCI), sin romper las claves."),
    4: ("sintetizar", "Generá una base sintética con el mismo esquema y unos 200 pacientes, con internaciones y "
                      "diagnósticos coherentes entre sí."),
    5: ("ambiguo", "Prepará una copia de la base para que el equipo de testing la use sin ver datos reales."),
}

SISTEMA = """Sos el orquestador de un sistema que prepara bases de datos de prueba a partir de una base de producción
de PostgreSQL. Recibís un pedido en lenguaje natural y devolvés un plan: una lista de pasos, cada uno con una
herramienta y sus parámetros. Si el pedido es ambiguo, anotá los supuestos que hacés y las preguntas que le harías al
usuario.

Herramientas:
- detectar: clasifica qué columnas son sensibles. Parámetros: tablas (lista, o ["todas"]).
- subconjunto: extrae un grupo de pacientes y todas las filas que dependen de ellos, sin romper claves.
  Parámetros: ancla (tabla, con esquema), filtro_sql (condición SQL sobre la tabla ancla, puede usar subconsultas
  a otras tablas), porcentaje (0 a 100, sobre los que cumplen el filtro).
- anonimizar: enmascara la base en el lugar. Parámetros: identificadores ("seudonimizar" o "eliminar"),
  fechas ("desplazar_por_paciente", "ruido_por_fila", "generalizar" o "sin_cambios"), edad ("decada", "ruido" o
  "sin_cambios"), texto_libre ("enmascarar" o "sin_cambios").
- sintetizar: entrena un generador y produce datos sintéticos. Parámetros: tablas (lista, con esquema), pacientes
  (cantidad a generar).

Esquema (tablas y columnas):
{esquema}

Pedido del usuario:
{pedido}"""

FORMATO = {"type": "object", "required": ["pasos", "supuestos", "preguntas"], "properties": {
    "pasos": {"type": "array", "items": {"type": "object", "required": ["herramienta", "parametros"], "properties": {
        "herramienta": {"type": "string", "enum": ["detectar", "subconjunto", "anonimizar", "sintetizar"]},
        "parametros": {"type": "object", "properties": {
            "tablas": {"type": "array", "items": {"type": "string"}}, "ancla": {"type": "string"},
            "filtro_sql": {"type": "string"}, "porcentaje": {"type": "number"},
            "identificadores": {"type": "string", "enum": ["seudonimizar", "eliminar"]},
            "fechas": {"type": "string", "enum": ["desplazar_por_paciente", "ruido_por_fila", "generalizar",
                                                  "sin_cambios"]},
            "edad": {"type": "string", "enum": ["decada", "ruido", "sin_cambios"]},
            "texto_libre": {"type": "string", "enum": ["enmascarar", "sin_cambios"]},
            "pacientes": {"type": "integer"}}}}}},
    "supuestos": {"type": "array", "items": {"type": "string"}},
    "preguntas": {"type": "array", "items": {"type": "string"}}}}


def esquema(conn, muestra=False):
    filas = conn.execute(sa.text("""select table_schema || '.' || table_name, string_agg(column_name, ', ' order by
        ordinal_position) from information_schema.columns where table_schema in ('mimiciv_hosp', 'mimiciv_icu')
        group by 1 order by 1""")).fetchall()
    if not muestra:
        return "\n".join(f"- {t}({c})" for t, c in filas)
    # Variante con muestra: 3 valores de ejemplo por columna (distintos, orden determinista), como A2b.
    lineas = []
    for t, cols in filas:
        partes = []
        for c in cols.split(", "):
            vs = [r[0] for r in conn.execute(sa.text(
                f'select v from (select distinct "{c}"::text v from {t} where "{c}" is not null limit 200) x '
                f'order by md5(v) limit 3'))]
            partes.append(f"{c} [{' | '.join(v[:30] for v in vs)}]")
        lineas.append(f"- {t}({', '.join(partes)})")
    return "\n".join(lineas)


def evaluar_subconjunto(conn, paso, corrida):
    """Ejecuta el filtro del LLM contra la verdad y, si es razonable, extrae el subconjunto con C1."""
    p = paso["parametros"]
    ancla, filtro = p.get("ancla", ""), p.get("filtro_sql", "")
    out = {"ancla": ancla, "filtro_sql": filtro, "porcentaje": p.get("porcentaje")}
    verdad = {r[0] for r in conn.execute(sa.text(
        f"select distinct subject_id from mimiciv_hosp.diagnoses_icd where {SEPSIS}"))}
    try:
        tabla = ancla if "." in ancla else f"mimiciv_hosp.{ancla}"
        elegidos = {r[0] for r in conn.execute(sa.text(f"select subject_id from {tabla} where {filtro}"))}
        out.update(filtro_corre=True, pacientes=len(elegidos), verdad=len(verdad),
                   aciertos=len(elegidos & verdad), de_mas=len(elegidos - verdad))
    except Exception as e:
        conn.rollback()
        out.update(filtro_corre=False, error=f"{type(e).__name__}: {str(e).splitlines()[0][:200]}")
        return out
    pct = p.get("porcentaje") or 100
    filtro_c1 = f"({filtro})" + (f" and hashtext('g1' || subject_id::text) % {round(100 / pct)} = 0" if pct < 100 else "")
    cfg = {"prueba": "G1m", "origen": "mimic_demo", "destino": f"g1m_caso3_c{corrida}",
           "salida": f"../G1-orquestacion/resultados/c1_caso3_c{corrida}",
           "ancla": {"tabla": tabla, "filtro": filtro_c1}, "control": "false",
           "copiar_enteras": ["mimiciv_hosp.d_icd_diagnoses", "mimiciv_hosp.d_icd_procedures", "mimiciv_hosp.d_hcpcs",
                              "mimiciv_hosp.d_labitems", "mimiciv_icu.d_items"],
           "relaciones_csv": "pruebas/_bases/evidencia/mimic-demo/relaciones.csv"}
    ruta = RAIZ / "pruebas/salud/C1-subconjunto" / f"_g1_caso3_c{corrida}.json"
    ruta.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
    r = subprocess.run([str(RAIZ / ".venv/bin/python"), str(RAIZ / "pruebas/salud/C1-subconjunto/subconjunto_salud.py"),
                        str(ruta)], capture_output=True, text=True)
    ruta.unlink()
    out["extraccion_c1"] = "ok, carga con todas las FK" if r.returncode == 0 else "error: " + r.stderr.strip()[-200:]
    if r.returncode == 0:
        out["salida_c1"] = r.stdout.strip()[:200]
    return out


def evaluar(caso, plan, conn, corrida):
    pasos = plan.get("pasos", [])
    herr = [p["herramienta"] for p in pasos]
    r = {"herramientas": herr, "supuestos": len(plan.get("supuestos", [])), "preguntas": len(plan.get("preguntas", []))}
    if caso == 1:
        r["bien"] = herr == ["detectar"]
    elif caso == 2:
        an = [p["parametros"] for p in pasos if p["herramienta"] == "anonimizar"]
        r["parametros"] = an[0] if an else None
        r["bien"] = bool(an) and an[0].get("identificadores") == "seudonimizar" and \
            an[0].get("fechas") == "desplazar_por_paciente" and "sintetizar" not in herr
        r["ejecucion"] = "equivale a B1m `consistentes` (0 incoherencias, 51 FK)" if r["bien"] else None
    elif caso == 3:
        sub = [p for p in pasos if p["herramienta"] == "subconjunto"]
        if sub:
            r["subconjunto"] = evaluar_subconjunto(conn, sub[0], corrida)
            s = r["subconjunto"]
            r["bien"] = s.get("filtro_corre", False) and s.get("aciertos") == s.get("verdad") and s.get("de_mas") == 0 \
                and str(s.get("extraccion_c1", "")).startswith("ok") and "patients" in s["ancla"]
        else:
            r["bien"] = False
    elif caso == 4:
        si = [p["parametros"] for p in pasos if p["herramienta"] == "sintetizar"]
        r["parametros"] = si[0] if si else None
        tablas = " ".join(si[0].get("tablas", [])) if si else ""
        r["bien"] = bool(si) and 150 <= (si[0].get("pacientes") or 0) <= 250 and \
            all(t in tablas for t in ("patients", "admissions", "diagnoses_icd"))
    else:
        protege = any(h in herr for h in ("anonimizar", "sintetizar"))
        an = [p["parametros"] for p in pasos if p["herramienta"] == "anonimizar"]
        fechas_ok = not an or an[0].get("fechas") in ("desplazar_por_paciente", "generalizar")
        r["parametros"] = [p["parametros"] for p in pasos]
        r["bien"] = protege and fechas_ok and (r["supuestos"] + r["preguntas"]) > 0
    return r


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--muestra", action="store_true", help="esquema con 3 valores de ejemplo por columna")
    ap.add_argument("--casos", default="1,2,3,4,5")
    a = ap.parse_args()
    sufijo = "_muestra" if a.muestra else ""
    eng = sa.create_engine("postgresql+psycopg2://postgres:postgres@127.0.0.1:55432/mimic_demo")
    (AQUI / "resultados" / "crudo").mkdir(parents=True, exist_ok=True)
    res = {"modelo": MODELO, "temperatura": 0.7, "muestra": a.muestra, "casos": {}}
    with eng.connect() as conn:
        texto = esquema(conn, a.muestra)
        for caso, (nombre, pedido) in CASOS.items():
            if str(caso) not in a.casos.split(","):
                continue
            corridas = []
            for corrida in (1, 2, 3):
                t0 = time.time()
                r = requests.post(f"{OLLAMA}/api/chat", timeout=1800, json=dict(
                    model=MODELO, stream=False, think=False, format=FORMATO, keep_alive="30m",
                    options={"temperature": 0.7, "seed": corrida, "num_ctx": 16384},
                    messages=[{"role": "user", "content": SISTEMA.format(esquema=texto, pedido=pedido)}])).json()
                seg = time.time() - t0
                contenido = r["message"]["content"]
                (AQUI / "resultados" / "crudo" / f"caso{caso}{sufijo}_c{corrida}.json").write_text(contenido, encoding="utf-8")
                try:
                    plan = json.loads(contenido)
                    ev = evaluar(caso, plan, conn, corrida)
                except Exception as e:
                    ev = {"bien": False, "error": f"{type(e).__name__}: {str(e)[:150]}"}
                corridas.append({"corrida": corrida, "segundos": round(seg, 1), **ev})
                print(f"[caso {caso} c{corrida}] {seg:.0f} s, bien={ev.get('bien')}, {ev.get('herramientas')}",
                      flush=True)
            res["casos"][caso] = {"nombre": nombre, "pedido": pedido, "corridas": corridas,
                                  "bien": sum(c["bien"] for c in corridas),
                                  "mismo_plan_en_las_3": len({json.dumps(c.get("herramientas")) for c in corridas}) == 1}
    (AQUI / "resultados" / f"g1m{sufijo}.json").write_text(json.dumps(res, indent=2, ensure_ascii=False, default=str),
                                                  encoding="utf-8")


if __name__ == "__main__":
    main()
