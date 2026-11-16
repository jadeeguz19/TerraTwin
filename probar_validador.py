from modules.excel_reader import cargar_todo
from modules.data_validation import validar

datos = cargar_todo("data/TerraTwin_limpio.xlsx")
problemas = validar(datos)

errores = [p for p in problemas if p["nivel"] == "ERROR"]
avisos = [p for p in problemas if p["nivel"] == "AVISO"]
print(f"{len(errores)} errores y {len(avisos)} avisos\n")
for p in problemas:
    print(f"[{p['nivel']}] ({p['hoja']}) {p['mensaje']}")