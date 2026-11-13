# B3: ARX (k-anonimato) sobre el registro «persona» de Pagila

Corrida: 2026-10-14 23:34

- Equipo: arm64, macOS 26.6.2. ARX 3.9.2 (libarx, Java en `eclipse-temurin:21-jdk`)
- Datos: `e3_entrenamiento`, 799 personas. Valores distintos por cuasi-identificador: {'district': 317, 'postal_code': 795, 'city': 479, 'country': 100, 'create_date': 350}
- Identificadores (se tapan con '*'): first_name, last_name, email, address, phone. Cuasi-identificadores: district, postal_code, city, country, create_date
- Ciudades con el mismo nombre en más de un país (suben directo a '*'): []

## Resultado de ARX

| variante | k | supresión máx. | cuasi-identificadores | segundos ARX | segundos con contenedor | filas suprimidas | clases | clase mín / prom. | riesgo máx. antes → después | riesgo prom. antes → después | niveles |
|---|---|---|---|---|---|---|---|---|---|---|---|
| k2 | 2 | 10% | 5 | 0.03 | 0.9 | 43 | 61 | 2 / 12.4 | 1.00 → 0.50 | 1.000 → 0.081 | district 1, postal_code 5, city 1, country 0, create_date 2 |
| k5 | 5 | 10% | 5 | 0.03 | 0.7 | 46 | 36 | 5 / 20.9 | 1.00 → 0.20 | 1.000 → 0.048 | district 1, postal_code 4, city 2, country 1, create_date 2 |
| k10 | 10 | 10% | 5 | 0.03 | 0.6 | 5 | 11 | 28 / 72.2 | 1.00 → 0.04 | 1.000 → 0.014 | district 1, postal_code 4, city 2, country 1, create_date 3 |
| k5_sin_supresion | 5 | 0% | 5 | 0.02 | 0.6 | 0 | 5 | 28 / 159.8 | 1.00 → 0.04 | 1.000 → 0.006 | district 1, postal_code 5, city 2, country 1, create_date 2 |
| k5_ciudad_pais_fecha | 5 | 10% | 3 | 0.02 | 0.6 | 37 | 42 | 5 / 18.1 | 1.00 → 0.20 | 0.961 → 0.055 | city 2, country 1, create_date 1 |

Niveles: 0 = sin cambio. postal_code 0–5 (dígitos tapados), district 0–1, city 0–2 (ciudad, país, '*'), country 0–1, create_date 0–3 (día, mes, año, '*').

## Vuelta a la base (con todas las restricciones)

| variante | carga | segundos | fecha día/mes/año/* | ciudad igual / a país / oculta | CP y ciudad intactos | direcciones de staff/store tocadas |
|---|---|---|---|---|---|---|
| k2 | ok | 0.7 | 0/0/756/43 | 0/756/43 | 0 | 441 |
| k5 | ok | 0.6 | 0/0/753/46 | 0/0/799 | 0 | 441 |
| k10 | ok | 0.5 | 0/0/0/799 | 0/0/799 | 0 | 441 |
| k5_sin_supresion | ok | 0.5 | 0/0/799/0 | 0/0/799 | 0 | 441 |
| k5_ciudad_pais_fecha | ok | 0.5 | 0/762/0/37 | 0/0/799 | 0 | 441 |

## Privacidad y calidad con E3

| variante | calidad / diagnóstico | Column Shapes | singling out univariado | singling out multivariado | linkability | inference district | inference city | inference country | inference postal_code | copias exactas | índice de memorización |
|---|---|---|---|---|---|---|---|---|---|---|---|
| k2 | 0.869 / 0.974 | 0.861 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0% | -1.01 |
| k5 | 0.868 / 0.972 | 0.851 | 0.000 | 0.010 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0% | -2.63 |
| k10 | 0.762 / 0.963 | 0.800 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0% | -3.91 |
| k5_sin_supresion | 0.871 / 0.974 | 0.861 | 0.000 | 0.015 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0% | -2.47 |
| k5_ciudad_pais_fecha | 0.903 / 0.997 | 0.918 | 0.019 | 0.015 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0% | -1.48 |

