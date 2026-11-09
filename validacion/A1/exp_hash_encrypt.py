"""Validación A1 (observación para B2): ¿hash y encrypt de presidio-anonymizer dan lo mismo para el mismo valor?"""
from importlib.metadata import version
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
t = "Mary Smith wrote to mary@example.com. Later, Mary Smith wrote again."
res = AnalyzerEngine().analyze(text=t, language="en")
an = AnonymizerEngine()
print("presidio-anonymizer", version("presidio-anonymizer"))
for nombre, op in {"hash": OperatorConfig("hash", {"hash_type": "sha256"}),
                   "encrypt": OperatorConfig("encrypt", {"key": "WmZq4t7w!z%C&F)J"})}.items():
    corridas = []
    for _ in range(2):
        r = an.anonymize(text=t, analyzer_results=res, operators={"DEFAULT": op})
        corridas.append([t_[:12] for t_ in [i.text for i in sorted(r.items, key=lambda x: x.start)]])
    print(nombre, "corrida 1:", corridas[0]); print(nombre, "corrida 2:", corridas[1])
    print(nombre, "| dentro del texto, las dos 'Mary Smith' iguales:", corridas[0][0] == corridas[0][2],
          "| entre corridas iguales:", corridas[0] == corridas[1])
