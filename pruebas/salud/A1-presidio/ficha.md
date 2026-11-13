# A1m / A1s — Presidio sobre MIMIC-IV demo y Synthea — Detectar

**Quién / cuándo:** Jero (ejecutado por Claude Code a pedido de Jero), 2026-11-08.
**Fuente de cada dato:** P = prueba propia, salvo donde dice D.

[← Base MIMIC](../../_bases/mimic-demo.md) · [Base Synthea](../../_bases/synthea.md) ·
[Lista de referencia](../../_bases/referencia/taxonomia.md) · [A1 sobre Pagila](../../A1-presidio/ficha.md)

Segunda ronda de A1: la misma herramienta y la misma metodología que en Pagila (validada en la validación cruzada
de A1), ahora sobre dos bases de salud. MIMIC no tiene identificadores directos (ya viene desidentificada); Synthea
sí los tiene (inventados).

## En pocas palabras

- **F1 de 0,78 en las dos bases** con presidio-structured, casi igual que en Pagila (0,80). Pero **el número engaña**:
  buena parte del recall son aciertos por casualidad, con la etiqueta equivocada.
- **Lo que Presidio sí sabe hacer:**
  - **fechas**: todas detectadas y bien etiquetadas (`DATE_TIME`), 45 de 45 en MIMIC y 35 de 35 en Synthea;
  - **nombres** (`PERSON`), **SSN** (`US_SSN`), **licencia de conducir**;
  - **ciudad, condado y lugar de nacimiento** (`LOCATION`).
- **Lo que no sabe hacer:**
  - **datos de salud:** marca la mitad, pero casi siempre con etiquetas absurdas (nombres de procedimientos como
    `PERSON`, tipo de fluido como `NRP`). Presidio no tiene ninguna noción de «dato de salud»;
  - **identificadores de paciente:** los marca todos, pero los toma por fechas, cuentas bancarias o licencias de
    conducir;
  - **demográficos** (sexo, estado civil, idioma, seguro): ninguno;
  - **pasaporte** (Synthea): no lo detecta. **Dirección:** la etiqueta como `PERSON`.
- **Falsos positivos en catálogos:** marca descripciones de diagnósticos (MIMIC) y datos de contacto de
  organizaciones y aseguradoras (Synthea) como datos personales.
- Igual que en Pagila: **el contexto (nombre de la columna) no ayuda** y **subir el umbral solo baja el recall**.

## Entorno

- Equipo: Mac M5 Pro, 16 GB, macOS 26.6.2. Python 3.11.16.
- presidio-analyzer 2.2.364, presidio-structured 0.0.8, spaCy 3.8.16, `en_core_web_lg` 3.8.0 (las mismas versiones
  que A1 sobre Pagila).
- Datos:
  - **MIMIC-IV demo** (`mimic_demo`): 342 columnas, de las que 339 tienen valores;
  - **Synthea de 1 000 pacientes** (`synthea_p1000`): 256 columnas, de las que 246 tienen valores.
- Listas de referencia congeladas: `data/columnas_sensibles_mimic.csv` (sha256 `a7459d31…`) y
  `data/columnas_sensibles_synthea.csv` (sha256 `5c8d0a3d…`).
- Script: `a1_presidio_salud.py` (esta carpeta). Las mismas variantes, umbrales, tamaño de muestra (200 valores por
  columna y 100 filas por tabla) y semilla que A1. Una diferencia: la muestra de structured se ordena por el contenido
  de la fila y no por `ctid` (observación de la validación de A1).
- Métricas: `pruebas/salud/comparar_salud.py`, que reutiliza `scripts/comparar_deteccion.py` sin modificarlo.

```bash
.venv/bin/python pruebas/salud/A1-presidio/a1_presidio_salud.py --base mimic
.venv/bin/python pruebas/salud/A1-presidio/a1_presidio_salud.py --base synthea
.venv/bin/python pruebas/salud/comparar_salud.py --base mimic
.venv/bin/python pruebas/salud/comparar_salud.py --base synthea
```

## Qué se midió y resultado

Mejor configuración y la variante manual de referencia, por base. «Etiqueta» = de las sensibles que tienen una
entidad de Presidio equivalente (`PERSON`, `DATE_TIME`, `US_SSN`…), cuántas recibieron esa entidad.

| Base | Variante | Eval. | TP | FP | FN | TN | Precisión | Recall | F1 | Etiqueta |
|---|---|---|---|---|---|---|---|---|---|---|
| MIMIC | structured, umbral 0 | 311 | 171 | 21 | 76 | 43 | 0,89 | 0,69 | **0,78** | 45/45 |
| MIMIC | manual, umbral 0 | 311 | 112 | 3 | 135 | 61 | 0,97 | 0,45 | 0,62 | 45/45 |
| Synthea | structured, umbral 0 | 219 | 127 | 39 | 32 | 21 | 0,77 | 0,80 | **0,78** | 39/41 |
| Synthea | manual, umbral 0 | 219 | 84 | 17 | 75 | 43 | 0,83 | 0,53 | 0,65 | 39/41 |
| *Pagila (A1)* | *structured, umbral 0* | *19* | *10* | *4* | *1* | *4* | *0,71* | *0,91* | *0,80* | *7/8* |

