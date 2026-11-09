# Synthea en PostgreSQL

**Quién / cuándo:** Jero (ejecutado por Claude Code a pedido de Jero), 2026-11-08.
**Fuente de cada dato:** P = prueba propia, salvo donde dice D.

[← Estado de las pruebas](../ESTADO.md) · [MIMIC-IV demo](mimic-demo.md)

Complementa a la [demo de MIMIC-IV](mimic-demo.md) (decisión del 2026-11-08). MIMIC aporta estructura y
distribuciones reales, cuasi-identificadores y datos de salud. Synthea aporta **volumen de personas** y **datos
personales directos**, que MIMIC no tiene porque ya viene desidentificada.

## Qué es

- **Synthea** (D): generador de pacientes sintéticos de MITRE (proyecto Synthetic Health). Simula la vida de cada
  paciente con módulos de reglas clínicas escritas por expertos, basados en estadísticas públicas de salud.
  Exporta CSV, FHIR y C-CDA.
- **No es candidata para el sistema:** solo genera datos de salud con su propio esquema. Se usa como **fuente de
  datos de prueba**.
- Licencia **Apache 2.0**; versión **v4.0.0** (2026-03-05); último commit 2026-10-21 (verificado en GitHub el
  2026-11-08).
- Limitaciones a declarar en las fichas:
  - sus distribuciones salen de reglas, no de pacientes reales;
  - es pública y los LLM probablemente conocen su esquema;
  - formatos de EE. UU. (SSN, estados, condados).

## Generación

- Jar oficial `synthea-with-dependencies.jar` de la versión v4.0.0, en `../herramientas-externas/synthea/` (fuera del
  repo). sha256 `ed43c20a…6ecc1`, igual al publicado en GitHub.
- Corre en Docker con `eclipse-temurin:21-jre`, sin instalar Java en la Mac:

  ```bash
  docker run --rm -v ../herramientas-externas/synthea:/app:ro -v $PWD/data/synthea/p100_s12345:/out \
    eclipse-temurin:21-jre java -jar /app/synthea-with-dependencies.jar \
    -p 100 -s 12345 -cs 12345 -r 20260101 --generate.thread_pool_size=1 \
    --exporter.baseDirectory=/out --exporter.csv.export=true --exporter.fhir.export=false \
    --exporter.hospital.fhir.export=false --exporter.practitioner.fhir.export=false
  ```

- Primera corrida: `-p 100` pide 100 pacientes **vivos**. Generó 117 personas: 100 vivas y 17 fallecidas
  (el estudio guarda a las fallecidas). Tardó unos 18 s.
- Salida en `data/synthea/p100_s12345/` (en `.gitignore`), con `SHA256SUMS.txt` de los 18 CSV.

### Reproducibilidad: hace falta un solo hilo

- **Con la semilla fija pero en paralelo (por defecto), dos corridas no dan lo mismo.** Los pacientes, encuentros,
  condiciones y observaciones son los mismos, en otro orden. Pero `claims_transactions` cambia de contenido, y
  `payers.revenue` también (sumas en distinto orden).
- **Con `--generate.thread_pool_size=1`, dos corridas dan los 18 archivos idénticos byte a byte**, y los mismos
  pacientes que en paralelo. Es la configuración que se usa.

### Para las pruebas de detección

Synthea agrega **números a los nombres** por defecto («Lyndon118 Kiehn525»), para que se vea que son inventados.
Eso puede hacer que un detector como Presidio no los reconozca como nombres. Antes de las pruebas de A, decidir si se
genera sin números y anotarlo. La opción existe: `generate.append_numbers_to_person_names = true` en el
`synthea.properties` del jar v4.0.0. Se cambia con `--generate.append_numbers_to_person_names=false`.

Otro valor por defecto a tener en cuenta: `exporter.years_of_history = 10`. Solo se exportan los últimos 10 años de
historia de cada paciente.

## Carga

```bash
.venv/bin/python scripts/cargar_synthea.py data/synthea/p100_s12345/csv --base synthea_p100
```

- Synthea no trae DDL para PostgreSQL. El script carga cada CSV en el esquema `synthea` con tipos inferidos por
  pandas, pasa las fechas a `timestamp` y los nombres de columna a minúscula.
- **Claves:** declara PK en `id` donde es único, y FK según el diccionario de datos de Synthea (por nombre de
  columna). **Solo declara las que se cumplen en los datos.**
- Resultado (`evidencia/synthea_p100/`):
  - 18 tablas, **260 838 filas**, 109 MB; 26 s de carga;
  - **8 PK y 40 FK declaradas**, de 41 propuestas. La única sin declarar es `claims.referringproviderid`, vacía
    en toda la base.

| Tabla | Filas |
|---|---|
| `claims_transactions` | 94 292 |
| `observations` | 87 770 |
| `imaging_studies` | 23 846 |
| `procedures` | 16 356 |
| `claims` | 12 340 |
| `encounters` | 6 998 |
| `medications` | 5 342 |
| … | … |
| `patients` | 117 |

- **Las relaciones de Synthea quedan todas declaradas** porque las declara este script. Para probar el
  descubrimiento de relaciones no declaradas (F2), el caso es MIMIC. En Synthea se puede repetir cargando sin FK.

## Base definitiva: 1 000 pacientes (`synthea_p1000`)

Decisión del 2026-11-08: con 1 000 pacientes alcanza. Son del mismo orden que los 999 clientes de Pagila: hay lugar
para un conjunto de control de 200 y las métricas por persona se comparan entre bases. 10 000 serían unas 24 millones
de filas, más de lo que las herramientas pueden procesar en 16 GB.

- Generación: mismo comando que arriba con `-p 1000` y **`--generate.append_numbers_to_person_names=false`** (nombres
  sin números, para que la detección sea justa). Un solo hilo y semilla 12345. Tardó 68 s.
- **1 151 personas** (1 000 vivas y 151 fallecidas), **2 441 460 filas**, 745 MB de CSV. Salida en
  `data/synthea/p1000_s12345/` (en `.gitignore`), con `SHA256SUMS.txt`.
- Tablas más grandes: `claims_transactions` 942 067, `observations` 871 564, `procedures` 149 180, `claims` 123 301,
  `imaging_studies` 109 996, `encounters` 69 350.
- Los nombres salen de las listas de Synthea, que incluyen nombres hispanos (por ejemplo «Andrés Hernán Olivo»).
- Carga: `scripts/cargar_synthea.py data/synthea/p1000_s12345/csv --base synthea_p1000`. Tardó **251 s**; la base ocupa
  **953 MB**. Las mismas 8 PK y 40 FK que con 100 pacientes.

## Evidencia

- `evidencia/synthea_p100/claves.csv` (PK y FK propuestas, con huérfanas) y `tiempos.txt`.
- `data/synthea/p100_s12345/synthea.log` y `SHA256SUMS.txt` (fuera del repo).
