# B1m / B1s — PostgreSQL Anonymizer sobre los subconjuntos de MIMIC y Synthea — Anonimizar

**Quién / cuándo:** Jero (ejecutado por Claude Code a pedido de Jero), 2026-11-09.
**Fuente de cada dato:** P = prueba propia, salvo donde dice D.

[← C1m / C1s subconjunto](../C1-subconjunto/ficha.md) · [B3m / B3s ARX](../B3-arx/ficha.md) ·
[Lista de referencia](../../_bases/referencia/taxonomia.md) · [A5 `anon.detect`](../A5-anon-detect/ficha.md)

Enmascaramiento estático (en el lugar) de los subconjuntos de la etapa 5: `mimic_c1_50` (47 pacientes, 733 000 filas)
y `synthea_c1_10` (85 pacientes, 103 000 filas). La pregunta central: ¿se puede anonimizar una base relacional de
salud **sin romper las relaciones ni la coherencia de las fechas**?

## En pocas palabras

- **Con las funciones que trae la extensión, la base queda íntegra pero incoherente y reversible:**
  - las 51 FK se mantienen;
  - pero las fechas se mueven por fila, al azar: 47 altas antes del ingreso, 200 traslados al revés y 249 000
    mediciones de UCI fuera de su estadía;
  - el id del paciente queda a la vista dentro de `poe_id` y `emar_id` (19 144 filas);
  - con un solo par original/seudónimo se revierten los 47 pacientes.
- **Con funciones propias, la base queda íntegra y coherente:**
  - FK válidas: 51 de 51 en MIMIC y 40 de 40 en Synthea;
  - **0 incoherencias nuevas** en las 13 reglas de fechas;
  - un único desplazamiento de fechas por paciente (47 de 47 y 85 de 85);
  - duración de las 115 internaciones intacta y sin fuga por ids compuestos.
- **Synthea:** nombres, SSN, licencia y pasaporte reemplazados en el 100 % de los pacientes, con el mismo formato;
  dirección falsa, geografía generalizada como pide HIPAA.
- **Dos límites del seudónimo con hash:**
  - **colisiones:** conservar el formato de 8 dígitos hace que no sea una biyección. En la MIMIC completa
    (cientos de miles de pacientes) habría claves primarias repetidas;
  - **reversión con la sal:** quien la conozca recorre los 10 millones de ids posibles en 3 s y queda con el
    original entre los candidatos para los 47 pacientes.
- **Lo que hubo que resolver para que funcione:**
  - FK diferibles: la extensión las difiere, pero las de MIMIC no lo eran;
  - un rol que no sea superusuario;
  - funciones propias en un esquema declarado de confianza;
  - `anon.init()` y permisos de lectura sobre los datos falsos.
- **Tiempo:** 3,6 minutos con las funciones nativas y 9 a 10 minutos con las propias, con la imagen emulada en la
  Mac.

## Entorno

- Equipo: Mac M5 Pro, 16 GB, macOS 26.6.2. Python 3.11.16.
- **PostgreSQL Anonymizer 3.3.2** sobre PostgreSQL 18.6: imagen `registry.gitlab.com/dalibo/postgresql_anonymizer:stable`,
  digest `sha256:379c4c88…6ce1`. Solo existe para amd64: **corre emulada en la Mac** (los tiempos son pesimistas).
- Contenedor propio `salud-anon` (puerto 55434), el mismo de A5; el `docker-compose.yml` común no se toca.
- Datos: copia de los subconjuntos de C1 (`pg_dump -Fc` desde `pagila-db`, restaurada en `salud-anon`). Los
  subconjuntos originales no se modifican.
- Archivos (esta carpeta):
  - `masc.sql`: funciones propias;
  - `b1_anon_salud.py`: copia, reglas, enmascaramiento y mediciones.

```bash
.venv/bin/python pruebas/salud/B1-anon/b1_anon_salud.py --base mimic --variante nativas
.venv/bin/python pruebas/salud/B1-anon/b1_anon_salud.py --base mimic --variante consistentes
.venv/bin/python pruebas/salud/B1-anon/b1_anon_salud.py --base synthea --variante consistentes
```

### Cómo trabaja

1. Copia el subconjunto al contenedor y lo prepara:
   - extensión y sal secreta de la base;
   - las tablas pasan a ser del rol `enmascarador`, que no es superusuario: la extensión no deja enmascarar como
     superusuario;
   - las FK pasan a `DEFERRABLE`;
   - carga `masc.sql` y `anon.init()`.
2. Guarda en un esquema aparte (`verif`, sin reglas) los ids y las fechas originales, para medir después.
3. **Genera las reglas desde la lista de referencia congelada:** cada columna recibe una función según su
   categoría (identificador de paciente, fecha HIPAA, identificador directo…) y la variante. No se escribió
   ninguna regla a mano por columna.
4. `anon.anonymize_database()` como `enmascarador`:
   - un `UPDATE` por tabla, con todas las columnas a la vez, así cada regla ve los valores originales de la fila;
   - todo en una transacción, con las FK diferidas que se validan al final.
