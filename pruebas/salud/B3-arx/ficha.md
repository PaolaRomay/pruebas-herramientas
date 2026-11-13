# B3m / B3s — ARX como medidor del riesgo del registro «paciente» (MIMIC y Synthea) — Anonimizar

**Quién / cuándo:** Jero (ejecutado por Claude Code a pedido de Jero), 2026-11-09.
**Fuente de cada dato:** P = prueba propia.

[← B1m / B1s PostgreSQL Anonymizer](../B1-anon/ficha.md) · [B3 ARX sobre Pagila](../../B3-arx/ficha.md) ·
[C1m / C1s subconjunto](../C1-subconjunto/ficha.md)

B1 seudonimiza ids y desplaza fechas, pero no cambia lo que hace única a una persona: la combinación de sexo,
edad, raza, seguro, idioma, estado civil o código postal. ARX mide ese riesgo y calcula cuánto habría que
generalizar para llegar a k-anonimato, con y sin l-diversidad sobre el diagnóstico (el atributo sensible que en
Pagila no existía).

## En pocas palabras

- **Casi todos los pacientes son únicos** por sus cuasi-identificadores:
  - subconjunto de MIMIC: 100 % (81 % después de B1, que agrupa la edad por década);
  - MIMIC demo completa: 90 %;
  - subconjunto de Synthea: 98 %; Synthea completa (1 151 personas): 70 %.
  - En todos los casos, el riesgo máximo antes de generalizar es 1: hay al menos una persona identificable con
    certeza.
- **Para llegar a k = 2 o k = 5, ARX tiene que borrar la edad entera en los subconjuntos.** También lleva la raza a
  `*` y suprime de 3 a 5 pacientes. En las bases completas alcanza con rangos de edad de 20 años y, en Synthea,
  el zip a 2 dígitos, pero suprime de 8 a 72 personas.
- **B1 no reduce el riesgo:** después de B1, ARX elige la misma transformación que antes en las dos bases. La
  década de edad y el zip de 3 dígitos no alcanzan.
- **La l-diversidad (l = 2) sobre el diagnóstico no cambia nada** una vez que se cumple k = 5: cada grupo ya tiene
  diagnósticos distintos.
- **Conclusión:** en bases chicas, k-anonimato a nivel de paciente destruye los cuasi-identificadores. Es un
  argumento para **datos sintéticos** (función D) cuando el destino necesita edad y demografía realistas.

## Entorno

- **ARX 3.9.2** (`libarx-3.9.2.jar`, el mismo de B3 sobre Pagila), en Docker con `eclipse-temurin:21-jdk`.
- Archivos (esta carpeta):
  - `ArxMedidor.java`: mide el riesgo, aplica k-anonimato y l-diversidad, y guarda solo métricas;
  - `b3_arx_salud.py`: arma el registro, las jerarquías y corre ARX.
- Los registros por paciente quedan en `salidas_grandes/`, fuera del repo; al repo van solo las métricas.

```bash
.venv/bin/python pruebas/salud/B3-arx/b3_arx_salud.py
```

### Registro «paciente»

| Base | Cuasi-identificadores | Sensible |
|---|---|---|
| MIMIC | sexo, edad (`anchor_age`), raza, seguro, idioma, estado civil (de la primera internación) | grupo del diagnóstico principal de la primera internación (versión CIE + primer carácter del código) |
| Synthea | sexo, edad al 2026-01-01, raza, etnia, estado civil, código postal de 3 dígitos | primera condición diagnosticada |

- **Jerarquías:**
  - edad: valor → rango de 5 años → 10 → 20 → `*` (niveles 0 a 4);
  - raza: valor → primera palabra («WHITE - RUSSIAN» → «WHITE») → `*`;
  - código postal: 3 dígitos → 2 → `*`;
  - el resto: valor → `*`.
