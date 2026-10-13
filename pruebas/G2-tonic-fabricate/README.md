# G2 — Tonic Fabricate, Data Agent (Orquestar, cualitativo)

Casos: los de G1, en [ESTADO.md](../ESTADO.md#casos-de-orquestación-propuesta-para-g1-2026-10-11).

1. Para cada caso de G1, escribir el pedido en el chat del Data Agent tal como figura en ESTADO.md y copiarlo textual en la ficha.
2. Cronometrar desde el envío hasta tener el resultado. Contar cada mensaje de corrección que haga falta.
3. Capturar la conversación (`evidencia/g2_caso<N>.png`) y descargar la salida (`salidas_grandes/`, no se sube).
4. Si el caso produce una base, verificar que cargue. **No usar `d5_fabricate.py` tal cual:** recrea `d5_auditoria`, que usa E5, y escribe en `resultados/` de D5. En su lugar:

   ```bash
   # carga sin restricciones (cuenta violaciones) y errores de carga en el log
   python -c "import sys; sys.path.insert(0, 'scripts'); import integridad as ig; ig.preparar_base('g2_caso1', sin_restricciones=True); ig.cargar_sql('g2_caso1', 'pruebas/G2-tonic-fabricate/salidas_grandes/caso1.sql', 'pruebas/G2-tonic-fabricate/evidencia/g2_caso1_carga.log')"
   python scripts/integridad.py --base g2_caso1 --salida pruebas/G2-tonic-fabricate/resultados/caso1
   ```

   Los `ERROR` del log son sentencias rechazadas. `integridad.csv` cuenta las violaciones fila por fila.
5. Repetir un caso al menos una vez para ver la variabilidad.
6. Completar la tabla de la ficha.
