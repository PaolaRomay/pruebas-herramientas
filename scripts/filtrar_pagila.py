#!/usr/bin/env python3
"""Adapta los dumps de Pagila para cargarlos en un Postgres estándar (13 o superior) y en
la imagen de PostgreSQL Anonymizer:
  - saca lo que depende de pgvector (tabla film_embedding, su índice y la extensión);
  - cambia uuidv7() (solo PostgreSQL 18) por gen_random_uuid();
  - saca SET transaction_timeout (solo PostgreSQL 17+).
Ninguna de las dos cosas interviene en las pruebas."""
import re
import sys

src, dst, kind = sys.argv[1], sys.argv[2], sys.argv[3]
text = open(src, encoding="utf-8").read()

if kind == "schema":
    # pg_dump separa los objetos con bloques que empiezan en "--\n-- Name: ..."
    blocks = re.split(r"(?m)^(?=--\n-- Name: )", text)
    keep = [b for b in blocks
            if "film_embedding" not in b and not re.search(r"Name: vector; Type: EXTENSION|EXTENSION IF NOT EXISTS vector|EXTENSION vector|public\.vector", b)]
    out = "".join(keep)
    # uuidv7() solo existe desde PostgreSQL 18; los valores ya vienen en los datos,
    # el DEFAULT solo afecta inserts nuevos, así que usamos el equivalente del núcleo.
    out = out.replace("uuidv7()", "gen_random_uuid()")
else:
    # Datos: quitar el COPY de film_embedding (hasta la línea "\.") y su encabezado
    out = re.sub(
        r"(?ms)^--\n-- Data for Name: film_embedding;.*?^\\\.\n\n?", "", text)

# Parámetro de sesión de PostgreSQL 17+; las versiones anteriores lo rechazan.
out = re.sub(r"(?m)^SET transaction_timeout = 0;\n", "", out)

open(dst, "w", encoding="utf-8").write(out)
print(f"{dst}: listo")
