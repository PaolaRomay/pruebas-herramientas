# Revisión de limitaciones y flujos

> Hoja de trabajo para decidir, ítem por ítem, qué queda del documento
> [limitaciones-y-casos-de-uso.md](limitaciones-y-casos-de-uso.md) (borrador del 2026-10-12).
> Cada ítem trae qué significa, una sugerencia y un campo **Decisión** para completar.
> Las sugerencias tienen en cuenta las pruebas hechas después del borrador (B3, D6 y las reglas de negocio implícitas).

[← Volver a la puerta de entrada](README.md)

**Sugerencias:** `DEJAR` = queda como está · `AJUSTAR` = queda, con el cambio indicado · `AGREGAR` = falta en el borrador.

**Decisiones:** completar con `dejar`, `ajustar`, `sacar` o `mover` y, si hace falta, una nota.

---

## 0. Qué va en cada entrega

- **Entrega 1 (informe de estado del arte):** solo las limitaciones del **estudio** (sección 2 de esta hoja).
- **Etapa 2 (definir la propuesta):** las limitaciones del **proyecto** (sección 3) y las funcionalidades (sección 4).

**Decisión:**

---

## 1. Lo que le falta al informe de la etapa 1

### 1.1 Sección «Alcance y limitaciones del estudio»
- **Qué es:** una sección nueva en el capítulo 1 que diga qué se relevó y qué no, con qué criterio y con qué fecha de corte.
- **Sugerencia:** DEJAR.
- **Decisión:**

### 1.2 Evidencia práctica de las herramientas
- **Qué es:** hoy la comparación del informe se apoya solo en documentación; la letra pide «evidencias verificables».
- **Sugerencia:** AJUSTAR. A las pruebas A1, D2, D5 y E3, sumarles B3 (ARX) y D6 (REaLTabFormer), que se hicieron después del borrador.
- **Decisión:**

### 1.3 Corrección sobre reproducibilidad
- **Qué es:** el anexo A dice «misma semilla, mismo resultado».
- **Sugerencia:** DEJAR. Está comprobado: MOSTLY AI no tiene semilla (D2) y Anonymeter no es determinista ni con semilla (E3).
- **Decisión:**

---

## 2. Limitaciones del estudio (entrega 1)

### L-E1 · Fecha de corte
- **Qué es:** el relevamiento refleja el estado del sector a fines de 2026; el mercado se consolidó mucho entre 2024 y 2026.
- **Sugerencia:** DEJAR. Ejemplo concreto: la plataforma gratuita de MOSTLY AI en la nube ya no existe (D2).
- **Decisión:**

### L-E2 · Herramientas comerciales
- **Qué es:** Tonic, Delphix, Informatica e IBM Optim se relevaron por documentación y, en Tonic, con las versiones gratuitas o de prueba. No se consideran como componente de la solución.
- **Sugerencia:** DEJAR.
- **Decisión:**

### L-E3 · Pruebas exploratorias, no benchmarks
- **Qué es:** una sola base (Pagila), una o pocas corridas por herramienta, en dos portátiles distintas. Los tiempos no se comparan entre equipos.
- **Sugerencia:** DEJAR.
- **Decisión:**

### L-E4 · La base de las pruebas es pública
- **Qué es:** los modelos de lenguaje conocen Pagila y Sakila, así que los resultados de herramientas con LLM pueden estar inflados.
- **Sugerencia:** AJUSTAR. Escribirlo como hipótesis: la salida de Tonic Fabricate coincide con la Sakila original (2 tiendas, alquileres en 2005) y no con Pagila v4 (500 tiendas, 2022-2026), lo que sugiere que el modelo reconoció el esquema. Proponer una prueba con columnas renombradas.
- **Decisión:**

### L-E5 · Sin GPU NVIDIA
- **Qué es:** no se probaron los generadores que exigen GPU (difusión, NeMo Safe Synthesizer); quedan evaluados solo por documentación.
- **Sugerencia:** DEJAR. Sin mencionar la prueba en Colab, que se descartó por innecesaria.
- **Decisión:**

### L-E6 · Cobertura por motor
- **Qué es:** el relevamiento compara siete motores, pero las pruebas prácticas se hicieron solo en PostgreSQL.
- **Sugerencia:** DEJAR.
- **Decisión:**

### L-E7 · Marco legal
- **Qué es:** se usan EDPB e ICO como referencia metodológica; el borrador de las Guías 02/2026 del EDPB estaba en consulta pública.
- **Sugerencia:** DEJAR.
- **Decisión:**

---

## 3. Limitaciones del proyecto (etapa 2)

Las marcadas con ⚠ dependen de lo que responda la cliente (sección 5).

### L-P1 ⚠ · Motor de base de datos
- **Qué es:** un solo motor: PostgreSQL, salvo que el caso de la cliente use otro.
- **Sugerencia:** DEJAR, pendiente de la cliente.
- **Decisión:**

