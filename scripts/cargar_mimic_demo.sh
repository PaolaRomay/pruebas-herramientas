#!/usr/bin/env bash
# Carga la demo de MIMIC-IV (2.2, abierta, ODbL) en la base `mimic_demo` del contenedor pagila-db,
# con los scripts oficiales de MIT-LCP/mimic-code (mimic-iv/buildmimic/postgres).
#
# Requisitos:
#   - la demo en data/mimic/demo/ (hosp/ e icu/ con los .csv.gz), descargada de
#     https://physionet.org/files/mimic-iv-demo/2.2/ y verificada con SHA256SUMS.txt;
#   - mimic-code clonado en $MIMIC_CODE (por defecto ../herramientas-externas/mimic-code).
#
# Uso:  scripts/cargar_mimic_demo.sh            # borra y recrea mimic_demo
# Deja un log por paso y los tiempos en pruebas/_bases/evidencia/mimic-demo/.
set -euo pipefail
cd "$(dirname "$0")/.."

RAIZ=$PWD
MIMIC_CODE=${MIMIC_CODE:-$RAIZ/../herramientas-externas/mimic-code}
SCRIPTS=$MIMIC_CODE/mimic-iv/buildmimic/postgres
DATOS=$RAIZ/data/mimic/demo
LOGS=$RAIZ/pruebas/_bases/evidencia/mimic-demo
CONT=pagila-db
BASE=mimic_demo
mkdir -p "$LOGS"

for d in hosp icu; do [ -d "$DATOS/$d" ] || { echo "Falta $DATOS/$d"; exit 1; }; done
[ -f "$SCRIPTS/create.sql" ] || { echo "No encuentro mimic-code en $MIMIC_CODE"; exit 1; }

echo "mimic-code: $(git -C "$MIMIC_CODE" log -1 --format='%h %ad' --date=short)" | tee "$LOGS/versiones.txt"
docker exec "$CONT" psql -U postgres -Atc "select version()" | tee -a "$LOGS/versiones.txt"

# Copia de datos y scripts dentro del contenedor (psql corre ahí; \COPY FROM PROGRAM usa su gzip)
docker exec "$CONT" rm -rf /tmp/mimic && docker exec "$CONT" mkdir -p /tmp/mimic/scripts
docker cp "$DATOS/hosp" "$CONT":/tmp/mimic/hosp >/dev/null
docker cp "$DATOS/icu" "$CONT":/tmp/mimic/icu >/dev/null
for f in create.sql load_gz.sql constraint.sql index.sql validate_demo.sql; do
  docker cp "$SCRIPTS/$f" "$CONT":/tmp/mimic/scripts/$f >/dev/null
done

docker exec "$CONT" dropdb -U postgres --if-exists "$BASE"
docker exec "$CONT" createdb -U postgres "$BASE"

: > "$LOGS/tiempos.csv"; echo "paso,segundos" >> "$LOGS/tiempos.csv"
paso() {  # paso <nombre> <archivo.sql>
  local t0=$(date +%s)
  docker exec "$CONT" sh -c "cd /tmp/mimic && psql -U postgres -d $BASE -v ON_ERROR_STOP=1 \
      -v mimic_data_dir=/tmp/mimic -f scripts/$2" > "$LOGS/$1.log" 2>&1
  local s=$(( $(date +%s) - t0 ))
  echo "$1,$s" >> "$LOGS/tiempos.csv"; echo "$1: ${s} s"
}
paso 1_create create.sql
paso 2_load load_gz.sql
paso 3_constraint constraint.sql
paso 4_index index.sql
paso 5_validate validate_demo.sql

docker exec "$CONT" psql -U postgres -d "$BASE" -Atc "select pg_size_pretty(pg_database_size('$BASE'))" \
  | sed 's/^/tamaño: /' | tee -a "$LOGS/versiones.txt"
docker exec "$CONT" rm -rf /tmp/mimic
echo "Listo: base $BASE"
