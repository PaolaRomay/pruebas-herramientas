# D6 — REaLTabFormer — Sintetizar (prueba de descarte)

**Quién / cuándo:** Jero (corrida por Claude Code a pedido de Jero), 2026-10-14.
**Fuente de cada dato:** D = documentación, P = prueba propia. Salvo donde dice D, todo es P. «Código» = leído en el código fuente de la versión instalada.

[← Estado](../ESTADO.md) · [D2 (MOSTLY AI)](../D2-mostlyai/ficha.md) · [E3](../E3-chequeos-propios/ficha.md)

**Por qué esta prueba:** el informe (Tabla 2.6) descarta REaLTabFormer porque «soporta una relación padre-hijo entre dos tablas, no esquemas relacionales arbitrarios (Solatorio y Dupriez, 2023)», y el §2.6.2 pide «confirmar con pruebas propias los límites reales de cada herramienta». Esta prueba lo mide sobre la cadena `customer → rental → payment` de Pagila.

## En pocas palabras

- **Confirma el descarte, con matices.** Con 2 niveles (`customer → rental`) funciona como promete. **Tres niveles no se pueden pedir**: los dos intentos nativos (dos claves o dos padres) fallan en la misma línea de la librería. Encadenando dos modelos a mano sí genera los tres niveles, pero **el nivel de abajo pierde la relación con el de arriba**: 1682 de 1684 pagos tienen un cliente distinto al de su alquiler.
- **Las FK que no son la del padre se tratan como números comunes.** Casi todas caen en valores que existen (de 0,1 % a 10 % sin padre); la que no se puede deducir (`payment.customer_id`) queda sin padre en el 94 % de las filas.
- **Caro y frágil en una Mac.** Entrenar 200 clientes llevó **64 min** (35 de ellos solo `rental`), y generar 50 clientes, 5 min. Con los valores por defecto se queda sin memoria o pagina a disco. Hicieron falta 3 fijaciones de versión, esquivar 4 bugs de la librería y 2 problemas de MPS y de formato de fechas.
- **Copia identidades.** Los textos salen del vocabulario de entrenamiento: **13 de 50 clientes sintéticos son nombre + apellido + email de un cliente real**. En E3, singling out univariado **0,63** e índice de memorización **0,80**. MOSTLY (D2) dio ≈ 0 de singling out.

## Entorno

- Equipo: Mac M5 Pro (`sysctl`: «Apple M5»), 16 GB de RAM, macOS 26.6.2. Docker Desktop con 8 GB asignados (contenedor `pagila-db` y otros contenedores ajenos a la prueba), así que el entrenamiento compite por memoria.
- Herramienta: `realtabformer` 0.2.4 (MIT, de worldbank/REaLTabFormer), sobre GPT-2 de Hugging Face. **Dispositivo: GPU de Apple (MPS)**: la librería cae a `mps` cuando no hay CUDA (código: `_validate_get_device`); la documentación lo marca «experimental» (D, docstring de `fit`).
- **Entorno de Python aparte** (`.venv-rtf`, `requirements-realtabformer.txt` y `.lock.txt`): torch 2.14.1, transformers 4.57.6, datasets 4.0.0, pandas 2.3.3, Python 3.11.16. Ver «Esfuerzo»: con las versiones actuales no anda.
- Datos: muestra de **200 clientes** de `e3_entrenamiento` (Pagila sin los 200 clientes de control de E3), orden por `md5('d6' || customer_id)`, con todos sus alquileres (10 461) y pagos (10 303). La muestra se eligió por tiempo de entrenamiento (ver «Esfuerzo»).
- Scripts (esta carpeta): `d6_realtabformer.py` con cuatro pasos (`exportar`, `entrenar`, `generar` y `cargar`) y `d6_tres_niveles.py` para el experimento 2. Comandos de la corrida:
  ```bash
  .venv-rtf/bin/python pruebas/D6-realtabformer/d6_realtabformer.py exportar --clientes 200
  .venv-rtf/bin/python pruebas/D6-realtabformer/d6_realtabformer.py entrenar --epocas-rental 20 --epocas-payment 20 --gradient-checkpointing
  .venv-rtf/bin/python pruebas/D6-realtabformer/d6_realtabformer.py generar --clientes 50 --lote 5
  .venv-rtf/bin/python pruebas/D6-realtabformer/d6_realtabformer.py cargar
  .venv-rtf/bin/python pruebas/D6-realtabformer/d6_tres_niveles.py --clientes 5
  .venv/bin/python pruebas/E3-chequeos-propios/evaluar_bd.py evaluar --candidata d6_auditoria --tipo sintetica --entrenada-con e3_entrenamiento --tablas customer,rental,payment
  ```

