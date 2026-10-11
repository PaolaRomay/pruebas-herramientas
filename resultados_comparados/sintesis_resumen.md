# Síntesis de bases de datos: comparación entre pruebas

Generado: 2026-10-11

Métricas mínimas de «Sintetizar» del plan: tiempo de entrenamiento y de generación, memoria máxima, claves huérfanas o duplicadas y un reporte de calidad. Se agregan la carga con todas las restricciones y la privacidad, medidas con el evaluador común E3. Cómo leer cada métrica: [docs/glosario-y-metodo.md](../docs/glosario-y-metodo.md).

## Costo

| Prueba | Herramienta | Aprende de | Entrenamiento (s) | Generación (s) | Memoria máx. (GB) | Filas cargadas | vs. Pagila |
|---|---|---|---|---|---|---|---|
| D2 | MOSTLY AI (SDK local 6.1.4) | e3_entrenamiento (Pagila sin el control) | 511.8 | 728.2 | 8.1 | 106343 | 88 % |
| D5 | Tonic Fabricate (web, versión de prueba) | solo el esquema (no ve datos) | nube (no medido) | nube (no medido) | nube (no medido) | 6070 | 5 % |

## Integridad

| Prueba | Sentencias rechazadas (carga estricta) | FK recreadas | Filas huérfanas | Filas duplicadas (PK/UNIQUE) | NOT NULL / CHECK | Tablas que quedaron vacías |
|---|---|---|---|---|---|---|
| D2 | 3 | 33/36 | 0 | 269 | 0 | - |
| D5 | 4 | 36/36 | 0 | 0 | 0 | payment |

«Filas huérfanas» incluye las 4 relaciones que el catálogo no cubre (FK de `payment` en la tabla padre y `store.manager_staff_id`).

## Calidad (SDMetrics, 0 a 1)

| Prueba | Calidad | Column Shapes | Column Pair Trends | Cardinality | Intertable Trends | Diagnóstico | Comparada contra |
|---|---|---|---|---|---|---|---|
| D2 | 0.768 | 0.79 | 0.879 | 0.705 | 0.699 | 0.969 | e3_entrenamiento |
| D5 | 0.601 | 0.625 | 0.787 | 0.427 | 0.567 | 0.935 | pagila |

![Distribuciones: Pagila real contra cada base sintética](graficos/sintesis_distribuciones.png)

## Privacidad

| Prueba | Riesgo máximo (Anonymeter) | En qué ataque | Copias exactas de personas |
|---|---|---|---|
| D2 | 0.005 | singling out (univariado) | 0.0 % |
| D5 | 0.182 | singling out (univariado) | 0.0 % |

## Notas por prueba

- **D2** ([ficha](../pruebas/D2-mostlyai/ficha.md)): Entrena por CPU (no usa MPS). La asignación de FK no-contexto de payment falló y fue al azar.
- **D5** ([ficha](../pruebas/D5-tonic-fabricate/ficha.md)): Se pidió el 20 % de las filas. Los 3210 pagos (año 2005) no entraron: payment queda vacía y eso baja la calidad (Cardinality) por razones ajenas a la forma de los datos.

Detalle por métrica en `sintesis_metricas.csv`. Se regenera con `python scripts/comparar_sintesis.py`.
