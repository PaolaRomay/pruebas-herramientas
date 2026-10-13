# E3: evaluación de `d5_auditoria` (sintetica)

Corrida: 2026-10-10 23:36

## Entorno

- Equipo: arm64, macOS 26.6.2, Python 3.11.16
- PostgreSQL 16.4 (Debian 16.4-1.pgdg120+2) (contenedor `pagila-db`). Restricciones: base común `pagila` (pagila-v4.0.0)
- sdv 1.32.1, sdmetrics 0.25.0, anonymeter 1.1.0, pandas 3.0.6, numpy 1.26.4
- Candidata: `d5_auditoria`, tipo `sintetica`
- Control: 200 clientes (20%), semilla `e3`; ataques de Anonymeter: hasta 500
- Tiempo: integridad 0 s, calidad 3 s, privacidad 2 s

## 1. Integridad

Restricciones de Pagila declaradas en la candidata: **0 de 132** (si están todas, la carga ya rechazó lo que las violaba).

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
| payment.customer_id -> customer (en la tabla padre) | declarada en 6 de 55 particiones | ok | 0 |  |
| payment.rental_id -> rental (en la tabla padre) | declarada en 6 de 55 particiones | ok | 0 |  |
| payment.staff_id -> staff (en la tabla padre) | declarada en 6 de 55 particiones | ok | 0 |  |
| store.manager_staff_id -> staff | no declarada en el catálogo | ok | 0 |  |

## 2. Calidad (SDMetrics)

Datos reales de comparación: `pagila`. Tablas: 15. Relaciones en la metadata: 21. Tiempo: 0 s.

**Calidad: 0.601**, **diagnóstico: 0.935** (0 a 1; 1 = igual a los datos reales).

| reporte | propiedad | score |
|---|---|---|
| calidad | Column Shapes | 0.625 |
| calidad | Column Pair Trends | 0.787 |
| calidad | Cardinality | 0.427 |
| calidad | Intertable Trends | 0.567 |
| diagnóstico | Data Validity | 0.893 |
| diagnóstico | Data Structure | 0.970 |
| diagnóstico | Relationship Validity | 0.943 |

Columnas por tipo en la metadata: id 37, unknown 17, numerical 8, categorical 5, datetime 4, boolean 2. Las `unknown` (texto con muchos valores distintos: nombres, correos, direcciones) y las `id` no entran en Column Shapes.

Columnas con peor forma (Column Shapes):

| tabla | columna | métrica | score |
|---|---|---|---|
| rental | return_date | KSComplement | 0.000 |
| rental | rental_date | KSComplement | 0.000 |
| customer | create_date | KSComplement | 0.000 |
| address | address2 | TVComplement | 0.000 |
| store | manager_staff_id | KSComplement | 0.006 |
| film | release_year | KSComplement | 0.060 |
| film | length | KSComplement | 0.892 |
| film | replacement_cost | KSComplement | 0.899 |

Excluidas de la comparación (tipo no soportado o columna técnica): actor.last_update, address.last_update, category.last_update, city.last_update, country.last_update, customer.last_update, film.last_update, film.special_features, film.fulltext, film_actor.last_update, film_category.last_update, inventory.last_update, language.last_update, rental.last_update, staff.last_update, staff.picture, store.last_update.

## 3. Privacidad

Registro «persona» (customer + address + city + country, 11 atributos). Original sin control: 799 filas; control: 200; candidata: 120.

**Anonymeter.** Riesgo = cuánto mejor le va al ataque contra los datos originales que contra el control (0 = nada, 1 = total). «Tasa azar» es un ataque que adivina sin mirar la candidata.

| ataque | detalle | n_ataques | riesgo | ic95 | tasa_ataque | tasa_azar | tasa_control | nota |
|---|---|---|---|---|---|---|---|---|
| singling out | univariado | 120 | 0.182 | 0.104–0.259 | 0.209 | 0.048 | 0.034 |  |
| singling out | multivariado (3 columnas) | 120 | 0.033 | 0.000–0.071 | 0.048 | 0.040 | 0.016 |  |
| linkability | first_name+last_name+email | district+postal_code+phone+city+country | 120 | 0.085 | 0.000–0.192 | 0.217 | 0.016 | 0.145 |  |
| inference | secreto district | 120 | 0.000 | 0.000–0.032 | 0.024 | 0.016 | 0.024 |  |
| inference | secreto city | 120 | 0.000 | 0.000–0.022 | 0.016 | 0.016 | 0.016 | el ataque no supera al azar: no concluyente |
| inference | secreto country | 120 | 0.051 | 0.000–0.114 | 0.096 | 0.024 | 0.048 |  |
| inference | secreto postal_code | 120 | 0.000 | 0.000–0.022 | 0.016 | 0.016 | 0.016 | el ataque no supera al azar: no concluyente |

**Distancia al registro más cercano (Gower, 0 = copia exacta).**

- Filas de la candidata que son copia exacta de una persona real: **0.0%**
- Mediana de la distancia candidata → original: 0.981 (percentil 5: 0.885); control → original, como referencia: 0.546
- Cuota de filas más cerca del entrenamiento que del control (submuestra de 200, mismo tamaño que el control): 0.358. Va de 0,50 (no memoriza) a 0.625 (copia todo el entrenamiento). **Índice de memorización: -1.13** (0 = no memoriza, 1 = copia todo; negativo = más lejos que el control)

## Filas por tabla

| tabla | pagila | candidata |
|---|---|---|
| actor | 200 | 40 |
| address | 1003 | 125 |
| category | 16 | 16 |
| city | 600 | 120 |
| country | 109 | 22 |
| customer | 999 | 120 |
| film | 1000 | 200 |
| film_actor | 5462 | 1092 |
| film_category | 2367 | 200 |
| inventory | 4581 | 916 |
| language | 6 | 6 |
| payment | 51061 | 0 |
| rental | 51805 | 3209 |
| staff | 1500 | 2 |
| store | 500 | 2 |

## Avisos

- privacidad: no se indicó --entrenada-con. Si la herramienta se entrenó con `pagila` completa, vio el control y el riesgo sale subestimado

Detalle en los CSV de esta carpeta (`e3_integridad.csv`, `e3_calidad_*.csv`, `e3_privacidad.csv`, `e3_dcr.csv`, `e3_conteos.csv`).
