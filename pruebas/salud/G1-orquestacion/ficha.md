# G1m — Orquestación con el LLM local sobre MIMIC-IV demo — Orquestar

**Quién / cuándo:** Jero (ejecutado por Claude Code a pedido de Jero), 2026-11-12.
**Fuente de cada dato:** P = prueba propia.

[← Casos de G1 (Pagila)](../../ESTADO.md#casos-de-orquestación-propuesta-para-g1-2026-10-11) ·
[A2m LLM local](../A2-llm-local/ficha.md) · [B1m](../B1-anon/ficha.md) · [C1m](../C1-subconjunto/ficha.md) ·
[D2m](../D2-mostlyai/ficha.md)

**Pregunta:** ¿un LLM local puede convertir un pedido en lenguaje natural en un plan ejecutable con las herramientas
que se probaron (detectar, subconjunto, anonimizar, sintetizar)?

## En pocas palabras

- **4 de 5 casos bien en las 3 corridas:** detectar, anonimizar, sintetizar y el pedido ambiguo.
  - Para anonimizar elige **seudonimizar los ids y desplazar las fechas por paciente**, la combinación que B1m
    mostró que es la correcta.
  - En el caso ambiguo hace 3 supuestos explícitos y 3 preguntas razonables.
- **El caso de subconjunto falla las 3 veces, en silencio:**
  - el plan es válido y el subconjunto se extrae y carga sin errores, pero **con 0 pacientes**;
  - el LLM escribe los códigos CIE con punto (`A41.%`), y en MIMIC van sin punto, o busca la palabra «Sepsis»
    dentro de la columna de códigos;
  - nunca une con el catálogo `d_icd_diagnoses`, donde está la descripción.
  - Darle 3 valores de ejemplo por columna **no lo arregla**: las 3 corridas buscan «Sepsis» en los códigos.
- **El plan es estable:** las mismas herramientas en las 3 corridas, salvo un paso `detectar` de más en el caso 3.
  Cambian detalles como la edad (ruido o década) o las tablas a sintetizar.
- **Tiempo:** 14 a 44 s por plan.
- **Conclusión:** como planificador, el LLM local acierta en qué hacer. Falla en **escribir SQL sobre el dominio**,
  y eso no da ningún error. El sistema necesita **verificar el resultado de cada paso** (por ejemplo, «el filtro
  devuelve 0 pacientes: ¿seguro?») antes de seguir.

## Entorno

- Ollama 0.40.15, `gemma4:12b-it-qat`, sin razonamiento, **temperatura 0,7** (para medir la variabilidad), semillas
  1 a 3, salida JSON forzada (herramientas y parámetros con valores cerrados).
- El LLM ve: la descripción de las 4 herramientas y sus parámetros, el esquema de MIMIC (tablas y columnas, sin
  valores) y el pedido. Variante `--muestra`: además, 3 valores de ejemplo por columna.
- Ejecución:
  - caso 3: el filtro del LLM se corre contra la base y **se extrae el subconjunto con `subconjunto_salud.py`** (C1m);
  - casos 2 y 1: el plan se compara con lo que ya se midió (B1m `consistentes`, A2m);
  - caso 4: se valida el plan (generar con MOSTLY lleva minutos y ya se midió en D2m).
- Script: `g1_orquestacion.py` (esta carpeta).

```bash
.venv/bin/python pruebas/salud/G1-orquestacion/g1_orquestacion.py                       # los 5 casos
.venv/bin/python pruebas/salud/G1-orquestacion/g1_orquestacion.py --muestra --casos 3   # con valores de ejemplo
```

## Casos y resultado

Los cinco casos de G1 sobre Pagila, adaptados a MIMIC. El pedido va textual.

| Caso | Pedido | Lo hizo bien si | Plan del LLM | Bien |
|---|---|---|---|---|
| 1 · Detectar | «¿Qué columnas de esta base tienen datos personales o datos de salud? Listalas con el tipo de dato de cada una.» | Plan = `detectar` | `detectar` (todas las tablas) | **3 de 3** |
| 2 · Anonimizar | «Anonimizá los identificadores de los pacientes y de los profesionales y las fechas. Las fechas de cada paciente tienen que seguir siendo coherentes entre sí (un alta no puede quedar antes del ingreso) y la base tiene que seguir cargando sin errores.» | `anonimizar` con ids seudonimizados y fechas desplazadas por paciente | `detectar` → `anonimizar` (seudonimizar, desplazar por paciente, edad y texto sin cambios) | **3 de 3** |
| 3 · Subconjunto | «Sacame un subconjunto con los pacientes que tuvieron sepsis y todo lo que dependa de ellos (internaciones, diagnósticos, laboratorios, UCI), sin romper las claves.» | Ancla `patients`; el filtro da los **17** pacientes con sepsis de la demo; el subconjunto carga con todas las FK | `subconjunto` → `anonimizar` (con `detectar` antes en 2 corridas); filtro con 0 pacientes | **0 de 3** |
| 4 · Sintetizar | «Generá una base sintética con el mismo esquema y unos 200 pacientes, con internaciones y diagnósticos coherentes entre sí.» | `sintetizar` ~200 pacientes con `patients`, `admissions`, `diagnoses_icd` | `subconjunto` → `sintetizar` (200 pacientes, de 6 a 9 tablas) | **3 de 3** |
| 5 · Ambiguo | «Prepará una copia de la base para que el equipo de testing la use sin ver datos reales.» | Combinación razonable y supuestos o preguntas explícitos | `detectar` → `anonimizar` (desplazar por paciente; edad por ruido o década; enmascarar texto libre); 3 supuestos y 3 preguntas | **3 de 3** |

Verdad del caso 3: pacientes con diagnóstico CIE-10 A40, A41 o R65.2, o CIE-9 038, 995.91, 995.92 o 785.52: **17 de
100**.

### El caso 3 en detalle

| Variante | Corrida | Filtro del LLM | Pacientes | Subconjunto con C1 |
|---|---|---|---|---|
| Esquema | 1 | `icd_code LIKE 'A41.%' OR icd_code LIKE 'R65.%'` | **0** | carga con todas las FK (solo catálogos) |
| Esquema | 2 y 3 | `icd_code LIKE '%Sepsis%'` | **0** | ídem |
| Esquema + 3 valores por columna | 1 y 2 | `icd_code LIKE '%Sepsis%' OR icd_code LIKE '%Septicemia%'` | **0** | ídem |
| Esquema + 3 valores por columna | 3 | ídem + `admission_location = 'SEPSIS'` | **0** | ídem |

Un filtro correcto tendría que unir con el catálogo: `subject_id in (select d.subject_id from diagnoses_icd d join
d_icd_diagnoses c using (icd_code, icd_version) where c.long_title ilike '%sepsis%' or ...)`, o usar los códigos sin
punto.

## Hallazgos

- **Elegir herramientas y opciones, bien; escribir SQL del dominio, mal.** El LLM sabe que para anonimizar una base
  clínica hay que desplazar las fechas por paciente, pero no sabe cómo se escriben los códigos CIE en MIMIC ni que la
  descripción está en otra tabla.
- **El peor error es el silencioso:** un subconjunto vacío que «carga perfecto». Ninguna herramienta de las etapas
  anteriores avisa, porque técnicamente no hay error. El orquestador tiene que verificar cantidades: comparar el
  resultado con lo que el usuario esperaba, o pedir confirmación.
- **Agrega pasos que nadie pidió:** anonimizar después del subconjunto, o un subconjunto antes de sintetizar.
  Razonables en un sistema de datos de prueba, pero tienen que quedar a la vista para que el usuario los confirme.
- **Mismo LLM, misma Mac, sin datos a terceros:** la orquestación entera es local.

## Limitaciones

- Cinco casos, tres corridas: es una prueba cualitativa, igual que G2 y G3.
- Las herramientas se describen con parámetros simplificados (por ejemplo, `fechas: desplazar_por_paciente`): el
  LLM no escribe las reglas de enmascaramiento, elige entre opciones.
- Los casos 1, 2 y 4 no se ejecutaron de nuevo: se comparan con lo ya medido en A2m, B1m y D2m.
- El LLM conoce MIMIC (A2m); aun así, no supo el formato de sus códigos.
- Los resultados de C1 del caso 3 (`resultados/c1_caso3_c*`) son los de la última corrida, con valores de ejemplo.
  Las dos variantes dieron 0 pacientes.

## Evidencia

- `resultados/g1m.json` (5 casos × 3 corridas) y `resultados/g1m_muestra.json` (caso 3 con valores de ejemplo).
- `resultados/crudo/`: el plan JSON de cada corrida.
- `resultados/c1_caso3_c*/`: manifiesto y conteos del subconjunto extraído con el filtro del LLM.