## Qué dice la documentación (D) y qué se armó

- Dos tipos de modelo: `tabular` (una tabla, GPT-2) y `relational` (un *encoder-decoder*: el encoder lee la fila del padre y el decoder genera **todas las filas hijas de ese padre como una sola secuencia**). El flujo del README: entrenar el padre como tabular, guardarlo, entrenar el hijo como relacional con `parent_realtabformer_path`, y generar primero padres y después hijos con `input_unique_ids` (D, README).
- `fit(df, in_df=None, join_on=None, ...)`: **un solo `in_df` (padre) y un solo `join_on` (str)** (código, firma de `fit` y `sample`). No hay forma de declarar una segunda FK ni un tercer nivel.
- Hay semilla (`random_state`, por defecto 1029) y parada temprana: el tabular por un «crítico» de sensibilidad (distancias al conjunto real) y el relacional por `eval_loss` con `train_size < 1` (código).
- Columnas: los números y las fechas se tokenizan **dígito a dígito** (las fechas pasan a segundos Unix); las columnas de texto se tratan como **categorías**: cada valor distinto es un token (código: `data_utils.process_data`).

Lo que se armó:

| Exp. | Pregunta | Cómo |
|---|---|---|
| 1 | ¿Funciona con 2 niveles? | `customer` (tabular, sin `customer_id`) → `rental` (relacional, `join_on=customer_id`), como el README |
| 2 | ¿3 niveles nativos? | No hay parámetro para un tercer nivel: la firma admite un solo padre (no se corre nada) |
| 3 | ¿Se puede encadenar a mano? | Un segundo relacional `rental → payment` (`join_on=rental_id`) que genera los pagos **a partir de los alquileres sintéticos** del exp. 1. `payment.customer_id` queda como una columna más |
| 4 | ¿Varios padres? | Las demás FK (`customer.address_id/store_id`, `rental.inventory_id/staff_id`, `payment.staff_id/customer_id`) entran como números comunes; se cuenta cuántas apuntan a filas que no existen |

Carga (`cargar`): `d6_auditoria` = copia de `e3_entrenamiento` sin restricciones, con `customer`, `rental` y `payment` reemplazadas por las sintéticas (las demás tablas quedan reales). Los pagos con fecha fuera de las particiones de `payment` no se pueden insertar y se cuentan aparte.

## Qué se midió y resultado

Muestra de entrenamiento: 200 clientes, 10 461 alquileres y 10 303 pagos. Se generaron **50 clientes** (ver «Esfuerzo»: generar es lento), con 1714 alquileres y 1692 pagos. Resumen completo en [`resultados/d6_resumen.md`](resultados/d6_resumen.md).

### Tiempos y memoria

La memoria es el RSS máximo del proceso (psutil, muestreo cada 0,25 s) más la memoria que reservó el driver de Metal (MPS). En una Mac la memoria es compartida, así que las dos compiten con el resto del sistema.

| Fase | Segundos | RSS máx. | MPS máx. |
|---|---|---|---|
| Entrenar `customer` (tabular, parada por el crítico) | 50 | 1,2 GB | 0,9 GB |
| **Entrenar `rental`** (relacional, batch 1, gradient checkpointing; corrió las 20 épocas, sin parada temprana) | **2113 (35 min)** | 1,6 GB | **7,0 GB** |
| Entrenar `payment` (relacional, batch 8, parada temprana en la época 13) | 1696 (28 min) | 2,0 GB | 7,0 GB |
| Generar 50 `customer` | 1 | 1,9 GB | 0,4 GB |
| **Generar `rental`** para 50 clientes (lotes de 5) | **277 (≈ 5,5 s por cliente)** | 2,7 GB | 2,0 GB |
| Generar `payment` (1714 alquileres) | 17 | 1,1 GB | 2,1 GB |

- Largo de la secuencia de hijos: **hasta 2178 tokens** por cliente en `rental` (87 alquileres × ~25 tokens), contra 23 en `payment` (un pago por alquiler). Por eso `rental` es lo caro: el costo de la atención crece con el cuadrado del largo.
- La primera generación (200 clientes, lotes de 64) llevó la Mac a 17,5 GB de swap y se cortó a los 12 min sin terminar el primer lote (`evidencia/d6_corrida.log`).

### Experimento 1: 2 niveles (`customer → rental`)

