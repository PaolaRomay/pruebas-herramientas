# F2m: relaciones con SchemaSpy, Metanome y el LLM local

Verdad: 51 FK declaradas y 25 relaciones no declaradas (20 se cumplen en los datos).

| Herramienta | Propuestas | Declaradas | No declaradas | No declaradas que se cumplen | Fuera de la verdad | Precisión |
|---|---|---|---|---|---|---|
| SchemaSpy (relaciones implícitas) | 15 | 0 de 51 | 10 de 25 | 5 de 20 | 5 | 0.667 |
| Metanome BINDER/SPIDER: todas las dependencias de inclusión | 2349 | 51 de 51 | 20 de 25 | 20 de 20 | 2278 | 0.03 |
| Metanome + filtro: padre único | 115 | 51 de 51 | 20 de 25 | 20 de 20 | 44 | 0.617 |
| Metanome + filtro: padre único + nombre | 73 | 50 de 51 | 20 de 25 | 20 de 20 | 3 | 0.959 |
| LLM local (F2m, corrida 1) | 11 | 0 de 51 | 5 de 25 | 2 de 20 | 6 | 0.455 |
