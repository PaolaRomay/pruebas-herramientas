# C1 — Script propio — Extraer subconjuntos

**Quién / cuándo:** Jero (escrito y corrido por Claude Code a pedido de Jero), 2026-11-02.
**Fuente de cada dato:** todo es P (prueba propia).

[← Estado](../ESTADO.md) · [Plan](../../docs/plan-de-pruebas.md) · [C1 Condenser](../C1-condenser/ficha.md) · [E3](../E3-chequeos-propios/ficha.md)

> Segunda parte de C1. Mismo ancla, mismo filtro y misma vara (`integridad.py` + bloque de integridad de E3) que [Condenser](../C1-condenser/ficha.md).

## En pocas palabras

- Un script de ~320 líneas (`subconjunto.py`) saca el subconjunto con **0 violaciones, incluidas las relaciones no declaradas** que Condenser dejaba rotas, y **cierra el ciclo `store` ↔ `staff` solo**, en 9 rondas, sin cortar nada.
- **Sin configuración de relaciones ya cubre las 55 particiones de `payment`.** Lleva las FK de las particiones a la tabla raíz, así que las 6 particiones con FK alcanzan para todas. A Condenser hubo que declararle 147 relaciones a mano. La única relación que hubo que declarar es `store.manager_staff_id → staff`.
- **No pierde filas.** El pago 29163, que apunta a un alquiler de otro cliente, se conserva: el script agrega ese alquiler y al cliente 182, y **lo registra en el manifiesto** como fila fuera del filtro.
- **Deja las secuencias bien.** En la base de Condenser quedan en 1, y en un entorno de pruebas el 5.º cliente o el 13.º alquiler insertado chocan con un id existente.
- Reproducible: dos corridas dieron contenido idéntico. Tarda 1,6 s.

## Entorno

- Equipo: Mac M5 Pro (`sysctl`: «Apple M5»), 16 GB de RAM, macOS 26.6.2.
- Python 3.11 del `.venv` del repo (`psycopg2-binary`), con las funciones de conexión de `scripts/integridad.py`. `pg_dump` y `psql` 16 se corren dentro del contenedor (variables `PG_DUMP_CMD` y `PSQL_CMD`).
- Origen: `pagila` (PostgreSQL 16.4). Destino: `pagila_c1p`.
- Uso:
  ```bash
  .venv/bin/python pruebas/C1-script-propio/subconjunto.py pruebas/C1-script-propio/config.json
  ```

## Cómo trabaja

`config.json` declara el origen, el destino, el ancla con su filtro, las tablas que se copian enteras (el mismo catálogo que en la corrida 2 de Condenser) y las relaciones extra.

1. **Grafo:** lee las FK del catálogo y lleva hijo y padre a su tabla raíz (`pg_partition_root`), sin repetir. Le suma `relaciones_extra`. En Pagila: 21 relaciones del catálogo + 1 extra.
2. **Instantánea:** abre una única transacción `REPEATABLE READ` sobre el origen. Las claves elegidas se guardan en tablas temporales de esa sesión; el origen no se modifica.
3. **Semilla:** las filas del ancla que cumplen el filtro forman el **núcleo**.
4. **Cierre por punto fijo.** En cada ronda:
   - **hacia arriba:** las filas hijas de filas del núcleo entran al núcleo (`rental`, `payment`);
   - **hacia abajo:** los padres de cualquier fila elegida entran al subconjunto, pero no al núcleo.

   Se repite hasta que una ronda no agrega nada. Solo el núcleo arrastra hijas: si un cliente que entra por referencia arrastrara sus alquileres, el subconjunto crecería sin control.
