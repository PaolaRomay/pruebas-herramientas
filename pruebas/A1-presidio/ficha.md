# A1 — Presidio — Detectar

**Fuente de cada dato:** D = documentación, P = prueba propia. Salvo donde dice D, todo es P.

## Entorno

- Equipo: Mac M1 (arm64), 8 GB de RAM, macOS 26.1. Python 3.11.17 (uv).
- Herramienta: presidio-analyzer 2.2.364, presidio-structured 0.0.8, spaCy 3.8.16, modelo `en_core_web_lg` 3.8.0, pandas 3.0.6. Versiones exactas en `requirements.lock.txt`.
- Datos: Pagila (tag `pagila-v4.0.0`) en PostgreSQL 16.4 dentro de Docker. Lista de referencia: `data/columnas_sensibles_borrador.csv` (**borrador, sin congelar**): 13 columnas sensibles, 8 no sensibles y 10 dudosas.
- Evaluadas: 11 sensibles y 8 no sensibles. Quedan fuera de las métricas las dudosas, `address.address2` (vacía en toda la base) y `staff.picture` (binaria).
- Muestra: 200 valores no vacíos por columna (variantes manuales) y 100 filas por tabla (structured). Muestreo determinista, semilla `a1`. Idioma de análisis: inglés.
- Script: `a1_presidio.py` (esta carpeta). Tiempo de la corrida completa: manual 7 s, manual_contexto 8 s, structured 70 s.

## Qué se midió y resultado

Se midió si cada columna queda marcada como sensible. TP = sensible marcada, FP = no sensible marcada, FN = sensible sin marcar. «Etiqueta» = de las columnas con entidad esperada, cuántas recibieron la entidad correcta. Cualquier entidad detectada cuenta como «marcada», aunque sea la equivocada.

Variantes: `manual` (Presidio sobre cada valor; marca si ≥50 % de los valores tienen detección), `manual_contexto` (igual, con el nombre de la columna delante del valor), `structured:<estrategia>` (presidio-structured; la estrategia define cómo elige la entidad de la columna).

| Variante                      | Umbral | TP  | FP  | FN  | TN  | Precisión | Recall | F1   | Etiqueta |
| ----------------------------- | ------ | --- | --- | --- | --- | --------- | ------ | ---- | -------- |
| manual                        | 0.0    | 9   | 3   | 2   | 5   | 0.75      | 0.82   | 0.78 | 7/8      |
| manual                        | 0.4    | 8   | 3   | 3   | 5   | 0.73      | 0.73   | 0.73 | 7/8      |
| manual                        | 0.6    | 7   | 3   | 4   | 5   | 0.70      | 0.64   | 0.67 | 7/8      |
| manual_contexto               | 0.0    | 8   | 3   | 3   | 5   | 0.73      | 0.73   | 0.73 | 6/8      |
| manual_contexto               | 0.4    | 7   | 3   | 4   | 5   | 0.70      | 0.64   | 0.67 | 6/8      |
| manual_contexto               | 0.6    | 6   | 3   | 5   | 5   | 0.67      | 0.55   | 0.60 | 6/8      |
| structured:highest_confidence | 0.0    | 10  | 4   | 1   | 4   | 0.71      | 0.91   | 0.80 | 7/8      |
| structured:highest_confidence | 0.4    | 10  | 4   | 1   | 4   | 0.71      | 0.91   | 0.80 | 7/8      |
| structured:highest_confidence | 0.6    | 10  | 4   | 1   | 4   | 0.71      | 0.91   | 0.80 | 7/8      |
| structured:mixed              | 0.0    | 10  | 4   | 1   | 4   | 0.71      | 0.91   | 0.80 | 7/8      |
| structured:mixed              | 0.4    | 10  | 4   | 1   | 4   | 0.71      | 0.91   | 0.80 | 7/8      |
| structured:mixed              | 0.6    | 10  | 4   | 1   | 4   | 0.71      | 0.91   | 0.80 | 7/8      |
| structured:most_common        | 0.0    | 10  | 4   | 1   | 4   | 0.71      | 0.91   | 0.80 | 6/8      |
| structured:most_common        | 0.4    | 10  | 4   | 1   | 4   | 0.71      | 0.91   | 0.80 | 6/8      |
| structured:most_common        | 0.6    | 10  | 4   | 1   | 4   | 0.71      | 0.91   | 0.80 | 7/8      |

Detalle por columna: `resultados/a1_columnas.csv`. Resumen y lista de fallos por configuración: `resultados/a1_resumen.md`.

