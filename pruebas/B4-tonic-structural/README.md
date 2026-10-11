# B4 — Tonic Structural (Anonimizar)

Requiere el trial de Structural, Pagila en Neon ([neon.md](../_herramientas/neon.md)) y el contenedor local levantado. Se usa `pagila_origen` completo, con los clientes de control (decisión en la ficha; afecta a E6).

## Pasos

1. En el workspace `pagila_origen` → `pagila_destino`, configurar los generadores de la tabla de la ficha: nombres y emails **consistentes**; `address`, `phone`, `uuid`, `username` y `password` anonimizados; claves `*_id` sin tocar. Captura en `evidencia/b4_generadores.png`.
2. Fijar una semilla y generar (**corrida 1**). Anotar el tiempo del job y capturar el log.
3. Traer el destino y medir la integridad (la cadena de conexión se lee de `.env`):

   ```bash
   python scripts/traer_neon.py --base b4_c1 --salida pruebas/B4-tonic-structural/resultados/corrida1
   ```

   Neon usa PostgreSQL 18.6: anteponer `PG_DUMP_CMD="docker run --rm -e {variable} postgres:18"`.
4. Repetir con la **misma semilla** (corrida 2 → `b4_c2`) y **sin semilla** (corrida 3 → `b4_c3`). Cada generación pisa `pagila_destino`, así que hay que traerla antes de volver a generar.
5. Extra fail-closed: agregar la columna en el origen, pedir la generación, capturar y volver atrás:

   ```bash
   set -a; source .env; set +a
   docker exec -i -e NEON_ORIGEN pagila-db sh -c 'psql "$NEON_ORIGEN"' <<'SQL'
   alter table customer add column notas text;
   update customer set notas = first_name || ' ' || last_name || ' vive en ' || address_id;
   SQL
   # ... pedir la generación en Structural y capturar el resultado ...
   docker exec -i -e NEON_ORIGEN pagila-db sh -c 'psql "$NEON_ORIGEN"' <<'SQL'
   alter table customer drop column notas;
   SQL
   ```

## Consultas de medición (sobre las copias locales)

Usan `dblink` para cruzar con la base común `pagila`, sin modificarla. Correr con `docker exec -i pagila-db psql -U postgres -d b4_c1`.

**Coherencia ciudad ↔ código postal contra el original:**

```sql
create extension if not exists dblink;
with ori as (select * from dblink('dbname=pagila user=postgres',
    'select address_id, city_id, postal_code from address') as t(address_id int, city_id int, postal_code text))
select count(*) as direcciones,
       count(*) filter (where a.city_id = o.city_id) as misma_ciudad,
       count(*) filter (where a.postal_code is not distinct from o.postal_code) as mismo_cp,
       count(*) filter (where exists (select 1 from ori p where p.city_id = a.city_id
                                      and p.postal_code is not distinct from a.postal_code)) as par_ciudad_cp_real
from address a join ori o using (address_id);
```

**Consistencia entre corridas** (en `b4_c1`, cambiando `b4_c2` por `b4_c3` para la corrida sin semilla):

```sql
with otra as (select * from dblink('dbname=b4_c2 user=postgres',
    'select customer_id, first_name, last_name, email, uuid::text from customer')
    as t(customer_id int, first_name text, last_name text, email text, uuid text))
select count(*) as clientes,
       count(*) filter (where c.first_name = o.first_name and c.last_name = o.last_name) as nombres_iguales,
       count(*) filter (where c.email = o.email) as emails_iguales,
       count(*) filter (where c.uuid::text = o.uuid) as uuid_iguales
from customer c join otra o using (customer_id);
```

**Consistencia dentro de una corrida** (¿un nombre original da siempre el mismo nombre falso?):

```sql
with ori as (select * from dblink('dbname=pagila user=postgres', 'select customer_id, first_name from customer')
             as t(customer_id int, first_name text))
select count(*) as nombres_originales_repetidos,
       count(*) filter (where falsos > 1) as con_mas_de_un_falso
from (select o.first_name, count(distinct c.first_name) as falsos, count(*) as n
      from customer c join ori o using (customer_id) group by o.first_name having count(*) > 1) x;
```

Las tres consultas se probaron sobre copias de Pagila con cambios conocidos. Con 10 códigos postales cambiados, la de coherencia dio 1003 / 1003 / 993 / 993. Con 5 nombres cambiados, la de corridas dio 994 nombres iguales de 999.

Al terminar, las bases `b4_c*` pueden quedar para E6 (`evaluar_bd.py evaluar --candidata b4_c1 --tipo anonimizada`) o borrarse con `DROP DATABASE`.
