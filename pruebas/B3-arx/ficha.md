# B3 — ARX — Anonimizar (k-anonimato)

**Quién / cuándo:** Jero (corrida por Claude Code a pedido de Jero), 2026-10-14.
**Fuente de cada dato:** D = documentación, P = prueba propia. Salvo donde dice D, todo es P. «Código» = leído en la API de la librería (`javap`).

[← Estado](../ESTADO.md) · [Plan](../../docs/plan-de-pruebas.md) · [E3](../E3-chequeos-propios/ficha.md)

## En pocas palabras

- ARX anonimiza **en el lugar**: las mismas 799 personas, con los mismos ids y claves. No genera datos nuevos: **tapa los identificadores con `*` y vuelve menos precisos** los cuasi-identificadores (código postal, distrito, ciudad, país, fecha de alta) hasta que cada persona se confunda con al menos *k*−1 más.
- **Privacidad muy alta y estructura intacta:** con todas las variantes, el riesgo de Anonymeter da ≈ 0 (de 0 a 0,019), 0 % de copias y **0 violaciones** de las 132 restricciones de Pagila. Es rápido: 0,03 s de cómputo.
- **Pero para testing deja poco.** En una base de 799 personas, con k = 5 ARX oculta ciudad, país y distrito en todas las filas, deja un solo dígito del código postal y la fecha en el año. Los nombres, emails, direcciones y teléfonos quedan como `*`: no son datos falsos con formato, son vacíos.
- **Trabaja con una sola tabla.** Hubo que aplanar `customer + address + city + country` y después volver a escribir en la base con código propio. Ahí aparecen problemas que ARX no ve: la base no puede guardar «país sí, ciudad no», las fechas no aceptan `2022` y 441 de las 799 direcciones también son de empleados o tiendas, que quedan modificadas.

## Entorno

- Equipo: Mac M5 Pro (`sysctl`: «Apple M5»), 16 GB de RAM, macOS 26.6.2.
- Herramienta: **ARX 3.9.2**, la librería `libarx-3.9.2.jar` (release del 2025-09-21 en GitHub, licencia **Apache 2.0**). sha256 del jar: `18040108e95ca7955d806bf32354b20601d664495653b8ee169d249f43f58d44`.
- **Java en Docker:** la Mac no tiene Java instalado. Se compiló y corrió con la imagen `eclipse-temurin:21-jdk`, sin instalar nada en la Mac. No se probó la interfaz gráfica de ARX (`arx-3.9.2-osx-64.jar`, 56 MB), que sí necesita Java instalado.
- Datos: registro «persona» de `e3_entrenamiento` (Pagila sin los 200 clientes de control de E3): **799 personas**, una fila por cliente con `customer` + `address` + `city` + `country`. Valores distintos: 317 distritos, 795 códigos postales, 479 ciudades, 100 países y 350 fechas de alta.
- Scripts (esta carpeta):
  - `ArxB3.java`: configura ARX y lo corre para una variante.
  - `b3_arx.py`, con cuatro pasos:
    - `exportar`: el registro «persona» y las jerarquías;
    - `anonimizar`: ARX en Docker;
    - `aplicar`: vuelta a una copia de la base;
    - `resumir`.
  ```bash
  .venv/bin/python pruebas/B3-arx/b3_arx.py exportar
  .venv/bin/python pruebas/B3-arx/b3_arx.py anonimizar
  .venv/bin/python pruebas/B3-arx/b3_arx.py aplicar
  .venv/bin/python pruebas/E3-chequeos-propios/evaluar_bd.py evaluar --candidata b3_k5 --tipo anonimizada --entrenada-con e3_entrenamiento --tablas customer,address,city,country   # una por variante
  .venv/bin/python pruebas/B3-arx/b3_arx.py resumir
  ```

## Qué es ARX y cómo se configuró

