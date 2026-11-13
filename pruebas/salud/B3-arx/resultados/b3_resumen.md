# B3m / B3s: ARX como medidor del registro «paciente»

Supresión máxima 10%. Riesgo = modelo del fiscal (1 / tamaño de la clase).

| Base | Conjunto | Filas | k | l | Únicos antes | Riesgo máx. antes | Solución | Suprimidas | Niveles | Riesgo máx. después |
|---|---|---|---|---|---|---|---|---|---|---|
| mimic | subconjunto | 47 | 2 | 1 | 100% | 1.00 | sí | 3 | {'sexo': 0, 'edad': 4, 'raza': 2, 'seguro': 1, 'idioma': 0, 'estado_civil': 0} | 0.50 |
| mimic | subconjunto | 47 | 5 | 1 | 100% | 1.00 | sí | 4 | {'sexo': 1, 'edad': 4, 'raza': 2, 'seguro': 0, 'idioma': 0, 'estado_civil': 1} | 0.20 |
| mimic | subconjunto | 47 | 5 | 2 | 100% | 1.00 | sí | 4 | {'sexo': 1, 'edad': 4, 'raza': 2, 'seguro': 0, 'idioma': 0, 'estado_civil': 1} | 0.20 |
| mimic | b1 | 47 | 2 | 1 | 81% | 1.00 | sí | 3 | {'sexo': 0, 'edad': 4, 'raza': 2, 'seguro': 1, 'idioma': 0, 'estado_civil': 0} | 0.50 |
| mimic | b1 | 47 | 5 | 1 | 81% | 1.00 | sí | 4 | {'sexo': 1, 'edad': 4, 'raza': 2, 'seguro': 0, 'idioma': 0, 'estado_civil': 1} | 0.20 |
| mimic | b1 | 47 | 5 | 2 | 81% | 1.00 | sí | 4 | {'sexo': 1, 'edad': 4, 'raza': 2, 'seguro': 0, 'idioma': 0, 'estado_civil': 1} | 0.20 |
| mimic | completa | 100 | 2 | 1 | 90% | 1.00 | sí | 8 | {'sexo': 0, 'edad': 3, 'raza': 2, 'seguro': 0, 'idioma': 0, 'estado_civil': 1} | 0.50 |
| mimic | completa | 100 | 5 | 1 | 90% | 1.00 | sí | 9 | {'sexo': 1, 'edad': 3, 'raza': 2, 'seguro': 0, 'idioma': 0, 'estado_civil': 1} | 0.20 |
| mimic | completa | 100 | 5 | 2 | 90% | 1.00 | sí | 9 | {'sexo': 1, 'edad': 3, 'raza': 2, 'seguro': 0, 'idioma': 0, 'estado_civil': 1} | 0.20 |
| synthea | subconjunto | 85 | 2 | 1 | 98% | 1.00 | sí | 5 | {'sexo': 0, 'edad': 4, 'raza': 2, 'etnia': 0, 'estado_civil': 0, 'zip3': 1} | 0.50 |
| synthea | subconjunto | 85 | 5 | 1 | 98% | 1.00 | sí | 5 | {'sexo': 0, 'edad': 4, 'raza': 2, 'etnia': 0, 'estado_civil': 1, 'zip3': 1} | 0.12 |
| synthea | subconjunto | 85 | 5 | 2 | 98% | 1.00 | sí | 5 | {'sexo': 0, 'edad': 4, 'raza': 2, 'etnia': 0, 'estado_civil': 1, 'zip3': 1} | 0.12 |
| synthea | b1 | 85 | 2 | 1 | 98% | 1.00 | sí | 5 | {'sexo': 0, 'edad': 4, 'raza': 2, 'etnia': 0, 'estado_civil': 0, 'zip3': 1} | 0.50 |
| synthea | b1 | 85 | 5 | 1 | 98% | 1.00 | sí | 5 | {'sexo': 0, 'edad': 4, 'raza': 2, 'etnia': 0, 'estado_civil': 1, 'zip3': 1} | 0.12 |
| synthea | b1 | 85 | 5 | 2 | 98% | 1.00 | sí | 5 | {'sexo': 0, 'edad': 4, 'raza': 2, 'etnia': 0, 'estado_civil': 1, 'zip3': 1} | 0.12 |
| synthea | completa | 1151 | 2 | 1 | 70% | 1.00 | sí | 63 | {'sexo': 0, 'edad': 3, 'raza': 0, 'etnia': 0, 'estado_civil': 0, 'zip3': 2} | 0.50 |
| synthea | completa | 1151 | 5 | 1 | 70% | 1.00 | sí | 72 | {'sexo': 0, 'edad': 4, 'raza': 0, 'etnia': 0, 'estado_civil': 0, 'zip3': 2} | 0.20 |
| synthea | completa | 1151 | 5 | 2 | 70% | 1.00 | sí | 72 | {'sexo': 0, 'edad': 4, 'raza': 0, 'etnia': 0, 'estado_civil': 0, 'zip3': 2} | 0.20 |
