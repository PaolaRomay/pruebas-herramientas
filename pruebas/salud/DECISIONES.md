# Decisiones tomadas sin consultar (pruebas sobre MIMIC y Synthea)

**Quién / cuándo:** Claude Code, a pedido de Jero («cualquier decisión que tomes que creas que me tendrías que
consultar, dejala anotada y cualquier cosa la cambiamos»), 2026-11-08 a 2026-11-12.

Cada decisión dice qué se hizo, por qué y qué cambia si se decide otra cosa. Las marcadas con **⚠** son las que más
conviene revisar.

## Generales

1. **⚠ `ESTADO.md` no se tocó.** Lo mantienen otras sesiones en paralelo. Las pruebas sobre las bases de salud
   (carpeta `pruebas/salud/`) no figuran ahí. *Si querés que figuren:* agregar una sección «Pruebas sobre MIMIC y
   Synthea» con un enlace a cada ficha.
2. **Los planes (`docs/plan-pruebas-mimic.md`, `docs/plan-validacion.md`) quedaron fuera de los commits**, como
   pediste. Tienen anotado el avance de cada etapa.
3. **Todo se hizo sobre la demo de MIMIC (100 pacientes)**, sin credenciales. Ninguna prueba usó la MIMIC completa.
   A7m (texto libre de MIMIC-IV-Note) no se hizo porque requiere credenciales.
4. **Ninguna fila de MIMIC ni de Synthea en el repo:** los datos, Parquet y registros por paciente quedan en
   `salidas_grandes/` (en `.gitignore`) o en las bases de Docker. Al repo van métricas, conteos y nombres de columnas.

## Etapa 2 · Lista de referencia

5. **⚠ `patients.anchor_age`, `anchor_year` y `anchor_year_group` (MIMIC) quedaron «dudoso»** (regla de HIPAA para
   edades: solo las mayores de 89 son identificador). Pregunta abierta desde la etapa 2: por coherencia con DEC-4
   (demográficos = sí), la edad podría pasar a «sí». Como «dudoso» no cuenta en las métricas de A; si cambia, hay
   que volver a congelar la lista y recalcular con `comparar_salud.py`. En B1 y B3 la edad se trató como
   cuasi-identificador igual.

## Etapa 4 · Detección

6. **⚠ `gliner2` 2.1.0 y `transformers` 5.22.2 se instalaron en el `.venv` del repo, pero no se agregaron a
   `requirements.txt`** (es de la base común, de Paola). No cambiaron ninguna versión existente. *Para acordar:*
   agregarlos o dejar GLiNER2 en un requirements aparte.
7. LLM local: temperatura 0, sin razonamiento, política escrita a partir de las fuentes de la lista (no de las
   decisiones DEC-1 a DEC-6). Variante ofuscada para medir contaminación.
8. A6: se combinaron salidas guardadas (no se volvió a correr Presidio ni el LLM).

## Etapa 5 · Subconjunto

9. **Porcentajes:** en la demo, 10 % y 50 % de los pacientes (el plan decía 1 % y 10 % de la completa; en la demo el
   1 % es un paciente). Synthea: 1 % y 10 %.
10. **Pacientes de control:** `hashtext('control' || id) % 5 = 0` (alrededor del 20 %), separados antes de extraer.
11. **Catálogos de MIMIC copiados enteros** (CIE, HCPCS, ítems de laboratorio y UCI): 284 000 filas.
12. **Bases de trabajo para B y D:** `mimic_c1_50` (47 pacientes) y `synthea_c1_10` (85).

## Etapa 6 · Anonimización

13. **⚠ Política de enmascaramiento (propuesta, no validada):** fechas ±180 días por paciente, edad por década, zip a
    3 dígitos, coordenadas con 1 decimal, condado y FIPS en nulo, ingresos con ruido del 10 %. Son parámetros de
    `b1_anon_salud.py`.
14. **La sal está en el script** para poder medir la reversión. En un sistema real, fuera del repo.
15. **Contenedor `salud-anon` propio** (puerto 55434), sin tocar el servicio `anon` del `docker-compose.yml`.
16. **Funciones propias en `masc.sql`** para lo que la extensión no trae (desplazamiento por paciente, ids
    compuestos, mismo formato). La función de hash se reescribió para que sea más rápida, con el mismo resultado.

## Etapa 7 · Síntesis

17. **⚠ Escalones de MOSTLY:** el plan pedía entrenar con 1 000, 5 000 y 10 000 pacientes; la demo tiene 100. Se
    entrenó con 47 (MIMIC) y se **generaron** 47, 1 000, 5 000 y 10 000. La escala del entrenamiento se midió con
    Synthea: 85 y 925 pacientes (770 000 filas).
18. **Tablas sintetizadas:** MIMIC 5 (`patients`, `admissions`, `diagnoses_icd`, `icustays`, `labevents`), Synthea 4
    (`patients`, `encounters`, `conditions`, `observations`). `observations` sin encuentro (3,7 %) quedó afuera.
19. **MOSTLY y SDV con valores por defecto**, sin reglas ni restricciones propias. **Pendiente:** probar las
    restricciones de SDV (*constraints*) para `alta >= ingreso`.
20. **SDV:** los nulos de las categóricas se reemplazan por una marca para esquivar un error de RDT 1.19.0.

## Etapa 8 · Validación

21. **⚠ SyntheRela en un entorno aparte** (`../herramientas-externas/venv-syntherela`): fija scikit-learn 1.3.1 y
    el `.venv` del repo tiene 1.9.1. Detección solo sobre las tablas padre y MMD sobre muestras de 5 000 filas, por
    tiempo.
22. **E3m / E3s es un evaluador nuevo** (`e3_salud.py`), no una modificación de `evaluar_bd.py`. Registro «paciente»,
    secreto = diagnóstico, controles = los de C1 (16 en MIMIC: Anonymeter queda poco concluyente).
23. **Normalización:** se quitan los espacios de los textos (los códigos CIE de MIMIC son `char(7)`).

## Etapa 9 · F y G

24. **F1:** 17 consultas (MIMIC) y 14 (Synthea) elegidas por nosotros; umbrales de «se conserva» por convención (20 %
    de error, 5 de 10 en rankings, variación total 0,2).
25. **F2 (relaciones):** la verdad de MIMIC son las 25 relaciones encontradas por nombre de columna en la etapa 1; en
    Synthea, las 40 FK del cargador.
26. **⚠ G1 (orquestación):** el caso 3 pide «todos los pacientes con sepsis» y no el 10 %, porque en la demo son 17.
    Temperatura 0,7 para medir variabilidad. Los casos 1, 2 y 4 no se ejecutaron de nuevo: se comparan con A2m,
    B1m y D2m.

## Mediciones con alguna salvedad

27. Tiempos de B1m `consistentes` y de A2m (dos corridas): la Mac se suspendió; se repitieron con el equipo
    despierto. Las clasificaciones y los resultados no cambiaron.
28. Tres corridas de SDV compartieron la máquina con F2 (el LLM usa la GPU): sus tiempos pueden estar algo inflados.
