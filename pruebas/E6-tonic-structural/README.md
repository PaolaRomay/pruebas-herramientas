# E6 — Tonic Structural (Validar privacidad)

Depende de B4 y del split de E1. Se usa el origen completo, con los clientes de control (decisión en la ficha): el riesgo sale subestimado.

1. Tener la base anonimizada de B4 en el contenedor, traída con `scripts/traer_neon.py` (por ejemplo `b4_c1`) generada desde `pagila_origen` completo.
2. Evaluar. Con `--entrenada-con` se indica qué vio la herramienta:

   ```bash
   python pruebas/E3-chequeos-propios/evaluar_bd.py evaluar --candidata b4_c1 --tipo anonimizada \
       --entrenada-con pagila --salida pruebas/E6-tonic-structural/resultados
   ```

   `--entrenada-con pagila` porque Structural vio la base completa. El evaluador deja el aviso de que el control no es control; queda como limitación.
3. Capturar el Privacy Hub de Structural para esa configuración (`evidencia/e6_privacy_hub.png`).
4. Completar la ficha y la comparación con E5 (ya tiene valores) y E1.
