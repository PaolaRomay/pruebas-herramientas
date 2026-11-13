#!/usr/bin/env python3
"""A2m / A2s: LLM local (Ollama) que clasifica columnas de MIMIC-IV demo y Synthea como sensibles o no.

Variantes:
  a2a            solo el esquema: nombre de la tabla y nombres y tipos de sus columnas.
  a2b            el esquema + hasta 5 valores distintos de cada columna (muestra determinista).
  a2b_ofuscado   como a2b, pero tablas y columnas renombradas (tabla_07, col_03): el LLM solo ve tipos y valores.
                 Comparada con a2b, mide cuánto depende el resultado de los nombres (y de que el LLM conozca el
                 esquema público de MIMIC o de Synthea).

Una consulta por tabla, con salida JSON forzada por esquema (structured outputs de Ollama). El LLM devuelve, por
columna, si es sensible y una entidad de una lista cerrada. Una columna que el LLM no devuelve no se cuenta (queda
en el registro de la corrida).

La política que recibe el LLM resume las fuentes de la lista de referencia (Ley 18.331 art. 4 y HIPAA Safe
Harbor), no las reglas ni las decisiones del equipo.

Uso:
  .venv/bin/python pruebas/salud/A2-llm-local/a2_llm_salud.py --base mimic --variante a2a --corridas 3
  .venv/bin/python pruebas/salud/A2-llm-local/a2_llm_salud.py --base mimic --sonda    # ¿reconoce el esquema?
Salida: resultados/<base>/a2<m|s>_<variante>_columnas.csv, a2<m|s>_<variante>_corrida.md y respuestas crudas en
resultados/<base>/crudo/ (sin valores de filas).
"""
import argparse
import csv
import datetime
import hashlib
import json
import platform
import time
from pathlib import Path

import pandas as pd
import requests
import sqlalchemy as sa

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[2]
BASES = {
    "mimic": dict(prueba="A2m", db="mimic_demo", referencia=RAIZ / "data" / "columnas_sensibles_mimic.csv"),
    "synthea": dict(prueba="A2s", db="synthea_p1000", referencia=RAIZ / "data" / "columnas_sensibles_synthea.csv"),
}
OLLAMA = "http://127.0.0.1:11434"
ENTIDADES = ["PERSON", "DATE_TIME", "LOCATION", "US_SSN", "US_DRIVER_LICENSE", "US_PASSPORT", "PHONE_EMAIL",
             "ID_PERSONA", "SALUD", "DEMOGRAFICO", "ECONOMICO", "PROFESIONAL", "OTRO", "NINGUNA"]

POLITICA = """Sos un clasificador de datos personales para una herramienta que prepara bases de datos de prueba a
partir de bases de producción. Te paso una tabla de una base de datos de salud. Para CADA columna decidí si es
sensible, es decir, si hay que anonimizarla o sintetizarla antes de usarla fuera de producción.

Criterio (Ley 18.331 de Uruguay, art. 4, y HIPAA Safe Harbor):
- Dato personal: cualquier información referida a una persona física determinada o determinable, directamente o
  combinada con otras columnas.
- Dato sensible: datos de salud (diagnósticos, procedimientos, medicamentos, resultados, signos vitales, notas
  clínicas) y origen racial o étnico.
- Son sensibles: nombres; fechas vinculadas a una persona (nacimiento, internación, alta, muerte, estudios);
  ubicaciones más chicas que un estado (dirección, ciudad, condado, código postal, coordenadas); teléfonos, correos;
  números de documento, seguro social, licencia, pasaporte; identificadores de paciente, de internación o de
  episodio; datos demográficos que combinados identifican (sexo, edad, estado civil, idioma, seguro); datos
  económicos del paciente; identificadores y nombres de profesionales de la salud.
- No son sensibles: catálogos y tablas de referencia que no describen a ninguna persona (descripciones de códigos,
  datos de hospitales u organizaciones), y columnas técnicas (contadores, números de orden, unidades de medida).

Entidad: elegí la que mejor describa la columna. PERSON (nombres de personas), DATE_TIME, LOCATION, US_SSN,
US_DRIVER_LICENSE, US_PASSPORT, PHONE_EMAIL, ID_PERSONA (identificador de paciente, internación o episodio), SALUD,
DEMOGRAFICO, ECONOMICO, PROFESIONAL (identificador de un profesional), OTRO (sensible, de otro tipo) o NINGUNA (no
sensible).

Respondé solo con el JSON pedido, con una entrada por columna, en el mismo orden y con el nombre exacto de la
columna."""


