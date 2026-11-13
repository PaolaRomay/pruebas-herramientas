# D2m / D2s — MOSTLY AI sobre MIMIC-IV demo y Synthea — Sintetizar

**Quién / cuándo:** Jero (ejecutado por Claude Code a pedido de Jero), 2026-11-12.
**Fuente de cada dato:** P = prueba propia, salvo donde dice D.

[← D2 sobre Pagila](../../D2-mostlyai/ficha.md) · [D3m / D3s SDV](../D3-sdv/ficha.md) ·
[E3m / E3s evaluador](../E3-evaluador/ficha.md) · [F1m utilidad](../F1-utilidad/ficha.md) ·
[C1m / C1s subconjunto](../C1-subconjunto/ficha.md)

## En pocas palabras

- **Escala: no es un problema en 16 GB.**
  - Entrenar con 925 pacientes de Synthea (770 000 filas, 4 tablas) tardó 21 minutos con 3,6 GB.
  - Generar 10 000 pacientes de MIMIC (6,7 millones de filas, 5 tablas) tardó 4 minutos con 1,8 GB.
  - El límite de memoria no apareció en ningún escalón.
- **Integridad perfecta:** 0 claves repetidas y 0 filas sin padre en todas las salidas.
- **Privacidad muy buena:** ningún paciente copiado; en las tablas de eventos, menos del 1,5 % de filas idénticas a
  una real (filas comunes, como una vacuna de rutina). Anonymeter: riesgo ≈ 0 (ver E3).
- **Pero no aprende las reglas de negocio:**
  - **fechas:** con los 47 pacientes de MIMIC, el alta queda antes del ingreso en la mitad de las internaciones; con
    los 925 de Synthea, el 30 % de los encuentros termina antes de empezar;
  - **muerte:** ninguna internación sintética de MIMIC termina en muerte (6 % en la real); con 85 pacientes de
    Synthea, ningún fallecido;
  - **códigos:** inventa códigos carácter por carácter. En MIMIC, solo el 28 % de los códigos CIE generados existe en
    el catálogo; en Synthea, el 69 % con 85 pacientes y el 91 % con 925.
- **Con más datos mejora mucho:** con 925 pacientes, mortalidad 12,0 % (real 12,6 %), sexo, raza, edad y costos casi
  iguales; calidad SDMetrics 0,85; 11 de 14 consultas de referencia se conservan. Con 47 pacientes, 5 de 17.
- **Conclusión:** sirve para volumen y privacidad. **No sirve sola** para datos que tienen que respetar reglas
  temporales o catálogos: hace falta una capa que las imponga o las corrija después.

## Entorno

- Equipo: Mac M5 Pro, 16 GB, macOS 26.6.2. **Entorno de Python aparte** (`../.venv`, Python 3.12.0), el mismo de D2
  sobre Pagila: mostlyai 6.1.4, mostlyai-engine 2.7.0, torch 2.13.0, pandas 3.0.6, numpy 2.5.3. Corre en CPU (el
  motor no usa la GPU de la Mac; ver D2 sobre Pagila).
- Modo local del SDK, sin conexión a ningún servicio.
- Script: `d2_mostly_salud.py` (esta carpeta), con tres pasos: `exportar` (.venv del repo), `entrenar` (entorno de
  MOSTLY) y `evaluar` (.venv del repo).
- Los Parquet reales y sintéticos quedan en `salidas_grandes/` (fuera del repo); al repo van solo métricas.

```bash
.venv/bin/python pruebas/salud/D2-mostlyai/d2_mostly_salud.py exportar --conjunto mimic_47
../.venv/bin/python pruebas/salud/D2-mostlyai/d2_mostly_salud.py entrenar --conjunto mimic_47
.venv/bin/python pruebas/salud/D2-mostlyai/d2_mostly_salud.py evaluar --conjunto mimic_47
# ídem con synthea_85 y synthea_925
```

### Conjuntos y modelo

