import pandas as pd


def _limpio(valor):
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return "no registrado"
    texto = str(valor).strip()
    return texto if texto else "no registrado"


def fuentes_region(df_variables, id_region):
    """Fuentes distintas citadas en la hoja de variables para una región."""
    fuentes = df_variables.loc[df_variables["ID Región"] == id_region, "Fuente"].dropna()
    return sorted({str(f).strip() for f in fuentes if str(f).strip() not in ("", "—")})


def _cifra(valor, formato, unidad):
    return "sin dato" if valor is None else f"{format(valor, formato)} {unidad}"


def generar_informe(ref_id, ref, cand_id, cand, resultado, coords, topo, mensaje_topo,
                    datos, nota, clima=None):
    analogos = datos["analogos"]
    fila = analogos[analogos["ID"] == cand_id]
    fila = fila.iloc[0] if not fila.empty else None

    def campo(columna):
        if fila is not None and columna in fila.index:
            return _limpio(fila[columna])
        return "no registrado"

    L = []
    L.append(f"# Informe TerraTwin: {ref['nombre']} frente a {cand['nombre']}\n")
    L.append("## 1. Resumen")
    L.append(f"- Región de referencia: **{ref['nombre']}** ({ref['cuerpo']}, {ref_id})")
    L.append(f"- Candidato terrestre: **{cand['nombre']}** ({cand_id}), {campo('País')}")
    if cand_id in coords:
        lat, lon = coords[cand_id]
        L.append(f"- Coordenadas: {lat:.4f}, {lon:.4f}")
    L.append(f"- Criterios cumplidos: **{resultado['cumplidos']} de {resultado['comparados']}** "
             f"({5 - resultado['comparados']} sin dato)")
    if resultado["indice"] is not None:
        L.append(f"- Índice de similitud (definido por el algoritmo de TerraTwin): "
                 f"**{resultado['indice']} %**")
    L.append("")
    L.append("## 2. Comparación por criterio")
    L.append("| Criterio | Referencia | Candidato | En común | Estado |")
    L.append("|---|---|---|---|---|")
    for d in resultado["detalle"]:
        L.append(f"| {d['criterio']} | {d['referencia']} | {d['candidato']} | "
                 f"{d['en_comun']} | {d['estado']} |")
    L.append("")
    L.append("## 3. Justificación y aplicaciones (según nuestra base documentada)")
    L.append("**Justificación de la analogía:**")
    L.append(campo("Justificación de analogía"))
    L.append("")
    L.append("**Aplicaciones en misiones espaciales:**")
    L.append(campo("Aplicaciones en misiones espaciales"))
    L.append("")
    L.append("## 4. Contexto topográfico medido (NASADEM)")
    if topo:
        L.append(f"- Elevación en el punto: {topo['elev_punto']:.0f} m"
                 if topo["elev_punto"] is not None else "- Elevación en el punto: sin dato")
        L.append(f"- Rango de elevación: {topo['elev_min']:.0f} a {topo['elev_max']:.0f} m")
        L.append(f"- Pendiente media: {topo['pend_media']:.1f}°")
        L.append(f"- Zona con pendiente menor de 5°: {topo['pct_suave']:.0f} %")
        L.append(f"- Ventana analizada: {topo['ventana_km']} × {topo['ventana_km']} km; "
                 f"{topo['pct_validos']:.0f} % de la ventana con dato")
        L.append("- Fuente: NASADEM (NASA LP DAAC), 1 segundo de arco. No entra en el índice "
                 "de similitud. Para compararla con Marte o la Luna a la misma escala, usar la "
                 "sección Descubrimiento.")
    else:
        L.append(mensaje_topo or "Sin dato topográfico.")
    L.append("")
    L.append("## 5. Clima estimado (NASA POWER)")
    if clima:
        L.append(f"- Temperatura media anual: {_cifra(clima.get('t2m_c'), '.1f', '°C')}")
        L.append(f"- Precipitación anual: {_cifra(clima.get('prec_mm_anio'), '.0f', 'mm/año')}")
        L.append(f"- Humedad relativa media: {_cifra(clima.get('rh2m_pct'), '.0f', '%')}")
        L.append(f"- Fuente: {clima.get('fuente', 'NASA POWER')}; consultado el "
                 f"{clima.get('consultado', 'sin fecha')}.")
        L.append("- Es un **estimado** de reanálisis de resolución gruesa (decenas de km): "
                 "describe la zona, no el punto exacto, y en sitios de gran relieve puede "
                 "diferir mucho del punto. No entra en el índice de similitud y no se compara "
                 "con la temperatura de Marte o la Luna.")
    else:
        L.append("Sin dato climático para este candidato.")
    L.append("")
    L.append("## 6. Limitaciones y diferencias")
    L.append(campo("Limitaciones y diferencias"))
    L.append("")
    L.append("Limitaciones generales de esta versión:")
    L.append("- El índice mide criterios cumplidos entre los comparables; no es una probabilidad "
             "ni prueba de que el lugar sea un análogo validado.")
    L.append("- «Sin dato» significa no documentado en nuestra base, no ausente.")
    L.append("- Las etiquetas de los perfiles se derivaron de la investigación documentada del "
             "equipo, no de una medición propia de composición.")
    L.append("- El ranking cubre solo 10 análogos terrestres documentados; no es una búsqueda global.")
    L.append("- Parte de la validación es circular: los análogos se eligieron por su relación "
             "con Marte y la Luna.")
    L.append("")
    L.append("## 7. Fuentes")
    L.append(f"Candidato ({cand_id}): {campo('Fuentes')}")
    L.append("")
    L.append(f"Región de referencia ({ref_id}), según la hoja de variables:")
    fuentes = fuentes_region(datos["variables"], ref_id)
    L.extend([f"- {f}" for f in fuentes] if fuentes else ["- no registradas"])
    L.append("")
    L.append(f"> {nota}")
    return "\n".join(L)