5. Mide coherencia, FK, consistencia por paciente, fugas y reversión.

### Reglas por variante

| Qué | MIMIC `nativas` (solo la extensión) | MIMIC `consistentes` y Synthea (funciones propias) |
|---|---|---|
| Ids de paciente, internación, estadía, cuidador | `anon.pseudo_shift`: suma una constante secreta | `masc.id_hash`: hash con sal; mismo largo y primer dígito (Synthea: UUID con hash) |
| Ids de profesionales (texto) | `anon.hash`, recortado al largo de la columna | `masc.texto_hash`: mismo largo y primer carácter |
| Ids compuestos `poe_id`, `emar_id` («<subject_id>-<n>») | — (la extensión no los ve) | `masc.id_compuesto`: seudonimiza la parte del paciente |
| Fechas (`cuasi_hipaa`) | `anon.dnoise(fecha, 180 días)`: ruido por fila | `masc.desplazar(fecha, paciente)`: entre −180 y +180 días, **el mismo para todas las fechas del paciente** |
| Edad (`anchor_age`) | `anon.noise(edad, 0,2)` | `masc.decada` (45 → 40) |
| Synthea: nombres | — | `anon.pseudo_first_name` / `pseudo_last_name` (deterministas por paciente) |
| Synthea: SSN, licencia, pasaporte, UDI, n.º de afiliado | — | `masc.mismo_formato`: cada dígito por otro derivado del hash |
| Synthea: dirección | — | `anon.fake_address()` |
| Synthea: ciudad, lugar de nacimiento | — | `anon.pseudo_city` |
| Synthea: condado, FIPS | — | `NULL` (HIPAA: más chico que un estado) |
| Synthea: código postal, coordenadas | — | zip a 3 dígitos; lat/lon con 1 decimal (unos 11 km) |
| Synthea: ingresos y gastos de salud | — | `anon.noise(…, 0,1)` |
| Datos de salud, catálogos, técnicas | quedan igual | quedan igual |

Columnas enmascaradas: 111 (MIMIC `nativas`), 120 (MIMIC `consistentes`), 91 (Synthea). Las reglas de cada corrida
están en `resultados/<base>_<variante>.json`.

## Resultados

### MIMIC: integridad y coherencia

| Medición | Origen | `nativas` | `consistentes` |
|---|---|---|---|
| FK del catálogo válidas | 51 | 51 | 51 |
| Alta antes del ingreso | 0 | **47** | 0 |
| Muerte fuera de la internación | 0 | **4** | 0 |
| Estadía de UCI fuera de su internación | 0 | **46** | 0 |
| `dod` distinto del día de la muerte | 0 | **7** | 0 |
| Traslado con salida antes de la entrada | 0 | **200** | 0 |
| Emergencia: salida antes del registro | 0 | **27** | 0 |
| `chartevents` fuera de su estadía de UCI (±1 día) | 56 | **249 456** | 56 |
| Pacientes con un único desplazamiento de fechas | — | 0 de 47 (7,7 distintos en promedio) | **47 de 47** |
| Internaciones con la misma duración | — | 0 de 115 | **115 de 115** |
| Edad igual a la original | — | 2 de 47 | 4 de 47 (las que ya eran múltiplo de 10) |
| `subject_id` originales que quedan | — | 0 | 0 |
| `poe_id` con el `subject_id` original adentro | 19 144 | **19 144 de 19 144** | 0 |

Las 56 mediciones de `chartevents` fuera de su estadía ya estaban así en el origen.

### Synthea (`consistentes`)

| Medición | Origen | Resultado |
|---|---|---|
| FK del catálogo válidas | 40 | 40 |
| Encuentro con fin antes del inicio; antes del nacimiento; muerte antes del nacimiento; condición o medicación con fin antes del inicio | 0 | 0 |
| Encuentro más de un día después de la muerte | 8 | 8 (ya estaban en el origen) |
| Pacientes con un único desplazamiento de fechas | — | **85 de 85** |
| Nombre, apellido, SSN o pasaporte igual al original | — | **0 de 85** |
| SSN con formato `ddd-dd-dddd` | 85 | 85 |
| SSN que empiezan con `999` | 85 | **0** (ver hallazgos) |
| Pasaportes con el formato original (`X########X`) | 63 | 63 |
| Licencias con el formato original (`S########`) | 72 | 72 |
| Combinaciones nombre + apellido distintas | — | 82 de 85 |
| Código postal igual al original | — | 20 de 85 (ya terminaban en 00) |
| Ids originales que quedan | — | 0 |

### Reversión

| Variante | Ataque | Resultado |
|---|---|---|
| MIMIC `nativas` | Conocer **un** par (`subject_id` original, seudónimo): da la constante de `pseudo_shift` | **47 de 47** recuperados |
| MIMIC `nativas` | `poe_id` | El id original está a la vista |
| MIMIC `consistentes` | Conocer la sal (filtrada o de alguien de adentro) y recorrer los 10 millones de ids de 8 dígitos | 3,3 s. **21** recuperados sin ambigüedad; los otros **26**, con el original entre 2 o más candidatos |
| MIMIC `consistentes` | Sin la sal | No hay forma conocida (sha256 con sal secreta) |
| Las dos | Conocer una fecha real de un paciente | `consistentes`: da su desplazamiento y revierte **todas** sus fechas. `nativas`: solo esa fila |

