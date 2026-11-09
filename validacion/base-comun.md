# Validación · Base común de pruebas

**Qué se valida:** lo que armó Paola en el commit `6011388` (2026-10-08): `docker-compose.yml`,
`scripts/get_pagila.sh`, `scripts/filtrar_pagila.py`, `requirements*.txt` y la sección de entorno del `README.md`.
**Quién / cuándo:** Jero (ejecutado por Claude Code a pedido de Jero), 2026-11-07.
**Equipo:** Mac M5 Pro, 16 GB, macOS 26.6.2, Docker con `postgres:16.4`, uv 0.12.21.

## Veredicto

**Sí, con observaciones.** La base y el entorno se reproducen exactamente. Las observaciones son de documentación,
no de resultados.

## Resultados

| # | Qué | Cómo | Resultado |
|---|---|---|---|
| 1.1 | Pagila se descarga igual | Descarga nueva del commit fijado (`481abd8`) + `filtrar_pagila.py`, en `validacion/base-comun/descarga/` | **Confirmado.** sha256 idénticos a `data/pagila/`: `01-schema.sql` `f42c9b45…a835`, `02-data.sql` `cbfca8bc…589e`. El commit fijado es el del tag `pagila-v4.0.0` (`git ls-remote`) |
| 1.2 | El filtrado no altera datos | `diff` entre los archivos crudos y los filtrados | **Confirmado.** Esquema: solo 58 `DEFAULT uuidv7()` → `gen_random_uuid()`. Datos: solo se quita `SET transaction_timeout = 0;`. Ninguna fila de datos cambia |
| 1.3 | La base levanta igual | Los dos `.sql` descargados, cargados en un contenedor `postgres:16.4` aparte (puerto 55440, borrado después), comparado con `pagila-db` | **Confirmado.** 15 tablas, 121 209 filas, 55 particiones de `payment`, 70 PK, 36 FK, 1 CHECK y 7 vistas, todo igual. **Contenido idéntico**: md5 por tabla igual en las 15 (`huella_*.txt`) |
| 1.4 | El entorno se reproduce | `uv venv --python 3.11` nuevo + `uv pip install -r requirements.lock.txt` | **Confirmado.** `uv pip freeze` igual al lock en los 94 paquetes (solo cambia la forma de escribir el hash del modelo de spaCy). El `.venv` que se usa hoy también coincide con el lock |
| 1.5 | El README se puede seguir | Pasos de verificación del README con el entorno nuevo | **Confirmado.** Da 999 clientes y Presidio detecta `EMAIL_ADDRESS` y `PERSON`. La frase en español del README da `PERSON` sobre «Mi nombre es Ana Perez» (score 0,85) y `URL` sobre `example.com` (0,5), como dice el README |

## Observaciones (a proponer a Paola; no se tocó ningún archivo)

1. **`filtrar_pagila.py` y `get_pagila.sh` dicen que sacan lo de pgvector**, pero la v4.0.0 no lo trae: esa parte
   no hace nada. El README ya aclara «si la versión lo trae»; convendría decirlo también en los comentarios de los
   scripts.
2. **README, sección Entorno Python:** dice que «SDV y Anonymeter todavía no se usaron». Ya se usan en E3 (D2, D5,
   D6, B3) con las versiones del lock y funcionan. Actualizar.
3. **`requirements-todo.txt`:** el comentario dice que resuelve con «numpy 1.26 y pandas 2.3». El lock tiene
   pandas 3.x. Actualizar el comentario.
4. **README:** dice que la v4.1.x exige PostgreSQL 18 por `uuidv7()`. La v4.0.0 también trae `uuidv7()` (por eso
   el filtro lo reemplaza). Lo que obliga a PostgreSQL 18 en la 4.1.x son las columnas virtuales; precisar.
5. **Imagen de PostgreSQL Anonymizer sin fijar:** `ANON_IMAGE` sigue en `:stable`. El README pide fijar el digest
   después del primer pull (queda para la validación de B1, etapa 6a).

## Evidencia

- `validacion/base-comun/descarga/`: archivos crudos y filtrados de la descarga nueva.
- `validacion/base-comun/conteos.sql`, `huella.sql`: consultas usadas.
- `validacion/base-comun/conteos_*.txt`, `huella_*.txt`: salida en `pagila-db` y en el contenedor de validación.
- `validacion/base-comun/freeze_nuevo.txt`, `freeze_venv_actual.txt`: paquetes del entorno nuevo y del actual.