### L-P2 ⚠ · Caso de estudio y datos
- **Qué es:** la validación final se hace con el caso de la cliente (objetivo 4); Pagila queda como base de desarrollo y comparación.
- **Sugerencia:** DEJAR, pendiente de la cliente.
- **Decisión:**

### L-P3 · Hardware
- **Qué es:** todo corre por CPU en portátiles; quedan fuera las técnicas que exigen GPU.
- **Sugerencia:** DEJAR. En D2, MOSTLY no usa la GPU de Apple y el pico de memoria fue de 8,1 GB.
- **Decisión:**

### L-P4 · Escala
- **Qué es:** bases de decenas de tablas y del orden de 10⁵ a 10⁶ filas en el subconjunto.
- **Sugerencia:** AJUSTAR. Pagila tiene 121 209 filas en total (15 tablas); 10⁶ no está probado. Ponerlo como meta a medir en la etapa 2.
- **Decisión:**

### L-P5 · Esquema soportado
- **Qué es:** dentro: FK simples y compuestas, PK compuestas, ciclos, particiones, FK no declaradas, tablas de catálogo. Fuera: referencias polimórficas y reglas que solo viven en el código de la aplicación.
- **Sugerencia:** AJUSTAR. Distinguir las **reglas implícitas declarables** de las que viven solo en el código. Ejemplos de las declarables: la devolución es posterior al alquiler; el cliente del pago es el del alquiler. Las herramientas de síntesis las rompen: MOSTLY genera un 38 % de devoluciones antes del alquiler y REaLTabFormer asigna mal el cliente en el 99,9 % de los pagos.
- **Decisión:**

### L-P6 · Tipos de datos
- **Qué es:** escalares, dentro. Texto libre: detectar y redactar, no sintetizar. BYTEA: reemplazar por relleno. JSON, geoespaciales y cifrados: fuera o con regla fija.
- **Sugerencia:** AJUSTAR. Dejar el texto libre abierto hasta probar un LLM local generando texto: MOSTLY lo genera carácter por carácter (`ENEIN HONTO`, correos con dos `@`).
- **Decisión:**

### L-P7 · Modelo de lenguaje
- **Qué es:** solo local, con la salida validada contra un esquema; nunca ejecuta SQL. Qué ve (nombres, estadísticos o muestra) se decide con la prueba A2b.
- **Sugerencia:** AJUSTAR. Varias pruebas propuestas hacen que el LLM **escriba** SQL (subconjunto, reglas de enmascaramiento). Precisarla así: «el LLM propone; el proceso valida y ejecuta sobre una copia».
- **Decisión:**

### L-P8 · Reproducibilidad
- **Qué es:** las etapas deterministas dan lo mismo con la misma semilla; las generativas y la validación de privacidad se reproducen por artefactos (generador y base guardados con su hash).
- **Sugerencia:** DEJAR.
- **Decisión:**

### L-P9 · Privacidad
- **Qué es:** el proceso mide el riesgo y bloquea por umbral; no certifica anonimato legal. La salida se trata como dato personal salvo evaluación del responsable.
- **Sugerencia:** DEJAR.
- **Decisión:**

### L-P10 · Utilidad para testing
- **Qué es:** se mide con una suite de referencia (consultas de negocio con aserciones y comparación de planes); la cobertura de código, solo si la cliente trae aplicación y tests.
- **Sugerencia:** DEJAR.
- **Decisión:**

### L-P11 · Modo de operación
- **Qué es:** por lotes, línea de comandos y archivos de configuración; revisión humana editando el catálogo. Sin interfaz gráfica ni integración real con CI/CD.
- **Sugerencia:** DEJAR (decisión de ustedes).
- **Decisión:**

### L-P12 · Volumen de salida
- **Qué es:** igual o menor que el origen, para que las métricas de privacidad y de planes sean comparables.
- **Sugerencia:** DEJAR.
- **Decisión:**

### L-P13 · Idioma
- **Qué es:** español e inglés; identificadores uruguayos (cédula, celular, RUT).
- **Sugerencia:** DEJAR.
- **Decisión:**

---

## 4. Funcionalidades y flujo principal (etapa 2)

**Flujo principal:** F1 → F2 → F3 → F4 → F5 → F6 → F7 → F8 (+F9) → F10 → F11 → entrega.
Si la validación (F10) rechaza, se ajusta la configuración o el catálogo y se vuelve a F8 o a F4. Si un componente
generativo falla, esa columna pasa a la vía determinista y queda registrado.

**Decisión sobre el flujo:**

### F1 · Introspección del esquema
- **Qué es:** leer tablas, claves, restricciones y particiones, y calcular el hash del esquema.
- **Sugerencia:** DEJAR.
- **Decisión:**

