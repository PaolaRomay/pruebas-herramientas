# Pruebas

Una carpeta por prueba, con el ID del plan (`A1-presidio/`, `B1-pg-anonymizer/`, `E1-sdv-anonymeter/`, ...).
Dentro: copia de `_plantilla/ficha.md` completada, los scripts usados y una carpeta `evidencia/` con capturas y logs.

Una prueba cuenta si: (1) dice con qué datos se hizo, (2) lleva hardware y versión, (3) tiene al menos un resultado concreto, (4) tiene evidencia guardada.

Estado de todas las pruebas: [ESTADO.md](ESTADO.md). Fichas por herramienta (Bloque 1) y notas de infraestructura (Neon): [_herramientas/](_herramientas/).

## Formato común de las pruebas de detección (A*)

Cada prueba A* deja `resultados/<id>_columnas.csv` (p. ej. `A9-llm-local/resultados/a9_columnas.csv`) con, al menos:

| Campo | Contenido |
|---|---|
| `prueba` | ID de la prueba (`A7`, `A9`, ...) |
| `variante` | configuración, p. ej. `manual umbral 0.0`, `gemma3-12b solo-nombres` |
| `corrida` | 1, 2, 3... si la herramienta no es determinista (LLMs); 1 si lo es |
| `tabla`, `columna` | columna de Pagila |
| `marcada` | `True`/`False`: la herramienta la considera sensible |
| `entidad` | etiqueta que le asignó (`PERSON`, `NAME_GIVEN`, `EMAIL_ADDRESS`...); vacía si no tiene |

Una fila por columna **analizada**: si la herramienta no analizó una columna, la fila no va (no cuenta como FN). Se pueden agregar columnas extra; el evaluador las ignora.

`python scripts/comparar_deteccion.py` lee todos los `pruebas/A*/resultados/*_columnas.csv`, los cruza con `data/columnas_sensibles_borrador.csv` (`--referencia` para otra lista) y escribe en `resultados_comparados/` las métricas (TP/FP/FN/TN, precisión, recall, F1, etiqueta correcta y estabilidad entre corridas), la matriz por columna y un resumen. Mismo criterio que A1: solo verdad si/no y sin las no evaluables (`--excluir`, por defecto `address.address2,staff.picture`). Los CSV anteriores de A1 y A7 se leen con adaptadores. Si una herramienta nombra las entidades de otra forma, agregar sus prefijos en `PREFIJOS_ESPERADOS`.
