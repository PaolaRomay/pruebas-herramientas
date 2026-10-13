# Pagila en Neon (para Tonic Structural)

**Quién / cuándo:** Jero, 2026-10-11 (fecha de los logs de carga).
**Fuente de cada dato:** P = prueba propia, salvo donde dice D.

[← Estado de las pruebas](../ESTADO.md) · [Ficha de Tonic](tonic.md)

Tonic Structural corre en la nube de Tonic y no puede leer el contenedor local, así que Pagila se cargó en una base PostgreSQL gestionada en **Neon**. Pruebas que lo usan: A8, B4, C2, E6 y G3.

> **Las cadenas de conexión están solo en `.env` (gitignored), como `NEON_ORIGEN` y `NEON_DESTINO`.** No se copian en ningún archivo del repo, ni en logs ni en capturas. Los comandos de abajo las pasan como variable de entorno.

## Bases

| Base | Contenido | Uso |
|---|---|---|
| `pagila_origen` | Copia exacta de Pagila (pagila-v4.0.0, mismos `01-schema.sql` y `02-data.sql` del repo) | Origen del workspace de Structural |
| `pagila_destino` | Vacía | Donde Structural escribe la base anonimizada o el subconjunto |

- Versión de PostgreSQL en Neon: **18.6** en las dos bases (`select version()`, 2026-10-11).
  - Es mayor que la del contenedor (16.4): `traer_neon.py` necesita un `pg_dump` 18. Ver «Traer el destino».
- Región: AWS `us-east-2` (sale del host de la conexión). Plan: _(completar)_.

## Carga

Se usó el `psql` del contenedor `pagila-db` (no hace falta PostgreSQL en el Mac). Esquema primero y datos después:

```bash
set -a; source .env; set +a
docker exec -i -e NEON_ORIGEN pagila-db sh -c 'psql "$NEON_ORIGEN"' < data/pagila/01-schema.sql > carga_esquema.log 2>&1
docker exec -i -e NEON_ORIGEN pagila-db sh -c 'psql "$NEON_ORIGEN"' < data/pagila/02-data.sql   > carga_datos.log 2>&1
```

Confirmado (Jero): fue este comando. La carga en Neon es solo para las pruebas de Structural (A8, B4, C2, E6, G3), que todavía no se corrieron.

### Errores esperables

- `carga_esquema.log`: **105 veces `ERROR: role "postgres" does not exist`**. Son los `ALTER ... OWNER TO postgres` del dump de Pagila. En Neon el usuario no se llama `postgres`, así que los objetos quedan a nombre del usuario de Neon. **No afecta a la prueba.** No hay otros errores. Se crearon 70 tablas, 37 índices, 15 triggers, 13 secuencias, 9 funciones, 7 vistas y 2 dominios.
- `carga_datos.log`: 0 errores. 69 `COPY` (las 14 tablas comunes más las 55 particiones de `payment`) y 13 `setval`.

Para evitar esos errores: cargar con `--no-owner` desde un dump propio o filtrar las líneas `OWNER TO`. No hace falta.

## Verificación de conteos

Del log de datos (`COPY n`), iguales a la base local:

| Tabla | Filas |
|---|---|
| customer | 999 |
| address | 1003 |
| film | 1000 |
| rental | 51 805 |
| payment (suma de las 55 particiones) | 51 061 |
| actor / city / country / staff / store | 200 / 600 / 109 / 1500 / 500 |

Para comprobarlo contra la base ya cargada:

```bash
docker exec -e NEON_ORIGEN pagila-db sh -c 'psql "$NEON_ORIGEN" -c "select (select count(*) from customer) c, (select count(*) from address) a, (select count(*) from film) f, (select count(*) from payment) p"'
```

Debe dar 999, 1003, 1000 y 51061.

Verificado el 2026-10-11 (con `psycopg2` del `.venv`, porque Docker estaba pausado): `pagila_origen` da **999, 1003, 1000 y 51061**, con 77 tablas en `public`. `pagila_destino` está vacía (0 tablas).

## Traer el destino

`scripts/traer_neon.py` hace el `pg_dump --data-only` de `NEON_DESTINO` dentro del contenedor, sin poner la cadena en la línea de comandos. Lo carga en una base local sin restricciones y mide la integridad con `scripts/integridad.py`. Uso en el README de [B4](../B4-tonic-structural/README.md).

Si Neon corre una versión de PostgreSQL mayor que 16, `pg_dump` falla con «server version mismatch». Se usa un `pg_dump` de la misma versión:

```bash
PG_DUMP_CMD="docker run --rm -e {variable} postgres:18" python scripts/traer_neon.py ...
```

Neon está en 18.6, así que **hace falta siempre**. Sin probar todavía: el dump de un `pg_dump` 18 puede traer líneas que el `psql` 16.4 del contenedor no entiende (por ejemplo `SET transaction_timeout` o `\restrict`). Si la carga falla por eso, mirar `carga.log` y filtrar esas líneas o levantar el contenedor local con PostgreSQL 18.

## Evidencia

- `evidencia/neon/carga_esquema.log` y `evidencia/neon/carga_datos.log`. Revisados: no contienen credenciales.