- Funciona. **0 alquileres sin cliente**: la clave la pone el script con `input_unique_ids`, así que es así por construcción.
- **Alquileres por cliente:** promedio 34,3 y mediana 23 en lo sintético, contra 52,3 y 61,5 en lo real. Genera secuencias más cortas que las reales, pero el máximo (81) es parecido.
- **Fechas:** los alquileres sintéticos van de 2023-12 a 2026-07; los reales, de 2022-02 a 2026-07. Pierde los primeros dos años. En E3 dan KS 0,46 para las fechas de `rental` y `payment`, y 0,29 para `customer.create_date`.
- **613 de 1714 alquileres (36 %) se devuelven antes de alquilarse**; en lo real, ninguno. La regla entre dos columnas de la misma fila no se aprende.
- 0 duplicados de la UNIQUE `(rental_date, inventory_id, customer_id)`.

### Experimento 2: 3 niveles nativos

Se intentó de verdad con 5 clientes, 1 época y CPU (`d6_tres_niveles.py`; `resultados/d6_exp2_tres_niveles.json`):

| Intento | Resultado |
|---|---|
| A. `join_on=["customer_id", "rental_id"]` (dos claves) | **Falla**: `AttributeError: 'DataFrame' object has no attribute 'unique'` en `realtabformer.py:923` |
| B. `in_df=[customer, rental]` (dos padres) | **Falla**: `TypeError: list indices must be integers or slices, not str` en `realtabformer.py:923` |
| C. `payment` como hija directa de `customer`, salteando `rental` | Entrena (son 2 niveles), pero `rental_id` queda como un número más: **77 de 77 pagos generados apuntan a alquileres que no existen** |

La línea 923 es `assert len(set(out_df[join_on].unique()).difference(in_df[join_on])) == 0`: el código da por hecho una sola columna de unión y un solo padre. No hay forma nativa de pedir un tercer nivel.

### Experimento 3: encadenado a mano (`customer → rental → payment`)

Un segundo modelo relacional `rental → payment` genera los pagos a partir de los alquileres sintéticos.

- **0 pagos sin alquiler** (la clave también la pone el script) y la cantidad está bien: 0,99 pagos por alquiler, contra 0,98 en lo real.
- **Pagos cuyo cliente no es el de su alquiler: 1682 de 1684.** En la muestra real: 0 de 10 303. `payment.customer_id` sale del vocabulario de ids reales: el modelo de pagos nunca ve qué cliente generó el alquiler.
  - Comparación: MOSTLY (D2) da 0, pero porque se reconstruye desde `rental` (la solución que su documentación recomienda). Acá se podría hacer lo mismo con un post-proceso: lo que muestra la prueba es que la herramienta no lo resuelve sola.
- **265 pagos (16 %) son anteriores a su alquiler.** El modelo de pagos sí ve la fecha del alquiler, pero no aprendió la regla.
- 8 pagos con fecha fuera de las particiones de `payment` no se pudieron cargar.

### Experimento 4: varios padres (FK como números comunes)

| FK | Filas | Sin padre |
|---|---|---|
| `customer.address_id → address` | 50 | 5 (10 %) |
| `customer.store_id → store` | 50 | 0 |
| `rental.inventory_id → inventory` | 1714 | 2 (0,1 %) |
| `rental.staff_id → staff` | 1714 | 0 |
| `payment.staff_id → staff` | 1684 | 0 |
| `payment.customer_id → customer` | 1684 | 1581 (94 %) |

- Una FK tratada como número casi siempre cae en un valor que existe, porque los dígitos salen del vocabulario de valores reales. **No hay ninguna garantía**: `address_id` queda huérfana en el 10 % de los clientes.
- Los 5 `address_id` huérfanos (648, 699, 704, 916 y 957) existen en Pagila: son direcciones de clientes del control, que `e3_entrenamiento` no tiene. No estaban en la muestra de entrenamiento, así que el modelo no las copió: compuso esos números dígito a dígito.

### Calidad (E3, SDMetrics contra `e3_entrenamiento`, solo `customer`, `rental` y `payment`)

- **Calidad 0,802** y **diagnóstico 0,948**. Column Shapes 0,770, Column Pair Trends 0,930, Cardinality 0,588, Intertable Trends 0,919, Relationship Validity 0,844.
- La calidad no es comparable uno a uno con D2 (0,768), porque D2 se midió sobre las 15 tablas.
- Peores columnas: las fechas (de 0,29 a 0,46). `amount` da 0,915: los montos salen del vocabulario, así que respetan el patrón «,99» de Pagila, cosa que MOSTLY no hacía.

### Privacidad (E3: Anonymeter y distancia al registro más cercano, frente a los 200 clientes de control)

