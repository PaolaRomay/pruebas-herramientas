# Detección de columnas sensibles: comparación entre pruebas

Generado: 2026-11-09 00:14

## Entradas

- Lista de referencia: `data/columnas_sensibles_synthea.csv` (sha256 `5c8d0a3d29070ca59ae8131bf84f40097416b086a44ae6782b6ceccbf0d9aa91`): 159 sensibles, 60 no sensibles, 37 dudosas (las dudosas no entran en las métricas)
- Excluidas de las métricas (no evaluables): ninguna
- `pruebas/salud/A1-presidio/resultados/synthea/a1s_columnas.csv` (formato común, sha256 `72fd16dcdcb4…`)
- `pruebas/salud/A2-llm-local/resultados/synthea/a2s_a2a_columnas.csv` (formato común, sha256 `7c65282a93de…`)
- `pruebas/salud/A2-llm-local/resultados/synthea/a2s_a2b_columnas.csv` (formato común, sha256 `f968bc0c0518…`)
- `pruebas/salud/A2-llm-local/resultados/synthea/a2s_a2b_ofuscado_columnas.csv` (formato común, sha256 `22146665823f…`)
- `pruebas/salud/A4-gliner2/resultados/synthea/a4s_columnas.csv` (formato común, sha256 `701bcd0d8696…`)
- `pruebas/salud/A5-anon-detect/resultados/synthea/a5s_columnas.csv` (formato común, sha256 `6add5cc4b382…`)
- `pruebas/salud/A6-llm-presidio/resultados/synthea/a6s_columnas.csv` (formato común, sha256 `ae50029906e9…`)

## Comparación

Orden: F1 y, a igualdad, recall (en anonimización un FN es un dato que se filtra). «Eval.» = columnas que entraron en las métricas: si una herramienta no analizó alguna, su denominador es menor. Las variantes con varias corridas muestran el promedio.

