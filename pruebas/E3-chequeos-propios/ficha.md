# E3 — Chequeos propios — Validar

**Quién / cuándo:** Jero, 2026-10-10 (validación) y 2026-10-11 (evaluación de D2 y D5).
**Fuente de cada dato:** D = documentación, P = prueba propia. Salvo donde dice D, todo es P.

[← Puerta de entrada](../../docs/README.md) · [Comparativa](../../docs/comparativa.md) · [Glosario](../../docs/glosario-y-metodo.md)

Es el evaluador común: no evalúa una herramienta sino la **base que produce** cualquiera de ellas (D, B, C), siempre con la misma vara. Cada prueba que genera una base la pasa por acá y copia en su propia ficha el `e3_resumen.md` que le toca.

## En pocas palabras

- Un script ([`evaluar_bd.py`](evaluar_bd.py)) que, en una sola corrida de segundos, mide tres cosas de cualquier base generada: **integridad** (fila por fila), **calidad** (SDMetrics) y **privacidad** (Anonymeter y distancia al registro más cercano, contra 200 clientes de control que la herramienta no vio).
- Encuentra lo que el catálogo de Pagila no cubre: FK de `payment` declaradas solo en 6 de 55 particiones, y la relación no declarada `store.manager_staff_id → staff`.
- Se validó con bases armadas a propósito: una rota, una copia exacta y una anonimizada. En las tres dio lo esperado.
- Ya evaluó [D2 (MOSTLY AI)](resultados/d2_auditoria/e3_resumen.md) y [D5 (Tonic Fabricate)](resultados/d5_auditoria/e3_resumen.md).

## Entorno

- Equipo: Mac M5 Pro (arm64), 16 GB de RAM, macOS 26. Python 3.11.17 (`.venv` del repo).
- Herramientas: sdv, sdmetrics, anonymeter, pandas y numpy en las versiones de `requirements.lock.txt`; el resumen de cada corrida las registra.
- Datos: Pagila (tag `pagila-v4.0.0`) en PostgreSQL 16.4 (contenedor `pagila-db`). Las restricciones se toman siempre de la base común `pagila`, que solo se lee.
- Script: `evaluar_bd.py` (esta carpeta). La integridad reutiliza `scripts/integridad.py` sin cambiarlo.

## Cómo se usa

1. `python pruebas/E3-chequeos-propios/evaluar_bd.py preparar` crea `e3_entrenamiento`: una copia de `pagila` sin los 200 clientes de control (20 %, semilla `e3`), ni sus alquileres, pagos y direcciones. **Las herramientas que aprenden de los datos se entrenan con esa base, no con `pagila`.**
2. La herramienta deja su salida en una base del contenedor. Para contar filas, conviene cargarla sin restricciones: `scripts/integridad.py`, `preparar_base(..., sin_restricciones=True)`.
3. `python pruebas/E3-chequeos-propios/evaluar_bd.py evaluar --candidata <base> --tipo sintetica|anonimizada|subconjunto [--entrenada-con e3_entrenamiento]`. El resultado queda en `resultados/<base>/`.

## Qué se midió y resultado

**Integridad** (métrica del plan: carga con restricciones y claves huérfanas):

- Todas las PK, UNIQUE, FK, NOT NULL y CHECK de Pagila, contadas fila por fila (`scripts/integridad.py`).
- Además, dos relaciones que el catálogo no cubre:
  - Las FK de `payment`, declaradas solo en 6 de sus 55 particiones. Se chequean sobre la tabla padre.
  - `store.manager_staff_id → staff`, que no tiene FK declarada.

**Calidad** (el «reporte de calidad» de D): el reporte de calidad y el diagnóstico multi-tabla de SDMetrics.

- La metadata sale del catálogo: claves y relaciones declaradas, más las de `payment` llevadas a la tabla padre.
- La relación no declarada `store → staff` queda afuera, porque cerraría un ciclo que SDV no admite.
- Se excluyen `film.fulltext` (tsvector), `film.special_features` (array), `staff.picture` (bytea) y las columnas `last_update`.
- El texto con muchos valores distintos (nombres, correos, direcciones) queda como `unknown` y no entra en Column Shapes.

**Privacidad** (métrica del plan: distancia al registro más cercano; también sirve para E1/E5):

- Anonymeter (singling out univariado y multivariado, linkability, inference con 4 secretos) sobre el registro «persona» (customer + address + city + country) frente al control.
- DCR (Gower), con dos indicadores:
  - el % de copias exactas;
  - la cuota de filas más cercanas al entrenamiento que al control, comparando conjuntos del mismo tamaño (≈ 0,50 = no memoriza).

**Validación del evaluador** (corridas sobre bases armadas a mano, en `resultados/validacion/`):

