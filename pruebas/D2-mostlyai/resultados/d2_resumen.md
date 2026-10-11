# D2: MOSTLY AI (SDK local) sobre Pagila

Corrida: 2026-10-11 00:18

## Entorno

- Equipo: arm64, macOS 26.6.2. Entrenamiento en CPU (el motor tabular no usa MPS).
- MOSTLY: mostlyai 6.1.4, mostlyai-engine 2.7.0, mostlyai-qa 1.10.8, torch 2.13.0, Python 3.12.0 (`/Users/jerojacques/Desktop/Tesis/.venv/bin/python`)
- Datos de entrenamiento: `e3_entrenamiento` (Pagila sin los 200 clientes de control de E3)
- Tope de entrenamiento: 10.0 min por tabla; el resto, valores por defecto
- store.manager_staff_id como FK no-contexto: sí

## Tiempos y memoria

| fase | segundos | memoria_max_mb |
|---|---|---|
| exportar (repo) | 2.1 | 174 |
| arranque (MOSTLY) | 5.9 | 601 |
| entrenamiento (MOSTLY) | 511.8 | 3109 |
| generacion (MOSTLY) | 728.2 | 8275 |
| post-proceso de claves y .sql (repo) | 0.6 | 205 |
| carga estricta + auditoría (repo) | 3.4 | 208 |

Segundos por tabla y etapa, según los registros de MOSTLY (`d2_tiempos_por_tabla.csv`):

| trabajo | tabla | leer | analizar | codificar | entrenar | reporte_modelo | generar | reporte_datos | finalizar | entregar |
|---|---|---|---|---|---|---|---|---|---|---|
| entrenamiento | country | 0.0 | 5.8 | 5.3 | 2.5 | 3.6 |  |  |  |  |
| entrenamiento | city | 0.0 | 2.8 | 0.2 | 12.1 | 0.2 |  |  |  |  |
| entrenamiento | address | 0.0 | 8.0 | 2.5 | 9.4 | 6.4 |  |  |  |  |
| entrenamiento | language | 0.0 | 0.0 | 0.0 | 0.8 | 0.0 |  |  |  |  |
| entrenamiento | category | 0.0 | 0.0 | 2.7 | 0.4 | 0.0 |  |  |  |  |
| entrenamiento | actor | 0.0 | 0.1 | 0.0 | 6.1 | 3.8 |  |  |  |  |
| entrenamiento | film | 0.1 | 3.3 | 0.1 | 40.4 | 6.9 |  |  |  |  |
| entrenamiento | film_actor | 0.1 | 2.8 | 3.6 | 9.9 | 2.9 |  |  |  |  |
| entrenamiento | film_category | 0.1 | 4.9 | 2.9 | 8.5 | 3.2 |  |  |  |  |
| entrenamiento | store | 0.0 | 0.0 | 0.0 | 6.4 | 0.0 |  |  |  |  |
| entrenamiento | staff | 0.0 | 0.1 | 0.8 | 38.9 | 8.5 |  |  |  |  |
| entrenamiento | customer | 0.1 | 4.5 | 3.7 | 22.6 | 4.6 |  |  |  |  |
| entrenamiento | inventory | 0.2 | 2.5 | 0.7 | 9.3 | 3.6 |  |  |  |  |
| entrenamiento | rental | 0.3 | 4.9 | 2.7 | 179.2 | 8.0 |  |  |  |  |
| entrenamiento | payment | 0.2 | 2.6 | 4.7 | 9.1 | 4.6 |  |  |  |  |
| entrenamiento | (global) |  |  |  |  |  |  |  | 13.3 |  |
| generacion | country |  |  |  |  |  | 0.0 | 1.5 |  |  |
| generacion | city |  |  |  |  |  | 0.2 | 0.0 |  |  |
| generacion | address |  |  |  |  |  | 0.2 | 3.2 |  |  |
| generacion | language |  |  |  |  |  | 0.0 | 0.0 |  |  |
| generacion | category |  |  |  |  |  | 0.0 | 0.0 |  |  |
| generacion | actor |  |  |  |  |  | 0.0 | 4.8 |  |  |
| generacion | film |  |  |  |  |  | 0.2 | 1.5 |  |  |
| generacion | film_actor |  |  |  |  |  | 0.1 | 1.2 |  |  |
| generacion | film_category |  |  |  |  |  | 0.1 | 1.2 |  |  |
| generacion | store |  |  |  |  |  | 0.0 | 0.0 |  |  |
| generacion | staff |  |  |  |  |  | 0.5 | 1.6 |  |  |
| generacion | customer |  |  |  |  |  | 0.4 | 1.8 |  |  |
| generacion | inventory |  |  |  |  |  | 0.1 | 1.2 |  |  |
| generacion | rental |  |  |  |  |  | 2.2 | 1.7 |  |  |
| generacion | payment |  |  |  |  |  | 559.5 | 4.7 |  |  |
| generacion | (global) |  |  |  |  |  |  |  | 6.3 | 0.0 |

