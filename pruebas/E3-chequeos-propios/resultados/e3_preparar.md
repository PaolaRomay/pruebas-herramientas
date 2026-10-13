# E3: base de entrenamiento sin el conjunto de control

Corrida: 2026-10-10 21:14

- Base creada: `e3_entrenamiento` (copia de `pagila` con CREATE DATABASE ... TEMPLATE).
- Control: 200 clientes (20%), orden por md5 con semilla `e3`. Lista en `e3_control.csv`.
- Filas borradas: payment 9997, rental 10142, customer 200, address 91.
- Direcciones de clientes de control que se conservan porque las usa staff o store: 109 de 200. Esas direcciones siguen en los datos de entrenamiento (es una particularidad de Pagila v4; anotarlo al interpretar linkability e inference).

| tabla | filas |
|---|---|
| actor | 200 |
| address | 912 |
| category | 16 |
| city | 600 |
| country | 109 |
| customer | 799 |
| film | 1000 |
| film_actor | 5462 |
| film_category | 2367 |
| inventory | 4581 |
| language | 6 |
| payment | 41064 |
| rental | 41663 |
| staff | 1500 |
| store | 500 |
