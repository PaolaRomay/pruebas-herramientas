# A7 — Tonic Textual — Detectar

**Quién / cuándo:** Jero, 2026-10-03 (texto libre). Las columnas todavía no se corrieron.
**Fuente de cada dato:** D = documentación, P = prueba propia. Salvo donde dice D, todo es P.

## Entorno

- Equipo: Mac M5 Pro, 16 GB de RAM, macOS 26.6.2. La detección corre en la nube de Tonic.
- Herramienta: Tonic Textual (web, textual.tonic.ai), cuenta gratuita de 100.000 palabras (D). Anotar la versión si la muestra y la fecha de la corrida.
- Modo usado: **Redaction** en todas las entidades (reemplaza por etiqueta), idioma automático.
- Datos: Pagila (pagila-v4.0.0). Los mismos valores que A1: 29 columnas, hasta 200 valores no vacíos por columna, muestreo determinista con semilla `a1` (`entrada/valores/`, generados con `a7_exportar.py`). Más `entrada/texto_libre.txt`: cuatro párrafos en español e inglés armados con filas reales de Pagila, con una cédula y un celular uruguayos inventados. Unas 10.300 palabras en total.
- Referencia: `data/columnas_sensibles_borrador.csv` (**borrador, sin congelar**), igual que A1.

## Qué se midió y resultado

Métricas mínimas de «Detectar»: columnas bien y mal clasificadas contra la lista manual y falsos negativos. Columna marcada si Textual detectó algo en al menos el 50 % de sus valores (mismo criterio que A1).

_(pendiente: correr las 29 columnas de `entrada/valores/` en Textual, pasos 2–4 del [README](README.md), y copiar acá la tabla de `resultados/a7_resumen.md`)_

Casos a mirar en particular (fallaron en A1):
- `customer.uuid` y `staff.password` (identificadores opacos):
- `address.phone` (solo dígitos; Presidio lo tomó por fecha):
- `country.country`, `language.name`, `film.description`, `film.title` (falsos positivos de Presidio):

Texto libre (`texto_libre.txt`), qué detectó y qué no (revisión manual de `salida/texto_libre.txt` contra la lista de referencia; las dudosas no cuentan):
- Nombres, correos, dirección y teléfono de Pagila dentro de una frase: tapó las 19 apariciones sensibles (recall 19/19 por aparición). Nombres y apellidos como NAME_GIVEN/NAME_FAMILY, los 3 correos como EMAIL_ADDRESS, las 2 direcciones como LOCATION_ADDRESS, y 632316273199 como PHONE_NUMBER. Etiqueta correcta 13/14: el teléfono `240552580` («mi número es») quedó como NUMERIC_PII. El usuario `geraldo.bauch` quedó tapado pero como EMAIL_ADDRESS, y el UUID del cliente como NUMERIC_PII.
- Falsos positivos (precisión ≈ 19/23 = 0,83): el título «DRIVER ANNIE» como dos NAME_GIVEN (el mismo tipo de error que Presidio con `film.title`), «Mexico» ×2 como LOCATION_COUNTRY (`country.country` es «no» en la lista) y, aparentemente, el «us» de la palabra «usuario» (`EMAIL_ADDRESS124uario`).
- Dudosas, todas tapadas: fechas (DATE_TIME), «Michoacn de Ocampo» (LOCATION_CITY; en Pagila es el distrito), Hidalgo (LOCATION_STATE; en Pagila es la ciudad), San Juan Bautista Tuxtepec (LOCATION_CITY), código postal (LOCATION_ZIP) y «0.99 dólares» (MONEY).
- Cédula uruguaya `4.187.392-6`: detectada, como NUMERIC_PII.
- Celular uruguayo `099 482 317`: detectado, como PHONE_NUMBER.
- Párrafo en español vs. párrafo en inglés: sin diferencias visibles; tapó todo lo sensible en los dos idiomas.
- Coherencia de tokens: el mismo valor recibe el mismo token en todo el documento (OMAR HALL → `c7tc2 Q3DP3` las dos veces, Mexico → `ILrpC`). Mantiene la coherencia, pero deja ver que dos menciones son de la misma persona.

## Esfuerzo

- Horas hasta la primera corrida: prácticamente nada. Se sube el archivo y el resultado sale casi automático.
- Problemas encontrados: ninguno.

## Hallazgos

- Limitaciones vistas en la práctica (texto libre):
  - Etiquetas genéricas para identificadores sin formato estándar: la cédula uruguaya, el UUID y un teléfono sin formato salieron como NUMERIC_PII. Los tapa, pero no dice qué son.
  - Falsos positivos por contexto: un título de película en mayúsculas tomado como nombres, un país de catálogo («Mexico») y el fragmento «us» dentro de «usuario».
  - El mismo valor recibe siempre el mismo token en el documento. Mantiene la coherencia, pero permite enlazar dos menciones de la misma persona.
  - Corre en la nube de Tonic: el texto sale del equipo. La cuenta gratuita tiene un tope de 100.000 palabras (D).
  - Copiar el resultado desde la vista web pierde el formato de los marcadores. Hay que descargar el archivo.
- Requisitos que surgen para el sistema:
  - Detección en texto libre, además de por columna, en español e inglés.
  - Reconocedores para identificadores locales (cédula, celular uruguayo) con etiqueta propia.
  - Lista de excepciones por dominio (títulos, catálogos de países) para bajar falsos positivos.
  - Tokens consistentes configurables: por documento, globales o sin enlace, según si hace falta relacionar menciones.
  - Opción de correr en local cuando los datos no pueden salir del equipo.

## Evidencia

- `resultados/a7_resumen.md` y `resultados/a7_columnas.csv` (generados por `a7_evaluar.py`).
- `salida/`: los archivos tal como los devolvió Textual.
  - `salida/texto_libre.txt` es una **copia desde la vista web** de Textual, no el archivo descargado. Los marcadores perdieron los corchetes (`NAME_GIVENGXW4j` en vez de `[NAME_GIVEN_xxxx]`) y hay saltos de línea agregados. Sirve como evidencia de qué se tapó, pero conviene reemplazarlo por el archivo descargado.
- Capturas en `evidencia/`: configuración del modo de redacción, la vista de `texto_libre.txt` con las entidades marcadas, y el contador de palabras usadas.

## Opcional

- ¿Mismo archivo, mismo resultado? Subir dos veces un mismo archivo y comparar la salida.