| Prueba | Variante | Corridas | Eval. | TP | FP | FN | TN | Precisión | Recall | F1 | Etiqueta |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A2s | a2b | 1 | 219 | 135 | 14 | 24 | 46 | 0.91 | 0.85 | 0.88 | 41/41 |
| A6s | cascada (a2b + presidio) | 1 | 219 | 135 | 15 | 24 | 45 | 0.90 | 0.85 | 0.87 | 41/41 |
| A2s | a2b_ofuscado | 1 | 219 | 141 | 24 | 18 | 36 | 0.85 | 0.89 | 0.87 | 39/41 |
| A6s | union (a2b + presidio) | 1 | 219 | 152 | 40 | 7 | 20 | 0.79 | 0.96 | 0.87 | 41/41 |
| A2s | a2a | 3 | 219 | 129 | 13 | 30 | 47 | 0.91 | 0.81 | 0.86 | 41/41 |
| A6s | union (a2a + presidio) | 1 | 219 | 149 | 40 | 10 | 20 | 0.79 | 0.94 | 0.86 | 41/41 |
| A6s | cascada (a2a + presidio) | 1 | 219 | 129 | 14 | 30 | 46 | 0.90 | 0.81 | 0.85 | 41/41 |
| A4s | pii_salud umbral 0.3 | 1 | 219 | 143 | 33 | 16 | 27 | 0.81 | 0.90 | 0.85 | 38/41 |
| A4s | pii_salud umbral 0.5 | 1 | 219 | 131 | 25 | 28 | 35 | 0.84 | 0.82 | 0.83 | 37/41 |
| A4s | pii_salud_contexto umbral 0.3 | 1 | 219 | 137 | 35 | 22 | 25 | 0.80 | 0.86 | 0.83 | 41/41 |
| A4s | pii umbral 0.3 | 1 | 219 | 123 | 30 | 36 | 30 | 0.80 | 0.77 | 0.79 | 38/41 |
| A1s | structured:highest_confidence umbral 0.0 | 1 | 219 | 127 | 39 | 32 | 21 | 0.77 | 0.80 | 0.78 | 38/41 |
| A1s | structured:mixed umbral 0.0 | 1 | 219 | 127 | 39 | 32 | 21 | 0.77 | 0.80 | 0.78 | 38/41 |
| A1s | structured:most_common umbral 0.0 | 1 | 219 | 127 | 39 | 32 | 21 | 0.77 | 0.80 | 0.78 | 39/41 |
| A1s | structured:highest_confidence umbral 0.4 | 1 | 219 | 126 | 38 | 33 | 22 | 0.77 | 0.79 | 0.78 | 38/41 |
| A1s | structured:mixed umbral 0.4 | 1 | 219 | 126 | 38 | 33 | 22 | 0.77 | 0.79 | 0.78 | 38/41 |
| A1s | structured:most_common umbral 0.4 | 1 | 219 | 126 | 38 | 33 | 22 | 0.77 | 0.79 | 0.78 | 38/41 |
| A6s | interseccion (a2b + presidio) | 1 | 219 | 110 | 13 | 49 | 47 | 0.89 | 0.69 | 0.78 | 40/41 |
| A1s | structured:highest_confidence umbral 0.6 | 1 | 219 | 123 | 34 | 36 | 26 | 0.78 | 0.77 | 0.78 | 37/41 |
| A1s | structured:mixed umbral 0.6 | 1 | 219 | 123 | 34 | 36 | 26 | 0.78 | 0.77 | 0.78 | 37/41 |
| A1s | structured:most_common umbral 0.6 | 1 | 219 | 123 | 34 | 36 | 26 | 0.78 | 0.77 | 0.78 | 37/41 |
| A6s | interseccion (a2a + presidio) | 1 | 219 | 107 | 12 | 52 | 48 | 0.90 | 0.67 | 0.77 | 40/41 |
| A4s | pii_salud umbral 0.7 | 1 | 219 | 111 | 20 | 48 | 40 | 0.85 | 0.70 | 0.77 | 37/41 |
| A4s | pii_salud_contexto umbral 0.5 | 1 | 219 | 110 | 21 | 49 | 39 | 0.84 | 0.69 | 0.76 | 40/41 |
| A4s | pii_contexto umbral 0.3 | 1 | 219 | 104 | 19 | 55 | 41 | 0.85 | 0.65 | 0.74 | 41/41 |
| A4s | pii umbral 0.5 | 1 | 219 | 94 | 21 | 65 | 39 | 0.82 | 0.59 | 0.69 | 37/41 |
| A4s | pii_contexto umbral 0.5 | 1 | 219 | 90 | 16 | 69 | 44 | 0.85 | 0.57 | 0.68 | 40/41 |
| A1s | manual_contexto umbral 0.0 | 1 | 219 | 87 | 17 | 72 | 43 | 0.84 | 0.55 | 0.66 | 39/41 |
| A1s | manual umbral 0.0 | 1 | 219 | 84 | 17 | 75 | 43 | 0.83 | 0.53 | 0.65 | 39/41 |
| A4s | pii umbral 0.7 | 1 | 219 | 81 | 11 | 78 | 49 | 0.88 | 0.51 | 0.65 | 37/41 |
| A4s | pii_salud_contexto umbral 0.7 | 1 | 219 | 83 | 16 | 76 | 44 | 0.84 | 0.52 | 0.64 | 38/41 |
| A4s | pii_contexto umbral 0.7 | 1 | 219 | 69 | 13 | 90 | 47 | 0.84 | 0.43 | 0.57 | 38/41 |
| A1s | manual umbral 0.4 | 1 | 219 | 61 | 12 | 98 | 48 | 0.84 | 0.38 | 0.53 | 38/41 |
| A1s | manual umbral 0.6 | 1 | 219 | 59 | 11 | 100 | 49 | 0.84 | 0.37 | 0.52 | 37/41 |
| A1s | manual_contexto umbral 0.6 | 1 | 219 | 51 | 8 | 108 | 52 | 0.86 | 0.32 | 0.47 | 39/41 |
| A1s | manual_contexto umbral 0.4 | 1 | 219 | 51 | 9 | 108 | 51 | 0.85 | 0.32 | 0.47 | 39/41 |
| A5s | en_US | 1 | 219 | 7 | 5 | 152 | 55 | 0.58 | 0.04 | 0.08 | 3/41 |
| A5s | en_US_directos | 1 | 219 | 5 | 5 | 154 | 55 | 0.50 | 0.03 | 0.06 | 3/41 |