**Qué es (D):** una herramienta de anonimización de la Universidad Técnica de Múnich, con interfaz gráfica y una API en Java. Implementa modelos de privacidad formales (k-anonimato, l-diversidad, t-cercanía, privacidad diferencial, entre otros) mediante **generalización** (volver un valor menos preciso), **supresión** (borrar filas enteras que obligarían a generalizar todo) y búsqueda de la transformación que pierde menos información.

**Lo que la API impone (código):**
- `Data.create(...)` recibe **una tabla**, de un CSV o de una fuente de datos. No hay forma de declarar relaciones entre tablas.
- Cada columna se declara como:
  - **identificador**: se reemplaza por `*`;
  - **cuasi-identificador**: necesita una jerarquía;
  - **sensible**;
  - **insensible**: queda igual.
- **Una columna sin declarar se trata como identificador y se borra.** En la primera corrida eso borró `customer_id`, `store_id`, `activebool` y `active` (`evidencia/b3_k5_sin_declarar_insensibles_muestra.csv`). Sin `customer_id`, el resultado no se puede volver a ubicar en la base.

**Configuración usada:**

| Columna | Tipo en ARX | Jerarquía (niveles) |
|---|---|---|
| `first_name`, `last_name`, `email`, `address`, `phone` | identificador | — (pasa a `*`) |
| `postal_code` | cuasi-identificador | `35200` → `3520*` → `352**` → `35***` → `3****` → `*` |
| `district` | cuasi-identificador | distrito → `*` |
| `city` | cuasi-identificador | ciudad → su país → `*` |
| `country` | cuasi-identificador | país → `*` |
| `create_date` | cuasi-identificador | `2022-05-20` → `2022-05` → `2022` → `*` |
| `customer_id`, `store_id`, `activebool`, `active` | insensible | — (quedan igual) |

- **Las jerarquías las arma uno.** ARX no las deduce: se generaron con `b3_arx.py exportar` a partir de los datos. Para la ciudad se usó la tabla `city` (ciudad → país). Para el país no hay un nivel intermedio (continente) porque Pagila no lo tiene.
- Modelo de privacidad: **k-anonimato**. Métrica de calidad: la de ARX por defecto (`Loss`).
- `address2` quedó afuera, porque es nula en toda la base.

**Variantes:**

| Variante | k | Supresión máxima | Cuasi-identificadores |
|---|---|---|---|
| `k2` | 2 | 10 % | los 5 |
| `k5` | 5 | 10 % | los 5 |
| `k10` | 10 | 10 % | los 5 |
| `k5_sin_supresion` | 5 | 0 % | los 5 |
| `k5_ciudad_pais_fecha` | 5 | 10 % | solo ciudad, país y fecha (distrito y código postal pasan a identificadores) |

**Vuelta a la base (`aplicar`, código propio):** se crea una copia de `e3_entrenamiento` (`b3_<variante>`) **con todas las restricciones** y se aplica la anonimización con `UPDATE` sobre `customer` y `address`. Para lo que el esquema no puede representar tal cual:
- **Fecha generalizada:** `create_date` es de tipo `date` y NOT NULL. `2022-05` pasa a `2022-05-01`, `2022` a `2022-01-01` y `*` a `2022-01-01`.
- **Ciudad o país ocultos:** `address` guarda la ciudad por FK, y el país sale de la ciudad. Se insertan filas marcador: una ciudad `*` por país y un país `*` con su ciudad `*`. Cuando ciudad o país es `*`, se usa la ciudad `*` del país `*`, para no destapar el país a través de la ciudad.

## Qué se midió y resultado

Métricas mínimas de «Anonimizar»: si las FK siguen resolviendo, si se conserva la relación entre columnas (ciudad ↔ código postal), si es reversible y el tiempo. Además, privacidad y calidad con E3. Resumen completo en [`resultados/b3_resumen.md`](resultados/b3_resumen.md).

### Lo que hizo ARX

