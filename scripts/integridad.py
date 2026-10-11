#!/usr/bin/env python3
"""Verificación de integridad de una base contra las restricciones de Pagila.

Sirve para cualquier prueba que produzca una base (o un .sql) con el esquema de Pagila:
síntesis (D), anonimización (B), subconjuntos (C) y los chequeos propios de E3.

Toma las restricciones de la base de referencia (`pagila`, la base común, que solo se lee) y
cuenta, fila por fila, cuántas las violan en la base auditada:

  PK / UNIQUE   filas que repiten una clave (incluye los índices únicos que no son constraint)
  FK            filas hijas cuya clave no existe en la tabla padre (huérfanas)
  NOT NULL      filas con NULL en una columna obligatoria
  CHECK         filas que no cumplen un CHECK de tabla o de dominio (por ejemplo `year`)

Para que los conteos signifiquen algo, la base auditada tiene que haberse cargado SIN
restricciones (si no, la propia carga ya rechazó las filas malas). `preparar_base(...,
sin_restricciones=True)` crea una base así a partir del esquema de Pagila.

Uso como script (sobre una base ya cargada):
    python scripts/integridad.py --base mi_base --salida pruebas/X/resultados
Uso como módulo: ver pruebas/D5-tonic-fabricate/d5_fabricate.py.

Conexión: por defecto la del README (127.0.0.1:55432, postgres/postgres). Se puede cambiar
con las variables PGHOST, PGPORT, PGUSER y PGPASSWORD. Los .sql se cargan con psql dentro del
contenedor (`docker exec -i pagila-db psql`); para otro psql, definir PSQL_CMD.
"""
import argparse
import csv
import os
import re
import shlex
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path

import psycopg2
from psycopg2 import sql

RAIZ = Path(__file__).resolve().parents[1]
ESQUEMA_PAGILA = RAIZ / "data" / "pagila" / "01-schema.sql"

# Errores de PostgreSQL más comunes al cargar datos, por SQLSTATE.
SQLSTATE = {
    "23503": "FK (clave foránea)",
    "23505": "PK/UNIQUE (duplicado)",
    "23514": "CHECK",
    "23502": "NOT NULL",
    "22P02": "tipo o valor inválido",
    "22007": "fecha u hora inválida",
    "22008": "fecha u hora fuera de rango",
    "22003": "número fuera de rango",
    "22001": "texto demasiado largo",
    "42P01": "tabla inexistente",
    "42703": "columna inexistente",
    "42P07": "objeto ya existe (DDL ignorada)",
    "42710": "objeto ya existe (DDL ignorada)",
    "42601": "error de sintaxis",
    "25P02": "ignorada (transacción abortada por un error anterior)",
}


# ----------------------------------------------------------------------------- conexión

def conectar(base):
    c = psycopg2.connect(
        host=os.environ.get("PGHOST", "127.0.0.1"),
        port=int(os.environ.get("PGPORT", "55432")),
        user=os.environ.get("PGUSER", "postgres"),
        password=os.environ.get("PGPASSWORD", "postgres"),
        dbname=base,
    )
    c.autocommit = True
    return c


@contextmanager
def conexion(base):
    """`with conexion("pagila") as c:` abre, entrega y cierra (sin abrir transacción)."""
    c = conectar(base)
    try:
        yield c
    finally:
        c.close()


def psql_cmd(base):
    base_cmd = os.environ.get("PSQL_CMD", "docker exec -i pagila-db psql -U postgres")
    return shlex.split(base_cmd) + ["-X", "-q", "-v", "ON_ERROR_STOP=0", "-v", "VERBOSITY=verbose", "-d", base, "-f", "-"]


def crear_base(nombre):
    """Crea la base `nombre` vacía; si existe, la borra antes. Nunca toca `pagila`."""
    if nombre in ("pagila", "postgres", "template0", "template1"):
        raise ValueError(f"no se puede recrear la base {nombre}")
    with conexion("postgres") as c, c.cursor() as cur:
        cur.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(nombre)))
        cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(nombre)))


