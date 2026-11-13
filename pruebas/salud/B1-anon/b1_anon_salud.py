#!/usr/bin/env python3
"""B1m / B1s: enmascaramiento estático con PostgreSQL Anonymizer sobre los subconjuntos de MIMIC y Synthea (C1).

Variantes:
  mimic nativas       solo funciones de la extensión: ids con anon.pseudo_shift, ids de texto con anon.hash, fechas
                      con anon.dnoise (ruido por fila), edad con anon.noise. Lo que haría alguien siguiendo la
                      documentación.
  mimic consistentes  funciones propias (masc.sql): ids con hash y sal conservando el formato, ids compuestos
                      (poe_id, emar_id) que llevan el subject_id adentro, fechas desplazadas por paciente, edad por
                      década.
  synthea consistentes  ídem para Synthea, más identificadores directos: nombres con anon.pseudo_*, SSN, licencia y
                      pasaporte con el mismo formato, dirección falsa, geografía generalizada (HIPAA), ingresos con
                      ruido.

Las reglas salen de la lista de referencia congelada (categoría de cada columna) + la tabla de funciones de cada
variante (REGLAS). Todo corre en el contenedor `salud-anon` (PostgreSQL Anonymizer 3.3.2), sobre una copia del
subconjunto: el subconjunto original en pagila-db no se toca. No se guardan filas: solo conteos y métricas.

Uso:  .venv/bin/python pruebas/salud/B1-anon/b1_anon_salud.py --base mimic --variante nativas
Salida: resultados/<base>_<variante>.json y .md
"""
import argparse
import csv
import datetime
import hashlib
import json
import re
import subprocess
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[2]
SAL = "sal-secreta-b1-2026-11-09"   # en un sistema real, fuera del repo; acá se publica para poder medir la reversión
BASES = {"mimic": dict(origen="mimic_c1_50", ref="columnas_sensibles_mimic.csv", clave="subject_id"),
         "synthea": dict(origen="synthea_c1_10", ref="columnas_sensibles_synthea.csv", clave=None)}
CLAVE_SYNTHEA = {"patients": "id", "claims": "patientid", "claims_transactions": "patientid"}  # resto: «patient»


def regla(base, variante, tabla, col, cat, tipo):
    """Función de enmascaramiento para una columna (texto de la etiqueta) o None si queda igual."""
    es_fecha = tipo.startswith("timestamp") or tipo == "date"
    if base == "mimic":
        if variante == "nativas":
            if col in ("subject_id", "hadm_id", "stay_id", "caregiver_id"):
                return f"anon.pseudo_shift({col})"
            if col.endswith("provider_id"):
                return f"anon.hash({col})"
            if cat == "cuasi_hipaa" and es_fecha:
                return f"anon.dnoise({col}, ''180 days''::interval)"
            if col == "anchor_age":
                return f"anon.noise({col}, 0.2)"
            return None
        if col in ("subject_id", "hadm_id", "stay_id", "caregiver_id"):
            return f"masc.id_hash({col})"
        if col.endswith("provider_id"):
            return f"masc.texto_hash({col})"
        if col in ("poe_id", "emar_id", "discontinue_of_poe_id", "discontinued_by_poe_id"):
            return f"masc.id_compuesto({col})"
        if cat == "cuasi_hipaa" and es_fecha:
            return f"masc.desplazar({col}, subject_id)"
        if col == "anchor_age":
            return f"masc.decada({col})"
        return None
    # synthea, consistentes
    clave = "id" if tabla == "patients" else CLAVE_SYNTHEA.get(tabla, "patient")
    if cat in ("ident_opaco", "ident_profesional") and col in (
            "id", "patient", "patientid", "encounter", "appointmentid", "instance_uid", "series_uid", "provider",
            "providerid", "supervisingproviderid"):
        return f"masc.uuid_hash({col})"
    directos = {("patients", "first"): "anon.pseudo_first_name(id)",
                ("patients", "middle"): "anon.pseudo_first_name(id, ''m'')",
                ("patients", "last"): "anon.pseudo_last_name(id)",
                ("patients", "maiden"): "anon.pseudo_last_name(id, ''m'')",
                ("patients", "ssn"): "masc.mismo_formato(ssn, id)",
                ("patients", "drivers"): "masc.mismo_formato(drivers, id)",
                ("patients", "passport"): "masc.mismo_formato(passport, id)",
                ("patients", "address"): "anon.fake_address()",
                ("patients", "birthplace"): "anon.pseudo_city(id, ''n'')",
                ("patients", "city"): "anon.pseudo_city(id)",
                ("patients", "county"): None, ("patients", "fips"): None,
                ("patients", "zip"): "masc.zip3(zip)",
                ("patients", "lat"): "masc.redondear(lat, 1)", ("patients", "lon"): "masc.redondear(lon, 1)",
                ("patients", "income"): "anon.noise(income, 0.1)",
                ("patients", "healthcare_expenses"): "anon.noise(healthcare_expenses, 0.1)",
                ("patients", "healthcare_coverage"): "anon.noise(healthcare_coverage, 0.1)",
                ("providers", "name"): "anon.pseudo_last_name(id)",
                ("providers", "address"): "anon.fake_address()",
                ("providers", "city"): "anon.pseudo_city(id)",
                ("providers", "zip"): "masc.zip3(zip)",
                ("providers", "lat"): "masc.redondear(lat, 1)", ("providers", "lon"): "masc.redondear(lon, 1)",
                ("payer_transitions", "memberid"): "masc.mismo_formato(memberid, patient)",
                ("payer_transitions", "owner_name"): "anon.pseudo_last_name(patient)",
                ("devices", "udi"): "masc.mismo_formato(udi, patient)"}
    if (tabla, col) in directos:
        f = directos[(tabla, col)]
        return f if f else "VALUE NULL"
    if cat == "cuasi_hipaa":
        return f"masc.desplazar({col}, {clave})"
    return None


