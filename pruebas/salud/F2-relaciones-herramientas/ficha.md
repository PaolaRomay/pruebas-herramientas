# F2m (herramientas) — SchemaSpy y Metanome descubren relaciones en MIMIC-IV demo — Entender el esquema

**Quién / cuándo:** Jero (ejecutado por Claude Code a pedido de Jero), 2026-11-13.
**Fuente de cada dato:** P = prueba propia, salvo donde dice D.

[← F2m LLM local](../F2-relaciones-llm/ficha.md) · [Ficha de SchemaSpy](../../_herramientas/schemaspy.md) ·
[Ficha de Metanome](../../_herramientas/metanome.md) · [C1m subconjunto](../C1-subconjunto/ficha.md) ·
[Base MIMIC](../../_bases/mimic-demo.md)

Funcionalidad F2 del sistema (relaciones no declaradas). La demo de MIMIC tiene **51 FK declaradas** y **25
relaciones que existen pero no están declaradas**. Sin ellas, el subconjunto de C1m deja 20 relaciones rotas.
¿Qué encuentran dos herramientas de código abierto que hacen esto, frente al LLM local?

## En pocas palabras

- **Metanome (BINDER o SPIDER) + dos filtros simples es lo mejor:**
  - encuentra las **20 de 20** relaciones no declaradas que se cumplen en los datos y 50 de las 51 declaradas;
  - con solo 3 propuestas fuera de la lista, de las que 2 son relaciones reales que la lista no tenía;
  - en 5 a 9 segundos.
- **Metanome solo da demasiado:** 2 349 dependencias de inclusión (todas ciertas en los datos, casi todas sin
  sentido, como `hospital_expire_flag ⊆ dosis`). Los filtros son los que la vuelven útil:
  - la columna padre es única y sin nulos (puede ser clave);
  - el nombre de la hija termina en el de la padre.
- **No ve las 5 relaciones con huérfanas** (por ejemplo `emar.poe_id → poe`): busca inclusiones exactas, y una
  sola fila sin padre la descarta.
- **SchemaSpy encuentra 10 de 25**, solo por nombre, sin mirar los datos:
  - acierta las 5 con huérfanas que Metanome no ve;
  - pero no ve las de tablas sin clave primaria (`caregiver`, `provider`), ni las que cruzan esquemas
    (`mimiciv_icu` → `mimiciv_hosp`), ni nombres distintos (`order_provider_id → provider_id`);
  - propone 5 falsas (`spec_itemid → d_labitems.itemid`).
- **El LLM local (F2m):** 5 de 25.
- **Conclusión para el sistema:** Metanome como base (inclusiones en los datos), filtrado por unicidad y nombre, más
  SchemaSpy o reglas de nombre para las relaciones «casi ciertas» con huérfanas, y revisión humana.

## Entorno

- Equipo: Mac M5 Pro, 16 GB, macOS 26.6.2. Las dos herramientas en Java, en Docker (sin instalar Java en la Mac).
- **SchemaSpy 7.0.2** (LGPL-3.0), imagen oficial `schemaspy/schemaspy:7.0.2`
  (`sha256:c8f98116…79b7`, arm64), contra `mimic_demo` en `pagila-db`, esquemas `mimiciv_hosp` y `mimiciv_icu`.
- **Metanome** (Apache-2.0), con:
  - **Metanome CLI 1.1.0** (`metanome-cli-1.1.0.jar`, Apache-2.0, GitHub `sekruse/metanome-cli`; sha256
    `55feccf2…be97`);
  - **BINDERFile 0.0.2** y **SPIDERFile 0.0.2** (jar publicados por HPI; sha256 `25cb2487…6011` y `3345aa33…d1d7`);
    algoritmos de dependencias de inclusión unarias;
  - Java 21 (`eclipse-temurin:21-jre`); los jar se compilaron con Java 8 y corren igual.
  - Entrada: las 31 tablas exportadas a CSV (129 MB, en `salidas_grandes/`, fuera del repo).
- Jar y CSV fuera del repo (`../herramientas-externas/metanome/`, `salidas_grandes/`).
- Script de comparación: `f2_herramientas.py` (esta carpeta).