| Conjunto | Origen | Pacientes | Tablas (contexto) | Filas |
|---|---|---|---|---|
| `mimic_47` | subconjunto `mimic_c1_50` (C1m) | 47 | `patients` → `admissions` → (`diagnoses_icd`, `icustays`); `patients` → `labevents` | 50 044 |
| `synthea_85` | subconjunto `synthea_c1_10` (C1s) | 85 | `patients` → `encounters` → (`conditions`, `observations`) | 39 115 |
| `synthea_925` | `synthea_p1000` sin los pacientes de control | 925 | ídem | 769 388 |

- Todas las FK son **de contexto** (la cadena paciente → internación/encuentro → evento), para que MOSTLY aprenda
  las secuencias de cada paciente.
- Columnas: las demográficas, fechas, códigos y valores clínicos de cada tabla (lista en `CONJUNTOS` del script).
  No se incluyeron identificadores directos.
- `observations` de Synthea sin encuentro (el 3,7 %) quedó afuera: no tiene padre de contexto.
- `max_training_time`: 10 minutos por tabla (valor por defecto). El resto, por defecto.

## Resultados

### Escala: tiempo y memoria

| Paso | Conjunto | Pacientes | Filas | Tiempo | Memoria máxima (proceso + hijos) |
|---|---|---|---|---|---|
| Entrenar | `mimic_47` | 47 | 50 044 | 86 s | 2,8 GB |
| Entrenar | `synthea_85` | 85 | 39 115 | 276 s | 3,1 GB |
| Entrenar | `synthea_925` | 925 | 769 388 | **1 237 s** | **3,6 GB** |
| Generar | `mimic_47` | 47 | 29 063 | 19 s | 4,3 GB |
| Generar | `mimic_47` | 1 000 | 680 843 | 37 s | 1,7 GB |
| Generar | `mimic_47` | 5 000 | 3 330 390 | 136 s | 1,9 GB |
| Generar | `mimic_47` | **10 000** | **6 705 257** | **253 s** | **1,8 GB** |
| Generar | `synthea_85` | 85 | 27 132 | 21 s | 4,2 GB |
| Generar | `synthea_925` | 925 | 412 948 | 132 s | 4,5 GB |

- La generación crece de forma lineal con los pacientes (unos 25 s cada 1 000) y la memoria no crece: MOSTLY genera
  por lotes. El pico de unos 4 GB aparece en la primera generación de cada conjunto (cargar el modelo).
- En Pagila (D2), la generación llegó a 8,1 GB por un fallo del modelo de FK no-contexto. Acá no hubo FK
  no-contexto.

### Reglas de negocio (violaciones)

| Regla | MIMIC real (47) | MOSTLY 47 | MOSTLY 1 000 | MOSTLY 10 000 |
|---|---|---|---|---|
| Alta >= ingreso | 0 | **39 de 82** | 990 de 1 914 | 9 132 de 18 323 |
| `hospital_expire_flag` coherente con la muerte | 0 | 6 | 130 | 1 224 |
| Emergencia: salida >= registro | 0 | 8 | 222 | 1 938 |
| UCI dentro de su internación | 0 | 31 de 39 | 641 de 849 | 6 230 de 8 282 |
| UCI: salida >= entrada | 0 | 17 | 455 | 4 391 |
| `los` = salida − entrada de UCI | 0 | 39 de 39 | 849 | 8 282 |
| Edad en la internación >= 18 | 0 | 1 | 255 | 2 114 |
| Muerte dentro de la internación / `dod` | 0 | 0 | 0 | 0 (no hay muertes) |

| Regla | Synthea real 85 | MOSTLY 85 | Synthea real 925 | MOSTLY 925 |
|---|---|---|---|---|
| Encuentro: fin >= inicio | 0 | **1 642 de 3 305** | 0 | **12 468 de 41 541** |
| Encuentro después del nacimiento | 0 | 110 | 0 | 2 525 |
| Encuentro antes de la muerte (+1 día) | 8 | 0 | 95 | 4 494 |
| Muerte >= nacimiento | 0 | 0 | 0 | 24 |
| Condición: fin >= inicio | 0 | 530 | 0 | 5 404 |
| Observación dentro de su encuentro (±1 día) | 28 | 19 614 | 439 | 122 746 |

### Distribuciones