# Reglas de coherencia (consultas que cuentan violaciones; mismas en el origen y en el resultado).
COHERENCIA = {
    "mimic": {
        "alta >= ingreso": "select count(*) from mimiciv_hosp.admissions where dischtime < admittime",
        "muerte dentro de la internación": "select count(*) from mimiciv_hosp.admissions where deathtime is not null "
                                           "and (deathtime < admittime or deathtime > dischtime + interval '1 day')",
        "UCI dentro de la internación": "select count(*) from mimiciv_icu.icustays i join mimiciv_hosp.admissions a "
                                        "using (hadm_id) where i.intime < a.admittime - interval '1 day' "
                                        "or i.outtime > a.dischtime + interval '1 day'",
        "dod = día de la muerte": "select count(*) from mimiciv_hosp.admissions a join mimiciv_hosp.patients p "
                                  "using (subject_id) where a.deathtime is not null and p.dod <> a.deathtime::date",
        "traslado: salida >= entrada": "select count(*) from mimiciv_hosp.transfers where outtime < intime",
        "emergencia: salida >= registro": "select count(*) from mimiciv_hosp.admissions where edouttime < edregtime",
        "chartevents dentro de su estadía UCI": "select count(*) from mimiciv_icu.chartevents c join mimiciv_icu.icustays i "
                                                "using (stay_id) where c.charttime < i.intime - interval '1 day' "
                                                "or c.charttime > i.outtime + interval '1 day'",
        "ingresos del paciente ordenados igual": None,   # se mide con la tabla de verificación
    },
    "synthea": {
        "encuentro: fin >= inicio": "select count(*) from synthea.encounters where stop < start",
        "encuentro después del nacimiento": "select count(*) from synthea.encounters e join synthea.patients p "
                                            "on p.id = e.patient where e.start::date < p.birthdate::date",
        "muerte >= nacimiento": "select count(*) from synthea.patients where deathdate <> '' and deathdate < birthdate",
        "encuentro antes de la muerte": "select count(*) from synthea.encounters e join synthea.patients p "
                                        "on p.id = e.patient where p.deathdate is not null and p.deathdate <> '' "
                                        "and e.start::date > p.deathdate::date + 1",
        "condición: fin >= inicio": "select count(*) from synthea.conditions where stop <> '' and stop < start",
        "medicación: fin >= inicio": "select count(*) from synthea.medications where stop <> '' and stop < start",
    },
}


def psql(cont, db, q, usuario="postgres"):
    r = subprocess.run(["docker", "exec", "-i", cont, "psql", "-U", usuario, "-X", "-q", "-At", "-v",
                        "ON_ERROR_STOP=1", "-d", db, "-f", "-"], input=q.encode(), capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode()[-2000:])
    return r.stdout.decode().strip()


