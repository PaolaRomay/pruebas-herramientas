# Lista de referencia de MIMIC demo y Synthea: taxonomía, reglas y anotación

**Quién / cuándo:** propuesta armada por Claude Code a pedido de Jero, 2026-11-08. **Estado: congelada el 2026-11-08** (sección 6).

[← MIMIC demo](../mimic-demo.md) · [Synthea](../synthea.md)

La lista de referencia es **la verdad** contra la que se miden las herramientas de detección (función A). Por eso
**no se arma con esas herramientas** (Presidio, GLiNER, el LLM local, `anon.detect`): la medición quedaría circular.
Cada etiqueta sale de una **norma o documentación citada**, o de un **criterio del equipo** escrito en una regla.

## 1. Fuentes

| Código | Fuente | Qué dice |
|---|---|---|
| HIPAA-A … HIPAA-R | 45 CFR 164.514(b)(2), *Safe Harbor*: los 18 identificadores. La norma con la que se desidentificó MIMIC | A nombres · B subdivisiones geográficas menores que un estado (calle, ciudad, condado, código postal) · C todos los elementos de fechas salvo el año ligadas a una persona, y edades mayores de 89 · D–F teléfono, fax, correo · G SSN · H número de historia clínica · I número de beneficiario del plan de salud · J número de cuenta · K número de certificado o licencia · L vehículos · M identificadores de dispositivos · N URL · O IP · P biometría · Q fotos · R cualquier otro número, característica o código único |
| L18331-4D | Ley 18.331, art. 4, literal D | «Dato personal: información de cualquier tipo referida a personas físicas o jurídicas determinadas o determinables» |
| L18331-4E | Ley 18.331, art. 4, literal E | «Dato sensible: datos personales que revelen origen racial y étnico, preferencias políticas, convicciones religiosas o morales, afiliación sindical e informaciones referentes a la salud o a la vida sexual». Equivale al art. 9 del RGPD |
| DOC-MIMIC | Documentación de MIMIC-IV | Tablas `d_*` = definiciones; `comments` = texto libre desidentificado con «___» |
| DOC-SYNTHEA | Diccionario de datos de Synthea | Qué es cada tabla y columna; claves |
| DEC-1 … DEC-6 | **Decisiones del equipo** (2026-11-08) | Lo que ninguna norma resuelve; ver sección 4 |

## 2. Taxonomía

| Categoría | Qué es | Sensible | Fuente típica |
|---|---|---|---|
| `IDENT_DIRECTO` | Identifica a la persona por sí solo: nombre, documento, licencia, pasaporte, dirección, número de beneficiario, identificador de dispositivo | sí | HIPAA A, B, G, I, K, M |
| `IDENT_OPACO` | Identificador interno de un paciente o de un episodio suyo (`subject_id`, `hadm_id`, `patient`, `encounter`) | sí | HIPAA H, R |
| `IDENT_REGISTRO` | Id de una fila u orden (`labevent_id`, `poe_id`, `claimid`): llega al paciente solo a través de su `subject_id` | dudoso | DEC-2 |
| `IDENT_PROFESIONAL` | Id u otros datos del personal de salud (`provider_id`, `caregiver_id`). Su nombre es `IDENT_DIRECTO` | sí | DEC-3 |
| `CUASI_HIPAA` | Cuasi-identificador que HIPAA lista: fechas ligadas a la persona, geografía menor que un estado | sí | HIPAA B, C |
| `CUASI` | Cuasi-identificador que HIPAA no lista: sexo, estado civil, idioma, seguro (sí, DEC-4); edad ≤ 89, año y estado o provincia (dudoso: HIPAA los permite) | sí / dudoso | DEC-4 / HIPAA |
| `SENSIBLE` | Dato sensible: salud (diagnósticos, procedimientos, medicación, resultados, desenlace) u origen racial y étnico | sí | L18331-4E |
| `TEXTO_LIBRE` | Texto libre que puede contener cualquier dato personal | sí | DOC-MIMIC |
| `ECONOMICO` | Ingresos, gastos y cobertura del paciente (sí); costos y pagos de cada prestación (dudoso) | sí / dudoso | DEC-5 |
| `CATALOGO` | Tablas de definición, organizaciones, aseguradoras | no | DOC |
| `NO_EVALUABLE` | Columna vacía en toda la base: no hay qué detectar | dudoso (fuera de las métricas) | DEC-6 |
| `TECNICO` | Orden de filas, versiones de código, unidades, estados administrativos, referencias a catálogos | no | DEC-1 |

- **sí / no / dudoso** es el mismo formato que la lista de Pagila. Las «dudosas» no entran en las métricas de A
  (criterio de `comparar_deteccion.py`).
- **`entidad_esperada`** se completa solo donde hay una entidad de Presidio equivalente (`PERSON`, `US_SSN`,
  `US_DRIVER_LICENSE`, `US_PASSPORT`, `LOCATION`, `DATE_TIME`).

### Diferencias de criterio con la lista de Pagila (a tener en cuenta)

- En Pagila, ciudad, código postal y fechas eran «dudosos». Acá **siguen HIPAA**: son `CUASI_HIPAA`, «sí».
- En Pagila, las claves foráneas a direcciones eran «no». Acá, los ids de **paciente o episodio** son `IDENT_OPACO`,
  «sí» (HIPAA H y R), y los ids de filas son «dudosos».
- **Raza y etnia** son `SENSIBLE` por la Ley 18.331 (origen racial y étnico). Pagila no tenía esas columnas.

