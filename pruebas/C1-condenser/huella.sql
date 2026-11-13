-- Huella de contenido: md5 por tabla de todas las filas ordenadas (para comparar corridas).
select c.relname, md5(coalesce((xpath('/row/h/text()', query_to_xml(format(
  'select md5(string_agg(t::text, %L order by t::text)) as h from %I t', '|', c.relname), false, true, '')))[1]::text, ''))
from pg_class c join pg_namespace n on n.oid=c.relnamespace
where n.nspname='public' and c.relkind='r' order by 1;
