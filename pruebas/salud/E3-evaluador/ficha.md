# E3m / E3s — Evaluador propio adaptado a salud — Validar (calidad, privacidad, riesgo)

**Quién / cuándo:** Jero (ejecutado por Claude Code a pedido de Jero), 2026-11-12.
**Fuente de cada dato:** P = prueba propia.

[← E3 sobre Pagila](../../E3-chequeos-propios/ficha.md) · [B1m / B1s](../B1-anon/ficha.md) ·
[D2m / D2s](../D2-mostlyai/ficha.md) · [D3m / D3s](../D3-sdv/ficha.md) · [E4m / E4s](../E4-syntherela/ficha.md) ·
[F1m utilidad](../F1-utilidad/ficha.md)

Una misma vara para comparar lo anonimizado (B1, PostgreSQL Anonymizer) y lo sintético (D2 MOSTLY AI, D3 SDV) sobre
las bases de salud.

## En pocas palabras

- **La anonimizada es la más útil y la menos privada:**
  - calidad SDMetrics 0,91 (MIMIC) y 0,90 (Synthea);
  - pero Anonymeter encuentra riesgo alto en MIMIC: singling out 0,72, inference 0,75 (riesgos de 0 a 1).
  - El 81 % de sus registros «paciente» está más cerca de un real que casi cualquier paciente de control.
  - Es lo esperable: son los mismos pacientes, con ids y fechas cambiados.
- **Las sintéticas son privadas:**
  - Anonymeter da riesgo de 0 a 0,08 en casi todos los ataques;
  - ninguna copia exacta de un paciente (salvo el 0,9 % con 925 pacientes de Synthea);
  - la distancia al real más cercano es igual o mayor que la del control.
- **Calidad de las sintéticas:** 0,68 a 0,77 con 47 u 85 pacientes, y **0,85** con 925. Entrenar con más pacientes
  sube la calidad sin subir el riesgo.
- **Códigos válidos:** B1 100 %. MOSTLY: 28 % (MIMIC) y 69 % a 91 % (Synthea). SDV: 55 % (MIMIC) y 100 % (Synthea).
- **Riesgo con ARX:** casi todos los registros «paciente» son únicos en todas las salidas, incluidas las sintéticas.
  En una sintética, «único» no identifica a nadie real, y por eso hay que leerlo junto con Anonymeter.
- **Rápido:** el evaluador entero tarda de 2 a 14 s por candidata (en Pagila, E3 tardaba minutos con Anonymeter
  multivariado).

## Entorno

- `.venv` del repo: Python 3.11.16, sdmetrics 0.25.0, anonymeter 1.1.0, sdv 1.32.1. ARX 3.9.2 en Docker
  (`ArxMedidor.java` de B3m / B3s).
- Script: `e3_salud.py` (esta carpeta). No modifica `pruebas/E3-chequeos-propios/evaluar_bd.py`.
- **Modo sin valores:** solo escribe conteos y métricas. Los registros para ARX quedan en
  `../B3-arx/salidas_grandes/` (fuera del repo).

```bash
.venv/bin/python pruebas/salud/E3-evaluador/e3_salud.py --entrenamiento mimic_47      # B1m, D2m, D3m
.venv/bin/python pruebas/salud/E3-evaluador/e3_salud.py --entrenamiento synthea_85    # B1s, D2s, D3s
.venv/bin/python pruebas/salud/E3-evaluador/e3_salud.py --entrenamiento synthea_925   # D2s con 925
```

### Qué cambió respecto de E3 sobre Pagila

| | E3 (Pagila) | E3m / E3s |
|---|---|---|
| Registro de privacidad | «persona» (cliente + dirección) | «paciente»: MIMIC sexo, edad, raza, seguro, idioma, estado civil; Synthea sexo, edad, raza, etnia, estado civil, condado |
| Secreto de *inference* | nombre, correo, teléfono | **diagnóstico** (MIMIC: grupo del diagnóstico principal; Synthea: primera condición) |
| Control | 200 clientes | pacientes de control de C1: 16 (MIMIC) y 226 (Synthea) |
| Bloques nuevos | — | reglas de negocio, códigos válidos contra el catálogo, riesgo con ARX |
| Entrada | bases en PostgreSQL | Parquet (D2, D3) y PostgreSQL (B1, control) |

### Arreglos en el camino

- **Códigos CIE con espacios:** MIMIC guarda `icd_code` como `char(7)` (rellenado con espacios); MOSTLY los devuelve
  sin espacios. Sin normalizar, el 0 % de los códigos de MOSTLY parecía válido y la base anonimizada no coincidía
  consigo misma en las consultas. Se quitan los espacios al leer, en todos los conjuntos.
- **Anonymeter 1.1.0** se llama con argumentos por nombre (como E3 sobre Pagila); la edad pasa a decimal porque
  numba no acepta enteros con nulos.

## Resultados

### MIMIC (entrenamiento: 47 pacientes; control: 16)

