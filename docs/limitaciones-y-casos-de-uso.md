# Alcance, limitaciones y funcionalidades esperadas

> Borrador de trabajo para cerrar la **etapa 1** de la planilla del Proyecto de Grado. Estado al 2026-10-12.
> Es material para discutir entre Paola y Jero y con la supervisora, no texto final del informe.

[← Volver a la puerta de entrada](README.md)

---

## 1. Dónde estamos según la planilla

| Etapa | Duración | Producto |
|---|---|---|
| **1. Estudio de conceptos y enfoques** ← *actual* | 2 meses | **Resultado 1:** informe de estado del arte, incluida la integración de IA en el proceso y en tareas específicas |
| 2. Relevamiento, análisis y evaluación de propuestas | 2 meses | Resultado 2: informe que evalúa propuestas y estrategias y **define** la propuesta propia |
| 3. Prototipo | 2 meses | Resultado 3: informe + prototipo |
| 4. Caso de estudio | 1 mes | Resultado 4: aplicación de la propuesta **con procesos y datos reales** (objetivo 4) |
| 5. Informe final y defensa | 1 mes | Resultado 5 |

**Consecuencia para este documento.** El producto de la etapa 1 es el informe de estado del arte. Las limitaciones
**del proyecto** y las funcionalidades del sistema son parte de definir la propuesta, que es la **etapa 2**: **no van
en el informe de la etapa 1**. Por eso lo que sigue se divide en:

- **Para el resultado 1 (informe de estado del arte):** sección 2 (lo que le falta al informe) y sección 3.1
  (limitaciones **del estudio**: qué se relevó y qué no. No confundir con las del proyecto).
- **Preparación de la etapa 2 (no va en el informe):** secciones 3.2, 4 y 5. Se adelantan ahora porque la sección 5
  (preguntas a la cliente) conviene resolverla cuanto antes y condiciona todo lo demás.

---

## 2. Qué le falta al informe de estado del arte para cerrar el resultado 1

| # | Falta | Dónde va en el informe | Base |
|---|---|---|---|
| 1 | **Delimitación del estudio**: qué se relevó y qué no, con qué criterio y fecha de corte | Cap. 1, nueva sección «Alcance y limitaciones del estudio» | Sección 2 de este documento |
| 2 | **Evidencia práctica** de las herramientas: hoy la comparación del informe se apoya solo en documentación (D). La letra pide «comparar herramientas con evidencias verificables» | Cap. 2, o un anexo «Pruebas exploratorias» que resuma la [comparativa](comparativa.md) | Pruebas A1, D2, D5, E3 (hechas) |
| 3 | **Corrección sobre reproducibilidad**: el anexo A dice «misma semilla, mismo resultado», pero D2 registró que MOSTLY AI no tiene semilla y Anonymeter no es determinista (E3) | Cap. 3.3 y anexo A | L-P8 en la sección 3 |

Para el punto 2 alcanza con lo que ya está hecho. No hace falta cerrar todas las pruebas pendientes para entregar
la etapa 1: muchas son en realidad parte de la etapa 2 (evaluar propuestas).

---

## 3. Limitaciones

### 3.1 Limitaciones del estudio (para el resultado 1, se pueden escribir ya)

| ID | Limitación | Fundamento |
|---|---|---|
| L-E1 | **Fecha de corte:** el relevamiento refleja el estado del sector al tercer cuatrimestre de 2026; hubo una fuerte consolidación entre 2024 y 2026 | Informe, Tabla 2.5 y 5.3 |
| L-E2 | **Herramientas comerciales** (Tonic, Delphix, Informatica, IBM Optim) relevadas por documentación y, en Tonic, con las versiones gratuitas o de prueba; no se consideran como componente de la solución | Costo y opacidad (informe 2.2.6 y 3.5) |
| L-E3 | **Pruebas exploratorias, no benchmarks:** una sola base (Pagila), una o pocas corridas por herramienta, en dos portátiles distintas. Los tiempos no se comparan entre equipos | [Plan de pruebas](plan-de-pruebas.md) |
| L-E4 | **La base de las pruebas es pública** y los modelos de lenguaje la conocen: Tonic Fabricate generó el Sakila clásico en vez del esquema v4 que se le pasó (D5). Los resultados de herramientas con LLM sobre Pagila pueden estar inflados | D5 |
| L-E5 | **Sin GPU NVIDIA:** no se probaron los generadores que la exigen (difusión, NeMo Safe Synthesizer); su evaluación queda solo por documentación | Equipos: Mac M5 Pro 16 GB y M1 8 GB |
| L-E6 | **Cobertura por motor**: el relevamiento compara siete motores, pero las pruebas prácticas se hicieron solo en PostgreSQL | Tabla 2.17; pruebas |
| L-E7 | **Marco legal**: se usan EDPB e ICO como referencia metodológica; el borrador de Guías 02/2026 del EDPB estaba en consulta pública al momento del estudio | Informe 2.1.2 |