def uno(cont, db, q):
    return psql(cont, db, q).splitlines()[-1]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", choices=BASES, required=True)
    ap.add_argument("--variante", choices=["nativas", "consistentes"], required=True)
    a = ap.parse_args()
    cfg = BASES[a.base]
    db = f"b1{a.base[0]}_{a.variante}"
    salida = AQUI / "resultados"
    salida.mkdir(exist_ok=True)
    res = {"prueba": f"B1{a.base[0]}", "variante": a.variante, "origen": cfg["origen"], "destino": db,
           "fecha": datetime.datetime.now().isoformat(timespec="seconds")}

    # 1. Copia del subconjunto al contenedor de anon.
    t0 = time.time()
    psql("salud-anon", "postgres", f"drop database if exists {db} with (force); create database {db};")
    dump = subprocess.run(["docker", "exec", "pagila-db", "pg_dump", "-U", "postgres", "-Fc", "--no-owner",
                           "--no-privileges", cfg["origen"]], capture_output=True, check=True).stdout
    r = subprocess.run(["docker", "exec", "-i", "salud-anon", "pg_restore", "-U", "postgres", "--no-owner", "-d", db],
                       input=dump, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode()[-2000:])
    res["segundos_copia"] = round(time.time() - t0, 1)
    esquemas = "('mimiciv_hosp','mimiciv_icu')" if a.base == "mimic" else "('synthea')"

    # 2. Preparación: extensión, sal, dueño de las tablas, FK diferibles, funciones propias.
    fks = psql("salud-anon", db, f"""
        select count(*) from pg_constraint k join pg_namespace n on n.oid = k.connamespace
        where k.contype = 'f' and n.nspname in {esquemas};""")
    prep = f"""
        create extension if not exists anon;
        alter database {db} set anon.salt = '{SAL}';
        do $$ declare r record; begin
          for r in select n.nspname, c.relname from pg_class c join pg_namespace n on n.oid = c.relnamespace
                   where c.relkind = 'r' and n.nspname in {esquemas} loop
            execute format('alter table %I.%I owner to enmascarador', r.nspname, r.relname); end loop;
          for r in select n.nspname, c.relname, k.conname from pg_constraint k join pg_class c on c.oid = k.conrelid
                   join pg_namespace n on n.oid = c.relnamespace where k.contype = 'f' and n.nspname in {esquemas} loop
            execute format('alter table %I.%I alter constraint %I deferrable', r.nspname, r.relname, r.conname);
          end loop; end $$;
        select anon.init();   -- datos falsos (nombres, ciudades, direcciones) para fake_* y pseudo_*
        grant usage on schema anon to enmascarador;
        grant select on all tables in schema anon to enmascarador;
        grant usage on schema {esquemas[2:-2].replace("','", ', ')} to enmascarador;
    """
    psql("salud-anon", db, prep)
    psql("salud-anon", db, (AQUI / "masc.sql").read_text())
    if a.variante == "nativas":
        psql("salud-anon", db, f"alter database {db} set anon.shift = 7349211;")
    res["fk_declaradas"] = int(fks)

    # 3. Tablas de verificación (ids y fechas originales), en un esquema sin reglas.
    if a.base == "mimic":
        verif = """create schema verif;
          create table verif.adm as select subject_id, hadm_id, admittime, dischtime from mimiciv_hosp.admissions;
          create table verif.icu as select subject_id, stay_id, intime, outtime from mimiciv_icu.icustays;
          create table verif.pac as select subject_id, dod, anchor_age from mimiciv_hosp.patients;
          create table verif.poe as select subject_id, poe_id from mimiciv_hosp.poe;"""
    else:
        verif = """create schema verif;
          create table verif.pac as select id, birthdate, deathdate, first, last, ssn, drivers, passport, zip
                                    from synthea.patients;
          create table verif.enc as select id, patient, start, stop from synthea.encounters;"""
    psql("salud-anon", db, verif)

    # 4. Coherencia en el origen (antes de enmascarar).
    coh = {k: {"antes": int(uno("salud-anon", db, q))} for k, q in COHERENCIA[a.base].items() if q}

    # 5. Reglas desde la lista de referencia.
    tipos = {}
    for l in psql("salud-anon", db, f"select table_schema, table_name, column_name, data_type "
                                    f"from information_schema.columns where table_schema in {esquemas}").splitlines():
        e, t, c, ty = l.split("|")
        tipos[(e, t, c)] = ty
    etiquetas, reglas = [], []
    for r in csv.DictReader(open(RAIZ / "data" / cfg["ref"], encoding="utf-8")):
        k = (r["esquema"], r["tabla"], r["columna"])
        if k not in tipos:
            continue
        f = regla(a.base, a.variante, r["tabla"], r["columna"], r["categoria"], tipos[k])
        if f:
            cuerpo = f if f.startswith("VALUE") else f"FUNCTION {f}"
            etiquetas.append(f"SECURITY LABEL FOR anon ON COLUMN {k[0]}.{k[1]}.{k[2]} IS 'MASKED WITH {cuerpo}';")
            reglas.append({"columna": f"{k[1]}.{k[2]}", "categoria": r["categoria"], "regla": cuerpo.replace("''", "'")})
    psql("salud-anon", db, "\n".join(etiquetas))
    res["reglas"] = reglas
    res["columnas_enmascaradas"] = len(reglas)

    # 6. Enmascaramiento estático (una transacción; las FK diferidas se validan al final).
    t0 = time.time()
    try:
        psql("salud-anon", db, "set role enmascarador; select anon.anonymize_database();")
        res["enmascarado"] = "ok"
    except RuntimeError as e:
        res["enmascarado"] = "error: " + str(e).strip().splitlines()[0][:300]
    res["segundos_enmascarar"] = round(time.time() - t0, 1)

    # 7. Mediciones.
    if res["enmascarado"] == "ok":
        for k, q in COHERENCIA[a.base].items():
            if q:
                coh[k]["despues"] = int(uno("salud-anon", db, q))
        res["coherencia"] = coh
        res["fk_validas"] = int(uno("salud-anon", db, f"""
            select count(*) from pg_constraint k join pg_namespace n on n.oid = k.connamespace
            where k.contype = 'f' and k.convalidated and n.nspname in {esquemas};"""))
        if a.base == "mimic":
            medir_mimic(db, a.variante, res)
        else:
            medir_synthea(db, res)

    (salida / f"{a.base}_{a.variante}.json").write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "reglas"}, indent=2, ensure_ascii=False))


