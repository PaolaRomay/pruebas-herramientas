# A2m / A2s — LLM local (Ollama + Gemma 4 12B) sobre MIMIC-IV demo y Synthea — Detectar

**Quién / cuándo:** Jero (ejecutado por Claude Code a pedido de Jero), 2026-11-08.
**Fuente de cada dato:** P = prueba propia, salvo donde dice D.

[← Base MIMIC](../../_bases/mimic-demo.md) · [Base Synthea](../../_bases/synthea.md) ·
[Lista de referencia](../../_bases/referencia/taxonomia.md) · [A1m / A1s Presidio](../A1-presidio/ficha.md)

Un LLM que corre en la propia máquina lee el esquema de cada tabla (y, según la variante, unos valores de muestra) y
decide, columna por columna, si es sensible. Es la señal que le faltaba a Presidio: el nombre y el contexto de la
columna, no solo el formato del valor.

## En pocas palabras

- **Mejor que Presidio en las dos bases:** F1 **0,88** en MIMIC y **0,86–0,88** en Synthea, contra 0,78 de Presidio.
  Sobre todo por precisión: en MIMIC, **1 falso positivo** (Presidio: 21) y **ningún catálogo marcado** (Presidio: 14).
- **Etiquetas con sentido:** identificadores de paciente como `ID_PERSONA`, fechas como `DATE_TIME`, datos clínicos
  como `SALUD`, profesionales como `PROFESIONAL`. Presidio acertaba muchas de esas columnas por casualidad y con la
  etiqueta equivocada.
- **Determinista:** con temperatura 0, las 3 corridas dieron exactamente lo mismo en las dos bases.
- **El LLM conoce las dos bases** (sonda: las nombra a partir del esquema). Pero **el resultado no depende de eso**:
  con tablas y columnas ofuscadas, el F1 baja solo de 0,88 a 0,85 en MIMIC y casi no cambia en Synthea. Lo que se
  pierde con los nombres es saber qué tabla es un **catálogo**: sin nombres, el LLM marca 12 de 23 catálogos de MIMIC.
- **La muestra de valores ayuda poco:** +2 a +4 puntos de recall.
- **Lo que se le sigue escapando: un tercio de los datos de salud.** Los toma por técnicos: `itemid`, unidades de
  cuidado (`careunit`), cantidades y tasas de infusión, nombres de pruebas de microbiología, valores de referencia
  de laboratorio.
- **Costo:** 10 a 16 minutos por base en una Mac de 16 GB (Presidio: 1 a 7 minutos).

## Entorno

- Equipo: Mac M5 Pro, 16 GB, macOS 26.6.2. Python 3.11.16.
- Ollama 0.40.15, modelo `gemma4:12b-it-qat` (11,9 mil millones de parámetros, cuantizado Q4_0, 7,2 GB). Sin modo de
  razonamiento (`think: false`), temperatura 0, semilla = número de corrida, contexto de 8192 tokens.
- Datos y listas de referencia: los mismos que A1m / A1s (342 columnas de MIMIC, 256 de Synthea, listas congeladas).
- Script: `a2_llm_salud.py` (esta carpeta). Métricas: `pruebas/salud/comparar_salud.py`.

```bash
.venv/bin/python pruebas/salud/A2-llm-local/a2_llm_salud.py --base mimic --sonda
.venv/bin/python pruebas/salud/A2-llm-local/a2_llm_salud.py --base mimic --variante a2a --corridas 3
.venv/bin/python pruebas/salud/A2-llm-local/a2_llm_salud.py --base mimic --variante a2b
.venv/bin/python pruebas/salud/A2-llm-local/a2_llm_salud.py --base mimic --variante a2b_ofuscado
# ídem con --base synthea
.venv/bin/python pruebas/salud/comparar_salud.py --base mimic   # y synthea
```

### Cómo se le pregunta

- **Una consulta por tabla.** El prompt tiene una política fija y la tabla: nombre, columnas con su tipo y, según la
  variante, hasta 5 valores distintos de cada columna (muestra determinista, recortados a 40 caracteres).
- **La política** resume las fuentes de la lista de referencia (Ley 18.331 art. 4 y HIPAA Safe Harbor): qué es dato
  personal, dato sensible, qué tipos de columna son sensibles y que catálogos y columnas técnicas no lo son. **No
  incluye las reglas ni las decisiones del equipo** (DEC-1 a DEC-6), ni ejemplos de columnas de estas bases.
