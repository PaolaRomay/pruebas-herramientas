# Plan de pruebas

> Transcripción del plan acordado entre Paola y Jero para el estado del arte de la tesis. Si hay
> diferencias con el documento de la tesis, vale el de la tesis. Estado al 2026-10-11.

[← Volver a la puerta de entrada](README.md)

## Para qué existen estas pruebas

La tesis (Ingeniería en Computación, FING, UdelaR) propone un **proceso asistido por IA para extraer,
anonimizar y generar bases de datos de preproducción para testing a partir de datos productivos**. Para el
estado del arte se prueban herramientas existentes que resuelven partes de ese proceso.

La regla que hace comparables las pruebas:

> **Cada herramienta se responde con las mismas preguntas, y cada función se mide con las mismas métricas
> sobre los mismos datos.**

- **Datos:** la base de ejemplo **Pagila** (pagila-v4.0.0) en PostgreSQL, igual para todos. Ver el
  [glosario y método](glosario-y-metodo.md#pagila).
- **Verdad de referencia** para las pruebas de detección: una lista de columnas sensibles armada a mano,
  [`data/columnas_sensibles_borrador.csv`](../data/columnas_sensibles_borrador.csv). **Todavía es un borrador**:
  hay que congelarla antes de dar por cerradas las comparaciones de la función A.
- Las pruebas son **exploratorias**. Lo importante es que queden registradas de forma comparable, no
  agotar cada herramienta.

## Cómo se nombran

Cada prueba tiene un ID: la **letra** es la función y el **número**, la herramienta o variante. Las pruebas
de la misma letra se comparan entre sí. Cada una vive en `pruebas/<ID>-<herramienta>/`.

## Funciones y métricas mínimas

| Letra | Función | Métricas mínimas |
|---|---|---|
| **A** | Detectar datos sensibles | Columnas bien y mal clasificadas contra la lista manual, y falsos negativos: TP, FP, FN, precisión, recall y F1. Con un modelo de lenguaje (LLM): repetir 3 veces y contar cuántas columnas cambian de etiqueta. |
| **B** | Anonimizar | Si las FK siguen resolviendo, si se conserva la relación entre columnas (ciudad ↔ código postal), si es reversible, y el tiempo. |
| **C** | Extraer subconjuntos | Integridad del subconjunto, % de la base que arrastra y ciclos resueltos, con la misma tabla ancla y el mismo filtro. |
| **D** | Sintetizar | Tiempo de entrenamiento y de generación, memoria máxima, claves huérfanas o duplicadas, y un reporte de calidad. |
| **E** | Validar privacidad | Anonymeter (singling out, linkability, inference) frente a un conjunto de control. |
| **F** | Utilidad para testing | Mini-experimento sobre base real vs. anonimizada vs. sintética. |
| **G** | Orquestar con un LLM | % de salidas JSON válidas, % de funciones bien elegidas, latencia y variabilidad, sobre los mismos casos. |

## Qué registra cada prueba (la ficha, «Bloque 2»)

Cada prueba tiene una `ficha.md` hecha a partir de [la plantilla](../pruebas/_plantilla/ficha.md), con:

1. **Entorno:** equipo, versión exacta de la herramienta y datos usados.
2. **Qué se midió y resultado:** solo las métricas mínimas de su función.
3. **Esfuerzo:** problemas encontrados para llegar a la primera corrida.
4. **Hallazgos:** limitaciones vistas en la práctica y requisitos que surgen para el sistema de la tesis.
5. **Evidencia:** resultados generados por los scripts, logs y gráficos.
6. **Opcional:** reproducibilidad (¿misma semilla, mismo resultado?).

Cada dato lleva su origen: **D** (documentación de la herramienta) o **P** (prueba propia).

Una prueba cuenta si (1) dice con qué datos se hizo, (2) lleva el hardware y la versión, (3) tiene al menos
un resultado concreto y (4) tiene evidencia guardada.

## Todas las pruebas y su estado

Estados: ✅ hecha · 🔄 en curso · 📝 hecha fuera del repo (hay que rehacerla o documentarla) · ⏳ pendiente.

### A — Detectar datos sensibles

| ID | Herramienta / variante | Responsable | Estado |
|---|---|---|---|
| A1 | Presidio (por valor, con y sin contexto, y presidio-structured) | Paola | ✅ [ficha](../pruebas/A1-presidio/ficha.md) |
| A2a | LLM local con solo los nombres de las columnas (Gemma 12B y 26B) | Jero | 📝 hecha fuera del repo, solo cualitativa: hay que rehacerla con las métricas de A |
| A2b | LLM con nombres + una muestra de valores (p. ej. Qwen 3 14B) | Jero | ⏳ |
| A3 | Reconocedor de cédula uruguaya en Presidio | Paola | ⏳ |
| A4 | GLiNER | sin asignar | ⏳ |
| A5 | `anon.detect` de PostgreSQL Anonymizer | sin asignar | ⏳ |
| A6 | El LLM propone por nombre y Presidio confirma por valor | Jero | ⏳ |
| A7 | Tonic Textual (sin trial) | Jero | 🔄 [ficha](../pruebas/A7-tonic-textual/ficha.md) |
| A8 | Tonic Structural (con trial) | sin asignar | ⏳ |

### B — Anonimizar

| ID | Herramienta / variante | Responsable | Estado |
|---|---|---|---|
| B1 | PostgreSQL Anonymizer | Paola | 🔄 |
| B2 | Presidio con cifrado reversible | Paola | ⏳ |
| B3 | ARX (k-anonimato) | Jero | ✅ [ficha](../pruebas/B3-arx/ficha.md) |
| B4 | Tonic Structural (con trial) | sin asignar | ⏳ |

### C — Extraer subconjuntos

| ID | Herramienta / variante | Responsable | Estado |
|---|---|---|---|
| C1 | Condenser o script propio. Ancla `customer`, filtro `hashtext('c1' \|\| customer_id::text) % 10 = 0` (98 clientes). Ojo: `payment` está particionada y hay un ciclo `store` ↔ `staff` | Jero | ✅ [Condenser](../pruebas/C1-condenser/ficha.md) · [script propio](../pruebas/C1-script-propio/ficha.md) |
| C2 | Tonic Structural (con trial) | sin asignar | ⏳ |

### D — Sintetizar

| ID | Herramienta / variante | Responsable | Estado |
|---|---|---|---|
| D1 | MOSTLY AI SDK multi-tabla, sobre **otro esquema** (10 tablas, ~15 000 filas por tabla) | Jero | ❌ **desestimada:** se usa solo D2 (misma herramienta, sobre Pagila, hecha en el repo) |
| D2 | MOSTLY AI sobre Pagila | Jero | ✅ [ficha](../pruebas/D2-mostlyai/ficha.md) |
| D3 | SDV con 3, 5 y 10 tablas | sin asignar | ⏳ |
| D4 | Faker (línea base) | sin asignar | ⏳ |
| D5 | Tonic Fabricate (sin trial) | Jero | ✅ [ficha](../pruebas/D5-tonic-fabricate/ficha.md) |
| D6 | REaLTabFormer, **prueba de descarte** (Tabla 2.6 del informe): 2 niveles, 3 niveles nativo y encadenado, varios padres | Jero | ✅ [ficha](../pruebas/D6-realtabformer/ficha.md): confirma el descarte |

### E — Validar privacidad

| ID | Herramienta / variante | Responsable | Estado |
|---|---|---|---|
| E1 | SDV + Anonymeter | Paola | 🔄 |
| E3 | Chequeos propios: carga con restricciones, huérfanas, distancia al registro más cercano | Jero | ✅ [ficha](../pruebas/E3-chequeos-propios/ficha.md). Es el **evaluador común** que se aplica a la salida de las demás pruebas. |
| E4 | SyntheRela | sin asignar | ⏳ |
| E5 | Anonymeter sobre la salida de Fabricate | Jero | ✅ **confirmada:** cubierta con E3 sobre la base de D5 ([ficha D5](../pruebas/D5-tonic-fabricate/ficha.md), sección Privacidad) |
| E6 | Tonic Structural (con trial) | sin asignar | ⏳ |

### F y G

| ID | Herramienta / variante | Responsable | Estado |
|---|---|---|---|
| F1 | Mini-experimento de utilidad para testing | sin asignar | ⏳ |
| G1 | Qwen 3 local con salida restringida a un JSON Schema | Jero | ⏳ |
| G3 | Tonic Structural (con trial) | sin asignar | ⏳ |

### Bases de salud (MIMIC y Synthea)

Sobre la demo abierta de MIMIC-IV (100 pacientes, ya desidentificada) y Synthea (1 000 pacientes inventados),
con listas de referencia propias ([taxonomía](../pruebas/_bases/referencia/taxonomia.md)). Sufijo **m** = MIMIC, **s** = Synthea. Las
pruebas de «F2» corresponden a la funcionalidad F2 del sistema (relaciones no declaradas), no a la letra F del plan
(utilidad). Fichas de herramienta nuevas: [SchemaSpy](../pruebas/_herramientas/schemaspy.md) y [Metanome](../pruebas/_herramientas/metanome.md).

| ID | Herramienta | Función | Estado | Ficha |
|---|---|---|---|---|
| A1m / A1s | Presidio | Detectar | Hecha (2026-11-08) | [ficha](../pruebas/salud/A1-presidio/ficha.md) |
| A2m / A2s | LLM local (Gemma 4 12B, Ollama): esquema, muestra y esquema ofuscado | Detectar | Hecha (2026-11-08) | [ficha](../pruebas/salud/A2-llm-local/ficha.md) |
| A4m / A4s | GLiNER2-PII | Detectar | Hecha (2026-11-08) | [ficha](../pruebas/salud/A4-gliner2/ficha.md) |
| A5m / A5s | `anon.detect` (PostgreSQL Anonymizer) | Detectar | Hecha (2026-11-09) | [ficha](../pruebas/salud/A5-anon-detect/ficha.md) |
| A6m / A6s | LLM local + Presidio combinados | Detectar | Hecha (2026-11-08) | [ficha](../pruebas/salud/A6-llm-presidio/ficha.md) |
| C1m / C1s | Script propio de subconjuntos (tablas sin PK, relaciones no declaradas, pacientes de control) | Extraer subconjuntos | Hecha (2026-11-09) | [ficha](../pruebas/salud/C1-subconjunto/ficha.md) |
| B1m / B1s | PostgreSQL Anonymizer (funciones nativas y propias) | Anonimizar | Hecha (2026-11-09) | [ficha](../pruebas/salud/B1-anon/ficha.md) |
| B3m / B3s | ARX como medidor de riesgo del registro «paciente» | Anonimizar | Hecha (2026-11-09) | [ficha](../pruebas/salud/B3-arx/ficha.md) |
| D2m / D2s | MOSTLY AI (escalones de 47 a 10 000 pacientes) | Sintetizar | Hecha (2026-11-12) | [ficha](../pruebas/salud/D2-mostlyai/ficha.md) |
| D3m / D3s | SDV (HMA) con 3, 4 y 5 tablas | Sintetizar | Hecha (2026-11-12) | [ficha](../pruebas/salud/D3-sdv/ficha.md) |
| E3m / E3s | Evaluador propio adaptado a salud | Validar | Hecha (2026-11-12) | [ficha](../pruebas/salud/E3-evaluador/ficha.md) |
| E4m / E4s | SyntheRela | Validar | Hecha (2026-11-12) | [ficha](../pruebas/salud/E4-syntherela/ficha.md) |
| F1m / F1s | Consultas de referencia (utilidad) | Utilidad | Hecha (2026-11-12) | [ficha](../pruebas/salud/F1-utilidad/ficha.md) |
| F2m / F2s | LLM local propone relaciones | Entender el esquema | Hecha (2026-11-12) | [ficha](../pruebas/salud/F2-relaciones-llm/ficha.md) |
| F2m | **SchemaSpy** y **Metanome** (BINDER, SPIDER) descubren relaciones no declaradas | Entender el esquema | Hecha (2026-11-13) | [ficha](../pruebas/salud/F2-relaciones-herramientas/ficha.md) |
| G1m | Orquestación con el LLM local | Orquestar | Hecha (2026-11-12) | [ficha](../pruebas/salud/G1-orquestacion/ficha.md) |

### Herramientas comerciales

Tonic y Delphix se **analizan pero no se integran** (son caras).

- **Sin trial** se pueden hacer A7 (Tonic Textual sobre `film.description` y otras columnas), D5 (Tonic
  Fabricate) y E5 (Anonymeter sobre la salida de Fabricate).
- **Con el trial de Tonic Structural:** A8, B4, C2, E6 y G3.

## Equipos

Jero usa una Mac M5 Pro con 16 GB de RAM y Paola, una M1 con 8 GB. **Los tiempos no son comparables entre
máquinas**: cada ficha dice en qué equipo se corrió.
