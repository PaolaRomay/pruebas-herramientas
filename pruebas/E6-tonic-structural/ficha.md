# E6 — Tonic Structural — Validar privacidad

**Quién / cuándo:** _(completar)_, _(fecha)_. Requiere el trial de Structural y la base anonimizada de B4.
**Fuente de cada dato:** D = documentación, P = prueba propia. Salvo donde dice D, todo es P.

[← Estado](../ESTADO.md) · [Ficha de Tonic](../_herramientas/tonic.md) · [B4](../B4-tonic-structural/ficha.md) · [E5](../E5-tonic-fabricate/ficha.md) · [E3](../E3-chequeos-propios/ficha.md)

**Pregunta:** después de anonimizar con Structural, ¿cuánto riesgo de reidentificación queda? Structural parte de los datos reales, a diferencia de Fabricate (E5), que no los ve, y de SDV (E1), que aprende de ellos.

> **Pendientes de decisión:**
> - Decidido (2026-10-11, propuesta de Jero, a avisar a Paola): **E1 adopta el split de E3**: 200 clientes (20 %), semilla `e3`, `pruebas/E3-chequeos-propios/resultados/e3_control.csv`.
> - **Structural no tiene que ver a los clientes de control.** `pagila_origen` en Neon es una copia exacta y los incluye. Para E6 hay que anonimizar un origen **sin el control**, es decir, el equivalente a `e3_entrenamiento`. Ver el pendiente en [B4](../B4-tonic-structural/ficha.md). Si se evalúa una base generada a partir del origen completo, el control deja de ser control y el riesgo sale subestimado. Decisión (2026-10-11): **se usa el origen completo** (`pagila_origen`, con el control) y se anota como limitación: el control deja de ser control y el riesgo de Anonymeter sale **subestimado**. B4 se corre una sola vez.

## Entorno

- Candidata: la copia local del destino de B4, `b4_c1` o la corrida que se acuerde, traída con `scripts/traer_neon.py`. Viene del origen completo (ver decisión arriba): los resultados de Anonymeter son una cota inferior del riesgo.
- Evaluador: `pruebas/E3-chequeos-propios/evaluar_bd.py evaluar --tipo anonimizada`, con las versiones de `requirements.lock.txt`. Equipo: _(chip, RAM, macOS)_.
- Registro evaluado: «persona» (customer + address + city + country), igual que E5 y E1.

## Qué se midió y resultado

Métrica mínima de «Validar privacidad»: Anonymeter (singling out, linkability, inference) frente a un conjunto de control. Más los chequeos de E3.

| Ataque | Detalle | Riesgo | IC 95 % |
|---|---|---|---|
| Singling out | univariado | _(completar)_ | |
| Singling out | multivariado (3 columnas) | _(completar)_ | |
| Linkability | nombre + email ↔ distrito + CP + teléfono + ciudad + país | _(completar)_ | |
| Inference | secretos `district`, `city`, `country`, `postal_code` | _(completar)_ | |

**Chequeos de E3:**
- Copias exactas: _(completar)_.
- Distancia mediana al registro real más cercano: _(completar)_.
- Índice de memorización: _(completar)_.

Ojo: una anonimización que conserva columnas, como ciudad, país o código postal si no se tocaron, tiene que dar más riesgo de linkability e inference que una síntesis. Anotar qué columnas dejó B4 sin tocar: _(completar)_.

**Comparación:**

| Prueba | Cómo se genera | Singling out (univ.) | Linkability | Copias exactas |
|---|---|---|---|---|
| E5 · Fabricate | Desde el esquema, sin datos | 0,182 | 0,085 | 0 % |
| E6 · Structural (esta) | Anonimiza datos reales | _(completar)_ | | |
| E1 · SDV | Aprende de los datos | _(completar desde E1)_ | | |

Privacy Hub de Structural (D): informa qué columnas quedaron protegidas, pero no mide riesgo de reidentificación. Lo que muestra para esta configuración: _(completar, captura)_.

## Esfuerzo

- Horas hasta la primera corrida: _(completar)_
- Problemas encontrados: _(completar)_

## Hallazgos

- Limitaciones vistas en la práctica: Structural vio a los clientes de control (origen completo), así que el riesgo medido está subestimado. _(completar con lo que surja)_
- Requisitos que surgen para el sistema: _(completar)_

## Evidencia

- `resultados/<candidata>/`: salida de `evaluar_bd.py` (`e3_resumen.md`, `e3_privacidad.csv`, `e3_dcr.csv`, ...).
- `evidencia/`: captura del Privacy Hub.