| Estadística | MIMIC real | MOSTLY 47 | MOSTLY 10 000 |
|---|---|---|---|
| Internaciones por paciente | 2,45 | 1,74 | 1,83 |
| Diagnósticos por internación | 15,4 | 14,2 | 14,6 |
| % mujeres | 44,7 | 46,8 | 45,9 |
| Edad mediana | 61 | 60 | 60 |
| Duración mediana de la internación (días) | 5,6 | **925,5** | 12,0 |
| % internaciones con muerte | 6,1 | **0** | **0** |
| Códigos CIE distintos | 797 | 1 096 | 71 639 |

| Estadística | Synthea real 85 | MOSTLY 85 | Synthea real 925 | MOSTLY 925 |
|---|---|---|---|---|
| Encuentros por paciente | 37,8 | 38,9 | 59,2 | 44,9 |
| Condiciones por paciente | 28,8 | 25,5 | 35,2 | 30,6 |
| % mujeres | 58,8 | 67,1 | 48,5 | 48,8 |
| Edad mediana | 45,4 | 41,5 | 45,4 | 44,5 |
| % fallecidos | 10,6 | **0** | 12,6 | 12,0 |
| Duración mediana del encuentro (horas) | 0,52 | 0,48 | 0,66 | 0,58 |
| Códigos de condición distintos | 167 | **16** | 416 | 75 |

### Integridad y copias

- **0 claves repetidas y 0 filas sin padre** en las 7 salidas.
- Filas idénticas a una real (sin contar ids): 0 pacientes, 0 internaciones o encuentros en los conjuntos chicos.
  Diagnósticos de MIMIC: 14 de 1 163. Synthea 925: 95 encuentros, 416 condiciones y 135 observaciones (filas muy
  comunes: misma clase, mismo código y fechas sin hora).

## Hallazgos

- **La escala no limita en este rango:** entrenar con casi un millón de filas entra en 3,6 GB y generar 10 000
  pacientes, en menos de 2 GB. Para la MIMIC completa, el entrenamiento crecería con las filas (`chartevents`); la
  generación, no.
- **Las reglas temporales se pierden siempre, con pocos o muchos datos.** MOSTLY aprende cada columna de fecha por
  separado, no la diferencia entre fechas. Es el mismo problema que en Pagila (38 % de devoluciones antes del
  alquiler), más grave en salud: un alta antes del ingreso o una medición fuera de la estadía no tienen sentido
  clínico.
- **Los códigos se inventan.** El modelo genera texto carácter por carácter: con pocos datos, la mayoría de los
  códigos CIE no existen. Con 925 pacientes, el 91 % de los códigos SNOMED de Synthea sí existe, pero solo usa 75
  de los 416 reales (la protección de valores raros los reemplaza).
- **Con pocos pacientes, los eventos raros desaparecen:** ninguna muerte con 47 u 85 pacientes. La protección de
  valores raros de MOSTLY (D) recorta lo que aparece poco, y en una base chica la muerte es rara.
- **El tamaño del entrenamiento importa más que el del resultado:** generar 10 000 pacientes a partir de 47 no
  mejora nada; entrenar con 925 sí.
- **Para el sistema:** usar MOSTLY (o un generador parecido) con una capa posterior de **reparación por reglas**
  (ordenar fechas, desplazar eventos dentro de su encuentro, mapear códigos al catálogo) o de rechazo. Las reglas
  que se usaron acá para medir son las mismas que harían falta para reparar.

## Limitaciones

- Una sola corrida por conjunto (MOSTLY no es determinista sin semilla; no se fijó).
- Configuración por defecto (10 minutos por tabla, sin ajuste de hiperparámetros ni reglas de MOSTLY).
- MIMIC: entrenamiento con 47 pacientes, poco para un generador. La MIMIC completa (con credenciales) sería la
  prueba justa.
- Synthea es sintético: el generador aprende las reglas de Synthea, no de pacientes reales.

## Evidencia

- `resultados/<conjunto>.json`: exportación, entrenamiento, cada escalón de generación (tiempo, memoria, filas) y
  evaluación (reglas, integridad, estadísticas, copias).
- Calidad, privacidad, utilidad y fidelidad multitabla de estas salidas: E3m / E3s, F1m / F1s, E4m / E4s.