- **Configuraciones:** (k = 2), (k = 5), (k = 5, l = 2 distinta). Supresión máxima: 10 % de las filas.
- **Conjuntos:**
  - el subconjunto de C1 antes de B1;
  - el mismo después de B1 `consistentes`;
  - la base completa (MIMIC demo: 100; Synthea: 1 151), para ver el efecto del tamaño.

## Resultados

| Base | Conjunto | Pacientes | Únicos antes | Riesgo máx. antes | k = 2: suprimidos | k = 2: generalización | k = 5: suprimidos | k = 5: generalización | Riesgo máx. después (k = 5) |
|---|---|---|---|---|---|---|---|---|---|
| MIMIC | subconjunto | 47 | 100 % | 1,00 | 3 | **edad `*`**, raza `*`, seguro `*` | 4 | **edad `*`**, raza `*`, sexo `*`, estado civil `*` | 0,20 |
| MIMIC | después de B1 | 47 | 81 % | 1,00 | 3 | ídem | 4 | ídem | 0,20 |
| MIMIC | demo completa | 100 | 90 % | 1,00 | 8 | edad en 20 años, raza `*`, estado civil `*` | 9 | ídem + sexo `*` | 0,20 |
| Synthea | subconjunto | 85 | 98 % | 1,00 | 5 | **edad `*`**, raza `*`, zip a 2 dígitos | 5 | ídem + estado civil `*` | 0,12 |
| Synthea | después de B1 | 85 | 98 % | 1,00 | 5 | ídem | 5 | ídem | 0,12 |
| Synthea | completa | 1 151 | 70 % | 1,00 | 63 | edad en 20 años, zip `*` | 72 | **edad `*`**, zip `*` | 0,20 |

Con k = 5 y l = 2 (diagnóstico o condición), ARX elige la misma transformación y suprime los mismos pacientes que con
k = 5 solo, en los seis conjuntos.

Métricas completas (niveles, clases de equivalencia, pérdida de información, segundos): `resultados/b3_metricas.json`
y `resultados/b3_resumen.md`.

## Hallazgos

- **El riesgo está en la combinación, no en ningún dato suelto.** Ninguno de los seis cuasi-identificadores es
  identificador por sí mismo; juntos, identifican a casi todos. Los detectores de A clasifican columnas una por
  una y no pueden ver esto: hace falta una medición como la de ARX sobre el registro completo.
- **B1 protege los identificadores, no los cuasi-identificadores.** Después de B1 sigue habiendo pacientes únicos y
  riesgo máximo 1. Seudonimizar el id no impide reconocer a alguien por una combinación del tipo «mujer, más de
  90 años, viuda, idioma distinto del inglés, Medicare» (ejemplo hipotético).
- **El tamaño manda:** con 47 u 85 pacientes no hay forma de cumplir k = 2 sin borrar la edad; con 1 151, alcanza
  con rangos de 20 años para k = 2, y para k = 5 vuelve a borrarla. En un entorno de pruebas, que suele ser un
  subconjunto chico, el k-anonimato es muy caro.
- **La l-diversidad sobre el diagnóstico no restringe más** con estos datos, porque los diagnósticos son muy
  variados. Podría importar con un atributo sensible de pocos valores (por ejemplo, VIH sí o no).
- **Para el sistema:** ofrecer la medición de ARX (riesgo antes y después) como **informe**, y dejar que el usuario
  elija entre generalizar (perdiendo utilidad) o sintetizar los cuasi-identificadores.

## Limitaciones

- La elección de cuasi-identificadores y jerarquías es propia; otras darían otros números.
- Modelo de riesgo del fiscal (el atacante sabe que la persona está en la base): es el más exigente.
- El diagnóstico se agrupó de forma gruesa (versión CIE + primer carácter); con el código completo, la
  l-diversidad podría restringir distinto.
- No se escribió el resultado de ARX en la base: se usó solo como medidor.

## Evidencia

- `resultados/b3_metricas.json` (18 corridas) y `resultados/b3_resumen.md`.
- `salidas_grandes/` (fuera del repo): registros y jerarquías por conjunto.
