#!/usr/bin/env python3
"""F2m (herramientas): SchemaSpy y Metanome (BINDER, SPIDER) descubren relaciones en MIMIC-IV demo; se comparan con
las relaciones ya mapeadas y con el LLM local (F2m).

Verdad:
  - declaradas: las 51 FK del catálogo de mimic_demo;
  - no declaradas: las 25 de pruebas/_bases/evidencia/mimic-demo/relaciones.csv (20 se cumplen en los datos y 5
    tienen huérfanas).

Entradas (ver la ficha para cómo se generan):
  salidas_grandes/schemaspy/<esquema>/mimic_demo.<esquema>.xml   (SchemaSpy 7.0.2; relaciones con implied=true/false)
  salidas_grandes/results/binder_inds, spider_inds               (Metanome CLI 1.1.0; dependencias de inclusión unarias)
  ../F2-relaciones-llm/resultados/mimic.json                     (LLM local)

Variantes de Metanome (todas las dependencias de inclusión son ciertas en los datos; la pregunta es cuáles son
relaciones):
  todas          cualquier A ⊆ B entre columnas distintas;
  clave          además, B es única y sin nulos (puede ser clave del padre) y A tiene algún valor no nulo;
  clave+nombre   además, el nombre de A es igual al de B o termina en él (admit_provider_id -> provider_id).

Uso:  .venv/bin/python pruebas/salud/F2-relaciones-herramientas/f2_herramientas.py
Salida: resultados/f2_herramientas.json y .md (solo nombres de tablas y columnas, y conteos)
"""
import csv
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import psycopg2

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[2]
GRANDES = AQUI / "salidas_grandes"
ESQUEMAS = ("mimiciv_hosp", "mimiciv_icu")


def conectar():
    return psycopg2.connect(host="127.0.0.1", port=55432, user="postgres", password="postgres", dbname="mimic_demo")


def verdad(cur):
    cur.execute("""
        select n.nspname || '.' || c.relname, a.attname, pn.nspname || '.' || pc.relname, pa.attname
        from pg_constraint k join pg_class c on c.oid = k.conrelid join pg_namespace n on n.oid = c.relnamespace
        join pg_class pc on pc.oid = k.confrelid join pg_namespace pn on pn.oid = pc.relnamespace
        join pg_attribute a on a.attrelid = k.conrelid and a.attnum = k.conkey[1]
        join pg_attribute pa on pa.attrelid = k.confrelid and pa.attnum = k.confkey[1]
        where k.contype = 'f' and n.nspname in %s""", (ESQUEMAS,))
    declaradas = set(cur.fetchall())
    no_decl, cumple = set(), {}
    for r in csv.DictReader(open(RAIZ / "pruebas/_bases/evidencia/mimic-demo/relaciones.csv", encoding="utf-8")):
        if r["declarada"] == "no":
            e, t, c = r["apunta_a"].split(".")
            k = (r["tabla"], r["columna"], f"{e}.{t}", c)
            no_decl.add(k)
            cumple[k] = r["se_cumple"] == "sí"
    return declaradas, no_decl, cumple


def schemaspy():
    rel = {}
    for esq in ESQUEMAS:
        raiz = ET.parse(GRANDES / "schemaspy" / esq / f"mimic_demo.{esq}.xml").getroot()
        for t in raiz.iter("table"):
            for c in t.iter("column"):
                for p in c.iter("parent"):
                    k = (f"{esq}.{t.get('name')}", c.get("name"), f"{p.get('schema') or esq}.{p.get('table')}",
                         p.get("column"))
                    rel[k] = p.get("implied") == "true"
    return {k for k, v in rel.items() if v}, {k for k, v in rel.items() if not v}


def metanome(archivo):
    out = set()
    for l in open(GRANDES / "results" / archivo, encoding="utf-8"):
        d = json.loads(l)
        a, b = d["dependant"]["columnIdentifiers"], d["referenced"]["columnIdentifiers"]
        if len(a) != 1:
            continue
        k = (a[0]["tableIdentifier"].replace("__", "."), a[0]["columnIdentifier"],
             b[0]["tableIdentifier"].replace("__", "."), b[0]["columnIdentifier"])
        if (k[0], k[1]) != (k[2], k[3]):
            out.add(k)
    return out


def perfiles(cur, columnas):
    """Para cada columna: ¿única y sin nulos? ¿tiene algún valor no nulo?"""
    p = {}
    for t, c in sorted(columnas):
        e, n = t.split(".")
        cur.execute(f'select count(*), count("{c}"), count(distinct "{c}") from "{e}"."{n}"')
        filas, no_nulos, distintos = cur.fetchone()
        p[(t, c)] = {"unica": filas > 0 and no_nulos == filas and distintos == filas, "con_valores": no_nulos > 0}
    return p


