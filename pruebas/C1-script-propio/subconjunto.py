#!/usr/bin/env python3
"""Prueba C1 (parte 2): extracción de un subconjunto coherente con un script propio.

Responde a lo que Condenser no resolvió (ver ../C1-condenser/ficha.md):

  - Grafo de relaciones = FK del catálogo, con las de las particiones llevadas a su tabla raíz
    (pg_partition_root, que da NULL si la tabla no está particionada), MÁS las relaciones no
    declaradas que se le pasen en la configuración (las que propone E3 / la capa 0 y confirma una persona).
  - Cierre por punto fijo: se repite hasta que ninguna relación agrega filas, así los ciclos
    (store <-> staff) se cierran solos, sin cortar nada.
  - Dos tipos de filas: el «núcleo» (las del ancla y sus hijas, hacia arriba) y las que entran
    solo porque alguien las referencia (hacia abajo). Solo el núcleo arrastra hijas: si no, un
    cliente traído por referencia arrastraría todos sus alquileres y el subconjunto crece sin control.
  - Las filas que el cierre agrega fuera del filtro en la tabla ancla se registran en el manifiesto
    (Condenser las descartaba en silencio).
  - Lectura del origen en una sola instantánea (REPEATABLE READ): el origen no se modifica; las
    tablas de trabajo son temporales de la sesión.
  - Esquema en dos fases (pg_dump pre-data, datos, post-data) y secuencias ajustadas al máximo.

Uso (desde la raíz del repo, con la base levantada):
    .venv/bin/python pruebas/C1-script-propio/subconjunto.py pruebas/C1-script-propio/config.json

pg_dump y psql se corren dentro del contenedor, con la misma versión que el servidor. Se pueden
cambiar con PG_DUMP_CMD y PSQL_CMD (como en scripts/integridad.py).
"""
import datetime
import hashlib
import io
import json
import os
import platform
import re
import shlex
import subprocess
import sys
import time
from importlib.metadata import version
from pathlib import Path

from psycopg2 import sql

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import integridad as ig  # noqa: E402

PG_DUMP = os.environ.get("PG_DUMP_CMD", "docker exec -i pagila-db pg_dump -U postgres")
PSQL = os.environ.get("PSQL_CMD", "docker exec -i pagila-db psql -U postgres")


# ----------------------------------------------------------------------------- catálogo

def tablas_logicas(cur):
    """Tablas comunes y raíces de particiones (las particiones se tratan a través de su raíz)."""
    cur.execute("""
        select c.oid, n.nspname, c.relname
        from pg_class c join pg_namespace n on n.oid = c.relnamespace
        where c.relkind in ('r', 'p') and not c.relispartition
          and n.nspname not in ('pg_catalog', 'information_schema') and n.nspname not like 'pg\\_%'
        order by 2, 3""")
    return {f"{s}.{t}": {"oid": o, "esquema": s, "nombre": t} for o, s, t in cur.fetchall()}


def clave_primaria(cur, oid):
    cur.execute("""
        select a.attname from pg_index i
        join lateral unnest(i.indkey) with ordinality k(attnum, ord) on true
        join pg_attribute a on a.attrelid = i.indrelid and a.attnum = k.attnum
        where i.indrelid = %s and i.indisprimary order by k.ord""", (oid,))
    return [r[0] for r in cur.fetchall()]


def columnas_copiables(cur, oid):
    """Columnas sin las generadas (no se pueden escribir con COPY)."""
    cur.execute("""select attname from pg_attribute
                   where attrelid = %s and attnum > 0 and not attisdropped and attgenerated = ''
                   order by attnum""", (oid,))
    return [r[0] for r in cur.fetchall()]


