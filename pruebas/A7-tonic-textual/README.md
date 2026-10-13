# A7 — Tonic Textual

1. `python pruebas/A7-tonic-textual/a7_exportar.py` genera `entrada/` (ya está generado en el repo; solo hace falta volver a correrlo si cambia la base o el muestreo).
2. En textual.tonic.ai, subir los 29 archivos de `entrada/valores/` y `entrada/texto_libre.txt`. En la configuración, todas las entidades en modo **Redaction** (no «Synthesis»), para que cada detección quede como `[TIPO_xxxx]`.
3. Descargar los archivos procesados y guardarlos con el **mismo nombre** en `salida/valores/` (y `salida/texto_libre.txt`).
4. `python pruebas/A7-tonic-textual/a7_evaluar.py` compara línea por línea y escribe `resultados/a7_resumen.md` con la tabla al lado de A1.
5. Completar `ficha.md` y guardar las capturas en `evidencia/`.
