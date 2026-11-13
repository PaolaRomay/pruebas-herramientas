# C1m / C1s — Subconjunto coherente de MIMIC-IV demo y Synthea con el script propio — Extraer subconjuntos

**Quién / cuándo:** Jero (escrito y corrido por Claude Code a pedido de Jero), 2026-11-09.
**Fuente de cada dato:** todo es P (prueba propia).

[← Base MIMIC](../../_bases/mimic-demo.md) · [Base Synthea](../../_bases/synthea.md) ·
[C1 script propio sobre Pagila](../../C1-script-propio/ficha.md) · [C1 Condenser](../../C1-condenser/ficha.md)

Segunda ronda de C1: el script propio que en Pagila dio 0 violaciones, ahora sobre dos bases de salud más grandes,
con tablas sin clave primaria y con relaciones que el catálogo no declara.

## En pocas palabras

- **Funciona en las dos bases con un cambio:** las tablas sin clave primaria (7 en MIMIC, entre ellas
  `chartevents`, la más grande; 10 en Synthea, entre ellas `observations`) se manejan por `ctid`. El prototipo de
  Pagila se cortaba con ellas.
- **Integridad:**
  - las 51 FK del catálogo de MIMIC y las 40 de Synthea se vuelven a crear en el destino sin errores;
  - de las **25 relaciones no declaradas** de MIMIC, las 20 que se cumplen en el origen quedan con **0 huérfanas**;
  - las 5 que ya tenían huérfanas en el origen (por ejemplo `emar.poe_id`) conservan algunas, siempre heredadas del
    origen, nunca creadas por la extracción.
- **Pacientes de control separados antes de extraer:** 16 de 100 en MIMIC y 226 de 1 151 en Synthea (alrededor del
  20 %); **ninguno entra a ningún subconjunto**.
- **Rápido y liviano:** entre 2 y 7 segundos, menos de 100 MB de memoria del proceso. **`chartevents` y `labevents`
  no lo vuelven inviable** en la demo: con el 50 % de los pacientes, 287 000 filas de `chartevents` en 7 s.
- **Cierre en 2 rondas** (en Pagila, 9): no hay ciclos. Ninguna fila del ancla entra fuera del filtro.
- **Reproducible:** dos corridas dan contenido idéntico (huella md5 de todas las tablas).
- **Límite para la MIMIC completa:** la copia arma cada tabla en memoria. Unos 150 MB por millón de filas de
  `chartevents`: con el 1 % de la completa entra en 16 GB; con el 10 %, no. Habría que pasar a copia en flujo.

## Entorno

- Equipo: Mac M5 Pro, 16 GB, macOS 26.6.2. Python 3.11.16 (`psycopg2-binary`), PostgreSQL 16.4 (`pagila-db`).
- Orígenes: `mimic_demo` (100 pacientes, 31 tablas, 1,4 millones de filas) y `synthea_p1000` (1 151 personas, 18
  tablas, 2,4 millones de filas).
- Script: `subconjunto_salud.py` (esta carpeta). Parte de `pruebas/C1-script-propio/subconjunto.py`, que no se toca.
- Configuraciones: `mimic_c1_10.json`, `mimic_c1_50.json`, `synthea_c1_1.json`, `synthea_c1_10.json`.

```bash
.venv/bin/python pruebas/salud/C1-subconjunto/subconjunto_salud.py pruebas/salud/C1-subconjunto/mimic_c1_10.json
```

### Qué cambia respecto del script de Pagila

- **Tablas sin clave primaria:** las filas se identifican por `ctid`, su posición física. Es estable porque todo
  (selección y copia) pasa en una única transacción `REPEATABLE READ` y el origen no se modifica.
- **Relaciones extra desde un CSV:** las no declaradas que encontró la etapa 1
  (`pruebas/_bases/evidencia/mimic-demo/relaciones.csv`), 25 en total. Synthea no tiene: el cargador declaró
  todas.