## Estabilidad entre corridas

Cambia la marca = la columna se marcó en unas corridas y en otras no. Cambia la entidad = marcada en todas, pero con distinta entidad. Acuerdo = columnas sin ningún cambio.

| Prueba | Variante | Corridas | Columnas | Cambia marca | Cambia entidad | Acuerdo | F1 por corrida | Inestables |
|---|---|---|---|---|---|---|---|---|
| A2s | a2a | 3 | 256 | 0 | 0 | 100% | 0.86, 0.86, 0.86 | - |

## Columnas sensibles que se escaparon

Por prueba: configuraciones (variante × corrida) que no la marcaron / que la analizaron.

- Ninguna herramienta la detectó: imaging_studies.modality_code, immunizations.code, providers.procedures, providers.speciality
- imaging_studies.modality_code: A1s 15/15, A2s 5/5, A4s 12/12, A5s 2/2, A6s 6/6
- immunizations.code: A1s 15/15, A2s 5/5, A4s 12/12, A5s 2/2, A6s 6/6
- providers.procedures: A1s 15/15, A2s 5/5, A4s 12/12, A5s 2/2, A6s 6/6
- providers.speciality: A1s 15/15, A2s 5/5, A4s 12/12, A5s 2/2, A6s 6/6
- supplies.description: A1s 15/15, A2s 4/5, A4s 12/12, A5s 2/2, A6s 6/6
- devices.description: A1s 15/15, A2s 3/5, A4s 9/12, A5s 2/2, A6s 4/6
- claims_transactions.diagnosisref2: A1s 15/15, A2s 1/5, A4s 12/12, A5s 2/2, A6s 2/6
- claims_transactions.diagnosisref3: A1s 15/15, A2s 1/5, A4s 12/12, A5s 2/2, A6s 2/6
- claims_transactions.diagnosisref4: A1s 15/15, A2s 1/5, A4s 12/12, A5s 2/2, A6s 2/6
- allergies.category: A1s 15/15, A4s 12/12, A5s 2/2, A6s 2/6
- imaging_studies.modality_description: A1s 12/15, A2s 5/5, A4s 6/12, A5s 2/2, A6s 6/6
- imaging_studies.bodysite_description: A1s 15/15, A2s 3/5, A4s 6/12, A5s 2/2, A6s 4/6
- providers.state: A1s 12/15, A2s 4/5, A4s 6/12, A5s 2/2, A6s 6/6
- claims_transactions.diagnosisref1: A1s 12/15, A2s 1/5, A4s 12/12, A5s 2/2, A6s 2/6
- payer_transitions.plan_ownership: A1s 15/15, A2s 3/5, A4s 4/12, A5s 2/2, A6s 4/6
- providers.encounters: A1s 6/15, A2s 4/5, A4s 12/12, A5s 2/2, A6s 4/6
- allergies.severity2: A1s 12/15, A4s 11/12, A5s 2/2, A6s 2/6
- observations.category: A1s 15/15, A4s 8/12, A5s 2/2, A6s 2/6
- allergies.severity1: A1s 12/15, A4s 10/12, A5s 2/2, A6s 2/6
- patients.prefix: A1s 15/15, A4s 7/12, A5s 2/2, A6s 2/6
- careplans.reasondescription: A1s 15/15, A4s 6/12, A5s 2/2, A6s 2/6
- encounters.reasondescription: A1s 15/15, A4s 6/12, A5s 2/2, A6s 2/6
- imaging_studies.procedure_code: A1s 10/15, A2s 4/5, A4s 5/12, A5s 2/2, A6s 4/6
- medications.reasondescription: A1s 15/15, A4s 6/12, A5s 2/2, A6s 2/6
- procedures.reasondescription: A1s 15/15, A4s 6/12, A5s 2/2, A6s 2/6
- patients.gender: A1s 15/15, A4s 3/12, A5s 1/2, A6s 2/6
- patients.marital: A1s 15/15, A4s 2/12, A5s 2/2, A6s 2/6
- providers.gender: A1s 15/15, A4s 3/12, A5s 1/2, A6s 2/6
- allergies.description: A1s 6/15, A4s 12/12, A5s 2/2
- procedures.reasoncode: A1s 4/15, A2s 4/5, A4s 6/12, A5s 2/2, A6s 4/6
- careplans.description: A1s 6/15, A2s 3/5, A4s 6/12, A5s 2/2, A6s 2/6
- careplans.reasoncode: A1s 2/15, A2s 5/5, A4s 6/12, A5s 2/2, A6s 4/6
- claims.diagnosis7: A1s 13/15, A4s 2/12, A5s 2/2, A6s 2/6
- encounters.code: A1s 4/15, A2s 5/5, A4s 4/12, A5s 2/2, A6s 4/6
- encounters.description: A1s 6/15, A2s 3/5, A4s 6/12, A5s 2/2, A6s 2/6
- encounters.encounterclass: A1s 15/15, A5s 2/2, A6s 2/6
- encounters.id: A1s 6/15, A2s 4/5, A4s 3/12, A5s 2/2, A6s 4/6
- patients.passport: A1s 15/15, A5s 2/2, A6s 2/6
- claims.diagnosis4: A1s 11/15, A4s 3/12, A5s 2/2, A6s 2/6
- claims.diagnosis6: A1s 13/15, A4s 1/12, A5s 2/2, A6s 2/6
- imaging_studies.series_uid: A1s 4/15, A4s 12/12, A5s 2/2
- medications.reasoncode: A1s 2/15, A2s 5/5, A4s 5/12, A5s 2/2, A6s 4/6
- observations.encounter: A1s 6/15, A4s 10/12, A5s 2/2
- procedures.code: A1s 2/15, A2s 5/5, A4s 5/12, A5s 2/2, A6s 4/6
- providers.id: A1s 6/15, A2s 4/5, A4s 2/12, A5s 2/2, A6s 4/6
- supplies.code: A1s 2/15, A2s 4/5, A4s 6/12, A5s 2/2, A6s 4/6
- allergies.code: A1s 4/15, A2s 4/5, A4s 3/12, A5s 2/2, A6s 4/6
- careplans.code: A1s 2/15, A2s 5/5, A4s 4/12, A5s 2/2, A6s 4/6
- claims.diagnosis5: A1s 11/15, A4s 2/12, A5s 2/2, A6s 2/6
- devices.code: A1s 2/15, A2s 5/5, A4s 4/12, A5s 2/2, A6s 4/6
- medications.code: A2s 5/5, A4s 6/12, A5s 2/2, A6s 4/6
- encounters.reasoncode: A1s 2/15, A2s 4/5, A4s 4/12, A5s 2/2, A6s 4/6
- imaging_studies.bodysite_code: A1s 3/15, A2s 4/5, A4s 3/12, A5s 2/2, A6s 4/6
- imaging_studies.patient: A1s 6/15, A4s 8/12, A5s 2/2
- medications.encounter: A1s 6/15, A4s 8/12, A5s 2/2
- procedures.encounter: A1s 6/15, A4s 8/12, A5s 2/2
- claims.appointmentid: A1s 6/15, A4s 7/12, A5s 2/2
- claims_transactions.appointmentid: A1s 6/15, A4s 7/12, A5s 2/2
- conditions.encounter: A1s 6/15, A4s 7/12, A5s 2/2
- devices.encounter: A1s 6/15, A4s 7/12, A5s 2/2
- patients.zip: A1s 6/15, A4s 7/12, A5s 2/2
- supplies.encounter: A1s 6/15, A4s 7/12, A5s 2/2
- allergies.description1: A1s 6/15, A4s 6/12, A5s 2/2
- allergies.description2: A1s 6/15, A4s 6/12, A5s 2/2
- allergies.encounter: A1s 6/15, A4s 6/12, A5s 2/2
- careplans.encounter: A1s 6/15, A4s 6/12, A5s 2/2
- claims.providerid: A1s 4/15, A4s 8/12, A5s 2/2
- claims_transactions.notes: A1s 6/15, A4s 6/12, A5s 2/2
- claims_transactions.providerid: A1s 4/15, A4s 8/12, A5s 2/2
- conditions.description: A1s 6/15, A4s 6/12, A5s 2/2
- imaging_studies.encounter: A1s 6/15, A4s 6/12, A5s 2/2
- imaging_studies.instance_uid: A1s 4/15, A4s 8/12, A5s 2/2
- immunizations.encounter: A1s 6/15, A4s 6/12, A5s 2/2
- medications.description: A1s 6/15, A4s 6/12, A5s 2/2
- observations.description: A1s 6/15, A4s 6/12, A5s 2/2
- patients.fips: A1s 6/15, A4s 6/12, A5s 2/2
- procedures.description: A1s 6/15, A4s 6/12, A5s 2/2
- allergies.patient: A1s 6/15, A4s 5/12, A5s 2/2
- encounters.provider: A1s 4/15, A4s 7/12, A5s 2/2
- patients.suffix: A4s 11/12, A5s 2/2
- careplans.patient: A1s 6/15, A4s 4/12, A5s 2/2
- claims.supervisingproviderid: A1s 4/15, A4s 6/12, A5s 2/2
- claims_transactions.supervisingproviderid: A1s 4/15, A4s 6/12, A5s 2/2
- immunizations.patient: A1s 6/15, A4s 4/12, A5s 2/2
- observations.value: A1s 6/15, A4s 4/12, A5s 2/2
- patients.race: A1s 6/15, A4s 4/12, A5s 2/2
- payer_transitions.memberid: A1s 6/15, A4s 4/12, A5s 2/2
- providers.lat: A1s 7/15, A4s 3/12, A5s 2/2
- allergies.reaction1: A1s 4/15, A2s 1/5, A4s 4/12, A5s 2/2
- conditions.code: A1s 2/15, A2s 3/5, A4s 2/12, A5s 2/2, A6s 2/6
- medications.patient: A1s 6/15, A4s 3/12, A5s 2/2
- supplies.patient: A1s 6/15, A4s 3/12, A5s 2/2
- devices.patient: A1s 6/15, A4s 2/12, A5s 2/2
- observations.code: A2s 4/5, A5s 2/2, A6s 4/6
- patients.birthplace: A4s 8/12, A5s 2/2
- patients.id: A1s 6/15, A4s 2/12, A5s 2/2
- patients.lat: A1s 4/15, A4s 4/12, A5s 2/2
- allergies.reaction2: A1s 4/15, A2s 1/5, A4s 2/12, A5s 2/2
- claims_transactions.procedurecode: A1s 2/15, A4s 5/12, A5s 2/2
- conditions.patient: A1s 6/15, A4s 1/12, A5s 2/2
- patients.healthcare_coverage: A1s 7/15, A5s 2/2
- claims.patientid: A1s 6/15, A5s 2/2
- claims_transactions.patientid: A1s 6/15, A5s 2/2
- encounters.patient: A1s 6/15, A5s 2/2
- immunizations.description: A4s 6/12, A5s 2/2
- observations.patient: A1s 6/15, A5s 2/2
- patients.ethnicity: A4s 6/12, A5s 2/2
- patients.healthcare_expenses: A1s 6/15, A5s 2/2
- procedures.patient: A1s 6/15, A5s 2/2
- providers.zip: A1s 2/15, A4s 4/12, A5s 2/2
- devices.udi: A1s 4/15, A4s 1/12, A5s 2/2
- patients.income: A1s 3/15, A4s 2/12, A5s 2/2
- payer_transitions.patient: A1s 5/15, A5s 2/2
- claims.diagnosis3: A1s 2/15, A4s 2/12, A5s 2/2
- patients.address: A1s 6/15
- patients.lon: A1s 4/15, A5s 2/2
- patients.ssn: A1s 4/15, A5s 2/2
- providers.address: A1s 6/15
- providers.lon: A1s 4/15, A5s 2/2
- claims.diagnosis2: A1s 2/15, A5s 2/2
- claims.lastbilleddate1: A4s 2/12, A5s 2/2
- claims.lastbilleddate2: A4s 2/12, A5s 2/2
- patients.drivers: A1s 2/15, A5s 2/2
- allergies.start: A5s 2/2
- careplans.start: A5s 2/2
- careplans.stop: A5s 2/2
- claims.currentillnessdate: A5s 2/2
- claims.diagnosis1: A5s 2/2
- claims.lastbilleddatep: A5s 2/2
- claims.servicedate: A5s 2/2
- claims_transactions.fromdate: A5s 2/2
- claims_transactions.todate: A5s 2/2
- conditions.start: A5s 2/2
- conditions.stop: A5s 2/2
- devices.start: A5s 2/2
- devices.stop: A5s 2/2
- encounters.start: A5s 2/2
- encounters.stop: A5s 2/2
- imaging_studies.date: A5s 2/2
- immunizations.date: A5s 2/2
- medications.start: A5s 2/2
- medications.stop: A5s 2/2
- observations.date: A5s 2/2
- patients.birthdate: A5s 2/2
- patients.county: A5s 2/2
- patients.deathdate: A5s 2/2
- patients.first: A5s 2/2
- patients.last: A5s 2/2
- patients.maiden: A5s 2/2
- patients.middle: A5s 2/2
- payer_transitions.end_date: A5s 2/2
- payer_transitions.owner_name: A5s 2/2
- payer_transitions.start_date: A5s 2/2
- procedures.start: A5s 2/2
- procedures.stop: A5s 2/2
- supplies.date: A5s 2/2