### 3.2 Limitaciones preliminares del proyecto (etapa 2, no va en el informe de la etapa 1)

Se presentan como **propuesta**: la decisión final es parte del resultado 2. Las marcadas con ⚠ dependen de lo que
aporte la cliente y no conviene fijarlas sin hablar con ella.

| ID | Dimensión | Propuesta preliminar | Fundamento |
|---|---|---|---|
| L-P1 ⚠ | **Motor de base de datos** | Un solo motor. PostgreSQL por defecto, **salvo que el caso de la cliente use otro** | Ver sección 5 |
| L-P2 ⚠ | **Caso de estudio y datos** | Validación final con el caso de la cliente (objetivo 4); Pagila como base de desarrollo y comparación | Planilla, objetivo 4 |
| L-P3 | **Hardware** | Todo corre por CPU en portátiles; quedan fuera técnicas que exigen GPU | L-E5; D2 (MOSTLY no usa la GPU de Apple, 8,1 GB de pico) |
| L-P4 | **Escala** | Bases de decenas de tablas y del orden de 10⁵–10⁶ filas en el subconjunto; el tope exacto se mide en la etapa 2 | D2: Pagila completa, 8,5 min de entrenamiento y 12,1 de generación |
| L-P5 | **Esquema soportado** | Dentro: FK simples y compuestas, PK compuestas, ciclos, particiones, FK no declaradas (propuestas y confirmadas por una persona), tablas de catálogo. Fuera: referencias polimórficas y reglas que solo viven en el código de la aplicación | D2, D5, E3; informe 2.4.3 |
| L-P6 | **Tipos de datos** | Dentro: escalares. Texto libre: detectar y redactar, no sintetizar. BYTEA: reemplazo por relleno. JSON, geoespaciales y cifrados: fuera o regla fija | Informe Tabla 2.19; A7 |
| L-P7 | **Modelo de lenguaje** | Solo local, con salida validada contra esquema; nunca ejecuta SQL. Qué ve (nombres, estadísticos o muestra) se decide con la prueba A2b | Restricción on-premise; informe 3.3 |
| L-P8 | **Reproducibilidad** | Etapas deterministas: idénticas con la misma semilla. Etapas generativas y validación de privacidad: **reproducibles por artefactos** (generador y base guardados con su hash) | D2, E3. Corrige el anexo A |
| L-P9 | **Privacidad** | El proceso mide el riesgo y bloquea por umbral; no certifica anonimato legal. La salida se trata como dato personal salvo evaluación del responsable | Principio «sintético ≠ anónimo»; EDPB 02/2026 |
| L-P10 | **Utilidad para testing** | Medida con una suite de referencia (consultas de negocio con aserciones y comparación de planes); la cobertura de código, solo si el caso de la cliente trae aplicación y tests | Informe Tabla 2.20 |
| L-P11 | **Modo de operación** | Por lotes, línea de comandos y archivos de configuración; revisión humana editando el catálogo. Sin interfaz gráfica ni integración real con CI/CD | Foco en las preguntas de investigación |
| L-P12 | **Volumen de salida** | Igual o menor que el origen | Mantiene comparables las métricas de privacidad y de planes |
| L-P13 | **Idioma** | Español e inglés; identificadores uruguayos (cédula, celular, RUT) | A1, A7 |

---