| Medición | B1 anonimizada | D2 MOSTLY AI | D3 SDV (5 tablas) |
|---|---|---|---|
| Calidad SDMetrics (global) | **0,91** | 0,70 | 0,69 |
| · formas de columnas | 0,70 | 0,80 | 0,79 |
| · tendencias de pares | 0,98 | 0,60 | 0,64 |
| · cardinalidad | 1,00 | 0,88 | 0,74 |
| · tendencias entre tablas | 0,97 | 0,54 | 0,58 |
| Códigos CIE que existen | 100 % | **28 %** | 55 % |
| Anonymeter: singling out | **0,72** (0,51–0,93) | 0,08 (0–0,36) | 0,08 (0–0,31)¹ |
| Anonymeter: linkability | 0,06 (0–0,24) | 0,06 (0–0,24) | 0 (0–0,23) |
| Anonymeter: inference (diagnóstico) | **0,75** (0,55–0,96) | 0 (0–0,15)¹ | 0 (0–0,15)¹ |
| DCR: copias exactas del registro | 8,5 % | 0 % | 0 % |
| DCR: % más cerca que el 5 % más cercano del control | **81 %** | 2 % | 0 % |
| ARX: registros únicos | 81 % | 100 % | 100 % |

### Synthea (entrenamiento: 85 pacientes; control: 226)

| Medición | B1 anonimizada | D2 MOSTLY AI | D3 SDV (4 tablas) |
|---|---|---|---|
| Calidad SDMetrics (global) | **0,90** | 0,77 | 0,68 |
| · tendencias entre tablas | 0,94 | 0,68 | 0,55 |
| Códigos de condición que existen | 100 % | 69 % | 100 % |
| Anonymeter: singling out | 0,26 (0,06–0,47) | 0 (0–0,11) | 0 |
| Anonymeter: linkability | 0,08 (0,01–0,15) | 0,02 (0–0,08)¹ | 0 (0–0,05)¹ |
| Anonymeter: inference (condición) | 0,87 (0,79–0,95)¹ | 0 (0–0,05) | 0,05 (0–0,10)¹ |
| DCR: copias exactas | 0 % | 0 % | 0 % |
| ARX: registros únicos | 86 % | 100 % | 100 % |

### Synthea con 925 pacientes (control: 226)

| Medición | D2 MOSTLY AI |
|---|---|
| Calidad SDMetrics (global) | **0,85** (formas 0,86; pares 0,83; cardinalidad 0,90; entre tablas 0,79) |
| Códigos de condición que existen | 91 % |
| Anonymeter (singling out, linkability, inference) | 0 / 0 / 0,04 |
| DCR: copias exactas | 0,9 % |
| ARX: registros únicos | 91 % (real: 74 %) |

¹ Ataque no concluyente: no supera al azar (`tasa_ataque <= tasa_azar` en Anonymeter).

### Tiempo

De 2 a 14 s por candidata en total: calidad 0,6 a 9 s; Anonymeter y DCR 0,1 a 2,6 s; ARX en Docker 1,3 a 1,9 s.

## Hallazgos

- **La pregunta no es «anonimizar o sintetizar», sino para qué.** B1 conserva todo lo que se consulta (F1m: 17 de
  17) y la coherencia, pero cualquiera que conozca algunos datos de un paciente lo encuentra (singling out 0,72) y
  le infiere el diagnóstico (0,75). Las sintéticas protegen, pero rompen reglas y catálogos (D2, D3).
- **Con bases chicas, Anonymeter es poco concluyente:** con 16 pacientes de control, los intervalos van de 0 a 0,3
  o más. Synthea, con 226 de control, da intervalos más cerrados. Para la MIMIC completa habría control de sobra.
- **El riesgo de ARX («únicos») no sirve solo para datos sintéticos:** un registro sintético único no corresponde a
  nadie. Hay que medir la distancia a los reales (DCR) o atacar (Anonymeter), como hace este evaluador.
- **Normalizar antes de comparar:** un detalle de formato (espacios en `char(n)`) cambiaba los resultados de
  «inválido» a «válido». El evaluador del sistema tiene que normalizar tipos y formatos.

## Limitaciones

- Anonymeter es aleatorio (linkability e inference no fijan semilla): de una corrida a otra los riesgos cambian
  algunos centésimos (por ejemplo, inference de B1 en MIMIC dio 0,63, 0,69, 0,57 y 0,75 en cuatro corridas). Se
  informa la última.
- El grupo de diagnóstico (versión CIE + primer carácter) es grueso.
- Calidad SDMetrics sobre las tablas del conjunto, con los metadatos de D3.

## Evidencia

- `resultados/<entrenamiento>.json`: por candidata, integridad, reglas, códigos, calidad (con propiedades),
  privacidad (riesgos con intervalo, tasas de ataque, azar y control) y riesgo con ARX, con el tiempo de cada bloque.
- `log_<entrenamiento>.txt`: salida de la última corrida.