## Falsos positivos compartidos

No sensibles marcadas por más de una prueba (herramienta distinta).

- allergies.type: A2s, A4s, A6s
- claims.primarypatientinsuranceid: A1s, A2s, A4s, A6s
- claims.secondarypatientinsuranceid: A1s, A2s, A4s, A6s
- claims_transactions.method: A1s, A6s
- claims_transactions.patientinsuranceid: A1s, A2s, A4s, A6s
- claims_transactions.placeofservice: A1s, A2s, A4s, A6s
- claims_transactions.transferoutid: A1s, A2s, A4s, A6s
- encounters.organization: A1s, A2s, A4s, A6s
- encounters.payer: A1s, A2s, A4s, A6s
- imaging_studies.sop_code: A1s, A2s, A4s, A6s
- medications.payer: A1s, A2s, A4s, A6s
- observations.units: A1s, A4s, A6s
- organizations.address: A1s, A2s, A4s, A5s, A6s
- organizations.city: A1s, A2s, A4s, A5s, A6s
- organizations.id: A1s, A2s, A4s, A6s
- organizations.lat: A1s, A2s, A4s, A6s
- organizations.lon: A1s, A2s, A4s, A6s
- organizations.name: A1s, A4s, A5s, A6s
- organizations.phone: A1s, A2s, A4s, A5s, A6s
- organizations.state: A1s, A4s
- organizations.utilization: A1s, A6s
- organizations.zip: A1s, A2s, A4s, A6s
- payer_transitions.payer: A1s, A2s, A4s, A6s
- payer_transitions.secondary_payer: A1s, A2s, A4s, A6s
- payers.amount_covered: A1s, A2s, A4s, A6s
- payers.amount_uncovered: A1s, A2s, A4s, A6s
- payers.covered_encounters: A1s, A4s, A6s
- payers.covered_immunizations: A1s, A4s, A6s
- payers.covered_medications: A1s, A4s, A6s
- payers.covered_procedures: A1s, A4s, A6s
- payers.id: A1s, A2s, A4s, A6s
- payers.member_months: A1s, A4s, A6s
- payers.name: A1s, A2s, A4s, A5s, A6s
- payers.qols_avg: A1s, A4s, A6s
- payers.revenue: A1s, A2s, A4s, A6s
- payers.uncovered_encounters: A1s, A6s
- payers.uncovered_immunizations: A1s, A4s, A6s
- payers.uncovered_medications: A1s, A4s, A6s
- payers.uncovered_procedures: A1s, A6s
- procedures.system: A1s, A6s
- providers.organization: A1s, A2s, A4s, A6s

FP de una sola prueba: claims.statusp (A1s), claims_transactions.transfertype (A4s), conditions.system (A4s), imaging_studies.sop_description (A4s), organizations.revenue (A4s), payers.ownership (A2s), payers.unique_customers (A4s)

Detalle en `deteccion_metricas.csv` (una fila por prueba + variante + corrida, con FN y FP) y `deteccion_por_columna.csv` (matriz columna × configuración).