Las tres estrategias de structured dan las mismas marcas; cambian solo algunas etiquetas. Tablas completas, con todas
las variantes: `resultados_comparados/salud/<base>/deteccion_resumen.md`.

### Por categoría de la lista (structured, umbral 0)

| Categoría | MIMIC: marcadas / columnas | Synthea: marcadas / columnas | Con qué etiqueta |
|---|---|---|---|
| Fechas y geografía HIPAA (`cuasi_hipaa`) | 45 / 45 | 35 / 35 | `DATE_TIME` y `LOCATION`, correctas. Código postal y FIPS, como fecha; coordenadas, como cuenta bancaria |
| Identificadores de paciente o episodio (`ident_opaco`) | 51 / 51 | 30 / 30 | **Equivocadas**: MIMIC `DATE_TIME`; Synthea (UUID) `US_DRIVER_LICENSE` |
| Identificadores directos (`ident_directo`) | — (no hay) | 11 / 12 | Nombres `PERSON` y SSN y licencia correctos. Pasaporte no detectado; dirección como `PERSON` |
| Datos de salud y origen (`sensible`) | 62 / 131 | 35 / 58 | **Equivocadas** (`PERSON`, `LOCATION`, `NRP`, `CREDIT_CARD`) |
| Profesionales | 12 / 14 | 12 / 16 | Ids como fecha o licencia; nombres como `PERSON` |
| Demográficos (`cuasi`: sexo, estado civil, idioma, seguro) | 0 / 4 | 1 / 5 | — |
| Económicos del paciente | — | 3 / 3 | Montos como números de cuenta |
| Catálogos (no sensibles) | **14 / 23** | **24 / 28** | Descripciones de diagnósticos como `PERSON`; contacto de organizaciones como `PERSON`, `LOCATION`, `PHONE_NUMBER` |
| Técnicas (no sensibles) | 7 / 41 | 15 / 32 | Números de orden como fecha |

Con la variante manual, umbral 0, en cambio, los identificadores de paciente de Synthea (UUID) casi no se marcan
(3 de 30), y en MIMIC salen como `US_BANK_NUMBER` o `DATE_TIME`.

### Tiempo

| Base | Manual | Manual con contexto | Structured (3 estrategias × 3 umbrales) |
|---|---|---|---|
| MIMIC (339 columnas) | 41 s | 57 s | 436 s |
| Synthea (246 columnas) | 35 s | 45 s | 345 s |

## Hallazgos

- **El F1 parecido al de Pagila esconde un comportamiento distinto.** En Pagila la mayoría de las sensibles eran
  nombres, correos y teléfonos, que Presidio conoce. Acá la mayoría son datos de salud e identificadores internos, y
  los aciertos en esas categorías son casuales: un id de 8 dígitos parece una fecha, un UUID parece una licencia.
- **Presidio no clasifica columnas: reconoce formatos.** Si el formato coincide con una entidad que conoce (fecha,
  SSN, nombre propio), acierta. Si no hay formato (un diagnóstico, un sexo, una dosis), falla o etiqueta mal.
- **Para datos de salud y cuasi-identificadores hace falta otra señal:** el nombre y la descripción de la columna
  (el LLM de A2) o un diccionario del dominio. Presidio solo sirve como primera capa, para formatos.
- **Los falsos positivos en catálogos son un problema práctico:** anonimizar descripciones de diagnósticos o datos
  de contacto de hospitales rompe la utilidad de la base sin proteger a nadie.
- **Pasaporte y dirección de Synthea:** formatos de EE. UU. que el reconocedor incluido no cubre bien (el pasaporte
  de Synthea no tiene el formato que espera Presidio). En Uruguay hará falta un reconocedor propio, igual que para la
  cédula (A3).
- **El contexto no ayuda** (manual con contexto ≈ manual), igual que en Pagila.

## Limitaciones

- La lista de referencia sale de reglas con fuente, sin anotación manual independiente (ver
  `pruebas/_bases/referencia/taxonomia.md`, sección 6).
- MIMIC y Synthea están en inglés y son de EE. UU.: se usa el modelo en inglés, a favor de Presidio.
- Una sola corrida: Presidio es determinista con la misma muestra.

## Evidencia

- `resultados/mimic/a1m_columnas.csv`, `resultados/mimic/a1m_corrida.md`.
- `resultados/synthea/a1s_columnas.csv`, `resultados/synthea/a1s_corrida.md`.
- `resultados_comparados/salud/mimic/` y `resultados_comparados/salud/synthea/`: métricas, matriz por columna y
  resumen.
