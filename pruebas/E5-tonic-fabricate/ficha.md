# E5 — Tonic Fabricate — Validar privacidad

**Quién / cuándo:** Jero. Evaluación corrida el 2026-10-10 con E3 sobre la base de D5.
**Fuente de cada dato:** D = documentación, P = prueba propia. Salvo donde dice D, todo es P.

[← Estado](../ESTADO.md) · [Ficha de Tonic](../_herramientas/tonic.md) · [D5](../D5-tonic-fabricate/ficha.md) · [E3](../E3-chequeos-propios/ficha.md) · [E6](../E6-tonic-structural/ficha.md)

**Pregunta:** ¿cuánto riesgo de reidentificación tiene una base sintetizada sin ver los datos reales? Es la **línea base de «síntesis pura»**: Fabricate generó desde el esquema y no se le pasaron datos. Pero consultó en internet la base pública (ver [D5](../D5-tonic-fabricate/ficha.md)), así que no es síntesis pura en sentido estricto. Contra esta línea se comparan E6 (Structural, anonimiza datos reales) y E1 (SDV, aprende de los datos).

> **Pendientes de decisión:**
> - Decidido (2026-10-11, propuesta de Jero, a avisar a Paola): **E1 adopta el split de E3**: 200 clientes (20 %), semilla `e3`, `pruebas/E3-chequeos-propios/resultados/e3_control.csv`. Es el que usó esta evaluación, así que E5 no se rehace.
> - ~~Propuesta a confirmar~~ **Confirmado (2026-10-11):** E5 queda cubierta con E3 sobre la base de D5, sin una corrida aparte.

## Entorno

- Candidata: `d5_auditoria`, la base de Fabricate de D5 cargada sin restricciones en el contenedor local (120 clientes, 125 direcciones). Ver [D5](../D5-tonic-fabricate/ficha.md).
- Evaluador: `pruebas/E3-chequeos-propios/evaluar_bd.py evaluar --candidata d5_auditoria --tipo sintetica`. Versiones: anonymeter 1.1.0, sdv 1.32.1, sdmetrics 0.25.0, pandas 3.0.6, numpy 1.26.4. PostgreSQL 16.4. Mac arm64, macOS 26.6.2.
- Registro evaluado: «persona» (customer + address + city + country). Son 120 filas sintéticas contra 799 reales (Pagila sin el control) y 200 de control.

## Qué se midió y resultado

Métrica mínima de «Validar privacidad»: Anonymeter (singling out, linkability, inference) frente a un conjunto de control. Valores copiados de `pruebas/E3-chequeos-propios/resultados/d5_auditoria/e3_privacidad.csv`.

| Ataque | Detalle | Riesgo | IC 95 % |
|---|---|---|---|
| Singling out | univariado | 0,182 | 0,104–0,259 |
| Singling out | multivariado (3 columnas) | 0,033 | 0,000–0,071 |
| Linkability | nombre + email ↔ distrito + CP + teléfono + ciudad + país | 0,085 | 0,000–0,192 |
| Inference | secreto `district` | 0,000 | 0,000–0,032 |
| Inference | secreto `city` | 0,000 | no supera al azar |
| Inference | secreto `country` | 0,051 | 0,000–0,114 |
| Inference | secreto `postal_code` | 0,000 | no supera al azar |

**Chequeos de E3** (`d5_auditoria/e3_dcr.csv` e `e3_integridad.csv`):
- 0 % de copias exactas.
- Distancia mediana al registro real más cercano: 0,981. El control está a 0,546.
- Índice de memorización: −1,13, o sea, más lejos de los datos reales que el propio control.
- Integridad: 0 violaciones de FK, PK, UNIQUE, NOT NULL y CHECK.

**Lectura:** el riesgo es bajo según lo medido (0 % de copias exactas, memorización −1,13). No es bajo por construcción: Fabricate consultó en internet la base pública (D5). Los valores distintos de 0 (singling out univariado, linkability) son compatibles con coincidencias de valores comunes, como nombres frecuentes o países grandes, más que con una filtración.

**Comparación:**

| Prueba | Cómo se genera | Singling out (univ.) | Linkability | Copias exactas |
|---|---|---|---|---|
| E5 · Fabricate (esta) | Desde el esquema; consultó la base pública en internet | 0,182 | 0,085 | 0 % |
| E6 · Structural | Anonimiza datos reales | _(completar desde E6)_ | | |
| E1 · SDV | Aprende de los datos | _(completar desde E1)_ | | |

## Esfuerzo

- Sin esfuerzo extra: es la misma corrida de E3 sobre D5.

## Hallazgos

- Una base generada sin pasarle datos reales da la referencia del riesgo «de fondo» por coincidencias. Por debajo de este valor, Anonymeter no distingue una herramienta de otra.
- Anonymeter no es determinista (E3): leer los riesgos con su intervalo y no compararlos en el tercer decimal.
- Requisitos que surgen para el sistema:
  - Medir la privacidad siempre, también en la síntesis «desde el esquema»: una herramienta puede traer datos de afuera (acá, la base pública en internet) aunque no se le pasen.
  - Registrar qué vio cada herramienta (`--entrenada-con`) y mantener un control que no haya visto, para que el riesgo no salga subestimado.
  - Informar cada riesgo con su intervalo de confianza y compararlo con esta línea base, no con 0.
  - Correr Anonymeter más de una vez (o con semilla fija) antes de comparar herramientas, porque no es determinista.

## Evidencia

- `pruebas/E3-chequeos-propios/resultados/d5_auditoria/` (`e3_resumen.md`, `e3_privacidad.csv`, `e3_dcr.csv`, `e3_integridad.csv`).
- `resultados/` y `evidencia/` de esta carpeta quedan para una nueva corrida si cambia el split.
