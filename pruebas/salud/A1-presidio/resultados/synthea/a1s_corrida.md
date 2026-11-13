# A1s: Presidio sobre synthea_p1000

- Corrida: 2026-11-08 13:55
- Equipo: arm64, macOS 26.6.2, Python 3.11.16
- presidio-analyzer 2.2.364, presidio-structured 0.0.8, spaCy 3.8.16, en_core_web_lg 3.8.0
- Referencia: `data/columnas_sensibles_synthea.csv`; columnas con valores: 246 de 256
- Parámetros: 200 valores por columna (manual), 100 filas por tabla (structured), marcar con ≥50%, umbrales 0,0.4,0.6, idioma `en`, semilla `a1`
- Tiempos: muestreo 9 s, manual 35 s, manual_contexto 45 s, structured 345 s
