select c.relname, (xpath('/row/h/text()', query_to_xml(format('select md5(string_agg(t::text, %L order by t::text)) h from public.%I t', E'\n', c.relname), false, true, '')))[1]::text
from pg_class c where c.relnamespace='public'::regnamespace and c.relkind in ('r','p') and not c.relispartition order by 1;