## 4. Funcionalidades esperadas (preliminar, etapa 2, no va en el informe de la etapa 1)

Derivadas de la arquitectura del informe (cap. 3) y de los requisitos que surgieron en las pruebas. Es la lista
de **qué tiene que hacer el proceso**; el detalle (entradas, salidas, criterios de aceptación) es trabajo de la
etapa 2.

| # | Funcionalidad | Capa | Rol de la IA | Requisito que la origina |
|---|---|---|---|---|
| F1 | Introspección del esquema: grafo de tablas, claves, restricciones, particiones, hash del esquema | 0 | Ninguno | Informe 3.2 |
| F2 | Propuesta de relaciones no declaradas, verificadas por contenido | 0 | Propone | E3: 49 de 55 particiones de `payment` sin FK |
| F3 | Clasificación de columnas en cascada (reglas → NER → LLM local), con confianza por columna | 1 | Propone | A1: Presidio solo mira valores; no detecta hashes ni ids |
| F4 | Revisión humana y congelamiento del catálogo como artefacto versionado | 1 | — | Reproducibilidad; riesgo de falso negativo (Tabla 4.1) |
| F5 | Declaración de restricciones de negocio en un formato propio | 3 | Propone | D2 y D5 violaron unicidad y rangos de partición |
| F6 | Extracción de un subconjunto coherente desde tablas ancla | 2 | — | No hay implementación abierta madura (Tabla 3.1) |
| F7 | Separación del conjunto de control antes de entrenar | 2/4 | — | E3: sin control previo se subestima el riesgo |
| F8 | Transformación por clase de columna: claves por vía determinista; catálogos copiados; datos con formato con valores falsos; negocio por síntesis; post-proceso de restricciones | 3 | — | D2: catálogos destruidos (`_RARE_`), textos sin formato, duplicados |
| F9 | Detección y redacción en texto libre | 3 | — | A7 |
| F10 | Validación independiente con gate bloqueante: integridad, fidelidad, utilidad, privacidad | 4 | — | Informe 3.2 y 3.3 |
| F11 | Manifiesto de trazabilidad firmado | 5 | — | EDPB 02/2026; anexo A |
| F12 | Refresco ante cambio de esquema: reclasifica solo lo nuevo | 0/1 | Propone | Riesgo de deriva (Tabla 4.1) |

**Flujo principal:** F1 → F2 → F3 → F4 → F5 → F6 → F7 → F8 (+F9) → F10 → F11 → entrega.
Si el gate rechaza, se ajusta la configuración o el catálogo y se vuelve a F8 o a F4; si un componente generativo
falla, la columna pasa a vía determinista y queda registrado (degradación elegante, informe 3.3).

---

## 5. Lo que hay que preguntarle a la cliente antes de cerrar la etapa 1

El objetivo 4 dice «caso de estudio **con base en procesos y datos reales**». Eso cambia dos supuestos con los que
venían trabajando:

1. **¿Va a haber datos reales?** Si la cliente aporta una base (o un entorno donde correr el proceso), la
   restricción on-premise deja de ser teórica: el proceso tiene que correr **en su infraestructura** y ningún dato
   puede salir de ahí, ni siquiera hacia los equipos de ustedes. Eso condiciona hardware, modelo de lenguaje y
   dónde se ejecutan las pruebas.
2. **¿Qué motor usa ese caso?** Si es PostgreSQL, L-P1 queda como está. Si es otro (SQL Server, Oracle, MySQL), se
   pierde PostgreSQL Anonymizer y la vía determinista pasa a ser Faker + tokenización propia. Conviene saberlo
   **antes** de invertir más en B1.
3. **¿El caso trae aplicación y tests?** Si sí, la utilidad para testing (L-P10) se mide con su suite real y con
   cobertura de código; si no, con la suite de referencia propia.
4. **¿Qué volumen y qué tipos de datos tiene?** Define L-P4 y L-P6.

Si la cliente no puede aportar datos reales, eso se dice como limitación del proyecto y el caso de estudio pasa a
ser un esquema propio poblado con datos ficticios uruguayos (más Pagila con columnas renombradas para controlar la
contaminación de L-E4).
