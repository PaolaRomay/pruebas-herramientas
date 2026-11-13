# F1m / F1s — Utilidad: consultas de referencia sobre real, anonimizada y sintéticas — Comparar

**Quién / cuándo:** Jero (ejecutado por Claude Code a pedido de Jero), 2026-11-12.
**Fuente de cada dato:** P = prueba propia.

[← B1m / B1s](../B1-anon/ficha.md) · [D2m / D2s](../D2-mostlyai/ficha.md) · [D3m / D3s](../D3-sdv/ficha.md) ·
[E3m / E3s](../E3-evaluador/ficha.md)

¿Una consulta que un equipo de desarrollo o de análisis haría sobre la base real da lo mismo sobre la anonimizada o
la sintética?

## En pocas palabras

- **La anonimizada (B1) conserva todo:** 17 de 17 consultas en MIMIC y 14 de 14 en Synthea. Desplazar fechas por
  paciente, seudonimizar ids y generalizar la edad no cambia ningún resultado agregado.
- **Las sintéticas conservan lo «de a una columna»** (sexo, raza, seguro, costos, condiciones más frecuentes) y
  **pierden lo que depende de fechas o de eventos raros:**
  - duración de la internación y de la estadía en UCI;
  - mortalidad: MOSTLY no genera muertes con 47 u 85 pacientes;
  - reinternación a 30 días;
  - diagnósticos más frecuentes en MIMIC.
- **MIMIC (47 pacientes):** MOSTLY 5 de 17, SDV 7 de 17. **Synthea (85):** MOSTLY 11 de 14, SDV 10 de 14.
  **Synthea (925):** MOSTLY 11 de 14, ahora con la mortalidad bien (5 % de error).

## Entorno

- `.venv` del repo. Script: `f1_utilidad.py` (esta carpeta). Lee los mismos datos que E3 (Parquet de D2 y D3; B1
  desde `salud-anon`).
- Criterio de «se conserva»:
  - número: error relativo de hasta 20 %;
  - ranking (top 10): al menos 5 de los 10 coinciden;
  - distribución: variación total de hasta 0,2 (0 = igual, 1 = disjuntas).
- Los resultados guardados son solo los agregados de cada consulta, nunca filas.

```bash
.venv/bin/python pruebas/salud/F1-utilidad/f1_utilidad.py --entrenamiento mimic_47   # y synthea_85, synthea_925
```

## Resultados

### MIMIC (47 pacientes)

| Consulta | B1 anonimizada | D2 MOSTLY AI | D3 SDV |
|---|---|---|---|
| Pacientes por diagnóstico (top 10 CIE) | ✓ 10/10 | ✗ 2/10 | ✗ 4/10 |
| Diagnóstico principal más frecuente (top 10) | ✓ 10/10 | ✗ 0/10 | ✗ 1/10 |
| Estadía media en UCI (`los`) | ✓ 0 % | ✓ 15 % | ✗ 84 % |
| Estadía media en UCI calculada con las fechas | ✓ 0 % | ✗ 47 998 % | ✗ 145 166 % |
| Duración mediana de la internación | ✓ 0 % | ✗ 16 427 % | ✗ 147 % |
| Mortalidad hospitalaria | ✓ 0 % | ✗ 100 % (no hay muertes) | ✗ 43 % |
| Mortalidad por grupo de edad | ✓ | ✗ | ✗ |
| Internaciones por tipo de admisión | ✓ | ✗ | ✓ |
| Internaciones por seguro | ✓ | ✓ | ✓ |
| Pacientes por sexo | ✓ | ✓ | ✓ |
| Pacientes por grupo de edad | ✓ | ✗ | ✓ |
| Internaciones por paciente | ✓ | ✗ 29 % | ✓ 0 % |
| % de internaciones con UCI | ✓ | ✓ 6 % | ✗ 21 % |
| Reinternación a 30 días | ✓ | ✗ 93 % | ✗ 60 % |
| Laboratorios más pedidos (top 10) | ✓ 9/10 | ✗ 3/10 | ✓ 6/10 |
| % de laboratorios anormales | ✓ | ✓ 16 % | ✓ 14 % |
| Primera unidad de UCI | ✓ | ✗ | ✗ |
| **Se conservan** | **17 de 17** | **5 de 17** | **7 de 17** |

En B1, «laboratorios más pedidos» da 9/10 y no 10/10 por un empate en el décimo puesto.

### Synthea

| Consulta | B1 (85) | MOSTLY (85) | SDV (85) | MOSTLY (925) |
|---|---|---|---|---|
| Pacientes por condición (top 10) | ✓ 10/10 | ✓ 6/10 | ✓ 7/10 | ✓ 8/10 |
| Condiciones más frecuentes (top 10) | ✓ 10/10 | ✓ 6/10 | ✓ 9/10 | ✓ 7/10 |
| Duración mediana del encuentro | ✓ | ✓ 8 % | ✗ 40 % | ✓ 13 % |
| Encuentros por paciente | ✓ | ✓ 3 % | ✓ 0 % | ✗ 24 % |
| % de pacientes fallecidos | ✓ | ✗ 100 % | ✗ 44 % | ✓ **5 %** |
| Edad mediana | ✓ | ✓ 9 % | ✓ 2 % | ✓ 2 % |
| Encuentros por clase | ✓ | ✓ | ✓ | ✓ |
| Pacientes por sexo | ✓ | ✓ | ✓ | ✓ |
| Pacientes por raza | ✓ | ✓ | ✓ | ✓ |
| Costo medio del encuentro | ✓ | ✓ 7 % | ✓ 1 % | ✓ 1 % |
| Observaciones más frecuentes (top 10) | ✓ 10/10 | ✓ 9/10 | ✗ 2/10 | ✓ 9/10 |
| Observaciones por encuentro | ✓ | ✗ 37 % | ✓ 0 % | ✗ 34 % |
| Encuentros por año | ✓ | ✗ | ✗ | ✗ |
| % de condiciones resueltas | ✓ | ✓ | ✓ | ✓ |
| **Se conservan** | **14 de 14** | **11 de 14** | **10 de 14** | **11 de 14** |

Tablas completas: `resultados/<entrenamiento>.md` y `.json`.

## Hallazgos

- **Para tests que consultan agregados, la anonimizada coherente es perfecta;** las sintéticas, no. Los errores de
  las sintéticas son exactamente los de las reglas de D2 y D3: una duración negativa o de 900 días no es un error de
  precisión, es un dato imposible.
- **MIMIC sufre más que Synthea** porque sus consultas dependen de fechas y de diagnósticos con miles de códigos;
  Synthea tiene pocos códigos y patrones muy regulares.
- **Entrenar con más pacientes arregla los eventos raros** (mortalidad), pero no las fechas.
- **Un test sobre los datos sintéticos que dependa de «alta después del ingreso» fallaría** con cualquiera de los dos
  generadores sin una capa de reparación.

## Limitaciones

- 17 y 14 consultas elegidas por nosotros; no salen de un caso de uso real de testing.
- Los umbrales de «se conserva» son una convención (los mismos para todas las candidatas).
- Las consultas corren en pandas sobre los Parquet, no en SQL sobre PostgreSQL.

## Evidencia

- `resultados/<entrenamiento>.json` y `.md`.
