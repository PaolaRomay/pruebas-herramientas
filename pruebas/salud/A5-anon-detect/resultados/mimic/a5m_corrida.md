# A5m: anon.detect sobre el esquema de mimic_demo

- Corrida: 2026-11-09 00:14
- PostgreSQL Anonymizer 3.3.2 sobre PostgreSQL 18.6 (Debian 18.6-1.pgdg13+2) (contenedor `salud-anon`, imagen `sha256:379c4c88a598…`)
- Diccionario `en_US`: 78 nombres de columna
- Referencia: `data/columnas_sensibles_mimic.csv`; 342 columnas
- Columnas detectadas: 3; tiempo de `anon.detect`: 0.21 s

| Columna | Categoría | Directo |
|---|---|---|
| admissions.insurance | health_plan_id | sí |
| admissions.language | lang | no |
| patients.gender | gender | no |
