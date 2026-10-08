# Base común para las pruebas exploratorias

PostgreSQL 16 con la base de ejemplo **Pagila** cargada automáticamente, para que todas las pruebas (Presidio, PostgreSQL Anonymizer, SDV, Anonymeter, etc.) se hagan sobre exactamente los mismos datos.

## Requisitos

- Docker Desktop corriendo.
- `uv` (`brew install uv`), que crea el entorno de Python 3.11. No se usa el Python de Homebrew: en macOS 26 su módulo `pyexpat` no carga y `python3.11 -m venv` falla en `ensurepip`. Tampoco sirve el `python3` del sistema (3.14), que Anonymeter no soporta.

## Puesta en marcha (una vez)

```bash
./scripts/get_pagila.sh
```

```bash
docker compose up -d
```

La primera vez tarda unos segundos en cargar los datos. Para verificar:

```bash
docker exec pagila-db psql -U postgres -d pagila -c "select count(*) from customer"
```

Debe dar **999**. Otros conteos de referencia: 1003 direcciones, 51061 pagos, 1000 películas.

Conexión desde otra herramienta: `postgresql://postgres:postgres@127.0.0.1:55432/pagila`.
Desde SQLAlchemy 2.1 hay que indicar el driver, porque sin él busca `psycopg` (v3) y no `psycopg2`: `postgresql+psycopg2://postgres:postgres@127.0.0.1:55432/pagila`.
(el puerto es 55432 para no chocar con un PostgreSQL ya instalado en el Mac).

Para volver a empezar de cero: `docker compose down -v && docker compose up -d`.

## Entorno Python

Instalar exactamente las versiones con las que se probó (incluye el modelo de spaCy, no hace falta bajarlo aparte):

```bash
uv venv --seed --python 3.11 .venv && source .venv/bin/activate
```

```bash
uv pip install -r requirements.lock.txt
```

`requirements.lock.txt` se generó en un M1 con la instalación de `requirements-todo.txt` (Presidio, SDV y Anonymeter juntos). Los `requirements*.txt` tienen rangos y sirven para rearmar el lock si hay que actualizar: `uv pip install -r requirements-todo.txt`, `python -m spacy download en_core_web_lg` (unos 400 MB) y `uv pip freeze > requirements.lock.txt`.

Ojo: el lock trae `pandas 3.x` junto con `numpy 1.26` y `sdv 1.32`. Se verificó que Presidio y SQLAlchemy funcionan, pero **SDV y Anonymeter todavía no se usaron**. Si la prueba E1 falla, sospechar primero de esa combinación de versiones.

## Verificación (los tres tienen que dar bien)

1. Base: el `select count(*) from customer` de arriba da 999.
2. Python llega a la base (da 999):

```bash
python -c "import sqlalchemy as s; e=s.create_engine('postgresql+psycopg2://postgres:postgres@127.0.0.1:55432/pagila'); print(e.connect().execute(s.text('select count(*) from customer')).scalar())"
```

3. Presidio detecta (debe listar `EMAIL_ADDRESS` y `PERSON`):

```bash
python -c "from presidio_analyzer import AnalyzerEngine; print(AnalyzerEngine().analyze(text='Mi nombre es Ana Perez y mi mail es ana@example.com', language='en')[:3])"
```

Dato para las fichas: con ese texto en español, Presidio (modelo en inglés) marca como `PERSON` toda la frase «Mi nombre es Ana Perez» y da un falso positivo de `URL` sobre el dominio del correo.

## PostgreSQL Anonymizer (prueba B1)

Se levanta aparte, en el puerto 55433:

```bash
docker compose --profile anon up -d anon
```

```bash
docker exec pagila-anon psql -U postgres -d pagila -c "CREATE EXTENSION IF NOT EXISTS anon CASCADE"
```

Lo que se comprobó en este Mac (M1, Docker 29): la imagen **solo se publica para amd64**, así que corre emulada (más lenta); está basada en PostgreSQL 18; carga Pagila sin errores; la extensión `anon` 3.2.3 se activa y `anon.init()` y `anon.fake_first_name()` funcionan. Todavía no se probaron reglas de enmascaramiento ni el dump anonimizado: eso es la prueba en sí. Para fijar la versión: después del primer pull, `docker images --digests` y poner el digest en `ANON_IMAGE`.

## Qué se cambia de Pagila (y por qué)

`scripts/get_pagila.sh` baja Pagila fijada al tag `pagila-v4.0.0` (la v4.1.x ya exige PostgreSQL 18) y `scripts/filtrar_pagila.py` le aplica tres ajustes para que cargue en PostgreSQL 16 y en la imagen de Anonymizer:

- `uuidv7()` (solo PostgreSQL 18) → `gen_random_uuid()`. Los valores de `uuid` vienen en los datos; el cambio solo afecta el DEFAULT de inserts nuevos.
- se saca `SET transaction_timeout` (PostgreSQL 17+).
- se saca lo de pgvector (si la versión lo trae). Ninguna prueba lo usa.

Los `.sql` de Pagila no se suben al repo (`.gitignore`): cada uno los baja con el script.

## Lista de columnas sensibles

`data/columnas_sensibles_borrador.csv` es un **borrador** armado leyendo las columnas de Pagila. Es la verdad de referencia contra la que se miden las pruebas de detección, así que hay que revisarlo entre los dos y congelarlo antes de empezar. Incluye columnas «dudosas» y «señuelo» (por ejemplo `film.title`) para poder contar falsos positivos. Una vez congelado, no se toca.

## Convenciones

- Una carpeta por prueba en `pruebas/<ID>-<herramienta>/`, con la ficha (`pruebas/_plantilla/ficha.md`), los scripts y `evidencia/`.
- Cada dato de la ficha lleva su origen: D (documentación) o P (prueba propia).
- Nadie modifica la base común; cada prueba trabaja sobre copias o exportaciones. Para copiar la base: `docker exec pagila-db psql -U postgres -c "CREATE DATABASE prueba_x TEMPLATE pagila"` (falla si hay otra conexión abierta a `pagila`; cerrarla antes).
- No hace falta el PostgreSQL instalado en el Mac: todo corre en el contenedor.
- La contraseña `postgres` es solo local (el puerto está atado a 127.0.0.1).

## Estructura

```
docker-compose.yml          servicio db (siempre) y anon (con --profile anon)
scripts/                    descarga y adaptación de Pagila
data/columnas_sensibles_borrador.csv
pruebas/                    una carpeta por prueba + plantilla de ficha
requirements*.txt           dependencias de Python
```
