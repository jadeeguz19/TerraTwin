from modules.similarity_engine import cargar_perfiles, ranking

perfiles = cargar_perfiles("data/perfiles_comparables.csv")

for id_ref in ["MAR-01", "MAR-02", "MAR-03", "LUN-09"]:
    print(f"\n=== Referencia: {perfiles[id_ref]['nombre']} ===")
    for f in ranking(perfiles, id_ref):
        print(f"{f['nombre']:<26} {f['cumplidos']} de {f['comparados']} criterios  (índice {f['indice']})")

# Detalle del primero para Jezero
primero = ranking(perfiles, "MAR-01")[0]
print(f"\nDetalle: Jezero vs {primero['nombre']}")
for d in primero["detalle"]:
    print(f"  {d['criterio']:<28} {d['estado']:<9} | ref: {d['referencia']} | cand: {d['candidato']}")