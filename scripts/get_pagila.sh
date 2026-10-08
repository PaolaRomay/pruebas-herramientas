#!/usr/bin/env bash
# Descarga Pagila (versión fijada por commit) y saca lo de pgvector, que no usamos.
set -euo pipefail
cd "$(dirname "$0")/.."

COMMIT="481abd8fd518fec9abeba14db9ed1a2895c9bd33"   # devrimgunduz/pagila, tag pagila-v4.0.0 (la v4.1.x ya exige PostgreSQL 18)
BASE="https://raw.githubusercontent.com/devrimgunduz/pagila/$COMMIT"
OUT="data/pagila"
mkdir -p "$OUT"

echo "Descargando esquema y datos de Pagila ($COMMIT)..."
curl -fsSL "$BASE/pagila-schema.sql" -o "$OUT/raw-schema.sql"
curl -fsSL "$BASE/pagila-data.sql"   -o "$OUT/raw-data.sql"

python3 scripts/filtrar_pagila.py "$OUT/raw-schema.sql" "$OUT/01-schema.sql" schema
python3 scripts/filtrar_pagila.py "$OUT/raw-data.sql"   "$OUT/02-data.sql"   data
rm "$OUT/raw-schema.sql" "$OUT/raw-data.sql"

echo "Listo. Si ya habías levantado el contenedor antes, recrealo para recargar:"
echo "  docker compose down -v && docker compose up -d"
