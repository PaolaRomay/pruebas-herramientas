select c.relname, (xpath('/row/n/text()', query_to_xml(format('select count(*) n from public.%I', c.relname), false, true, '')))[1]::text::bigint
from pg_class c where c.relnamespace='public'::regnamespace and c.relkind in ('r','p') and not c.relispartition order by 1;
select 'particiones_payment', count(*) from pg_inherits where inhparent='public.payment'::regclass;
select 'restricciones', contype, count(*) from pg_constraint where connamespace='public'::regnamespace group by contype order by contype;
select 'vistas', count(*) from pg_views where schemaname='public';
select 'version', version();
