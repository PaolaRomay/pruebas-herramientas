#!/usr/bin/env python3
"""Trae una base de Neon (u otro PostgreSQL remoto) al contenedor local y mide su integridad.

Para las pruebas de Tonic Structural (B4, C2, E6): Structural escribe en `pagila_destino`, en Neon, y
todas las mediciones se hacen sobre una copia local con la misma vara que el resto (scripts/integridad.py
y, para E6, pruebas/E3-chequeos-propios/evaluar_bd.py).

Pasos:
  1. pg_dump --data-only de la base remota, corrido dentro del contenedor. La cadena de conexión se lee
     de la variable (por defecto NEON_DESTINO), del entorno o de .env, y se pasa al contenedor como
     variable de entorno: nunca va en la línea de comandos, ni en el log ni en los archivos de salida.
  2. Crea la base local con el esquema de Pagila SIN restricciones (integridad.preparar_base) y carga el
     dump; así las filas que violan algo entran y se pueden contar.
  3. Cuenta violaciones de PK, UNIQUE, FK, NOT NULL y CHECK contra la base común `pagila`, y filas por
     tabla contra `pagila`.

Uso (desde la raíz del repo, con el entorno activado y el contenedor levantado):
    python scripts/traer_neon.py --base b4_corrida1 --salida pruebas/B4-tonic-structural/resultados/corrida1
    python scripts/traer_neon.py --variable NEON_ORIGEN --base neon_origen --salida /tmp/x   # control

Salidas: `<base>.sql` en salidas_grandes/ de la prueba (no se sube), y en --salida: integridad.csv,
conteos.csv, errores_carga.csv y traer_neon.md.

Si el PostgreSQL de Neon es más nuevo que el pg_dump del contenedor (16), pg_dump se niega
(«server version mismatch»). En ese caso usar un pg_dump de la misma versión mayor, por ejemplo:
    PG_DUMP_CMD="docker run --rm -e {variable} postgres:18" python scripts/traer_neon.py ...
"""
import argparse
import datetime
import hashlib
import os
import shlex
import subprocess
import time
from pathlib import Path

import integridad as ig

RAIZ = Path(__file__).resolve().parents[1]
PG_DUMP_CMD = "docker exec -i -e {variable} pagila-db"


def leer_variable(nombre):
    """Valor de la variable desde el entorno o, si no está, desde .env (sin imprimirlo)."""
    if os.environ.get(nombre):
        return os.environ[nombre]
    env = RAIZ / ".env"
    if env.exists():
        for linea in env.read_text(encoding="utf-8").splitlines():
            clave, _, valor = linea.partition("=")
            if clave.strip() == nombre:
                return valor.strip().strip("'\"")
    raise SystemExit(f"no está definida {nombre} (ni en el entorno ni en .env)")


def volcar(variable, destino):
    """pg_dump --data-only de la base remota a `destino`. Devuelve (segundos, stderr)."""
    env = dict(os.environ, **{variable: leer_variable(variable)})
    prefijo = os.environ.get("PG_DUMP_CMD", PG_DUMP_CMD).format(variable=variable)
    cmd = shlex.split(prefijo) + ["sh", "-c", f'exec pg_dump "${variable}" --data-only --no-owner --no-privileges']
    Path(destino).parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    with open(destino, "wb") as f:
        r = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, env=env)
    err = r.stderr.decode("utf-8", errors="replace").replace(env[variable], f"${variable}")
    if r.returncode != 0:
        raise SystemExit(f"pg_dump falló ({r.returncode}):\n{err}")
    return time.time() - t0, err


def sha256(ruta):
    return hashlib.sha256(Path(ruta).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--variable", default="NEON_DESTINO", help="variable con la cadena de conexión (entorno o .env)")
    ap.add_argument("--base", required=True, help="base local a crear (se borra si existe)")
    ap.add_argument("--salida", required=True, help="carpeta de resultados (CSV y resumen)")
    ap.add_argument("--dump", default=None,
                    help="dónde guardar el .sql (por defecto <prueba>/salidas_grandes/<base>.sql)")
    ap.add_argument("--referencia", default="pagila", help="base de la que se toman restricciones y conteos")
    a = ap.parse_args()

    salida = Path(a.salida)
    # por defecto, en salidas_grandes/ de la prueba (la carpeta que contiene resultados/)
    prueba = next((d.parent for d in [salida, *salida.parents] if d.name == "resultados"), salida)
    dump = Path(a.dump) if a.dump else prueba / "salidas_grandes" / f"{a.base}.sql"

    print(f"pg_dump de ${a.variable} → {dump}", flush=True)
    seg_dump, avisos_dump = volcar(a.variable, dump)
    _, avisos = ig.preparar_base(a.base, sin_restricciones=True)
    seg_carga, out = ig.cargar_sql(a.base, dump, salida / "carga.log")
    errores = ig.parsear_errores(out)

    with ig.conexion(a.referencia) as ref:
        restr = ig.restricciones(ref)
        conteo_ref = ig.conteos(ref)
    with ig.conexion(a.base) as c:
        viol = ig.contar_violaciones(c, restr)
        conteo = ig.conteos(c)

    ig.guardar_csv(salida / "integridad.csv", viol, ig.CAMPOS_RESTRICCIONES)
    filas = [{"tabla": t, a.referencia: conteo_ref.get(t, ""), a.base: conteo.get(t, ""),
              "proporcion": f"{conteo.get(t, 0) / conteo_ref[t]:.4f}" if conteo_ref.get(t) else ""}
             for t in sorted(set(conteo_ref) | set(conteo))]
    ig.guardar_csv(salida / "conteos.csv", filas, ["tabla", a.referencia, a.base, "proporcion"])
    ig.guardar_csv(salida / "errores_carga.csv", errores, list(errores[0]) if errores else ["sin_errores"])

    tot_ref, tot = sum(conteo_ref.values()), sum(conteo.values())
    md = [f"# Copia local de ${a.variable} en `{a.base}`", "",
          f"Corrida: {datetime.datetime.now():%Y-%m-%d %H:%M}", "",
          f"- Dump: `{dump.name}` ({dump.stat().st_size} bytes, sha256 `{sha256(dump)}`), {seg_dump:.0f} s",
          f"- Carga sin restricciones: {seg_carga:.0f} s, {len(errores)} errores (`errores_carga.csv`)",
          f"- Filas: {tot} en total contra {tot_ref} de `{a.referencia}` ({tot / tot_ref:.1%}); detalle en `conteos.csv`",
          "", "| Tipo | Restricciones | Violadas | Filas que violan | Sin comprobar |", "|---|---|---|---|---|"]
    for tipo, d in ig.resumen_por_tipo(viol).items():
        md.append(f"| {tipo} | {d['restricciones']} | {d['violadas']} | {d['filas']} | {d['sin_comprobar']} |")
    if avisos or avisos_dump.strip():
        md += ["", "## Avisos", ""] + [f"- {x}" for x in avisos] + \
              [f"- pg_dump: {x}" for x in avisos_dump.strip().splitlines()]
    (salida / "traer_neon.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
