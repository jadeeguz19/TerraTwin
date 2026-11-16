import math
from modules.excel_reader import cargar_todo
from modules.map_visualization import coordenadas_analogos

datos = cargar_todo("data/TerraTwin_limpio.xlsx")
coords = coordenadas_analogos(datos["analogos"])
nombres = dict(zip(datos["analogos"]["ID"], datos["analogos"]["Nombre de Región"]))

for id_c, (lat, lon) in coords.items():
    if lat > 60 or lat < -56:
        print(f"{id_c} {nombres[id_c]}: fuera de cobertura NASADEM")
        continue
    la, lo = math.floor(lat), math.floor(lon)
    tesela = f"{'n' if la >= 0 else 's'}{abs(la):02d}{'e' if lo >= 0 else 'w'}{abs(lo):03d}"
    print(f"{id_c} {nombres[id_c]}: lat {lat:.4f}, lon {lon:.4f} -> tesela {tesela}")