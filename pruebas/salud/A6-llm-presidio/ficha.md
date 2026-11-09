# A6m / A6s — LLM local + Presidio combinados, sobre MIMIC-IV demo y Synthea — Detectar

**Quién / cuándo:** Jero (ejecutado por Claude Code a pedido de Jero), 2026-11-08.
**Fuente de cada dato:** P = prueba propia.

[← A1m / A1s Presidio](../A1-presidio/ficha.md) · [A2m / A2s LLM local](../A2-llm-local/ficha.md) ·
[Lista de referencia](../../_bases/referencia/taxonomia.md)

¿Mejora la detección si se combinan las dos señales: el LLM, que lee el significado de la columna, y Presidio, que
reconoce formatos en los valores? No se corre nada nuevo: se combinan, columna por columna, las salidas ya guardadas.

## En pocas palabras

- **«El LLM propone y Presidio confirma» (intersección) empeora:** precisión 1,00 en MIMIC, pero el recall cae de
  0,79 a 0,57–0,61 (F1 0,73–0,76). Presidio no «confirma» lo que no tiene formato: descarta 46 columnas de salud y
  los demográficos que el LLM había encontrado bien.
- **La unión** sube el recall (0,91 en MIMIC, 0,94–0,96 en Synthea) y da el mejor F1 de MIMIC (**0,91**), pero lo
  que agrega Presidio son **aciertos casuales** (ids y datos de salud con etiquetas como `US_BANK_NUMBER` o
  `US_DRIVER_LICENSE`) junto con todos sus falsos positivos en catálogos. En Synthea no mejora (0,86–0,87).
- **La cascada** (decide el LLM; Presidio agrega solo formatos fuertes: SSN, correo, teléfono, tarjeta, IP) **queda
  igual que el LLM solo**: 0,88 y 0,87. El LLM ya había encontrado esos formatos por el nombre de la columna.
- **Conclusión:** sobre estas bases, Presidio no le agrega nada confiable al LLM para clasificar columnas. Su lugar
  en el sistema es otro: **el texto libre** (detectar entidades dentro de un valor) y la anonimización.

## Entorno

- Entradas (sin volver a correr nada):
  - LLM: A2 `a2b` (esquema + valores) y `a2a` (solo esquema), corrida 1 (las 3 corridas son idénticas);
  - Presidio: A1 `structured:most_common umbral 0.0`, la mejor configuración de A1m / A1s.
- Script: `a6_combinar.py` (esta carpeta). Métricas: `pruebas/salud/comparar_salud.py`.

```bash
.venv/bin/python pruebas/salud/A6-llm-presidio/a6_combinar.py
.venv/bin/python pruebas/salud/comparar_salud.py --base mimic   # y synthea
```

### Reglas de combinación

| Variante | Marcada si… | Etiqueta |
|---|---|---|
| `interseccion` | la marcan el LLM **y** Presidio (la idea original de A6: el LLM propone, Presidio confirma) | la del LLM |
| `union` | la marca el LLM **o** Presidio | la del LLM; si solo la marca Presidio, la de Presidio |
| `cascada` | la marca el LLM, **o** Presidio detecta un formato fuerte (`US_SSN`, `EMAIL_ADDRESS`, `PHONE_NUMBER`, `CREDIT_CARD`, `IP_ADDRESS`) | ídem |

Los formatos fuertes son los reconocedores de Presidio con patrón y validación propios. Quedan fuera los que en A1
dieron aciertos casuales (`DATE_TIME`, `US_BANK_NUMBER`, `US_DRIVER_LICENSE`, `PERSON`).

## Qué se midió y resultado