5. **Copia:** esquema `pre-data`, datos con `COPY` (sin columnas generadas; las filas de `payment` van a la tabla padre y PostgreSQL las ubica en su partición), esquema `post-data`. Al final lleva cada secuencia al máximo de su columna.
6. **Manifiesto** (`resultados/manifiesto.json`), base de F11:
   - configuración y su sha256;
   - sha256 del esquema del origen;
   - versiones del entorno y commit del repo;
   - relaciones usadas, con su origen;
   - rondas del cierre, filas del ancla fuera del filtro con el motivo, conteos, secuencias ajustadas y tiempos.

## Resultados (frente a Condenser, corrida 2)

| Métrica | Condenser | Script propio |
|---|---|---|
| Configuración de relaciones a mano | 147 entradas | **1** (`store.manager_staff_id`) |
| Clientes | 98 | 98 del filtro + 1 por referencia (182) |
| `payment` | 5 249 (descarta el 29163 sin aviso) | **5 250** |
| `rental` | 5 319 | 5 320 (+ el alquiler 4591, que referencia el pago 29163) |
| `store` / `staff` | 4 / 2 | **12 / 12** (ciclo cerrado) |
| `address` | 102 | 113 (direcciones de las tiendas y empleados agregados) |
| `integridad.py` (132 restricciones del catálogo) | 0 violaciones | 0 violaciones |
| E3: FK de `payment` en la tabla padre | 0 | 0 |
| E3: `store.manager_staff_id → staff` | **2 violaciones** | **0** |
| Ciclos | No los resuelve (se cae o deja huérfanas) | Cerrado en 9 rondas |
| Filas extraídas | 23 068 (19,0 %) | 23 114 (19,1 %) |
| Secuencias | En 1 (choca al 5.º `customer` insertado) | Ajustadas al máximo |
| Registro de lo que agrega o descarta | No | Manifiesto |
| Tiempo | 3–4 s | 1,6 s (0,8 s de cierre) |
| Mismo resultado en dos corridas | Sí | Sí |

**Variante sin relaciones extra** (`config_sin_relaciones_extra.json`): las 55 particiones quedan cubiertas igual, y la relación `store.manager_staff_id` vuelve a dar 2 violaciones, como en Condenser. Es decir: lo que el catálogo no declara hay que decírselo; lo que declara a medias (las particiones) se completa solo.

**Rondas del cierre** (filas nuevas, núcleo / por referencia): 1: 10 569 / 3 252 · 2: 0 / 111 · 3: 0 / 12 · 4: 0 / 8 · 5: 0 / 6 · 6: 0 / 4 · 7: 0 / 1 · 8: 0 / 2 · 9: 0 / 0. Las rondas 3 a 8 son la cadena tienda → gerente → tienda del gerente → …

Detalle: `resultados/conteos.csv`, `resultados/e3/pagila_c1p/e3_resumen.md`.

## Esfuerzo

- Menos de una hora, escrito y corrido por Claude Code.
- Dos errores en el camino:
  - `pg_partition_root` devuelve NULL para las tablas no particionadas. Con eso, el grafo quedaba vacío y la carga fallaba al poner las FK (corregido con `coalesce`).
  - Una consulta compuesta mal armada con `psycopg2.sql`.

## Hallazgos

- **Limitaciones del prototipo:**
  - Exige clave primaria en todas las tablas.
  - Las claves elegidas viven en tablas temporales del origen: para bases grandes hay que medir. Pagila tarda menos de 1 s.
  - Lleva a la raíz cualquier FK declarada en una partición. Es una **suposición**: que lo que vale para 6 particiones vale para las 55. Se cumple en Pagila, pero en el sistema tiene que ser una relación **propuesta** que confirme la persona (F2), no un hecho.
  - Copia en el destino solo el esquema del origen (sin roles ni permisos: `--no-owner --no-privileges`).
  - Solo PostgreSQL: usa `pg_partition_root`, `pg_dump` y `COPY`.