**Colisiones del seudónimo de 8 dígitos:** de los 10 millones de ids posibles, 3,68 millones van a parar a un
seudónimo ya usado: el hash conservando el formato no es una biyección. Con 47 pacientes no hubo choques; con los
cientos de miles de pacientes de la MIMIC completa, la probabilidad de que dos compartan seudónimo es prácticamente 1
(paradoja del cumpleaños), y el `UPDATE` fallaría por clave primaria repetida.

### Tiempo

| Corrida | Copia al contenedor | Enmascarar |
|---|---|---|
| MIMIC `nativas` (733 000 filas) | 24 s | **217 s** |
| MIMIC `consistentes` | 25 s | **544 s** |
| Synthea `consistentes` (103 000 filas) | 4 s | **585 s** |

- Imagen emulada (amd64 en Apple Silicon): en un servidor amd64 debería ser bastante más rápido.
- **El costo está en el hash con sal:** `anon.hash` tarda unos 100 µs por llamada en la imagen emulada (20 000
  llamadas en 2,1 s, contra 0,02 s de `pseudo_shift`). Se reescribió la función base de `masc.sql` con `sha256`
  del núcleo: da exactamente lo mismo (2 000 de 2 000 iguales) y tarda unos 31 µs.
- Synthea tarda más que MIMIC con menos filas: tiene más columnas enmascaradas por fila y las fechas son texto que
  hay que convertir.
- Una corrida anterior de MIMIC `consistentes` marcó 6,3 horas porque la Mac se suspendió; se repitió con el equipo
  despierto. Las dos dieron los mismos resultados (reproducible).

## Hallazgos

- **La integridad referencial sale gratis; la coherencia, no.** Las funciones de la extensión mantienen las FK si
  se aplican igual en todas las tablas, pero el ruido de fechas por fila (`dnoise`) destruye el orden de los eventos
  de cada paciente. Para salud, el desplazamiento **por paciente** es imprescindible, y la extensión no lo trae: hubo
  que escribirlo.
- **Identificadores escondidos en otras columnas:** `poe_id` y `emar_id` llevan el `subject_id` en el texto. En la lista
  de referencia figuran como ids de registro («dudoso»), no como ids de paciente: con las reglas por categoría
  habrían quedado sin enmascarar, igual que en `nativas`. El sistema necesita detectar columnas **derivadas** de
  un identificador (por ejemplo, comprobando si contienen sus valores), no solo los identificadores.
- **Seudonimizar conservando el formato tiene un precio:** con un dominio chico (ids de 8 dígitos) hay colisiones
  y se puede recorrer todo el dominio si se filtra la sal. Para la MIMIC completa hace falta una **tabla de
  correspondencia** (biyección guardada aparte) o permitir que el id cambie de formato.
- **El desplazamiento por paciente es reversible para quien conozca una fecha real** de ese paciente. Es el
  compromiso conocido de este método (D: es lo que hace MIMIC con sus propias fechas).
- **`mismo_formato` sobre el SSN de Synthea pierde el prefijo `999`,** que Synthea usa a propósito porque nunca se
  asigna. Un SSN enmascarado podría coincidir con uno real. Hay que conservar los prefijos «no asignables» o
  generar SSN en rangos inválidos.
- **Requisitos de la extensión que el sistema tiene que resolver solo:** FK diferibles, rol no superusuario,
  esquema de confianza para funciones propias, `anon.init()` y permisos sobre sus tablas, y que **la sal solo la
  vea un superusuario** (las funciones que la usan tienen que ser `SECURITY DEFINER`). Ninguno está en un único
  lugar de la documentación; hubo que descubrirlos con errores.
- **Las reglas se generaron desde la lista de columnas sensibles**, sin escribirlas a mano. Es exactamente el puente
  que tiene que hacer el sistema: detección (A) → reglas de anonimización (B).

## Limitaciones

- Subconjuntos chicos (47 y 85 pacientes): la integridad y la coherencia se miden igual, pero el riesgo de
  reidentificación es alto por el tamaño (ver B3m / B3s).
- No se enmascaró el texto libre (`labevents.comments`, `microbiologyevents.comments`): en la demo ya tiene `___`
  donde había datos personales.
- Las elecciones de política (±180 días, edad por década, zip de 3 dígitos, coordenadas con 1 decimal) son una
  propuesta, no una recomendación validada.
- La sal está en el script para poder medir la reversión; en un sistema real va fuera del repo.

## Evidencia

- `resultados/<base>_<variante>.json`: reglas aplicadas, tiempos, coherencia antes y después, FK, consistencia por
  paciente, fugas y reversión. No contiene filas.
- `resultados/log_mimic.txt`, `resultados/log_synthea.txt`: salida de la última corrida.
- Bases enmascaradas en `salud-anon`: `b1m_nativas`, `b1m_consistentes`, `b1s_consistentes`.
