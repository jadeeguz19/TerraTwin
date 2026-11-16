import folium

from modules.data_validation import parsear_coordenada


def color_indice(indice):
    """Los cortes solo sirven para visualizar; el índice real se muestra siempre."""
    if indice is None:
        return "gray"
    if indice >= 75:
        return "green"
    if indice >= 50:
        return "orange"
    return "red"


def coordenadas_analogos(df_analogos):
    """Devuelve {ID: (lat, lon)} solo con las coordenadas que se pudieron interpretar."""
    coords = {}
    for _, f in df_analogos.iterrows():
        lat = parsear_coordenada(f["Latitud"])
        lon = parsear_coordenada(f["Longitud"])
        if lat is not None and lon is not None:
            coords[f["ID"]] = (lat, lon)
    return coords


def crear_mapa(tabla, coords):
    mapa = folium.Map(location=[20, 0], zoom_start=2, tiles="OpenStreetMap")
    for f in tabla:
        if f["id"] not in coords:
            continue
        lat, lon = coords[f["id"]]
        indice = "sin criterios comparables" if f["indice"] is None else f"{f['indice']} %"
        html = (f"<b>{f['nombre']}</b><br>"
                f"{f['cumplidos']} de {f['comparados']} criterios cumplidos<br>"
                f"Índice: {indice}<br>"
                f"<small>Coordenadas: {lat:.4f}, {lon:.4f}</small>")
        color = color_indice(f["indice"])
        folium.CircleMarker(
            location=[lat, lon],
            radius=10,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.8,
            tooltip=f["nombre"],
            popup=folium.Popup(html, max_width=300),
        ).add_to(mapa)

    # Ajusta el encuadre para que se vean todos los puntos, incluidos los polares
    puntos = [coords[f["id"]] for f in tabla if f["id"] in coords]
    if puntos:
        mapa.fit_bounds([[min(p[0] for p in puntos), min(p[1] for p in puntos)],
                        [max(p[0] for p in puntos), max(p[1] for p in puntos)]])
    return mapa