| Base | Prueba | TP | FP | FN | TN | Precisión | Recall | F1 |
|---|---|---|---|---|---|---|---|---|
| MIMIC | *Presidio solo (A1m)* | *171* | *21* | *76* | *43* | *0,89* | *0,69* | *0,78* |
| MIMIC | *LLM solo, `a2b` (A2m)* | *199* | *6* | *48* | *58* | *0,97* | *0,81* | *0,88* |
| MIMIC | intersección (`a2b`) | 150 | 0 | 97 | 64 | **1,00** | 0,61 | 0,76 |
| MIMIC | intersección (`a2a`) | 142 | 0 | 105 | 64 | **1,00** | 0,57 | 0,73 |
| MIMIC | unión (`a2a`) | 224 | 22 | 23 | 42 | 0,91 | **0,91** | **0,91** |
| MIMIC | unión (`a2b`) | 220 | 27 | 27 | 37 | 0,89 | 0,89 | 0,89 |
| MIMIC | cascada (`a2b`) | 200 | 6 | 47 | 58 | 0,97 | 0,81 | 0,88 |
| Synthea | *Presidio solo (A1s)* | *127* | *39* | *32* | *21* | *0,77* | *0,80* | *0,78* |
| Synthea | *LLM solo, `a2b` (A2s)* | *135* | *14* | *24* | *46* | *0,91* | *0,85* | ***0,88*** |
| Synthea | intersección (`a2b`) | 110 | 13 | 49 | 47 | 0,89 | 0,69 | 0,78 |
| Synthea | unión (`a2b`) | 152 | 40 | 7 | 20 | 0,79 | **0,96** | 0,87 |
| Synthea | cascada (`a2b`) | 135 | 15 | 24 | 45 | 0,90 | 0,85 | 0,87 |

La etiqueta queda bien en todas (45/45 en MIMIC; 40 o 41 de 41 en Synthea): la pone el LLM.
Tablas completas: `resultados_comparados/salud/<base>/deteccion_resumen.md`.

### Qué agrega Presidio en la unión (`a2a`)

| | MIMIC | Synthea |
|---|---|---|
| Columnas que marca Presidio y el LLM no | 64 | 52 |
| … sensibles (aciertos) | 29: 28 de salud, 1 profesional | 20: 17 de salud, 3 ids |
| … con qué etiqueta de Presidio | `DATE_TIME`, `PERSON`, `US_DRIVER_LICENSE`, `US_BANK_NUMBER`, `NRP` | `US_BANK_NUMBER`, `US_DRIVER_LICENSE`, `DATE_TIME` |
| … no sensibles (falsos positivos) | 21: 14 catálogos, 7 técnicas | 27: 18 catálogos, 9 técnicas |
| … dudosas (no cuentan) | 14 ids de registro | 5 ids de registro |

Ninguno de los 29 aciertos en MIMIC tiene la etiqueta correcta: Presidio marca, por ejemplo, un `itemid` porque
parece una fecha. El recall sube, pero por casualidad: en otra base (con otros formatos de id) no se repetiría.

### Qué pierde la intersección

Sensibles que el LLM marcó bien y Presidio no confirma: en MIMIC, 46 de salud, 4 demográficos, 2 profesionales y 1
de texto libre; en Synthea, 17 de salud, 3 demográficos, 1 identificador directo y 1 profesional.

## Hallazgos

- **Presidio no sirve como «confirmación» de columnas:** solo confirma lo que tiene formato, y la mitad de lo
  sensible en una base de salud no lo tiene (diagnósticos, medicamentos, sexo, estado civil).
- **La unión parece la mejor en MIMIC, pero por las razones equivocadas.** Las columnas que agrega Presidio son
  aciertos casuales con etiqueta errónea, más todos sus falsos positivos en catálogos. Para el sistema, es mejor
  cubrir ese hueco del LLM (datos de salud «indirectos»: `itemid`, unidades, cantidades) con una **política más
  explícita** o una regla del usuario, que con aciertos casuales.
- **La cascada no cambia nada en estas bases** porque los formatos fuertes (SSN, teléfono) tienen nombres de columna
  claros y el LLM ya los encuentra. Puede servir en bases con nombres poco claros (la variante ofuscada de A2 lo
  sugiere); queda como red de seguridad barata.
- **Diseño que sale de A1, A2 y A6:** el LLM clasifica las columnas; Presidio (o GLiNER) trabaja **dentro** de los
  valores de texto libre, donde una columna mezcla datos personales con texto común.

## Limitaciones

- Combina las salidas guardadas: hereda las limitaciones de A1m / A1s y A2m / A2s (un modelo, una política, lista
  sin anotación manual independiente).
- No se probó combinar con la variante manual de Presidio (fracción de valores), solo con la mejor configuración.

## Evidencia

- `resultados/<base>/a6<m|s>_columnas.csv`: por columna, la marca combinada y las marcas y entidades del LLM y de
  Presidio.
- `resultados_comparados/salud/<base>/`: métricas, matriz por columna y resumen.
