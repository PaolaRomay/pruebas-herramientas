# MIMIC-IV demo en PostgreSQL

**Quién / cuándo:** Jero (ejecutado por Claude Code a pedido de Jero), 2026-11-08.
**Fuente de cada dato:** P = prueba propia, salvo donde dice D.

[← Estado de las pruebas](../ESTADO.md) · [Synthea](synthea.md)

Segunda ronda de pruebas: una base de salud, más sensible y más grande que Pagila. Se usa la **demo abierta** de
MIMIC-IV porque no hay credenciales de PhysioNet para la base completa (decisión del 2026-11-07). Se combina con
[Synthea](synthea.md), que aporta lo que la demo no tiene: volumen de personas y datos personales directos.

## Qué es y cómo se accede

- **MIMIC-IV** (D): historias clínicas desidentificadas de pacientes del Beth Israel Deaconess Medical Center
  (Boston). La base completa y las notas clínicas (MIMIC-IV-Note) exigen credenciales de PhysioNet (curso CITI
  «Data or Specimens Only Research» y referencia de la supervisora) y firmar un acuerdo de uso (DUA) por módulo.
- **El DUA prohíbe compartir los datos con terceros** (D). La guía de PhysioNet de 2025 pide no usar servicios de LLM
  en la nube salvo que se verifique retención cero, y recomienda modelos locales. Si algún día se usa la completa,
  ni el repo ni asistentes en la nube pueden ver filas.
- **Demo 2.2** (D): 100 pacientes, mismo esquema, sin notas clínicas, licencia abierta **ODbL**. Esta es la que se usa.

## Descarga

- De `https://physionet.org/files/mimic-iv-demo/2.2/` (sin usuario), a `data/mimic/demo/`. La carpeta está en
  `.gitignore`: los datos no van al repo.
- **34 archivos, los 34 con su sha256 correcto** según `SHA256SUMS.txt` de PhysioNet. 18 MB comprimidos.

## Carga

```bash
scripts/cargar_mimic_demo.sh    # borra y recrea la base mimic_demo en pagila-db
```

- Usa los scripts oficiales de [MIT-LCP/mimic-code](https://github.com/MIT-LCP/mimic-code)
  (`mimic-iv/buildmimic/postgres`, commit `303d26c`, 2026-09-01), clonado fuera del repo en
  `../herramientas-externas/mimic-code`: `create.sql` → `load_gz.sql` → `constraint.sql` → `index.sql` →
  `validate_demo.sql`.
- PostgreSQL 16.4 (el contenedor común). Cada paso tardó 1 s o menos.
- **Validación oficial: 28 de 28 tablas «PASSED»** con los conteos esperados de la demo (`validate_demo.sql`
  no cubre `caregiver`, `ingredientevents` ni `provider`).
- Base `mimic_demo`: **201 MB**, esquemas `mimiciv_hosp` (22 tablas) e `mimiciv_icu` (9 tablas).

| | Pagila | MIMIC-IV demo |
|---|---|---|
| Tablas | 15 | 31 |
| Filas | 121 209 | ≈ 1,4 millones |
| Personas | 999 clientes | **100 pacientes** (275 internaciones, 140 estadías en UCI) |
| Tablas más grandes | `rental` 51 805 | `chartevents` 668 862; `d_icd_diagnoses` 109 775; `labevents` 107 727 |

## Desidentificación (ya viene hecha)

Comprobado en los datos de la demo:
- **Sin nombres ni datos de contacto.** `patients` tiene solo `subject_id`, `gender`, `anchor_age`, `anchor_year`,
  `anchor_year_group` y `dod`. Los profesionales tienen ids opacos (`provider_id`).
- **Fechas corridas al futuro,** de forma consistente dentro de cada paciente: internaciones entre 2110 y 2201. El
  período real solo se conoce en grupos de 3 años (`anchor_year_group`: 2011–2013, 2014–2016).
- **Edades topeadas:** `anchor_age` va de 21 a 91; los mayores de 89 aparecen agrupados.
- **Texto libre redactado con «___»:** 9 163 filas de `labevents`, 380 de `emar_detail` y 352 de
  `microbiologyevents`.
- Quedan cuasi-identificadores: `race` (14 valores), `marital_status` (5), `insurance` (3), `language` (2), sexo,
  edad y fechas relativas.

**Consecuencia:** en MIMIC la detección mide cuasi-identificadores, identificadores opacos y datos de salud, no
nombres. Las pruebas se hacen sobre datos que **ya pasaron** por una desidentificación: hay que decirlo en cada ficha.

## Claves y relaciones

`constraint.sql` declara **24 PK y 51 FK**. Con `pruebas/_bases/relaciones_mimic.py` se buscaron las relaciones que
existen por nombre de columna y se verificaron contra los datos (`evidencia/mimic-demo/relaciones.csv`; solo
conteos):

- **27 relaciones no declaradas**: 25 por nombre de columna, más las 2 compuestas de códigos ICD
  (`diagnoses_icd` y `procedures_icd` → catálogos, por `icd_code` + `icd_version`).
- **22 se cumplen sin huérfanas.** Entre ellas:
  - `labevents.hadm_id` y `transfers.hadm_id` → `admissions`;
  - todas las de `ingredientevents` (la tabla no tiene ninguna FK declarada);
  - `caregiver_id` en las 6 tablas de eventos de UCI;
  - `*_provider_id` en 7 columnas;
  - `omr.subject_id`.
- **5 no se cumplen en la demo:**
  - `emar.poe_id` → `poe`: 1 063 de 35 835;
  - `emar_detail.pharmacy_id` → `pharmacy`: 769 de 34 788;
  - `emar.pharmacy_id` → `pharmacy`: 559 de 29 372;
  - `pharmacy.poe_id` → `poe`: 19 de 15 220;
  - `prescriptions.poe_id` → `poe`: 19 de 17 969.

  Puede ser propio de cómo se recortó la demo; con la completa no se puede comprobar.
- **7 tablas sin clave primaria:** `drgcodes`, `emar_detail`, `omr`, `provider`, `caregiver`, `ingredientevents` y
  **`chartevents`** (la más grande). Ojo: el script propio de subconjuntos (C1) **exige PK en todas las tablas**.

Comparado con Pagila (49 de 55 particiones sin FK y una relación lógica sin declarar), MIMIC tiene muchas más
relaciones implícitas, y algunas no se cumplen del todo: un caso más realista para F2 (proponer relaciones y
confirmarlas).

Pruebas de F2 sobre esta base (2026-11-12 y 2026-11-13): el [LLM local](../salud/F2-relaciones-llm/ficha.md)
encuentra 5 de las 25; [SchemaSpy y Metanome](../salud/F2-relaciones-herramientas/ficha.md) encuentran 10 de 25 y 20
de 25 (las 20 que se cumplen). Metanome además encontró 2 relaciones reales que esta lista no tenía
(`poe.discontinued_by_poe_id → poe.poe_id` y `procedureevents.linkorderid → procedureevents.orderid`).

## Evidencia

- `evidencia/mimic-demo/`: `versiones.txt`, `tiempos.csv`, un log por paso de la carga
  (`1_create.log` … `5_validate.log`) y `relaciones.csv`.
