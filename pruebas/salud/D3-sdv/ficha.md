# D3m / D3s — SDV (HMASynthesizer) sobre MIMIC-IV demo y Synthea — Sintetizar

**Quién / cuándo:** Jero (ejecutado por Claude Code a pedido de Jero), 2026-11-12.
**Fuente de cada dato:** P = prueba propia, salvo donde dice D.

[← D2m / D2s MOSTLY AI](../D2-mostlyai/ficha.md) · [E3m / E3s evaluador](../E3-evaluador/ficha.md) ·
[F1m utilidad](../F1-utilidad/ficha.md)

Comparación de referencia para MOSTLY AI: el sintetizador multitabla clásico de SDV (HMA, modelos estadísticos
jerárquicos) sobre los mismos datos, con la misma evaluación.

## En pocas palabras

- **Muy rápido y liviano:** 3 a 5 tablas en menos de 2 minutos y menos de 0,6 GB.
- **Integridad perfecta** (0 claves repetidas, 0 filas sin padre) y **la misma cantidad de filas** que la base real.
- **Tampoco respeta las reglas temporales:** con 5 tablas de MIMIC, 48 de 115 altas antes del ingreso; en Synthea,
  1 530 de 3 214 encuentros que terminan antes de empezar. Agregar tablas no lo empeora ni lo mejora.
- **Respeta los catálogos más que MOSTLY:** en Synthea, el 100 % de los códigos existe (elige entre los reales);
  en MIMIC, el 55 % (MOSTLY: 28 %).
- **Peor calidad global y peor utilidad que MOSTLY** con los mismos datos: SDMetrics 0,69 contra 0,70 (MIMIC) y
  0,68 contra 0,77 (Synthea); consultas de referencia que se conservan: 7 de 17 y 10 de 14.
- **Hubo que esquivar un error de la librería:** RDT 1.19.0 falla con categóricas que tienen nulos.

## Entorno

- Equipo: Mac M5 Pro, 16 GB, macOS 26.6.2. `.venv` del repo: Python 3.11.16, **SDV 1.32.1** (ya instalado para E1).
  Licencia de SDV: Business Source License (D), uso no comercial y de investigación permitido.
- Mismos Parquet de entrada que D2 (paso `exportar` de `d2_mostly_salud.py`) y misma evaluación.
- Script: `d3_sdv_salud.py` (esta carpeta). Sintéticos en `salidas_grandes/` (fuera del repo).

```bash
.venv/bin/python pruebas/salud/D3-sdv/d3_sdv_salud.py --conjunto mimic_47 --tablas 3   # y 5
.venv/bin/python pruebas/salud/D3-sdv/d3_sdv_salud.py --conjunto synthea_85 --tablas 3 # y 4
```

- **Metadatos explícitos:** PK, FK y tipo de cada columna se declaran en el script (no se usa la detección
  automática). Las fechas son `datetime`; los códigos y banderas, categóricos.
- **Variantes:** 3 tablas (`patients`, `admissions`, `diagnoses_icd` / `patients`, `encounters`, `conditions`) y la
  base completa del conjunto (5 tablas en MIMIC, 4 en Synthea).
- `HMASynthesizer` con valores por defecto, `sample(scale=1.0)`.
- **Error de RDT 1.19.0:** `OverflowError: Range exceeds valid bounds` al codificar una categórica con nulos
  (`discharge_location`, `marital_status`). El `UniformEncoder` no encuentra el intervalo de `NaN`. Se reemplazan
  los nulos por una marca antes de entrenar y se vuelven a nulos al generar.

## Resultados

| Conjunto | Tablas | Entrenar | Generar | Memoria | Filas generadas |
|---|---|---|---|---|---|
| `mimic_47` | 3 | 1,3 s | 1,6 s | 0,4 GB | 1 936 |
| `mimic_47` | 5 | 5,9 s | 8,7 s | 0,6 GB | 50 044 |
| `synthea_85` | 3 | 4,2 s | 15,2 s | 0,4 GB | 5 744 |
| `synthea_85` | 4 | 32,8 s | 76,8 s | 0,5 GB | 39 115 |

### Reglas de negocio (violaciones)