| Candidata | Qué se esperaba | Resultado |
|---|---|---|
| `e3_val_rota`: copia de pagila con 5 pagos huérfanos en `payment_p2024_03` y un `store` con gerente inexistente | `integridad.py` solo no lo ve; E3 sí | `integridad.py`: 0 violaciones en 132 restricciones. E3: 5 huérfanas en `payment.customer_id` y 1 en `store.manager_staff_id`. PostgreSQL aceptó los dos cambios sin error. |
| `e3_entrenamiento` evaluada como si fuera sintética (peor caso: publicar los datos tal cual) | calidad 1, riesgo ≈ 1, 100 % copias, índice de memorización 1 | Calidad 1,000 y diagnóstico 1,000. Anonymeter: riesgo 0,98–0,99 en los 7 ataques. DCR: 100 % copias exactas, índice de memorización 1,00. |
| `e3_val_anon`: copia de pagila con nombres, correos y teléfonos enmascarados y `payment.amount` × 3, evaluada como anonimizada | baja la calidad solo en `amount`; cae la linkability por identidad; quedan los cuasi-identificadores | `payment.amount` KS 0,325 (el resto de las columnas en 1); calidad global 0,991. Linkability 0,00; singling out univariado 0,49; inference de `postal_code` 0,44. 0 % copias exactas, pero índice de memorización 0,87. |

Tiempo de una corrida completa sobre Pagila: ~6 s, memoria máxima ~630 MB (M5 Pro, 16 GB).

## Esfuerzo

- Problemas encontrados:
  - Pagila v4 comparte direcciones entre clientes y staff/store. De las 200 direcciones de clientes de control, 109 siguen en `e3_entrenamiento` porque las usa otro registro. El control queda parcialmente expuesto en `address`; tenerlo en cuenta al leer linkability e inference.
  - SDV solo acepta PK de una columna: para `payment` (PK `payment_date + payment_id`) se usa `payment_id`, que es única en los datos.

## Hallazgos

- Limitaciones vistas en la práctica:
  - Las FK declaradas no alcanzan para verificar integridad: en Pagila, 49 de 55 particiones de `payment` no tienen FK y `store.manager_staff_id` tampoco. Una base puede «cargar sin errores» con huérfanas.
  - Sin un control separado *antes* de entrenar, Anonymeter subestima el riesgo. El evaluador lo avisa cuando no se pasa `--entrenada-con`.
  - El score global de calidad diluye una columna rota: con `payment.amount` triplicado bajó de 1,000 a 0,991. Hay que leer la tabla de peores columnas, no solo el número.
  - En una base anonimizada 1 a 1, «0 % copias exactas» no significa que no haya filtración: el índice de memorización dio 0,87, porque cada fila sigue estando muy cerca de su persona real.
  - La cuota de DCR tiene un techo menor que 1 cuando entrenamiento y control tienen distinto tamaño (acá 0,625). Por eso se informa también el índice normalizado.
- Requisitos que surgen para el sistema:
  - Inferir y verificar relaciones no declaradas (por nombre de columna y por contenido), no solo leer `pg_constraint`.
  - Separar el conjunto de control como parte del proceso, antes de cualquier entrenamiento.

## Evidencia

- [`resultados/e3_preparar.md`](resultados/e3_preparar.md) y [`resultados/e3_control.csv`](resultados/e3_control.csv): la base de entrenamiento y la lista de control.
- Validación: [base rota](resultados/validacion/e3_val_rota/e3_resumen.md), [copia exacta](resultados/validacion/e3_entrenamiento/e3_resumen.md) y [anonimizada](resultados/validacion/e3_val_anon/e3_resumen.md), con sus CSV en la misma carpeta.
- Evaluaciones de otras pruebas: [D2](resultados/d2_auditoria/e3_resumen.md) y [D5](resultados/d5_auditoria/e3_resumen.md).
- Las bases de prueba de la validación (`e3_val_rota`, `e3_val_anon`) se borraron después de evaluarlas; cómo se armaron está en la tabla «Validación del evaluador».

## Opcional

- ¿Misma semilla, mismo resultado? Se verificó corriendo E3 dos veces sobre la misma base (`d2_auditoria`, 2026-10-11):
  - **Idénticos:** la lista de control (md5 + semilla), la integridad, las propiedades de calidad y la distancia al registro más cercano.
  - El detalle de calidad salía con las filas en otro orden (mismos valores). Se corrigió en el script ordenando las relaciones; ahora sale idéntico byte a byte.
  - **Anonymeter no es determinista**, aunque singling out recibe semilla: el riesgo univariado dio 0,004 en una corrida y 0,000 en la otra, y la tasa de ataque de linkability (que no recibe semilla) dio 0,986 y 0,976. Las conclusiones no cambian, pero los riesgos hay que leerlos con su intervalo de confianza y no compararlos en el tercer decimal.
