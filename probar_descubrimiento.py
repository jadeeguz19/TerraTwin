from modules.discovery import buscar_ventanas, estadisticas_ventanas, zonas
from modules.planetary_topography import ventana_mola

REGIONES = {"Jezero": (18.4, 77.7), "Gale": (-5.44, 137.70), "Gusev": (-14.53, 175.52)}
TESELAS = {
    "S25W070 (Atacama)": ("data/processed/S25W070.hgt", {"Yungay (EAR-03)": (-24.0638, -69.8805)}),
    "N18W072 (Enriquillo)": ("data/processed/N18W072.hgt", {"Enriquillo (EAR-01)": (18.5283, -71.7152)}),
}

referencias = {n: ventana_mola(lat, lon) for n, (lat, lon) in REGIONES.items()}

for tesela, (ruta, conocidos) in TESELAS.items():
    s = estadisticas_ventanas(ruta)
    print(f"\n##### Tesela {tesela}: {s['n_evaluadas']} ventanas evaluadas #####")
    print(f"  Máscara de agua usada: {s['usa_mascara']} | ventanas excluidas por agua: {s['excluidas_agua']}")
    for nombre, ref in referencias.items():
        m = buscar_ventanas(s, ref)
        z = zonas(s, m, conocidos)
        print(f"\n  Referencia {nombre} (pendiente {ref['pend_mediana']:.1f}°, relieve {ref['relieve']:.0f} m)")
        print(f"  Ventanas que coinciden: {int(m.sum())} de {s['n_evaluadas']}  ->  {len(z)} zonas")
        for zona in z[:3]:
            print(f"    zona {zona['id']}: {zona['ventanas']} ventanas | "
                  f"lat {zona['lat_min']:.2f} a {zona['lat_max']:.2f} | "
                  f"lon {zona['lon_min']:.2f} a {zona['lon_max']:.2f} | "
                  f"pend {zona['pend_media']:.1f}° | contiene: {zona['conocidos'] or 'ninguno conocido'}")