- **La decisión de diseño que importa:** distinguir núcleo de referencias. Sin esa distinción, el cliente 182 arrastraría todos sus alquileres y pagos, y por la cadena de tiendas el subconjunto crecería mucho más allá del 10 % pedido.
- **Requisitos que confirma para el sistema (F6, F2, F11):** grafo con relaciones propuestas y confirmadas, cierre por punto fijo, instantánea consistente del origen, manifiesto con lo que se agregó fuera del filtro y por qué, secuencias ajustadas, filtro determinista.
- **Es candidato a componente de la capa de extracción.** Lo que falta para eso: leer las relaciones confirmadas del catálogo de la capa 0 en vez del JSON, la opción de recortar catálogos a lo usado, y medirlo con una base más grande.

## Cómo se integraría en el sistema

**No es un script por base.** El código no conoce Pagila (verificado: los únicos nombres de Pagila en `subconjunto.py` están en un comentario y en el contenedor por defecto, que se cambia con `PG_DUMP_CMD` / `PSQL_CMD`). Tablas, claves primarias, FK, particiones, columnas generadas y secuencias se leen del catálogo de PostgreSQL. Lo único propio de cada base es `config.json`, que son datos:

| Parte | ¿Cambia por base? | Quién la produce en el sistema |
|---|---|---|
| El código | No: el mismo para cualquier base PostgreSQL | Componente de extracción (F6) |
| Tablas, PK, FK declaradas | Se leen, no se escriben | Introspección (F1) |
| `relaciones_extra` | Sí | E3 o el LLM las proponen, una persona confirma (F2) |
| Ancla y filtro | Sí | Lo pide el usuario; el LLM puede proponerlo |
| `copiar_enteras` (catálogos) | Sí | La clasificación (F3) propone qué tablas son catálogo |

Es el patrón del proyecto: el LLM propone la configuración, la persona la confirma y el script la ejecuta de forma determinista. En Pagila esa configuración fueron cuatro datos: ancla, filtro, lista de catálogos y una relación.

**Lo que sí limita la integración:**
- **El motor.** Solo PostgreSQL. Las partes específicas (`pg_partition_root`, `pg_dump`, `COPY`, secuencias; unas 100 de las ~320 líneas) se reescriben **una vez por motor**, no por base. El algoritmo (grafo, núcleo, punto fijo) no cambia. Por eso importa saber el motor del caso de la cliente.
- **Supuestos del prototipo:** clave primaria obligatoria, y las FK de particiones llevadas a la raíz sin confirmación.
- **Escala sin medir:** las claves elegidas viven en tablas temporales del origen y la lectura es una transacción abierta durante toda la extracción. En Pagila es menos de 1 s; con millones de filas, y sobre una base productiva en uso, hay que medirlo (etapa 2).

**Por qué un componente propio y no una herramienta:** la alternativa abierta (Condenser) está sin mantenimiento, no cierra ciclos y pierde filas sin aviso; las maduras son comerciales (Tonic Structural, Delphix) y están descartadas como componente. El informe ya señala que no hay una implementación abierta madura (Tabla 3.1). Es razonable para la tesis **con alcance acotado** (un motor, el caso de la cliente, escala del orden de L-P4), no como subconjuntador general.

**Próximo paso para acercarlo al sistema:** que lea las relaciones confirmadas desde el catálogo de la capa 0 en vez del JSON, conectando C1 con E3 (que ya detecta relaciones implícitas) y con A6.

## Evidencia

- `subconjunto.py`, `config.json`, `config_sin_relaciones_extra.json`.
- `resultados/manifiesto.json`, `resultados/conteos.csv`, `resultados/huella.txt` (md5 por tabla; dos corridas idénticas).
- `resultados/integridad.csv` (`scripts/integridad.py`) y `resultados/e3/pagila_c1p/` (bloque de integridad de E3).
- `resultados/sin_relaciones_extra/`: manifiesto y E3 de la variante. La base de esa variante se borró después de evaluarla.

## Opcional

- **¿Misma semilla, mismo resultado?** Sí: el filtro es determinista y dos corridas dieron la misma huella en las 69 tablas físicas.
