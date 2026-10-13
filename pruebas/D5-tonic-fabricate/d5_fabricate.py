#!/usr/bin/env python3
"""Prueba D5: ¿la base que generó Tonic Fabricate respeta el esquema de Pagila?

Carga el .sql exportado de Fabricate dos veces, en bases nuevas (la base común `pagila` solo se lee):

  1. Carga estricta (d5_estricta): esquema de Pagila con todas sus restricciones, como si se
     restaurara en una base real. Las FK se ponen al final (igual que pg_dump), para que el orden de
     los INSERT no cuente como error. Mide si el archivo se puede cargar tal cual y qué rechaza.
  2. Carga para auditar (d5_auditoria): el mismo esquema, sin restricciones. Entra todo y después
     se cuenta, fila por fila, qué viola cada PK, UNIQUE, FK, NOT NULL y CHECK (scripts/integridad.py).

Uso (desde la raíz del repo, con el entorno activado y la base levantada):
    python pruebas/D5-tonic-fabricate/d5_fabricate.py
    python pruebas/D5-tonic-fabricate/d5_fabricate.py --archivo otra/ruta.sql

Deja en resultados/ el resumen (d5_resumen.md) y los CSV, en evidencia/ los errores de carga,
y los logs completos de psql en salidas_grandes/ (no se suben al repo).
"""
import argparse
import datetime
import hashlib
import platform
import re
import sys
from collections import Counter
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import integridad as ig  # noqa: E402


def inspeccionar(ruta):
    """Qué trae el archivo: tamaño, hash y cantidad de sentencias de cada tipo."""
    datos = Path(ruta).read_bytes()
    texto = datos.decode("utf-8", errors="replace")
    contar = lambda p: len(re.findall(p, texto, re.I | re.M))
    return {
        "bytes": len(datos),
        "sha256": hashlib.sha256(datos).hexdigest(),
        "insert": contar(r"^\s*INSERT\s+INTO"),
        "copy": contar(r"^\s*COPY\s+\S+.*FROM\s+stdin"),
        "create_table": contar(r"^\s*CREATE\s+TABLE"),
        "drop": contar(r"^\s*DROP\s+(TABLE|SCHEMA|DATABASE)"),
        "alter_table": contar(r"^\s*ALTER\s+TABLE"),
        "transacciones": contar(r"^\s*(BEGIN|START\s+TRANSACTION)\s*;"),
        "tablas_insert": sorted(set(m.lower() for m in re.findall(
            r'^\s*(?:INSERT\s+INTO|COPY)\s+(?:"?public"?\.)?"?(\w+)"?', texto, re.I | re.M))),
    }


