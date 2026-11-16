from modules.planetary_topography import ventana_mola

# Coordenadas de la hoja «Variables científicas» del Excel
REGIONES = {
    "Jezero": (18.4, 77.7),
    "Gale": (-5.44, 137.70),
    "Gusev": (-14.53, 175.52),
}

for nombre, (lat, lon) in REGIONES.items():
    print(f"\n=== {nombre} ({lat}, {lon}) ===")
    r = ventana_mola(lat, lon)
    if r is None:
        print("Sin dato (la ventana no cabe en el mosaico o no tiene datos)")
        continue
    for clave, valor in r.items():
        print(f"  {clave}: {round(valor, 1) if isinstance(valor, float) else valor}")