| Ataque | Riesgo | IC 95 % |
|---|---|---|
| Singling out univariado | **0,628** | 0,493–0,764 |
| Singling out multivariado | 0,185 | 0,065–0,305 |
| Linkability | 0,000 | 0,000–0,191 |
| Inference (`country`) | 0,180 | 0,000–0,405 |
| Inference (`district`, `city`, `postal_code`) | 0,000 | — |

- 0 % de copias exactas del registro «persona» completo (11 atributos). Pero la distancia mediana al real más cercano es **0,302**, contra 0,546 del control, con un **índice de memorización de 0,80**. MOSTLY (D2): singling out 0,005 e índice 0,87, que ahí era un artefacto del texto inventado; acá no lo es.
- Causa: las columnas de texto son categóricas. **Cada nombre, apellido y email sintético es uno real** (100 %), y **13 de los 50 clientes** repiten la combinación nombre + apellido + email de un cliente real. En esos 13, la dirección y la fecha de alta son otras.
- Ojo al leerlo: en `d6_auditoria` las direcciones, ciudades y países son las reales de `e3_entrenamiento` (solo se sintetizaron 3 tablas). El riesgo de los atributos de ubicación no es solo de REaLTabFormer. El de nombre y email sí.
- Son 50 clientes sintéticos: los intervalos de Anonymeter son anchos.

## Esfuerzo

- Horas hasta la primera corrida completa: unas 2 h de ajustes (hechos por Claude Code) (el humo con 20 clientes) más ≈ 1 h 10 min de corrida buena (64 min de entrenamiento y 5 min de generación), sin contar las corridas cortadas.
- **Con las versiones actuales de las dependencias no anda.** `pip install realtabformer` trae pandas 3, transformers 5 y datasets 4.x, y hubo que fijar tres versiones (`requirements-realtabformer.txt`):
  1. pandas 3: falla al convertir fechas (`TypeError: cannot safely cast non-equivalent object to int64`). Log: `evidencia/d6_humo_pandas3.log`.
  2. transformers 5: `TrainingArguments.__init__() got an unexpected keyword argument 'overwrite_output_dir'` (`d6_humo_transformers5.log`).
  3. Al bajar transformers, el `datasets` nuevo pide un `huggingface_hub` incompatible (`ImportError: cannot import name 'BucketNotFoundError'`, `d6_humo_datasets.log`).
- **Bugs de la 0.2.4 con los valores por defecto** (se esquivaron desde el script, sin tocar la librería):
  4. `fit` del tabular llama a `sample(**gen_kwargs)` con `gen_kwargs=None` → `TypeError` (`d6_humo_gen_kwargs.log`). Se pasa `gen_kwargs={}`.
  5. `save()` no convierte `full_save_dir` (un `Path`) antes de pasarlo a JSON → `TypeError: Object of type PosixPath is not JSON serializable`. Se convierte a texto antes de guardar.
  6. El guardado intermedio cada 5 épocas falla con `AssertionError` porque `experiment_id` recién se asigna al terminar `fit` (`d6_corrida_save_full.log`). Se apaga con `save_full_every_epoch=0`. No aparece en un humo de 2 épocas.
- **Datos:** Pagila v4 guarda las fechas con microsegundos y la librería exige segundos enteros (divide por 1e9 y castea a entero): hubo que recortar las fechas a segundos. También supone fechas en nanosegundos (`datetime64[ns]`).
- **GPU de Apple (MPS):**
  7. La atención SDPA de torch no admite dropout al entrenar en MPS (`NotImplementedError`, `d6_humo_mps_sdpa.log`). Se fuerza la atención «eager» en el modelo relacional.
  8. Al muestrear, si el modelo genera una fecha sin dígitos, la librería hace `int('')` y se cae todo el `sample` (`ValueError`, `d6_generar_int_vacio*.log`). Se genera por lotes y se reintenta el lote que falla: falló 1 vez en 10 lotes de alquileres y 0 en los pagos.
  9. **Memoria:** la secuencia de hijos de un cliente llega a ~2100 tokens (83 alquileres × ~25 tokens). Con el batch por defecto (8) el relacional pidió más de 20 GB de MPS con solo 20 clientes y se cortó (`MPS backend out of memory`, `d6_humo_oom_batch8.log`). Con batch 1 usó 11 GB y, con Docker abierto, la Mac entró en swap: la primera corrida de 200 clientes no llegó al paso 100 en 30 minutos (≥ 14 s por paso, `d6_corrida_swap.log`) y se cortó. Con *gradient checkpointing* bajó a 3,9 GB en el humo (`d6_humo_gc.log`); en la corrida de 200 clientes usó 7 GB y unos 2,6 s por paso de optimización. Generar con lotes de 64 clientes volvió a llevar la Mac al swap: se generó con lotes de 5 y solo 50 clientes.