- **Pacientes de control:** un filtro (`hashtext('control' || id) % 5 = 0`) los separa; el filtro del ancla los
  excluye y el manifiesto verifica que ninguno entró.
- **Mediciones de escala:** tiempo por fase, memoria máxima del proceso, tamaño de las tablas de trabajo, bytes
  temporales que escribió PostgreSQL, mayor tabla copiada y tamaño de la base destino.
- **Integridad de las no declaradas:** cuenta huérfanas en el destino y las compara con el origen.

### Configuración

- **Ancla:** `patients`. Filtro determinista: `hashtext('c1' || id) % N = 0`, sin los de control. Los
  subconjuntos son anidados (el del 10 % está dentro del del 50 %).
- **Porcentajes:** el plan pedía 1 % y 10 % de la MIMIC completa. En la demo, el 1 % sería 1 paciente; se usan
  **10 % y 50 %**. En Synthea, **1 % y 10 %**.
- **MIMIC, catálogos copiados enteros:** `d_icd_diagnoses`, `d_icd_procedures`, `d_hcpcs`, `d_labitems`, `d_items`
  (284 000 filas), para que todos los códigos se puedan resolver. En Synthea no hay catálogos: organizaciones,
  aseguradoras y profesionales entran solo si alguien los referencia.

## Resultados

| Extracción | Pacientes | Filas | % de filas | Filas sin catálogos | Tiempo | Memoria | Base destino |
|---|---|---|---|---|---|---|---|
| MIMIC 10 % | 9 de 100 | 374 349 | 26,8 % | 84 481 (7,6 %) | 4,3 s | 63 MB | 77 MB |
| MIMIC 50 % | 47 de 100 | 732 996 | 52,4 % | 443 128 (40,0 %) | 7,4 s | 96 MB | 124 MB |
| Synthea 1 % | 12 de 1 151 | 10 995 | 0,5 % | — | 2,4 s | 47 MB | 13 MB |
| Synthea 10 % | 85 de 1 151 | 102 558 | 4,2 % | — | 4,9 s | 70 MB | 50 MB |

- En MIMIC, el «% de filas» incluye los catálogos enteros. Sin ellos, la proporción de filas sigue a la de
  pacientes.
- En Synthea, el 7,4 % de los pacientes arrastra el 4,2 % de las filas porque los elegidos tienen menos historia
  que el promedio. Lo mismo pasa en el origen: sus observaciones son el 4,1 % del total.

### Tablas grandes

| Extracción | `chartevents` | `labevents` | `observations` | `claims_transactions` |
|---|---|---|---|---|
| MIMIC 10 % | 54 577 de 668 862 | 7 905 de 107 727 | — | — |
| MIMIC 50 % | 286 989 | 48 042 | — | — |
| Synthea 1 % | — | — | 4 009 de 871 564 | 4 370 de 942 067 |
| Synthea 10 % | — | — | 35 816 | 41 891 |

### Tiempo por fase y escala

| Extracción | Selección | Esquema (pre) | Copia | Índices y FK (post) | Tablas de trabajo | Temporales de PostgreSQL | Mayor tabla copiada |
|---|---|---|---|---|---|---|---|
| MIMIC 10 % | 2,0 s | 0,2 s | 0,6 s | 0,8 s | 32 MB | 0 | 8 MB |
| MIMIC 50 % | 4,6 s | 0,2 s | 1,3 s | 1,0 s | 78 MB | 198 MB | 27 MB |
| Synthea 1 % | 1,7 s | 0,2 s | 0,1 s | 0,1 s | 3 MB | 0 | 2 MB |
| Synthea 10 % | 3,5 s | 0,2 s | 0,6 s | 0,2 s | 22 MB | 0 | 18 MB |

La selección domina, y dentro de ella los joins por `ctid` sobre `chartevents`. Con el 50 %, PostgreSQL escribió
198 MB a disco para ordenar (`DISTINCT` sobre muchas filas).

### Integridad

