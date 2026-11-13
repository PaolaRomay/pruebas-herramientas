#!/usr/bin/env python3
"""F2m / F2s: el LLM local propone relaciones entre tablas a partir del esquema; se miden contra los datos.

  mimic    el LLM ve el esquema con las PK y las 51 FK declaradas, y propone relaciones NO declaradas. Verdad: las 25
           no declaradas de pruebas/_bases/evidencia/mimic-demo/relaciones.csv (encontradas por nombre de columna y
           verificadas contra los datos).
  synthea  el LLM ve el esquema SIN ninguna FK (solo tablas, columnas, tipos y PK) y propone todas las relaciones.
           Verdad: las 40 FK que declaró el cargador (verificadas: 0 huérfanas).
Cada propuesta que no está en la verdad se verifica contra los datos (huérfanas, valores en común): puede ser una
relación real que la verdad no tenía, o un error.

Corre con Ollama (gemma4:12b-it-qat), temperatura 0, salida JSON forzada. Tres corridas con semillas 1, 2 y 3.
Uso:  .venv/bin/python pruebas/salud/F2-relaciones-llm/f2_relaciones_llm.py --base mimic
Salida: resultados/<base>.json; respuestas crudas en resultados/crudo/
"""
import argparse
import csv
import datetime
import json
import time
from pathlib import Path

import requests
import sqlalchemy as sa

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[2]
OLLAMA = "http://127.0.0.1:11434"
BASES = {"mimic": dict(db="mimic_demo", esquemas=("mimiciv_hosp", "mimiciv_icu")),
         "synthea": dict(db="synthea_p1000", esquemas=("synthea",))}

PROMPT = """Sos un asistente que analiza bases de datos relacionales. Te paso el esquema de una base de PostgreSQL
(tablas, columnas con su tipo, clave primaria{fk_txt}). {tarea}

Una relación es: una columna de una tabla (hija) cuyos valores son valores de una columna de otra tabla (padre),
normalmente su clave o un identificador único. Proponé solo relaciones donde estés razonablemente seguro.
Respondé con el JSON pedido.

Esquema:
{esquema}"""
TAREA = {"mimic": "Proponé las relaciones entre tablas que existen en los datos pero NO están declaradas como clave "
                  "foránea (no repitas las declaradas).",
         "synthea": "La base no tiene ninguna clave foránea declarada. Proponé todas las relaciones entre tablas."}


def esquema_texto(conn, esquemas, con_fk):
    cols = conn.execute(sa.text("""
        select c.table_schema, c.table_name, c.column_name, c.data_type from information_schema.columns c
        where c.table_schema = any(:e) order by 1, 2, c.ordinal_position"""), {"e": list(esquemas)}).fetchall()
    pks = {(r[0], r[1]): r[2] for r in conn.execute(sa.text("""
        select n.nspname, c.relname, string_agg(a.attname, ', ') from pg_index i join pg_class c on c.oid = i.indrelid
        join pg_namespace n on n.oid = c.relnamespace join pg_attribute a on a.attrelid = c.oid and a.attnum = any(i.indkey)
        where i.indisprimary and n.nspname = any(:e) group by 1, 2"""), {"e": list(esquemas)})}
    fks = {}
    if con_fk:
        for r in conn.execute(sa.text("""
            select n.nspname, c.relname, a.attname, pn.nspname || '.' || pc.relname, pa.attname
            from pg_constraint k join pg_class c on c.oid = k.conrelid join pg_namespace n on n.oid = c.relnamespace
            join pg_class pc on pc.oid = k.confrelid join pg_namespace pn on pn.oid = pc.relnamespace
            join pg_attribute a on a.attrelid = k.conrelid and a.attnum = k.conkey[1]
            join pg_attribute pa on pa.attrelid = k.confrelid and pa.attnum = k.confkey[1]
            where k.contype = 'f' and n.nspname = any(:e)"""), {"e": list(esquemas)}):
            fks.setdefault((r[0], r[1]), []).append(f"{r[2]} -> {r[3]}.{r[4]}")
    tablas, lineas = {}, []
    for e, t, c, ty in cols:
        tablas.setdefault((e, t), []).append(f"{c} {ty}")
    for (e, t), cs in tablas.items():
        l = f"- {e}.{t}({', '.join(cs)})"
        if (e, t) in pks:
            l += f"; PK: {pks[(e, t)]}"
        if (e, t) in fks:
            l += f"; FK declaradas: {'; '.join(fks[(e, t)])}"
        lineas.append(l)
    return "\n".join(lineas), {f"{e}.{t}": [c.split()[0] for c in cs] for (e, t), cs in tablas.items()}


def verdad(base, conn):
    if base == "mimic":
        out = set()
        for r in csv.DictReader(open(RAIZ / "pruebas/_bases/evidencia/mimic-demo/relaciones.csv", encoding="utf-8")):
            if r["declarada"] == "no":
                e, t, c = r["apunta_a"].split(".")
                out.add((r["tabla"], r["columna"], f"{e}.{t}", c))
        return out
    return {(f"{r[0]}.{r[1]}", r[2], r[3], r[4]) for r in conn.execute(sa.text("""
        select n.nspname, c.relname, a.attname, pn.nspname || '.' || pc.relname, pa.attname
        from pg_constraint k join pg_class c on c.oid = k.conrelid join pg_namespace n on n.oid = c.relnamespace
        join pg_class pc on pc.oid = k.confrelid join pg_namespace pn on pn.oid = pc.relnamespace
        join pg_attribute a on a.attrelid = k.conrelid and a.attnum = k.conkey[1]
        join pg_attribute pa on pa.attrelid = k.confrelid and pa.attnum = k.confkey[1]
        where k.contype = 'f' and n.nspname = 'synthea'"""))}


