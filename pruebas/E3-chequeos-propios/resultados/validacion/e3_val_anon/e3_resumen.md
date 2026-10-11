# E3: evaluación de `e3_val_anon` (anonimizada)

Corrida: 2026-10-10 21:16

## Entorno

- Equipo: arm64, macOS 26.6.2, Python 3.11.16
- PostgreSQL 16.4 (Debian 16.4-1.pgdg120+2) (contenedor `pagila-db`). Restricciones: base común `pagila` (pagila-v4.0.0)
- sdv 1.32.1, sdmetrics 0.25.0, anonymeter 1.1.0, pandas 3.0.6, numpy 1.26.4
- Candidata: `e3_val_anon`, tipo `anonimizada`
- Control: 200 clientes (20%), semilla `e3`; ataques de Anonymeter: hasta 500
- Tiempo: integridad 0 s, calidad 2 s, privacidad 2 s

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
| payment.customer_id -> customer (en la tabla padre) | declarada en 6 de 55 particiones | ok | 0 |  |
| payment.rental_id -> rental (en la tabla padre) | declarada en 6 de 55 particiones | ok | 0 |  |
| payment.staff_id -> staff (en la tabla padre) | declarada en 6 de 55 particiones | ok | 0 |  |
| store.manager_staff_id -> staff | no declarada en el catálogo | ok | 0 |  |

## 2. Calidad (SDMetrics)

Datos reales de comparación: `pagila`. Tablas: 15. Relaciones en la metadata: 21. Tiempo: 0 s.

**Calidad: 0.991**, **diagnóstico: 0.996** (0 a 1; 1 = igual a los datos reales).

| reporte | propiedad | score |
|---|---|---|
| calidad | Column Shapes | 0.964 |
| calidad | Column Pair Trends | 1.000 |
| calidad | Cardinality | 1.000 |
| calidad | Intertable Trends | 1.000 |
| diagnóstico | Data Validity | 0.988 |
| diagnóstico | Data Structure | 1.000 |
| diagnóstico | Relationship Validity | 1.000 |

Columnas por tipo en la metadata: id 37, unknown 17, numerical 8, categorical 5, datetime 4, boolean 2. Las `unknown` (texto con muchos valores distintos: nombres, correos, direcciones) y las `id` no entran en Column Shapes.

Columnas con peor forma (Column Shapes):

| tabla | columna | métrica | score |
|---|---|---|---|
| payment | amount | KSComplement | 0.325 |
| address | address2 | TVComplement | 1.000 |
| staff | active | TVComplement | 1.000 |
| rental | return_date | KSComplement | 1.000 |
| rental | rental_date | KSComplement | 1.000 |
| payment | payment_date | KSComplement | 1.000 |
| language | name | TVComplement | 1.000 |
| film | rating | TVComplement | 1.000 |

Excluidas de la comparación (tipo no soportado o columna técnica): actor.last_update, address.last_update, category.last_update, city.last_update, country.last_update, customer.last_update, film.last_update, film.special_features, film.fulltext, film_actor.last_update, film_category.last_update, inventory.last_update, language.last_update, rental.last_update, staff.last_update, staff.picture, store.last_update.

## 3. Privacidad

Registro «persona» (customer + address + city + country, 11 atributos). Original sin control: 799 filas; control: 200; candidata: 799.

**Anonymeter.** Riesgo = cuánto mejor le va al ataque contra los datos originales que contra el control (0 = nada, 1 = total). «Tasa azar» es un ataque que adivina sin mirar la candidata.

| ataque | detalle | n_ataques | riesgo | ic95 | tasa_ataque | tasa_azar | tasa_control | nota |
|---|---|---|---|---|---|---|---|---|
| singling out | univariado | 200 | 0.488 | 0.418–0.558 | 0.495 | 0.181 | 0.014 |  |
| singling out | multivariado (3 columnas) | 200 | 0.133 | 0.084–0.181 | 0.142 | 0.137 | 0.011 |  |
| linkability | first_name+last_name+email | district+postal_code+phone+city+country | 200 | 0.000 | 0.000–0.000 | 0.009 | 0.009 | 0.054 | el ataque no supera al azar: no concluyente |
| inference | secreto district | 200 | 0.118 | 0.000–0.263 | 0.451 | 0.083 | 0.377 |  |
| inference | secreto city | 200 | 0.189 | 0.049–0.329 | 0.495 | 0.073 | 0.377 |  |
| inference | secreto country | 200 | 0.217 | 0.070–0.364 | 0.539 | 0.103 | 0.412 |  |
| inference | secreto postal_code | 200 | 0.436 | 0.367–0.505 | 0.441 | 0.009 | 0.009 |  |

**Distancia al registro más cercano (Gower, 0 = copia exacta).**

- Filas de la candidata que son copia exacta de una persona real: **0.0%**
- Mediana de la distancia candidata → original: 0.364 (percentil 5: 0.364); control → original, como referencia: 0.546
- Cuota de filas más cerca del entrenamiento que del control (submuestra de 200, mismo tamaño que el control): 0.609. Va de 0,50 (no memoriza) a 0.625 (copia todo el entrenamiento). **Índice de memorización: 0.87** (0 = no memoriza, 1 = copia todo; negativo = más lejos que el control)

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