### F2 · Relaciones no declaradas
- **Qué es:** proponer relaciones que el catálogo no tiene y verificarlas contra los datos.
- **Sugerencia:** DEJAR. Evidencia: las FK de `payment` están declaradas solo en 6 de sus 55 particiones, y `store.manager_staff_id → staff` no está declarada.
- **Evidencia nueva (MIMIC, 2026-11-13):** la demo de MIMIC-IV tiene 25 relaciones sin declarar. Herramientas de código abierto que lo resuelven: **Metanome** (Apache 2.0) con dos filtros encuentra las 20 que se cumplen, con precisión 0,96; **SchemaSpy** (LGPL-3.0) encuentra 10, incluidas las 5 con huérfanas; el LLM local, 5. Ver [F2m con herramientas](../pruebas/salud/F2-relaciones-herramientas/ficha.md).
- **Decisión:**

### F3 · Clasificación de columnas en cascada
- **Qué es:** reglas → NER → LLM local, con una confianza por columna.
- **Sugerencia:** DEJAR. La van a respaldar A2a, A2b (LLM) y A5 (`anon.detect`, que detecta solo por nombre de columna).
- **Decisión:**

### F4 · Revisión humana y congelamiento del catálogo
- **Qué es:** una persona aprueba la clasificación y queda guardada como artefacto versionado.
- **Sugerencia:** DEJAR.
- **Decisión:**

### F5 · Restricciones de negocio
- **Qué es:** declarar las restricciones de negocio en un formato propio.
- **Sugerencia:** AJUSTAR. Agregar «y validarlas después de generar». La evidencia es la tabla de reglas implícitas (ver L-P5). Fabricate cumple las reglas de sentido común solo porque inventa su propia lógica, la de la Sakila clásica.
- **Decisión:**

### F6 · Extracción de subconjunto
- **Qué es:** extraer un subconjunto coherente a partir de tablas ancla.
- **Sugerencia:** DEJAR (la prueba C1 sigue pendiente).
- **Decisión:**

### F7 · Conjunto de control
- **Qué es:** separar un conjunto de control antes de entrenar, para medir la privacidad.
- **Sugerencia:** DEJAR. Es lo que hace E3 (200 clientes de control).
- **Decisión:**

### F8 · Transformación por clase de columna
- **Qué es:** claves por vía determinista; catálogos copiados; datos con formato reemplazados por valores falsos; datos de negocio sintetizados; post-proceso de restricciones.
- **Sugerencia:** AJUSTAR. Nombrar las candidatas: PostgreSQL Anonymizer para columnas estructuradas (seudonimización determinista), Presidio para el texto y ARX como medidor de k-anonimato, no como anonimizador (B3: deja `*` y no sirve para testing).
- **Decisión:**

### F9 · Texto libre
- **Qué es:** detectar y redactar datos personales dentro de texto libre.
- **Sugerencia:** DEJAR, con Presidio (analyzer + anonymizer).
- **Decisión:**

### F10 · Validación con gate bloqueante
- **Qué es:** validación independiente de integridad, fidelidad, utilidad y privacidad; si no pasa, la base no se entrega.
- **Sugerencia:** AJUSTAR. Sumarle la validación de las reglas de negocio de F5.
- **Decisión:**

### F11 · Manifiesto de trazabilidad
- **Qué es:** un registro firmado de qué se hizo, con qué versiones y con qué resultados.
- **Sugerencia:** DEJAR.
- **Decisión:**

### F12 · Refresco ante cambio de esquema
- **Qué es:** cuando cambia el esquema, reclasificar solo lo nuevo.
- **Sugerencia:** DEJAR.
- **Decisión:**

### Nueva · Capa de adaptadores
- **Qué es:** el código que lleva los datos de la base al formato de cada herramienta (DataFrames, CSV, solo el esquema) y los vuelve a cargar. En todas las pruebas hubo que escribirlo: D2 y D6 con Parquet, B3 con CSV, D5 con el `.sql` de Fabricate.
- **Sugerencia:** AGREGAR, como funcionalidad propia o dentro de F8.
- **Decisión:**

---

## 5. Preguntas a la cliente (lo más urgente)

1. **¿Va a haber datos reales?** Si los hay, el proceso tiene que correr en su infraestructura y ningún dato puede salir de ahí.
2. **¿Qué motor usa?** Si no es PostgreSQL, se pierde PostgreSQL Anonymizer y la vía determinista pasa a ser Faker más una tokenización propia.
3. **¿Trae aplicación con tests?** Define cómo se mide la utilidad (L-P10).
4. **¿Qué volumen y qué tipos de datos tiene?** Define L-P4 y L-P6.

Si la cliente no puede aportar datos reales, se declara como limitación del proyecto y el caso de estudio pasa a ser
un esquema propio con datos ficticios uruguayos, más Pagila con las columnas renombradas (por L-E4).

**Decisión:**