def mapa_id(variante, expr):
    return f"anon.pseudo_shift({expr})" if variante == "nativas" else f"masc.id_hash({expr})"


def medir_mimic(db, variante, res):
    m = mapa_id(variante, "v.hadm_id")
    # Desplazamiento de fechas por paciente: ¿uno solo para todas sus fechas?
    q = f"""
      with d as (
        select v.subject_id, extract(epoch from a.admittime - v.admittime) s from verif.adm v
          join mimiciv_hosp.admissions a on a.hadm_id = {m}
        union all select v.subject_id, extract(epoch from a.dischtime - v.dischtime) from verif.adm v
          join mimiciv_hosp.admissions a on a.hadm_id = {m}
        union all select v.subject_id, extract(epoch from i.intime - v.intime) from verif.icu v
          join mimiciv_icu.icustays i on i.stay_id = {mapa_id(variante, 'v.stay_id')}
        union all select v.subject_id, extract(epoch from i.outtime - v.outtime) from verif.icu v
          join mimiciv_icu.icustays i on i.stay_id = {mapa_id(variante, 'v.stay_id')})
      select count(*), count(*) filter (where n = 1), round(avg(n), 1) from
        (select subject_id, count(distinct s) n from d group by 1) x;"""
    tot, uno_solo, prom = uno("salud-anon", db, q).split("|")
    res["fechas_por_paciente"] = {"pacientes": int(tot), "con_un_solo_desplazamiento": int(uno_solo),
                                  "desplazamientos_distintos_promedio": float(prom)}
    q = f"""select count(*), count(*) filter (where (a.dischtime - a.admittime) = (v.dischtime - v.admittime))
            from verif.adm v join mimiciv_hosp.admissions a on a.hadm_id = {m};"""
    n, igual = uno("salud-anon", db, q).split("|")
    res["duracion_internacion_igual"] = {"internaciones": int(n), "igual": int(igual)}
    # Fuga por ids compuestos: prefijo de poe_id igual al subject_id original.
    q = """select count(*), count(*) filter (where split_part(p.poe_id, '-', 1) in
             (select subject_id::text from verif.pac)) from mimiciv_hosp.poe p;"""
    n, fuga = uno("salud-anon", db, q).split("|")
    res["fuga_poe_id"] = {"filas": int(n), "prefijo_con_subject_id_original": int(fuga)}
    # Ids originales que siguen en la base.
    res["subject_id_originales_que_quedan"] = int(uno("salud-anon", db,
        "select count(*) from mimiciv_hosp.patients where subject_id in (select subject_id from verif.pac);"))
    res["edad"] = uno("salud-anon", db, """select count(*) filter (where p.anchor_age = v.anchor_age) || ' de ' ||
        count(*) || ' iguales' from verif.pac v join mimiciv_hosp.patients p on p.subject_id = """
                      + mapa_id(variante, "v.subject_id") + ";")
    # Reversión.
    originales = sorted(int(x) for x in psql("salud-anon", db, "select subject_id from verif.pac").splitlines())
    seudo = sorted(int(x) for x in psql("salud-anon", db, "select subject_id from mimiciv_hosp.patients").splitlines())
    if variante == "nativas":
        # Con un solo par conocido (original, seudónimo) se obtiene el desplazamiento y se revierte todo.
        par = int(uno("salud-anon", db, f"select anon.pseudo_shift({originales[0]})"))
        k = par - originales[0]
        recuperados = sum(1 for s in seudo if s - k in set(originales))
        res["reversion"] = {"metodo": "un par conocido -> desplazamiento", "recuperados": recuperados,
                            "de": len(seudo)}
    else:
        # Con la sal (filtrada o de alguien de adentro): se recorre todo el dominio de 8 dígitos 1xxxxxxx.
        t0 = time.time()
        objetivo, inverso, colisiones = set(seudo), {}, 0
        vistos = bytearray(10_000_000)
        for i in range(10_000_000, 20_000_000):
            h = int(hashlib.sha256(f"id{i}{SAL}".encode()).hexdigest()[:15], 16) % 10_000_000
            if vistos[h]:
                colisiones += 1
            vistos[h] = 1
            if 10_000_000 + h in objetivo:
                inverso.setdefault(10_000_000 + h, []).append(i)
        orig = set(originales)
        aciertos = sum(1 for s in seudo if len(inverso.get(s, [])) == 1 and inverso[s][0] in orig)
        ambiguos = sum(1 for s in seudo if len(inverso.get(s, [])) > 1)
        # La mapa real: el seudónimo de cada original (para verificar que el recorrido acierta).
        correctos = sum(1 for s in seudo for c in inverso.get(s, []) if c in orig)
        res["reversion"] = {"metodo": "sal conocida -> recorrer los 10 millones de ids posibles",
                            "recuperados_sin_ambiguedad": aciertos, "con_varios_candidatos": ambiguos,
                            "con_el_original_entre_los_candidatos": correctos, "de": len(seudo),
                            "segundos": round(time.time() - t0, 1),
                            "colisiones_en_el_dominio": colisiones,
                            "seudonimos_distintos_en_el_dominio": int(sum(vistos))}
        del vistos


