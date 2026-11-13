# A4m / A4s — GLiNER2-PII sobre MIMIC-IV demo y Synthea — Detectar

**Quién / cuándo:** Jero (ejecutado por Claude Code a pedido de Jero), 2026-11-08.
**Fuente de cada dato:** P = prueba propia, salvo donde dice D.

[← Base MIMIC](../../_bases/mimic-demo.md) · [Base Synthea](../../_bases/synthea.md) ·
[Lista de referencia](../../_bases/referencia/taxonomia.md) · [A1m / A1s Presidio](../A1-presidio/ficha.md) ·
[A2m / A2s LLM local](../A2-llm-local/ficha.md)

## Qué es

- **GLiNER2** (D): modelo chico (unos 205 millones de parámetros, base mDeBERTa-v3) que extrae entidades de un
  texto **según etiquetas que se le escriben en lenguaje natural** («person name», «medical condition»), sin
  reentrenar. Licencia Apache 2.0.
- Se usa el checkpoint oficial **`fastino/gliner2-privacy-filter-PII-multi`** (D: ajustado para datos personales,
  multilingüe, 42 tipos de entidad).
- Como Presidio, trabaja **sobre los valores**, no sobre el esquema. A diferencia de Presidio, se le pueden pedir
  categorías que no son formatos: condición médica, medicamento, sexo, estado civil.

## En pocas palabras

- **Mejor configuración: etiquetas de datos personales + salud, umbral 0,3**: F1 **0,83** en MIMIC y **0,85** en
  Synthea. Mejor que Presidio (0,78 en las dos) y peor que el LLM local (0,88).
- **Agregar etiquetas de salud y demográficas sirve:** +5 puntos de F1 en MIMIC y +7 en Synthea respecto de solo
  datos personales. En Synthea marca 48 de 58 columnas de salud (Presidio: 35; LLM: 40).
- **Pero muchos aciertos siguen siendo casuales**, como en Presidio: los ids de paciente de MIMIC salen como
  teléfonos (`PHONE_NUMBER`) y los UUID de Synthea como **números de seguro social** (`US_SSN`). En datos de salud,
  menos de la mitad de los aciertos tienen una etiqueta de salud.
- **Falsos positivos en catálogos:** 14 de 23 en MIMIC y 20 de 28 en Synthea (el LLM: 0 y 6).
- **El contexto (nombre de la columna delante) sube la precisión y baja el recall**; con salud y umbral 0,5 queda
  casi igual (0,82 en MIMIC). Con umbral 0,7 se pierden etiquetas.
- **Rápido:** 3,5 a 6 minutos por variante y base en la GPU de la Mac, para 100 valores por columna.

## Entorno

- Equipo: Mac M5 Pro, 16 GB, macOS 26.6.2, Python 3.11.16. Dispositivo `mps` (GPU de Apple).
- `gliner2` 2.1.0, `transformers` 5.22.2, `torch` 2.14.1. **Instalados en el `.venv` para esta prueba** (2026-11-08):
  `gliner2` no declara `transformers` como dependencia y hubo que instalarlo aparte. No cambió ninguna versión que ya
  estaba. No se agregaron a `requirements.txt` (base común): queda para acordar.
- Modelo descargado de Hugging Face en la primera corrida (unos minutos), en la caché local.
- Datos y listas de referencia: los mismos que A1m / A1s.
- Script: `a4_gliner2_salud.py` (esta carpeta). Métricas: `pruebas/salud/comparar_salud.py`.

```bash
.venv/bin/python -m pip install gliner2==2.1.0 transformers==5.22.2
.venv/bin/python pruebas/salud/A4-gliner2/a4_gliner2_salud.py --base mimic   # y synthea
.venv/bin/python pruebas/salud/comparar_salud.py --base mimic                # y synthea
```

### Metodología

Igual que la variante manual de A1 (Presidio), para poder compararlas:

- **Muestra:** la misma que A1 (orden por md5 del valor, semilla `a1`), pero los primeros **100 valores** por
  columna en lugar de 200, por tiempo. Valores recortados a 300 caracteres.
- Una columna se marca si GLiNER2 detecta alguna entidad en al menos el **50 % de sus valores**; la entidad es la
  más frecuente.
- **Variantes:**
  - `pii`: once etiquetas de datos personales (person name, date, location, street address, social security number,
    driver license number, passport number, phone number, email address, identification number, financial amount);
  - `pii_salud`: las anteriores + nueve de salud y demográficas (medical condition, medication, medical procedure,
    lab test, gender, ethnicity, marital status, language, health insurance);
  - `_contexto`: el valor precedido por el nombre de la columna («marital status: MARRIED»);
  - umbrales de confianza 0,3, 0,5 y 0,7.
- Determinista (sin muestreo aleatorio en la inferencia): una corrida.

## Qué se midió y resultado

| Base | Variante | TP | FP | FN | TN | Precisión | Recall | F1 | Etiqueta |
|---|---|---|---|---|---|---|---|---|---|
| MIMIC | `pii`, umbral 0,3 | 171 | 18 | 76 | 46 | 0,90 | 0,69 | 0,78 | 45/45 |
| MIMIC | **`pii_salud`, umbral 0,3** | 193 | 24 | 54 | 40 | 0,89 | **0,78** | **0,83** | 45/45 |
| MIMIC | `pii_salud_contexto`, umbral 0,5 | 177 | 8 | 70 | 56 | **0,96** | 0,72 | 0,82 | 45/45 |
| MIMIC | *Presidio structured (A1m)* | *171* | *21* | *76* | *43* | *0,89* | *0,69* | *0,78* | *45/45* |
| MIMIC | *LLM `a2b` (A2m)* | *199* | *6* | *48* | *58* | *0,97* | *0,81* | *0,88* | *45/45* |
| Synthea | `pii`, umbral 0,3 | 123 | 30 | 36 | 30 | 0,80 | 0,77 | 0,79 | 38/41 |
| Synthea | **`pii_salud`, umbral 0,3** | 143 | 33 | 16 | 27 | 0,81 | **0,90** | **0,85** | 38/41 |
| Synthea | `pii_salud_contexto`, umbral 0,3 | 137 | 35 | 22 | 25 | 0,80 | 0,86 | 0,83 | **41/41** |
| Synthea | *Presidio structured (A1s)* | *127* | *39* | *32* | *21* | *0,77* | *0,80* | *0,78* | *39/41* |
| Synthea | *LLM `a2b` (A2s)* | *135* | *14* | *24* | *46* | *0,91* | *0,85* | *0,88* | *41/41* |

