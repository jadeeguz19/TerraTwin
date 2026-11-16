from modules.discovery import FACTOR, LADO, MAX_AGUA, PASO

RELIEVE_MIN_M = 50  # margen mínimo de relieve usado en buscar_ventanas


def generar_informe_descubrimiento(id_ref, ref, fuente, coord_ref, ref_topo, seleccion, resumen,
                                   lista, tol_pend, tol_rel, sin_mascara, zona_extensa, nota):
    """Ficha en Markdown del descubrimiento: referencia, parámetros, resultado, zonas y límites.
    'tol_rel' viene en porcentaje (30 = 30 %)."""
    lat_r, lon_r = coord_ref
    margen_rel = max(tol_rel / 100 * ref_topo["relieve"], RELIEVE_MIN_M)
    L = []
    L.append(f"# Descubrimiento TerraTwin: {ref['nombre']}\n")
    L.append("Zonas **nuevas, solo topografía**: no tienen análisis de composición ni son "
             "análogos validados.\n")

    L.append("## 1. Referencia medida")
    L.append(f"- Región: **{ref['nombre']}** ({ref['cuerpo']}, {id_ref})")
    L.append(f"- Fuente: {fuente}; ventana de {ref_topo['ventana_km']} × {ref_topo['ventana_km']} km "
             f"alrededor de {lat_r}, {lon_r}")
    L.append(f"- Resolución usada: {ref_topo['resolucion_m']:.0f} m por píxel")
    L.append(f"- Pendiente mediana: {ref_topo['pend_mediana']:.1f}°")
    L.append(f"- Relieve en la ventana: {ref_topo['relieve']:.0f} m")
    L.append("")

    L.append("## 2. Parámetros de la búsqueda")
    L.append(f"- Teselas buscadas: {', '.join(seleccion)}")
    L.append(f"- Terreno terrestre: NASADEM (NASA LP DAAC, 1 segundo de arco), promediado en "
             f"bloques de {FACTOR} × {FACTOR} píxeles (~463 m)")
    L.append(f"- Ventanas de {LADO} × {LADO} píxeles gruesos (~9,7 km), con paso de {PASO} "
             f"(traslapadas)")
    L.append(f"- Tolerancia de pendiente: ±{tol_pend}° (definida por el equipo)")
    L.append(f"- Tolerancia de relieve: ±{tol_rel} % (margen efectivo ±{margen_rel:.0f} m; "
             f"mínimo {RELIEVE_MIN_M} m; definida por el equipo)")
    L.append(f"- Se descartan ventanas con más de {MAX_AGUA * 100:.0f} % de agua según la máscara "
             f"de agua .swb de NASADEM (umbral definido por el equipo)")
    if sin_mascara:
        L.append(f"- Sin máscara de agua en {', '.join(sin_mascara)}: se usó una regla "
                 f"aproximada (más de la mitad de píxeles a 0 m)")
    L.append("- Una zona es un grupo de ventanas vecinas (8 direcciones) que coinciden")
    L.append("- Distancia a la referencia: 0 = idéntica en pendiente y relieve; cerca de 1 = en "
             "el borde de la tolerancia. Medida definida por el equipo para ordenar las zonas; "
             "no es una probabilidad")
    L.append(f"- Zona extensa: {zona_extensa} ventanas o más (umbral del equipo): casi una tesela "
             f"entera, la topografía no distingue ahí")
    L.append("")

    L.append("## 3. Resultado")
    L.append(f"- Ventanas evaluadas: {sum(r['evaluadas'] for r in resumen)}")
    L.append(f"- Excluidas por agua: {sum(r['excluidas_agua'] for r in resumen)}")
    L.append(f"- Ventanas que coinciden: {sum(r['coinciden'] for r in resumen)}")
    L.append(f"- Zonas: {len(lista)}")
    L.append("")
    L.append("| Tesela | Ventanas evaluadas | Excluidas por agua | Coinciden | Zonas |")
    L.append("|---|---|---|---|---|")
    for r in resumen:
        L.append(f"| {r['tesela']} | {r['evaluadas']} | {r['excluidas_agua']} | "
                 f"{r['coinciden']} | {r['zonas']} |")
    L.append("")
    if lista:
        L.append("Zonas ordenadas por distancia a la referencia:\n")
        L.append("| Zona | Distancia | Ventanas | Lat mín | Lat máx | Lon mín | Lon máx "
                 "| Pend. media (°) | Relieve medio (m) | Análogo conocido dentro | Aviso |")
        L.append("|---|---|---|---|---|---|---|---|---|---|---|")
        for z in lista:
            aviso = "zona extensa" if z["ventanas"] >= zona_extensa else ""
            L.append(f"| {z['id_zona']} | {z['distancia']:.2f} | {z['ventanas']} "
                     f"| {z['lat_min']:.3f} | {z['lat_max']:.3f} | {z['lon_min']:.3f} "
                     f"| {z['lon_max']:.3f} | {z['pend_media']:.2f} | {z['relieve_medio']:.0f} "
                     f"| {', '.join(z['conocidos']) or 'ninguno'} | {aviso} |")
    else:
        L.append("Ninguna ventana coincide con estas tolerancias.")
    L.append("")

    L.append("## 4. Límites")
    L.append("- Solo se compara topografía (pendiente mediana y relieve): no composición, "
             "minerales ni agua.")
    L.append("- Cubre únicamente las teselas indicadas, no toda la Tierra.")
    L.append("- Con referencias llanas casi cualquier planicie coincide; una zona de decenas de "
             "ventanas es una meseta, no un hallazgo.")
    L.append("- Las tolerancias, el umbral de agua y el umbral de zona extensa son parámetros del "
             "equipo, no valores científicos.")
    L.append("- Las escalas de Marte (463 m), la Luna (474 m) y la Tierra (463 m) son parecidas "
             "pero no idénticas.")
    if ref["cuerpo"] == "Marte":
        L.append("- Los huecos entre pasadas de MOLA se rellenan por interpolación: las pendientes "
                 "de Marte pueden salir algo suaves.")
    else:
        L.append("- Las coordenadas de la región lunar son aproximadas en nuestro Excel: la "
                 "medición describe la ventana de 10 km alrededor de ese punto. La elevación "
                 "lunar es relativa a una esfera de referencia, no al nivel del mar.")
    L.append("- Parte de la validación es circular: los análogos se eligieron por su relación con "
             "Marte y la Luna.")
    L.append("")

    L.append("## 5. Fuentes")
    L.append("- NASADEM Merged DEM Global 1 arc second V001 (NASA LP DAAC)")
    L.append("- Marte: mosaico global MOLA 463 m (USGS Astrogeology)"
             if ref["cuerpo"] == "Marte" else
             "- Luna: mosaico global LOLA 118 m, LDEM (USGS Astrogeology)")
    L.append("")
    L.append(f"> {nota}")
    return "\n".join(L)