## Métricas propias de MOSTLY (reporte de modelo, contra su holdout interno)

Accuracy global: **0.8696678818181819**

| tabla | accuracy | accuracy_max_holdout | dcr_share | discriminador_auc | ims_entrenamiento |
|---|---|---|---|---|---|
| country | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 |
| address | 0.918 | 0.958 | 0.000 | 1.000 | 0.000 |
| actor | 0.896 | 0.936 | 1.000 | 1.000 | 0.000 |
| film | 0.831 | 0.863 | 0.602 | 1.000 | 0.000 |
| film_actor | 0.909 | 0.905 | 0.500 | 0.481 | 1.000 |
| film_category | 0.958 | 0.955 | 0.500 | 0.516 | 1.000 |
| staff | 0.870 | 0.935 | 0.918 | 0.999 | 0.000 |
| customer | 0.896 | 0.931 | 1.000 | 1.000 | 0.000 |
| inventory | 0.908 | 0.917 | 0.500 | 0.512 | 1.000 |
| rental | 0.721 | 0.809 | 0.622 | 0.748 | 0.000 |
| payment | 0.660 | 0.908 | 0.453 | 0.827 | 0.000 |

## Filas

| tabla | pagila | entrenamiento | sintetica | cargadas_auditoria | cargadas_estricta |
|---|---|---|---|---|---|
| country | 109 | 109 | 109 | 109 | 109 |
| city | 600 | 600 | 795 | 795 | 795 |
| address | 1003 | 912 | 795 | 795 | 795 |
| language | 6 | 6 | 6 | 6 | 6 |
| category | 16 | 16 | 16 | 16 | 16 |
| actor | 200 | 200 | 200 | 200 | 200 |
| film | 1000 | 1000 | 1000 | 1000 | 1000 |
| film_actor | 5462 | 5462 | 5461 | 5461 | 0 |
| film_category | 2367 | 2367 | 2360 | 2360 | 0 |
| store | 500 | 500 | 500 | 500 | 0 |
| staff | 1500 | 1500 | 1388 | 1388 | 1388 |
| customer | 999 | 799 | 640 | 640 | 640 |
| inventory | 4581 | 4581 | 4619 | 4619 | 4619 |
| rental | 51805 | 41663 | 44227 | 44227 | 44227 |
| payment | 51061 | 41064 | 44227 | 44227 | 44227 |

## Integridad

- Carga estricta: **3** sentencias rechazadas; FK que se pudieron volver a crear: **33 de 36**

| tipo | tabla | sentencias |
|---|---|---|
| PK/UNIQUE (duplicado) | film_actor | 1 |
| PK/UNIQUE (duplicado) | film_category | 1 |
| PK/UNIQUE (duplicado) | store | 1 |

- FK que falla: `customer.customer_store_id_fkey`: ERROR:  insert or update on table "customer" violates foreign key constraint "customer_store_id_fkey"
- FK que falla: `inventory.inventory_store_id_fkey`: ERROR:  insert or update on table "inventory" violates foreign key constraint "inventory_store_id_fkey"
- FK que falla: `staff.staff_store_id_fkey`: ERROR:  insert or update on table "staff" violates foreign key constraint "staff_store_id_fkey"

Violaciones fila por fila (carga sin restricciones, `scripts/integridad.py`):

| tipo | restricciones | violadas | filas | sin_comprobar |
|---|---|---|---|---|
| FK | 36 | 0 | 0 | 0 |
| PK | 15 | 2 | 184 | 0 |
| UNIQUE (índice) | 5 | 1 | 85 | 0 |
| NOT NULL | 75 | 0 | 0 | 0 |
| CHECK (dominio) | 1 | 0 | 0 | 0 |

| tipo | tabla | nombre | columnas | violaciones | ejemplos |
|---|---|---|---|---|---|
| PK | film_actor | film_actor_pkey | actor_id, film_id | 70 | (68,352); (4,282); (6,168) |
| PK | film_category | film_category_pkey | film_id, category_id | 114 | (109,4); (697,9); (27,5) |
| UNIQUE (índice) | store | idx_unq_manager_staff_id | manager_staff_id | 85 | (1366); (604); (1173) |

- Claves que MOSTLY generó sin fila padre (quedaron en -1): ninguna
- Pagos cuyo cliente no es el de su alquiler: 0 (customer_id se reconstruye desde rental, así que tiene que dar 0)
- Tiendas cuyo gerente trabaja en esa tienda: 0 (en Pagila real: 1 de 500)
- Rango de fechas: pagos 2022-01-30 a 2026-07-13, alquileres 2022-02-14 a 2026-07-27 (particiones de payment: 2022-01 a 2026-07)

Calidad y privacidad con la vara común: `pruebas/E3-chequeos-propios/resultados/d2_auditoria/`. Reportes HTML de MOSTLY en `salidas_grandes/reportes_mostly/` (no se suben: ~170 MB).