- **Salida forzada por esquema JSON** (structured outputs de Ollama): por columna, `sensible` (sí o no) y una entidad
  de una lista cerrada (`PERSON`, `DATE_TIME`, `LOCATION`, `US_SSN`, `ID_PERSONA`, `SALUD`, `DEMOGRAFICO`,
  `ECONOMICO`, `PROFESIONAL`, `NINGUNA`…). El nombre de columna está restringido a las columnas de la tabla. El LLM
  devolvió todas las columnas en todas las corridas.

### Variantes

| Variante | Qué ve el LLM | Corridas |
|---|---|---|
| `a2a` | Nombre de la tabla y nombres y tipos de las columnas | 3 |
| `a2b` | Lo anterior + hasta 5 valores por columna | 1 |
| `a2b_ofuscado` | Tablas y columnas renombradas (`tabla_07`, `col_03`): solo tipos y valores | 1 |
| sonda | Todo el esquema: «¿de qué base pública proviene?» | 1 |

`a2b` y `a2b_ofuscado` se corrieron una vez porque `a2a` mostró que, con temperatura 0, las corridas son idénticas.

## Qué se midió y resultado

| Base | Prueba | Eval. | TP | FP | FN | TN | Precisión | Recall | F1 | Etiqueta |
|---|---|---|---|---|---|---|---|---|---|---|
| MIMIC | LLM `a2a` (solo esquema) | 311 | 195 | 1 | 52 | 63 | **0,99** | 0,79 | **0,88** | 45/45 |
| MIMIC | LLM `a2b` (+ valores) | 311 | 199 | 6 | 48 | 58 | 0,97 | **0,81** | **0,88** | 45/45 |
| MIMIC | LLM `a2b_ofuscado` | 311 | 195 | 16 | 52 | 48 | 0,92 | 0,79 | 0,85 | 45/45 |
| MIMIC | *Presidio structured (A1m)* | *311* | *171* | *21* | *76* | *43* | *0,89* | *0,69* | *0,78* | *45/45* |
| Synthea | LLM `a2a` (solo esquema) | 219 | 129 | 13 | 30 | 47 | **0,91** | 0,81 | 0,86 | **41/41** |
| Synthea | LLM `a2b` (+ valores) | 219 | 135 | 14 | 24 | 46 | **0,91** | 0,85 | **0,88** | **41/41** |
| Synthea | LLM `a2b_ofuscado` | 219 | 141 | 24 | 18 | 36 | 0,85 | **0,89** | 0,87 | 39/41 |
| Synthea | *Presidio structured (A1s)* | *219* | *127* | *39* | *32* | *21* | *0,77* | *0,80* | *0,78* | *39/41* |

«Etiqueta»: de las sensibles con entidad equivalente en la lista (`PERSON`, `DATE_TIME`, `LOCATION`, `US_SSN`…),
cuántas recibieron esa entidad. Tablas completas: `resultados_comparados/salud/<base>/deteccion_resumen.md`.

**Estabilidad (`a2a`, 3 corridas):** 100 % de acuerdo en las dos bases; ninguna columna cambia de marca ni de entidad.

### Por categoría de la lista

Columnas marcadas / columnas de la categoría.

| Categoría | MIMIC `a2a` | MIMIC `a2b` | MIMIC ofuscado | Synthea `a2a` | Synthea `a2b` | Synthea ofuscado |
|---|---|---|---|---|---|---|
| Fechas y geografía HIPAA (`cuasi_hipaa`) | 45/45 | 45/45 | 45/45 | 35/35 | 35/35 | 35/35 |
| Identificadores de paciente o episodio (`ident_opaco`) | 51/51 | 51/51 | 49/51 | 29/30 | 29/30 | 30/30 |
| Identificadores directos (`ident_directo`) | — | — | — | 12/12 | 12/12 | 12/12 |
| Demográficos (`cuasi`) | 7/7 | 7/7 | 7/7 | 5/6 | 6/6 | 6/6 |
| Datos de salud y origen (`sensible`) | 80/131 | 83/131 | 84/131 | 35/58 | 40/58 | 42/58 |
| Profesionales | 13/14 | 14/14 | 11/14 | 11/16 | 11/16 | 14/16 |
| Económicos del paciente | — | — | — | 20/22 | 20/22 | 13/22 |
| Catálogos (no sensibles) | **0/23** | **0/23** | 12/23 | 6/28 | 6/28 | 12/28 |
| Técnicas (no sensibles) | 1/41 | 6/41 | 4/41 | 7/32 | 8/32 | 12/32 |
| Texto libre | 2/2 | 2/2 | 2/2 | — | — | — |

