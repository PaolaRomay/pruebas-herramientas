# Detección de columnas sensibles: comparación entre pruebas

Generado: 2026-10-10 21:46

## Entradas

- Lista de referencia: `data/columnas_sensibles_borrador.csv` (sha256 `02bc79fe113ed3204882a0138e2d116bb96cc910ae0ad12b12db4637afd144c5`): 13 sensibles, 8 no sensibles, 10 dudosas (las dudosas no entran en las métricas)
- Excluidas de las métricas (no evaluables): address.address2, staff.picture
- `pruebas/A1-presidio/resultados/a1_columnas.csv` (adaptador A1, sha256 `696e4fabc59b…`)

## Comparación

Orden: F1 y, a igualdad, recall (en anonimización un FN es un dato que se filtra). «Eval.» = columnas que entraron en las métricas: si una herramienta no analizó alguna, su denominador es menor. Las variantes con varias corridas muestran el promedio.

| Prueba | Variante | Corridas | Eval. | TP | FP | FN | TN | Precisión | Recall | F1 | Etiqueta |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A1 | structured:highest_confidence umbral 0.0 | 1 | 19 | 10 | 4 | 1 | 4 | 0.71 | 0.91 | 0.80 | 7/8 |
| A1 | structured:highest_confidence umbral 0.4 | 1 | 19 | 10 | 4 | 1 | 4 | 0.71 | 0.91 | 0.80 | 7/8 |
| A1 | structured:highest_confidence umbral 0.6 | 1 | 19 | 10 | 4 | 1 | 4 | 0.71 | 0.91 | 0.80 | 7/8 |
| A1 | structured:mixed umbral 0.0 | 1 | 19 | 10 | 4 | 1 | 4 | 0.71 | 0.91 | 0.80 | 7/8 |
| A1 | structured:mixed umbral 0.4 | 1 | 19 | 10 | 4 | 1 | 4 | 0.71 | 0.91 | 0.80 | 7/8 |
| A1 | structured:mixed umbral 0.6 | 1 | 19 | 10 | 4 | 1 | 4 | 0.71 | 0.91 | 0.80 | 7/8 |
| A1 | structured:most_common umbral 0.0 | 1 | 19 | 10 | 4 | 1 | 4 | 0.71 | 0.91 | 0.80 | 6/8 |
| A1 | structured:most_common umbral 0.4 | 1 | 19 | 10 | 4 | 1 | 4 | 0.71 | 0.91 | 0.80 | 6/8 |
| A1 | structured:most_common umbral 0.6 | 1 | 19 | 10 | 4 | 1 | 4 | 0.71 | 0.91 | 0.80 | 7/8 |
| A1 | manual umbral 0.0 | 1 | 19 | 9 | 3 | 2 | 5 | 0.75 | 0.82 | 0.78 | 7/8 |
| A1 | manual umbral 0.4 | 1 | 19 | 8 | 3 | 3 | 5 | 0.73 | 0.73 | 0.73 | 7/8 |
| A1 | manual_contexto umbral 0.0 | 1 | 19 | 8 | 3 | 3 | 5 | 0.73 | 0.73 | 0.73 | 6/8 |
| A1 | manual umbral 0.6 | 1 | 19 | 7 | 3 | 4 | 5 | 0.70 | 0.64 | 0.67 | 7/8 |
| A1 | manual_contexto umbral 0.4 | 1 | 19 | 7 | 3 | 4 | 5 | 0.70 | 0.64 | 0.67 | 6/8 |
| A1 | manual_contexto umbral 0.6 | 1 | 19 | 6 | 3 | 5 | 5 | 0.67 | 0.55 | 0.60 | 6/8 |

## Columnas sensibles que se escaparon

Por prueba: configuraciones (variante × corrida) que no la marcaron / que la analizaron.

- Ninguna herramienta la detectó: staff.password
- staff.password: A1 15/15
- customer.uuid: A1 6/15
- address.phone: A1 4/15
- address.address: A1 3/15
- staff.username: A1 2/15

## Falsos positivos compartidos

No sensibles marcadas por más de una prueba (herramienta distinta).

- ninguno

FP de una sola prueba: country.country (A1), film.description (A1), film.title (A1), language.name (A1)

Detalle en `deteccion_metricas.csv` (una fila por prueba + variante + corrida, con FN y FP) y `deteccion_por_columna.csv` (matriz columna × configuración).