Las 12 configuraciones por base: `resultados_comparados/salud/<base>/deteccion_resumen.md`. En general, subir el
umbral sube algo la precisión y baja mucho el recall.

### Por categoría de la lista

Columnas marcadas / columnas de la categoría (las columnas vacías no se analizan).

| Categoría | MIMIC `pii` 0,3 | MIMIC `pii_salud` 0,3 | Synthea `pii` 0,3 | Synthea `pii_salud` 0,3 |
|---|---|---|---|---|
| Fechas y geografía HIPAA | 45/45 | 45/45 | 35/35 | 35/35 |
| Identificadores de paciente o episodio | 51/51 | 51/51 | 27/30 | 29/30 |
| Identificadores directos | — | — | 12/12 | 12/12 |
| Demográficos (`cuasi`) | 3/7 | 5/7 | 6/6 | 5/6 |
| Datos de salud y origen | 59/131 | **77/131** | 29/58 | **48/58** |
| Profesionales | 14/14 | 14/14 | 12/16 | 12/16 |
| Económicos del paciente | — | — | 20/22 | 14/22 |
| Catálogos (no sensibles) | 8/23 | 14/23 | 19/28 | 20/28 |
| Técnicas (no sensibles) | 10/41 | 10/41 | 11/32 | 13/32 |

### Con qué etiqueta acierta (`pii_salud`, umbral 0,3)

- **Fechas y geografía HIPAA:** en MIMIC, las 45 como `DATE_TIME`. En Synthea, 29 `DATE_TIME`, 4 `LOCATION` y 2
  `FINANCIAL` (coordenadas).
- **Identificadores directos de Synthea:** 6 como `PERSON` (nombres), 2 `US_SSN`, 2 `PHONE_NUMBER`, 1 `LOCATION` y
  1 `ID_NUMBER`; la licencia de conducir sale como SSN.
- **Identificadores de paciente:** **casuales**. MIMIC: 31 como `PHONE_NUMBER` y 20 como `ID_NUMBER`. Synthea: 28 de
  29 como `US_SSN` (son UUID).
- **Datos de salud:** en MIMIC, 24 de 77 con una etiqueta de salud (`MEDICATION`, `MEDICAL_CONDITION`,
  `MEDICAL_PROCEDURE`); el resto como `FINANCIAL` (25: cantidades y dosis), `PHONE_NUMBER` (12: códigos) o
  `LOCATION`. En Synthea, 22 de 48.
- **Demográficos:** algunos bien (`MARITAL_STATUS`, `ETHNICITY`, `LANGUAGE`, `INSURANCE`), otros como `PERSON`.

### Tiempo

| Base | `pii` | `pii_contexto` | `pii_salud` | `pii_salud_contexto` |
|---|---|---|---|---|
| MIMIC (339 columnas × 100 valores) | 218 s | 232 s | 323 s | 352 s |
| Synthea (246 columnas × 100 valores) | 163 s | 170 s | 237 s | 251 s |

Más etiquetas = más tiempo (20 etiquetas tardan un 50 % más que 11). Cada configuración de umbral sale de la misma
pasada.

## Hallazgos

- **GLiNER2 queda entre Presidio y el LLM.** Le gana a Presidio porque se le pueden pedir categorías de salud y
  demográficas; pierde contra el LLM porque, como Presidio, **mira valores sueltos, no la columna**: no puede saber
  que una tabla es un catálogo ni que un número es un id.
- **Las etiquetas de salud suben el recall de verdad, pero con etiquetas mezcladas.** Una dosis («5 mg») sale como
  monto financiero; un código, como teléfono. Sirve para decidir «sensible o no», no para saber qué tipo de dato es.
- **Los aciertos casuales en ids son peores que los de Presidio para anonimizar:** un UUID etiquetado `US_SSN`
  llevaría a aplicarle una máscara de SSN.
- **Mejor uso en el sistema: texto libre.** Es rápido, corre en la GPU de la Mac, es multilingüe y acepta etiquetas
  a pedido (por ejemplo «cédula de identidad uruguaya»). Es el candidato natural para A7m (notas clínicas) y para
  probar en español, frente a Presidio, que necesita un reconocedor escrito a mano para cada formato.

## Limitaciones

- 100 valores por columna en lugar de los 200 de A1 (la muestra es un subconjunto de la de A1).
- Las etiquetas son una elección propia: otras redacciones («diagnosis» en vez de «medical condition») pueden dar
  otro resultado. No se probaron.
- La lista de referencia sale de reglas, sin anotación manual independiente (ver `taxonomia.md`).
- Datos en inglés: el modelo es multilingüe, pero no se probó en español.

## Evidencia

- `resultados/<base>/a4<m|s>_columnas.csv` (por columna y configuración: marca, entidad, fracción) y
  `a4<m|s>_corrida.md`.
- `resultados_comparados/salud/<base>/`: métricas, matriz por columna y resumen.
