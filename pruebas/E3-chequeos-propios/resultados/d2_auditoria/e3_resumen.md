# E3: evaluación de `d2_auditoria` (sintetica)

Corrida: 2026-10-11 00:18

## Entorno

- Equipo: arm64, macOS 26.6.2, Python 3.11.16
- PostgreSQL 16.4 (Debian 16.4-1.pgdg120+2) (contenedor `pagila-db`). Restricciones: base común `pagila` (pagila-v4.0.0)
- sdv 1.32.1, sdmetrics 0.25.0, anonymeter 1.1.0, pandas 3.0.6, numpy 1.26.4
- Candidata: `d2_auditoria`, tipo `sintetica`, entrenada con `e3_entrenamiento`
- Control: 200 clientes (20%), semilla `e3`; ataques de Anonymeter: hasta 500
- Tiempo: integridad 0 s, calidad 3 s, privacidad 2 s

## 1. Integridad

Restricciones de Pagila declaradas en la candidata: **0 de 132** (si están todas, la carga ya rechazó lo que las violaba).

Restricciones del catálogo (`scripts/integridad.py`):

| tipo | restricciones | violadas | filas | sin_comprobar |
|---|---|---|---|---|
| FK | 36 | 0 | 0 | 0 |
| PK | 15 | 2 | 184 | 0 |
| UNIQUE (índice) | 5 | 1 | 85 | 0 |
| NOT NULL | 75 | 0 | 0 | 0 |
| CHECK (dominio) | 1 | 0 | 0 | 0 |

Relaciones que el catálogo no cubre (agregadas por E3):

| nombre | origen | estado | violaciones | ejemplos |
|---|---|---|---|---|
| payment.customer_id -> customer (en la tabla padre) | declarada en 6 de 55 particiones | ok | 0 |  |
| payment.rental_id -> rental (en la tabla padre) | declarada en 6 de 55 particiones | ok | 0 |  |
| payment.staff_id -> staff (en la tabla padre) | declarada en 6 de 55 particiones | ok | 0 |  |
| store.manager_staff_id -> staff | no declarada en el catálogo | ok | 0 |  |

Restricciones del catálogo violadas:

| tipo | tabla | nombre | columnas | violaciones | ejemplos |
|---|---|---|---|---|---|
| PK | film_actor | film_actor_pkey | actor_id, film_id | 70 | (68,352); (4,282); (6,168) |
| PK | film_category | film_category_pkey | film_id, category_id | 114 | (109,4); (697,9); (27,5) |
| UNIQUE (índice) | store | idx_unq_manager_staff_id | manager_staff_id | 85 | (1366); (604); (1173) |

## 2. Calidad (SDMetrics)

Datos reales de comparación: `e3_entrenamiento`. Tablas: 15. Relaciones en la metadata: 21. Tiempo: 0 s.

**Calidad: 0.768**, **diagnóstico: 0.969** (0 a 1; 1 = igual a los datos reales).

| reporte | propiedad | score |
|---|---|---|
| calidad | Column Shapes | 0.790 |
| calidad | Column Pair Trends | 0.879 |
| calidad | Cardinality | 0.705 |
| calidad | Intertable Trends | 0.699 |
| diagnóstico | Data Validity | 0.919 |
| diagnóstico | Data Structure | 1.000 |
| diagnóstico | Relationship Validity | 0.988 |

Columnas por tipo en la metadata: id 37, unknown 17, numerical 8, categorical 5, datetime 4, boolean 2. Las `unknown` (texto con muchos valores distintos: nombres, correos, direcciones) y las `id` no entran en Column Shapes.

Columnas con peor forma (Column Shapes):

| tabla | columna | métrica | score |
|---|---|---|---|
| category | name | TVComplement | 0.000 |
| language | name | TVComplement | 0.000 |
| store | manager_staff_id | KSComplement | 0.408 |
| customer | create_date | KSComplement | 0.631 |
| payment | amount | KSComplement | 0.727 |
| payment | payment_date | KSComplement | 0.843 |
| rental | return_date | KSComplement | 0.859 |
| rental | rental_date | KSComplement | 0.860 |

Excluidas de la comparación (tipo no soportado o columna técnica): actor.last_update, address.last_update, category.last_update, city.last_update, country.last_update, customer.last_update, film.last_update, film.special_features, film.fulltext, film_actor.last_update, film_category.last_update, inventory.last_update, language.last_update, rental.last_update, staff.last_update, staff.picture, store.last_update.

## 3. Privacidad

Registro «persona» (customer + address + city + country, 11 atributos). Original sin control: 799 filas; control: 200; candidata: 640.

**Anonymeter.** Riesgo = cuánto mejor le va al ataque contra los datos originales que contra el control (0 = nada, 1 = total). «Tasa azar» es un ataque que adivina sin mirar la candidata.

| ataque | detalle | n_ataques | riesgo | ic95 | tasa_ataque | tasa_azar | tasa_control | nota |
|---|---|---|---|---|---|---|---|---|
| singling out | univariado | 200 | 0.005 | 0.000–0.021 | 0.014 | 0.009 | 0.009 |  |
| singling out | multivariado (3 columnas) | 200 | 0.000 | 0.000–0.013 | 0.009 | 0.029 | 0.009 | el ataque no supera al azar: no concluyente |
| linkability | first_name+last_name+email | district+postal_code+phone+city+country | 200 | 0.000 | 0.000–1.000 | 0.981 | 0.009 | 0.991 |  |
| inference | secreto district | 200 | 0.000 | 0.000–0.013 | 0.009 | 0.009 | 0.009 | el ataque no supera al azar: no concluyente |
| inference | secreto city | 200 | 0.000 | 0.000–0.013 | 0.009 | 0.009 | 0.009 | el ataque no supera al azar: no concluyente |
| inference | secreto country | 200 | 0.000 | 0.000–0.013 | 0.009 | 0.009 | 0.009 | el ataque no supera al azar: no concluyente |
| inference | secreto postal_code | 200 | 0.000 | 0.000–0.013 | 0.009 | 0.009 | 0.009 | el ataque no supera al azar: no concluyente |

**Distancia al registro más cercano (Gower, 0 = copia exacta).**

- Filas de la candidata que son copia exacta de una persona real: **0.0%**
- Mediana de la distancia candidata → original: 0.727 (percentil 5: 0.727); control → original, como referencia: 0.546
- Cuota de filas más cerca del entrenamiento que del control (submuestra de 200, mismo tamaño que el control): 0.609. Va de 0,50 (no memoriza) a 0.625 (copia todo el entrenamiento). **Índice de memorización: 0.87** (0 = no memoriza, 1 = copia todo; negativo = más lejos que el control)

## Filas por tabla

| tabla | pagila | candidata |
|---|---|---|
| actor | 200 | 200 |
| address | 1003 | 795 |
| category | 16 | 16 |
| city | 600 | 795 |
| country | 109 | 109 |
| customer | 999 | 640 |
| film | 1000 | 1000 |
| film_actor | 5462 | 5461 |
| film_category | 2367 | 2360 |
| inventory | 4581 | 4619 |
| language | 6 | 6 |
| payment | 51061 | 44227 |
| rental | 51805 | 44227 |
| staff | 1500 | 1388 |
| store | 500 | 500 |

Detalle en los CSV de esta carpeta (`e3_integridad.csv`, `e3_calidad_*.csv`, `e3_privacidad.csv`, `e3_dcr.csv`, `e3_conteos.csv`).
