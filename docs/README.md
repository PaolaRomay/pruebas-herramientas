# Pruebas de herramientas: cómo leer este repositorio

Este repositorio reúne las **pruebas de herramientas existentes** que hicimos Paola y Jero para el estado del
arte de la tesis de grado (Ingeniería en Computación, FING, UdelaR). El tema de la tesis es un proceso asistido
por IA para extraer, anonimizar y generar bases de datos de preproducción a partir de datos productivos.

Cada herramienta se prueba **con las mismas preguntas, las mismas métricas y los mismos datos** (la base de
ejemplo Pagila), para poder compararlas. Esta página explica qué leer y en qué orden. No hace falta instalar
nada: todos los resultados están escritos en los archivos `.md` y en los gráficos.

**Informe de avance (primera entrega):** [proyecto-de-grado-entrega-1.pdf](proyecto-de-grado-entrega-1.pdf), el relevamiento del estado del arte en el que venimos avanzando. Este repositorio tiene las pruebas que lo respaldan.

## Recorrido de lectura

| Paso | Documento | Para qué |
|---|---|---|
| 1 | [Plan de pruebas](plan-de-pruebas.md) | Qué se prueba, con qué métricas, y el estado de cada prueba |
| 2 | [Glosario y método común](glosario-y-metodo.md) | Los datos (Pagila), la lista de referencia, el conjunto de control y cómo se calcula cada métrica |
| 3 | [Comparativa](comparativa.md) | Las herramientas lado a lado, por función, con los resultados que hay hoy |
| 4 | Las fichas de cada prueba (tabla de abajo) | El detalle de cada herramienta: entorno, resultados, hallazgos y evidencia |

Para una lectura rápida alcanza con los pasos 3 y 4. Si un término no se entiende, está en el paso 2.

## Pruebas con resultados

| ID | Herramienta | Función | Ficha | Qué mirar primero |
|---|---|---|---|---|
| A1 | Presidio | Detectar | [ficha](../pruebas/A1-presidio/ficha.md) | Tabla de métricas y «Hallazgos» |
| A7 | Tonic Textual | Detectar | [ficha](../pruebas/A7-tonic-textual/ficha.md) | 🔄 en curso: todavía sin resultados |
| D2 | MOSTLY AI | Sintetizar | [ficha](../pruebas/D2-mostlyai/ficha.md) | «En pocas palabras», los gráficos y «Hallazgos» |
| D5 | Tonic Fabricate | Sintetizar | [ficha](../pruebas/D5-tonic-fabricate/ficha.md) | «En pocas palabras» y «¿Qué pasó con las fechas de los pagos?» |
| E3 | Chequeos propios (evaluador común) | Validar | [ficha](../pruebas/E3-chequeos-propios/ficha.md) | «Validación del evaluador» |

El estado de todas las pruebas, incluidas las pendientes y las que se hicieron fuera del repo, está en el
[plan](plan-de-pruebas.md#todas-las-pruebas-y-su-estado).

## Cómo está organizado

```
docs/                          ← empezar acá: plan, glosario, comparativa
pruebas/
  _plantilla/ficha.md          estructura común de todas las fichas
  <ID>-<herramienta>/          una carpeta por prueba
    ficha.md                   el informe de la prueba (lo primero que hay que leer)
    <script>.py                el código que la corrió
    resultados/                tablas y gráficos generados por el script (.md, .csv, .png)
    evidencia/                 errores de carga, logs y otros respaldos
    salidas_grandes/           (no está en el repo: bases generadas, modelos, reportes HTML pesados)
resultados_comparados/         tablas que juntan todas las pruebas de una misma función
  deteccion_resumen.md         función A
  sintesis_resumen.md          función D
  graficos/                    gráficos comparativos
scripts/                       herramientas comunes: descarga de Pagila, integridad, comparadores, gráficos
data/columnas_sensibles_borrador.csv   la lista de referencia de columnas sensibles
README.md                      cómo levantar el entorno (base de datos y Python) para reproducir las pruebas
```

## Cómo leer una ficha

Todas las fichas siguen la misma estructura:

1. **Entorno:** equipo, versiones exactas y datos usados.
2. **Qué se midió y resultado:** las métricas mínimas de su función.
3. **Esfuerzo:** problemas para llegar a la primera corrida.
4. **Hallazgos:** limitaciones y requisitos que surgen para el sistema de la tesis.
5. **Evidencia:** dónde están los resultados y respaldos.

Cada dato está marcado **D** (sale de la documentación de la herramienta) o **P** (prueba propia). Los tiempos
dependen del equipo: Jero usa una Mac M5 Pro de 16 GB y Paola una M1 de 8 GB.

## Lo que no está en el repositorio, y por qué

- **`salidas_grandes/`** de cada prueba: las bases sintéticas, los modelos entrenados y los reportes HTML de
  las herramientas (en D2 son 671 MB). Pesan demasiado para versionarlos y se regeneran con los scripts.
  Todo dato que importa para entender la prueba está copiado en la ficha, en `resultados/` o en un gráfico.
- **Las bases de datos del contenedor** (`d2_auditoria`, `e3_entrenamiento`, etc.): existen solo en la
  máquina donde se corrió la prueba.
- **Los reportes HTML** de herramientas como MOSTLY AI: GitHub muestra el código de un `.html`, no la página.
  En su lugar, los gráficos importantes están en PNG dentro de las fichas.

Para **reproducir** una prueba: levantar el entorno según el [README principal](../README.md) y seguir la
sección «Uso» del script de cada prueba.