def verificar(conn, h, c, p, r):
    """Huérfanas y valores en común de una relación propuesta (solo conteos)."""
    try:
        q = sa.text(f"""select count(*) filter (where x.{c} is not null),
            count(*) filter (where x.{c} is not null and not exists (select 1 from {p} y where y.{r}::text = x.{c}::text)),
            count(distinct x.{c}) from {h} x""")
        n, huerf, dist = conn.execute(q).fetchone()
        return {"filas_no_nulas": n, "huerfanas": huerf, "distintos": dist,
                "se_cumple": n > 0 and huerf == 0, "parcial": n > 0 and 0 < huerf < n}
    except Exception as e:
        conn.rollback()
        return {"error": f"{type(e).__name__}: {str(e)[:120]}"}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", choices=BASES, required=True)
    ap.add_argument("--modelo", default="gemma4:12b-it-qat")
    ap.add_argument("--corridas", type=int, default=3)
    a = ap.parse_args()
    cfg = BASES[a.base]
    eng = sa.create_engine(f"postgresql+psycopg2://postgres:postgres@127.0.0.1:55432/{cfg['db']}")
    (AQUI / "resultados" / "crudo").mkdir(parents=True, exist_ok=True)
    with eng.connect() as conn:
        texto, columnas = esquema_texto(conn, cfg["esquemas"], con_fk=(a.base == "mimic"))
        ver = verdad(a.base, conn)
        nombres_t = sorted(columnas)
        formato = {"type": "object", "required": ["relaciones"], "properties": {"relaciones": {"type": "array", "items": {
            "type": "object", "required": ["tabla_hija", "columna_hija", "tabla_padre", "columna_padre"],
            "properties": {"tabla_hija": {"type": "string", "enum": nombres_t}, "columna_hija": {"type": "string"},
                           "tabla_padre": {"type": "string", "enum": nombres_t},
                           "columna_padre": {"type": "string"}}}}}}
        prompt = PROMPT.format(fk_txt=" y claves foráneas declaradas" if a.base == "mimic" else "",
                               tarea=TAREA[a.base], esquema=texto)
        res = {"prueba": f"F2{a.base[0]}", "modelo": a.modelo, "fecha": datetime.datetime.now().isoformat(timespec="minutes"),
               "verdad": len(ver), "corridas": []}
        verif_cache = {}
        for corrida in range(1, a.corridas + 1):
            t0 = time.time()
            r = requests.post(f"{OLLAMA}/api/chat", timeout=1800, json=dict(
                model=a.modelo, stream=False, think=False, format=formato, keep_alive="30m",
                options={"temperature": 0, "seed": corrida, "num_ctx": 16384},
                messages=[{"role": "user", "content": prompt}])).json()
            seg = time.time() - t0
            (AQUI / "resultados" / "crudo" / f"{a.base}_c{corrida}.json").write_text(r["message"]["content"])
            props = set()
            for x in json.loads(r["message"]["content"])["relaciones"]:
                k = (x["tabla_hija"], x["columna_hija"], x["tabla_padre"], x["columna_padre"])
                if k[0] != k[2] or k[1] != k[3]:
                    props.add(k)
            invalidas = [k for k in props if k[1] not in columnas.get(k[0], []) or k[3] not in columnas.get(k[2], [])]
            validas = props - set(invalidas)
            # Para MIMIC, una propuesta que ya es FK declarada no cuenta como acierto ni error: se informa aparte.
            declaradas = set()
            if a.base == "mimic":
                declaradas = {k for k in validas if f"{k[1]} -> {k[2]}.{k[3]}" in texto.split(f"- {k[0]}(")[-1].split("\n")[0]}
                validas -= declaradas
            tp = validas & ver
            extra = validas - ver
            detalle_extra = []
            for k in sorted(extra):
                if k not in verif_cache:
                    verif_cache[k] = verificar(conn, *k)
                detalle_extra.append({"relacion": f"{k[0]}.{k[1]} -> {k[2]}.{k[3]}", **verif_cache[k]})
            extra_ok = sum(1 for d in detalle_extra if d.get("se_cumple"))
            res["corridas"].append({
                "corrida": corrida, "segundos": round(seg, 1), "tokens": r.get("eval_count"),
                "propuestas": len(props), "columnas_inexistentes": len(invalidas), "ya_declaradas": len(declaradas),
                "aciertos": len(tp), "recall": round(len(tp) / len(ver), 3),
                "precision_contra_verdad": round(len(tp) / max(len(validas), 1), 3),
                "fuera_de_la_verdad_que_se_cumplen": extra_ok,
                "precision_verificada": round((len(tp) + extra_ok) / max(len(validas), 1), 3),
                "no_encontradas": sorted(f"{k[0]}.{k[1]} -> {k[2]}.{k[3]}" for k in ver - tp),
                "fuera_de_la_verdad": detalle_extra,
                "inexistentes": sorted(f"{k[0]}.{k[1]} -> {k[2]}.{k[3]}" for k in invalidas)})
            print(f"[{a.base} c{corrida}] {seg:.0f} s, {len(props)} propuestas, {len(tp)}/{len(ver)} aciertos, "
                  f"{extra_ok} extra verificadas, {len(invalidas)} con columnas inexistentes", flush=True)
    (AQUI / "resultados" / f"{a.base}.json").write_text(json.dumps(res, indent=2, ensure_ascii=False),
                                                        encoding="utf-8")


if __name__ == "__main__":
    main()
