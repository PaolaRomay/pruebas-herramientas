-- Filas por tabla lógica (las particiones de payment se suman en payment).
select coalesce(p.relname, c.relname) as tabla, sum((xpath('/row/n/text()', query_to_xml(format('select count(*) as n from %I', c.relname), false, true, '')))[1]::text::bigint) as filas
from pg_class c join pg_namespace n on n.oid=c.relnamespace
left join pg_inherits i on i.inhrelid=c.oid left join pg_class p on p.oid=i.inhparent
where n.nspname='public' and c.relkind='r' group by 1 order by 1;
