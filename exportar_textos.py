from modules.excel_reader import cargar_todo

ana = cargar_todo("data/TerraTwin_limpio.xlsx")["analogos"]
columnas = ["Justificación de analogía", "Aplicaciones en misiones espaciales",
            "Limitaciones y diferencias"]
with open("data/textos_es.txt", "w", encoding="utf-8") as f:
    for _, fila in ana.iterrows():
        f.write(f"## {fila['ID']} | {fila['Nombre de Región']}\n")
        for c in columnas:
            f.write(f"{c}: {str(fila[c]).strip()}\n")
        f.write("\n")
print("Listo: data/textos_es.txt")