def cargar_sql(base, archivo, log=None):
    """Carga un .sql con psql sin cortar en el primer error. Devuelve (segundos, salida de psql)."""
    t0 = time.time()
    with open(archivo, "rb") as f:
        r = subprocess.run(psql_cmd(base), stdin=f, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    seg = time.time() - t0
    salida = r.stdout.decode("utf-8", errors="replace")
    if log:
        Path(log).parent.mkdir(parents=True, exist_ok=True)
        Path(log).write_text(salida, encoding="utf-8")
    return seg, salida


def parsear_errores(salida):
    """Una fila por cada ERROR que reportó psql: línea del archivo, SQLSTATE, tipo, tabla, mensaje."""
    errores = []
    lineas = salida.splitlines()
    for i, l in enumerate(lineas):
        m = re.search(r"(?:psql:[^:]*:(\d+): )?ERROR:\s+([0-9A-Z]{5}): (.*)", l)
        if not m:
            continue
        linea, estado, msg = m.groups()
        detalle, contexto, tabla = "", "", ""
        for extra in lineas[i + 1:i + 9]:
            if "ERROR:" in extra:
                break
            if extra.startswith("DETAIL:"):
                detalle = extra[7:].strip()
            elif extra.startswith("CONTEXT:"):
                contexto = extra[8:].strip()
            elif extra.startswith("TABLE NAME:"):
                tabla = extra[11:].strip()
        if not tabla:
            for patron in (r'on table "([^"]+)"', r'of relation "([^"]+)"', r'relation "([^"]+)"', r"COPY (\w+)"):
                t = re.search(patron, msg + " " + contexto)
                if t:
                    tabla = t.group(1)
                    break
        tipo = SQLSTATE.get(estado, "otro")
        if estado == "23514" and "no partition" in msg:
            tipo = "fuera de las particiones"
        errores.append({"linea": int(linea) if linea else "", "sqlstate": estado, "tipo": tipo, "tabla": tabla,
                        "mensaje": msg.strip(), "detalle": detalle, "contexto": contexto})
    return errores


# ----------------------------------------------------------------------------- catálogo

def tablas_base(conn):
    """Tablas de public (las particiones se cuentan dentro de su tabla padre)."""
    with conn.cursor() as cur:
        cur.execute("""select c.relname from pg_class c
                       where c.relnamespace = 'public'::regnamespace and c.relkind in ('r','p')
                         and not c.relispartition order by 1""")
        return [r[0] for r in cur.fetchall()]


def conteos(conn):
    out = {}
    with conn.cursor() as cur:
        for t in tablas_base(conn):
            cur.execute(sql.SQL("select count(*) from public.{}").format(sql.Identifier(t)))
            out[t] = cur.fetchone()[0]
    return out


def restricciones(conn):
    """Restricciones de la base (normalmente la referencia `pagila`), en un formato que se puede
    volver a comprobar en otra base: tipo, tabla, nombre, columnas y lo necesario para el chequeo."""
    res = []
    with conn.cursor() as cur:
        # PK, UNIQUE, FK y CHECK de tabla (sin las copias heredadas por las particiones)
        cur.execute("""
            select con.contype, rel.relname, con.conname,
                   array(select a.attname from unnest(con.conkey) with ordinality k(n, o)
                         join pg_attribute a on a.attrelid = con.conrelid and a.attnum = k.n order by k.o),
                   fr.relname,
                   array(select a.attname from unnest(con.confkey) with ordinality k(n, o)
                         join pg_attribute a on a.attrelid = con.confrelid and a.attnum = k.n order by k.o),
                   pg_get_constraintdef(con.oid)
            from pg_constraint con
            join pg_class rel on rel.oid = con.conrelid
            left join pg_class fr on fr.oid = con.confrelid
            where con.connamespace = 'public'::regnamespace and con.conparentid = 0
              and con.contype in ('p','u','f','c') and rel.relkind in ('r','p')
            order by 1, 2, 3""")
        tipos = {"p": "PK", "u": "UNIQUE", "f": "FK", "c": "CHECK"}
        for ct, tabla, nombre, cols, ftabla, fcols, defin in cur.fetchall():
            r = {"tipo": tipos[ct], "tabla": tabla, "nombre": nombre, "columnas": list(cols),
                 "definicion": defin}
            if ct == "f":
                r["ref_tabla"], r["ref_columnas"] = ftabla, list(fcols)
            if ct == "c":
                r["expresion"] = re.sub(r"^CHECK \((.*)\)( NOT VALID)?$", r"\1", defin)
            res.append(r)
        # Índices únicos que no son constraint (en Pagila: uuid, rental_date+inventory+customer...)
        cur.execute("""
            select rel.relname, ic.relname,
                   array(select a.attname from unnest(i.indkey::int2[]) with ordinality k(n, o)
                         join pg_attribute a on a.attrelid = i.indrelid and a.attnum = k.n order by k.o),
                   pg_get_expr(i.indpred, i.indrelid), i.indexprs is not null, pg_get_indexdef(i.indexrelid)
            from pg_index i join pg_class rel on rel.oid = i.indrelid join pg_class ic on ic.oid = i.indexrelid
            where rel.relnamespace = 'public'::regnamespace and i.indisunique and rel.relkind in ('r','p')
              and not rel.relispartition
              and not exists (select 1 from pg_constraint c where c.conindid = i.indexrelid)
            order by 1, 2""")
        for tabla, nombre, cols, pred, con_expr, defin in cur.fetchall():
            res.append({"tipo": "UNIQUE (índice)", "tabla": tabla, "nombre": nombre, "columnas": list(cols),
                        "predicado": pred, "con_expresion": con_expr, "definicion": defin})
        # NOT NULL
        cur.execute("""
            select c.relname, a.attname from pg_attribute a join pg_class c on c.oid = a.attrelid
            where c.relnamespace = 'public'::regnamespace and c.relkind in ('r','p') and not c.relispartition
              and a.attnum > 0 and not a.attisdropped and a.attnotnull order by 1, a.attnum""")
        for tabla, col in cur.fetchall():
            res.append({"tipo": "NOT NULL", "tabla": tabla, "nombre": f"{tabla}.{col}", "columnas": [col],
                        "definicion": "NOT NULL"})
        # CHECK de dominios (por ejemplo film.release_year de tipo `year`)
        cur.execute("""
            select c.relname, a.attname, t.typname, pg_get_constraintdef(con.oid), format_type(t.typbasetype, t.typtypmod)
            from pg_attribute a join pg_class c on c.oid = a.attrelid join pg_type t on t.oid = a.atttypid
            join pg_constraint con on con.contypid = t.oid
            where c.relnamespace = 'public'::regnamespace and c.relkind in ('r','p') and not c.relispartition
              and a.attnum > 0 and not a.attisdropped and t.typtype = 'd' and con.contype = 'c'""")
        for tabla, col, dominio, defin, tipo_base in cur.fetchall():
            expr = re.sub(r"^CHECK \((.*)\)$", r"\1", defin)
            expr = re.sub(r"\bVALUE\b", sql.Identifier(col).as_string(conn), expr)
            res.append({"tipo": "CHECK (dominio)", "tabla": tabla, "nombre": f"{dominio} en {tabla}.{col}",
                        "columnas": [col], "definicion": defin, "expresion": expr, "dominio": dominio,
                        "tipo_base": tipo_base})
    return res


def _cols(nombres, alias=None):
    ids = [sql.Identifier(n) if alias is None else sql.SQL("{}.{}").format(sql.Identifier(alias), sql.Identifier(n))
           for n in nombres]
    return sql.SQL(", ").join(ids)


def contar_violaciones(conn, restr, ejemplos=3):
    """Agrega a cada restricción `violaciones` (filas que la violan), `ejemplos` y `estado`
    (`ok`, `violada`, `tabla vacía o ausente`, `no comprobada`)."""
    with conn.cursor() as cur:
        cur.execute("select relname from pg_class where relnamespace = 'public'::regnamespace and relkind in ('r','p')")
        existentes = {r[0] for r in cur.fetchall()}
    out = []
    with conn.cursor() as cur:
        for r in restr:
            r = dict(r)
            t = sql.Identifier(r["tabla"])
            if r["tabla"] not in existentes or (r["tipo"] == "FK" and r["ref_tabla"] not in existentes):
                r.update(violaciones=None, ejemplos="", estado="tabla ausente")
                out.append(r)
                continue
            try:
                if r["tipo"] in ("PK", "UNIQUE", "UNIQUE (índice)"):
                    if r.get("con_expresion"):
                        r.update(violaciones=None, ejemplos="", estado="no comprobada (índice con expresión)")
                        out.append(r)
                        continue
                    pred = sql.SQL(" and ({})").format(sql.SQL(r["predicado"])) if r.get("predicado") else sql.SQL("")
                    q = sql.SQL("""select coalesce(sum(n - 1), 0), (array_agg(k order by n desc))[1:{e}]
                                   from (select count(*) n, row({c})::text k from public.{t}
                                         where num_nulls({c}) = 0 {p} group by {c} having count(*) > 1) s""").format(
                        c=_cols(r["columnas"]), t=t, p=pred, e=sql.Literal(ejemplos))
                elif r["tipo"] == "FK":
                    cond = sql.SQL(" and ").join(
                        sql.SQL("p.{} = h.{}").format(sql.Identifier(pc), sql.Identifier(hc))
                        for pc, hc in zip(r["ref_columnas"], r["columnas"]))
                    q = sql.SQL("""select count(*), (array_agg(distinct row({hc})::text))[1:{e}] from public.{t} h
                                   where num_nulls({hc}) = 0
                                     and not exists (select 1 from public.{rt} p where {cond})""").format(
                        hc=_cols(r["columnas"], "h"), t=t, rt=sql.Identifier(r["ref_tabla"]), cond=cond,
                        e=sql.Literal(ejemplos))
                elif r["tipo"] == "NOT NULL":
                    q = sql.SQL("select count(*), null::text[] from public.{t} where {c} is null").format(
                        t=t, c=sql.Identifier(r["columnas"][0]))
                elif r["tipo"] in ("CHECK", "CHECK (dominio)"):
                    q = sql.SQL("""select count(*), (array_agg(row({c})::text))[1:{e}] from public.{t}
                                   where ({x}) is false""").format(
                        t=t, x=sql.SQL(r["expresion"]), c=_cols(r["columnas"]) if r["columnas"] else sql.SQL("1"),
                        e=sql.Literal(ejemplos))
                else:
                    continue
                cur.execute(q)
                n, ej = cur.fetchone()
                r.update(violaciones=int(n), ejemplos="; ".join(ej or []), estado="ok" if n == 0 else "violada")
            except psycopg2.Error as e:
                r.update(violaciones=None, ejemplos="", estado=f"no comprobada ({e.pgcode})")
            out.append(r)
    return out


# ----------------------------------------------------------------------------- preparar bases

def quitar_fks(conn):
    """Quita las FK y devuelve su definición para volver a ponerlas con poner_fks()."""
    fks = []
    with conn.cursor() as cur:
        cur.execute("""select rel.relname, con.conname, pg_get_constraintdef(con.oid)
                       from pg_constraint con join pg_class rel on rel.oid = con.conrelid
                       where con.connamespace = 'public'::regnamespace and con.contype = 'f'
                         and con.conparentid = 0 order by 1, 2""")
        fks = cur.fetchall()
        for tabla, nombre, _ in fks:
            cur.execute(sql.SQL("alter table public.{} drop constraint {}").format(
                sql.Identifier(tabla), sql.Identifier(nombre)))
    return fks


def poner_fks(conn, fks):
    """Vuelve a crear cada FK (PostgreSQL valida todas las filas). Devuelve [(tabla, nombre, ok, error)]."""
    out = []
    with conn.cursor() as cur:
        for tabla, nombre, defin in fks:
            try:
                cur.execute(sql.SQL("alter table public.{} add constraint {} ").format(
                    sql.Identifier(tabla), sql.Identifier(nombre)) + sql.SQL(defin))
                out.append((tabla, nombre, True, ""))
            except psycopg2.Error as e:
                out.append((tabla, nombre, False, (e.pgerror or "").strip().splitlines()[0]))
    return out


def quitar_todo(conn):
    """Deja las tablas sin restricciones (para cargar todo y después contar violaciones).
    Conserva tipos, enums y particiones. Devuelve una lista de avisos."""
    avisos = []
    with conn.cursor() as cur:
        quitar_fks(conn)
        cur.execute("""select rel.relname, con.conname from pg_constraint con join pg_class rel on rel.oid = con.conrelid
                       where con.connamespace = 'public'::regnamespace and con.contype in ('p','u','c','x')
                         and con.conparentid = 0 and rel.relkind in ('r','p')""")
        for tabla, nombre in cur.fetchall():
            cur.execute(sql.SQL("alter table public.{} drop constraint {}").format(
                sql.Identifier(tabla), sql.Identifier(nombre)))
        cur.execute("""select ic.relname from pg_index i join pg_class ic on ic.oid = i.indexrelid
                       join pg_class rel on rel.oid = i.indrelid
                       where rel.relnamespace = 'public'::regnamespace and i.indisunique
                         and rel.relkind in ('r','p') and not rel.relispartition""")
        for (indice,) in cur.fetchall():
            cur.execute(sql.SQL("drop index if exists public.{}").format(sql.Identifier(indice)))
        # columnas de un dominio con CHECK -> tipo base, para que la carga no las rechace
        cur.execute("""select c.relname, a.attname, format_type(t.typbasetype, t.typtypmod)
                       from pg_attribute a join pg_class c on c.oid = a.attrelid join pg_type t on t.oid = a.atttypid
                       where c.relnamespace = 'public'::regnamespace and c.relkind in ('r','p') and not c.relispartition
                         and a.attnum > 0 and not a.attisdropped and t.typtype = 'd'
                         and exists (select 1 from pg_constraint k where k.contypid = t.oid)""")
        for tabla, col, base in cur.fetchall():
            try:
                cur.execute(sql.SQL("alter table public.{} alter column {} type ").format(
                    sql.Identifier(tabla), sql.Identifier(col)) + sql.SQL(base))
            except psycopg2.Error as e:
                avisos.append(f"no se pudo cambiar el tipo de {tabla}.{col}: {e.pgcode}")
        cur.execute("""select c.relname, a.attname from pg_attribute a join pg_class c on c.oid = a.attrelid
                       where c.relnamespace = 'public'::regnamespace and c.relkind in ('r','p') and not c.relispartition
                         and a.attnum > 0 and not a.attisdropped and a.attnotnull""")
        for tabla, col in cur.fetchall():
            try:
                cur.execute(sql.SQL("alter table public.{} alter column {} drop not null").format(
                    sql.Identifier(tabla), sql.Identifier(col)))
            except psycopg2.Error as e:
                avisos.append(f"NOT NULL de {tabla}.{col} se mantiene ({e.pgcode})")
    return avisos


def preparar_base(nombre, sin_restricciones=False, esquema=ESQUEMA_PAGILA):
    """Crea `nombre` con el esquema de Pagila. Con sin_restricciones=True le saca PK, UNIQUE, FK,
    CHECK y NOT NULL. Devuelve (errores al aplicar el esquema, avisos)."""
    crear_base(nombre)
    _, salida = cargar_sql(nombre, esquema)
    errores = parsear_errores(salida)
    avisos = []
    if sin_restricciones:
        with conexion(nombre) as c:
            avisos = quitar_todo(c)
    return errores, avisos


# ----------------------------------------------------------------------------- salidas

def guardar_csv(ruta, filas, campos):
    Path(ruta).parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore")
        w.writeheader()
        for fila in filas:
            w.writerow({k: (", ".join(v) if isinstance(v, list) else v) for k, v in fila.items()})


CAMPOS_RESTRICCIONES = ["tipo", "tabla", "nombre", "columnas", "ref_tabla", "ref_columnas", "estado",
                        "violaciones", "ejemplos", "definicion"]


def resumen_por_tipo(resultado):
    tipos = {}
    for r in resultado:
        d = tipos.setdefault(r["tipo"], {"restricciones": 0, "violadas": 0, "filas": 0, "sin_comprobar": 0})
        d["restricciones"] += 1
        if r["estado"] == "violada":
            d["violadas"] += 1
            d["filas"] += r["violaciones"]
        elif r["estado"] != "ok":
            d["sin_comprobar"] += 1
    return tipos


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", required=True, help="base a auditar (cargada sin restricciones)")
    ap.add_argument("--referencia", default="pagila", help="base de la que se toman las restricciones")
    ap.add_argument("--salida", required=True, help="carpeta donde escribir integridad.csv")
    a = ap.parse_args()
    with conexion(a.referencia) as ref:
        restr = restricciones(ref)
    with conexion(a.base) as c:
        res = contar_violaciones(c, restr)
    guardar_csv(Path(a.salida) / "integridad.csv", res, CAMPOS_RESTRICCIONES)
    for tipo, d in resumen_por_tipo(res).items():
        print(f"{tipo:16} {d['restricciones']:3} restricciones, {d['violadas']:3} violadas, "
              f"{d['filas']:6} filas, {d['sin_comprobar']} sin comprobar")


if __name__ == "__main__":
    main()
