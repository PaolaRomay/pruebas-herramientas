# D5: Tonic Fabricate, integridad de la base generada contra el esquema de Pagila

Corrida: 2026-10-10 23:36

## Entorno

- Equipo: arm64, Darwin 25.6.0, Python 3.11.16
- PostgreSQL 16.4 (Debian 16.4-1.pgdg120+2) (contenedor `pagila-db`), referencia: base `pagila` (pagila-v4.0.0)
- Archivo de Fabricate: `fabricate.sql`, 934,367 bytes, sha256 `8961211272f5f4d9…`
- Contenido: 22 INSERT, 0 COPY, 0 CREATE TABLE, 0 ALTER TABLE
- Tiempo de carga: estricta 0.2 s, sin restricciones 0.1 s

## 1. ¿Se puede cargar tal cual? (carga estricta)

Errores de psql: **4** sentencias rechazadas. Cada sentencia rechazada descarta todas sus filas (un COPY o un INSERT de varias filas falla entero).

| tipo | tabla | sentencias |
|---|---|---|
| fuera de las particiones | payment | 4 |

FK que se pudieron volver a crear después de cargar: **36 de 36**.

## 2. Violaciones fila por fila (carga sin restricciones)

| tipo | restricciones | violadas | filas | sin_comprobar |
|---|---|---|---|---|
| FK | 36 | 0 | 0 | 0 |
| PK | 15 | 0 | 0 | 0 |
| UNIQUE (índice) | 5 | 0 | 0 | 0 |
| NOT NULL | 75 | 0 | 0 | 0 |
| CHECK (dominio) | 1 | 0 | 0 | 0 |

«filas» = filas que violan (para PK/UNIQUE, filas que sobran por clave repetida).

Errores que quedan aun sin restricciones (tipos, enums, particiones, columnas o tablas que no existen):

| tipo | tabla | sentencias |
|---|---|---|
| fuera de las particiones | payment | 4 |

## 3. Filas por tabla

| tabla | pagila_real | fabricate_cargadas_sin_restricciones | fabricate_cargadas_estricta |
|---|---|---|---|
| actor | 200 | 40 | 40 |
| address | 1003 | 125 | 125 |
| category | 16 | 16 | 16 |
| city | 600 | 120 | 120 |
| country | 109 | 22 | 22 |
| customer | 999 | 120 | 120 |
| film | 1000 | 200 | 200 |
| film_actor | 5462 | 1092 | 1092 |
| film_category | 2367 | 200 | 200 |
| inventory | 4581 | 916 | 916 |
| language | 6 | 6 | 6 |
| payment | 51061 | 0 | 0 |
| rental | 51805 | 3209 | 3209 |
| staff | 1500 | 2 | 2 |
| store | 500 | 2 | 2 |

Detalle: `d5_restricciones.csv`, `d5_conteos.csv` y `../evidencia/d5_errores_carga.csv`. Logs completos de psql en `salidas_grandes/` (no se suben).
