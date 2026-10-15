# D6: REaLTabFormer sobre customer -> rental -> payment

Corrida: 2026-10-14 22:22

## Entorno

- Equipo: arm64, macOS 26.6.2. Dispositivo del modelo: mps (memoria MPS ocupada al entrenar; ver tabla)
- realtabformer 0.2.4, torch 2.14.1, transformers 4.57.6, pandas 2.3.3, Python 3.11.16
- Muestra: 200 clientes de `e3_entrenamiento` (semilla `d6`) con sus alquileres y pagos: {'customer': 200, 'rental': 10461, 'payment': 10303}
- Épocas máx.: customer 100, rental 20, payment 20; batch 8 (customer, payment) y 1 (rental); gradient checkpointing en rental: sí; semilla del modelo 1029
- Largo máximo de la secuencia hija (tokens): rental 2178, payment 23

## Tiempos y memoria

| fase | segundos | memoria_max_mb | mps_max_mb |
|---|---|---|---|
| exportar | 0.2 | 308 | 0 |
| entrenar customer (tabular) | 50.3 | 1188 | 901 |
| entrenar rental (relacional, padre customer) | 2113.2 | 1583 | 7001 |
| entrenar payment (relacional, padre rental) | 1696.3 | 2004 | 6992 |
| cargar modelos | 3.6 | 1890 | 0 |
| generar customer | 0.9 | 1890 | 443 |
| generar rental | 276.5 | 2732 | 2044 |
| generar payment | 17.0 | 1096 | 2068 |
| cargar y medir | 1.0 | 290 | 0 |

## Filas

| tabla | muestra real | sintética |
|---|---|---|
| customer | 200 | 50 |
| rental | 10461 | 1714 |
| payment | 10303 | 1692 |

| medida | datos | min | mediana | promedio | max | ceros |
|---|---|---|---|---|---|---|
| alquileres por cliente | real | 0 | 61.5 | 52.3 | 87 | 1 |
| alquileres por cliente | sintético | 1 | 23.0 | 34.28 | 81 | 0 |
| pagos por alquiler | real | 0 | 1.0 | 0.98 | 1 | 158 |
| pagos por alquiler | sintético | 0 | 1.0 | 0.99 | 1 | 22 |

## Coherencia de la cadena (exp. 3)

- Alquileres sin cliente: 0 · pagos sin alquiler: 0 (las claves de la relación modelada las pone el script, así que tienen que dar 0)
- **Pagos cuyo cliente no es el de su alquiler: 1682 de 1684** (muestra real: 0 de 10303)
- Pagos anteriores a su alquiler: 265
- Alquileres devueltos antes de alquilarse: 613 (muestra real: 0)
- Pagos fuera de las particiones de payment (no se pudieron cargar): 8
- Duplicados de la UNIQUE (rental_date, inventory_id, customer_id): 0

## FK que no se pueden declarar (exp. 4)

| fk | filas | sin_padre | pct |
|---|---|---|---|
| customer.address_id -> address | 50 | 5 | 10.0 |
| customer.store_id -> store | 50 | 0 | 0.0 |
| rental.inventory_id -> inventory | 1714 | 2 | 0.1 |
| rental.staff_id -> staff | 1714 | 0 | 0.0 |
| payment.staff_id -> staff | 1684 | 0 | 0.0 |
| payment.customer_id -> customer | 1684 | 1581 | 93.9 |

## Valores copiados del entrenamiento (% de filas sintéticas)

| columna | pct |
|---|---|
| first_name | 100.0 |
| last_name | 100.0 |
| email | 100.0 |
| persona_completa (nombre+apellido+email) | 26.0 |

Calidad y privacidad con la vara común: `pruebas/E3-chequeos-propios/resultados/d6_auditoria/`.
