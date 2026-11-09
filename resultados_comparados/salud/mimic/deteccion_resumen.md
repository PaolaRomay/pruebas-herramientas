# Detección de columnas sensibles: comparación entre pruebas

Generado: 2026-11-09 00:14

## Entradas

- Lista de referencia: `data/columnas_sensibles_mimic.csv` (sha256 `a7459d31b629be0b78d6a2941b2f1b1b7a84139a93e06ac3cc673bd808296f72`): 247 sensibles, 64 no sensibles, 31 dudosas (las dudosas no entran en las métricas)
- Excluidas de las métricas (no evaluables): ninguna
- `pruebas/salud/A1-presidio/resultados/mimic/a1m_columnas.csv` (formato común, sha256 `182df2c4bd6c…`)
- `pruebas/salud/A2-llm-local/resultados/mimic/a2m_a2a_columnas.csv` (formato común, sha256 `323c7dbb9e76…`)
- `pruebas/salud/A2-llm-local/resultados/mimic/a2m_a2b_columnas.csv` (formato común, sha256 `a52db05e771d…`)
- `pruebas/salud/A2-llm-local/resultados/mimic/a2m_a2b_ofuscado_columnas.csv` (formato común, sha256 `6d06f2df3521…`)
- `pruebas/salud/A4-gliner2/resultados/mimic/a4m_columnas.csv` (formato común, sha256 `f08d1a106384…`)
- `pruebas/salud/A5-anon-detect/resultados/mimic/a5m_columnas.csv` (formato común, sha256 `d38f56b5f9c7…`)
- `pruebas/salud/A6-llm-presidio/resultados/mimic/a6m_columnas.csv` (formato común, sha256 `14cc3276de1a…`)

## Comparación

Orden: F1 y, a igualdad, recall (en anonimización un FN es un dato que se filtra). «Eval.» = columnas que entraron en las métricas: si una herramienta no analizó alguna, su denominador es menor. Las variantes con varias corridas muestran el promedio.

