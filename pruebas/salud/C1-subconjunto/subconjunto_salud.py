#!/usr/bin/env python3
"""C1m / C1s: subconjunto coherente de MIMIC-IV demo y Synthea con el script propio, adaptado a tablas sin PK.

Parte de pruebas/C1-script-propio/subconjunto.py (que no se toca) y le agrega:
  - Tablas sin clave primaria (7 en MIMIC, entre ellas chartevents; 10 en Synthea): sus filas se identifican por
    `ctid`, que es estable dentro de la única instantánea REPEATABLE READ en la que se hace todo (el origen no se
    modifica). El prototipo de Pagila se cortaba con esas tablas.
  - Relaciones extra desde un CSV (la salida de pruebas/_bases/relaciones_mimic.py: las no declaradas).
  - Pacientes de control: un filtro que separa pacientes para E3 antes de extraer; el manifiesto cuenta cuántos hay y
    verifica que ninguno entró al subconjunto.
  - Mediciones de escala: tiempo por fase, memoria del proceso, tamaño de las tablas de trabajo, bytes temporales
    que escribió PostgreSQL y tamaño de la base destino.
  - Integridad: las FK del catálogo se vuelven a crear en el destino (si alguna se viola, la carga falla); las
    relaciones no declaradas se cuentan en el destino y se comparan con el origen.

Uso:  .venv/bin/python pruebas/salud/C1-subconjunto/subconjunto_salud.py pruebas/salud/C1-subconjunto/<config>.json
"""
import csv
import datetime
import hashlib
import io
import json
import os
import platform
import re
import resource
import shlex
import subprocess
import sys
import time
from importlib.metadata import version
from pathlib import Path

from psycopg2 import sql

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))
import integridad as ig  # noqa: E402

PG_DUMP = os.environ.get("PG_DUMP_CMD", "docker exec -i pagila-db pg_dump -U postgres")
PSQL = os.environ.get("PSQL_CMD", "docker exec -i pagila-db psql -U postgres")
CTID = "_ctid"   # nombre de la columna de trabajo para tablas sin PK («ctid» está reservado)


# ----------------------------------------------------------------------------- catálogo

def tablas_logicas(cur):
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
    cur.execute("""select attname from pg_attribute
                   where attrelid = %s and attnum > 0 and not attisdropped and attgenerated = ''
                   order by attnum""", (oid,))
    return [r[0] for r in cur.fetchall()]


def relaciones_declaradas(cur):
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


def relaciones_csv(ruta):
    """CSV de relaciones_mimic.py: tabla, columna, apunta_a (esquema.tabla.columna), declarada, huerfanas…"""
    out = []
    for r in csv.DictReader(open(RAIZ / ruta, encoding="utf-8")):
        if r["declarada"] == "sí":
            continue
        esq, tab, col = r["apunta_a"].split(".")
        out.append({"hijo": r["tabla"], "columnas": [r["columna"]], "padre": f"{esq}.{tab}", "referencia": [col],
                    "origen": f"relaciones no declaradas ({ruta})", "huerfanas_origen": int(r["huerfanas"])})
    return out


# ----------------------------------------------------------------------------- selección

