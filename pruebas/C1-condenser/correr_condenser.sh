#!/usr/bin/env bash
# Corre Condenser (TonicAI/condenser @ 14ff407) con la config de la carpeta indicada.
# Uso: ./correr_condenser.sh corridaN   (la carpeta tiene config.json; la salida queda en salida.log)
# Nota: POSTGRES_PATH no alcanza: Condenser hace chdir a esa ruta pero llama a psql/pg_dump por PATH.
set -euo pipefail
cd "$(dirname "$0")/$1"
RAIZ="$(cd ../../.. && pwd)"
CONDENSER="${CONDENSER:-$HOME/Desktop/Tesis/herramientas-externas/condenser}"
DESTINO="$(python3 -c 'import json;print(json.load(open("config.json"))["destination_db_connection_info"]["db_name"])')"
docker exec pagila-db psql -q -U postgres -c "drop database if exists $DESTINO" -c "create database $DESTINO"
export PATH="$(cd .. && pwd)/bin_pg16:$PATH"   # psql/pg_dump 16 del contenedor: el pg_dump 18 de libpq emite SET transaction_timeout, que PG16 rechaza
inicio=$(date +%s)
"$RAIZ/.venv-condenser/bin/python" "$CONDENSER/direct_subset.py" -v > salida.log 2>&1 || echo "SALIDA CON ERROR: $?" | tee -a salida.log
echo "segundos: $(( $(date +%s) - inicio ))" | tee -a salida.log
