import json
import time
import urllib.request

from modules.excel_reader import cargar_todo
from modules.map_visualization import coordenadas_analogos

PARAMETROS = "T2M,PRECTOTCORR,RH2M"

datos = cargar_todo("data/TerraTwin_limpio.xlsx")
coords = coordenadas_analogos(datos["analogos"])
nombres = dict(zip(datos["analogos"]["ID"], datos["analogos"]["Nombre de Región"]))

primero = True
for id_c, (lat, lon) in coords.items():
    url = ("https://power.larc.nasa.gov/api/temporal/climatology/point"
           f"?parameters={PARAMETROS}&community=AG&longitude={lon}&latitude={lat}&format=JSON")
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            d = json.load(r)
        if primero:
            print("Claves de la respuesta:", list(d.keys()))
            print("Claves de properties:", list(d.get("properties", {}).keys()))
            primero = False
        p = d["properties"]["parameter"]
        print(f"{id_c} {nombres[id_c]} ({lat:.2f}, {lon:.2f}): "
              f"T2M anual {p['T2M']['ANN']} | PRECTOTCORR anual {p['PRECTOTCORR']['ANN']} "
              f"| RH2M anual {p['RH2M']['ANN']}")
    except Exception as e:
        print(f"{id_c} {nombres[id_c]}: ERROR {e}")
    time.sleep(1)  # para no saturar la API