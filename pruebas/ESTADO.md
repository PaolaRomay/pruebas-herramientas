# Estado de las pruebas

Índice único de todas las pruebas del plan. Estado al 2026-10-14. Para qué mide cada función, ver [docs/plan-de-pruebas.md](../docs/plan-de-pruebas.md). El plan tiene su propia tabla de estado: **al cambiar un estado, actualizar las dos**.

Estados: **Hecha** · **Hecha fuera del repo** (hay que rehacerla o documentarla) · **En curso** · **Pendiente** · **Requiere trial** (Tonic Structural, 14 días). Fichas de herramienta (Bloque 1): [_herramientas/](_herramientas/).

| ID | Herramienta | Función | Estado | Responsable | Carpeta |
|---|---|---|---|---|---|
| A1 | Presidio | Detectar | Hecha | Paola | [A1-presidio](A1-presidio/ficha.md) |
| A2a | LLM local, solo nombres de columnas (Gemma 12B y 26B) | Detectar | Hecha fuera del repo: rehacer sobre Pagila con las métricas de A | Jero | — |
| A2b | LLM con nombres + muestra de valores | Detectar | Pendiente | Jero | — |
| A3 | Presidio + reconocedor de cédula uruguaya | Detectar | Pendiente | Paola | — |
| A4 | GLiNER | Detectar | Pendiente | sin asignar | — |
| A5 | `anon.detect` (PostgreSQL Anonymizer) | Detectar | Pendiente | sin asignar | — |
| A6 | LLM propone por nombre y Presidio confirma | Detectar | Pendiente | Jero | — |
| A7 | Tonic Textual | Detectar | En curso: scripts listos y texto libre revisado; falta correr las columnas | Jero | [A7-tonic-textual](A7-tonic-textual/ficha.md) |
| A8 | Tonic Structural | Detectar | Requiere trial | sin asignar | [A8-tonic-structural](A8-tonic-structural/ficha.md) |
| B1 | PostgreSQL Anonymizer | Anonimizar | En curso | Paola | — |
| B2 | Presidio con cifrado reversible | Anonimizar | Pendiente | Paola | — |
| B3 | ARX (k-anonimato) | Anonimizar | Hecha (2026-10-14) | Jero | [B3-arx](B3-arx/ficha.md) |
| B4 | Tonic Structural (incluye el extra fail-closed) | Anonimizar | Requiere trial | sin asignar | [B4-tonic-structural](B4-tonic-structural/ficha.md) |
| C1 | Condenser o script propio | Extraer subconjuntos | Pendiente. Ancla `customer`, filtro 10 % con semilla (ver C2) | Jero | — |
| C2 | Tonic Structural | Extraer subconjuntos | Requiere trial (ancla y filtro ya definidos) | sin asignar | [C2-tonic-structural](C2-tonic-structural/ficha.md) |
| D1 | MOSTLY AI, otro esquema (no Pagila) | Sintetizar | Desestimada (2026-10-11): se usa solo D2, hecha en el repo | Jero | — |
| D2 | MOSTLY AI (SDK local) | Sintetizar | Hecha | Jero | [D2-mostlyai](D2-mostlyai/ficha.md) |
| D3 | SDV con 3, 5 y 10 tablas | Sintetizar | Pendiente | sin asignar | — |
| D4 | Faker (línea base) | Sintetizar | Pendiente | sin asignar | — |
| D5 | Tonic Fabricate | Sintetizar | Hecha | Jero | [D5-tonic-fabricate](D5-tonic-fabricate/ficha.md) |
| D6 | REaLTabFormer (prueba de descarte) | Sintetizar | Hecha (2026-10-14): confirma el descarte | Jero | [D6-realtabformer](D6-realtabformer/ficha.md) |
| E1 | SDV + Anonymeter | Validar privacidad | En curso. Usa el split de E3 (decidido 2026-10-11, avisar a Paola) | Paola | — |
| E3 | Chequeos propios (evaluador común) | Validar | Hecha | Jero | [E3-chequeos-propios](E3-chequeos-propios/ficha.md) |
| E4 | SyntheRela | Validar | Pendiente | sin asignar | — |
| E5 | Anonymeter sobre Fabricate (vía E3) | Validar privacidad | Hecha (confirmada: cubierta con E3 sobre D5, con el split que adoptó E1) | Jero | [E5-tonic-fabricate](E5-tonic-fabricate/ficha.md) |
| E6 | Anonymeter sobre Structural (salida de B4) | Validar privacidad | Requiere trial. Depende de B4 | sin asignar | [E6-tonic-structural](E6-tonic-structural/ficha.md) |
| F1 | Mini-experimento de utilidad para testing | Utilidad | Pendiente | sin asignar | — |
| G1 | Qwen 3 local con JSON Schema | Orquestar | Pendiente. Casos propuestos (ver abajo) | Jero | — |
| G2 | Tonic Fabricate, Data Agent (cualitativo) | Orquestar | Pendiente (casos definidos) | sin asignar | [G2-tonic-fabricate](G2-tonic-fabricate/ficha.md) |
| G3 | Tonic Structural, Agent y MCP (cualitativo) | Orquestar | Requiere trial (casos definidos) | sin asignar | [G3-tonic-structural](G3-tonic-structural/ficha.md) |

