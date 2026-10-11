# Glosario y método común

[← Volver a la puerta de entrada](README.md)

Qué significan los términos que aparecen en las fichas y cómo se mide igual en todas las pruebas.

## Los datos

### Pagila

Base de ejemplo de PostgreSQL que simula un videoclub: clientes, películas, alquileres y pagos. Se usa la
versión **pagila-v4.0.0**, fijada por commit para que todas las pruebas usen exactamente los mismos datos.

- **15 tablas** y 121 209 filas en total. `payment` cuenta como una sola tabla aunque está **particionada**
  en 55 tablas físicas, una por mes de 2022-01 a 2026-07.
- **Personas y transacciones:** `customer` (999), `rental` (51 805), `payment` (51 061), `staff` (1500),
  `store` (500).
- **Ubicación:** `address` (1003), `city` (600), `country` (109).
- **Catálogo:** `film` (1000), `actor` (200), `category` (16), `language` (6), `inventory` (4581), y las
  tablas de relación `film_actor` (5462) y `film_category` (2367).
- Corre en Docker (contenedor `pagila-db`). Nadie la modifica: cada prueba trabaja sobre **copias**.

Dos particularidades del esquema que aparecen en varias pruebas:

- Solo 6 de las 55 particiones de `payment` declaran sus FK. Una base puede tener pagos huérfanos y PostgreSQL
  no lo impide.
- `store.manager_staff_id` apunta a `staff`, pero **no tiene FK declarada** (solo un índice único). Junto con
  `staff.store_id → store` forma un ciclo que las herramientas que leen el catálogo no ven.

### Lista de referencia (columnas sensibles)

[`data/columnas_sensibles_borrador.csv`](../data/columnas_sensibles_borrador.csv): 31 columnas de Pagila
marcadas a mano como `si` (13), `no` (8) o `dudoso` (10).

- Las `dudoso` no entran en las métricas.
- Incluye **señuelos** (`film.title`, `film.description`) para medir falsos positivos.
- Es la «verdad» contra la que se miden las pruebas A. **Todavía es borrador.**

### Conjunto de control

200 clientes de Pagila (20 %, siempre los mismos, elegidos con una semilla) que **ninguna herramienta debe
ver**. Las herramientas que aprenden de los datos se entrenan con `e3_entrenamiento`, una copia de Pagila sin
esos clientes. Después se mide si un atacante averigua más sobre las personas del entrenamiento que sobre las
del control. Si la diferencia es grande, la herramienta filtra información de personas reales.

## Cómo se mide

### Detección (A): TP, FP, FN, precisión, recall, F1

Cada columna se compara contra la lista de referencia:

- **TP**: sensible y la herramienta la marcó.
- **FP**: no sensible y la marcó (falsa alarma).
- **FN**: sensible y **no** la marcó, es decir, un dato que se filtraría.
- **Precisión** = TP / (TP + FP): de lo que marcó, cuánto era sensible.
- **Recall** = TP / (TP + FN): de lo sensible, cuánto encontró. En anonimización es la métrica que más
  importa.
- **F1**: el promedio armónico de las dos.

Con 19 columnas evaluables, **una columna más o menos mueve unos 5 puntos el F1**: las diferencias chicas no
son concluyentes.

### Integridad: carga estricta y carga para auditar

Toda base generada se carga **dos veces** en bases nuevas:

1. **Estricta:** con todas las restricciones de Pagila, como si se restaurara en un ambiente real. Mide si
   «carga tal cual». Un `COPY` o un `INSERT` de muchas filas es **todo o nada**: una sola fila mala descarta
   la sentencia entera.
2. **Para auditar:** sin restricciones. Entra todo, y después se cuenta **fila por fila** qué viola cada
   restricción:
   - **Huérfana**: fila hija cuya FK apunta a un padre que no existe.
   - **Duplicada**: fila que repite una PK o un valor único.
   - **NOT NULL / CHECK**: valores vacíos u obligaciones de dominio que no se cumplen.

Lo hace [`scripts/integridad.py`](../scripts/integridad.py), y E3 le agrega las dos relaciones que el
catálogo no cubre.

### Calidad: SDMetrics

Compara la base generada contra la real y da puntajes de 0 a 1 (1 = indistinguible en esa propiedad):

- **Column Shapes:** ¿cada columna tiene la misma distribución? Usa KS para números y fechas, y TV para
  categorías.
- **Column Pair Trends:** ¿se conservan las correlaciones entre columnas?
- **Cardinality:** ¿cada padre tiene una cantidad parecida de hijos? Por ejemplo, alquileres por cliente.
- **Intertable Trends:** ¿se conservan las correlaciones entre tablas relacionadas?
- **Diagnóstico** (Data Validity, Data Structure, Relationship Validity): ¿los valores están en rango y las
  claves bien formadas?

El texto con muchos valores distintos (nombres, correos) no entra en Column Shapes: SDMetrics no compara
texto libre.

### Privacidad: Anonymeter y distancia al registro más cercano

- **Anonymeter** simula tres ataques y compara cuánto aciertan contra las personas del entrenamiento y contra
  las del control:
  - **singling out**: aislar a una persona por una combinación de atributos;
  - **linkability**: unir dos fuentes parciales de una misma persona;
  - **inference**: deducir un dato secreto a partir de otros.

  **Riesgo** = cuánto mejor le va al ataque contra el entrenamiento que contra el control (0 = nada,
  1 = total). Si el ataque no supera a uno que adivina al azar, el resultado no es concluyente.
- **Copias exactas:** % de filas generadas idénticas a una persona real.
- **Distancia al registro más cercano (DCR):** qué tan cerca está cada fila generada de la persona real más
  parecida. Se calcula con la distancia de Gower: 0 = copia, 1 = nada en común.
- **Índice de memorización:** ¿las filas generadas están más cerca de las personas del entrenamiento que de
  las del control? 0 = no memoriza; 1 = copia lo que vio. Con texto generado carácter por carácter el índice
  pierde poder de discriminación (ver la ficha de D2).

### E3: el evaluador común

[E3](../pruebas/E3-chequeos-propios/ficha.md) no prueba una herramienta: es **la vara con la que se miden las
bases generadas por las demás**. Junta integridad, calidad y privacidad en una sola corrida, y se validó con
bases armadas a propósito (una rota, una copia exacta y una anonimizada).

## Otros términos

- **D / P:** origen de cada dato de una ficha. **D** = documentación de la herramienta; **P** = prueba propia.
- **FK de contexto / no-contexto** (MOSTLY AI): en una tabla hija, la FK de contexto es la que el generador
  usa para conservar las correlaciones con el padre. Solo puede haber una por tabla; las demás (no-contexto)
  solo garantizan que la clave exista.
- **Value protection** (MOSTLY AI): reemplaza categorías raras y recorta valores extremos para proteger la
  privacidad.
- **Muestreo determinista:** las muestras se eligen ordenando por un hash con semilla. Misma semilla, mismas
  filas, en cualquier máquina.
- **`salidas_grandes/`:** carpeta de cada prueba con salidas pesadas (bases generadas, modelos, reportes HTML).
  **No se sube al repositorio**; los datos que importan se copian a la ficha o a `resultados/`.