def relaciones_declaradas(cur):
    """FK del catálogo, con hijo y padre llevados a su tabla raíz y sin repetir."""
    cur.execute("""
        select distinct
          rn.nspname || '.' || rc.relname, array(select attname from unnest(k.conkey) with ordinality u(n, o)
                 join pg_attribute a on a.attrelid = k.conrelid and a.attnum = u.n order by u.o),
          pn.nspname || '.' || pc.relname, array(select attname from unnest(k.confkey) with ordinality u(n, o)
                 join pg_attribute a on a.attrelid = k.confrelid and a.attnum = u.n order by u.o)
        from pg_constraint k
        join pg_class rc on rc.oid = coalesce(pg_partition_root(k.conrelid), k.conrelid) join pg_namespace rn on rn.oid = rc.relnamespace
        join pg_class pc on pc.oid = coalesce(pg_partition_root(k.confrelid), k.confrelid) join pg_namespace pn on pn.oid = pc.relnamespace
        where k.contype = 'f'""")
    return [{"hijo": h, "columnas": list(hc), "padre": p, "referencia": list(pr), "origen": "catálogo"}
            for h, hc, p, pr in cur.fetchall()]


def calificar(nombre):
    return nombre if "." in nombre else f"public.{nombre}"


# ----------------------------------------------------------------------------- selección

class Seleccion:
    """Claves elegidas por tabla, en tablas temporales de la sesión sobre el origen."""

    def __init__(self, cur, tablas):
        self.cur, self.tablas = cur, tablas
        for t in tablas.values():
            for tipo in ("sel", "nuc"):   # sel = todo lo que se copia; nuc = núcleo (arrastra hijas)
                tmp = f"_{tipo}_{t['oid']}"
                t[tipo] = sql.Identifier(tmp)
                cols = sql.SQL(", ").join(sql.Identifier(c) for c in t["pk"])
                cur.execute(sql.SQL("create temp table {} as select {} from {} limit 0").format(
                    t[tipo], cols, self.ident(t)))
                cur.execute(sql.SQL("alter table {} add primary key ({})").format(t[tipo], cols))

    @staticmethod
    def ident(t):
        return sql.Identifier(t["esquema"], t["nombre"])

    def agregar(self, t, destino, consulta):
        """Inserta las claves que devuelve `consulta` (alias de la tabla: «x») en sel o nuc."""
        cols = sql.SQL(", ").join(sql.SQL("x.") + sql.Identifier(c) for c in t["pk"])
        self.cur.execute(sql.SQL("insert into {} select distinct {} {} on conflict do nothing").format(
            t[destino], cols, consulta))
        return self.cur.rowcount

    def sembrar(self, t, filtro):
        q = sql.SQL("from {} x where {}").format(self.ident(t), sql.SQL(filtro))
        n = self.agregar(t, "nuc", q)
        self.agregar(t, "sel", sql.SQL("from {} x").format(t["nuc"]))
        return n

    def todo(self, t):
        return self.agregar(t, "sel", sql.SQL("from {} x").format(self.ident(t)))

    def _union(self, ref_x, ref_y, cols_x, cols_y):
        return sql.SQL(" and ").join(
            sql.SQL("{}.{} = {}.{}").format(sql.Identifier(ref_x), sql.Identifier(a), sql.Identifier(ref_y), sql.Identifier(b))
            for a, b in zip(cols_x, cols_y))

    def hacia_arriba(self, r):
        """Hijas de filas del núcleo del padre: entran al núcleo (y a sel)."""
        h, p = self.tablas[r["hijo"]], self.tablas[r["padre"]]
        q = sql.SQL("from {h} x join {p} y on {on} join {nuc} s on {pk}").format(
            h=self.ident(h), p=self.ident(p), nuc=p["nuc"],
            on=self._union("x", "y", r["columnas"], r["referencia"]),
            pk=self._union("y", "s", p["pk"], p["pk"]))
        n = self.agregar(h, "nuc", q)
        self.agregar(h, "sel", sql.SQL("from {} x").format(h["nuc"]))
        return n

    def hacia_abajo(self, r):
        """Padres de cualquier fila elegida del hijo: entran a sel (no al núcleo)."""
        h, p = self.tablas[r["hijo"]], self.tablas[r["padre"]]
        q = sql.SQL("from {p} x join {h} y on {on} join {sel} s on {pk}").format(
            p=self.ident(p), h=self.ident(h), sel=h["sel"],
            on=self._union("x", "y", r["referencia"], r["columnas"]),
            pk=self._union("y", "s", h["pk"], h["pk"]))
        return self.agregar(p, "sel", q)

    def contar(self, t, tipo):
        self.cur.execute(sql.SQL("select count(*) from {}").format(t[tipo]))
        return self.cur.fetchone()[0]