def esquema_json(cols):
    return {"type": "object", "required": ["columnas"], "properties": {"columnas": {
        "type": "array", "items": {"type": "object", "required": ["columna", "sensible", "entidad"], "properties": {
            "columna": {"type": "string", "enum": cols}, "sensible": {"type": "boolean"},
            "entidad": {"type": "string", "enum": ENTIDADES}}}}}}


def muestra(conn, esq, tabla, col, n, semilla):
    q = sa.text(f'select v from (select distinct "{col}"::text as v from "{esq}"."{tabla}" '
                f'where "{col}" is not null and "{col}"::text <> \'\') d order by md5(v || :s) limit :n')
    return [r[0][:40] for r in conn.execute(q, {"s": semilla, "n": n})]


def preguntar(modelo, prompt, formato, opciones):
    r = requests.post(f"{OLLAMA}/api/chat", timeout=900, json=dict(
        model=modelo, stream=False, think=False, format=formato, options=opciones, keep_alive="30m",
        messages=[{"role": "user", "content": prompt}]))
    r.raise_for_status()
    return r.json()


def sonda(modelo, conn):
    """¿El LLM reconoce de qué base pública es el esquema? Solo nombres de tablas y columnas."""
    filas = conn.execute(sa.text(
        "select table_name, string_agg(column_name, ', ' order by ordinal_position) from information_schema.columns "
        "where table_schema not in ('pg_catalog','information_schema') group by table_name order by table_name"))
    texto = "\n".join(f"- {t}({c})" for t, c in filas)
    p = ("Este es el esquema de una base de datos (tablas y columnas). ¿Reconocés de qué base de datos pública o "
         "de qué generador proviene? Respondé en una o dos oraciones, con el nombre si lo sabés.\n\n" + texto)
    return preguntar(modelo, p, None, {"temperature": 0, "seed": 1, "num_ctx": 16384})["message"]["content"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", choices=BASES, required=True)
    ap.add_argument("--variante", choices=["a2a", "a2b", "a2b_ofuscado"])
    ap.add_argument("--corridas", type=int, default=1)
    ap.add_argument("--modelo", default="gemma4:12b-it-qat")
    ap.add_argument("--temperatura", type=float, default=0.0)
    ap.add_argument("--n-valores", type=int, default=5)
    ap.add_argument("--semilla", default="a2")
    ap.add_argument("--sonda", action="store_true")
    a = ap.parse_args()
    cfg = BASES[a.base]
    salida = AQUI / "resultados" / a.base
    (salida / "crudo").mkdir(parents=True, exist_ok=True)
    eng = sa.create_engine(f"postgresql+psycopg2://postgres:postgres@127.0.0.1:55432/{cfg['db']}")

    if a.sonda:
        with eng.connect() as conn:
            r = sonda(a.modelo, conn)
        (salida / f"{cfg['prueba'].lower()}_sonda.md").write_text(
            f"# Sonda de contaminación ({cfg['db']}, {a.modelo}, temperatura 0)\n\n"
            "Pregunta: ¿de qué base pública o generador proviene este esquema? (solo nombres de tablas y "
            f"columnas)\n\nRespuesta:\n\n> {r.strip()}\n", encoding="utf-8")
        print(r)
        return
    if not a.variante:
        ap.error("falta --variante")

    ref = list(csv.DictReader(open(cfg["referencia"], encoding="utf-8")))
    tablas = {}
    for r in ref:
        tablas.setdefault((r["esquema"], r["tabla"]), []).append(r["columna"])
    ofuscar = a.variante == "a2b_ofuscado"
    con_valores = a.variante in ("a2b", "a2b_ofuscado")

    t0 = time.time()
    with eng.connect() as conn:
        tipos = {(r[0], r[1], r[2]): r[3] for r in conn.execute(sa.text(
            "select table_schema, table_name, column_name, data_type from information_schema.columns"))}
        valores = {}
        if con_valores:
            for (esq, tabla), cols in tablas.items():
                for c in cols:
                    valores[(esq, tabla, c)] = ([] if tipos.get((esq, tabla, c)) == "bytea"
                                               else muestra(conn, esq, tabla, c, a.n_valores, a.semilla))
    t_muestra = time.time() - t0

    filas, registro, tiempos, tokens = [], [], [], 0
    for corrida in range(1, a.corridas + 1):
        tc = time.time()
        for i, ((esq, tabla), cols) in enumerate(sorted(tablas.items()), 1):
            alias = {c: (f"col_{j:02d}" if ofuscar else c) for j, c in enumerate(cols, 1)}
            inv = {v: k for k, v in alias.items()}
            nombre_t = f"tabla_{i:02d}" if ofuscar else tabla
            lineas = []
            for c in cols:
                l = f"- {alias[c]} ({tipos.get((esq, tabla, c), '?')})"
                if con_valores:
                    vs = valores[(esq, tabla, c)]
                    l += ": " + (" | ".join(vs) if vs else "(sin valores)")
                lineas.append(l)
            prompt = f"{POLITICA}\n\nTabla: {nombre_t}\nColumnas:\n" + "\n".join(lineas)
            opciones = {"temperature": a.temperatura, "seed": corrida, "num_ctx": 8192}
            ti = time.time()
            r = preguntar(a.modelo, prompt, esquema_json(list(alias.values())), opciones)
            dt = time.time() - ti
            tokens += r.get("eval_count", 0)
            contenido = r["message"]["content"]
            (salida / "crudo" / f"{cfg['prueba'].lower()}_{a.variante}_c{corrida}_{tabla}.json").write_text(
                contenido, encoding="utf-8")
            try:
                resp = {inv[x["columna"]]: x for x in json.loads(contenido)["columnas"] if x["columna"] in inv}
            except (json.JSONDecodeError, KeyError) as e:
                resp = {}
                registro.append(f"corrida {corrida}, {tabla}: respuesta inválida ({type(e).__name__})")
            faltan = [c for c in cols if c not in resp]
            if faltan:
                registro.append(f"corrida {corrida}, {tabla}: el LLM no devolvió {len(faltan)} de {len(cols)} "
                                f"columnas ({', '.join(faltan[:5])}{'…' if len(faltan) > 5 else ''})")
            for c in cols:
                if c in resp:
                    filas.append(dict(corrida=corrida, tabla=tabla, columna=c, marcada=bool(resp[c]["sensible"]),
                                      entidad=resp[c]["entidad"] if resp[c]["sensible"] else "",
                                      entidad_llm=resp[c]["entidad"]))
            print(f"[{a.base} {a.variante} c{corrida}] {i}/{len(tablas)} {tabla}: {len(cols)} col, {dt:.0f} s",
                  flush=True)
        tiempos.append(time.time() - tc)

    df = pd.DataFrame(filas)
    df.insert(0, "variante", a.variante)
    df.insert(0, "prueba", cfg["prueba"])
    nombre = f"{cfg['prueba'].lower()}_{a.variante}"
    df.to_csv(salida / f"{nombre}_columnas.csv", index=False)
    md = [f"# {cfg['prueba']} {a.variante}: LLM local sobre {cfg['db']}", "",
          f"- Corrida: {datetime.datetime.now():%Y-%m-%d %H:%M}",
          f"- Equipo: {platform.machine()}, macOS {platform.mac_ver()[0]}, Python {platform.python_version()}",
          f"- Ollama {requests.get(f'{OLLAMA}/api/version').json()['version']}, modelo `{a.modelo}`, sin razonamiento "
          f"(`think: false`), temperatura {a.temperatura}, semilla = número de corrida, `num_ctx` 8192",
          f"- Política (sha256 del texto): `{hashlib.sha256(POLITICA.encode()).hexdigest()[:16]}`",
          f"- Referencia: `{cfg['referencia'].relative_to(RAIZ)}`; {len(ref)} columnas en {len(tablas)} tablas",
          f"- Valores por columna: {a.n_valores if con_valores else 0}; semilla de muestra `{a.semilla}`",
          f"- Tiempos: muestreo {t_muestra:.0f} s; por corrida " + ", ".join(f"{t:.0f} s" for t in tiempos),
          f"- Tokens generados (total): {tokens}"]
    if registro:
        md += ["", "## Registro", ""] + [f"- {x}" for x in registro]
    (salida / f"{nombre}_corrida.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
