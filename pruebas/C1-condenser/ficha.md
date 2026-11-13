# C1 — Condenser — Extraer subconjuntos

**Quién / cuándo:** Jero (corrida por Claude Code a pedido de Jero), 2026-11-02.
**Fuente de cada dato:** D = documentación, P = prueba propia. Salvo donde dice D, todo es P. «Código» = leído en el código fuente de Condenser.

[← Estado](../ESTADO.md) · [Plan](../../docs/plan-de-pruebas.md) · [E3](../E3-chequeos-propios/ficha.md)

> C1 tiene dos partes: **Condenser** (esta ficha) y un **[script propio](../C1-script-propio/ficha.md)**, que tiene la comparación lado a lado.

## En pocas palabras

- Condenser saca un subconjunto **coherente y reproducible** de Pagila en 3–4 s: los 98 clientes del filtro, sus alquileres y pagos, y todo lo que referencian. La base destino conserva el esquema entero (las 55 particiones de `payment`, índices, triggers y vistas) y pasa el chequeo común **sin violaciones**. Tres corridas dieron un contenido idéntico, tabla por tabla.
- **Pero solo sigue las FK declaradas.** Con la configuración mínima trajo pagos de 6 de las 55 particiones (las únicas con FK) y dejó vacías `actor`, `category`, `film_actor` y `film_category`. Hubo que declararle a mano 147 relaciones (49 particiones × 3 columnas) y la lista de tablas de catálogo.
- **No resuelve ciclos.** Al declararle la relación implícita `store.manager_staff_id → staff`, que cierra el ciclo `store` ↔ `staff`, se cae. Cortándolo se completa, pero el lado cortado queda con huérfanas en los dos sentidos posibles. Cerrar el ciclo exige agregar 8 tiendas y 10 empleados más (12 y 12 en vez de 4 y 2), cosa que Condenser no hace porque recorre el grafo una sola vez.
- **Deja las secuencias en 1:** en un entorno de pruebas, el 5.º cliente o el 13.º alquiler que se inserte choca con un id existente.
- **Sin mantenimiento:** último cambio de código el 2023-05-18.

## Entorno