# ----------------------------------------------------------------------------- copia

def pg_dump_seccion(base, seccion):
    r = subprocess.run(shlex.split(PG_DUMP) + ["-d", base, "--schema-only", "--no-owner", "--no-privileges",
                                                f"--section={seccion}"], capture_output=True, check=True)
    return r.stdout


def psql_estricto(base, script):
    r = subprocess.run(shlex.split(PSQL) + ["-X", "-q", "-v", "ON_ERROR_STOP=1", "-d", base, "-f", "-"],
                       input=script, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode("utf-8", errors="replace"))


def copiar_datos(cur_origen, conn_destino, sel):
    with conn_destino.cursor() as cd:
        for t in sel.tablas.values():
            cols = sql.SQL(", ").join(sql.Identifier(c) for c in t["copiar"])
            cols_x = sql.SQL(", ").join(sql.SQL("x.") + sql.Identifier(c) for c in t["copiar"])
            buf = io.BytesIO()
            cur_origen.copy_expert(sql.SQL("copy (select {} from {} x join {} s using ({})) to stdout").format(
                cols_x, sel.ident(t), t["sel"], sql.SQL(", ").join(sql.Identifier(c) for c in t["pk"])
            ).as_string(cur_origen), buf)
            buf.seek(0)
            cd.copy_expert(sql.SQL("copy {} ({}) from stdin").format(sel.ident(t), cols).as_string(cd), buf)


def ajustar_secuencias(conn):
    """Lleva cada secuencia usada como default al máximo de su columna (si no, el próximo INSERT choca)."""
    ajustadas = []
    with conn.cursor() as cur:
        cur.execute("""
            select n.nspname, c.relname, a.attname, pg_get_expr(d.adbin, d.adrelid)
            from pg_attrdef d join pg_class c on c.oid = d.adrelid join pg_namespace n on n.oid = c.relnamespace
            join pg_attribute a on a.attrelid = d.adrelid and a.attnum = d.adnum
            where pg_get_expr(d.adbin, d.adrelid) like 'nextval(%' and not c.relispartition""")
        for esquema, tabla, col, expr in cur.fetchall():
            seq = re.search(r"nextval\('([^']+)'", expr).group(1)
            cur.execute(sql.SQL("select max({}) from {}").format(sql.Identifier(col), sql.Identifier(esquema, tabla)))
            m = cur.fetchone()[0]
            cur.execute("select setval(%s::regclass, %s, %s)", (seq, m or 1, m is not None))
            ajustadas.append({"secuencia": seq, "tabla": f"{esquema}.{tabla}", "columna": col, "valor": m})
    return ajustadas


# ----------------------------------------------------------------------------- principal

def sha256(b):
    return hashlib.sha256(b).hexdigest()