def medir(nombre, props, declaradas, no_decl, cumple):
    nd = props & no_decl
    d = props & declaradas
    otras = props - declaradas - no_decl
    return {"herramienta": nombre, "propuestas": len(props),
            "declaradas_encontradas": len(d), "de_declaradas": len(declaradas),
            "no_declaradas_encontradas": len(nd), "de_no_declaradas": len(no_decl),
            "no_declaradas_que_se_cumplen": sum(1 for k in nd if cumple[k]),
            "de_las_que_se_cumplen": sum(cumple.values()),
            "recall_no_declaradas": round(len(nd) / len(no_decl), 3),
            "propuestas_fuera_de_la_verdad": len(otras),
            "precision_contra_la_verdad": round((len(nd) + len(d)) / max(len(props), 1), 3),
            "no_encontradas": sorted(f"{k[0]}.{k[1]} -> {k[2]}.{k[3]}" for k in no_decl - props),
            "ejemplos_fuera_de_la_verdad": sorted(f"{k[0]}.{k[1]} -> {k[2]}.{k[3]}" for k in otras)[:40]}


def main():
    con = conectar()
    cur = con.cursor()
    declaradas, no_decl, cumple = verdad(cur)
    ss_impl, ss_decl = schemaspy()
    binder, spider = metanome("binder_inds"), metanome("spider_inds")
    prof = perfiles(cur, {(k[0], k[1]) for k in binder | spider} | {(k[2], k[3]) for k in binder | spider})
    clave = {k for k in binder if prof[(k[2], k[3])]["unica"] and prof[(k[0], k[1])]["con_valores"]}
    clave_nombre = {k for k in clave if k[1] == k[3] or k[1].endswith("_" + k[3]) or k[1].endswith(k[3])}
    llm = set()
    for x in json.loads((AQUI.parent / "F2-relaciones-llm/resultados/mimic.json").read_text())["corridas"][0][
            "fuera_de_la_verdad"]:
        pass
    crudo = json.loads((AQUI.parent / "F2-relaciones-llm/resultados/crudo/mimic_c1.json").read_text())
    llm = {(r["tabla_hija"], r["columna_hija"], r["tabla_padre"], r["columna_padre"]) for r in crudo["relaciones"]}

    res = {"verdad": {"declaradas": len(declaradas), "no_declaradas": len(no_decl),
                      "no_declaradas_que_se_cumplen": sum(cumple.values())},
           "schemaspy_declaradas_que_lee": len(ss_decl & declaradas),
           "binder_igual_a_spider": binder == spider,
           "herramientas": [
               medir("SchemaSpy (relaciones implícitas)", ss_impl, declaradas, no_decl, cumple),
               medir("Metanome BINDER/SPIDER: todas las dependencias de inclusión", binder, declaradas, no_decl, cumple),
               medir("Metanome + filtro: padre único", clave, declaradas, no_decl, cumple),
               medir("Metanome + filtro: padre único + nombre", clave_nombre, declaradas, no_decl, cumple),
               medir("LLM local (F2m, corrida 1)", llm, declaradas, no_decl, cumple),
           ]}
    (AQUI / "resultados").mkdir(exist_ok=True)
    (AQUI / "resultados" / "f2_herramientas.json").write_text(json.dumps(res, indent=2, ensure_ascii=False),
                                                              encoding="utf-8")
    md = ["# F2m: relaciones con SchemaSpy, Metanome y el LLM local", "",
          f"Verdad: {len(declaradas)} FK declaradas y {len(no_decl)} relaciones no declaradas "
          f"({sum(cumple.values())} se cumplen en los datos).", "",
          "| Herramienta | Propuestas | Declaradas | No declaradas | No declaradas que se cumplen | Fuera de la verdad | "
          "Precisión |", "|---|---|---|---|---|---|---|"]
    for h in res["herramientas"]:
        md.append(f"| {h['herramienta']} | {h['propuestas']} | {h['declaradas_encontradas']} de {h['de_declaradas']} | "
                  f"{h['no_declaradas_encontradas']} de {h['de_no_declaradas']} | "
                  f"{h['no_declaradas_que_se_cumplen']} de {h['de_las_que_se_cumplen']} | "
                  f"{h['propuestas_fuera_de_la_verdad']} | {h['precision_contra_la_verdad']} |")
    (AQUI / "resultados" / "f2_herramientas.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    for h in res["herramientas"]:
        print("\n==", h["herramienta"], "\nno encontradas:", h["no_encontradas"], "\nfuera (ej.):",
              h["ejemplos_fuera_de_la_verdad"][:12])


if __name__ == "__main__":
    main()