```bash
# SchemaSpy
docker run --rm -v "$PWD/salidas_grandes/schemaspy":/output schemaspy/schemaspy:7.0.2 -t pgsql11 \
  -host host.docker.internal -port 55432 -db mimic_demo -u postgres -p postgres -schemas mimiciv_hosp,mimiciv_icu
# Metanome (BINDER; SPIDER igual con su jar y su clase)
docker run --rm -v ../herramientas-externas/metanome:/m:ro -v "$PWD/salidas_grandes":/w -w /w eclipse-temurin:21-jre \
  java -Xmx4g -cp /m/metanome-cli-1.1.0.jar:/m/BINDERFile-0.0.2-SNAPSHOT.jar de.metanome.cli.App \
  --algorithm de.metanome.algorithms.binder.BINDERFile.BINDERFile --files load:archivos.txt \
  --file-key INPUT_GENERATOR --separator , --header --algorithm-config TEMP_FOLDER_PATH:/w/tmp -o file:binder
# Comparación
.venv/bin/python pruebas/salud/F2-relaciones-herramientas/f2_herramientas.py
```

### Problemas en el camino (Metanome)

- **No hay una versión lista para usar** de la plataforma: se usó la línea de comandos de un autor de HPI y los jar
  de los algoritmos que publica HPI (de 2015).
- **El nombre del parámetro de entrada** (`INPUT_GENERATOR`) no está documentado: se sacó de las clases del jar.
- **Versiones de interfaz distintas:** pasarle un parámetro booleano (`DETECT_NARY`) falla con `AbstractMethodError`,
  porque el jar del algoritmo usa una interfaz más vieja que la línea de comandos. Se corrió sin ese parámetro
  (detecta solo dependencias unarias, que son las que interesan para FK de una columna).
- **El nombre de la tabla se corta en el primer punto del archivo:** `mimiciv_hosp.admissions.csv` quedaba como
  tabla `mimiciv_hosp`. Se renombraron los archivos a `mimiciv_hosp__admissions.csv`.

## Qué hace cada una

- **SchemaSpy** (D): documenta una base (HTML, diagramas, XML) leyendo el catálogo. Además de las FK declaradas,
  propone **relaciones implícitas**: una columna cuyo nombre y tipo coinciden con la **clave primaria** de otra
  tabla. No mira los datos. Trabaja **un esquema por vez**.
- **Metanome** (D): plataforma de **perfilado de datos** de HPI. Sus algoritmos BINDER y SPIDER descubren
  **dependencias de inclusión** (IND): pares de columnas A ⊆ B donde todos los valores de A aparecen en B. Toda FK
  cumplida es una IND, pero no toda IND es una FK. No mira los nombres.

## Resultados

Verdad: 51 FK declaradas y 25 no declaradas (20 se cumplen en los datos; 5 tienen huérfanas en el origen).

| Herramienta | Propuestas | FK declaradas | No declaradas | … de las que se cumplen | Fuera de la lista | Precisión | Tiempo |
|---|---|---|---|---|---|---|---|
| SchemaSpy (relaciones implícitas) | 15 | — (las lee del catálogo) | 10 de 25 | 5 de 20 | 5 | 0,67 | 9 s (con el HTML) |
| Metanome, todas las IND | 2 349 | 51 de 51 | 20 de 25 | **20 de 20** | 2 278 | 0,03 | 5 s (BINDER), 9 s (SPIDER) |
| Metanome + padre único | 115 | 51 de 51 | 20 de 25 | 20 de 20 | 44 | 0,62 | + 1 s |
| **Metanome + padre único + nombre** | **73** | **50 de 51** | **20 de 25** | **20 de 20** | **3** | **0,96** | + 1 s |
| LLM local (F2m, corrida 1) | 11 | — | 5 de 25 | 2 de 20 | 6 | 0,45 | 75 s |

- BINDER y SPIDER dan **exactamente las mismas** 2 349 IND (cambia solo el algoritmo).
- «Padre único»: la columna referenciada no tiene nulos ni repetidos. «Nombre»: el nombre de la hija es igual al de
  la padre o termina en él.
- La FK declarada que pierde el filtro de nombre: `hcpcsevents.hcpcs_cd → d_hcpcs.code` (nombres distintos).

