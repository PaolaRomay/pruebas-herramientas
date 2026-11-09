# A5m / A5s — `anon.detect` (PostgreSQL Anonymizer) sobre MIMIC-IV demo y Synthea — Detectar

**Quién / cuándo:** Jero (ejecutado por Claude Code a pedido de Jero), 2026-11-09.
**Fuente de cada dato:** P = prueba propia, salvo donde dice D.

[← Base MIMIC](../../_bases/mimic-demo.md) · [Base Synthea](../../_bases/synthea.md) ·
[Lista de referencia](../../_bases/referencia/taxonomia.md) · [A2m / A2s LLM local](../A2-llm-local/ficha.md)

## Qué es

- **`anon.detect(idioma)`** (D: código de la función en la extensión 3.3.2) es la detección que trae PostgreSQL
  Anonymizer para proponer reglas de enmascaramiento.
- **No mira valores.** Compara el nombre de cada columna, en minúscula y **con coincidencia exacta**, contra un
  diccionario de nombres típicos (`anon.identifier`). Cada nombre tiene una categoría (`anon.identifiers_category`) y
  la marca de si es identificador directo.
- Diccionario en inglés (`en_US`): **78 nombres**, por ejemplo `first_name`, `firstname`, `last_name`, `email`,
  `phone`, `address`, `city`, `zipcode`, `birth`, `date_birth`, `social_security`, `patient_id`, `insurance`,
  `gender`, `language`. Hay otro en francés (94). El usuario puede agregar nombres propios.

## En pocas palabras

- **Detecta casi nada:** 3 de 247 sensibles en MIMIC y 7 de 159 en Synthea. F1 **0,02** y **0,08**.
- **En MIMIC**, solo `admissions.insurance`, `admissions.language` y `patients.gender`. Ninguna fecha, ningún id
  (`subject_id` y `hadm_id` no están en el diccionario; `patient_id`, sí) y ningún dato de salud.
- **En Synthea** no reconoce los nombres de los pacientes (las columnas se llaman `first`, `last`, `maiden`), ni el
  SSN (`ssn`), ni la fecha de nacimiento (`birthdate`): el diccionario tiene `firstname`, `social_security` y
  `date_birth`, y la coincidencia es exacta. Sí marca dirección, ciudad y sexo, pero también los de hospitales y
  aseguradoras (5 falsos positivos).
- **Es lo esperado:** un diccionario de nombres «de manual» no sirve para esquemas reales. Confirma con datos lo
  que se vio en Pagila y justifica el LLM (A2).

## Entorno

- Imagen `registry.gitlab.com/dalibo/postgresql_anonymizer:stable`, digest
  `sha256:379c4c88a5987dbf282e0b383a8f9fdcd9eeae224baca62c44e4129894f46ce1` (creada el 2026-10-28):
  **PostgreSQL Anonymizer 3.3.2 sobre PostgreSQL 18.6**. Solo existe para amd64: en la Mac corre emulada.
- **Contenedor propio, `salud-anon`** (puerto 55434), aparte del servicio `anon` del `docker-compose.yml` (base común,
  pensado para B1 sobre Pagila), que no se toca.
- **Solo el esquema, sin filas:** `pg_dump --schema-only` de `mimic_demo` y `synthea_p1000` desde `pagila-db`,
  restaurado en el contenedor, y `select anon.init()` para cargar el diccionario. Como `anon.detect` solo lee el
  catálogo, el resultado es el mismo que con los datos.
- Script: `a5_anon_detect_salud.py` (esta carpeta; los comandos para preparar el contenedor están en su docstring).
  Métricas: `pruebas/salud/comparar_salud.py`.

```bash
.venv/bin/python pruebas/salud/A5-anon-detect/a5_anon_detect_salud.py --base mimic   # y synthea
.venv/bin/python pruebas/salud/comparar_salud.py --base mimic                        # y synthea
```

Variantes: `en_US` (cualquier categoría del diccionario) y `en_US_directos` (solo las que el diccionario considera
identificador directo). Determinista: una corrida. `anon.detect` tarda 0,2 s.

## Qué se midió y resultado

| Base | Variante | TP | FP | FN | TN | Precisión | Recall | F1 | Etiqueta |
|---|---|---|---|---|---|---|---|---|---|
| MIMIC | `en_US` | 3 | 0 | 244 | 64 | 1,00 | 0,01 | **0,02** | 0/45 |
| MIMIC | `en_US_directos` | 1 | 0 | 246 | 64 | 1,00 | 0,00 | 0,01 | 0/45 |
| Synthea | `en_US` | 7 | 5 | 152 | 55 | 0,58 | 0,04 | **0,08** | 3/41 |
| Synthea | `en_US_directos` | 5 | 5 | 154 | 55 | 0,50 | 0,03 | 0,06 | 3/41 |
| *MIMIC* | *LLM `a2b` (A2m)* | *199* | *6* | *48* | *58* | *0,97* | *0,81* | *0,88* | *45/45* |
| *Synthea* | *LLM `a2b` (A2s)* | *135* | *14* | *24* | *46* | *0,91* | *0,85* | *0,88* | *41/41* |

### Columnas detectadas

| Base | Columna | Categoría del diccionario | Directo | En la lista |
|---|---|---|---|---|
| MIMIC | `admissions.insurance` | `health_plan_id` | sí | sensible |
| MIMIC | `admissions.language` | `lang` | no | sensible |
| MIMIC | `patients.gender` | `gender` | no | sensible |
| Synthea | `patients.address`, `patients.city` | `street_address`, `city` | sí | sensibles |
| Synthea | `patients.gender`, `providers.gender` | `gender` | no | sensibles |
| Synthea | `providers.name`, `providers.address`, `providers.city` | `name`, `street_address`, `city` | sí | sensibles (profesional) |
| Synthea | `organizations.name`, `.address`, `.city`, `.phone` | `name`, `street_address`, `city`, `phone_number` | sí | **no sensibles** (catálogo) |
| Synthea | `payers.name` | `name` | sí | **no sensible** (catálogo) |
| Synthea | `payers.address`, `payers.city`, `payers.phone` | ídem | sí | dudosas (vacías) |

`insurance` como «identificador del plan de salud» es una etiqueta equivocada: la columna dice el tipo de seguro
(Medicare, Medicaid…), no un número.

## Hallazgos

- **La coincidencia exacta de nombres es la mayor debilidad:** `first` no es `firstname`, `ssn` no es
  `social_security`, `birthdate` no es `date_birth`, `subject_id` no es `patient_id`. Bastaría con agregar esos
  nombres al diccionario, pero eso es hacer a mano la lista que la herramienta debería encontrar.
- **No sabe de tablas:** marca igual el nombre de un paciente y el de una aseguradora.
- **No tiene categorías de salud:** el diccionario no tiene nada para diagnósticos, medicamentos o resultados, que
  son la mayoría de las sensibles en estas bases.
- **Utilidad real en el sistema:** ninguna como detector. PostgreSQL Anonymizer sigue siendo candidato para
  **aplicar** el enmascaramiento (función B), con las reglas que proponga el LLM.

## Limitaciones

- Solo el diccionario que viene con la extensión, sin agregados propios (es el comportamiento «de fábrica»).
- La lista de referencia sale de reglas, sin anotación manual independiente (ver `taxonomia.md`).

## Evidencia

- `resultados/<base>/a5<m|s>_columnas.csv` y `a5<m|s>_corrida.md` (versión, imagen y columnas detectadas).
- `resultados_comparados/salud/<base>/`: métricas, matriz por columna y resumen.