- Equipo: Mac M5 Pro (`sysctl`: «Apple M5»), 16 GB de RAM, macOS 26.6.2.
- Herramienta: **Condenser** ([TonicAI/condenser](https://github.com/TonicAI/condenser)), commit `14ff407` (2023-05-18), licencia **MIT**. Clonado fuera del repo, en `~/Desktop/Tesis/herramientas-externas/condenser`.
- Python 3.11 en `.venv-condenser`: `psycopg2-binary==2.9.13`, `toposort==1.10`, `mysql-connector-python==26.10.0`. El último hace falta aunque no se use MySQL: `db_connect.py` lo importa siempre (código).
- `pg_dump` y `psql` **16**, los del contenedor `pagila-db`, a través de los envoltorios de `bin_pg16/` (ver Esfuerzo).
- Origen: `pagila` (PostgreSQL 16.4, 15 tablas lógicas, 121 209 filas, 35 MB). Destino: `pagila_c1` en el mismo contenedor.
- Ancla y filtro del plan: `customer`, `hashtext('c1' || customer_id::text) % 10 = 0` → **98 clientes**.
- Uso:
  ```bash
  cd pruebas/C1-condenser
  ./correr_condenser.sh corrida2      # borra y recrea pagila_c1, corre Condenser, deja salida.log
  docker exec -i pagila-db psql -U postgres -d pagila_c1 -At < huella.sql   # huella de contenido
  cd ../.. && .venv/bin/python scripts/integridad.py --base pagila_c1 --salida pruebas/C1-condenser/resultados
  ```

## Qué es Condenser y cómo trabaja

**Qué es (D):** el subconjuntador de código abierto que publicó Tonic antes de su producto comercial. El README dice que soporta PostgreSQL y MySQL y bases de hasta unos 10 GB.

**Cómo trabaja (D + código):**
1. Copia el esquema con `pg_dump --section=pre-data` (tablas, sin claves ni índices).
2. Toma las filas del ancla (con `where` o con `percent`).
3. **Hacia arriba**, de forma ávida: trae las filas hijas que apuntan a lo ya traído (`rental`, `payment`).
4. **Hacia abajo:** trae lo que esas filas referencian (`inventory`, `film`, `store`, `address`…).
5. Agrega claves, índices y triggers con `pg_dump --section=post-data`.

**Configuración:** un `config.json` por corrida. Opciones relevantes: `fk_augmentation` (relaciones no declaradas), `passthrough_tables` (tablas que se copian enteras), `dependency_breaks` (FK que se ignoran para cortar un ciclo).

## Corridas

| Corrida | Configuración | Resultado |
|---|---|---|
| 1 | Mínima: ancla y filtro | Corre. `payment`: **1 493** filas, solo de las 6 particiones con FK. `actor`, `category`, `film_actor`, `film_category`: **vacías** |
| 2 | + `fk_augmentation` para las 49 particiones sin FK (147 entradas) + `passthrough_tables` para `film`, `film_actor`, `film_category`, `actor`, `category`, `language` | **La mejor.** 55/55 particiones con datos, `payment` 5 249 filas, catálogo completo, 0 violaciones. Quedan 2 tiendas con gerente ausente (relación no declarada, no se le dijo) |
| 3 | 2 + `store.manager_staff_id → staff` | **Se cae** con `toposort.CircularDependencyError` (ver abajo) |
| 3b | 3 + corte `staff → store` (`perserve_fk_opportunistically`) | Termina con error al agregar la FK `staff_store_id_fkey`: 2 empleados apuntan a tiendas que no se trajeron. Chequeo común: 1 FK violada, 2 filas |
| 4 | 3 + corte `store → staff` (ídem) | Termina sin error, pero igual que la 2: 2 tiendas con gerente ausente |

### Métricas de C (corrida 2)

| Métrica | Valor |
|---|---|
| Clientes extraídos | 98 (9,8 %) |
| Integridad, FK declaradas (`integridad.py`, 132 restricciones) | **0 violaciones** |
| Integridad, FK implícitas de `payment` (consulta propia) | 0 huérfanas |
| Integridad, `store.manager_staff_id` (implícita) | **2 tiendas de 4 con gerente ausente** (E3: `resultados/e3_corrida2/`) |
| Secuencias en el destino | **Quedan en 1.** El primer id existente es 5 en `customer`, 13 en `rental` y 16 059 en `payment`: ahí choca un `INSERT` |
| Pagos esperados de los 98 clientes | 5 250; extraídos 5 249 (ver Hallazgos) |
| % de la base que arrastra | **19,0 % de las filas** (23 068 de 121 209), 15 MB de 35 MB. Sin el catálogo copiado entero: `inventory` 68,5 %, el resto ≈ 10 % |
| Ciclos resueltos | **No** (corridas 3, 3b y 4) |
| Tiempo | 3–4 s por corrida |
| Misma configuración, mismo resultado | **Sí**: huella md5 de las 69 tablas físicas idéntica en 3 corridas |

Detalle por tabla: `resultados/conteos_corrida2.csv`.

## Esfuerzo

- Menos de una hora hasta la corrida 2, corrida por Claude Code y contando la lectura del código. A mano, calcular bastante más.
- Problemas encontrados:
  - **`POSTGRES_PATH` no funciona como dice el README (código):** Condenser hace `chdir` a esa carpeta, pero llama a `psql`/`pg_dump` por nombre, así que los busca en el `PATH`.
  - **Versión del cliente:** el `pg_dump` 18 de Homebrew (`libpq`) escribe `SET transaction_timeout`, que PostgreSQL 16 rechaza. No es un defecto de Condenser: el cliente tiene que ser de la misma versión que el servidor. Se resolvió con los envoltorios de `bin_pg16/`, que corren las herramientas 16 dentro del contenedor.
  - **Documentación inconsistente:** el README dice que el ancla va en el campo `target`; el ejemplo y el código usan `table`. La opción para conservar FK al cortar un ciclo se llama `perserve_fk_opportunistically`, con error de tipeo, y no está en el README.
  - **El reporte final usa estimaciones** (`reltuples` de `pg_class`): muestra `-1` en las tablas sin estadísticas y no sirve como conteo. Los conteos de esta ficha son `count(*)`.
  - El README dice que avisa si hay un ciclo sin cortar; en la práctica se cae con la excepción de `toposort` y la lista de todas las tablas.

## Hallazgos

- **Limitaciones vistas en la práctica:**
  - Depende por completo de las FK declaradas y de lo que se le declare a mano. En Pagila hubo que escribir 147 relaciones: inviable sin generarlas con código. Es justo lo que E3 detecta automáticamente.
  - No trae por sí solo las tablas que cuelgan del lado «abajo» (`film_actor`, `film_category` y sus catálogos). Hay que decidirlo tabla por tabla.
  - No cierra ciclos: recorre una vez y lo que queda del lado cortado lo descarta o lo deja huérfano.
  - El pago 29163 (cliente 401, uno de los 98) apunta a un alquiler del cliente 182. Condenser lo descarta para no romper la FK. Es correcto, pero lo hace en silencio: el subconjunto pierde una fila sin registro.
  - Sin mantenimiento desde 2023.
- **Requisitos que surgen para el sistema:**
  - La extracción tiene que usar el **grafo de relaciones de la capa 0, incluidas las no declaradas que confirma la persona** (F2), no solo las FK del catálogo.
  - Tiene que **cerrar ciclos por punto fijo** (repetir hasta que no aparezcan filas nuevas). En Pagila el cierre es chico (12 tiendas y 12 empleados).
  - Tiene que **registrar lo que descarta y por qué** (filas como el pago 29163) en el manifiesto de trazabilidad (F11).
  - Tratamiento explícito de las tablas de catálogo: copiar enteras o recortar a lo usado, como decisión configurable.
  - Filtro determinista (como el `hashtext` del plan) en vez de `percent`, que usa `random()` sin semilla (código: `subset.py`).
- **Secuencias:** no las ajusta. `pg_dump --section=pre-data` crea las secuencias sin su valor (el `setval` va en la sección de datos, que Condenser no usa). El sistema tiene que llevarlas al máximo de su columna.
- **Lo que vale la pena reutilizar:** el algoritmo de dos pasadas (arriba ávida, abajo completa) y la técnica de copiar el esquema en dos fases (`pre-data`, datos, `post-data`), que mantuvo particiones, índices, triggers y vistas sin trabajo extra.

## Evidencia

- `corrida1/` … `corrida4/`: `config.json` y `salida.log` (salida con `-v`: cada consulta y su tiempo).
- `corrida2/particiones_sin_fk.txt`: las 49 particiones a las que se les declaró la relación.
- `resultados/conteos_corrida2.csv`: filas por tabla, origen y subconjunto.
- `resultados/huella_corrida2.txt`: huella md5 por tabla (comparar con `huella.sql`).
- `resultados/integridad_corrida2.csv`, `resultados/integridad_corrida3.csv`: chequeo común (`scripts/integridad.py`). Para la corrida 3 corresponde a la variante 3b.
- `resultados/e3_corrida2/pagila_c1/`: bloque de integridad de E3 (incluye las relaciones no declaradas).
- `correr_condenser.sh`, `bin_pg16/`, `huella.sql`, `conteos.sql`: scripts.

## Opcional

- **¿Misma semilla, mismo resultado?** Con filtro `where` determinista, sí: 3 corridas idénticas. Con `percent` no: usa `random()` sin semilla (código, no probado).
