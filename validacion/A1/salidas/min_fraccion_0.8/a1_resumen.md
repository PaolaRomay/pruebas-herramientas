# A1: Presidio, detección de columnas sensibles en Pagila

Corrida: 2026-11-07 20:23

## Entorno

- Equipo: arm64, macOS 26.6.2, Python 3.11.16
- presidio-analyzer 2.2.364, presidio-structured 0.0.8, spaCy 3.8.16, modelo en_core_web_lg 3.8.0, pandas 3.0.6
- Base: Pagila (pagila-v4.0.0) en PostgreSQL, puerto 55432
- Lista de referencia: `columnas_sensibles_borrador.csv` (13 sensibles, 8 no sensibles, 10 dudosas que no entran en las métricas)
- Parámetros: 200 valores por columna (manual), 100 filas por tabla (structured), marcar con ≥80% de valores detectados, idioma `en`, semilla `a1`
- Tiempo: manual 4 s, manual_contexto 5 s, structured 14 s

## Resultados

TP = sensibles bien marcadas, FP = no sensibles marcadas, FN = sensibles no marcadas. «Etiqueta» = columnas sensibles con entidad esperada cuya entidad dominante coincide.

| Variante | Umbral | TP | FP | FN | TN | Precisión | Recall | F1 | Etiqueta |
|---|---|---|---|---|---|---|---|---|---|
| manual | 0.0 | 4 | 1 | 7 | 7 | 0.80 | 0.36 | 0.50 | 3/8 |
| manual_contexto | 0.0 | 5 | 1 | 6 | 7 | 0.83 | 0.45 | 0.59 | 4/8 |
| structured:highest_confidence | 0.0 | 10 | 4 | 1 | 4 | 0.71 | 0.91 | 0.80 | 7/8 |
| structured:mixed | 0.0 | 10 | 4 | 1 | 4 | 0.71 | 0.91 | 0.80 | 7/8 |
| structured:most_common | 0.0 | 10 | 4 | 1 | 4 | 0.71 | 0.91 | 0.80 | 6/8 |

## Qué falló en cada configuración

- **manual, umbral 0.0**. FN: customer.last_name, customer.uuid, address.address, staff.first_name, staff.last_name, staff.username, staff.password. FP: country.country
- **manual_contexto, umbral 0.0**. FN: customer.last_name, customer.uuid, address.address, staff.last_name, staff.username, staff.password. FP: country.country
- **structured:highest_confidence, umbral 0.0**. FN: staff.password. FP: country.country, film.title, film.description, language.name
- **structured:mixed, umbral 0.0**. FN: staff.password. FP: country.country, film.title, film.description, language.name
- **structured:most_common, umbral 0.0**. FN: staff.password. FP: country.country, film.title, film.description, language.name

## Avisos

- address.address2: sin ningún valor no vacío en la base; no hay qué detectar, queda fuera de las métricas
- staff.picture: binaria (bytea), Presidio no la analiza; queda fuera de las métricas
- language.name: solo 6 valores distintos no vacíos; resultado poco fiable

Detalle por columna en `a1_columnas.csv`. Falta completar a mano la ficha (esfuerzo, hallazgos y evidencia).
