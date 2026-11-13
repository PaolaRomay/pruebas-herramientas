-- Funciones de enmascaramiento propias para B1m / B1s, en el esquema `masc` (declarado TRUSTED para anon).
-- Todas son deterministas y dependen de la sal secreta de la base (anon.salt, vía anon.hash): el mismo valor de
-- entrada da siempre el mismo seudónimo en todas las tablas, así se mantienen las relaciones.
create schema if not exists masc;

-- Entero de 60 bits a partir del hash con sal. Da exactamente lo mismo que anon.hash(t) (sha256 de t || sal).
-- La sal (anon.salt) solo la puede leer un superusuario: el rol que enmascara no la ve. Por eso la función es
-- SECURITY DEFINER, igual que anon.hash. Escrita en plpgsql cuesta ~31 µs por llamada con la imagen emulada,
-- contra ~100 µs de anon.hash (medido con 20 000 llamadas).
create or replace function masc.h(t text) returns bigint language plpgsql stable parallel safe security definer
  set search_path = ''
  as $$ begin return ('x' || left(pg_catalog.encode(pg_catalog.sha256(pg_catalog.convert_to(
                        t || pg_catalog.current_setting('anon.salt'), 'UTF8')), 'hex'), 15))::bit(60)::bigint; end $$;

-- Id entero con el mismo largo y el mismo primer dígito (MIMIC: 1xxxxxxx pacientes, 2xxxxxxx internaciones,
-- 3xxxxxxx estadías). No es una biyección: puede haber colisiones (se miden).
create or replace function masc.id_hash(id bigint) returns bigint language sql stable parallel safe
  as $$ select case when id < 10 then id else
         left(id::text, 1)::bigint * (10 ^ (length(id::text) - 1))::bigint
         + masc.h('id' || id::text) % (10 ^ (length(id::text) - 1))::bigint end $$;

-- Ids compuestos «<subject_id>-<secuencia>» (poe_id, emar_id): se seudonimiza la parte del paciente.
create or replace function masc.id_compuesto(t text) returns text language sql stable parallel safe
  as $$ select masc.id_hash(split_part(t, '-', 1)::bigint)::text || '-' || split_part(t, '-', 2) $$;

-- Texto con el mismo largo y el mismo primer carácter (ids de profesionales «P12MPP»).
create or replace function masc.texto_hash(t text) returns text language sql stable parallel safe
  as $$ select left(t, 1) || upper(substr(anon.hash('tx' || t), 1, length(t) - 1)) $$;

-- UUID seudónimo (ids de Synthea).
create or replace function masc.uuid_hash(t text) returns text language sql stable parallel safe
  as $$ select regexp_replace(left(anon.hash('uuid' || t), 32), '(.{8})(.{4})(.{4})(.{4})(.{12})',
                              '\1-\2-\3-\4-\5') $$;

-- Mismo formato: cada dígito se reemplaza por un dígito derivado del hash (SSN, licencia, pasaporte, UDI).
create or replace function masc.mismo_formato(t text, clave text) returns text language sql stable parallel safe
  as $$ select string_agg(case when c ~ '[0-9]'
                               then (('x' || substr(anon.hash('fmt' || clave || i::text), 1, 2))::bit(8)::int % 10)::text
                               else c end, '' order by i)
        from unnest(string_to_array(t, null)) with ordinality u(c, i) $$;

-- Desplazamiento de fechas por paciente: entre -180 y +180 días, el mismo para todas las fechas del paciente.
create or replace function masc.dias(clave text) returns int language sql stable parallel safe
  as $$ select (masc.h('fecha' || clave) % 361)::int - 180 $$;
create or replace function masc.desplazar(t timestamp, clave bigint) returns timestamp language sql stable parallel safe
  as $$ select t + make_interval(days => masc.dias(clave::text)) $$;
create or replace function masc.desplazar(t date, clave bigint) returns date language sql stable parallel safe
  as $$ select t + masc.dias(clave::text) $$;
-- Synthea guarda las fechas como texto ISO: «2019-02-17» o «2019-02-17T05:07:38Z».
create or replace function masc.desplazar(t text, clave text) returns text language sql stable parallel safe
  as $$ select case when t is null or t = '' then t
                    when length(t) = 10 then to_char(t::date + masc.dias(clave), 'YYYY-MM-DD')
                    else to_char(t::timestamptz at time zone 'UTC' + make_interval(days => masc.dias(clave)),
                                 'YYYY-MM-DD"T"HH24:MI:SS"Z"') end $$;

-- Generalizaciones.
create or replace function masc.decada(x smallint) returns smallint language sql immutable parallel safe
  as $$ select (x / 10 * 10)::smallint $$;
create or replace function masc.zip3(x bigint) returns bigint language sql immutable parallel safe
  as $$ select x / 100 * 100 $$;
create or replace function masc.redondear(x double precision, d int) returns double precision language sql
  immutable parallel safe as $$ select round(x::numeric, d)::double precision $$;

security label for anon on schema masc is 'TRUSTED';
grant usage on schema masc to enmascarador;
