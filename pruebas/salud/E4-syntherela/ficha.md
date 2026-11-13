# E4m / E4s — SyntheRela sobre las salidas de D2 y D3 — Validar (fidelidad multitabla)

**Quién / cuándo:** Jero (ejecutado por Claude Code a pedido de Jero), 2026-11-12.
**Fuente de cada dato:** P = prueba propia, salvo donde dice D.

[← D2m / D2s MOSTLY AI](../D2-mostlyai/ficha.md) · [D3m / D3s SDV](../D3-sdv/ficha.md) ·
[E3m / E3s evaluador](../E3-evaluador/ficha.md)

## Qué es

**SyntheRela** (D): biblioteca de evaluación de datos sintéticos **relacionales** (versión 0.0.4, PyPI). Además de
métricas por columna y por tabla, mide si se conservan las **relaciones entre tablas**:

- **Cardinalidad** (`CardinalityShapeSimilarity`): compara la distribución de «hijos por padre» (internaciones por
  paciente, diagnósticos por internación…) con una prueba de Kolmogorov-Smirnov. Estadístico 0 = igual, 1 = distinta.
- **Detección agregada** (`AggregationDetection`): un clasificador (XGBoost) intenta distinguir filas reales de
  sintéticas de una tabla, usando también **agregados de sus tablas hijas** (cuántas internaciones, promedio de
  laboratorios…). Exactitud 0,5 = indistinguibles; 1 = las distingue siempre.
- **MMD por tabla** (`MaximumMeanDiscrepancy`): distancia entre distribuciones de una tabla. 0 = iguales.

## En pocas palabras

- **Un clasificador distingue casi siempre lo sintético de lo real** cuando mira cada paciente con sus hijos:
  exactitud de 0,74 a 0,98 en `patients` y de 0,84 a 1,00 en internaciones o encuentros. Ningún generador llega
  cerca de 0,5.
- **MOSTLY conserva mejor la cantidad de hijos por padre** (estadístico KS 0,04 a 0,15) que SDV (0,10 a 0,34), salvo
  que SDV copia exactamente los conteos de la real en la cantidad total.
- **Con más pacientes de entrenamiento, MOSTLY mejora:** con 925 pacientes de Synthea, KS 0,06 en
  pacientes → encuentros y MMD de `patients` 0,008 (con 85: 0,11 y 0,23).
- **Rápido:** 17 a 36 s por par real/sintético.

## Entorno

- **Entorno de Python aparte**, fuera del repo (`../herramientas-externas/venv-syntherela`, Python 3.11.16):
  syntherela 0.0.4 fija **scikit-learn 1.3.1**; el `.venv` del repo tiene 1.9.1 y bajarlo podía romper otras pruebas.
  Trae sdv 1.39.0, sdmetrics 0.33.0, xgboost 1.7.6, numpy 1.26.4 y pyarrow 18.1.0 (pyarrow 19 o más pide numpy 2).
- Script: `e4_syntherela.py` (esta carpeta). Lee los mismos Parquet que D2 y D3 (con la misma normalización de
  formatos que E3).

```bash
../herramientas-externas/venv-syntherela/bin/python pruebas/salud/E4-syntherela/e4_syntherela.py
```

### Ajustes

- **Detección solo sobre las tablas padre** (`patients` e internaciones o encuentros): es donde SyntheRela agrega
  las tablas hijas. Sobre `labevents` u `observations` la primera corrida no terminó en 10 minutos.
- **MMD sobre una muestra de 5 000 filas por tabla:** su costo crece con el cuadrado de las filas. En
  `diagnoses_icd` de MIMIC no aplica (no tiene columnas numéricas ni fechas).
- MOSTLY devuelve vacíos de dos tipos (`pd.NA` y `None`) en una misma columna; los codificadores de scikit-learn no
  lo aceptan. Se unifican como `NaN`.

## Resultados

| Conjunto | Generador | Cardinalidad (KS, por relación) | Detección: `patients` | Detección: internaciones / encuentros | MMD (`patients`) |
|---|---|---|---|---|---|
| MIMIC 47 | MOSTLY AI | pac→int 0,15; int→diag 0,15; int→UCI 0,04; pac→lab 0,15 | 0,98 | 0,84 | 0,59 |
| MIMIC 47 | SDV HMA | pac→int 0,34; int→diag 0,31; int→UCI 0,10; pac→lab 0,28 | 0,80 | 0,98 | 0,02 |
| Synthea 85 | MOSTLY AI | pac→enc 0,11; enc→cond 0,06; enc→obs 0,13 | 0,74 | 1,00 | 0,23 |
| Synthea 85 | SDV HMA | pac→enc 0,13; enc→cond 0,17; enc→obs 0,25 | 0,99 | 1,00 | 0,04 |
| Synthea 925 | MOSTLY AI | pac→enc 0,06; enc→cond 0,06; enc→obs 0,17 | 0,80 | 0,95 | **0,008** |

MMD de las otras tablas y los valores completos (p-valores de KS, error estándar de la detección):
`resultados/e4.json`.

## Hallazgos

- **SyntheRela confirma lo que E3 mide con reglas:** las tablas de eventos (internaciones, encuentros) son fáciles de
  distinguir, porque sus fechas están desordenadas y sus duraciones no tienen sentido. La detección no dice por qué;
  las reglas de E3, sí.
- **Las dos métricas multitabla miran cosas distintas:** SDV conserva los totales y elige valores reales (MMD de
  `patients` bajo), pero reparte mal los hijos (KS alto). MOSTLY reparte mejor los hijos, pero cambia las
  distribuciones de los pacientes con pocos datos.
- **Instalarlo fue la parte más difícil:** dependencias fijas viejas (scikit-learn 1.3.1, numpy 1) obligan a un
  entorno aparte. Para el sistema, conviene usar su idea (detección con agregados de hijas) más que la biblioteca.

## Limitaciones

- Una corrida; la detección usa validación cruzada de 5 particiones con semilla fija.
- Detección solo en tablas padre; MMD sobre muestras de 5 000 filas.
- Bases chicas (47 y 85 pacientes): el clasificador tiene pocas filas en `patients`.

## Evidencia

- `resultados/e4.json`.
