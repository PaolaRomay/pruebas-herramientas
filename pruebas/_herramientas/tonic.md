# Tonic.ai — ficha de herramienta (Bloque 1)

**Quién / cuándo:** Jero. Datos de documentación consultados el 06/10/2026 y completados el 2026-10-11.
**Fuente de cada dato:** D = documentación, P = prueba propia (marcado en cada línea).

[← Estado de las pruebas](../ESTADO.md) · [Plan](../../docs/plan-de-pruebas.md) · [Neon](neon.md)

Tonic son **tres productos separados**, con cuentas, precios y alcance distintos. Son comerciales: se **analizan, no se integran** en el sistema de la tesis.

| Producto | Qué hace | Acceso usado | Pruebas |
|---|---|---|---|
| Tonic Textual | Detecta y redacta entidades sensibles en **texto**. No entiende tablas ni claves. Compite con Presidio. (D) | textual.tonic.ai, cuenta gratis de 100.000 palabras (D) | [A7](../A7-tonic-textual/ficha.md) |
| Tonic Fabricate | Chat (Data Agent) que genera bases **sintéticas desde cero** a partir de un esquema o de un pedido en lenguaje natural. No necesita los datos reales, aunque acepta una muestra. (D) | fabricate.tonic.ai, plan Free con USD 5 de crédito por mes (D) | [D5](../D5-tonic-fabricate/ficha.md), [E5](../E5-tonic-fabricate/ficha.md), [G2](../G2-tonic-fabricate/ficha.md) |
| Tonic Structural | Se conecta a una base, escanea columnas sensibles, aplica generadores por columna, hace subsetting y escribe una base destino. (D) | app.tonic.ai, trial de 14 días con correo institucional (D). Pagila cargada en Neon: ver [neon.md](neon.md) | [A8](../A8-tonic-structural/ficha.md), [B4](../B4-tonic-structural/ficha.md) (incluye fail-closed), [C2](../C2-tonic-structural/ficha.md), [E6](../E6-tonic-structural/ficha.md), [G3](../G3-tonic-structural/ficha.md) |

## Tonic Structural

