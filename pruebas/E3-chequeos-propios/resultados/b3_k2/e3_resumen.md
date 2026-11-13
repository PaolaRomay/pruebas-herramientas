# E3: evaluación de `b3_k2` (anonimizada)

Corrida: 2026-10-14 23:21

## Entorno

- Equipo: arm64, macOS 26.6.2, Python 3.11.16
- PostgreSQL 16.4 (Debian 16.4-1.pgdg120+2) (contenedor `pagila-db`). Restricciones: base común `pagila` (pagila-v4.0.0)
- sdv 1.32.1, sdmetrics 0.25.0, anonymeter 1.1.0, pandas 3.0.6, numpy 1.26.4
- Candidata: `b3_k2`, tipo `anonimizada`, entrenada con `e3_entrenamiento`
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

Datos reales de comparación: `e3_entrenamiento`. Tablas: 4. Relaciones en la metadata: 3. Tiempo: 0 s.

**Calidad: 0.869**, **diagnóstico: 0.974** (0 a 1; 1 = igual a los datos reales).

| reporte | propiedad | score |
|---|---|---|
| calidad | Column Shapes | 0.861 |
| calidad | Column Pair Trends | 0.956 |
| calidad | Cardinality | 0.723 |
| calidad | Intertable Trends | 0.936 |
| diagnóstico | Data Validity | 0.923 |
| diagnóstico | Data Structure | 1.000 |
| diagnóstico | Relationship Validity | 0.998 |

Columnas por tipo en la metadata: unknown 9, id 8, numerical 2, categorical 1, boolean 1, datetime 1. Las `unknown` (texto con muchos valores distintos: nombres, correos, direcciones) y las `id` no entran en Column Shapes.

Columnas con peor forma (Column Shapes):

| tabla | columna | métrica | score |
|---|---|---|---|
| customer | create_date | KSComplement | 0.307 |
| address | address2 | TVComplement | 1.000 |
| customer | store_id | KSComplement | 1.000 |
| customer | activebool | TVComplement | 1.000 |
| customer | active | KSComplement | 1.000 |

Excluidas de la comparación (tipo no soportado o columna técnica): address.last_update, city.last_update, country.last_update, customer.last_update.

## 3. Privacidad

Registro «persona» (customer + address + city + country, 11 atributos). Original sin control: 799 filas; control: 200; candidata: 799.

**Anonymeter.** Riesgo = cuánto mejor le va al ataque contra los datos originales que contra el control (0 = nada, 1 = total). «Tasa azar» es un ataque que adivina sin mirar la candidata.

| ataque | detalle | n_ataques | riesgo | ic95 | tasa_ataque | tasa_azar | tasa_control | nota |
|---|---|---|---|---|---|---|---|---|
| singling out | univariado | 200 | 0.000 | 0.000–0.003 | 0.009 | 0.009 | 0.032 | el ataque no supera al azar: no concluyente |
| singling out | multivariado (3 columnas) | 200 | 0.000 | 0.000–0.013 | 0.009 | 0.019 | 0.012 | el ataque no supera al azar: no concluyente |
| linkability | first_name+last_name+email | district+postal_code+phone+city+country | 200 | 0.000 | 0.000–0.020 | 0.073 | 0.009 | 0.112 |  |
| inference | secreto district | 200 | 0.000 | 0.000–0.013 | 0.009 | 0.009 | 0.009 | el ataque no supera al azar: no concluyente |
| inference | secreto city | 200 | 0.000 | 0.000–0.013 | 0.009 | 0.009 | 0.009 | el ataque no supera al azar: no concluyente |
| inference | secreto country | 200 | 0.000 | 0.000–0.144 | 0.392 | 0.063 | 0.402 |  |
| inference | secreto postal_code | 200 | 0.000 | 0.000–0.013 | 0.009 | 0.009 | 0.009 | el ataque no supera al azar: no concluyente |

**Distancia al registro más cercano (Gower, 0 = copia exacta).**

- Filas de la candidata que son copia exacta de una persona real: **0.0%**
- Mediana de la distancia candidata → original: 0.637 (percentil 5: 0.636); control → original, como referencia: 0.546
- Cuota de filas más cerca del entrenamiento que del control (submuestra de 200, mismo tamaño que el control): 0.373. Va de 0,50 (no memoriza) a 0.625 (copia todo el entrenamiento). **Índice de memorización: -1.02** (0 = no memoriza, 1 = copia todo; negativo = más lejos que el control)

## Filas por tabla

| tabla | pagila | candidata |
|---|---|---|
| actor | 200 | 200 |
| address | 1003 | 912 |
| category | 16 | 16 |
| city | 600 | 658 |
| country | 109 | 110 |
| customer | 999 | 799 |
| film | 1000 | 1000 |
| film_actor | 5462 | 5462 |
| film_category | 2367 | 2367 |
| inventory | 4581 | 4581 |
| language | 6 | 6 |
| payment | 51061 | 41064 |
| rental | 51805 | 41663 |
| staff | 1500 | 1500 |
| store | 500 | 500 |

## Avisos

- privacidad: ningún customer_id de control aparece en la candidata; si la herramienta cambió las claves, el control no se pudo separar y el riesgo puede estar subestimado

Detalle en los CSV de esta carpeta (`e3_integridad.csv`, `e3_calidad_*.csv`, `e3_privacidad.csv`, `e3_dcr.csv`, `e3_conteos.csv`).
