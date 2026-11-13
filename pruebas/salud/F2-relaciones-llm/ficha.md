# F2m / F2s — El LLM local propone relaciones entre tablas — Entender el esquema

**Quién / cuándo:** Jero (ejecutado por Claude Code a pedido de Jero), 2026-11-12.
**Fuente de cada dato:** P = prueba propia.

[← Base MIMIC (relaciones no declaradas)](../../_bases/mimic-demo.md) · [Base Synthea](../../_bases/synthea.md) ·
[A2m / A2s LLM local](../A2-llm-local/ficha.md) · [C1m / C1s subconjunto](../C1-subconjunto/ficha.md)

Etapa 3 del plan de MIMIC: ¿puede el LLM local encontrar las relaciones que el catálogo no declara? C1 mostró que
sin ellas el subconjunto deja 20 relaciones rotas en MIMIC.

## En pocas palabras

- **MIMIC (proponer las no declaradas, viendo las 51 FK declaradas):** encuentra **5 de 25** (recall 0,20).
  - De las 11 propuestas, 5 son correctas y 1 más se cumple en los datos aunque no estaba en la verdad.
  - Las otras 5 relacionan `orderid` entre tablas de UCI que no comparten valores (falsas).
  - Pierde las más evidentes por el nombre: `caregiver_id → caregiver` (6) y `*_provider_id → provider` (5).
- **Synthea (proponer todas, sin ninguna FK declarada):** encuentra **24 de 40** (recall 0,60, precisión 0,92).
  - Propone una relación por tabla, hacia el paciente, y casi nunca la segunda: no aparece ninguna de las 10
    `encounter → encounters`, ni las de aseguradoras (`payer`).
  - Las 2 propuestas falsas (`departmentid → organizations`) no se cumplen en ninguna fila.
- **Determinista:** las tres corridas dan exactamente lo mismo. Ninguna columna inventada.
- **Conclusión:** el LLM solo no alcanza para el grafo de relaciones. La búsqueda por **nombre de columna + valores
  en común** (lo que hizo `relaciones_mimic.py` en la etapa 1) encontró las 25 de MIMIC. El LLM puede sumar como
  segunda opinión, siempre verificado contra los datos.

## Entorno

- Ollama 0.40.15, `gemma4:12b-it-qat`, sin razonamiento, temperatura 0, semillas 1 a 3, contexto de 16 384 tokens,
  salida JSON forzada (las tablas restringidas a las existentes).
- El LLM ve solo el esquema: tablas, columnas con tipo, PK y, en MIMIC, las FK declaradas. Ningún valor.
- Verdad:
  - **MIMIC:** las 25 relaciones no declaradas de `pruebas/_bases/evidencia/mimic-demo/relaciones.csv` (encontradas
    por nombre y verificadas contra los datos; 20 se cumplen y 5 tienen huérfanas en el origen);
  - **Synthea:** las 40 FK que declaró el cargador (0 huérfanas).
- Cada propuesta fuera de la verdad se verifica contra los datos (huérfanas y valores en común): puede ser una
  relación real que faltaba o un error.
- Script: `f2_relaciones_llm.py` (esta carpeta).

```bash
.venv/bin/python pruebas/salud/F2-relaciones-llm/f2_relaciones_llm.py --base mimic     # y synthea
```

## Resultados

| Base | Propuestas | Aciertos | Recall | Precisión contra la verdad | Fuera de la verdad que se cumplen | Precisión verificada | Tiempo por corrida |
|---|---|---|---|---|---|---|---|
| MIMIC | 11 | 5 de 25 | **0,20** | 0,45 | 1 | 0,55 | 60–75 s |
| Synthea | 26 | 24 de 40 | **0,60** | 0,92 | 0 | 0,92 | 112–120 s |

Las tres corridas de cada base dan las mismas propuestas.

### MIMIC

- **Aciertos (5):** `emar`, `emar_detail` y `prescriptions` → `pharmacy.pharmacy_id`; `poe.order_provider_id →
  provider`; `prescriptions.poe_id → poe`.
- **No encontradas (20):** los 6 `caregiver_id → caregiver` de las tablas de UCI, 5 `*_provider_id → provider`,
  `labevents`, `transfers` e `ingredientevents.hadm_id → admissions`, `omr.subject_id → patients`,
  `ingredientevents` → `patients`, `icustays` y `d_items`, `emar.poe_id` y `pharmacy.poe_id → poe`.
- **Fuera de la verdad (6):**
  - `procedureevents.linkorderid → procedureevents.orderid` se cumple (0 huérfanas): una relación real, dentro de la
    misma tabla, que la búsqueda por nombre no consideraba;
  - 5 entre `orderid` y `linkorderid` de `inputevents`, `ingredientevents` y `procedureevents`, con el 100 % de
    huérfanas: no comparten ningún valor.

### Synthea

- **No encontradas (16):** las 10 `encounter → encounters.id` y las 6 que van a `payers.id` (`payer`, `secondary_payer` y los ids de seguro del
  paciente en `claims`).
- **Fuera de la verdad (2):** `claims.departmentid` y `claims_transactions.departmentid → organizations`, con el 100 %
  de huérfanas.

## Hallazgos

- **El LLM prioriza un patrón (la relación con el paciente) y deja de buscar.** En Synthea encontró todas las
  `patient → patients` y ninguna `encounter → encounters`, aunque los nombres son igual de claros.
- **En MIMIC, ver las FK declaradas no ayuda:** propone sobre todo relaciones raras (`orderid`) y omite las de
  cuidadores y profesionales, que siguen el mismo patrón de nombres que las declaradas.
- **Encontró una relación que el método por nombre no veía** (dentro de la misma tabla). Es el aporte posible del
  LLM: casos que no siguen la convención `<tabla>_id`.
- **Para el sistema:** método por nombre y valores como base, el LLM como fuente de candidatos extra, y **toda
  propuesta verificada contra los datos** antes de usarla (como hace este script).

## Limitaciones

- Un solo modelo, sin razonamiento, con el esquema entero en un prompt (unos 4 000 a 6 000 tokens). Pedir tabla por
  tabla o con razonamiento podría dar más recall.
- La verdad de MIMIC sale de un método por nombre de columna: relaciones con otros nombres podrían faltar (como la
  que encontró el LLM).
- El LLM conoce MIMIC y Synthea (ver A2): con un esquema propio podría rendir distinto.

## Evidencia

- `resultados/<base>.json`: por corrida, propuestas, aciertos, no encontradas, verificación de cada propuesta fuera de
  la verdad y tiempos.
- `resultados/crudo/`: la respuesta JSON del LLM por corrida (solo nombres de tablas y columnas).