- Versión: v1885, del 6 de octubre de 2026, según las release notes (D, https://www.tonic.ai/tonic-structural-release-notes/v1885). Sale aproximadamente una versión por día (D, https://docs.tonic.ai/app/resources/release-notes).
- Versión vista en la app: _(completar al abrir el trial: versión que muestra app.tonic.ai el día de la prueba)_ (P).
- Licencia: propietaria, SaaS. Términos: https://www.tonic.ai/terms-and-conditions (D).
- Precio: sin precio público. Planes Professional (hasta 10 TB de origen y 10 usuarios) y Enterprise, los dos a cotizar (D, https://www.tonic.ai/pricing).
  - Vendr estima una mediana de USD 45.525/año, y USD 18.000–32.000/año con 1–3 fuentes de datos (D, Vendr, https://vendr.com/marketplace/tonicai, mediana sobre 33 compras).
- Restricciones de la licencia: prohíbe ingeniería inversa, obras derivadas y el uso «en beneficio de un competidor» (D, términos).
- Capacidades (D):
  - Genera: Parcial.
  - Anonimiza: Sí.
  - Detecta: Sí.
  - Subconjuntos: Sí.
  - Valida: Parcial. Tiene Privacy Hub y bloquea la generación ante cambios de esquema, pero no mide riesgo de reidentificación.
- Conectores: PostgreSQL 14–18, SQL Server 2016+, MySQL, Oracle (D).
- Extensibilidad: API REST, servidor MCP y generadores compuestos. No admite código propio (D).
- Ejecución local: solo con Enterprise autoalojado. El trial corre en la nube de Tonic, por eso Pagila se cargó en Neon (D).
- Implicancia para la tesis: con la licencia del trial, Pagila tiene que salir del equipo. Con datos productivos reales, eso exigiría el plan autoalojado.

## Tonic Fabricate

- Versión: no muestra número de versión; se registra la fecha de cada corrida (P, ver [D5](../D5-tonic-fabricate/ficha.md)).
- Licencia: propietaria, SaaS. Términos generales de Tonic, los mismos que Structural: no hay términos propios por producto (D, https://www.tonic.ai/terms-and-conditions, actualizados el 5 de febrero de 2026).
- Precio: Free USD 0 (USD 5 de crédito por mes) y Plus USD 29/mes (USD 25 de crédito y después pago por uso). Enterprise a cotizar (D, https://www.tonic.ai/pricing). El consumo se mide en tokens.
- Capacidades (D):
  - Genera: Sí, desde el esquema. En D5 no se le pasaron datos, pero buscó en internet la base pública (P).
  - Anonimiza: No, no ve datos.
  - Detecta: No. La documentación no describe una función de detección de datos sensibles.
  - Subconjuntos: Parcial. Se le puede pedir al Data Agent que exporte registros seleccionados.
  - Valida: Parcial. Los workflows pueden validar los datos nuevos. No mide el riesgo de privacidad.
  - Repetibilidad: no tiene semilla. Para regenerar igual, la documentación propone el «reusable generator approach», un script de workflow que se vuelve a correr (D, https://docs.tonic.ai/fabricate/databases-and-data/reusable-generator-approach).
- Formatos de salida (D, https://docs.tonic.ai/fabricate/databases-and-data/data-agent-db-export-data):
  - Para todos los planes: CSV, JSON, JSONL, MySQL, PostgreSQL y SQLite. En D5 se usó la exportación a .sql.
  - Enterprise: además Parquet, Avro, Delta Lake, Iceberg, SQL Server, Oracle, MongoDB, XML, entre otros.
- Conectores: Live Connect a PostgreSQL, MySQL, SQL Server, Oracle, Snowflake, BigQuery, Redshift y Microsoft Fabric. Requiere licencia Enterprise (D).
- Extensibilidad: API REST, paquete npm y servidor MCP (D, https://docs.tonic.ai/fabricate/fabricate-api). La API acepta `format` (`sql`, `sqlite`, `postgres-optimized`, `csv`, `jsonl`) y no tiene parámetro de semilla.
- Ejecución local: solo con Enterprise autoalojado, con Docker Compose (D, https://docs.tonic.ai/fabricate/self-hosting-fabricate/deploying-and-managing-a-self-hosted-instance).

## Tonic Textual

- Versión: la app web no muestra número de versión. Se registra la fecha de la corrida, 2026-10-03 (P, [A7](../A7-tonic-textual/ficha.md)).
- Licencia: propietaria, SaaS. Términos generales de Tonic (D, https://www.tonic.ai/terms-and-conditions).
- Precio: pago por uso, tarifa fija por cada 1.000 palabras, sin precio publicado. Enterprise a cotizar (D, https://www.tonic.ai/pricing). Cuenta gratis de 100.000 palabras: es la que se usó en A7 (P); la página de precios no la menciona.
- Capacidades (D):
  - Genera: Parcial. El modo Synthesis reemplaza cada valor detectado por uno falso realista, y el mismo valor original siempre recibe el mismo reemplazo. No genera bases (D, https://docs.tonic.ai/textual/dataset-configure-redaction/textual-datasets-select-handling-type).
  - Anonimiza: Sí, sobre texto.
  - Detecta: Sí, sobre texto.
  - Subconjuntos: No.
  - Valida: Parcial. El Request Auditor mide la calidad de la detección (entidades que se escaparon). No mide el riesgo de reidentificación (D, https://docs.tonic.ai/textual/tonic-textual-api/request-auditor).
- Formatos: TXT, CSV, TSV, JSON, DOCX, HTML, XLSX, PPTX, PDF e imágenes (PNG, JPG, TIF) (D, https://docs.tonic.ai/textual/dataset-files/dataset-file-types).
- Fuentes: archivos subidos, Amazon S3, Azure, SharePoint y OneLake (Microsoft Fabric) (D).
- Extensibilidad: API REST y SDK de Python, `tonic-textual` en PyPI (D, https://docs.tonic.ai/textual/tonic-textual-api/textual-python-sdk).
- Ejecución local: sí, autoalojado con Kubernetes o Docker. Según la página de precios, es del plan Enterprise (D, https://docs.tonic.ai/textual/textual-install-administer/deploying-a-self-hosted-instance).

## Pendientes

- Confirmar en la app la versión de Structural (P).