| Prueba | Variante | Corridas | Eval. | TP | FP | FN | TN | Precisión | Recall | F1 | Etiqueta |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A6m | union (a2a + presidio) | 1 | 311 | 224 | 22 | 23 | 42 | 0.91 | 0.91 | 0.91 | 45/45 |
| A6m | union (a2b + presidio) | 1 | 311 | 220 | 27 | 27 | 37 | 0.89 | 0.89 | 0.89 | 45/45 |
| A6m | cascada (a2b + presidio) | 1 | 311 | 200 | 6 | 47 | 58 | 0.97 | 0.81 | 0.88 | 45/45 |
| A2m | a2b | 1 | 311 | 199 | 6 | 48 | 58 | 0.97 | 0.81 | 0.88 | 45/45 |
| A2m | a2a | 3 | 311 | 195 | 1 | 52 | 63 | 0.99 | 0.79 | 0.88 | 45/45 |
| A6m | cascada (a2a + presidio) | 1 | 311 | 195 | 1 | 52 | 63 | 0.99 | 0.79 | 0.88 | 45/45 |
| A2m | a2b_ofuscado | 1 | 311 | 195 | 16 | 52 | 48 | 0.92 | 0.79 | 0.85 | 45/45 |
| A4m | pii_salud umbral 0.3 | 1 | 311 | 193 | 24 | 54 | 40 | 0.89 | 0.78 | 0.83 | 45/45 |
| A4m | pii_salud_contexto umbral 0.3 | 1 | 311 | 190 | 22 | 57 | 42 | 0.90 | 0.77 | 0.83 | 45/45 |
| A4m | pii_salud_contexto umbral 0.5 | 1 | 311 | 177 | 8 | 70 | 56 | 0.96 | 0.72 | 0.82 | 45/45 |
| A4m | pii umbral 0.3 | 1 | 311 | 171 | 18 | 76 | 46 | 0.90 | 0.69 | 0.78 | 45/45 |
| A4m | pii_contexto umbral 0.3 | 1 | 311 | 165 | 10 | 82 | 54 | 0.94 | 0.67 | 0.78 | 45/45 |
| A1m | structured:highest_confidence umbral 0.0 | 1 | 311 | 171 | 21 | 76 | 43 | 0.89 | 0.69 | 0.78 | 45/45 |
| A1m | structured:mixed umbral 0.0 | 1 | 311 | 171 | 21 | 76 | 43 | 0.89 | 0.69 | 0.78 | 45/45 |
| A1m | structured:most_common umbral 0.0 | 1 | 311 | 171 | 21 | 76 | 43 | 0.89 | 0.69 | 0.78 | 45/45 |
| A1m | structured:highest_confidence umbral 0.4 | 1 | 311 | 170 | 21 | 77 | 43 | 0.89 | 0.69 | 0.78 | 45/45 |
| A1m | structured:mixed umbral 0.4 | 1 | 311 | 170 | 21 | 77 | 43 | 0.89 | 0.69 | 0.78 | 45/45 |
| A1m | structured:most_common umbral 0.4 | 1 | 311 | 170 | 21 | 77 | 43 | 0.89 | 0.69 | 0.78 | 45/45 |
| A1m | structured:highest_confidence umbral 0.6 | 1 | 311 | 168 | 21 | 79 | 43 | 0.89 | 0.68 | 0.77 | 45/45 |
| A1m | structured:mixed umbral 0.6 | 1 | 311 | 168 | 21 | 79 | 43 | 0.89 | 0.68 | 0.77 | 45/45 |
| A1m | structured:most_common umbral 0.6 | 1 | 311 | 168 | 21 | 79 | 43 | 0.89 | 0.68 | 0.77 | 45/45 |
| A4m | pii umbral 0.5 | 1 | 311 | 161 | 12 | 86 | 52 | 0.93 | 0.65 | 0.77 | 45/45 |
| A4m | pii_salud umbral 0.5 | 1 | 311 | 163 | 18 | 84 | 46 | 0.90 | 0.66 | 0.76 | 45/45 |
| A6m | interseccion (a2b + presidio) | 1 | 311 | 150 | 0 | 97 | 64 | 1.00 | 0.61 | 0.76 | 45/45 |
| A6m | interseccion (a2a + presidio) | 1 | 311 | 142 | 0 | 105 | 64 | 1.00 | 0.57 | 0.73 | 45/45 |
| A4m | pii_contexto umbral 0.5 | 1 | 311 | 127 | 4 | 120 | 60 | 0.97 | 0.51 | 0.67 | 45/45 |
| A4m | pii umbral 0.7 | 1 | 311 | 128 | 10 | 119 | 54 | 0.93 | 0.52 | 0.66 | 45/45 |
| A4m | pii_salud_contexto umbral 0.7 | 1 | 311 | 119 | 5 | 128 | 59 | 0.96 | 0.48 | 0.64 | 32/45 |
| A4m | pii_salud umbral 0.7 | 1 | 311 | 120 | 9 | 127 | 55 | 0.93 | 0.49 | 0.64 | 45/45 |
| A1m | manual_contexto umbral 0.0 | 1 | 311 | 116 | 6 | 131 | 58 | 0.95 | 0.47 | 0.63 | 45/45 |
| A1m | manual umbral 0.0 | 1 | 311 | 112 | 3 | 135 | 61 | 0.97 | 0.45 | 0.62 | 45/45 |
| A4m | pii_contexto umbral 0.7 | 1 | 311 | 98 | 2 | 149 | 62 | 0.98 | 0.40 | 0.56 | 33/45 |
| A1m | manual umbral 0.4 | 1 | 311 | 72 | 2 | 175 | 62 | 0.97 | 0.29 | 0.45 | 45/45 |
| A1m | manual umbral 0.6 | 1 | 311 | 69 | 2 | 178 | 62 | 0.97 | 0.28 | 0.43 | 45/45 |
| A1m | manual_contexto umbral 0.4 | 1 | 311 | 57 | 5 | 190 | 59 | 0.92 | 0.23 | 0.37 | 45/45 |
| A1m | manual_contexto umbral 0.6 | 1 | 311 | 55 | 5 | 192 | 59 | 0.92 | 0.22 | 0.36 | 45/45 |
| A5m | en_US | 1 | 311 | 3 | 0 | 244 | 64 | 1.00 | 0.01 | 0.02 | 0/45 |
| A5m | en_US_directos | 1 | 311 | 1 | 0 | 246 | 64 | 1.00 | 0.00 | 0.01 | 0/45 |

## Estabilidad entre corridas

Cambia la marca = la columna se marcó en unas corridas y en otras no. Cambia la entidad = marcada en todas, pero con distinta entidad. Acuerdo = columnas sin ningún cambio.

| Prueba | Variante | Corridas | Columnas | Cambia marca | Cambia entidad | Acuerdo | F1 por corrida | Inestables |
|---|---|---|---|---|---|---|---|---|
| A2m | a2a | 3 | 342 | 0 | 0 | 100% | 0.88, 0.88, 0.88 | - |

## Columnas sensibles que se escaparon

Por prueba: configuraciones (variante × corrida) que no la marcaron / que la analizaron.

