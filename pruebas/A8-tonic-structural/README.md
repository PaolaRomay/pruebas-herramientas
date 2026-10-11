# A8 — Tonic Structural (Detectar)

Requiere el trial de Structural y Pagila en Neon ([neon.md](../_herramientas/neon.md)).

1. En app.tonic.ai, crear un workspace con origen `pagila_origen` y destino `pagila_destino`. Anotar en la ficha la versión que muestra la app.
2. **Variante 1, `scan sin LLM`:** correr el sensitivity scan por defecto. Capturar la vista de resultados con la confianza de cada columna y guardarla en `evidencia/a8_scan_sin_llm.png`.
3. **Variante 2, `scan con LLM`:** si la app tiene la opción de escaneo con modelo de lenguaje, correrla **3 veces**, con una captura por corrida (`evidencia/a8_scan_llm_c1.png`, `_c2`, `_c3`). Si la opción no existe, anotarlo en la ficha (D/P) y saltear el paso.
4. Copiar `a8_columnas_plantilla.csv` a `resultados/a8_columnas.csv` y completar, para las 29 columnas:
   - `marcada`: `True` si Structural la considera sensible y `False` si no. No dejar vacíos: el comparador da error.
   - `entidad`: el tipo que le asigna Structural, tal como aparece en la app.
   - `confianza`: la que muestra la app (columna extra, el comparador la ignora).
   - Para la variante 2, repetir las 29 filas por corrida con `variante` = `scan con LLM` y `corrida` = 1, 2, 3.
   - Si Structural no analizó alguna columna, borrar esa fila: no cuenta como FN.
5. Si Structural nombra entidades que no empiezan con los prefijos de `PREFIJOS_ESPERADOS` en `scripts/comparar_deteccion.py` (por ejemplo `FIRST_NAME`, `US_PHONE`), agregarlos ahí.
6. `python scripts/comparar_deteccion.py` y copiar a la ficha la fila de A8, la estabilidad y la matriz por columna de los casos `customer.uuid`, `staff.password` y `address.phone`.