## 3. Archivos y cómo se regeneran

| Archivo | Qué es |
|---|---|
| `perfilar_columnas.py` → `perfil_<base>.csv` | Por columna: tipo, % de nulos, distintos, si es única, largo, PK o FK. Solo agregados |
| `reglas.csv` | Las reglas, editables. Cada una con categoría, sensible, entidad, fuente y nota. Gana la **primera** que coincide |
| `aplicar_reglas.py` → `propuesta_<base>.csv` | Aplica las reglas al perfil. Lo que no cubre ninguna regla queda `SIN_REGLA` |
| `anotacion.py` | `plantillas`: arma la muestra y una plantilla por persona; `acuerdo`: kappa y desacuerdos |

```bash
.venv/bin/python pruebas/_bases/referencia/perfilar_columnas.py --base mimic_demo --esquemas mimiciv_hosp,mimiciv_icu
.venv/bin/python pruebas/_bases/referencia/perfilar_columnas.py --base synthea_p100 --esquemas synthea
.venv/bin/python pruebas/_bases/referencia/aplicar_reglas.py perfil_mimic_demo.csv --base-reglas mimic
.venv/bin/python pruebas/_bases/referencia/aplicar_reglas.py perfil_synthea_p100.csv --base-reglas synthea
```

## 4. Decisiones del equipo (2026-11-08)

Las 165 columnas que ninguna norma resolvía salían de 14 reglas, agrupadas en 6 decisiones. Se decidieron reglas,
no columnas sueltas. En `reglas.csv` figuran con fuente `DEC-1` … `DEC-6`.

| Decisión | Qué cubre | Decidido |
|---|---|---|
| DEC-1 · Técnicas | Números de orden, versiones de código ICD, unidades, estados, referencias a catálogos | **no**: autonumerados y metadatos que no dicen nada de la persona |
| DEC-2 · Ids de registro | Ids de filas u órdenes (`labevent_id`, `poe_id`, `claimid`…) | **dudoso**: llegan al paciente solo vía su id; ninguna herramienta los distingue por valor |
| DEC-3 · Profesionales | Ids y datos del personal de salud (`provider_id`, `caregiver_id`, tabla `providers`) | **sí**: son datos personales (Ley 18.331, art. 4 D) aunque no sean del paciente. La referencia de `providers` a su organización es técnica (DEC-1) |
| DEC-4 · Demográficos fuera de HIPAA | Sexo, estado civil, idioma, seguro, prefijo y sufijo del nombre, relación con el titular del plan | **sí**: identifican en combinación; en una base sin nombres son lo único que identifica |
| DEC-5 · Económicos | Ingresos, gastos y cobertura del paciente / costos y pagos de cada prestación | **sí** los del paciente; **dudoso** los costos (precios de servicios, no identifican) |
| DEC-6 · Corrección | `claims_transactions.notes` / columnas vacías | `notes` no es texto libre (repite la descripción del procedimiento) → **sensible**. **Toda columna vacía en toda la base queda fuera** (`NO_EVALUABLE`), como `address2` en Pagila |

Quedan como estaban, por su fuente HIPAA: `anchor_age`, `anchor_year`, `anchor_year_group` (MIMIC) y `state`
(Synthea), en **dudoso**.

## 5. Resultado (después de las decisiones)

| | MIMIC demo (342) | Synthea p1000 (256) |
|---|---|---|
| sí | 247 | 159 |
| dudoso | 31 | 37 |
| no | 64 | 60 |
| De ellas, vacías (`NO_EVALUABLE`) | 4 | 11 |

- **MIMIC no tiene ningún `IDENT_DIRECTO`**: es lo esperable en una base ya desidentificada.
- **Synthea definitiva: 1 000 pacientes** (`synthea_p1000`, ver [synthea.md](../synthea.md)). Las 11 columnas vacías
  son las mismas con 100 y con 1 000 pacientes: Synthea no las llena nunca (por ejemplo `allergies.stop`,
  `claims.diagnosis8`, los datos de contacto de `payers`).

## 6. Congelamiento (2026-11-08)

**Decisión del equipo:** las reglas se dan por buenas y **no se hace la anotación manual a ciegas**. La lista sale
entera de reglas con fuente (normas, documentación y las decisiones DEC-1 a DEC-6).

| Archivo | Base | Columnas | sha256 |
|---|---|---|---|
| `data/columnas_sensibles_mimic.csv` | `mimic_demo` | 342 | `a7459d31b629be0b78d6a2941b2f1b1b7a84139a93e06ac3cc673bd808296f72` |
| `data/columnas_sensibles_synthea.csv` | `synthea_p1000` | 256 | `5c8d0a3d29070ca59ae8131bf84f40097416b086a44ae6782b6ceccbf0d9aa91` |

- **Formato:** compatible con `scripts/comparar_deteccion.py` (`tabla`, `columna`, `sensible` = si / no / dudoso,
  `categoria`, `comentario`). Agrega `entidad_esperada`, `esquema`, `regla` y `fuente`.
- **Regla de cambio:** a partir de ahora no se editan a mano. Si una regla cambia, se edita `reglas.csv`, se vuelve a
  aplicar, se recalcula el sha256 y se anota aquí con fecha y motivo.
- **Limitación a declarar en el informe:** no se midió el acuerdo entre anotadores (kappa). La lista está respaldada
  por reglas con fuente citada, no por anotación independiente. `anotacion.py` queda disponible por si después se
  quiere medir con una muestra de 65 columnas.
