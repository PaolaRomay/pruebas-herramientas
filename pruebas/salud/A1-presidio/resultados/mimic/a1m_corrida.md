# A1m: Presidio sobre mimic_demo

- Corrida: 2026-11-08 13:47
- Equipo: arm64, macOS 26.6.2, Python 3.11.16
- presidio-analyzer 2.2.364, presidio-structured 0.0.8, spaCy 3.8.16, en_core_web_lg 3.8.0
- Referencia: `data/columnas_sensibles_mimic.csv`; columnas con valores: 339 de 342
- Parámetros: 200 valores por columna (manual), 100 filas por tabla (structured), marcar con ≥50%, umbrales 0,0.4,0.6, idioma `en`, semilla `a1`
- Tiempos: muestreo 4 s, manual 41 s, manual_contexto 57 s, structured 436 s