| Variante | Filas suprimidas | Clases (mín. / prom.) | Riesgo máx. antes → después | Riesgo prom. antes → después | Qué quedó |
|---|---|---|---|---|---|
| `k2` | 43 | 61 (2 / 12,4) | 1,00 → 0,50 | 1,000 → 0,081 | ciudad → **país visible**, distrito y CP ocultos, fecha → año |
| `k5` | 46 | 36 (5 / 20,9) | 1,00 → 0,20 | 1,000 → 0,048 | ciudad, país y distrito ocultos, **CP: 1 dígito**, fecha → año |
| `k10` | 5 | 11 (28 / 72,2) | 1,00 → 0,04 | 1,000 → 0,014 | ciudad, país y distrito ocultos, CP: 1 dígito, **fecha oculta** |
| `k5_sin_supresion` | 0 | 5 (28 / 159,8) | 1,00 → 0,04 | 1,000 → 0,006 | todo oculto salvo la fecha → año |
| `k5_ciudad_pais_fecha` | 37 | 42 (5 / 18,1) | 1,00 → 0,20 | 0,961 → 0,055 | ciudad y país ocultos, **fecha → mes** |

- El riesgo es el del modelo «fiscal» de ARX: el atacante sabe que la persona está en los datos, y el riesgo de una fila es 1 / el tamaño de su grupo.
  - **Antes**, el riesgo es 1 para todos: cada persona es única con sus 5 cuasi-identificadores.
  - Con 799 filas y datos tan dispersos (795 códigos postales distintos), ARX necesita generalizar mucho para llegar a k = 5.
- **La solución «óptima» de ARX no es la útil para testing.** Con solo 3 cuasi-identificadores, la métrica `Loss` prefirió ocultar toda la geografía y conservar el mes, en vez de conservar el país. Según la documentación (D), se pueden dar pesos por columna para orientar la elección; no se probó.
- **Supresión contra generalización:** sin supresión (k = 5, 0 %), todos los grupos quedan grandes (mínimo 28) a costa de ocultar todo; con 10 % de supresión se borran 46 filas y el resto conserva algo más.

### Tiempo

- **ARX: 0,02 a 0,03 s** por variante (cómputo de la librería), y **0,6 a 0,9 s** contando el arranque del contenedor y de Java.
- Vuelta a la base: 0,5 a 0,8 s por variante.
- La evaluación con E3 tarda más que todo eso (unos 3 min, casi todo de Anonymeter).

### ¿Las FK siguen resolviendo?

**Sí: 0 violaciones** en las 36 FK, 15 PK, 5 UNIQUE, 75 NOT NULL y el CHECK de Pagila, más las 4 relaciones que agrega E3, en las cinco variantes. Las 799 actualizaciones entraron sin error con todas las restricciones puestas.

Es así porque ARX no toca las claves: `customer_id`, `address_id` y `store_id` quedan iguales. Los únicos cambios de FK los hizo nuestro adaptador (`address.city_id` → ciudad marcador), y apuntan a filas que existen.

### ¿Se conserva la relación ciudad ↔ código postal?

**No, en ninguna variante.** Personas con ciudad y código postal intactos: **0 de 799** en las cinco. ARX generaliza cada cuasi-identificador por separado y, con k ≥ 2, en estos datos no deja ningún código postal completo.

| Variante | Ciudad intacta / subió a país / oculta | Fecha día / mes / año / oculta |
|---|---|---|
| `k2` | 0 / 756 / 43 | 0 / 0 / 756 / 43 |
| `k5` | 0 / 0 / 799 | 0 / 0 / 753 / 46 |
| `k10` | 0 / 0 / 799 | 0 / 0 / 0 / 799 |
| `k5_sin_supresion` | 0 / 0 / 799 | 0 / 0 / 799 / 0 |
| `k5_ciudad_pais_fecha` | 0 / 0 / 799 | 0 / 762 / 0 / 37 |

