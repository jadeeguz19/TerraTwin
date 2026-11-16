import time

from modules.planetary_topography import ventana_luna

# Coordenadas tomadas de tu Excel (Marius Hills y Aristarchus son "aproximadamente")
REGIONES = {
    "Marius Hills (LUN-09)": (13.0, -53.0),
    "Aristarchus (LUN-08)": (25.0, -50.0),
    "Mare Tranquillitatis (LUN-10)": (8.35, 30.83),
}

for nombre, (lat, lon) in REGIONES.items():
    t0 = time.time()
    r = ventana_luna(lat, lon)
    seg = round(time.time() - t0, 1)
    print(f"\n{nombre}  ({lat}, {lon})  [{seg} s]")
    if r is None:
        print("  sin dato (la ventana no cabe o no tiene datos)")
        continue
    print(f"  elevación en el punto: {r['elev_punto']:.0f} m")
    print(f"  rango: {r['elev_min']:.0f} a {r['elev_max']:.0f} m  |  relieve: {r['relieve']:.0f} m")
    print(f"  pendiente mediana: {r['pend_mediana']:.1f}°  |  media: {r['pend_media']:.1f}°")
    print(f"  datos válidos: {r['pct_validos']:.0f} %  |  resolución: {r['resolucion_m']:.0f} m")