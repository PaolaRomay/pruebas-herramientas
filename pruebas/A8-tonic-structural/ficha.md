# A8 — Tonic Structural — Detectar

**Quién / cuándo:** _(completar)_, _(fecha)_. Requiere el trial de Structural.
**Fuente de cada dato:** D = documentación, P = prueba propia. Salvo donde dice D, todo es P.

[← Estado](../ESTADO.md) · [Ficha de Tonic](../_herramientas/tonic.md) · [Neon](../_herramientas/neon.md) · [A1](../A1-presidio/ficha.md) · [A7](../A7-tonic-textual/ficha.md)

**Pregunta:** ¿encuentra bien las columnas sensibles?

> **Pendiente de decisión:** la lista de referencia `data/columnas_sensibles_borrador.csv` **todavía no está congelada**. Las métricas de esta ficha son provisorias hasta que se congele.

## Entorno

- Equipo: _(chip, RAM, macOS)_. El escaneo corre en la nube de Tonic.
- Herramienta: Tonic Structural (app.tonic.ai), trial de 14 días (D). Versión que muestra la app: _(completar)_.
- Workspace: `pagila_origen` → `pagila_destino` en Neon ([neon.md](../_herramientas/neon.md)). PostgreSQL 18.6.
- Datos: Pagila (pagila-v4.0.0), copia exacta (999 customers, 1003 addresses, 1000 films, 51061 payments).
- Se evalúan solo las **29 columnas de A1** (las mismas que A7), contra `data/columnas_sensibles_borrador.csv`. Lo que Structural marque fuera de esas 29 se anota en Hallazgos.

## Qué se midió y resultado

Variantes:

| Variante | Qué es | Corridas |
|---|---|---|
| `scan sin LLM` | Sensitivity scan por defecto | 1 |
| `scan con LLM` | Escaneo asistido por modelo de lenguaje, si la opción existe: _(completar: ¿existe? nombre en la app)_ | 3 |

Resultados en `resultados/a8_columnas.csv` (formato común; ver [pruebas/README.md](../README.md#formato-común-de-las-pruebas-de-detección-a)). Las métricas las calcula `python scripts/comparar_deteccion.py`, que las pone al lado de A1 y A7 en `resultados_comparados/deteccion_resumen.md`.

| Variante | Corridas | TP | FP | FN | TN | Precisión | Recall | F1 | Etiqueta |
|---|---|---|---|---|---|---|---|---|---|
| scan sin LLM | 1 | _(completar)_ | | | | | | | |
| scan con LLM (promedio) | 3 | _(completar)_ | | | | | | | |
| Referencia: A1 structured:highest_confidence, umbral 0.0 | 1 | 10 | 4 | 1 | 4 | 0.71 | 0.91 | 0.80 | 7/8 |
| Referencia: A7 Tonic Textual | 1 | _(cuando A7 tenga resultados de columnas)_ | | | | | | | |

**Estabilidad (scan con LLM):** columnas que cambian de marca: _(completar)_. Columnas que cambian de entidad: _(completar)_. Acuerdo: _(completar)_.

**Casos que Presidio (A1) no detectó:**

| Columna | A1 | A8 sin LLM | A8 con LLM | Confianza que muestra Structural |
|---|---|---|---|---|
| `customer.uuid` | FN en manual; structured la marca con etiquetas absurdas | _(completar)_ | | |
| `staff.password` | FN en todas las variantes | _(completar)_ | | |
| `address.phone` | sale como DATE_TIME; FN con umbral ≥ 0.4 | _(completar)_ | | |

**Señuelos (falsos positivos de A1):** `country.country`, `language.name`, `film.description` y `film.title`. En A8: _(completar)_.

## Esfuerzo

- Horas hasta la primera corrida: _(completar)_
- Problemas encontrados: _(completar)_

## Hallazgos

- Limitaciones vistas en la práctica: _(completar)_
- ¿Usa el nombre de la columna, el tipo o los valores? _(completar; A1 mostró que Presidio solo mira valores)_
- Columnas marcadas fuera de las 29 evaluadas (por ejemplo, claves `*_id`): _(completar)_
- Requisitos que surgen para el sistema: _(completar)_

## Evidencia

- `resultados/a8_columnas.csv`.
- `evidencia/`: captura del resultado del escaneo **con las confianzas** de cada columna, una por variante y corrida. _(completar nombres de archivo)_

## Opcional

- ¿Dos escaneos sin LLM dan lo mismo? _(completar)_