class Seleccion:
    """Claves elegidas por tabla (PK o ctid), en tablas temporales de la sesión sobre el origen."""

    def __init__(self, cur, tablas):
        self.cur, self.tablas = cur, tablas
        for t in tablas.values():
            for tipo in ("sel", "nuc"):
                t[tipo] = sql.Identifier(f"_{tipo}_{t['oid']}")
                if t["pk"]:
                    cols = sql.SQL(", ").join(sql.Identifier(c) for c in t["pk"])
                    self.cur.execute(sql.SQL("create temp table {} as select {} from {} limit 0").format(
                        t[tipo], cols, self.ident(t)))
                else:
                    self.cur.execute(sql.SQL("create temp table {} ({} tid)").format(t[tipo], sql.Identifier(CTID)))
                self.cur.execute(sql.SQL("alter table {} add primary key ({})").format(
                    t[tipo], sql.SQL(", ").join(sql.Identifier(c) for c in self.claves_tmp(t))))

    @staticmethod
    def ident(t):
        return sql.Identifier(t["esquema"], t["nombre"])

    @staticmethod
    def claves_origen(t):
        return t["pk"] or ["ctid"]

    @staticmethod
    def claves_tmp(t):
        return t["pk"] or [CTID]

    def igual_claves(self, alias_origen, t, alias_tmp):
        """x.pk = s.pk (o x.ctid = s._ctid)."""
        return sql.SQL(" and ").join(
            sql.SQL("{}.{} = {}.{}").format(sql.Identifier(alias_origen), sql.Identifier(a),
                                            sql.Identifier(alias_tmp), sql.Identifier(b))
            for a, b in zip(self.claves_origen(t), self.claves_tmp(t)))

    def agregar(self, t, destino, consulta, desde_tmp=False):
        """Inserta las claves que devuelve `consulta` (alias «x»: tabla de origen, o temporal si desde_tmp)."""
        nombres = self.claves_tmp(t) if desde_tmp else self.claves_origen(t)
        cols = sql.SQL(", ").join(sql.SQL("x.") + sql.Identifier(c) for c in nombres)
        self.cur.execute(sql.SQL("insert into {} select distinct {} {} on conflict do nothing").format(
            t[destino], cols, consulta))
        return self.cur.rowcount

    def sembrar(self, t, filtro):
        n = self.agregar(t, "nuc", sql.SQL("from {} x where {}").format(self.ident(t), sql.SQL(filtro)))
        self.agregar(t, "sel", sql.SQL("from {} x").format(t["nuc"]), desde_tmp=True)
        return n

    def todo(self, t):
        return self.agregar(t, "sel", sql.SQL("from {} x").format(self.ident(t)))

    @staticmethod
    def _union(ref_x, ref_y, cols_x, cols_y):
        return sql.SQL(" and ").join(
            sql.SQL("{}.{} = {}.{}").format(sql.Identifier(ref_x), sql.Identifier(a), sql.Identifier(ref_y),
                                            sql.Identifier(b)) for a, b in zip(cols_x, cols_y))

    def hacia_arriba(self, r):
        """Hijas de filas del núcleo del padre: entran al núcleo (y a sel)."""
        h, p = self.tablas[r["hijo"]], self.tablas[r["padre"]]
        q = sql.SQL("from {h} x join {p} y on {on} join {nuc} s on {pk}").format(
            h=self.ident(h), p=self.ident(p), nuc=p["nuc"],
            on=self._union("x", "y", r["columnas"], r["referencia"]), pk=self.igual_claves("y", p, "s"))
        n = self.agregar(h, "nuc", q)
        if n:
            self.agregar(h, "sel", sql.SQL("from {} x").format(h["nuc"]), desde_tmp=True)
        return n

    def hacia_abajo(self, r):
        """Padres de cualquier fila elegida del hijo: entran a sel (no al núcleo)."""
        h, p = self.tablas[r["hijo"]], self.tablas[r["padre"]]
        q = sql.SQL("from {p} x join {h} y on {on} join {sel} s on {pk}").format(
            p=self.ident(p), h=self.ident(h), sel=h["sel"],
            on=self._union("x", "y", r["referencia"], r["columnas"]), pk=self.igual_claves("y", h, "s"))
        return self.agregar(p, "sel", q)

    def contar(self, t, tipo):
        self.cur.execute(sql.SQL("select count(*) from {}").format(t[tipo]))
        return self.cur.fetchone()[0]

    def bytes_trabajo(self):
        self.cur.execute("select coalesce(sum(pg_total_relation_size(c.oid)), 0) from pg_class c "
                         "where c.relpersistence = 't' and c.relkind = 'r' and c.relname like '\\_%'")
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
    """Copia tabla por tabla en memoria (BytesIO). Devuelve el mayor volumen copiado de una tabla, en bytes."""
    mayor = 0
    with conn_destino.cursor() as cd:
        for t in sel.tablas.values():
            cols = sql.SQL(", ").join(sql.Identifier(c) for c in t["copiar"])
            cols_x = sql.SQL(", ").join(sql.SQL("x.") + sql.Identifier(c) for c in t["copiar"])
            buf = io.BytesIO()
            cur_origen.copy_expert(sql.SQL("copy (select {} from {} x join {} s on {}) to stdout").format(
                cols_x, sel.ident(t), t["sel"], sel.igual_claves("x", t, "s")).as_string(cur_origen), buf)
            mayor = max(mayor, buf.tell())
            buf.seek(0)
            cd.copy_expert(sql.SQL("copy {} ({}) from stdin").format(sel.ident(t), cols).as_string(cd), buf)
    return mayor


def ajustar_secuencias(conn):
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


