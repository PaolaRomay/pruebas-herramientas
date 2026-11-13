# Metanome — ficha de herramienta (Bloque 1)

**Quién / cuándo:** Jero (relevado y probado por Claude Code a pedido de Jero), 2026-11-13.
**Fuente de cada dato:** D = documentación o repositorio, P = prueba propia (marcado en cada línea).

[← Estado de las pruebas](../ESTADO.md) · [SchemaSpy](schemaspy.md) ·
[Prueba F2m sobre MIMIC](../salud/F2-relaciones-herramientas/ficha.md)

## Qué es

- Plataforma de **perfilado de datos** del grupo de sistemas de información del Hasso Plattner Institute (HPI,
  Alemania). Reúne algoritmos que descubren metadatos a partir de los valores: claves candidatas, dependencias
  funcionales y **dependencias de inclusión** (D).
- **Dependencia de inclusión (IND):** A ⊆ B, todos los valores de la columna A aparecen en la columna B. Toda FK que se
  cumple es una IND; no toda IND es una FK (D, P).
- Algoritmos usados: **BINDER** y **SPIDER**, que encuentran IND unarias (y BINDER también de varias columnas) sobre
  archivos o sobre una base (D).
- Función en el sistema: **entender el esquema** (funcionalidad F2, relaciones no declaradas), como fuente de
  candidatos por datos, sin depender de los nombres.

## Datos clave

| Dato | Valor |
|---|---|
| Licencia | **Apache 2.0**: la plataforma, el repositorio de algoritmos y la línea de comandos `metanome-cli` (D, GitHub, verificado el 2026-11-13). Permisiva: se puede integrar en cualquier sistema conservando el aviso de copyright. |
| Versiones | La plataforma no publica versiones (etiquetas `metanome-0.0.1`, `metanome-0.0.2`, `1.0.0`). Jar de los algoritmos publicados por HPI: `BINDERFile` y `SPIDERFile` 0.0.2 (compilados con Java 8, 2015). `metanome-cli` 1.1.0 (2017) (D, P) |
| Último cambio | Plataforma: 2025-06-05. Algoritmos: 2023-05-15. `metanome-cli`: 2022-04-12 (D) |
| Ejecución | Local. Java (en la prueba, Java 21 en Docker, sin instalar nada en la Mac) (P) |
| Entrada | CSV (una tabla por archivo) o una base por JDBC (D) |
| Usa IA | No |
| Repositorios | https://github.com/HPI-Information-Systems/Metanome · https://github.com/HPI-Information-Systems/metanome-algorithms · https://github.com/sekruse/metanome-cli |
| Documentación | https://hpi.de/en/database-group/projects/data-integration-projects/data-profiling-and-analytics/metanome-data-profiling/ |

## Lo que mostró la prueba (F2m, demo de MIMIC-IV)

- 2 349 IND en 5 s (BINDER) y 9 s (SPIDER), las mismas en los dos (P).
- Sola, casi todo es ruido (97 % de inclusiones ciertas pero sin sentido). Con dos filtros simples (la columna padre
  es única; el nombre de la hija termina en el de la padre): **73 propuestas, las 20 de 20 relaciones no declaradas
  que se cumplen, 50 de 51 FK declaradas, precisión 0,96**, y 2 relaciones reales que no estaban mapeadas (P).
- No ve las 5 relaciones con filas huérfanas: busca inclusiones exactas (P).

## Cómo se corre (y problemas)

```bash
java -cp metanome-cli-1.1.0.jar:BINDERFile-0.0.2-SNAPSHOT.jar de.metanome.cli.App \
  --algorithm de.metanome.algorithms.binder.BINDERFile.BINDERFile --files load:archivos.txt \
  --file-key INPUT_GENERATOR --separator , --header --algorithm-config TEMP_FOLDER_PATH:/tmp -o file:binder
```

- El nombre del parámetro de entrada (`INPUT_GENERATOR`) no está documentado: se sacó de las clases del jar (P).
- Los parámetros booleanos (`DETECT_NARY`) fallan con `AbstractMethodError`: el jar del algoritmo y la línea de
  comandos usan versiones distintas de la interfaz de Metanome (P).
- El nombre de la tabla se corta en el primer punto del archivo (`esquema.tabla.csv` queda como `esquema`) (P).
- Proyecto académico con poca actividad: sirve, pero el sistema tendría que reimplementar el algoritmo (SPIDER es
  simple: ordenar valores y recorrerlos en paralelo) o mantener una copia propia.
