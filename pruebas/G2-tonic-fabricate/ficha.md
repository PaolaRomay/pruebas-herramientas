# G2 — Tonic Fabricate (Data Agent) — Orquestar con un LLM

**Quién / cuándo:** _(completar)_, _(fecha)_. Sin trial: plan Free de Fabricate (USD 5 de crédito por mes, D).
**Fuente de cada dato:** D = documentación, P = prueba propia. Salvo donde dice D, todo es P.

[← Estado](../ESTADO.md) · [Ficha de Tonic](../_herramientas/tonic.md) · [D5](../D5-tonic-fabricate/ficha.md) · [G3](../G3-tonic-structural/ficha.md)

**Pregunta:** ¿el Data Agent de Fabricate entiende pedidos en lenguaje natural y los resuelve bien?

Es una prueba **cualitativa**: la herramienta es un chat, así que no hay JSON ni funciones que contar como en G1. Las métricas de G (% de JSON válido, % de funciones bien elegidas, latencia, variabilidad) se reemplazan por: si lo hizo bien, cuántas correcciones manuales hicieron falta, el tiempo y si el resultado carga sin errores.

> **Casos:** los de G1, propuestos el 2026-10-11 en [ESTADO.md](../ESTADO.md#casos-de-orquestación-propuesta-para-g1-2026-10-11), con el criterio de «lo hizo bien» de cada uno. Los casos 1–3 suponen datos reales: si Fabricate no puede, se anota «no aplica» y por qué.

## Entorno

- Herramienta: Tonic Fabricate (fabricate.tonic.ai), Data Agent. Versión: no la muestra; fecha de la corrida: _(completar)_.
- Entrada: esquema de Pagila (`data/pagila/01-schema.sql`, o el recorte que se use en cada caso).
- Verificación de carga: `scripts/integridad.py` sobre una base local sin restricciones (pasos en el README). No se usa `d5_fabricate.py` porque pisaría la base y los resultados de D5.
- Equipo de verificación: _(chip, RAM, macOS)_.

## Qué se midió y resultado

| Caso (de G1) | Pedido al Data Agent (textual) | ¿Lo hizo bien? | Correcciones manuales | Tiempo | ¿Carga sin errores? | Evidencia |
|---|---|---|---|---|---|---|
| 1 · Detectar | «¿Qué columnas de esta base tienen datos personales? Listalas con el tipo de dato de cada una.» | | | | | |
| 2 · Anonimizar | «Anonimizá nombres, emails, teléfonos y direcciones de los clientes y del personal. El mismo cliente tiene que tener el mismo nombre falso en todas las tablas y la base tiene que seguir cargando sin errores.» | | | | | |
| 3 · Subconjunto | «Sacame un subconjunto con el 10 % de los clientes y todo lo que dependa de ellos (alquileres y pagos), sin romper las claves.» | | | | | |
| 4 · Sintetizar | «Generá una base sintética con el mismo esquema y 100 clientes, con alquileres y pagos coherentes entre sí.» | | | | | |
| 5 · Ambiguo | «Prepará una copia de la base para que el equipo de testing la use sin ver datos reales.» | | | | | |

Criterio de «lo hizo bien»: el de cada caso en [ESTADO.md](../ESTADO.md#casos-de-orquestación-propuesta-para-g1-2026-10-11).

**Antecedente (D5, P):** pedido «20 % de las filas de Pagila». Generó el Sakila clásico (2005, 2 tiendas) en lugar del esquema v4, con proporciones entre 0,1 % y 100 %. `payment` no cargó porque sus fechas no caen en ninguna partición. No es un caso de G1, pero muestra que el agente no siempre respeta el esquema que recibe.

**Variabilidad:** ¿el mismo pedido dos veces da lo mismo? _(completar)_

## Esfuerzo

- Horas hasta la primera corrida: _(completar)_
- Créditos consumidos: _(completar)_
- Problemas encontrados: _(completar)_

## Hallazgos

- Limitaciones vistas en la práctica: _(completar)_
- Requisitos que surgen para el sistema: _(completar)_

## Evidencia

- `evidencia/`: capturas de cada conversación (pedido y respuesta) y salida de la carga de cada caso. _(completar nombres)_
