# A1: Presidio, detección de columnas sensibles en Pagila

Corrida: 2026-10-04 14:49

## Entorno

- Equipo: arm64, macOS 26.1, Python 3.11.17
- presidio-analyzer 2.2.364, presidio-structured 0.0.8, spaCy 3.8.16, modelo en_core_web_lg 3.8.0, pandas 3.0.6
- Base: Pagila (pagila-v4.0.0) en PostgreSQL, puerto 55432
- Lista de referencia: `columnas_sensibles_borrador.csv` (13 sensibles, 8 no sensibles, 10 dudosas que no entran en las métricas)
- Parámetros: 200 valores por columna (manual), 100 filas por tabla (structured), marcar con ≥50% de valores detectados, idioma `en`, semilla `a1`
- Tiempo: manual 7 s, manual_contexto 8 s, structured 70 s

## Resultados

TP = sensibles bien marcadas, FP = no sensibles marcadas, FN = sensibles no marcadas. «Etiqueta» = columnas sensibles con entidad esperada cuya entidad dominante coincide.

| Variante | Umbral | TP | FP | FN | TN | Precisión | Recall | F1 | Etiqueta |
|---|---|---|---|---|---|---|---|---|---|
| manual | 0.0 | 9 | 3 | 2 | 5 | 0.75 | 0.82 | 0.78 | 7/8 |
| manual | 0.4 | 8 | 3 | 3 | 5 | 0.73 | 0.73 | 0.73 | 7/8 |
| manual | 0.6 | 7 | 3 | 4 | 5 | 0.70 | 0.64 | 0.67 | 7/8 |
| manual_contexto | 0.0 | 8 | 3 | 3 | 5 | 0.73 | 0.73 | 0.73 | 6/8 |
| manual_contexto | 0.4 | 7 | 3 | 4 | 5 | 0.70 | 0.64 | 0.67 | 6/8 |
| manual_contexto | 0.6 | 6 | 3 | 5 | 5 | 0.67 | 0.55 | 0.60 | 6/8 |
| structured:highest_confidence | 0.0 | 10 | 4 | 1 | 4 | 0.71 | 0.91 | 0.80 | 7/8 |
| structured:highest_confidence | 0.4 | 10 | 4 | 1 | 4 | 0.71 | 0.91 | 0.80 | 7/8 |
| structured:highest_confidence | 0.6 | 10 | 4 | 1 | 4 | 0.71 | 0.91 | 0.80 | 7/8 |
| structured:mixed | 0.0 | 10 | 4 | 1 | 4 | 0.71 | 0.91 | 0.80 | 7/8 |
| structured:mixed | 0.4 | 10 | 4 | 1 | 4 | 0.71 | 0.91 | 0.80 | 7/8 |
| structured:mixed | 0.6 | 10 | 4 | 1 | 4 | 0.71 | 0.91 | 0.80 | 7/8 |
| structured:most_common | 0.0 | 10 | 4 | 1 | 4 | 0.71 | 0.91 | 0.80 | 6/8 |
| structured:most_common | 0.4 | 10 | 4 | 1 | 4 | 0.71 | 0.91 | 0.80 | 6/8 |
| structured:most_common | 0.6 | 10 | 4 | 1 | 4 | 0.71 | 0.91 | 0.80 | 7/8 |

## Qué falló en cada configuración

- **manual, umbral 0.0**. FN: customer.uuid, staff.password. FP: country.country, film.description, language.name
- **manual, umbral 0.4**. FN: customer.uuid, address.phone, staff.password. FP: country.country, film.description, language.name
- **manual, umbral 0.6**. FN: customer.uuid, address.phone, staff.username, staff.password. FP: country.country, film.description, language.name
- **manual_contexto, umbral 0.0**. FN: customer.uuid, address.address, staff.password. FP: country.country, film.description, language.name
- **manual_contexto, umbral 0.4**. FN: customer.uuid, address.address, address.phone, staff.password. FP: country.country, film.description, language.name
- **manual_contexto, umbral 0.6**. FN: customer.uuid, address.address, address.phone, staff.username, staff.password. FP: country.country, film.description, language.name
- **structured:highest_confidence, umbral 0.0**. FN: staff.password. FP: country.country, film.title, film.description, language.name
- **structured:highest_confidence, umbral 0.4**. FN: staff.password. FP: country.country, film.title, film.description, language.name
- **structured:highest_confidence, umbral 0.6**. FN: staff.password. FP: country.country, film.title, film.description, language.name
- **structured:mixed, umbral 0.0**. FN: staff.password. FP: country.country, film.title, film.description, language.name
- **structured:mixed, umbral 0.4**. FN: staff.password. FP: country.country, film.title, film.description, language.name
- **structured:mixed, umbral 0.6**. FN: staff.password. FP: country.country, film.title, film.description, language.name
- **structured:most_common, umbral 0.0**. FN: staff.password. FP: country.country, film.title, film.description, language.name
- **structured:most_common, umbral 0.4**. FN: staff.password. FP: country.country, film.title, film.description, language.name
- **structured:most_common, umbral 0.6**. FN: staff.password. FP: country.country, film.title, film.description, language.name

## Avisos

- address.address2: sin ningún valor no vacío en la base; no hay qué detectar, queda fuera de las métricas
- staff.picture: binaria (bytea), Presidio no la analiza; queda fuera de las métricas
- language.name: solo 6 valores distintos no vacíos; resultado poco fiable

Detalle por columna en `a1_columnas.csv`. Falta completar a mano la ficha (esfuerzo, hallazgos y evidencia).