def main():
    ruta_cfg = Path(sys.argv[1])
    cfg_bytes = ruta_cfg.read_bytes()
    cfg = json.loads(cfg_bytes)
    salida = ruta_cfg.parent / cfg.get("salida", "resultados")
    salida.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    conn = ig.conectar(cfg["origen"])
    conn.autocommit = False
    conn.set_session(isolation_level="REPEATABLE READ")   # una sola instantánea del origen
    cur = conn.cursor()

    tablas = tablas_logicas(cur)
    for nombre, t in tablas.items():
        t["pk"] = clave_primaria(cur, t["oid"])
        t["copiar"] = columnas_copiables(cur, t["oid"])
        if not t["pk"]:
            sys.exit(f"{nombre} no tiene clave primaria: este prototipo no la soporta.")

    relaciones = relaciones_declaradas(cur)
    for r in cfg.get("relaciones_extra", []):
        relaciones.append({"hijo": calificar(r["hijo"]), "columnas": r["columnas"], "padre": calificar(r["padre"]),
                           "referencia": r["referencia"], "origen": "configuración"})

    sel = Seleccion(cur, tablas)
    ancla = tablas[calificar(cfg["ancla"]["tabla"])]
    semilla = sel.sembrar(ancla, cfg["ancla"]["filtro"])
    for nombre in cfg.get("copiar_enteras", []):
        sel.todo(tablas[calificar(nombre)])

    # Cierre por punto fijo.
    t_cierre = time.time()
    rondas = []
    while True:
        arriba = sum(sel.hacia_arriba(r) for r in relaciones)
        abajo = sum(sel.hacia_abajo(r) for r in relaciones)
        rondas.append({"ronda": len(rondas) + 1, "filas_nucleo_nuevas": arriba, "filas_referenciadas_nuevas": abajo})
        if arriba == 0 and abajo == 0:
            break
    t_cierre = time.time() - t_cierre

    # Filas de la tabla ancla que entraron sin cumplir el filtro (solo por referencia).
    pk_a = sql.SQL(", ").join(sql.Identifier(c) for c in ancla["pk"])
    cur.execute(sql.SQL("select {pk} from {sel} except select {pk} from {nuc} order by 1").format(
        pk=pk_a, sel=ancla["sel"], nuc=ancla["nuc"]))
    ancla_fuera_filtro = [list(r) for r in cur.fetchall()]

    conteos = []
    for nombre, t in tablas.items():
        cur.execute(sql.SQL("select count(*) from {}").format(sel.ident(t)))
        conteos.append({"tabla": nombre, "origen": cur.fetchone()[0], "subconjunto": sel.contar(t, "sel"),
                        "nucleo": sel.contar(t, "nuc")})

    # Base destino: esquema en dos fases, con los datos en el medio.
    destino = cfg["destino"]
    ig.crear_base(destino)
    pre, post = pg_dump_seccion(cfg["origen"], "pre-data"), pg_dump_seccion(cfg["origen"], "post-data")
    psql_estricto(destino, pre)
    dst = ig.conectar(destino)
    t_copia = time.time()
    copiar_datos(cur, dst, sel)
    t_copia = time.time() - t_copia
    psql_estricto(destino, post)
    secuencias = ajustar_secuencias(dst)
    dst.close()
    conn.rollback()   # descarta las tablas temporales; el origen no se tocó
    conn.close()

    with ig.conexion("postgres") as c, c.cursor() as cc:
        cc.execute("show server_version")
        version_pg = cc.fetchone()[0]
    try:
        commit = subprocess.run(["git", "-C", str(RAIZ), "rev-parse", "--short", "HEAD"],
                                capture_output=True, text=True).stdout.strip()
    except OSError:
        commit = ""

    manifiesto = {
        "prueba": "C1 script propio",
        "fecha": datetime.datetime.now().isoformat(timespec="seconds"),
        "configuracion": cfg, "configuracion_sha256": sha256(cfg_bytes),
        "esquema_origen_sha256": sha256(pre + post),
        "entorno": {"postgresql": version_pg, "python": platform.python_version(),
                    "psycopg2": version("psycopg2-binary"), "equipo": platform.machine(),
                    "commit_repo": commit},
        "relaciones": relaciones,
        "semilla_filas_ancla": semilla,
        "rondas_cierre": rondas,
        "ancla_fuera_del_filtro": {"cantidad": len(ancla_fuera_filtro), "claves": ancla_fuera_filtro,
                                   "motivo": "referenciadas por filas del subconjunto; se agregan para no dejar huérfanas"},
        "conteos": conteos,
        "secuencias_ajustadas": secuencias,
        "segundos": {"cierre": round(t_cierre, 2), "copia_datos": round(t_copia, 2), "total": round(time.time() - t0, 2)},
    }
    (salida / "manifiesto.json").write_text(json.dumps(manifiesto, indent=2, ensure_ascii=False, default=str),
                                            encoding="utf-8")
    tot_o = sum(c["origen"] for c in conteos)
    tot_s = sum(c["subconjunto"] for c in conteos)
    print(f"{destino}: {tot_s} de {tot_o} filas ({100 * tot_s / tot_o:.1f} %), {len(rondas)} rondas, "
          f"{len(ancla_fuera_filtro)} filas del ancla fuera del filtro, {manifiesto['segundos']['total']} s")


if __name__ == "__main__":
    main()
