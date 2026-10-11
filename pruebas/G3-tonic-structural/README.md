# G3 — Tonic Structural, Structural Agent y MCP (Orquestar, cualitativo)

Casos: los de G1, en [ESTADO.md](../ESTADO.md#casos-de-orquestación-propuesta-para-g1-2026-10-11). Requiere el trial de Structural y Pagila en Neon ([neon.md](../_herramientas/neon.md)).

1. Para cada caso de G1, escribir el pedido en el Structural Agent tal como figura en ESTADO.md y copiarlo textual en la ficha.
2. Cronometrar y contar las correcciones manuales. Capturar la conversación y la configuración que quedó (`evidencia/g3_caso<N>.png`).
3. Si el caso genera una base, traerla y medirla:

   ```bash
   python scripts/traer_neon.py --base g3_caso1 --salida pruebas/G3-tonic-structural/resultados/caso1
   ```

4. Si da el tiempo, repetir algún caso por el servidor MCP de Structural desde un cliente MCP. Anotar en la ficha cuál y con qué versión.
5. Completar la tabla de la ficha.
