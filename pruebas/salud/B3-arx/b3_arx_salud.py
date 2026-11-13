#!/usr/bin/env python3
"""B3m / B3s: ARX como medidor del riesgo de reidentificación del registro «paciente».

Un registro por paciente con sus cuasi-identificadores y un atributo sensible (el diagnóstico o la primera condición).
ARX mide el riesgo (modelo del fiscal: 1 / tamaño de la clase de equivalencia) y busca la generalización mínima que
cumple k-anonimato (y l-diversidad distinta sobre el atributo sensible).

Conjuntos medidos:
  <base>_subconjunto   el subconjunto de C1 antes de enmascarar (lo que se entregaría sin B1);
  <base>_b1            el mismo después de B1 «consistentes» (MIMIC: edad por década; Synthea: zip a 3 dígitos);
  <base>_completa      la base entera (MIMIC demo: 100 pacientes; Synthea: 1 151), para ver el efecto del tamaño.

Cuasi-identificadores:
  MIMIC: sexo, edad (anchor_age), raza, seguro, idioma, estado civil (de la primera internación).
  Synthea: sexo, edad (al 2026-01-01), raza, etnia, estado civil, zip de 3 dígitos.
Sensible:
  MIMIC: grupo del diagnóstico principal de la primera internación (versión CIE + primer carácter del código).
  Synthea: la primera condición diagnosticada (descripción).

Los CSV con los registros quedan en salidas_grandes/ (fuera del repo); solo se guardan las métricas.
Uso:  .venv/bin/python pruebas/salud/B3-arx/b3_arx_salud.py
Salida: resultados/b3_metricas.json y b3_resumen.md
"""
import json
import subprocess
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[2]
TRABAJO = AQUI / "salidas_grandes"
JAR = RAIZ / "pruebas" / "B3-arx" / "salidas_grandes" / "lib" / "libarx-3.9.2.jar"
IMAGEN = "eclipse-temurin:21-jdk"
CONFIGS = [(2, 1), (5, 1), (5, 2)]   # (k, l)
SUPRESION = 0.1

Q_MIMIC = """
select p.subject_id as id, p.gender as sexo, p.anchor_age as edad,
       coalesce(a.race, 'NA') as raza, coalesce(a.insurance, 'NA') as seguro, coalesce(a.language, 'NA') as idioma,
       coalesce(a.marital_status, 'NA') as estado_civil, coalesce(d.grupo, 'NA') as diagnostico
from mimiciv_hosp.patients p
left join lateral (select * from mimiciv_hosp.admissions a where a.subject_id = p.subject_id
                   order by admittime limit 1) a on true
left join lateral (select d.icd_version || '-' || left(d.icd_code, 1) as grupo from mimiciv_hosp.diagnoses_icd d
                   where d.hadm_id = a.hadm_id order by seq_num limit 1) d on true
order by 1"""
Q_SYNTHEA = """
select p.id, p.gender as sexo,
       (date_part('year', age(date '2026-01-01', p.birthdate::date)))::int as edad,
       p.race as raza, p.ethnicity as etnia, coalesce(nullif(p.marital, ''), 'NA') as estado_civil,
       coalesce((p.zip / 100)::text, 'NA') as zip3, coalesce(c.description, 'NA') as condicion
from synthea.patients p
left join lateral (select description from synthea.conditions c where c.patient = p.id
                   order by start, description limit 1) c on true
order by 1"""
BASES = {
    "mimic": dict(q=Q_MIMIC, cuasi=["sexo", "edad", "raza", "seguro", "idioma", "estado_civil"], sensible="diagnostico",
                  fuentes={"subconjunto": ("pagila-db", "mimic_c1_50"), "b1": ("salud-anon", "b1m_consistentes"),
                           "completa": ("pagila-db", "mimic_demo")}),
    "synthea": dict(q=Q_SYNTHEA, cuasi=["sexo", "edad", "raza", "etnia", "estado_civil", "zip3"], sensible="condicion",
                    fuentes={"subconjunto": ("pagila-db", "synthea_c1_10"), "b1": ("salud-anon", "b1s_consistentes"),
                             "completa": ("pagila-db", "synthea_p1000")}),
}


def consultar(cont, db, q):
    r = subprocess.run(["docker", "exec", "-i", cont, "psql", "-U", "postgres", "-X", "-q", "-A", "-F", ";",
                        "-P", "footer=off", "-d", db, "-c", q], capture_output=True, check=True)
    return r.stdout.decode().strip().splitlines()


