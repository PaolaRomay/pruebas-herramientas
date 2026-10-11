# Comparativa de herramientas

[← Volver a la puerta de entrada](README.md)

Una sección por función del [plan de pruebas](plan-de-pruebas.md). Cada tabla sale de los resultados que ya
están en el repositorio, medidos con las mismas métricas sobre los mismos datos. Los números de esta página son
**al 2026-10-11**. Las tablas completas y actualizadas se regeneran con un script y están enlazadas en cada
sección.

| Función | Pruebas con resultados | Tabla completa |
|---|---|---|
| A — Detectar | A1 (A7 en curso) | [`resultados_comparados/deteccion_resumen.md`](../resultados_comparados/deteccion_resumen.md) |
| B — Anonimizar | — (B1 en curso) | — |
| C — Extraer subconjuntos | — | — |
| D — Sintetizar | D2, D5 | [`resultados_comparados/sintesis_resumen.md`](../resultados_comparados/sintesis_resumen.md) |
| E — Validar privacidad | E3 (evaluador común), E5 (vía E3) | sección Privacidad de la tabla de D |
| F — Utilidad para testing | — | — |
| G — Orquestar con un LLM | — | — |

---

## A — Detectar datos sensibles

**Pregunta:** ¿qué columnas de Pagila marca como sensibles cada herramienta, comparado con la lista hecha a
mano?

Por ahora solo A1 tiene resultados. Cuando A7 (Tonic Textual) y las pruebas con LLM (A2, A6) tengan los suyos,
entran solas en la tabla completa: [`scripts/comparar_deteccion.py`](../scripts/comparar_deteccion.py) lee todos
los `pruebas/A*/resultados/*_columnas.csv`.

Mejor configuración de cada modo de A1 (Presidio), sobre 19 columnas evaluables:

| Prueba | Configuración | TP | FP | FN | Precisión | Recall | F1 |
|---|---|---|---|---|---|---|---|
| A1 | presidio-structured (las tres estrategias, cualquier umbral) | 10 | 4 | 1 | 0,71 | 0,91 | **0,80** |
| A1 | Presidio valor por valor, umbral 0 | 9 | 3 | 2 | 0,75 | 0,82 | 0,78 |
| A1 | Presidio con el nombre de la columna como contexto, umbral 0 | 8 | 3 | 3 | 0,73 | 0,73 | 0,73 |

**Lo que se escapa:**

- `staff.password` (un hash) no la detecta ninguna configuración.
- `customer.uuid` y `address.phone` (solo dígitos, lo toma por fecha) se escapan según la configuración.

**Falsos positivos estables:** `country.country`, `language.name` y `film.description`, más `film.title` con
structured. Detalle y motivos en la [ficha de A1](../pruebas/A1-presidio/ficha.md).

---

## D — Sintetizar

**Pregunta:** ¿cuánto cuesta generar una versión sintética de Pagila, se puede restaurar con sus
restricciones, se parece a la real y protege a las personas?

| | **D2 · MOSTLY AI** | **D5 · Tonic Fabricate** |
|---|---|---|
| Cómo genera | Aprende de los datos (entrenado sin el control) | Solo del esquema: no ve datos |
| Dónde corre | Local, en la Mac (CPU) | Nube de Tonic (versión de prueba) |
| Entrenamiento / generación | 8,5 min / 12,1 min | no medido (nube) |
| Memoria máxima | 8,1 GB (en la generación) | no aplica |
| Filas cargadas vs. Pagila | 88 % | 5 % (se pidió el 20 %; los pagos no entraron) |
| **¿Carga con todas las restricciones?** | **No:** 3 sentencias rechazadas por duplicados; 33 de 36 FK | **No:** 4 sentencias rechazadas (todos los pagos, por fecha); 36 de 36 FK |
| Filas huérfanas | **0** | **0** (también en los pagos rechazados) |
| Filas duplicadas (PK / únicos) | 269 (`film_actor`, `film_category`, gerentes de `store`) | 0 |
| **Calidad** (SDMetrics) | **0,768** | 0,601 |
| Diagnóstico (validez y estructura) | 0,969 | 0,935 |
| **Riesgo de privacidad** (Anonymeter, máximo) | **0,005** | 0,182 * |
| Copias exactas de personas | 0 % | 0 % |

\* A D5 no se le pasaron datos, pero consultó en internet la base pública. Su riesgo bajo es medido (0 % de copias exactas), no por construcción. El 0,18 de singling out es compatible
con coincidencias en valores comunes (nombres o países frecuentes), no con una filtración.

![Distribuciones: Pagila real contra cada base sintética](../resultados_comparados/graficos/sintesis_distribuciones.png)

**Cómo leer el gráfico:**

- **Montos:** Pagila solo tiene montos terminados en ,99. MOSTLY los corre a otros tramos; Fabricate los
  respeta bastante mejor.
- **Duración:** MOSTLY acumula películas en los extremos porque su protección recorta los valores extremos al
  borde del rango. Fabricate inventa su propia distribución.
- **Rating:** las dos herramientas lo reproducen razonablemente.
- **Alquileres por mes:** MOSTLY sigue la forma real; los de Fabricate caen todos en 2005, fuera del rango del
  esquema.

**En una línea:** MOSTLY se parece más a los datos reales y no deja huérfanas, pero rompe la unicidad de las
tablas de relación y borra las tablas de catálogo (todo `_RARE_`). Fabricate respeta la estructura pero no el
esquema real: genera el Sakila clásico y pierde todos los pagos por la fecha.

---

## E — Validar privacidad

- **E3** es el evaluador común. Su validación con bases armadas a propósito está en su
  [ficha](../pruebas/E3-chequeos-propios/ficha.md):
  - detecta huérfanas que PostgreSQL acepta sin error;
  - da riesgo ≈ 1 cuando se «publican» los datos tal cual;
  - baja la calidad justo en la columna alterada.
- **E5** (Anonymeter sobre la salida de Fabricate): son los resultados de privacidad de la columna D5 de la
  tabla anterior. Que E5 quede cubierta así es una propuesta a confirmar.
- **E1** (SDV + Anonymeter) está en curso.

---

## B, C, F, G

Sin resultados todavía. Ver el estado de cada prueba en el [plan](plan-de-pruebas.md#todas-las-pruebas-y-su-estado).