## Pendientes de decisión que traban pruebas

| Pendiente | Lo define | Traba |
|---|---|---|
| Congelar `data/columnas_sensibles_borrador.csv` | Paola y Jero | A1–A8 (métricas provisorias hasta entonces) |

### Propuesta de Jero para los «dudoso» de la lista (2026-10-11, a cerrar con Paola)

El CSV no se modificó. Al congelarlo:

| Columnas | Propuesta | Motivo |
|---|---|---|
| `customer.create_date`, `payment.payment_date`, `rental.rental_date`, `rental.return_date` | no | El riesgo de las fechas como cuasi-identificador se mide en E (Anonymeter), no en A |
| `address.district`, `address.postal_code`, `city.city` | si | Son parte de la dirección de la persona |
| `actor.first_name`, `actor.last_name` | si | Criterio por tipo de dato: un nombre de persona es PII aunque sea público |
| `payment.amount` | si | Dato confidencial del negocio |

### Casos de orquestación (propuesta para G1, 2026-10-11)

Los mismos para G1, G2 y G3. El pedido se envía textual.

| Caso | Función | Pedido | Lo hizo bien si |
|---|---|---|---|
| 1 | Detectar | «¿Qué columnas de esta base tienen datos personales? Listalas con el tipo de dato de cada una.» | Marca las columnas «si» de la lista congelada; criterio de A (recall sobre todo). |
| 2 | Anonimizar | «Anonimizá nombres, emails, teléfonos y direcciones de los clientes y del personal. El mismo cliente tiene que tener el mismo nombre falso en todas las tablas y la base tiene que seguir cargando sin errores.» | Cubre las columnas sensibles, deja las claves `*_id` sin tocar, nombres y emails consistentes, 0 violaciones de integridad (como B4). |
| 3 | Subconjunto | «Sacame un subconjunto con el 10 % de los clientes y todo lo que dependa de ellos (alquileres y pagos), sin romper las claves.» | Ancla `customer`, ~10 % de clientes, 0 huérfanas, `payment` incluida (como C). |
| 4 | Sintetizar | «Generá una base sintética con el mismo esquema y 100 clientes, con alquileres y pagos coherentes entre sí.» | Respeta el esquema v4 (no el Sakila clásico), ~100 clientes, carga sin errores, fechas de `payment` dentro de las particiones. |
| 5 | Ambiguo | «Prepará una copia de la base para que el equipo de testing la use sin ver datos reales.» | Elige una combinación razonable (anonimizar o sintetizar, opcionalmente subconjunto) y pregunta o explicita lo que asume. |
