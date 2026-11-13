# SchemaSpy — ficha de herramienta (Bloque 1)

**Quién / cuándo:** Jero (relevado y probado por Claude Code a pedido de Jero), 2026-11-13.
**Fuente de cada dato:** D = documentación o repositorio, P = prueba propia (marcado en cada línea).

[← Estado de las pruebas](../ESTADO.md) · [Metanome](metanome.md) ·
[Prueba F2m sobre MIMIC](../salud/F2-relaciones-herramientas/ficha.md)

## Qué es

- Herramienta de **documentación de bases de datos**: se conecta por JDBC, lee el catálogo y genera un sitio HTML con
  tablas, columnas, restricciones, diagramas de relaciones y anomalías (D). También deja un XML por esquema con todas
  las relaciones (P).
- **Relaciones implícitas** (*implied relationships*): además de las FK declaradas, propone una relación cuando una
  columna tiene el mismo nombre y tipo que la **clave primaria** de otra tabla (D, confirmado en P). No mira los
  datos.
- Función en el sistema: **entender el esquema** (funcionalidad F2, relaciones no declaradas), como fuente de
  candidatos por nombre. Lo que sale alimenta la extracción de subconjuntos y la validación de integridad.

## Datos clave

| Dato | Valor |
|---|---|
| Licencia | **LGPL-3.0** (GitHub, archivos `COPYING` y `COPYING.LESSER`; D, verificado el 2026-11-13). Código abierto, copyleft débil: se puede usar como herramienta o biblioteca dentro de un sistema con otra licencia; las modificaciones a SchemaSpy se publican bajo LGPL. |
| Última versión | v7.0.2 (2025-09-20) (D) |
| Último cambio en el repositorio | 2026-03-05 (D) |
| Ejecución | Local. Java; imagen oficial de Docker `schemaspy/schemaspy` (también para arm64) (D, P) |
| Motores | Los que tengan driver JDBC (PostgreSQL, MySQL, Oracle, SQL Server…) (D) |
| Usa IA | No |
| Repositorio | https://github.com/schemaspy/schemaspy |
| Documentación | https://schemaspy.readthedocs.io |

## Lo que mostró la prueba (F2m, demo de MIMIC-IV)

- 15 relaciones implícitas en 9 s (con el sitio HTML): **10 de las 25 relaciones no declaradas**, precisión 0,67 (P).
- Encuentra las relaciones que se cumplen «casi»: las 5 con filas huérfanas, que un método por datos no ve (P).
- **No ve** relaciones hacia tablas sin clave primaria (`caregiver`, `provider`), entre esquemas (procesa un esquema
  por vez) ni con nombres distintos (`order_provider_id → provider_id`) (P).
- Propone relaciones falsas por coincidencia de sufijo (`spec_itemid → d_labitems.itemid`) (P).

## Alternativa relevada, no probada

- **SchemaCrawler** (https://www.schemacrawler.com): hace algo parecido («asociaciones débiles» por nombre). Licencia a
  elección EPL-2.0, LGPL-3.0 o GPL-3.0; la distribución con los drivers JDBC incluidos es solo GPL-3.0 (D, página de
  licencias, 2026-11-13). Muy activa (v18.0.2, 2026-11-10).
