# E5 — Tonic Fabricate (Validar privacidad)

La evaluación ya está hecha con E3 sobre la base de D5 (`pruebas/E3-chequeos-propios/resultados/d5_auditoria/`). Hay que volver a correrla solo si cambia el split original/control (pendiente: el mismo que E1).

1. Si cambió el control, regenerar la base de entrenamiento con el split nuevo:
   `python pruebas/E3-chequeos-propios/evaluar_bd.py preparar` (con la semilla o fracción que se acuerde).
2. Cargar la base de Fabricate sin restricciones. `python pruebas/D5-tonic-fabricate/d5_fabricate.py` crea `d5_auditoria` (ver su «Uso»).
3. Evaluar. No lleva `--entrenada-con`, porque Fabricate no aprendió de ningún dato:

   ```bash
   python pruebas/E3-chequeos-propios/evaluar_bd.py evaluar --candidata d5_auditoria --tipo sintetica \
       --salida pruebas/E5-tonic-fabricate/resultados
   ```

   Los resultados quedan en `resultados/d5_auditoria/`. Sin `--salida`, pisarían los de E3.
4. Actualizar la tabla de la ficha y la comparación con E6 y E1.