| Regla | MIMIC real | SDV 3 tablas | SDV 5 tablas | MOSTLY (D2m) |
|---|---|---|---|---|
| Alta >= ingreso | 0 | 60 de 115 | 48 de 115 | 39 de 82 |
| Muerte dentro de la internación | 0 | 4 | 4 | 0 (no hay muertes) |
| `hospital_expire_flag` coherente | 0 | 20 | 10 | 6 |
| UCI dentro de su internación | 0 | — | 63 de 66 | 31 de 39 |
| `dod` = día de la muerte | 0 | — | 4 | 0 |
| Edad en la internación >= 18 | 0 | — | 14 | 1 |

| Regla | Synthea real | SDV 3 tablas | SDV 4 tablas | MOSTLY (D2s 85) |
|---|---|---|---|---|
| Encuentro: fin >= inicio | 0 | 1 496 de 3 214 | 1 530 de 3 214 | 1 642 de 3 305 |
| Encuentro después del nacimiento | 0 | 198 | 184 | 110 |
| Encuentro antes de la muerte (+1 día) | 8 | — | 472 | 0 |
| Condición: fin >= inicio | 0 | 548 | 517 | 530 |
| Observación dentro de su encuentro | 28 | — | 31 283 de 33 371 | 19 614 |

### Distribuciones (base completa del conjunto)

| Estadística | MIMIC real | SDV 5 tablas | Synthea real | SDV 4 tablas |
|---|---|---|---|---|
| Hijos por padre (internaciones, encuentros…) | — | iguales a la real (HMA conserva los conteos) | — | iguales |
| % mujeres | 44,7 | 55,3 | 58,8 | 64,7 |
| Edad mediana | 61 | 60 | 45,4 | 44,6 |
| Duración mediana de la internación / encuentro | 5,6 días | 13,9 días | 0,52 h | 0,31 h |
| Mortalidad | 6,1 % de internaciones | 3,5 % | 10,6 % de pacientes | 15,3 % |
| Códigos distintos | 797 CIE | 483 | 167 | 135 |

### Copias

Filas idénticas a una real (sin ids): 2 pacientes y 217 diagnósticos en MIMIC 5 tablas (con 3 columnas, `seq_num`,
código y versión, coincidir es fácil); 0 en Synthea 4 tablas.

## Hallazgos

- **HMA conserva la estructura (conteos de hijos) y elige valores reales de las categóricas:** por eso todos los
  códigos de Synthea existen y la cardinalidad es exacta. Pero modela cada columna con una distribución marginal y
  correlaciones simples: las fechas pierden su orden igual que con MOSTLY.
- **Rapidez:** 10 a 100 veces más rápido que MOSTLY en estos tamaños. Sirve como generador de base para pruebas
  funcionales donde importa la forma de los datos y no su realismo.
- **Más tablas no rompen nada** (a diferencia de D6 en Pagila con REaLTabFormer), pero tampoco mejoran las reglas.
- **El error con nulos** es el tipo de problema que el sistema tiene que absorber: un dato real (estado civil
  desconocido) rompe la librería con un mensaje que no dice qué columna es.

## Limitaciones

- Una corrida por variante; SDV no fija semilla por defecto. Las salidas `synthea_85_3t` se regeneraron una vez
  (la segunda corrida es la que está en los resultados).
- No se probaron otros sintetizadores de SDV (el multitabla gratuito es HMA) ni restricciones (*constraints*) de
  SDV, que podrían imponer `alta >= ingreso` dentro de una tabla. **Queda como prueba pendiente.**
- Las corridas de `mimic_47` (3 y 5 tablas) y `synthea_85` (4 tablas) compartieron la máquina con la prueba F2 del
  LLM, que usa la GPU y unos 9 GB de memoria. Sus tiempos pueden estar algo inflados. La de `synthea_85` con 3
  tablas se repitió sola.

## Evidencia

- `resultados/<conjunto>_<n>t.json`: entorno, tiempos, filas, integridad, reglas, estadísticas y copias.
- Calidad, privacidad, utilidad y fidelidad multitabla: E3m / E3s, F1m / F1s, E4m / E4s.