Comparado con Presidio (A1m / A1s): los demográficos pasan de 0/4 y 1/5 a casi todos; los catálogos de MIMIC, de
14/23 a 0/23; los datos de salud, de 62/131 marcados con etiquetas absurdas a 80/131 marcados como `SALUD`.

### Sonda de contaminación

Con solo los nombres de tablas y columnas, a la pregunta «¿de qué base pública proviene?»:

- MIMIC: «Este esquema pertenece a la base de datos **MIMIC-III**…» (es la IV, pero la reconoce).
- Synthea: «Este esquema pertenece a la base de datos de ejemplo **Synthea**…».

Respuestas completas: `resultados/<base>/a2<m|s>_sonda.md`.

### Tiempo

| Base | `a2a` (por corrida) | `a2b` | `a2b_ofuscado` | Tokens generados por corrida |
|---|---|---|---|---|
| MIMIC (31 tablas, 342 columnas) | 862–911 s | 974 s | 957 s | ~12 600 |
| Synthea (18 tablas, 256 columnas) | 582–606 s | 693 s | 734 s | ~9 000 |

Unos 15 tokens por segundo. **Las corridas 1 y 2 de `a2a` en MIMIC del lote (1695 s y 15 336 s) no cuentan:** la Mac
estaba a batería y se suspendió varias veces; las clasificaciones no cambian (temperatura 0), solo el tiempo. Los
862 s son de una corrida de prueba previa, idéntica en resultado. El resto se corrió con el equipo enchufado y
`caffeinate`.

## Hallazgos

- **El LLM resuelve lo que Presidio no puede: clasificar columnas por su significado.** Distingue catálogos de datos
  de pacientes, reconoce demográficos sin formato (sexo, estado civil, idioma, seguro) y etiqueta los datos clínicos
  como salud.
- **Los nombres de columna aportan sobre todo para descartar.** Sin nombres (ofuscado), el recall se mantiene o sube,
  pero se marcan catálogos y técnicas: el LLM ve descripciones de diagnósticos o direcciones y no sabe que son de un
  catálogo o de un hospital.
- **La contaminación existe pero no explica el resultado.** El LLM reconoce MIMIC y Synthea, pero con todo ofuscado
  pierde solo 3 puntos de F1 en MIMIC y ninguno en Synthea. Para una base propia (sin esquema público) es esperable
  algo parecido a la variante ofuscada, con nombres que ayudan a descartar catálogos.
- **Hueco que queda: datos de salud «indirectos».** `itemid` (qué se midió o administró), unidades de cuidado,
  cantidades, tasas y valores de referencia. Para el LLM son técnicos; para la lista son salud, porque dicen qué le
  pasó al paciente. Es un caso de criterio: conviene que la política del sistema lo diga explícitamente (o que el
  usuario lo decida, como en DEC-1 a DEC-6), en lugar de esperar que el modelo lo infiera.
- **Falsos positivos de Synthea:** los ids de seguro del paciente (`primarypatientinsuranceid`) y el pagador de cada
  encuentro, que la lista trata como técnicos, y los datos de contacto de `organizations`. Son discutibles: un
  revisor humano podría marcarlos igual.
- **Arquitectura en cascada:** el LLM como clasificador principal por columna (esquema + muestra), y Presidio solo
  para confirmar formatos concretos (SSN, licencia, fechas) y para el texto libre.
- **Viable en local:** 10 a 16 minutos por base, sin enviar datos a terceros. Con la MIMIC completa, el esquema es el
  mismo (31 tablas): el costo no crece con las filas, solo con las columnas.

## Limitaciones

- Un solo modelo (Gemma 4 12B, el único que entra cómodo en 16 GB junto con Docker). No se probó un modelo más grande
  ni el modo de razonamiento.
- Política y prompt en español sobre esquemas en inglés; no se probaron otras redacciones de la política.
- La lista de referencia sale de reglas, sin anotación manual independiente (ver `taxonomia.md`). Parte de los FN de
  datos de salud y de los FP de Synthea son decisiones de criterio, no errores claros.
- `a2b` y `a2b_ofuscado`, una sola corrida (justificado por el determinismo de `a2a`).

## Evidencia

- `resultados/<base>/a2<m|s>_<variante>_columnas.csv` y `_corrida.md` (parámetros, tiempos, sha256 de la política).
- `resultados/<base>/a2<m|s>_sonda.md`.
- `resultados/<base>/crudo/`: la respuesta JSON del LLM por tabla y corrida (sin valores de filas).
- `resultados_comparados/salud/<base>/`: métricas, matriz por columna y resumen.
