#!/usr/bin/env python3
"""Prueba D6, experimento 2: ¿se le pueden pedir 3 niveles (customer -> rental -> payment) a REaLTabFormer
de forma nativa? Se intenta de verdad, con una muestra mínima (pocos clientes, 1 época, CPU), y se
registra qué pasa con cada intento en resultados/d6_exp2_tres_niveles.json:

  A  join_on con dos claves: payment hijo de rental y de customer a la vez (join_on=[...]).
  B  dos tablas padre: in_df=[customer, rental].
  C  saltear el nivel del medio: payment como hija directa de customer (join_on=customer_id).
     Entrena (son 2 niveles), pero rental_id queda como un número más: se mide si los pagos generados
     apuntan a alquileres de su mismo cliente.

Uso (después de `d6_realtabformer.py exportar`):
    .venv-rtf/bin/python pruebas/D6-realtabformer/d6_tres_niveles.py [--clientes 5]
"""
import argparse
import json
import os
import time
import traceback
import warnings
from pathlib import Path

AQUI = Path(__file__).resolve().parent
ENTRADA = AQUI / "salidas_grandes" / "entrada"
SALIDA = AQUI / "resultados" / "d6_exp2_tres_niveles.json"
FECHAS = {("customer", "create_date"), ("rental", "rental_date"), ("rental", "return_date"),
          ("payment", "payment_date")}


def intento(nombre, fn):
    t0 = time.perf_counter()
    try:
        detalle = fn()
        r = {"resultado": "corrió", **(detalle or {})}
    except Exception as e:
        tb = traceback.extract_tb(e.__traceback__)
        donde = next((f"{Path(f.filename).name}:{f.lineno}" for f in reversed(tb) if "realtabformer" in f.filename),
                     f"{Path(tb[-1].filename).name}:{tb[-1].lineno}")
        r = {"resultado": "falló", "error": f"{type(e).__name__}: {str(e)[:300]}", "donde": donde}
    r["segundos"] = round(time.perf_counter() - t0, 1)
    print(f"[{nombre}] {r['resultado']}: {r.get('error', '')}", flush=True)
    return r


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--clientes", type=int, default=5)
    a = ap.parse_args()
    warnings.filterwarnings("ignore")
    import pandas as pd
    from realtabformer import REaLTabFormer

    d = {t: pd.read_parquet(ENTRADA / f"{t}.parquet") for t in ("customer", "rental", "payment")}
    for t, c in FECHAS:   # mismos ajustes que d6_realtabformer.py
        d[t][c] = d[t][c].astype("datetime64[ns]").dt.floor("s")
    ids = d["customer"]["customer_id"].head(a.clientes)
    cus = d["customer"][d["customer"]["customer_id"].isin(ids)]
    ren = d["rental"][d["rental"]["customer_id"].isin(ids)]
    pay = d["payment"][d["payment"]["rental_id"].isin(ren["rental_id"])]
    os.chdir(AQUI / "salidas_grandes")
    kw = dict(epochs=1, batch_size=1, output_max_length=None, train_size=1)

    def eager(m):
        for c in (m.relational_config, m.relational_config.encoder, m.relational_config.decoder):
            c._attn_implementation = "eager"
        return m

    res = {"muestra": {"clientes": len(cus), "alquileres": len(ren), "pagos": len(pay)}, "intentos": {}}

    def a_dos_claves():
        m = eager(REaLTabFormer(model_type="relational", **kw))
        m.fit(df=pay.drop(columns=["payment_id"]), in_df=ren, join_on=["customer_id", "rental_id"], device="cpu")
    res["intentos"]["A join_on con dos claves"] = intento("A", a_dos_claves)

    def b_dos_padres():
        m = eager(REaLTabFormer(model_type="relational", **kw))
        m.fit(df=pay.drop(columns=["payment_id"]), in_df=[cus, ren], join_on="customer_id", device="cpu")
    res["intentos"]["B in_df con dos tablas padre"] = intento("B", b_dos_padres)

    def c_saltear_rental():
        m = eager(REaLTabFormer(model_type="relational", **kw))
        m.fit(df=pay.drop(columns=["payment_id"]), in_df=cus, join_on="customer_id", device="cpu")
        gen = m.sample(input_unique_ids=cus["customer_id"], input_df=cus.drop(columns=["customer_id"]),
                       gen_batch=8, device="cpu")
        if "customer_id" not in gen.columns:
            gen.index.name = "customer_id"
            gen = gen.reset_index()
        propio = ren.set_index("rental_id")["customer_id"]
        dueno = gen["rental_id"].map(propio)
        return {"pagos_generados": len(gen),
                "rental_id_inexistente": int(dueno.isna().sum()),
                "rental_id_de_otro_cliente": int((dueno.notna() & (dueno != gen["customer_id"])).sum()),
                "rental_id_de_su_cliente": int((dueno == gen["customer_id"]).sum()),
                "nota": "entrena porque son 2 niveles; rental_id es un número más, no una FK"}
    res["intentos"]["C payment hija directa de customer"] = intento("C", c_saltear_rental)

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
