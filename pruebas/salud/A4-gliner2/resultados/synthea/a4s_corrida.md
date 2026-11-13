# A4s: GLiNER2-PII sobre synthea_p1000

- Corrida: 2026-11-08 22:44
- Equipo: arm64, macOS 26.6.2, Python 3.11.16, dispositivo `mps`
- gliner2 2.1.0, transformers 5.22.2, torch 2.14.1; modelo `fastino/gliner2-privacy-filter-PII-multi`
- Referencia: `data/columnas_sensibles_synthea.csv`; columnas con valores: 246 de 256
- Parámetros: 100 valores por columna, marcar con ≥50%, umbrales 0.3,0.5,0.7, semilla `a1`, lote 32
- Etiquetas `pii`: person name, date, location, street address, social security number, driver license number, passport number, phone number, email address, identification number, financial amount
- Etiquetas agregadas en `pii_salud`: medical condition, medication, medical procedure, lab test, gender, ethnicity, marital status, language, health insurance
- Tiempos: muestreo 10 s, pii 163 s, pii_contexto 170 s, pii_salud 237 s, pii_salud_contexto 251 s
