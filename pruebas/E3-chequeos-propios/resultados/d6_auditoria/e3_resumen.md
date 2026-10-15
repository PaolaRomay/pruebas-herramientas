# E3: evaluación de `d6_auditoria` (sintetica)

Corrida: 2026-10-14 22:22

## Entorno

- Equipo: arm64, macOS 26.6.2, Python 3.11.16
- PostgreSQL 16.4 (Debian 16.4-1.pgdg120+2) (contenedor `pagila-db`). Restricciones: base común `pagila` (pagila-v4.0.0)
- sdv 1.32.1, sdmetrics 0.25.0, anonymeter 1.1.0, pandas 3.0.6, numpy 1.26.4
- Candidata: `d6_auditoria`, tipo `sintetica`, entrenada con `e3_entrenamiento`
- Control: 200 clientes (20%), semilla `e3`; ataques de Anonymeter: hasta 500
- Tiempo: integridad 0 s, calidad 3 s, privacidad 2 s

## 1. Integridad

Restricciones de Pagila declaradas en la candidata: **0 de 132** (si están todas, la carga ya rechazó lo que las violaba).

Restricciones del catálogo (`scripts/integridad.py`):

| tipo | restricciones | violadas | filas | sin_comprobar |
|---|---|---|---|---|
| FK | 36 | 2 | 7 | 0 |
| PK | 15 | 0 | 0 | 0 |
| UNIQUE (índice) | 5 | 0 | 0 | 0 |
| NOT NULL | 75 | 0 | 0 | 0 |
| CHECK (dominio) | 1 | 0 | 0 | 0 |

Relaciones que el catálogo no cubre (agregadas por E3):

| nombre | origen | estado | violaciones | ejemplos |
|---|---|---|---|---|
| payment.customer_id -> customer (en la tabla padre) | declarada en 6 de 55 particiones | violada | 1581 | (101); (112); (114) |
| payment.rental_id -> rental (en la tabla padre) | declarada en 6 de 55 particiones | ok | 0 |  |
| payment.staff_id -> staff (en la tabla padre) | declarada en 6 de 55 particiones | ok | 0 |  |
| store.manager_staff_id -> staff | no declarada en el catálogo | ok | 0 |  |

Restricciones del catálogo violadas:

| tipo | tabla | nombre | columnas | violaciones | ejemplos |
|---|---|---|---|---|---|
| FK | customer | customer_address_id_fkey | address_id | 5 | (648); (699); (704) |
| FK | rental | rental_inventory_id_fkey | inventory_id | 2 | (4584); (4588) |

## 2. Calidad (SDMetrics)

Datos reales de comparación: `e3_entrenamiento`. Tablas: 3. Relaciones en la metadata: 3. Tiempo: 0 s.

**Calidad: 0.802**, **diagnóstico: 0.948** (0 a 1; 1 = igual a los datos reales).

| reporte | propiedad | score |
|---|---|---|
| calidad | Column Shapes | 0.770 |
| calidad | Column Pair Trends | 0.930 |
| calidad | Cardinality | 0.588 |
| calidad | Intertable Trends | 0.919 |
| diagnóstico | Data Validity | 0.999 |
| diagnóstico | Data Structure | 1.000 |
| diagnóstico | Relationship Validity | 0.844 |

Columnas por tipo en la metadata: id 9, numerical 7, datetime 4, unknown 3, boolean 1. Las `unknown` (texto con muchos valores distintos: nombres, correos, direcciones) y las `id` no entran en Column Shapes.

Columnas con peor forma (Column Shapes):

| tabla | columna | métrica | score |
|---|---|---|---|
| customer | create_date | KSComplement | 0.288 |
| rental | rental_date | KSComplement | 0.457 |
| payment | payment_date | KSComplement | 0.457 |
| rental | return_date | KSComplement | 0.457 |
| customer | address_id | KSComplement | 0.809 |
| payment | amount | KSComplement | 0.915 |
| rental | inventory_id | KSComplement | 0.938 |
| customer | store_id | KSComplement | 0.956 |

Excluidas de la comparación (tipo no soportado o columna técnica): customer.last_update, rental.last_update.

## 3. Privacidad

Registro «persona» (customer + address + city + country, 11 atributos). Original sin control: 799 filas; control: 200; candidata: 50.

**Anonymeter.** Riesgo = cuánto mejor le va al ataque contra los datos originales que contra el control (0 = nada, 1 = total). «Tasa azar» es un ataque que adivina sin mirar la candidata.

| ataque | detalle | n_ataques | riesgo | ic95 | tasa_ataque | tasa_azar | tasa_control | nota |
|---|---|---|---|---|---|---|---|---|
| singling out | univariado | 50 | 0.628 | 0.493–0.764 | 0.649 | 0.184 | 0.054 |  |
| singling out | multivariado (3 columnas) | 50 | 0.185 | 0.065–0.305 | 0.221 | 0.129 | 0.045 |  |
| linkability | first_name+last_name+email | district+postal_code+phone+city+country | 50 | 0.000 | 0.000–0.191 | 0.259 | 0.073 | 0.296 |  |
| inference | secreto district | 50 | 0.000 | 0.000–0.206 | 0.259 | 0.036 | 0.277 |  |
| inference | secreto city | 50 | 0.000 | 0.000–0.217 | 0.277 | 0.036 | 0.296 |  |
| inference | secreto country | 50 | 0.180 | 0.000–0.405 | 0.407 | 0.036 | 0.277 |  |
| inference | secreto postal_code | 50 | 0.000 | 0.000–0.052 | 0.036 | 0.036 | 0.036 | el ataque no supera al azar: no concluyente |

**Distancia al registro más cercano (Gower, 0 = copia exacta).**

- Filas de la candidata que son copia exacta de una persona real: **0.0%**
- Mediana de la distancia candidata → original: 0.302 (percentil 5: 0.203); control → original, como referencia: 0.546
- Cuota de filas más cerca del entrenamiento que del control (submuestra de 200, mismo tamaño que el control): 0.600. Va de 0,50 (no memoriza) a 0.625 (copia todo el entrenamiento). **Índice de memorización: 0.80** (0 = no memoriza, 1 = copia todo; negativo = más lejos que el control)

## Filas por tabla

| tabla | pagila | candidata |
|---|---|---|
| actor | 200 | 200 |
| address | 1003 | 912 |
| category | 16 | 16 |
| city | 600 | 600 |
| country | 109 | 109 |
| customer | 999 | 50 |
| film | 1000 | 1000 |
| film_actor | 5462 | 5462 |
| film_category | 2367 | 2367 |
| inventory | 4581 | 4581 |
| language | 6 | 6 |
| payment | 51061 | 1684 |
| rental | 51805 | 1714 |
| staff | 1500 | 1500 |
| store | 500 | 500 |

Detalle en los CSV de esta carpeta (`e3_integridad.csv`, `e3_calidad_*.csv`, `e3_privacidad.csv`, `e3_dcr.csv`, `e3_conteos.csv`).