def tabla_md(filas, columnas):
    out = ["| " + " | ".join(columnas) + " |", "|" + "---|" * len(columnas)]
    out += ["| " + " | ".join(str(f.get(c, "")) for c in columnas) + " |" for f in filas]
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--archivo", default=str(AQUI / "salidas_grandes" / "fabricate.sql"),
                    help="el .sql exportado de Fabricate")
    ap.add_argument("--permitir-drop", action="store_true",
                    help="cargar aunque el archivo traiga DROP TABLE/SCHEMA (por defecto se frena)")
    a = ap.parse_args()

    archivo = Path(a.archivo)
    if not archivo.exists():
        sys.exit(f"No encuentro {archivo}. Copiá ahí el .sql de Fabricate o pasalo con --archivo.")
    salidas, res_dir, ev_dir = AQUI / "salidas_grandes", AQUI / "resultados", AQUI / "evidencia"
    for d in (salidas, res_dir, ev_dir):
        d.mkdir(exist_ok=True)

    info = inspeccionar(archivo)
    print(f"Archivo: {archivo.name}, {info['bytes']:,} bytes, {info['insert']} INSERT, {info['copy']} COPY, "
          f"{info['create_table']} CREATE TABLE, {info['drop']} DROP")
    if info["drop"] and not a.permitir_drop:
        sys.exit("El archivo trae DROP TABLE/SCHEMA: reemplazaría el esquema de Pagila y la prueba no mediría "
                 "nada. Sacá esas sentencias (o usá --permitir-drop si sabés lo que hacés).")

    if info["transacciones"]:
        # Con BEGIN/COMMIT, el primer error aborta la transacción y todo lo que sigue se ignora:
        # se cargaría casi nada y no se sabría qué filas están mal. Se carga una copia sin esas líneas.
        sin_tx = salidas / (archivo.stem + "_sin_transacciones.sql")
        patron = re.compile(r"^\s*(BEGIN|START\s+TRANSACTION|COMMIT|END)\s*;\s*$", re.I)
        with open(archivo, encoding="utf-8", errors="replace") as f, open(sin_tx, "w", encoding="utf-8") as g:
            for linea in f:
                if not patron.match(linea):
                    g.write(linea)
        print(f"El archivo trae {info['transacciones']} BEGIN: se carga una copia sin BEGIN/COMMIT ({sin_tx.name}).")
        a_cargar = sin_tx
    else:
        a_cargar = archivo

    with ig.conexion("pagila") as ref:
        restr = ig.restricciones(ref)
        conteo_real = ig.conteos(ref)
        with ref.cursor() as cur:
            cur.execute("show server_version")
            version_pg = cur.fetchone()[0]

    # 1. Carga estricta
    print("1/2 Carga estricta (esquema completo de Pagila)...")
    err_esq, _ = ig.preparar_base("d5_estricta")
    if err_esq:
        sys.exit(f"El esquema de Pagila dio {len(err_esq)} errores al aplicarse; revisar antes de seguir.")
    with ig.conexion("d5_estricta") as c:
        fks = ig.quitar_fks(c)
    seg_estricta, out = ig.cargar_sql("d5_estricta", a_cargar, salidas / "carga_estricta.log")
    err_estricta = ig.parsear_errores(out)
    with ig.conexion("d5_estricta") as c:
        fk_res = ig.poner_fks(c, fks)
        conteo_estricta = ig.conteos(c)

    # 2. Carga para auditar
    print("2/2 Carga sin restricciones y auditoría...")
    _, avisos = ig.preparar_base("d5_auditoria", sin_restricciones=True)
    seg_aud, out = ig.cargar_sql("d5_auditoria", a_cargar, salidas / "carga_auditoria.log")
    err_aud = ig.parsear_errores(out)
    with ig.conexion("d5_auditoria") as c:
        conteo_aud = ig.conteos(c)
        viol = ig.contar_violaciones(c, restr)
    tablas_extra = sorted(set(conteo_aud) - set(conteo_real))

    # --- salidas
    ig.guardar_csv(res_dir / "d5_restricciones.csv", viol, ig.CAMPOS_RESTRICCIONES)
    filas_conteo = [{"tabla": t, "pagila_real": conteo_real.get(t, ""), "fabricate_cargadas_sin_restricciones":
                     conteo_aud.get(t, 0), "fabricate_cargadas_estricta": conteo_estricta.get(t, 0)}
                    for t in sorted(set(conteo_real) | set(conteo_aud))]
    ig.guardar_csv(res_dir / "d5_conteos.csv", filas_conteo, list(filas_conteo[0]))
    errores = [dict(e, fase="estricta") for e in err_estricta] + [dict(e, fase="auditoria") for e in err_aud]
    ig.guardar_csv(ev_dir / "d5_errores_carga.csv", errores,
                   ["fase", "linea", "sqlstate", "tipo", "tabla", "mensaje", "detalle", "contexto"])

    por_tipo = ig.resumen_por_tipo(viol)
    fk_fallidas = [f for f in fk_res if not f[2]]
    ahora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    md = [f"# D5: Tonic Fabricate, integridad de la base generada contra el esquema de Pagila", "",
          f"Corrida: {ahora}", "",
          "## Entorno", "",
          f"- Equipo: {platform.machine()}, {platform.system()} {platform.release()}, Python {platform.python_version()}",
          f"- PostgreSQL {version_pg} (contenedor `pagila-db`), referencia: base `pagila` (pagila-v4.0.0)",
          f"- Archivo de Fabricate: `{archivo.name}`, {info['bytes']:,} bytes, sha256 `{info['sha256'][:16]}…`",
          f"- Contenido: {info['insert']} INSERT, {info['copy']} COPY, {info['create_table']} CREATE TABLE, "
          f"{info['alter_table']} ALTER TABLE"
          + (f"; traía {info['transacciones']} BEGIN y se cargó sin BEGIN/COMMIT" if info["transacciones"] else ""),
          f"- Tiempo de carga: estricta {seg_estricta:.1f} s, sin restricciones {seg_aud:.1f} s",
          "", "## 1. ¿Se puede cargar tal cual? (carga estricta)", "",
          f"Errores de psql: **{len(err_estricta)}** sentencias rechazadas. Cada sentencia rechazada descarta "
          "todas sus filas (un COPY o un INSERT de varias filas falla entero).", ""]
    if err_estricta:
        cnt = Counter((e["tipo"], e["tabla"]) for e in err_estricta)
        md += [tabla_md([{"tipo": t, "tabla": tb, "sentencias": n} for (t, tb), n in cnt.most_common()],
                        ["tipo", "tabla", "sentencias"]), ""]
    md += [f"FK que se pudieron volver a crear después de cargar: **{len(fk_res) - len(fk_fallidas)} de {len(fk_res)}**.", ""]
    if fk_fallidas:
        md += ["FK que fallan (hay filas huérfanas):", ""] + [f"- `{t}.{n}`: {e}" for t, n, _, e in fk_fallidas] + [""]
    md += ["## 2. Violaciones fila por fila (carga sin restricciones)", "",
           tabla_md([{"tipo": t, **d} for t, d in por_tipo.items()],
                    ["tipo", "restricciones", "violadas", "filas", "sin_comprobar"]), "",
           "«filas» = filas que violan (para PK/UNIQUE, filas que sobran por clave repetida).", ""]
    violadas = [v for v in viol if v["estado"] == "violada"]
    if violadas:
        md += ["Restricciones violadas:", "",
               tabla_md([{**v, "columnas": ", ".join(v["columnas"])} for v in violadas],
                        ["tipo", "tabla", "nombre", "columnas", "violaciones", "ejemplos"]), ""]
    otras = [v for v in viol if v["estado"] not in ("ok", "violada")]
    if otras:
        md += ["Sin comprobar: " + ", ".join(f"`{v['nombre']}` ({v['estado']})" for v in otras), ""]
    if err_aud:
        cnt = Counter((e["tipo"], e["tabla"]) for e in err_aud)
        md += ["Errores que quedan aun sin restricciones (tipos, enums, particiones, columnas o tablas que no existen):", "",
               tabla_md([{"tipo": t, "tabla": tb, "sentencias": n} for (t, tb), n in cnt.most_common()],
                        ["tipo", "tabla", "sentencias"]), ""]
    md += ["## 3. Filas por tabla", "",
           tabla_md(filas_conteo, ["tabla", "pagila_real", "fabricate_cargadas_sin_restricciones",
                                   "fabricate_cargadas_estricta"]), ""]
    if tablas_extra:
        md += [f"Tablas que creó el archivo y no existen en Pagila: {', '.join(tablas_extra)}", ""]
    if avisos:
        md += ["## Avisos", ""] + [f"- {x}" for x in avisos] + [""]
    md += ["Detalle: `d5_restricciones.csv`, `d5_conteos.csv` y `../evidencia/d5_errores_carga.csv`. "
           "Logs completos de psql en `salidas_grandes/` (no se suben)."]
    (res_dir / "d5_resumen.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"Carga estricta: {len(err_estricta)} sentencias rechazadas; FK ok {len(fk_res) - len(fk_fallidas)}/{len(fk_res)}")
    for t, d in por_tipo.items():
        print(f"  {t:16} {d['violadas']:3}/{d['restricciones']:<3} violadas, {d['filas']} filas")
    print(f"Listo: {res_dir / 'd5_resumen.md'}")


if __name__ == "__main__":
    main()