- **FK del catálogo:** se vuelven a crear en el destino con `ON_ERROR_STOP` (51 en MIMIC, 40 en Synthea). Si alguna
  fila violara una FK, la carga fallaba: no falló en ninguna extracción.
- **Relaciones no declaradas de MIMIC (25):**

| Relación | Huérfanas en el origen | Destino 10 % | Destino 50 % |
|---|---|---|---|
| Las 20 que se cumplen en el origen (proveedores, cuidadores, `labevents.hadm_id`, `omr.subject_id`…) | 0 | 0 | 0 |
| `emar.poe_id → poe` | 1 063 | 124 | 143 |
| `emar.pharmacy_id → pharmacy` | 559 | 28 | 28 |
| `emar_detail.pharmacy_id → pharmacy` | 769 | 28 | 28 |
| `pharmacy.poe_id → poe` | 19 | 0 | 16 |
| `prescriptions.poe_id → poe` | 19 | 0 | 16 |

Las huérfanas del destino son filas que ya eran huérfanas en el origen. No puede ser de otra forma: si el padre
existiera en el origen, el cierre lo habría traído.

- **Pacientes de control en el subconjunto:** 0 en las cuatro.
- **Secuencias:** ninguna tabla de estas bases usa secuencias.

### Reproducibilidad

`mimic_c1_10` y `synthea_c1_10`, extraídas dos veces: la huella (md5 del contenido ordenado de cada tabla) es
idéntica. El orden físico de las filas puede cambiar; el contenido, no.

## Hallazgos

- **El enfoque de Pagila escala a esquemas reales con un cambio chico.** La falta de PK es común en tablas de
  eventos (las más grandes); `ctid` dentro de una instantánea lo resuelve sin tocar el origen.
- **Las relaciones no declaradas son imprescindibles:** sin el CSV de la etapa 1, los proveedores y cuidadores no
  entrarían al subconjunto y quedarían 20 relaciones rotas. El sistema necesita proponerlas (F2) antes de extraer.
- **Las huérfanas del origen no las arregla nadie:** el subconjunto las hereda. Conviene informarlas en el
  manifiesto, como se hace acá, para que no parezcan un error de la extracción.
- **Proporción de filas ≠ proporción de pacientes:** depende de la historia de cada paciente. Si el objetivo es un
  tamaño de base, conviene elegir por filas o por eventos, no solo por pacientes.
- **El cuello de botella para la MIMIC completa es la copia en memoria:** unos 150 MB por millón de filas de
  `chartevents` (8,4 MB por 54 577 filas). Con el 1 % de la completa entra en 16 GB; para el 10 % hay que copiar en
  flujo (de `COPY TO` a `COPY FROM` sin guardar la tabla entera). La selección también crece con el origen; no se
  pudo medir sin la base completa.

## Propuesta para las etapas siguientes

Bases de trabajo para B (anonimización) y D (sintéticos): **`mimic_c1_50`** (47 pacientes, 733 000 filas) y
**`synthea_c1_10`** (85 pacientes, 103 000 filas). Para E3, los pacientes de control (16 y 226) quedan fuera de
las dos.

## Limitaciones

- Solo la demo de MIMIC: la escala de la completa (cientos de veces más filas) se estima, no se midió.
- La memoria del PostgreSQL del contenedor no se midió aparte; solo la del proceso Python, las tablas de trabajo y
  los temporales.
- `ctid` exige que nadie modifique el origen durante la extracción. Acá se garantiza con la instantánea; en una base
  de producción con escrituras también, porque `REPEATABLE READ` ve siempre la misma versión de cada fila.

## Evidencia

- `resultados/<extracción>/manifiesto.json`: configuración y su sha256, sha256 del esquema, entorno, tablas sin PK,
  relaciones, ancla y control, rondas, conteos, integridad, escala y tiempos.
- `resultados/<extracción>/conteos.csv`: filas por tabla (origen, subconjunto, núcleo, clave usada).
- Bases destino en `pagila-db`: `mimic_c1_10`, `mimic_c1_50`, `synthea_c1_1`, `synthea_c1_10`.
