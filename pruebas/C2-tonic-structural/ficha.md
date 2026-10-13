# C2 — Tonic Structural — Extraer subconjuntos

**Quién / cuándo:** _(completar)_, _(fecha)_. Requiere el trial de Structural.
**Fuente de cada dato:** D = documentación, P = prueba propia. Salvo donde dice D, todo es P.

[← Estado](../ESTADO.md) · [Ficha de Tonic](../_herramientas/tonic.md) · [Neon](../_herramientas/neon.md) · [Plan, función C](../../docs/plan-de-pruebas.md#c--extraer-subconjuntos)

**Pregunta:** ¿extrae bien un pedazo de la base?

> **Decidido (2026-10-11), igual para C1 y C2:**
> - Tabla ancla: `customer`.
> - Filtro: 10 % aleatorio con semilla fija, como cláusula WHERE: `hashtext('c1' || customer_id::text) % 10 = 0`. En Pagila local selecciona **98 de 999 clientes**.

## Entorno

- Equipo de verificación: _(chip, RAM, macOS)_. El subsetting corre en la nube de Tonic.
- Herramienta: Tonic Structural (app.tonic.ai), trial de 14 días (D). Versión que muestra la app: _(completar)_.
- Origen y destino: `pagila_origen` → `pagila_destino` en Neon, PostgreSQL 18.6 ([neon.md](../_herramientas/neon.md)).
- Configuración: subsetting con la tabla ancla y el filtro de C1. Generadores: passthrough en todo, para medir solo el subconjunto (C1 tampoco anonimiza).
- Verificación: `scripts/traer_neon.py` (copia local sin restricciones y `scripts/integridad.py` contra `pagila`).

## Qué se midió y resultado

Métricas mínimas de «Extraer subconjuntos»: integridad del subconjunto, % de la base que arrastra y ciclos resueltos, con la misma tabla ancla y el mismo filtro que C1.

- **% de cada tabla y de la base total** (`resultados/conteos.csv`):

  | Tabla | Pagila | Subconjunto | % |
  |---|---|---|---|
  | _(completar desde conteos.csv)_ | | | |
  | **Total** | 121 209 | _(completar)_ | |

- **Huérfanas y duplicadas** (`resultados/traer_neon.md`, `integridad.csv`): FK _(completar)_, PK _(completar)_, UNIQUE _(completar)_, NOT NULL _(completar)_, CHECK _(completar)_.
- **Ciclo `store` ↔ `staff`:** en Pagila, `staff.store_id → store` y `store.manager_staff_id → staff`. Esta última no tiene FK declarada, solo un índice único: la chequea E3, no `integridad.py`. Hay 500 tiendas y 1500 empleados.
  - ¿Lo resolvió Structural? _(completar)_
  - ¿Quedan tiendas cuyo gerente no está en el subconjunto? _(completar con la consulta del README)_
- **`payment` particionada** (55 particiones por mes, 2022-01 a 2026-07):
  - ¿Structural la trató como una sola tabla o partición por partición? _(completar)_
  - Pagos que entraron: _(completar)_.
  - ¿Pagos cuyo alquiler o cliente no está en el subconjunto? _(completar con la consulta del README)_
- **Tiempo del job:** _(completar)_.

## Esfuerzo

- Horas hasta la primera corrida: _(completar)_
- Problemas encontrados: _(completar)_

## Hallazgos

- Limitaciones vistas en la práctica: _(completar)_
- Requisitos que surgen para el sistema: _(completar)_

## Evidencia

- `resultados/`: salida de `scripts/traer_neon.py`.
- `salidas_grandes/c2.sql`: dump del destino (no se sube).
- `evidencia/`: configuración del subsetting (ancla, filtro, opciones), log y tiempo del job.

## Opcional

- ¿Dos corridas iguales dan el mismo subconjunto? _(completar)_
