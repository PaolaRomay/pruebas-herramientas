#!/usr/bin/env python3
"""Prueba B3: ARX (k-anonimato) sobre los datos personales de Pagila.

ARX trabaja con UNA tabla. Se arma el registro «persona» (customer + address + city + country, una fila
por cliente) desde `e3_entrenamiento` (Pagila sin los 200 clientes de control de E3), se anonimiza con
la librería de ARX (Java, en un contenedor) y el resultado se vuelve a escribir en una copia de la base
CON todas sus restricciones, para ver qué se puede representar en el esquema real.

Pasos (desde la raíz del repo, con la base levantada y Docker; Python del .venv del repo):
  exportar    persona.csv + una jerarquía de generalización por cuasi-identificador
  anonimizar  corre ArxB3.java en eclipse-temurin:21-jdk para cada variante (k = 2, 5, 10; con y sin
              supresión) y guarda la tabla anonimizada y las métricas de ARX
  aplicar     por variante: copia e3_entrenamiento en `b3_<variante>` y aplica la anonimización con
              UPDATE (restricciones puestas); mide lo que la base no puede representar
  resumir     arma resultados/b3_resumen.md
Después, por variante:
    .venv/bin/python pruebas/E3-chequeos-propios/evaluar_bd.py evaluar --candidata b3_k5 \\
        --tipo anonimizada --entrenada-con e3_entrenamiento --tablas customer,address,city,country
"""
import argparse
import datetime
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
GRANDES = AQUI / "salidas_grandes"
ENTRADA, SALIDA_ARX, LIB = GRANDES / "entrada", GRANDES / "arx", GRANDES / "lib"
RESULTADOS, EVIDENCIA = AQUI / "resultados", AQUI / "evidencia"
BASE = "e3_entrenamiento"
JAR = "libarx-3.9.2.jar"
IMAGEN_JAVA = "eclipse-temurin:21-jdk"

CUASI = ["district", "postal_code", "city", "country", "create_date"]
# (nombre, k, límite de supresión: fracción de filas que ARX puede eliminar en vez de generalizar,
#  cuasi-identificadores que se generalizan; los demás de CUASI se tapan como identificadores)
VARIANTES = [("k2", 2, 0.10, CUASI), ("k5", 5, 0.10, CUASI), ("k10", 10, 0.10, CUASI),
             ("k5_sin_supresion", 5, 0.0, CUASI),
             ("k5_ciudad_pais_fecha", 5, 0.10, ["city", "country", "create_date"])]
IDENTIFICADORES = ["first_name", "last_name", "email", "address", "phone"]
PERSONA_SQL = """
    select c.customer_id, c.store_id, c.first_name, c.last_name, c.email, a.address, a.phone, a.district,
           coalesce(a.postal_code, '') as postal_code, ci.city, co.country,
           to_char(c.create_date, 'YYYY-MM-DD') as create_date, c.activebool, c.active
    from customer c
    join address a using (address_id)
    join city ci using (city_id)
    join country co using (country_id)
    order by c.customer_id"""
FECHA_SUPRIMIDA = "2022-01-01"   # create_date es NOT NULL y de tipo date: '*' no entra (ver `aplicar`)


def registrar(clave, datos):
    RESULTADOS.mkdir(parents=True, exist_ok=True)
    f = RESULTADOS / "b3_tiempos.json"
    todo = json.loads(f.read_text()) if f.exists() else {}
    todo[clave] = {**datos, "registrado": f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S}"}
    f.write_text(json.dumps(todo, indent=2, ensure_ascii=False), encoding="utf-8")


# ----------------------------------------------------------------------------- exportar

