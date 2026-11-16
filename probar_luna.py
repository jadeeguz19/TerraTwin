from modules.excel_reader import cargar_todo

reg = cargar_todo("data/TerraTwin_limpio.xlsx")["regiones"]
luna = reg[reg["Cuerpo planetario"].astype(str).str.contains("Luna", case=False, na=False)]
for _, f in luna.iterrows():
    print(f["ID"], "|", f["Nombre de la región"], "|", repr(f["Coordenadas"]))