- Ninguna herramienta la detectó: admissions.hospital_expire_flag, drgcodes.drg_severity, pharmacy.status, procedureevents.ordercategorydescription
- admissions.hospital_expire_flag: A1m 15/15, A2m 5/5, A4m 12/12, A5m 2/2, A6m 6/6
- drgcodes.drg_severity: A1m 15/15, A2m 5/5, A4m 12/12, A5m 2/2, A6m 6/6
- pharmacy.status: A1m 15/15, A2m 5/5, A4m 12/12, A5m 2/2, A6m 6/6
- procedureevents.ordercategorydescription: A1m 15/15, A2m 5/5, A4m 12/12, A5m 2/2, A6m 6/6
- labevents.priority: A1m 15/15, A2m 4/5, A4m 12/12, A5m 2/2, A6m 6/6
- microbiologyevents.dilution_comparison: A1m 15/15, A2m 4/5, A4m 12/12, A5m 2/2, A6m 6/6
- microbiologyevents.dilution_text: A1m 15/15, A2m 4/5, A4m 12/12, A5m 2/2, A6m 6/6
- microbiologyevents.dilution_value: A1m 15/15, A2m 4/5, A4m 12/12, A5m 2/2, A6m 6/6
- prescriptions.form_unit_disp: A1m 15/15, A2m 4/5, A4m 12/12, A5m 2/2, A6m 6/6
- procedureevents.ordercategoryname: A1m 15/15, A2m 4/5, A4m 12/12, A5m 2/2, A6m 6/6
- drgcodes.drg_mortality: A1m 15/15, A2m 5/5, A4m 10/12, A5m 2/2, A6m 6/6
- labevents.ref_range_upper: A1m 15/15, A2m 4/5, A4m 10/12, A5m 2/2, A6m 6/6
- inputevents.ordercomponenttypedescription: A1m 15/15, A2m 4/5, A4m 9/12, A5m 2/2, A6m 6/6
- poe_detail.field_name: A1m 15/15, A2m 3/5, A4m 12/12, A5m 2/2, A6m 4/6
- icustays.first_careunit: A1m 15/15, A2m 4/5, A4m 8/12, A5m 2/2, A6m 6/6
- prescriptions.dose_unit_rx: A1m 15/15, A2m 4/5, A4m 8/12, A5m 2/2, A6m 6/6
- procedureevents.originalrate: A1m 15/15, A2m 2/5, A4m 12/12, A5m 2/2, A6m 4/6
- emar_detail.reason_for_no_barcode: A1m 15/15, A2m 1/5, A4m 12/12, A5m 2/2, A6m 4/6
- icustays.last_careunit: A1m 15/15, A2m 4/5, A4m 7/12, A5m 2/2, A6m 6/6
- inputevents.ordercategorydescription: A1m 15/15, A2m 4/5, A4m 7/12, A5m 2/2, A6m 6/6
- prescriptions.form_rx: A1m 15/15, A2m 1/5, A4m 12/12, A5m 2/2, A6m 4/6
- emar_detail.non_formulary_visual_verification: A1m 15/15, A2m 2/5, A4m 10/12, A5m 2/2, A6m 4/6
- emar_detail.complete_dose_not_given: A1m 15/15, A2m 1/5, A4m 12/12, A5m 2/2, A6m 2/6
- emar_detail.restart_interval: A1m 15/15, A2m 1/5, A4m 12/12, A5m 2/2, A6m 2/6
- emar_detail.site: A1m 15/15, A2m 1/5, A4m 12/12, A5m 2/2, A6m 2/6
- emar_detail.will_remainder_of_dose_be_given: A1m 15/15, A2m 1/5, A4m 12/12, A5m 2/2, A6m 2/6
- ingredientevents.originalamount: A1m 15/15, A2m 4/5, A4m 7/12, A5m 2/2, A6m 4/6
- labevents.ref_range_lower: A1m 15/15, A2m 4/5, A4m 5/12, A5m 2/2, A6m 6/6
- pharmacy.basal_rate: A1m 15/15, A2m 1/5, A4m 12/12, A5m 2/2, A6m 2/6
- pharmacy.dispensation: A1m 12/15, A2m 2/5, A4m 12/12, A5m 2/2, A6m 4/6
- pharmacy.duration: A1m 15/15, A2m 1/5, A4m 12/12, A5m 2/2, A6m 2/6
- pharmacy.duration_interval: A1m 15/15, A2m 1/5, A4m 12/12, A5m 2/2, A6m 2/6
- pharmacy.lockout_interval: A1m 15/15, A2m 1/5, A4m 12/12, A5m 2/2, A6m 2/6
- pharmacy.proc_type: A1m 15/15, A2m 1/5, A4m 12/12, A5m 2/2, A6m 2/6
- prescriptions.drug_type: A1m 15/15, A2m 2/5, A4m 9/12, A5m 2/2, A6m 4/6
- emar.event_txt: A1m 15/15, A4m 12/12, A5m 2/2, A6m 2/6
- inputevents.patientweight: A1m 15/15, A4m 12/12, A5m 2/2, A6m 2/6
- pharmacy.infusion_type: A1m 15/15, A2m 1/5, A4m 11/12, A5m 2/2, A6m 2/6
- poe.order_type: A1m 15/15, A4m 12/12, A5m 2/2, A6m 2/6
- prescriptions.doses_per_24_hrs: A1m 12/15, A2m 1/5, A4m 12/12, A5m 2/2, A6m 4/6
- emar_detail.infusion_rate_adjustment: A1m 15/15, A2m 1/5, A4m 10/12, A5m 2/2, A6m 2/6
- emar_detail.prior_infusion_rate: A1m 15/15, A2m 1/5, A4m 10/12, A5m 2/2, A6m 2/6
- emar_detail.infusion_rate: A1m 15/15, A2m 1/5, A4m 9/12, A5m 2/2, A6m 2/6
- pharmacy.doses_per_24_hrs: A1m 12/15, A2m 1/5, A4m 12/12, A5m 2/2, A6m 2/6
- pharmacy.expiration_value: A1m 15/15, A2m 4/5, A4m 4/12, A5m 2/2, A6m 4/6
- pharmacy.one_hr_max: A1m 12/15, A2m 1/5, A4m 12/12, A5m 2/2, A6m 2/6
- procedureevents.patientweight: A1m 15/15, A4m 10/12, A5m 2/2, A6m 2/6
- drgcodes.drg_type: A1m 15/15, A2m 5/5, A5m 2/2, A6m 6/6
- pharmacy.sliding_scale: A1m 15/15, A2m 1/5, A4m 8/12, A5m 2/2, A6m 2/6
- admissions.marital_status: A1m 15/15, A4m 8/12, A5m 2/2, A6m 2/6
- emar_detail.new_iv_bag_hung: A1m 15/15, A2m 1/5, A4m 7/12, A5m 2/2, A6m 2/6
- emar_detail.side: A1m 15/15, A2m 1/5, A4m 7/12, A5m 2/2, A6m 2/6
- emar_detail.administration_type: A1m 15/15, A2m 1/5, A4m 6/12, A5m 2/2, A6m 2/6
- emar_detail.completion_interval: A1m 9/15, A2m 1/5, A4m 12/12, A5m 2/2, A6m 2/6
- emar_detail.infusion_complete: A1m 15/15, A2m 1/5, A4m 6/12, A5m 2/2, A6m 2/6
- microbiologyevents.interpretation: A1m 15/15, A4m 7/12, A5m 2/2, A6m 2/6
- procedureevents.locationcategory: A1m 15/15, A2m 3/5, A4m 2/12, A5m 2/2, A6m 4/6
- transfers.eventtype: A1m 6/15, A2m 4/5, A4m 12/12, A5m 2/2, A6m 2/6
- labevents.comments: A1m 15/15, A4m 6/12, A5m 2/2, A6m 2/6
- labevents.flag: A1m 15/15, A4m 6/12, A5m 2/2, A6m 2/6
- microbiologyevents.org_itemid: A1m 6/15, A2m 4/5, A4m 9/12, A5m 2/2, A6m 4/6
- admissions.language: A1m 15/15, A4m 6/12, A5m 1/2, A6m 2/6
- drgcodes.drg_code: A1m 6/15, A2m 5/5, A4m 7/12, A5m 2/2, A6m 4/6
- emar_detail.product_amount_given: A1m 15/15, A2m 1/5, A4m 4/12, A5m 2/2, A6m 2/6
- inputevents.secondaryordercategoryname: A1m 6/15, A2m 3/5, A4m 11/12, A5m 2/2, A6m 2/6
- labevents.order_provider_id: A1m 15/15, A4m 5/12, A5m 2/2, A6m 2/6
- microbiologyevents.order_provider_id: A1m 15/15, A4m 5/12, A5m 2/2, A6m 2/6
- microbiologyevents.org_name: A1m 6/15, A2m 3/5, A4m 11/12, A5m 2/2, A6m 2/6
- microbiologyevents.spec_itemid: A1m 3/15, A2m 4/5, A4m 11/12, A5m 2/2, A6m 4/6
- microbiologyevents.test_itemid: A1m 6/15, A2m 4/5, A4m 8/12, A5m 2/2, A6m 4/6
- omr.result_name: A1m 12/15, A4m 10/12, A5m 2/2
- admissions.discharge_location: A1m 15/15, A4m 4/12, A5m 2/2, A6m 2/6
- microbiologyevents.ab_itemid: A1m 6/15, A2m 4/5, A4m 7/12, A5m 2/2, A6m 4/6
- prescriptions.prod_strength: A1m 6/15, A2m 1/5, A4m 12/12, A5m 2/2, A6m 2/6
- admissions.insurance: A1m 15/15, A4m 5/12, A6m 2/6
- chartevents.itemid: A1m 4/15, A2m 4/5, A4m 8/12, A5m 2/2, A6m 4/6
- labevents.itemid: A1m 3/15, A2m 5/5, A4m 8/12, A5m 2/2, A6m 4/6
- admissions.admission_type: A1m 15/15, A4m 2/12, A5m 2/2, A6m 2/6
- emar_detail.dose_due: A1m 15/15, A2m 1/5, A4m 1/12, A5m 2/2, A6m 2/6
- emar_detail.dose_given: A1m 15/15, A2m 1/5, A4m 1/12, A5m 2/2, A6m 2/6
- ingredientevents.itemid: A1m 2/15, A2m 4/5, A4m 9/12, A5m 2/2, A6m 4/6
- inputevents.itemid: A1m 4/15, A2m 4/5, A4m 7/12, A5m 2/2, A6m 4/6
- outputevents.itemid: A1m 4/15, A2m 4/5, A4m 7/12, A5m 2/2, A6m 4/6
- pharmacy.disp_sched: A1m 6/15, A2m 1/5, A4m 12/12, A5m 2/2
- procedureevents.itemid: A1m 4/15, A2m 4/5, A4m 7/12, A5m 2/2, A6m 4/6
- datetimeevents.itemid: A1m 3/15, A2m 4/5, A4m 7/12, A5m 2/2, A6m 4/6
- emar_detail.infusion_rate_adjustment_amount: A1m 15/15, A2m 1/5, A5m 2/2, A6m 2/6
- emar_detail.product_code: A1m 6/15, A2m 3/5, A4m 7/12, A5m 2/2, A6m 2/6
- microbiologyevents.spec_type_desc: A1m 6/15, A2m 3/5, A4m 7/12, A5m 2/2, A6m 2/6
- microbiologyevents.test_name: A1m 6/15, A2m 3/5, A4m 7/12, A5m 2/2, A6m 2/6
- poe.order_subtype: A1m 6/15, A4m 12/12, A5m 2/2
- prescriptions.dose_val_rx: A1m 12/15, A2m 1/5, A4m 1/12, A5m 2/2, A6m 4/6
- services.curr_service: A1m 6/15, A2m 1/5, A4m 11/12, A5m 2/2
- chartevents.valuenum: A1m 15/15, A5m 2/2, A6m 2/6
- drgcodes.description: A1m 6/15, A2m 3/5, A4m 6/12, A5m 2/2, A6m 2/6
- inputevents.ordercategoryname: A1m 6/15, A2m 3/5, A4m 6/12, A5m 2/2, A6m 2/6
- inputevents.totalamount: A1m 15/15, A5m 2/2, A6m 2/6
- labevents.value: A1m 15/15, A5m 2/2, A6m 2/6
- labevents.valuenum: A1m 15/15, A5m 2/2, A6m 2/6
- microbiologyevents.ab_name: A1m 6/15, A2m 3/5, A4m 6/12, A5m 2/2, A6m 2/6
- outputevents.value: A1m 15/15, A5m 2/2, A6m 2/6
- prescriptions.form_val_disp: A1m 9/15, A2m 1/5, A4m 6/12, A5m 2/2, A6m 1/6
- patients.gender: A1m 15/15, A5m 1/2, A6m 2/6
- transfers.careunit: A1m 6/15, A2m 3/5, A4m 5/12, A5m 2/2, A6m 2/6
- diagnoses_icd.icd_code: A1m 5/15, A4m 10/12, A5m 2/2
- hcpcsevents.short_description: A1m 6/15, A4m 9/12, A5m 2/2
- services.prev_service: A1m 3/15, A2m 1/5, A4m 11/12, A5m 2/2
- caregiver.caregiver_id: A1m 6/15, A2m 4/5, A4m 2/12, A5m 2/2, A6m 2/6
- pharmacy.frequency: A1m 6/15, A2m 1/5, A4m 7/12, A5m 2/2
- prescriptions.route: A1m 6/15, A2m 1/5, A4m 5/12, A5m 2/2, A6m 2/6
- procedures_icd.icd_code: A1m 6/15, A4m 7/12, A5m 2/2
- admissions.admission_location: A1m 6/15, A4m 6/12, A5m 2/2
- emar.medication: A1m 6/15, A4m 6/12, A5m 2/2
- emar_detail.product_description_other: A1m 6/15, A4m 6/12, A5m 2/2
- ingredientevents.originalrate: A1m 6/15, A2m 3/5, A4m 1/12, A5m 2/2, A6m 2/6
- microbiologyevents.comments: A1m 6/15, A4m 6/12, A5m 2/2
- omr.result_value: A1m 6/15, A4m 6/12, A5m 2/2
- pharmacy.medication: A1m 6/15, A4m 6/12, A5m 2/2
- pharmacy.route: A1m 6/15, A2m 1/5, A4m 5/12, A5m 2/2
- poe.order_provider_id: A1m 6/15, A2m 1/5, A4m 5/12, A5m 2/2
- prescriptions.drug: A1m 6/15, A4m 6/12, A5m 2/2
- prescriptions.formulary_drug_cd: A1m 6/15, A2m 1/5, A4m 3/12, A5m 2/2, A6m 2/6
- procedureevents.originalamount: A1m 6/15, A2m 1/5, A4m 3/12, A5m 2/2, A6m 2/6
- procedureevents.value: A1m 6/15, A2m 1/5, A4m 3/12, A5m 2/2, A6m 2/6
- emar_detail.route: A1m 6/15, A2m 1/5, A4m 4/12, A5m 2/2
- icustays.los: A1m 3/15, A2m 4/5, A5m 2/2, A6m 4/6
- ingredientevents.amount: A1m 6/15, A2m 3/5, A5m 2/2, A6m 2/6
- ingredientevents.caregiver_id: A1m 6/15, A4m 5/12, A5m 2/2
- ingredientevents.rate: A1m 6/15, A2m 3/5, A5m 2/2, A6m 2/6
- inputevents.rate: A1m 6/15, A2m 3/5, A5m 2/2, A6m 2/6
- prescriptions.order_provider_id: A1m 6/15, A4m 5/12, A5m 2/2
- inputevents.caregiver_id: A1m 6/15, A4m 4/12, A5m 2/2
- procedureevents.location: A1m 6/15, A4m 4/12, A5m 2/2
- admissions.race: A1m 6/15, A4m 3/12, A5m 2/2
- chartevents.caregiver_id: A1m 6/15, A4m 3/12, A5m 2/2
- datetimeevents.caregiver_id: A1m 6/15, A4m 3/12, A5m 2/2
- emar_detail.product_description: A1m 3/15, A4m 6/12, A5m 2/2
- inputevents.amount: A1m 4/15, A2m 3/5, A5m 2/2, A6m 2/6
- inputevents.originalamount: A1m 9/15, A5m 2/2
- outputevents.caregiver_id: A1m 6/15, A4m 3/12, A5m 2/2
- poe_detail.field_value: A1m 6/15, A4m 3/12, A5m 2/2
- admissions.admit_provider_id: A1m 6/15, A4m 2/12, A5m 2/2
- labevents.subject_id: A1m 4/15, A2m 1/5, A4m 3/12, A5m 2/2
- procedureevents.caregiver_id: A1m 6/15, A2m 1/5, A4m 1/12, A5m 2/2
- provider.provider_id: A1m 6/15, A4m 2/12, A5m 2/2
- chartevents.subject_id: A1m 4/15, A4m 3/12, A5m 2/2
- datetimeevents.subject_id: A1m 4/15, A4m 3/12, A5m 2/2
- diagnoses_icd.subject_id: A1m 4/15, A4m 3/12, A5m 2/2
- emar.enter_provider_id: A1m 6/15, A4m 1/12, A5m 2/2
- emar.subject_id: A1m 4/15, A4m 3/12, A5m 2/2
- emar_detail.subject_id: A1m 4/15, A4m 3/12, A5m 2/2
- inputevents.originalrate: A1m 6/15, A4m 1/12, A5m 2/2
- inputevents.subject_id: A1m 4/15, A4m 3/12, A5m 2/2
- microbiologyevents.subject_id: A1m 4/15, A4m 3/12, A5m 2/2
- omr.subject_id: A1m 4/15, A4m 3/12, A5m 2/2
- outputevents.subject_id: A1m 4/15, A4m 3/12, A5m 2/2
- pharmacy.subject_id: A1m 4/15, A4m 3/12, A5m 2/2
- poe.subject_id: A1m 4/15, A4m 3/12, A5m 2/2
- poe_detail.subject_id: A1m 4/15, A4m 3/12, A5m 2/2
- prescriptions.subject_id: A1m 4/15, A4m 3/12, A5m 2/2
- transfers.subject_id: A1m 4/15, A4m 3/12, A5m 2/2
- admissions.hadm_id: A1m 4/15, A4m 2/12, A5m 2/2
- chartevents.value: A1m 6/15, A5m 2/2
- drgcodes.hadm_id: A1m 4/15, A4m 2/12, A5m 2/2
- hcpcsevents.hadm_id: A1m 4/15, A4m 2/12, A5m 2/2
- icustays.hadm_id: A1m 4/15, A4m 2/12, A5m 2/2
- labevents.hadm_id: A1m 4/15, A2m 1/5, A4m 1/12, A5m 2/2
- microbiologyevents.hadm_id: A1m 4/15, A4m 2/12, A5m 2/2
- prescriptions.gsn: A1m 2/15, A2m 2/5, A5m 2/2, A6m 2/6
- services.hadm_id: A1m 4/15, A4m 2/12, A5m 2/2
- services.subject_id: A1m 2/15, A4m 4/12, A5m 2/2
- transfers.hadm_id: A1m 4/15, A4m 2/12, A5m 2/2
- admissions.subject_id: A1m 2/15, A4m 3/12, A5m 2/2
- chartevents.hadm_id: A1m 4/15, A4m 1/12, A5m 2/2
- chartevents.stay_id: A1m 4/15, A4m 1/12, A5m 2/2
- diagnoses_icd.hadm_id: A1m 4/15, A4m 1/12, A5m 2/2
- drgcodes.subject_id: A1m 2/15, A4m 3/12, A5m 2/2
- emar.hadm_id: A1m 2/15, A4m 3/12, A5m 2/2
- hcpcsevents.hcpcs_cd: A1m 2/15, A4m 3/12, A5m 2/2
- hcpcsevents.subject_id: A1m 2/15, A4m 3/12, A5m 2/2
- icustays.stay_id: A1m 4/15, A4m 1/12, A5m 2/2
- icustays.subject_id: A1m 2/15, A4m 3/12, A5m 2/2
- ingredientevents.stay_id: A1m 4/15, A4m 1/12, A5m 2/2
- ingredientevents.subject_id: A1m 2/15, A4m 3/12, A5m 2/2
- inputevents.stay_id: A1m 4/15, A4m 1/12, A5m 2/2
- patients.subject_id: A1m 2/15, A4m 3/12, A5m 2/2
- pharmacy.hadm_id: A1m 2/15, A4m 3/12, A5m 2/2
- prescriptions.hadm_id: A1m 2/15, A4m 3/12, A5m 2/2
- prescriptions.ndc: A1m 2/15, A2m 1/5, A5m 2/2, A6m 2/6
- procedureevents.hadm_id: A1m 4/15, A4m 1/12, A5m 2/2
- procedureevents.stay_id: A1m 4/15, A4m 1/12, A5m 2/2
- procedureevents.subject_id: A1m 2/15, A4m 3/12, A5m 2/2
- procedures_icd.hadm_id: A1m 4/15, A4m 1/12, A5m 2/2
- procedures_icd.subject_id: A1m 2/15, A4m 3/12, A5m 2/2
- outputevents.stay_id: A1m 3/15, A4m 1/12, A5m 2/2
- datetimeevents.hadm_id: A1m 2/15, A4m 1/12, A5m 2/2
- ingredientevents.hadm_id: A1m 2/15, A4m 1/12, A5m 2/2
- inputevents.hadm_id: A1m 2/15, A4m 1/12, A5m 2/2
- outputevents.hadm_id: A1m 2/15, A4m 1/12, A5m 2/2
- poe.hadm_id: A1m 2/15, A4m 1/12, A5m 2/2
- admissions.edregtime: A4m 2/12, A5m 2/2
- chartevents.storetime: A4m 2/12, A5m 2/2
- datetimeevents.stay_id: A1m 2/15, A5m 2/2
- datetimeevents.storetime: A4m 2/12, A5m 2/2
- emar.storetime: A4m 2/12, A5m 2/2
- ingredientevents.storetime: A4m 2/12, A5m 2/2
- inputevents.storetime: A4m 2/12, A5m 2/2
- labevents.storetime: A4m 2/12, A5m 2/2
- microbiologyevents.storetime: A4m 2/12, A5m 2/2
- outputevents.storetime: A4m 2/12, A5m 2/2
- poe.ordertime: A4m 2/12, A5m 2/2
- procedureevents.storetime: A4m 2/12, A5m 2/2
- chartevents.charttime: A4m 1/12, A5m 2/2
- microbiologyevents.charttime: A4m 1/12, A5m 2/2
- pharmacy.entertime: A4m 1/12, A5m 2/2
- admissions.admittime: A5m 2/2
- admissions.deathtime: A5m 2/2
- admissions.dischtime: A5m 2/2
- admissions.edouttime: A5m 2/2
- datetimeevents.charttime: A5m 2/2
- datetimeevents.value: A5m 2/2
- emar.charttime: A5m 2/2
- emar.scheduletime: A5m 2/2
- hcpcsevents.chartdate: A5m 2/2
- icustays.intime: A5m 2/2
- icustays.outtime: A5m 2/2
- ingredientevents.endtime: A5m 2/2
- ingredientevents.starttime: A5m 2/2
- inputevents.endtime: A5m 2/2
- inputevents.starttime: A5m 2/2
- labevents.charttime: A5m 2/2
- microbiologyevents.chartdate: A5m 2/2
- microbiologyevents.storedate: A5m 2/2
- omr.chartdate: A5m 2/2
- outputevents.charttime: A5m 2/2
- patients.dod: A5m 2/2
- pharmacy.starttime: A5m 2/2
- pharmacy.stoptime: A5m 2/2
- pharmacy.verifiedtime: A5m 2/2
- prescriptions.starttime: A5m 2/2
- prescriptions.stoptime: A5m 2/2
- procedureevents.endtime: A5m 2/2
- procedureevents.starttime: A5m 2/2
- procedures_icd.chartdate: A5m 2/2
- services.transfertime: A5m 2/2
- transfers.intime: A5m 2/2
- transfers.outtime: A5m 2/2