def huerfanas(conn, r):
    """Filas del hijo con valor no nulo que no encuentran al padre."""
    h_esq, h_tab = r["hijo"].split(".")
    p_esq, p_tab = r["padre"].split(".")
    no_nulo = sql.SQL(" and ").join(sql.SQL("x.{} is not null").format(sql.Identifier(c)) for c in r["columnas"])
    on = Seleccion._union("y", "x", r["referencia"], r["columnas"])
    with conn.cursor() as cur:
        cur.execute(sql.SQL("select count(*) from {} x where {} and not exists (select 1 from {} y where {})").format(
            sql.Identifier(h_esq, h_tab), no_nulo, sql.Identifier(p_esq, p_tab), on))
        return cur.fetchone()[0]


def temp_bytes(cur, base):
    cur.execute("select temp_bytes from pg_stat_database where datname = %s", (base,))
    return cur.fetchone()[0]


# ----------------------------------------------------------------------------- principal

def sha256(b):
    return hashlib.sha256(b).hexdigest()


def main():
    ruta_cfg = Path(sys.argv[1])
    cfg_bytes = ruta_cfg.read_bytes()
    cfg = json.loads(cfg_bytes)
    salida = ruta_cfg.parent / cfg["salida"]
    salida.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    conn = ig.conectar(cfg["origen"])
    with conn.cursor() as c:
        tb0 = temp_bytes(c, cfg["origen"])
    conn.autocommit = False
    conn.set_session(isolation_level="REPEATABLE READ")
    cur = conn.cursor()

    tablas = tablas_logicas(cur)
    for t in tablas.values():
        t["pk"] = clave_primaria(cur, t["oid"])
        t["copiar"] = columnas_copiables(cur, t["oid"])
    sin_pk = sorted(n for n, t in tablas.items() if not t["pk"])

    relaciones = relaciones_declaradas(cur)
    if cfg.get("relaciones_csv"):
        relaciones += relaciones_csv(cfg["relaciones_csv"])

    sel = Seleccion(cur, tablas)
    ancla = tablas[cfg["ancla"]["tabla"]]
    cur.execute(sql.SQL("select count(*), count(*) filter (where {c}), count(*) filter (where ({f})) "
                        "from {t}").format(c=sql.SQL(cfg["control"]), f=sql.SQL(cfg["ancla"]["filtro"]),
                                           t=sel.ident(ancla)))
    n_ancla, n_control, n_filtro = cur.fetchone()
    t_sel = time.time()
    semilla = sel.sembrar(ancla, cfg["ancla"]["filtro"])
    for nombre in cfg.get("copiar_enteras", []):
        sel.todo(tablas[nombre])

    rondas = []
    while True:
        tr = time.time()
        arriba = sum(sel.hacia_arriba(r) for r in relaciones)
        abajo = sum(sel.hacia_abajo(r) for r in relaciones)
        rondas.append({"ronda": len(rondas) + 1, "filas_nucleo_nuevas": arriba, "filas_referenciadas_nuevas": abajo,
                       "segundos": round(time.time() - tr, 2)})
        if arriba == 0 and abajo == 0:
            break
    t_sel = time.time() - t_sel
    bytes_trabajo = sel.bytes_trabajo()

    pk_a = sql.SQL(", ").join(sql.Identifier(c) for c in ancla["pk"])
    cur.execute(sql.SQL("select count(*) from (select {pk} from {sel} except select {pk} from {nuc}) d").format(
        pk=pk_a, sel=ancla["sel"], nuc=ancla["nuc"]))
    ancla_fuera_filtro = cur.fetchone()[0]
    cur.execute(sql.SQL("select count(*) from {t} x join {sel} s using ({pk}) where {c}").format(
        t=sel.ident(ancla), sel=ancla["sel"], pk=pk_a, c=sql.SQL(cfg["control"])))
    control_en_subconjunto = cur.fetchone()[0]

    conteos = []
    for nombre, t in tablas.items():
        cur.execute(sql.SQL("select count(*) from {}").format(sel.ident(t)))
        conteos.append({"tabla": nombre, "origen": cur.fetchone()[0], "subconjunto": sel.contar(t, "sel"),
                        "nucleo": sel.contar(t, "nuc"), "clave": "pk" if t["pk"] else "ctid"})

    destino = cfg["destino"]
    ig.crear_base(destino)
    t_esq = time.time()
    pre, post = pg_dump_seccion(cfg["origen"], "pre-data"), pg_dump_seccion(cfg["origen"], "post-data")
    psql_estricto(destino, pre)
    t_esq = time.time() - t_esq
    dst = ig.conectar(destino)
    t_copia = time.time()
    mayor_tabla = copiar_datos(cur, dst, sel)
    t_copia = time.time() - t_copia
    t_post = time.time()
    psql_estricto(destino, post)   # índices y FK del catálogo: si una FK se viola, falla acá
    t_post = time.time() - t_post
    secuencias = ajustar_secuencias(dst)
    conn.rollback()
    conn.autocommit = True
    with conn.cursor() as c:
        tb1 = temp_bytes(c, cfg["origen"])

    integridad_extra = []
    for r in relaciones:
        if r["origen"] == "catálogo":
            continue
        integridad_extra.append({"relacion": f"{r['hijo']}.{r['columnas'][0]} -> {r['padre']}.{r['referencia'][0]}",
                                 "huerfanas_origen": r["huerfanas_origen"], "huerfanas_destino": huerfanas(dst, r)})
    with dst.cursor() as c:
        c.execute("select pg_database_size(current_database())")
        bytes_destino = c.fetchone()[0]
        c.execute("select count(*) from pg_constraint where contype = 'f'")
        fk_destino = c.fetchone()[0]
    dst.close()
    conn.close()

    with ig.conexion("postgres") as c, c.cursor() as cc:
        cc.execute("show server_version")
        version_pg = cc.fetchone()[0]
    commit = subprocess.run(["git", "-C", str(RAIZ), "rev-parse", "--short", "HEAD"],
                            capture_output=True, text=True).stdout.strip()
    tot_o = sum(c["origen"] for c in conteos)
    tot_s = sum(c["subconjunto"] for c in conteos)
    manifiesto = {
        "prueba": cfg["prueba"],
        "fecha": datetime.datetime.now().isoformat(timespec="seconds"),
        "configuracion": cfg, "configuracion_sha256": sha256(cfg_bytes),
        "esquema_origen_sha256": sha256(pre + post),
        "entorno": {"postgresql": version_pg, "python": platform.python_version(),
                    "psycopg2": version("psycopg2-binary"), "equipo": platform.machine(), "commit_repo": commit},
        "tablas_sin_pk": sin_pk,
        "relaciones": {"catalogo": sum(r["origen"] == "catálogo" for r in relaciones),
                       "extra": sum(r["origen"] != "catálogo" for r in relaciones)},
        "ancla": {"filas": n_ancla, "control": n_control, "cumplen_filtro": n_filtro, "semilla": semilla,
                  "fuera_del_filtro": ancla_fuera_filtro, "control_en_subconjunto": control_en_subconjunto},
        "rondas_cierre": rondas,
        "conteos": conteos,
        "filas": {"origen": tot_o, "subconjunto": tot_s, "porcentaje": round(100 * tot_s / tot_o, 2)},
        "integridad": {"fk_catalogo_recreadas_en_destino": fk_destino,
                       "relaciones_no_declaradas": integridad_extra},
        "secuencias_ajustadas": secuencias,
        "escala": {"memoria_max_proceso_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2**20, 1),
                   "tablas_trabajo_mb": round(bytes_trabajo / 2**20, 1),
                   "temp_bytes_postgres_mb": round((tb1 - tb0) / 2**20, 1),
                   "mayor_tabla_copiada_mb": round(mayor_tabla / 2**20, 1),
                   "base_destino_mb": round(bytes_destino / 2**20, 1)},
        "segundos": {"seleccion": round(t_sel, 2), "esquema_pre": round(t_esq, 2), "copia_datos": round(t_copia, 2),
                     "esquema_post": round(t_post, 2), "total": round(time.time() - t0, 2)},
    }
    (salida / "manifiesto.json").write_text(json.dumps(manifiesto, indent=2, ensure_ascii=False, default=str),
                                            encoding="utf-8")
    with open(salida / "conteos.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["tabla", "origen", "subconjunto", "nucleo", "clave"])
        w.writeheader()
        w.writerows(conteos)
    print(f"{destino}: {tot_s} de {tot_o} filas ({manifiesto['filas']['porcentaje']} %), {len(rondas)} rondas, "
          f"semilla {semilla} de {n_ancla} (control {n_control}, en subconjunto {control_en_subconjunto}), "
          f"fuera del filtro {ancla_fuera_filtro}, {manifiesto['segundos']['total']} s, "
          f"escala {manifiesto['escala']}")


if __name__ == "__main__":
    main()