def jerarquias(df):
    """Una fila por valor: valor; nivel 1; nivel 2; ... (todas con la misma cantidad de niveles)."""
    j = {}
    # Código postal: se tapan dígitos de derecha a izquierda (5 niveles) y al final '*'.
    filas = []
    for v in sorted(df["postal_code"].unique()):
        filas.append([v] + [v[:max(len(v) - i, 0)] + "*" * min(i, len(v)) for i in range(1, 5)] + ["*"])
    j["postal_code"] = filas
    j["district"] = [[v, "*"] for v in sorted(df["district"].unique())]
    # Ciudad -> su país -> '*'. Un nombre de ciudad que está en más de un país sube directo a '*'
    # (una jerarquía tiene que darle UN padre a cada valor).
    paises = df.groupby("city")["country"].unique()
    j["city"] = [[c, p[0] if len(p) == 1 else "*", "*"] for c, p in paises.items()]
    j["country"] = [[v, "*"] for v in sorted(df["country"].unique())]
    j["create_date"] = [[v, v[:7], v[:4], "*"] for v in sorted(df["create_date"].unique())]
    return j, [c for c, p in paises.items() if len(p) > 1]


def exportar(a):
    import pandas as pd
    import sqlalchemy as sa
    ENTRADA.mkdir(parents=True, exist_ok=True)
    eng = sa.create_engine(f"postgresql+psycopg2://postgres:postgres@127.0.0.1:55432/{BASE}")
    with eng.connect() as c:
        df = pd.read_sql(sa.text(PERSONA_SQL), c)
    df = df.astype(str)
    for col in df.columns:
        if df[col].str.contains(";").any():
            sys.exit(f"{col} tiene ';', que es el separador del CSV")
    df.to_csv(ENTRADA / "persona.csv", sep=";", index=False)
    jer, ambiguas = jerarquias(df)
    for col, filas in jer.items():
        (ENTRADA / f"jerarquia_{col}.csv").write_text("\n".join(";".join(f) for f in filas) + "\n",
                                                      encoding="utf-8")
    info = {"base": BASE, "filas": len(df), "columnas": list(df.columns),
            "valores_distintos": {c: int(df[c].nunique()) for c in CUASI},
            "niveles_jerarquia": {c: len(f[0]) for c, f in jer.items()},
            "ciudades_en_varios_paises": ambiguas}
    registrar("exportar", info)
    print(json.dumps(info, ensure_ascii=False, indent=2))


# ----------------------------------------------------------------------------- anonimizar

def docker_java(cmd):
    return subprocess.run(["docker", "run", "--rm", "-v", f"{AQUI}:/b3", "-w", "/b3", IMAGEN_JAVA, "sh", "-c", cmd],
                          capture_output=True, text=True)


def anonimizar(a):
    SALIDA_ARX.mkdir(parents=True, exist_ok=True)
    cp = f"salidas_grandes/lib/{JAR}:salidas_grandes/clases"
    r = docker_java(f"mkdir -p salidas_grandes/clases && javac -cp salidas_grandes/lib/{JAR} "
                    f"-d salidas_grandes/clases ArxB3.java && java -version 2>&1 | head -1")
    if r.returncode:
        sys.exit(r.stdout + r.stderr)
    java = r.stdout.strip()
    log = []
    for nombre, k, sup, qis in VARIANTES:
        t0 = time.perf_counter()
        r = docker_java(f"java -Xmx2g -cp {cp} ArxB3 salidas_grandes/entrada salidas_grandes/arx {nombre} {k} {sup} "
                        + ",".join(qis))
        seg = time.perf_counter() - t0
        log.append(f"== {nombre} (k={k}, supresión {sup}) {seg:.1f} s, código {r.returncode}\n{r.stdout}{r.stderr}")
        print(log[-1][:300], flush=True)
        if r.returncode:
            continue
        m = json.loads((SALIDA_ARX / f"{nombre}_metricas.json").read_text())
        m["segundos_contenedor"] = round(seg, 1)
        m["java"] = java
        (RESULTADOS / f"b3_arx_{nombre}.json").write_text(json.dumps(m, indent=2, ensure_ascii=False),
                                                         encoding="utf-8")
    EVIDENCIA.mkdir(parents=True, exist_ok=True)
    (EVIDENCIA / "b3_anonimizar.log").write_text("\n".join(log), encoding="utf-8")


