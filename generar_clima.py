import csv
import json
import time
import urllib.request
from datetime import date

from modules.excel_reader import cargar_todo
from modules.map_visualization import coordenadas_analogos

PARAMETROS = ["T2M", "PRECTOTCORR", "RH2M"]
SALIDA = "data/clima_analogos.csv"

datos = cargar_todo("data/TerraTwin_limpio.xlsx")
coords = coordenadas_analogos(datos["analogos"])
nombres = dict(zip(datos["analogos"]["ID"], datos["analogos"]["Nombre de Región"]))


def valor(p, par):
    """Valor anual, o None si falta o es un relleno (-999)."""
    v = p.get(par, {}).get("ANN")
    return None if v is None or v <= -990 else v


filas = []
unidades = {}
for id_c, (lat, lon) in coords.items():
    url = ("https://power.larc.nasa.gov/api/temporal/climatology/point"
           f"?parameters={','.join(PARAMETROS)}&community=AG"
           f"&longitude={lon}&latitude={lat}&format=JSON")
    fila = {"id": id_c, "nombre": nombres[id_c], "lat": lat, "lon": lon,
            "t2m_c": "", "prec_mm_dia": "", "prec_mm_anio": "", "rh2m_pct": "",
            "fuente": "NASA POWER climatología (MERRA-2, reanálisis: estimado)",
            "consultado": str(date.today())}
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            d = json.load(r)
        p = d["properties"]["parameter"]
        for par in PARAMETROS:
            unidades[par] = d.get("parameters", {}).get(par, {}).get("units", "?")
        t, pr, rh = valor(p, "T2M"), valor(p, "PRECTOTCORR"), valor(p, "RH2M")
        fila["t2m_c"] = "" if t is None else round(t, 2)
        fila["rh2m_pct"] = "" if rh is None else round(rh, 1)
        if pr is not None:
            fila["prec_mm_dia"] = round(pr, 3)
            if unidades.get("PRECTOTCORR") == "mm/day":
                fila["prec_mm_anio"] = round(pr * 365)
    except Exception as e:
        print(f"{id_c} {nombres[id_c]}: ERROR {e} (queda sin dato)")
    filas.append(fila)
    time.sleep(1)

with open(SALIDA, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(filas[0].keys()))
    w.writeheader()
    w.writerows(filas)

print("Unidades según la API:", unidades)
for f in filas:
    print(f["id"], f["nombre"], "|", f["t2m_c"], "°C |", f["prec_mm_dia"], "mm/día |",
          f["prec_mm_anio"], "mm/año |", f["rh2m_pct"], "%")
print("Guardado en", SALIDA)