def medir_synthea(db, res):
    q = """with d as (
             select v.patient, e.start::timestamptz - v.start::timestamptz s from verif.enc v
               join synthea.encounters e on e.id = masc.uuid_hash(v.id)
             union all select v.id, (p.birthdate::date - v.birthdate::date) * interval '1 day' from verif.pac v
               join synthea.patients p on p.id = masc.uuid_hash(v.id))
           select count(*), count(*) filter (where n = 1) from (select patient, count(distinct s) n from d group by 1) x;"""
    tot, uno_solo = uno("salud-anon", db, q).split("|")
    res["fechas_por_paciente"] = {"pacientes": int(tot), "con_un_solo_desplazamiento": int(uno_solo)}
    q = """select count(*),
             count(*) filter (where p.first = v.first), count(*) filter (where p.last = v.last),
             count(*) filter (where p.ssn = v.ssn), count(*) filter (where p.ssn ~ '^999-[0-9]{2}-[0-9]{4}$'),
             count(*) filter (where p.passport is not null and p.passport <> '' and p.passport = v.passport),
             count(*) filter (where p.zip = v.zip)
           from verif.pac v join synthea.patients p on p.id = masc.uuid_hash(v.id);"""
    n, nom, ape, ssn, ssn_fmt, pas, zip_ = map(int, uno("salud-anon", db, q).split("|"))
    res["directos"] = {"pacientes": n, "nombre_igual": nom, "apellido_igual": ape, "ssn_igual": ssn,
                       "ssn_formato_valido": ssn_fmt, "pasaporte_igual": pas, "zip_igual": zip_}
    res["nombres_distintos"] = uno("salud-anon", db, "select count(distinct first || ' ' || last) || ' de ' || count(*) "
                                                     "from synthea.patients;")
    res["ids_originales_que_quedan"] = int(uno("salud-anon", db,
        "select count(*) from synthea.patients where id in (select id from verif.pac);"))


if __name__ == "__main__":
    main()
