# C2 — Tonic Structural (Extraer subconjuntos)

Requiere el trial de Structural y Pagila en Neon ([neon.md](../_herramientas/neon.md)).

1. En el workspace `pagila_origen` → `pagila_destino`, configurar el subsetting con ancla `customer` y WHERE `hashtext('c1' || customer_id::text) % 10 = 0` (98 clientes), generadores en passthrough. Capturar la configuración en `evidencia/c2_subsetting.png`.
2. Generar. Anotar el tiempo del job y capturar el log.
3. Traer el destino y medir:

   ```bash
   python scripts/traer_neon.py --base c2 --salida pruebas/C2-tonic-structural/resultados
   ```

   `conteos.csv` da el % de cada tabla contra Pagila; `traer_neon.md` da el total y las violaciones.
4. Chequeos que `integridad.py` no cubre (en `docker exec -i pagila-db psql -U postgres -d c2`):

   ```sql
   -- ciclo store ↔ staff: tiendas cuyo gerente no quedó en el subconjunto
   select count(*) from store s where not exists (select 1 from staff t where t.staff_id = s.manager_staff_id);
   -- payment sobre la tabla padre (en Pagila las FK están declaradas solo en 6 de las 55 particiones)
   select count(*) filter (where not exists (select 1 from rental r where r.rental_id = p.rental_id)) as sin_rental,
          count(*) filter (where not exists (select 1 from customer c where c.customer_id = p.customer_id)) as sin_cliente,
          count(*) filter (where not exists (select 1 from staff s where s.staff_id = p.staff_id)) as sin_empleado
   from payment p;
   ```

   El mismo chequeo, más completo, lo hace E3: `python pruebas/E3-chequeos-propios/evaluar_bd.py evaluar --candidata c2 --tipo subconjunto --bloques integridad`.
5. Completar la ficha.
