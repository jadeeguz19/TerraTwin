from modules.excel_reader import cargar_todo

datos = cargar_todo("data/TerraTwin_limpio.xlsx")
print(sorted(datos["regiones"]["ID"]))
print(sorted(datos["variables"]["ID Región"].unique()))
print(sorted(datos["analogos"]["ID"]))