### ¿Es reversible?

**No.** La generalización pierde información (de `2022` no se puede volver a `2022-05-20`), y ARX no guarda una tabla de correspondencias. Lo único que queda para relacionar con el original es `customer_id`, que es la misma clave. Para un ambiente de testing eso es razonable; para publicar datos, no.

### Cómo queda un cliente (variante `k5`)

| | Antes (`e3_entrenamiento`) | Después (`b3_k5`) |
|---|---|---|
| Cliente 1 | MARY · SMITH · MARY.SMITH@sakilacustomer.org · 2022-05-20 · 1913 Hanoi Way · 28303384290 · Nagasaki · 35200 · Sasebo · Japan | `*` · `*` · `*` · 2022-01-01 · `*` · `*` · `*` · `3****` · `*` · `*` |
| Empleado 1 (comparte dirección con un cliente) | Warner · 42 Brindisi Place · Yerevan · Yerevan | Warner · `*` · `*` · `*` |

### Privacidad y calidad (E3, contra los 200 clientes de control)

| Variante | Calidad / diagnóstico | Column Shapes | Singling out (univ. / multiv.) | Linkability | Inference (4 secretos) | Copias exactas | Índice de memorización |
|---|---|---|---|---|---|---|---|
| `k2` | 0,869 / 0,974 | 0,861 | 0,000 / 0,000 | 0,000 | 0,000 | 0 % | −1,01 |
| `k5` | 0,868 / 0,972 | 0,851 | 0,000 / 0,010 | 0,000 | 0,000 | 0 % | −2,63 |
| `k10` | 0,762 / 0,963 | 0,800 | 0,000 / 0,000 | 0,000 | 0,000 | 0 % | −3,91 |
| `k5_sin_supresion` | 0,871 / 0,974 | 0,861 | 0,000 / 0,015 | 0,000 | 0,000 | 0 % | −2,47 |
| `k5_ciudad_pais_fecha` | 0,903 / 0,997 | 0,918 | 0,019 / 0,015 | 0,000 | 0,000 | 0 % | −1,48 |

- **Privacidad:** riesgo ≈ 0 en todo. En la mayoría de los ataques, Anonymeter avisa que el ataque no supera al azar (no concluyente), porque casi no quedan valores para atacar. El índice de memorización es negativo: cada fila anonimizada está **más lejos** de su persona real que las personas del control.
  - Contraste con la validación de E3: una base anonimizada «1 a 1» (solo reemplazando valores) dio un índice de 0,87. Esa es la diferencia de la generalización.
- **La calidad de E3 es engañosa acá.** SDMetrics no compara el texto de muchos valores distintos (nombres, emails, direcciones), que es justamente lo que ARX borró. Además, casi todas las columnas numéricas (ids, `store_id`, `active`) quedaron sin tocar. Un 0,87 no significa que la base sirva para testing.

## Esfuerzo

- Unas 1,5 h hasta la primera corrida completa (hecha por Claude Code). Problemas encontrados:
  - **No hay librería de Python:** la API es Java y la Mac no tiene Java. Se resolvió con un contenedor de Java.
  - **Por defecto borra las columnas sin declarar,** incluida la clave (ver arriba).
  - **Las jerarquías se arman a mano** (acá, con un script), una por cuasi-identificador. Cada valor necesita un único padre: una ciudad con el mismo nombre en dos países no se puede subir a «su» país. En Pagila hay un caso, pero ninguno entre las ciudades de clientes.
  - **Volver a la base es trabajo propio:** el resultado es un CSV de una tabla. Hubo que escribir el adaptador para fechas, ciudades y países, y decidir qué hacer con lo que el esquema no puede guardar.

## Hallazgos

