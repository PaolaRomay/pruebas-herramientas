# A5s: anon.detect sobre el esquema de synthea_p1000

- Corrida: 2026-11-09 00:14
- PostgreSQL Anonymizer 3.3.2 sobre PostgreSQL 18.6 (Debian 18.6-1.pgdg13+2) (contenedor `salud-anon`, imagen `sha256:379c4c88a598…`)
- Diccionario `en_US`: 78 nombres de columna
- Referencia: `data/columnas_sensibles_synthea.csv`; 256 columnas
- Columnas detectadas: 15; tiempo de `anon.detect`: 0.18 s

| Columna | Categoría | Directo |
|---|---|---|
| organizations.address | street_address | sí |
| organizations.city | city | sí |
| organizations.name | name | sí |
| organizations.phone | phone_number | sí |
| patients.address | street_address | sí |
| patients.city | city | sí |
| patients.gender | gender | no |
| payers.address | street_address | sí |
| payers.city | city | sí |
| payers.name | name | sí |
| payers.phone | phone_number | sí |
| providers.address | street_address | sí |
| providers.city | city | sí |
| providers.gender | gender | no |
| providers.name | name | sí |
