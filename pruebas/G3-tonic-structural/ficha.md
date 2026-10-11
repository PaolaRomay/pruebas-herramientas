# G3 — Tonic Structural (Structural Agent y MCP) — Orquestar con un LLM

**Quién / cuándo:** _(completar)_, _(fecha)_. Requiere el trial de Structural.
**Fuente de cada dato:** D = documentación, P = prueba propia. Salvo donde dice D, todo es P.

[← Estado](../ESTADO.md) · [Ficha de Tonic](../_herramientas/tonic.md) · [Neon](../_herramientas/neon.md) · [G2](../G2-tonic-fabricate/ficha.md) · [B4](../B4-tonic-structural/ficha.md)

**Pregunta:** ¿el agente de Structural configura bien un workspace a partir de pedidos en lenguaje natural?

Es una prueba **cualitativa**, igual que G2: si lo hizo bien, cuántas correcciones manuales hicieron falta, el tiempo y si el resultado carga sin errores.

> **Casos:** los de G1, propuestos el 2026-10-11 en [ESTADO.md](../ESTADO.md#casos-de-orquestación-propuesta-para-g1-2026-10-11), con el criterio de «lo hizo bien» de cada uno. El caso 4 (sintetizar) puede no aplicar a Structural: anotar «no aplica» y por qué.

## Entorno

- Herramienta: Tonic Structural (app.tonic.ai), trial de 14 días (D). Versión que muestra la app: _(completar)_.
- Interfaces probadas:
  - Structural Agent (chat dentro de la app): _(completar: ¿existe en el trial?)_.
  - Servidor MCP de Structural (D), si da el tiempo: _(completar: cliente MCP usado y versión)_.
- Workspace: `pagila_origen` → `pagila_destino` en Neon ([neon.md](../_herramientas/neon.md)).
- Verificación de carga: `python scripts/traer_neon.py --base g3_caso<N> --salida pruebas/G3-tonic-structural/resultados/caso<N>`.

## Qué se midió y resultado

| Caso (de G1) | Interfaz | Pedido (textual) | ¿Lo hizo bien? | Correcciones manuales | Tiempo | ¿Carga sin errores? | Evidencia |
|---|---|---|---|---|---|---|---|
| 1 · Detectar | Agent | «¿Qué columnas de esta base tienen datos personales? Listalas con el tipo de dato de cada una.» | | | | | |
| 2 · Anonimizar | Agent | «Anonimizá nombres, emails, teléfonos y direcciones de los clientes y del personal. El mismo cliente tiene que tener el mismo nombre falso en todas las tablas y la base tiene que seguir cargando sin errores.» | | | | | |
| 3 · Subconjunto | Agent | «Sacame un subconjunto con el 10 % de los clientes y todo lo que dependa de ellos (alquileres y pagos), sin romper las claves.» | | | | | |
| 4 · Sintetizar | Agent | «Generá una base sintética con el mismo esquema y 100 clientes, con alquileres y pagos coherentes entre sí.» | | | | | |
| 5 · Ambiguo | Agent | «Prepará una copia de la base para que el equipo de testing la use sin ver datos reales.» | | | | | |
| _(caso)_ | MCP | _(opcional: repetir un caso)_ | | | | | |

Criterio de «lo hizo bien»: el de cada caso en [ESTADO.md](../ESTADO.md#casos-de-orquestación-propuesta-para-g1-2026-10-11).

**Variabilidad:** ¿el mismo pedido dos veces da la misma configuración? _(completar)_

## Esfuerzo

- Horas hasta la primera corrida: _(completar)_
- Problemas encontrados: _(completar)_

## Hallazgos

- Limitaciones vistas en la práctica: _(completar)_
- ¿Qué expone el MCP: configurar, generar, consultar el escaneo? _(completar, D/P)_
- Requisitos que surgen para el sistema: _(completar)_

## Evidencia

- `evidencia/`: capturas de cada conversación y de la configuración resultante.
- `resultados/caso<N>/`: salida de `scripts/traer_neon.py` cuando el caso genera una base. _(crear al correr)_
