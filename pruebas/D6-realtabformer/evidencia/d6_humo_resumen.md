# D6: REaLTabFormer sobre customer -> rental -> payment

Corrida: 2026-10-14 19:51

## Entorno

- Equipo: arm64, macOS 26.6.2. Dispositivo del modelo: mps:0
- realtabformer 0.2.4, torch 2.14.1, transformers 4.57.6, pandas 2.3.3, Python 3.11.16
- Muestra: None clientes de `None` (semilla `None`) con sus alquileres y pagos: None
- Épocas máx.: customer 2, rental None, payment None; batch 8 (customer, payment) y None (rental); semilla del modelo 1029
- Largo máximo de la secuencia hija (tokens): rental 2078, payment 23

## Tiempos y memoria

| fase | segundos | memoria_max_mb | mps_max_mb |
|---|---|---|---|
| exportar |  |  |  |
| entrenar customer (tabular) | 7.1 | 1035 | 876 |
| entrenar rental (relacional, padre customer) | 240.7 | 1448 | 11132 |
| entrenar payment (relacional, padre rental) | 148.5 | 670 | 11132 |
| generar customer | 1.3 | 139 | 8028 |
| generar rental | 29.5 | 426 | 8028 |
| generar payment | 15.1 | 299 | 8036 |
| cargar y medir | 0.9 | 285 | 0 |

## Filas

| tabla | muestra real | sintética |
|---|---|---|
| customer | 20 | 20 |
| rental | 1109 | 275 |
| payment | 1094 | 257 |

| medida | datos | min | mediana | promedio | max | ceros |
|---|---|---|---|---|---|---|
| alquileres por cliente | real | 2 | 70.5 | 55.45 | 83 | 0 |
| alquileres por cliente | sintético | 1 | 12.0 | 13.75 | 39 | 0 |
| pagos por alquiler | real | 0 | 1.0 | 0.99 | 1 | 15 |
| pagos por alquiler | sintético | 0 | 1.0 | 0.93 | 1 | 18 |

## Coherencia de la cadena (exp. 3)

- Alquileres sin cliente: 0 · pagos sin alquiler: 0 (las claves de la relación modelada las pone el script, así que tienen que dar 0)
- **Pagos cuyo cliente no es el de su alquiler: 254 de 254** (muestra real: 0 de 1094)
- Pagos anteriores a su alquiler: 141
- Alquileres devueltos antes de alquilarse: 181 (muestra real: 0)
- Pagos fuera de las particiones de payment (no se pudieron cargar): 3
- Duplicados de la UNIQUE (rental_date, inventory_id, customer_id): 0

## FK que no se pueden declarar (exp. 4)

| fk | filas | sin_padre | pct |
|---|---|---|---|
| customer.address_id -> address | 20 | 4 | 20.0 |
| customer.store_id -> store | 20 | 0 | 0.0 |
| rental.inventory_id -> inventory | 275 | 10 | 3.6 |
| rental.staff_id -> staff | 275 | 0 | 0.0 |
| payment.staff_id -> staff | 254 | 0 | 0.0 |
| payment.customer_id -> customer | 254 | 254 | 100.0 |

## Valores copiados del entrenamiento (% de filas sintéticas)

| columna | pct |
|---|---|
| first_name | 100.0 |
| last_name | 100.0 |
| email | 100.0 |
| persona_completa (nombre+apellido+email) | 0.0 |

Calidad y privacidad con la vara común: `pruebas/E3-chequeos-propios/resultados/d6_auditoria/`.