### Qué se le escapa a cada una

| Relaciones no declaradas | SchemaSpy | Metanome + filtros | LLM |
|---|---|---|---|
| 6 × `caregiver_id → caregiver` (tabla sin PK) | ✗ | ✓ | ✗ |
| 5 × `*_provider_id → provider` (tabla sin PK, nombres distintos) | ✗ | ✓ | 1 de 5 |
| `ingredientevents` → `patients`, `admissions` (cruzan esquemas) | ✗ | ✓ | ✗ |
| `labevents`, `transfers`, `omr` → `admissions`, `patients`; `ingredientevents` → `icustays`, `d_items` | ✓ | ✓ | ✗ |
| `prescriptions.pharmacy_id → pharmacy` | ✗ | ✓ | ✗ |
| 5 con huérfanas (`emar.poe_id`, `emar.pharmacy_id`, `pharmacy.poe_id`…) | ✓ | ✗ | 3 de 5 |

### Propuestas fuera de la lista

- **Metanome + filtros (3):**
  - `poe.discontinued_by_poe_id → poe.poe_id` y `procedureevents.linkorderid → procedureevents.orderid`:
    **relaciones reales dentro de la misma tabla**, que la lista no tenía (la segunda también la propuso el LLM);
  - `icustays.intime → transfers.intime`: coincidencia (cada ingreso a UCI es también un traslado), no una FK.
- **SchemaSpy (5):** `microbiologyevents.spec_itemid`, `test_itemid`, `org_itemid` y `ab_itemid → d_labitems.itemid`
  (por el sufijo `itemid`, pero son códigos de otro catálogo) e `ingredientevents.orderid → procedureevents.orderid`.
- **Metanome sin filtros:** ejemplos de IND ciertas y sin sentido: `admissions.hospital_expire_flag ⊆
  labevents.valuenum` (0 y 1 aparecen entre los valores de laboratorio), `diagnoses_icd.seq_num ⊆
  labevents.labevent_id`.

## Hallazgos

- **Las dos señales se complementan:** los datos (Metanome) encuentran lo que los nombres no dicen (tablas sin PK,
  nombres distintos, otro esquema) y los nombres (SchemaSpy) encuentran lo que los datos no confirman del todo
  (relaciones con algunas huérfanas).
- **Una IND no es una relación:** sin filtros, el 97 % de lo que devuelve Metanome es ruido. Los dos filtros que se
  usaron son triviales y bajan de 2 349 a 73 propuestas, con 70 correctas.
- **SchemaSpy depende de que el catálogo esté bien:** si la tabla padre no tiene PK (como `caregiver` y `provider`
  en MIMIC) no infiere nada. Justamente las bases con relaciones sin declarar suelen tener también PK sin declarar.
- **Mi script de la etapa 1 (`relaciones_mimic.py`)** hacía lo mismo que «nombre + datos», pero con reglas de nombre
  escritas a mano para MIMIC. Metanome + filtros llega al mismo resultado (20 de 20) **sin conocer el esquema**, y
  además encontró 2 relaciones que esas reglas no tenían.
- **Escala:** 1,4 millones de filas en 5 a 9 s. Para la MIMIC completa, BINDER está pensado para no entrar en
  memoria (D: particiona a disco); queda por medir.

## Limitaciones

- La verdad de las no declaradas salió de reglas de nombre (etapa 1); las 2 relaciones nuevas muestran que no está
  completa.
- Solo dependencias unarias (una columna). Relaciones de varias columnas (`icd_code` + `icd_version` →
  `d_icd_diagnoses`) no se buscaron: el parámetro para activarlas falla con estos jar.
- Los jar de Metanome son de 2015; el proyecto tiene poca actividad.
- SchemaSpy se corrió con sus opciones por defecto (no se probó `-schemas` con análisis entre esquemas ni sus
  opciones de metadatos extra).

## Evidencia

- `resultados/f2_herramientas.json` (por herramienta: propuestas, aciertos, no encontradas y ejemplos fuera de la
  lista) y `resultados/f2_herramientas.md`.
- Fuera del repo (`salidas_grandes/`): el sitio HTML y los XML de SchemaSpy, las IND de BINDER y SPIDER y los CSV.
