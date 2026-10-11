# E3: evaluación de `e3_val_rota` (subconjunto)

Corrida: 2026-10-10 21:14

## Entorno

- Equipo: arm64, macOS 26.6.2, Python 3.11.16
- PostgreSQL 16.4 (Debian 16.4-1.pgdg120+2) (contenedor `pagila-db`). Restricciones: base común `pagila` (pagila-v4.0.0)
- sdv 1.32.1, sdmetrics 0.25.0, anonymeter 1.1.0, pandas 3.0.6, numpy 1.26.4
- Candidata: `e3_val_rota`, tipo `subconjunto`
- Control: 200 clientes (20%), semilla `e3`; ataques de Anonymeter: hasta 500
- Tiempo: integridad 0 s

## 1. Integridad

Restricciones de Pagila declaradas en la candidata: **132 de 132** (si están todas, la carga ya rechazó lo que las violaba).

Restricciones del catálogo (`scripts/integridad.py`):

| tipo | restricciones | violadas | filas | sin_comprobar |
|---|---|---|---|---|
| FK | 36 | 0 | 0 | 0 |
| PK | 15 | 0 | 0 | 0 |
| UNIQUE (índice) | 5 | 0 | 0 | 0 |
| NOT NULL | 75 | 0 | 0 | 0 |
| CHECK (dominio) | 1 | 0 | 0 | 0 |

Relaciones que el catálogo no cubre (agregadas por E3):

| nombre | origen | estado | violaciones | ejemplos |
|---|---|---|---|---|
| payment.customer_id -> customer (en la tabla padre) | declarada en 6 de 55 particiones | violada | 5 | (99999) |
| payment.rental_id -> rental (en la tabla padre) | declarada en 6 de 55 particiones | ok | 0 |  |
| payment.staff_id -> staff (en la tabla padre) | declarada en 6 de 55 particiones | ok | 0 |  |
| store.manager_staff_id -> staff | no declarada en el catálogo | violada | 1 | (88888) |

## Filas por tabla

| tabla | pagila | candidata |
|---|---|---|
| actor | 200 | 200 |
| address | 1003 | 1003 |
| category | 16 | 16 |
| city | 600 | 600 |
| country | 109 | 109 |
| customer | 999 | 999 |
| film | 1000 | 1000 |
| film_actor | 5462 | 5462 |
| film_category | 2367 | 2367 |
| inventory | 4581 | 4581 |
| language | 6 | 6 |
| payment | 51061 | 51061 |
| rental | 51805 | 51805 |
| staff | 1500 | 1500 |
| store | 500 | 500 |

Detalle en los CSV de esta carpeta (`e3_integridad.csv`, `e3_calidad_*.csv`, `e3_privacidad.csv`, `e3_dcr.csv`, `e3_conteos.csv`).
