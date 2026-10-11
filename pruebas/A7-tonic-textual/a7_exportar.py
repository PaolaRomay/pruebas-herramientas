#!/usr/bin/env python3
"""Prueba A7: exporta los textos que se le pasan a Tonic Textual.

1. valores/<tabla>.<columna>.txt: los MISMOS valores que analizó A1 (mismas 29 columnas, mismo
   muestreo determinista con semilla `a1`, hasta 200 valores no vacíos), uno por línea. Así el
   resultado de Textual se compara cifra por cifra con el de Presidio.
2. texto_libre.txt: párrafos en español e inglés armados con filas reales de Pagila, más una
   cédula y un celular uruguayos inventados (Pagila no los tiene). Mide lo que Textual hace con
   texto corrido, que es para lo que está pensado.

Uso (desde la raíz del repo, con la base levantada):
    python pruebas/A7-tonic-textual/a7_exportar.py
"""
import csv
from pathlib import Path

import sqlalchemy as sa

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
URL_DB = "postgresql+psycopg2://postgres:postgres@127.0.0.1:55432/pagila"
SEMILLA, N = "a1", 200

# Las mismas columnas que analizó A1 (sensibles, no sensibles y dudosas evaluables).
COLUMNAS = [
    ("customer", "first_name"), ("customer", "last_name"), ("customer", "email"), ("customer", "uuid"),
    ("customer", "address_id"), ("customer", "create_date"), ("address", "address"), ("address", "district"),
    ("address", "postal_code"), ("address", "phone"), ("address", "city_id"), ("city", "city"),
    ("country", "country"), ("staff", "first_name"), ("staff", "last_name"), ("staff", "email"),
    ("staff", "username"), ("staff", "password"), ("staff", "address_id"), ("actor", "first_name"),
    ("actor", "last_name"), ("payment", "amount"), ("payment", "payment_date"), ("rental", "rental_date"),
    ("rental", "return_date"), ("film", "title"), ("film", "description"), ("category", "name"),
    ("language", "name"),
]


def muestra_columna(conn, tabla, columna):
    """Igual que en a1_presidio.py: hasta N valores no vacíos, en orden determinista."""
    q = sa.text(f'select "{columna}"::text from public."{tabla}" where "{columna}" is not null '
                f'and "{columna}"::text <> \'\' order by md5("{columna}"::text || :s) limit :n')
    return [r[0] for r in conn.execute(q, {"s": SEMILLA, "n": N})]


TEXTO_LIBRE = """\
Reclamo recibido el {rental_date}. Lo hizo {first_name} {last_name}, que escribió desde el correo {email} porque le cobraron dos veces el alquiler de «{title}». Vive en {address}, {district}, {city} ({country}), código postal {postal_code}, y dejó como teléfono {phone}.

Nota interna de la tienda: el empleado {s_first} {s_last} (usuario {username}, correo {s_email}) atendió el reclamo y devolvió {amount} dólares. Para validar la identidad, presentó la cédula 4.187.392-6 y dio un celular alternativo: 099 482 317.

Customer support log: {first_name2} {last_name2} called on {payment_date} asking to update the account linked to {email2}. The new mailing address is {address2}, {city2}, {country2}. Customer ID in the system: {uuid2}.

Comentario libre del cliente: "Quiero que me devuelvan la plata. Me llamo {first_name2} {last_name2} y mi número es {phone2}."
"""


def main():
    eng = sa.create_engine(URL_DB)
    salida = AQUI / "entrada" / "valores"
    salida.mkdir(parents=True, exist_ok=True)
    indice, palabras = [], 0
    with eng.connect() as conn:
        for tabla, columna in COLUMNAS:
            vals = [v.replace("\n", " ") for v in muestra_columna(conn, tabla, columna)]
            ruta = salida / f"{tabla}.{columna}.txt"
            ruta.write_text("\n".join(vals) + "\n", encoding="utf-8")
            n_pal = sum(len(v.split()) for v in vals)
            palabras += n_pal
            indice.append({"archivo": ruta.name, "tabla": tabla, "columna": columna, "valores": len(vals),
                           "palabras": n_pal})

        q = sa.text("""
            select c.first_name, c.last_name, c.email, a.address, a.district, ci.city, co.country,
                   a.postal_code, a.phone, r.rental_date::date, f.title
            from customer c join address a using (address_id) join city ci using (city_id)
            join country co using (country_id) join rental r using (customer_id)
            join inventory i using (inventory_id) join film f using (film_id)
            order by md5(c.customer_id::text || :s), r.rental_id limit 1""")
        uno = dict(conn.execute(q, {"s": SEMILLA}).mappings().one())
        q2 = sa.text("""
            select c.first_name first_name2, c.last_name last_name2, c.email email2, c.uuid uuid2,
                   a.address address2, ci.city city2, co.country country2, a.phone phone2,
                   p.payment_date::date payment_date, p.amount
            from customer c join address a using (address_id) join city ci using (city_id)
            join country co using (country_id) join payment p using (customer_id)
            order by md5(c.customer_id::text || :s || '2'), p.payment_id limit 1""")
        dos = dict(conn.execute(q2, {"s": SEMILLA}).mappings().one())
        q3 = sa.text("""select first_name s_first, last_name s_last, username, email s_email
                        from staff order by md5(staff_id::text || :s) limit 1""")
        tres = dict(conn.execute(q3, {"s": SEMILLA}).mappings().one())
    texto = TEXTO_LIBRE.format(**uno, **dos, **tres)
    (AQUI / "entrada" / "texto_libre.txt").write_text(texto, encoding="utf-8")
    palabras += len(texto.split())

    with open(AQUI / "entrada" / "indice.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(indice[0]))
        w.writeheader()
        w.writerows(indice)
    print(f"{len(indice)} archivos de valores + texto_libre.txt en {AQUI / 'entrada'}; "
          f"unas {palabras:,} palabras en total (el cupo gratis de Textual es 100.000).")


if __name__ == "__main__":
    main()