# ----------------------------------------------------------------------------- aplicar

def nivel_fecha(v):
    """Valor de create_date que entra en una columna date: el primer día del intervalo generalizado."""
    if v == "*":
        return FECHA_SUPRIMIDA, "suprimida"
    if len(v) == 4:
        return f"{v}-01-01", "año"
    if len(v) == 7:
        return f"{v}-01", "mes"
    return v, "día"


def aplicar(a):
    import pandas as pd
    from psycopg2 import sql
    sys.path.insert(0, str(RAIZ / "scripts"))
    import integridad as ig

    orig = pd.read_csv(ENTRADA / "persona.csv", sep=";", dtype=str, keep_default_na=False)
    for nombre, _, _, _ in VARIANTES:
        archivo = SALIDA_ARX / f"{nombre}.csv"
        if not archivo.exists():
            print(f"{nombre}: ARX no dio solución, se saltea")
            continue
        anon = pd.read_csv(archivo, sep=";", dtype=str, keep_default_na=False)
        assert (anon["customer_id"] == orig["customer_id"]).all(), "ARX cambió el orden de las filas"
        base = f"b3_{nombre}"
        t0 = time.perf_counter()
        with ig.conexion("postgres") as c, c.cursor() as cur:
            cur.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(base)))
            cur.execute(sql.SQL("CREATE DATABASE {} TEMPLATE {}").format(sql.Identifier(base), sql.Identifier(BASE)))
        conn = ig.conectar(base)
        conn.autocommit = False
        cuenta = {"fecha_" + k: 0 for k in ("día", "mes", "año", "suprimida")}
        cuenta.update(ciudad_conservada=0, ciudad_a_pais=0, ciudad_suprimida=0, pais_suprimido_con_ciudad=0,
                      direcciones_compartidas_con_staff_o_store=0)
        error = None
        try:
            with conn.cursor() as cur:
                cur.execute("select a.address_id from address a where exists (select 1 from staff s where "
                            "s.address_id = a.address_id) or exists (select 1 from store s where s.address_id = a.address_id)")
                compartidas = {r[0] for r in cur.fetchall()}
                cur.execute("select customer_id, address_id, city_id, country_id from customer join address "
                            "using (address_id) join city using (city_id)")
                dueno = {str(r[0]): r[1:] for r in cur.fetchall()}
                cur.execute("select country, country_id from country")
                pais_id = dict(cur.fetchall())
                # Marcadores para lo generalizado: una ciudad '*' por país y un país '*' con su ciudad '*'.
                # La base guarda ciudad -> país por FK: no tiene dónde poner «ciudad oculta, país visible».
                marcadores = {}

                def ciudad_marcador(country_id):
                    if country_id not in marcadores:
                        cur.execute("insert into city (city, country_id) values ('*', %s) returning city_id",
                                    (country_id,))
                        marcadores[country_id] = cur.fetchone()[0]
                    return marcadores[country_id]

                cur.execute("insert into country (country) values ('*') returning country_id")
                pais_oculto = cur.fetchone()[0]
                for o, n in zip(orig.itertuples(index=False), anon.itertuples(index=False)):
                    address_id, city_id, country_id = dueno[o.customer_id]
                    fecha, nivel = nivel_fecha(n.create_date)
                    cuenta["fecha_" + nivel] += 1
                    # Se aplica lo más general entre ciudad y país, para no destapar nada.
                    if n.country == "*" or n.city == "*":
                        nueva_ciudad = ciudad_marcador(pais_oculto)
                        cuenta["ciudad_suprimida"] += 1
                        if n.country == "*" and n.city not in ("*",):
                            cuenta["pais_suprimido_con_ciudad"] += 1
                    elif n.city == o.city:
                        nueva_ciudad = city_id
                        cuenta["ciudad_conservada"] += 1
                    else:   # la ciudad subió a su país
                        nueva_ciudad = ciudad_marcador(pais_id[n.city] if n.city in pais_id else country_id)
                        cuenta["ciudad_a_pais"] += 1
                    cuenta["direcciones_compartidas_con_staff_o_store"] += address_id in compartidas
                    cur.execute("update customer set first_name = %s, last_name = %s, email = %s, create_date = %s "
                                "where customer_id = %s",
                                (n.first_name, n.last_name, n.email, fecha, int(o.customer_id)))
                    cur.execute("update address set address = %s, phone = %s, district = %s, postal_code = %s, "
                                "city_id = %s where address_id = %s",
                                (n.address, n.phone, n.district, n.postal_code, nueva_ciudad, address_id))
            conn.commit()
        except Exception as e:   # con restricciones puestas, una violación corta todo
            conn.rollback()
            error = f"{type(e).__name__}: {str(e)[:300]}"
        finally:
            conn.close()
        seg = time.perf_counter() - t0
        # Relación ciudad <-> código postal: ¿cuántas personas conservan las dos tal cual?
        par = pd.DataFrame({"cp": (anon["postal_code"] == orig["postal_code"]),
                            "ciudad": (anon["city"] == orig["city"])})
        res = {"base": base, "segundos_aplicar": round(seg, 1), "error": error, **cuenta,
               "cp_y_ciudad_conservados": int((par.cp & par.ciudad).sum()),
               "solo_ciudad_conservada": int((~par.cp & par.ciudad).sum()),
               "solo_cp_conservado": int((par.cp & ~par.ciudad).sum()),
               "ninguno": int((~par.cp & ~par.ciudad).sum()),
               "valores_distintos_despues": {c: int(anon[c].nunique()) for c in CUASI}}
        registrar(f"aplicar_{nombre}", res)
        print(json.dumps(res, ensure_ascii=False), flush=True)