def jerarquia(col, valores):
    """Niveles de generalización: edad en rangos de 5, 10 y 20 años; raza por su primera palabra; resto, valor o *."""
    filas = []
    for v in sorted(set(valores)):
        if col == "edad":
            e = int(v)
            filas.append([v, f"{e // 5 * 5}-{e // 5 * 5 + 4}", f"{e // 10 * 10}-{e // 10 * 10 + 9}",
                          f"{e // 20 * 20}-{e // 20 * 20 + 19}", "*"])
        elif col == "raza":
            filas.append([v, v.replace("/", " ").split(" ")[0], "*"])
        elif col == "zip3":
            filas.append([v, v[:-1] + "*" if len(v) > 1 else "*", "*"])
        else:
            filas.append([v, "*"])
    return filas


def main():
    TRABAJO.mkdir(exist_ok=True)
    if not JAR.exists():
        raise SystemExit(f"falta {JAR}: se baja con pruebas/B3-arx/b3_arx.py (paso exportar)")
    (TRABAJO / "lib").mkdir(exist_ok=True)
    (TRABAJO / "lib" / JAR.name).write_bytes(JAR.read_bytes())
    docker = ["docker", "run", "--rm", "-v", f"{AQUI}:/b3", "-w", "/b3", IMAGEN, "sh", "-c"]
    subprocess.run(docker + [f"mkdir -p salidas_grandes/clases && javac -cp salidas_grandes/lib/{JAR.name} "
                             f"-d salidas_grandes/clases ArxMedidor.java"], check=True, capture_output=True)
    metricas = []
    for base, cfg in BASES.items():
        for nombre, (cont, db) in cfg["fuentes"].items():
            lineas = consultar(cont, db, cfg["q"])
            cab, filas = lineas[0].split(";"), [l.split(";") for l in lineas[1:]]
            d = TRABAJO / f"{base}_{nombre}"
            d.mkdir(exist_ok=True)
            (d / f"{base}_{nombre}.csv").write_text("\n".join(lineas) + "\n", encoding="utf-8")
            for c in cfg["cuasi"]:
                j = jerarquia(c, [f[cab.index(c)] for f in filas])
                (d / f"jerarquia_{c}.csv").write_text("\n".join(";".join(x) for x in j) + "\n", encoding="utf-8")
            for k, l in CONFIGS:
                cmd = (f"java -Xmx2g -cp salidas_grandes/lib/{JAR.name}:salidas_grandes/clases ArxMedidor "
                       f"salidas_grandes/{base}_{nombre} {base}_{nombre} {k} {l} {SUPRESION} "
                       f"{','.join(cfg['cuasi'])} {cfg['sensible']}")
                r = subprocess.run(docker + [cmd], capture_output=True, text=True)
                if r.returncode != 0:
                    raise RuntimeError(r.stderr[-1500:])
                m = json.loads(r.stdout.strip().splitlines()[-1])
                m["base"], m["conjunto"] = base, nombre
                m["valores_distintos_sensible"] = len({f[cab.index(cfg['sensible'])] for f in filas})
                metricas.append(m)
                print(base, nombre, k, l, m.get("filas_suprimidas"), m.get("nivel_por_cuasi_identificador"),
                      m["riesgo_antes"]["fraccion_unicos"], flush=True)
    sal = AQUI / "resultados"
    sal.mkdir(exist_ok=True)
    (sal / "b3_metricas.json").write_text(json.dumps(metricas, indent=2, ensure_ascii=False), encoding="utf-8")
    md = ["# B3m / B3s: ARX como medidor del registro «paciente»", "",
          f"Supresión máxima {SUPRESION:.0%}. Riesgo = modelo del fiscal (1 / tamaño de la clase).", "",
          "| Base | Conjunto | Filas | k | l | Únicos antes | Riesgo máx. antes | Solución | Suprimidas | "
          "Niveles | Riesgo máx. después |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for m in metricas:
        ra, rd = m["riesgo_antes"], m.get("riesgo_despues", {})
        md.append(f"| {m['base']} | {m['conjunto']} | {m['filas']} | {m['k']} | {m['l']} | "
                  f"{ra['fraccion_unicos']:.0%} | {ra['riesgo_maximo']:.2f} | {'sí' if m['solucion_encontrada'] else 'no'} | "
                  f"{m.get('filas_suprimidas', '—')} | {m.get('nivel_por_cuasi_identificador', '—')} | "
                  f"{rd.get('riesgo_maximo', float('nan')):.2f} |")
    (sal / "b3_resumen.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
