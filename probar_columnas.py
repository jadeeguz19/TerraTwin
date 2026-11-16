from modules.excel_reader import cargar_todo
from modules.data_validation import validar

datos = cargar_todo("data/TerraTwin_limpio.xlsx")
ana = datos["analogos"]
columnas = ["Usos como análogo", "Limitaciones y diferencias",
            "Aplicaciones en misiones espaciales"]

for _, f in ana.iterrows():
    print(f"\n{f['ID']} {f['Nombre de Región']}")
    for c in columnas:
        if c not in ana.columns:
            print(f"  [{c}] (la columna no existe)")
            continue
        v = f[c]
        vacia = v is None or str(v).strip() in ("", "nan")
        print(f"  [{c}] {'VACÍA' if vacia else str(v).strip()[:70]}")

problemas = validar(datos)
print("\nValidación:", len(problemas), "problemas")
for p in problemas:
    print(" ", p["nivel"], p["hoja"], p["mensaje"])