## Hallazgos

- Limitaciones vistas en la práctica:
  - **Un solo padre por tabla y dos niveles.** Pedirle más falla (exp. 2). Encadenar modelos funciona técnicamente, pero cada modelo solo ve a su padre directo: las relaciones que «saltan» un nivel (`payment.customer_id`) quedan rotas en el 99,9 % de las filas.
  - **Las FK que no son la del padre no se pueden declarar.** Salen como números del vocabulario: casi siempre existen, pero sin garantía (10 % huérfanas en `address_id`).
  - **El costo crece con la cantidad de hijos por padre.** Todos los hijos de un padre son una sola secuencia (más de 2000 tokens en `rental`). Con los valores por defecto (batch 8) no entra en 20 GB de GPU con 20 clientes. Con batch 1 y gradient checkpointing entra, pero entrenar 200 clientes lleva una hora y generar, unos 5,5 s por cliente. Extrapolando, la base completa (799 clientes) serían unas 4 h de entrenamiento y 1 h de generación; no se midió.
  - **No aprende reglas entre columnas**: el 36 % de las devoluciones es anterior al alquiler y el 16 % de los pagos es anterior a su alquiler.
  - **Copia valores e identidades.** El texto es categórico: no inventa nombres, los reutiliza. El 26 % de los clientes repite nombre + apellido + email de uno real.
  - **Mantenimiento:** la última versión (0.2.4) no anda con pandas 3, transformers 5 ni el `datasets` actual, y tiene bugs en caminos por defecto (`gen_kwargs=None`, `save()` con `Path`, guardado intermedio, fechas sin dígitos al muestrear). MPS (la GPU de Apple) es «experimental» y necesitó cambiar la atención.
- Lo que hizo bien: con 2 niveles la estructura sale correcta por construcción. Genera una cantidad de hijos variable y razonable. Respeta el vocabulario (montos «,99», `staff_id` y `store_id` válidos). Tiene semilla.
- **Veredicto: confirma el descarte del informe.** «Soporta una relación padre-hijo entre dos tablas» es exacto: no es solo una falta de documentación, la API no lo permite (exp. 2). Con trabajo propio se puede encadenar, pero la coherencia entre niveles se pierde (exp. 3). Además, en este equipo es lento, frágil y con riesgo de privacidad alto. Esto cierra el `[VERIFICAR]` del §2.6.2 para REaLTabFormer.
- Requisitos que surgen para el sistema:
  - El orquestador tiene que saber qué relaciones conserva cada generador. Las que no (FK no-padre, relaciones que saltan niveles) se reconstruyen o se validan después de generar, como hace D2 con `payment.customer_id`.
  - Validar reglas de negocio entre columnas (devolución ≥ alquiler, pago ≥ alquiler) después de generar.
  - Medir siempre la privacidad: un generador que trata el texto como categorías reutiliza identidades reales aunque «sintetice».
  - Estimar memoria y tiempo según los hijos por padre antes de elegir un generador secuencial.

## Evidencia

- [`resultados/d6_resumen.md`](resultados/d6_resumen.md): tiempos, memoria, filas, coherencia y FK (lo genera el script).
- `resultados/d6_tiempos.json`, `d6_coherencia.json`, `d6_distribuciones.csv`, `d6_otras_fk.csv` y `d6_exp2_tres_niveles.json`.
- [E3 sobre `d6_auditoria`](../E3-chequeos-propios/resultados/d6_auditoria/e3_resumen.md): integridad, calidad y privacidad con la vara común.
- `evidencia/d6_corrida.log` (entrenamiento de la corrida buena; la generación de ese log es la que se cortó por swap), `d6_generar.log` (generación buena), `d6_e3.log` y `d6_exp2_tres_niveles.log`. `evidencia/d6_humo*.log` y `d6_corrida_*.log`: cada error de «Esfuerzo». `evidencia/d6_humo_resumen.md`: resumen del humo con 20 clientes y 2 épocas.
- No se suben (`salidas_grandes/`): Parquet de entrada y sintéticos, modelos y checkpoints.

## Opcional

- ¿Misma semilla, mismo resultado? Hay `random_state` (se usó 1029) y el script fija también la semilla de torch, pero no se verificó repitiendo la corrida. En MPS las operaciones no son necesariamente deterministas.