# ----------------------------------------------------------------------------- resumir

def tabla_md(filas, columnas):
    out = ["| " + " | ".join(columnas) + " |", "|" + "---|" * len(columnas)]
    out += ["| " + " | ".join(str(f.get(c, "")) for c in columnas) + " |" for f in filas]
    return "\n".join(out)


def resumir(a):
    t = json.loads((RESULTADOS / "b3_tiempos.json").read_text())
    ex = t["exportar"]
    filas_arx, filas_db, filas_e3 = [], [], []
    for nombre, k, sup, qis in VARIANTES:
        f = RESULTADOS / f"b3_arx_{nombre}.json"
        if not f.exists():
            continue
        m = json.loads(f.read_text())
        niveles = ", ".join(f"{q} {n}" for q, n in m.get("nivel_por_cuasi_identificador", {}).items())
        filas_arx.append({"variante": nombre, "k": k, "supresión máx.": f"{sup:.0%}",
                          "cuasi-identificadores": len(qis),
                          "segundos ARX": round(m["segundos_anonimizar"], 2),
                          "segundos con contenedor": m["segundos_contenedor"],
                          "filas suprimidas": m.get("filas_suprimidas"), "clases": m.get("clases_equivalencia"),
                          "clase mín / prom.": f"{m.get('clase_min')} / {m.get('clase_promedio', 0):.1f}",
                          "riesgo máx. antes → después": f"{m['riesgo_antes']['riesgo_maximo']:.2f} → "
                          f"{m.get('riesgo_despues', {}).get('riesgo_maximo', float('nan')):.2f}",
                          "riesgo prom. antes → después": f"{m['riesgo_antes']['riesgo_promedio']:.3f} → "
                          f"{m.get('riesgo_despues', {}).get('riesgo_promedio', float('nan')):.3f}",
                          "niveles": niveles})
        ap = t.get(f"aplicar_{nombre}")
        if ap:
            filas_db.append({"variante": nombre, "carga": "ok" if not ap["error"] else ap["error"],
                             "segundos": ap["segundos_aplicar"],
                             "fecha día/mes/año/*": f"{ap['fecha_día']}/{ap['fecha_mes']}/{ap['fecha_año']}/{ap['fecha_suprimida']}",
                             "ciudad igual / a país / oculta": f"{ap['ciudad_conservada']}/{ap['ciudad_a_pais']}/{ap['ciudad_suprimida']}",
                             "CP y ciudad intactos": ap["cp_y_ciudad_conservados"],
                             "direcciones de staff/store tocadas": ap["direcciones_compartidas_con_staff_o_store"]})
        e3 = RAIZ / "pruebas/E3-chequeos-propios/resultados" / f"b3_{nombre}"
        if (e3 / "e3_privacidad.csv").exists():
            import pandas as pd
            p = pd.read_csv(e3 / "e3_privacidad.csv")
            d = pd.read_csv(e3 / "e3_dcr.csv") if (e3 / "e3_dcr.csv").exists() else None
            q = pd.read_csv(e3 / "e3_calidad_propiedades.csv") if (e3 / "e3_calidad_propiedades.csv").exists() else None
            import re
            texto = (e3 / "e3_resumen.md").read_text()
            cal = re.search(r"\*\*Calidad: ([0-9.]+)\*\*, \*\*diagnóstico: ([0-9.]+)", texto)
            fila = {"variante": nombre, "calidad / diagnóstico": f"{cal.group(1)} / {cal.group(2)}" if cal else ""}
            if q is not None:
                fila["Column Shapes"] = f"{q[q.Property == 'Column Shapes'].Score.iloc[0]:.3f}"
            for r in p.itertuples():
                nombre_ataque = r.ataque if r.ataque != "inference" else f"inference {str(r.detalle).split()[-1]}"
                if r.ataque == "singling out":
                    nombre_ataque += " " + str(r.detalle).split()[0]
                fila[nombre_ataque] = f"{r.riesgo:.3f}" if r.riesgo == r.riesgo else ""
            if d is not None:
                fila["copias exactas"] = f"{d.copias_exactas.iloc[0]:.0%}"
                fila["índice de memorización"] = f"{d.indice_memorizacion.iloc[0]:.2f}"
            filas_e3.append(fila)
    cols_e3 = list(dict.fromkeys(k for f in filas_e3 for k in f))
    md = ["# B3: ARX (k-anonimato) sobre el registro «persona» de Pagila", "",
          f"Corrida: {datetime.datetime.now():%Y-%m-%d %H:%M}", "",
          f"- Equipo: {platform.machine()}, macOS {platform.mac_ver()[0]}. ARX {json.loads((RESULTADOS / 'b3_arx_k5.json').read_text()).get('arx')} "
          f"(libarx, Java en `{IMAGEN_JAVA}`)",
          f"- Datos: `{ex['base']}`, {ex['filas']} personas. Valores distintos por cuasi-identificador: {ex['valores_distintos']}",
          f"- Identificadores (se tapan con '*'): {', '.join(IDENTIFICADORES)}. Cuasi-identificadores: {', '.join(CUASI)}",
          f"- Ciudades con el mismo nombre en más de un país (suben directo a '*'): {ex['ciudades_en_varios_paises']}", "",
          "## Resultado de ARX", "", tabla_md(filas_arx, list(filas_arx[0])) if filas_arx else "(sin resultados)", "",
          "Niveles: 0 = sin cambio. postal_code 0–5 (dígitos tapados), district 0–1, city 0–2 (ciudad, país, '*'), "
          "country 0–1, create_date 0–3 (día, mes, año, '*').", "",
          "## Vuelta a la base (con todas las restricciones)", "",
          tabla_md(filas_db, list(filas_db[0])) if filas_db else "(sin resultados)", "",
          "## Privacidad y calidad con E3", "",
          tabla_md(filas_e3, cols_e3) if filas_e3 else "(correr E3 sobre b3_<variante>)", ""]
    (RESULTADOS / "b3_resumen.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for c in ("exportar", "anonimizar", "aplicar", "resumir"):
        sub.add_parser(c)
    a = ap.parse_args()
    {"exportar": exportar, "anonimizar": anonimizar, "aplicar": aplicar, "resumir": resumir}[a.cmd](a)


if __name__ == "__main__":
    main()