**Sensibilidad al criterio de marcado (variante manual, umbral de score 0):**

| Exigir al menos        | TP  | FP  | FN  | Recall | Precisión | F1   |
| ---------------------- | --- | --- | --- | ------ | --------- | ---- |
| 20 % de los valores    | 10  | 4   | 1   | 0,91   | 0,71      | 0,80 |
| 50 % (el usado arriba) | 9   | 3   | 2   | 0,82   | 0,75      | 0,78 |
| 80 % de los valores    | 4   | 1   | 7   | 0,36   | 0,80      | 0,50 |

Son pocas columnas (19 evaluables): una columna más o menos mueve mucho el F1, por lo que las diferencias chicas entre variantes no son concluyentes.

## Esfuerzo

- Horas hasta la primera corrida: _(completar)_
- Problemas encontrados:
  - El Python de Homebrew no sirve en macOS 26 (`pyexpat` no carga y `venv` falla en `ensurepip`); se usó `uv`.
  - SQLAlchemy 2.1 necesita indicar el driver en la URL (`postgresql+psycopg2://`).
  - La versión actual de Pagila (4.1.x) exige PostgreSQL 18 (`uuidv7()`, columnas virtuales); se fijó la 4.0.0 y se adaptó la carga.
  - En presidio-structured, el parámetro `analyzer_score_threshold` se ignora si se le pasa un analizador ya creado; hay que dejar que lo cree él. Con ese error, los tres umbrales daban resultados idénticos.

## Hallazgos

- **No detecta identificadores opacos:** `customer.uuid` y `staff.password` no se detectan en el modo manual; `staff.password` tampoco con structured. Presidio no tiene entidad para ids o hashes. Structured marca `uuid`, pero con etiquetas absurdas (`MEDICAL_LICENSE`, `DATE_TIME`), por lo que el acierto es casual.
- **Falsos positivos estables:** `country.country`, `language.name` (los toma por lugar y nacionalidad), `film.description` y, con structured, `film.title`. No cambian con el umbral ni con la estrategia.
- **El teléfono no se reconoce** cuando viene solo con dígitos, sin separadores (`address.phone`): sale como `DATE_TIME`. Hace falta un reconocedor propio.
- **Subir el umbral de score solo baja el recall.** Con 0,6 en manual se pierden `address.phone` y `staff.username`.
- **El contexto no ayudó:** pegar el nombre de la columna al valor empeoró el resultado respecto de no ponerlo.
- **La estrategia de structured cambia la etiqueta, no la marca.** Con `most_common`, `customer.email` sale como `URL` (el dominio del correo se detecta como URL y suma más veces que el correo). Con `highest_confidence` y `mixed` sale `EMAIL_ADDRESS`. Etiqueta correcta: 6/8 con `most_common` y 7/8 con las otras dos. Se vio en `customer.email` y `staff.username`.
- **Presidio solo mira los valores.** Se comprobó que presidio-structured da lo mismo con las columnas renombradas a nombres sin sentido: no usa nombres ni tipos ni claves foráneas.
- **Prueba con texto en español** (fuera del script): el modelo en inglés marca como `PERSON` toda la frase «Mi nombre es Ana Perez», no solo el nombre.
- **Observaciones de anonimización** (demo aparte, no es parte de A1; sirve para B2): `hash` y `encrypt` dieron un resultado distinto para el mismo valor dentro del mismo texto y entre corridas, lo que rompe JOIN y claves foráneas si se usan tal cual. El único operador reversible es `encrypt`. No genera datos falsos por sí solo (reemplaza por `<PERSON>`, etc.). Que se pueda fijar el comportamiento (por ejemplo, una sal en `hash`) o usar Faker en un operador `custom` figura en la documentación (D) y no se probó.
- **Requisitos que surgen para el sistema:**
  - Complementar con una señal que lea el nombre y el esquema (modelo de lenguaje, prueba A2/A6): el nombre sabe lo que debería ser la columna y el valor, lo que contiene.
  - Reconocedores propios para formatos locales (cédula uruguaya, teléfonos sin separadores).
  - Excluir de antemano claves e identificadores numéricos del análisis automático.
  - Congelar la lista de columnas sensibles antes de comparar herramientas.

## Evidencia

- `resultados/a1_resumen.md` y `resultados/a1_columnas.csv` (generados por el script).
- _(agregar capturas de la corrida en `evidencia/`)_

## Opcional

- Reproducibilidad: el muestreo es determinista y las corridas repetidas dieron las mismas cifras en las variantes manuales y en structured.