- Limitaciones vistas en la práctica:
  - **Una tabla por vez y sin relaciones.** Hay que aplanar y después volver a escribir. El esquema real no siempre puede representar el resultado:
    - un país visible con la ciudad oculta no entra, porque el país sale de la ciudad por FK;
    - una fecha generalizada no entra en una columna `date`.
  - **Efectos colaterales en datos compartidos:** 441 de las 799 direcciones de clientes también son de empleados o tiendas (particularidad de Pagila v4). Anonimizar la persona cambió esas direcciones: el empleado 1 quedó con dirección `*`. ARX no puede saberlo porque no ve las otras tablas.
  - **No genera datos falsos:** los identificadores quedan como `*`. Para testing, un email `*` o un teléfono `*` rompe validaciones de formato. Habría que combinarlo con un generador de valores falsos (Faker, PostgreSQL Anonymizer) para los identificadores y usar ARX solo para los cuasi-identificadores.
  - **Con pocos datos y muy dispersos, el k-anonimato destruye la utilidad:** con 799 personas y 795 códigos postales distintos, k = 5 deja la geografía en `*`. En una base productiva más grande, la pérdida sería menor (no se midió).
  - **La configuración define todo:** qué columnas son cuasi-identificadores, las jerarquías y la métrica cambian mucho el resultado, y el «óptimo» de ARX no coincide con lo útil para testing.
  - **Es irreversible** (puede ser una ventaja).
- Lo que hizo bien:
  - **Estructura intacta:** 0 violaciones con todas las restricciones, mismas claves y mismo volumen.
  - **Privacidad medible y garantizada por construcción** (k-anonimato), con riesgo ≈ 0 en E3.
  - **Muy rápido:** menos de 1 s.
  - **Gratis y Apache 2.0.**
  - Informa el riesgo antes y después.
- Requisitos que surgen para el sistema:
  - **Combinar técnicas por tipo de columna:**
    - identificadores directos → valores falsos con formato (Faker / PostgreSQL Anonymizer);
    - cuasi-identificadores → generalización con un k objetivo (ARX), solo si el volumen lo permite;
    - claves → intactas.
  - **El sistema tiene que conocer el esquema que ARX no ve:** filas compartidas entre tablas, FK que determinan otros valores (ciudad → país) y tipos de columna (fechas).
  - **Elegir los cuasi-identificadores y las jerarquías es una decisión de privacidad y utilidad.** Un orquestador (G) puede proponerlos, pero hay que validarlos con E3.
  - **Medir la utilidad para testing con algo más que SDMetrics** (función F): formatos válidos y que las consultas típicas sigan devolviendo filas.

## Evidencia

- [`resultados/b3_resumen.md`](resultados/b3_resumen.md): las tres tablas (ARX, vuelta a la base, E3). Lo genera el script.
- `resultados/b3_arx_<variante>.json`: métricas de ARX por variante (niveles, supresión, clases, riesgo antes y después, tiempos). `resultados/b3_tiempos.json`: exportación y vuelta a la base.
- [E3 sobre `b3_k5`](../E3-chequeos-propios/resultados/b3_k5/e3_resumen.md), y las demás variantes en `pruebas/E3-chequeos-propios/resultados/b3_*`.
- `evidencia/b3_anonimizar.log` (salida de ARX), `b3_anonimizar_sin_insensibles.log` y `b3_k5_sin_declarar_insensibles_muestra.csv` (la corrida que borró `customer_id`), y `b3_e3_<variante>.log`.
- No se suben (`salidas_grandes/`): el jar de ARX (36 MB), `persona.csv`, las jerarquías (contienen todos los valores de Pagila) y las tablas anonimizadas.

## Opcional

- ¿Misma semilla, mismo resultado? ARX es **determinista**: busca la transformación óptima en un espacio finito, sin azar. Las tres corridas de `anonimizar` de esta prueba (la que borró `customer_id`, la corregida y la que agregó la variante de 3 cuasi-identificadores) dieron exactamente los mismos niveles para las variantes repetidas.
