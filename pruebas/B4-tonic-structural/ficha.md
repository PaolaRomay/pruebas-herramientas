# B4 — Tonic Structural — Anonimizar

**Quién / cuándo:** _(completar)_, _(fecha)_. Requiere el trial de Structural.
**Fuente de cada dato:** D = documentación, P = prueba propia. Salvo donde dice D, todo es P.

[← Estado](../ESTADO.md) · [Ficha de Tonic](../_herramientas/tonic.md) · [Neon](../_herramientas/neon.md) · [E3](../E3-chequeos-propios/ficha.md) · [E6](../E6-tonic-structural/ficha.md)

**Pregunta:** ¿anonimiza sin romper la base?

> **Pendiente de decisión (afecta a E6):** `pagila_origen` es una copia exacta de Pagila, así que incluye a los 200 clientes de control de E3. Si la base anonimizada de B4 se va a evaluar con Anonymeter en E6, Structural **no tiene que ver** a esos clientes. Opciones:
> - (a) Cargar en Neon la base de entrenamiento de E3 (`e3_entrenamiento`) como origen.
> - (b) Correr B4 dos veces: sobre la copia completa para las métricas de B, y sobre el origen sin control para E6.
>
> Decisión (2026-10-11): **se usa el origen completo** (`pagila_origen`, con el control) y se anota como limitación: el control deja de ser control y el riesgo de Anonymeter sale **subestimado**. B4 se corre una sola vez.

## Entorno

- Equipo de verificación: _(chip, RAM, macOS)_. La generación corre en la nube de Tonic; en el equipo solo se trae el destino y se mide.
- Herramienta: Tonic Structural (app.tonic.ai), trial de 14 días (D). Versión que muestra la app: _(completar)_.
- Origen y destino: `pagila_origen` → `pagila_destino` en Neon, PostgreSQL 18.6 ([neon.md](../_herramientas/neon.md)).
- Verificación: copia local del destino con `scripts/traer_neon.py` (pg_dump dentro del contenedor y carga sin restricciones), más `scripts/integridad.py` contra la base común `pagila`.

## Configuración de generadores

| Columnas | Generador elegido en Structural | ¿Consistente? |
|---|---|---|
| `customer.first_name`, `customer.last_name`, `staff.first_name`, `staff.last_name` | _(completar)_ | sí (pedido) |
| `customer.email`, `staff.email` | _(completar)_ | sí (pedido) |
| `address.address`, `address.address2` | _(completar)_ | |
| `address.phone` | _(completar)_ | |
| `customer.uuid` | _(completar)_ | |
| `staff.username` | _(completar)_ | |
| `staff.password` | _(completar)_ | |
| `address.postal_code`, `address.district`, `city.city` (dudosas) | _(completar: se tocan o no; justificar)_ | |
| Claves `*_id` | **sin tocar** (passthrough) | — |

Captura de la configuración: `evidencia/b4_generadores.png`. Semilla usada: _(completar)_.

## Qué se midió y resultado

Métricas mínimas de «Anonimizar»: si las FK siguen resolviendo, si se conserva la relación entre columnas (ciudad ↔ código postal), si es reversible, y el tiempo.

- **FK que resuelven** (`resultados/corrida1/traer_neon.md` e `integridad.csv`):

  | Tipo | Restricciones | Violadas | Filas que violan |
  |---|---|---|---|
  | FK | _(completar)_ | | |
  | PK | _(completar)_ | | |
  | UNIQUE | _(completar)_ | | |
  | NOT NULL | _(completar)_ | | |
  | CHECK | _(completar)_ | | |

  Filas por tabla contra Pagila (`conteos.csv`): _(completar; ¿copió todas las filas?)_
- **Coherencia ciudad ↔ código postal** contra el original (consulta del README):

  | Direcciones | Misma `city_id` | Mismo `postal_code` | Par (ciudad, CP) que existe en Pagila |
  |---|---|---|---|
  | _(completar)_ | | | |

- **Reversibilidad:** _(completar)_.
  - D: ¿qué generadores de Structural son reversibles o tienen clave? _(completar)_
  - P: ¿se puede reconstruir algún valor original desde el destino? _(completar)_
- **Tiempo del job:** _(completar: el que informa Structural, con captura)_. Más el tiempo de traerlo a local: _(completar)_.
- **Consistencia** (consulta del README):

  | Comparación | Nombres iguales | Emails iguales | uuid iguales |
  |---|---|---|---|
  | Corrida 1 vs. corrida 2 (misma semilla) | _(completar)_ | | |
  | Corrida 1 vs. corrida 3 (sin semilla) | _(completar)_ | | |

  Dentro de una corrida, ¿el mismo nombre original da siempre el mismo nombre falso? _(completar)_

### Extra: ¿bloquea la generación si cambia el esquema? (fail-closed)

Se agrega una columna nueva en `pagila_origen` (`customer.notas text`, con un valor que parezca sensible) y se vuelve a pedir la generación. Según la documentación, Structural bloquea la generación ante cambios de esquema (D).

- ¿Bloqueó? _(completar)_. Mensaje: _(completar)_. Captura: `evidencia/b4_fail_closed.png`.
- Si no bloqueó, ¿qué hizo con la columna nueva: la copió tal cual o la anonimizó? _(completar)_
- Después de la prueba se borró la columna de `pagila_origen`: _(confirmar)_.

## Esfuerzo

- Horas hasta la primera corrida: _(completar)_
- Problemas encontrados: _(completar)_

## Hallazgos

- Limitaciones vistas en la práctica: _(completar)_
- Requisitos que surgen para el sistema: _(completar)_

## Evidencia

- `resultados/corrida1/`, `corrida2/`, `corrida3/`: salida de `scripts/traer_neon.py` (`traer_neon.md`, `integridad.csv`, `conteos.csv`, `errores_carga.csv`, `carga.log`).
- `salidas_grandes/b4_c*.sql`: dumps del destino (no se suben).
- `evidencia/`: configuración de generadores, log y tiempo del job, prueba de fail-closed.

## Opcional

- ¿Misma semilla, mismo resultado? Ver «Consistencia».