## Falsos positivos compartidos

No sensibles marcadas por más de una prueba (herramienta distinta).

- d_hcpcs.code: A1m, A2m, A4m, A6m
- d_hcpcs.long_description: A1m, A2m, A4m, A6m
- d_hcpcs.short_description: A1m, A2m, A4m, A6m
- d_icd_diagnoses.icd_code: A1m, A2m, A4m, A6m
- d_icd_diagnoses.long_title: A1m, A2m, A4m, A6m
- d_icd_procedures.icd_code: A1m, A2m, A4m, A6m
- d_icd_procedures.long_title: A1m, A2m, A4m, A6m
- d_items.abbreviation: A1m, A2m, A4m, A6m
- d_items.category: A1m, A2m, A6m
- d_items.itemid: A1m, A4m, A6m
- d_items.label: A1m, A2m, A4m, A6m
- d_labitems.fluid: A1m, A2m, A4m, A6m
- d_labitems.itemid: A1m, A4m, A6m
- d_labitems.label: A1m, A2m, A4m, A6m
- datetimeevents.valueuom: A1m, A4m
- emar.emar_seq: A1m, A4m, A6m
- emar_detail.dose_due_unit: A2m, A4m, A6m
- emar_detail.dose_given_unit: A2m, A4m, A6m
- emar_detail.emar_seq: A1m, A2m, A4m, A6m
- emar_detail.infusion_rate_unit: A2m, A4m, A6m
- emar_detail.product_unit: A2m, A6m
- ingredientevents.statusdescription: A2m, A6m
- inputevents.rateuom: A1m, A4m, A6m
- inputevents.totalamountuom: A1m, A4m
- labevents.valueuom: A1m, A6m
- outputevents.valueuom: A2m, A4m
- pharmacy.expiration_unit: A1m, A2m, A6m
- poe.poe_seq: A1m, A4m, A6m
- poe.transaction_type: A2m, A6m
- poe_detail.poe_seq: A1m, A4m, A6m
- prescriptions.poe_seq: A1m, A4m, A6m

FP de una sola prueba: chartevents.valueuom (A4m), d_icd_diagnoses.icd_version (A4m), d_icd_procedures.icd_version (A4m), d_items.highnormalvalue (A4m), diagnoses_icd.icd_version (A4m), ingredientevents.amountuom (A4m), inputevents.amountuom (A4m), inputevents.statusdescription (A2m), microbiologyevents.test_seq (A4m), procedures_icd.icd_version (A4m)

Detalle en `deteccion_metricas.csv` (una fila por prueba + variante + corrida, con FN y FP) y `deteccion_por_columna.csv` (matriz columna × configuración).
