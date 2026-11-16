import re
from pathlib import Path

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from modules.discovery import estadisticas_ventanas
from modules.discovery_ranking import buscar_en_teselas
from modules.discovery_report import generar_informe_descubrimiento
from modules.estilos import (aplicar_estilos, buscar_imagen, etiqueta_lateral, hero,
                             marca_lateral, tarjeta_region, tarjetas, top_analogos)
from modules.excel_reader import cargar_todo
from modules.map_visualization import coordenadas_analogos, crear_mapa
from modules.planetary_topography import ventana_luna, ventana_mola
from modules.report_generator import generar_informe
from modules.similarity_engine import CRITERIOS, _texto, cargar_perfiles, comparar, ranking
from modules.topography import nombre_tesela, resumen_topografico, ruta_tesela

st.set_page_config(page_title="TerraTwin", layout="wide")
aplicar_estilos()

# Coordenadas con las que se midió cada región de referencia (MOLA para Marte, LOLA para la Luna).
# Las de Marius Hills son "aproximadamente 13° N, 53° O" en nuestro Excel: la medición describe
# la ventana de 10 km alrededor de ese punto aproximado, no necesariamente los domos.
COORD_REF = {
    "MAR-01": (18.4, 77.7),
    "MAR-02": (-5.44, 137.70),
    "MAR-03": (-14.53, 175.52),
    "LUN-09": (13.0, -53.0),
}

# Parámetros del equipo (no son valores científicos)
ZONA_EXTENSA = 50        # zonas con este número de ventanas o más se marcan como "extensas"
MIN_VENTANAS_TESELA = 20  # teselas con menos ventanas evaluables se avisan
TODAS = "Todas las zonas"


@st.cache_data
def obtener_perfiles():
    return cargar_perfiles("data/perfiles_comparables.csv")


@st.cache_data
def obtener_datos():
    return cargar_todo("data/TerraTwin_limpio.xlsx")


@st.cache_data
def obtener_coordenadas():
    return coordenadas_analogos(obtener_datos()["analogos"])


@st.cache_data
def obtener_clima():
    """Clima estimado de los análogos (data/clima_analogos.csv, de NASA POWER).
    Los datos vacíos quedan como None: sin dato, nunca cero."""
    ruta = Path("data/clima_analogos.csv")
    if not ruta.exists():
        return {}
    df = pd.read_csv(ruta, encoding="utf-8-sig")
    clima = {}
    for _, f in df.iterrows():
        def v(col):
            return None if col not in df.columns or pd.isna(f[col]) else float(f[col])
        clima[f["id"]] = {
            "t2m_c": v("t2m_c"), "prec_mm_anio": v("prec_mm_anio"), "rh2m_pct": v("rh2m_pct"),
            "fuente": str(f.get("fuente", "NASA POWER")),
            "consultado": str(f.get("consultado", "sin fecha")),
        }
    return clima


@st.cache_data
def topografia(ruta, lat, lon):
    return resumen_topografico(ruta, lat, lon)


@st.cache_data(show_spinner=False)
def ventanas_tesela(ruta):
    return estadisticas_ventanas(ruta)


@st.cache_data(show_spinner=False)
def referencia_topo(cuerpo, lat, lon):
    """Topografía medida de la región de referencia: MOLA (Marte) o LOLA (Luna)."""
    if cuerpo == "Luna":
        return ventana_luna(lat, lon)
    return ventana_mola(lat, lon)


def teselas_disponibles():
    """Nombres de las teselas NASADEM que están en data/processed (ej. 'N18W072')."""
    return sorted(p.stem.upper() for p in Path("data/processed").glob("*.hgt"))


def nombre_zona(tesela):
    """'N18W072' -> 'Lago Enriquillo': el sitio documentado que cae dentro de esa tesela.
    Si no hay ninguno, devuelve el código de la tesela."""
    if tesela == TODAS:
        return tesela
    nombres = {}
    for k, (lat, lon) in obtener_coordenadas().items():
        if k in perfiles and -56 <= lat <= 60:
            nombres[nombre_tesela(lat, lon)] = perfiles[k]["nombre"]
    return nombres.get(tesela, tesela)


def limites_tesela(nombre):
    """'N18W072' -> [[lat_sur, lon_oeste], [lat_norte, lon_este]] (esquina inferior izquierda + 1°)."""
    m = re.fullmatch(r"([NS])(\d+)([EW])(\d+)", nombre)
    lat = int(m.group(2)) * (1 if m.group(1) == "N" else -1)
    lon = int(m.group(4)) * (1 if m.group(3) == "E" else -1)
    return [[lat, lon], [lat + 1, lon + 1]]


def crear_mapa_zonas(nombres_teselas, lista_zonas, conocidos):
    limites = {n: limites_tesela(n) for n in nombres_teselas}
    mapa = folium.Map(tiles="OpenStreetMap")
    for n, lim in limites.items():
        folium.Rectangle(lim, color="gray", weight=1, fill=False,
                         tooltip=f"Tesela NASADEM {n}").add_to(mapa)
    varias = len(nombres_teselas) > 1
    for z in lista_zonas:
        extensa = z["ventanas"] >= ZONA_EXTENSA
        etiqueta = (f"Zona {z['id_zona']} · nueva, solo topografía · distancia "
                    f"{z['distancia']:.2f} · {z['ventanas']} ventanas · pendiente "
                    f"{z['pend_media']:.1f}° · relieve {z['relieve_medio']:.0f} m"
                    + (" · ZONA EXTENSA" if extensa else ""))
        folium.Rectangle([[z["lat_min"], z["lon_min"]], [z["lat_max"], z["lon_max"]]],
                         color="orange", weight=2, fill=True,
                         fill_opacity=0.12 if extensa else 0.35,
                         dash_array="6,6" if extensa else None,
                         tooltip=etiqueta, popup=etiqueta).add_to(mapa)
        if varias:  # con varias teselas el mapa se aleja: un punto en el centro ayuda a verlas
            folium.CircleMarker([(z["lat_min"] + z["lat_max"]) / 2,
                                 (z["lon_min"] + z["lon_max"]) / 2],
                                radius=5, color="orange", fill=True, fill_opacity=0.9,
                                tooltip=etiqueta).add_to(mapa)
    for nombre, (la, lo) in conocidos.items():
        for lim in limites.values():
            if lim[0][0] <= la <= lim[1][0] and lim[0][1] <= lo <= lim[1][1]:
                folium.CircleMarker([la, lo], radius=7, color="blue", fill=True, fill_opacity=0.8,
                                    tooltip=f"Análogo documentado: {nombre}").add_to(mapa)
                break
    sur = min(l[0][0] for l in limites.values())
    oeste = min(l[0][1] for l in limites.values())
    norte = max(l[1][0] for l in limites.values())
    este = max(l[1][1] for l in limites.values())
    mapa.fit_bounds([[sur, oeste], [norte, este]])
    return mapa


def estado_topografia(id_c, coords):
    """Devuelve (resultado, mensaje). Si no hay dato, resultado es None y hay mensaje.
    La tesela de NASADEM se busca sola en data/processed según las coordenadas."""
    if id_c not in coords:
        return None, "Sin coordenadas válidas para este candidato."
    lat, lon = coords[id_c]
    if lat > 60 or lat < -56:
        return None, ("Sin dato topográfico: este sitio está fuera de la cobertura de "
                      "NASADEM (60° N a 56° S).")
    nombre, ruta = ruta_tesela(lat, lon)
    if not ruta.exists():
        return None, (f"Sin dato topográfico: la tesela NASADEM {nombre} aún no se ha "
                      f"incorporado en esta versión.")
    res = topografia(str(ruta), lat, lon)
    if res is None:
        return None, "Sin dato topográfico válido en esta zona."
    return res, None


perfiles = obtener_perfiles()
referencias = {pid: f"{p['nombre']} ({p['cuerpo']})"
               for pid, p in perfiles.items() if p["cuerpo"] != "Tierra"}
imagen = buscar_imagen()

# Logo del equipo (carpeta "logos", aparte de "assets" para no confundirlo con la mascota)
LOGO = next(Path("logos").glob("logo.*"), None)
if LOGO is not None:
    st.sidebar.image(str(LOGO), width=140)
marca_lateral(imagen)
st.sidebar.divider()
etiqueta_lateral("NAVEGACIÓN")
seccion = st.sidebar.radio("Sección", ["Inicio", "Explorador", "Mapa", "Análisis",
                                       "Descubrimiento", "Informes"],
                           label_visibility="collapsed")
st.sidebar.divider()
etiqueta_lateral("REGIÓN DE REFERENCIA")
id_ref = st.sidebar.selectbox("Región de referencia", list(referencias),
                              format_func=lambda i: referencias[i],
                              label_visibility="collapsed")
ref = perfiles[id_ref]
tabla = ranking(perfiles, id_ref)

NOTA = ("El índice es una medida definida por el algoritmo de TerraTwin: criterios cumplidos "
        "entre los criterios comparables. No es una probabilidad ni prueba de que un lugar "
        "sea un análogo validado. «Sin dato» significa no documentado en nuestra base, no ausente.")

if seccion == "Inicio":
    st.markdown(
        hero(["Explora otros mundos.", "Encuentra conexiones en la Tierra."],
             "Una herramienta para comparar regiones de Marte y la Luna con lugares "
             "terrestres documentados como posibles análogos, a partir de características "
             "con fuente.",
             ["MARTE", "LUNA", "TIERRA"]),
        unsafe_allow_html=True)

    st.subheader("Panel de exploración")
    p1, p2, p3 = st.columns(3)
    p1.metric("Región de referencia", ref["nombre"])
    p2.metric("Análogos documentados", sum(1 for p in perfiles.values() if p["cuerpo"] == "Tierra"))
    p3.metric("Criterios de comparación", len(CRITERIOS))

    st.subheader("¿Qué puedes explorar?")
    st.markdown(tarjetas([
        ("01 · Explorador", "Consulta perfiles de regiones y compara análogos terrestres "
                            "documentados."),
        ("02 · Análisis", "Examina criterios compartidos, contexto topográfico y estimaciones "
                          "climáticas."),
        ("03 · Descubrimiento", "Busca zonas terrestres con características topográficas "
                                "similares a una región de referencia."),
    ]), unsafe_allow_html=True)

    st.markdown(tarjeta_region(
        ref["nombre"], ref["cuerpo"],
        f"Actualmente estás explorando {ref['nombre']}, ubicada en {ref['cuerpo']}. Puedes "
        f"cambiar la región desde el selector de la barra lateral."), unsafe_allow_html=True)
    st.info("Alcance de esta versión: ranking de 10 análogos terrestres documentados, "
            "no una búsqueda global. La sección Descubrimiento compara solo topografía y cubre "
            "únicamente las zonas descargadas.")

elif seccion == "Explorador":
    st.header(f"Referencia: {ref['nombre']}")
    st.markdown(tarjeta_region(ref["nombre"], ref["cuerpo"]), unsafe_allow_html=True)
    st.markdown("<h3 class='tt-acento'>Posibles análogos terrestres</h3>", unsafe_allow_html=True)
    st.markdown(top_analogos(tabla, perfiles), unsafe_allow_html=True)
    st.caption("Los tres con mayor índice de similitud, una medida definida por TerraTwin "
               "(criterios cumplidos entre los comparables); no es una probabilidad.")
    st.subheader("Perfil de la región")
    st.table(pd.DataFrame([{"Característica": etiqueta, "Valor": _texto(ref[clave])}
                           for clave, etiqueta, _ in CRITERIOS]))
    st.subheader("Ranking de análogos terrestres documentados")
    st.dataframe(pd.DataFrame([{
        "Candidato": f["nombre"],
        "Criterios cumplidos": f"{f['cumplidos']} de {f['comparados']}",
        "Índice de similitud (%)": f["indice"],
        "Criterios sin dato": len(CRITERIOS) - f["comparados"],
    } for f in tabla]), hide_index=True)
    st.caption(NOTA)

elif seccion == "Mapa":
    st.header(f"Mapa: análogos terrestres frente a {ref['nombre']}")
    coords = obtener_coordenadas()
    mapa = crear_mapa(tabla, coords)
    st_folium(mapa, height=520, width=900, returned_objects=[])
    faltan = [f["nombre"] for f in tabla if f["id"] not in coords]
    if faltan:
        st.warning(f"Sin coordenadas válidas: {', '.join(faltan)}")
    st.caption("Verde: 75 % o más · Naranja: 50–74 % · Rojo: menos de 50 % · "
               "Gris: sin criterios comparables. Los cortes solo sirven para visualizar. "
               "La región de referencia (Marte o Luna) no se dibuja aquí: este es un mapa "
               "de la Tierra y no debe usarse como cartografía de otros cuerpos. " + NOTA)

elif seccion == "Análisis":
    st.header(f"Análisis: {ref['nombre']}")
    nombres = {f["id"]: f["nombre"] for f in tabla}
    id_c = st.selectbox("Candidato terrestre", list(nombres), format_func=lambda i: nombres[i])
    r = comparar(ref, perfiles[id_c])
    st.write(f"**{ref['nombre']}** frente a **{nombres[id_c]}**: "
             f"{r['cumplidos']} de {r['comparados']} criterios cumplidos.")
    st.dataframe(pd.DataFrame(r["detalle"]).rename(columns={
        "criterio": "Criterio", "referencia": "Referencia", "candidato": "Candidato",
        "en_comun": "En común", "estado": "Estado"}), hide_index=True)
    st.caption(NOTA)

    st.subheader("Contexto topográfico medido (NASADEM)")
    coords = obtener_coordenadas()
    res, mensaje = estado_topografia(id_c, coords)
    if res is None:
        st.info(mensaje)
    else:
        lat, lon = coords[id_c]
        c1, c2, c3, c4 = st.columns(4)
        punto = res["elev_punto"]
        c1.metric("Elevación en el punto", "sin dato" if punto is None else f"{punto:.0f} m")
        c2.metric("Rango de elevación", f"{res['elev_min']:.0f}–{res['elev_max']:.0f} m")
        c3.metric("Pendiente media", f"{res['pend_media']:.1f}°")
        c4.metric("Zona con pendiente < 5°", f"{res['pct_suave']:.0f} %")
        if res["pct_validos"] < 99.5:
            st.warning(f"Solo el {res['pct_validos']:.0f} % de la ventana tiene dato (el resto "
                       f"queda fuera de la tesela descargada o sin medición). Las cifras "
                       f"describen únicamente esa parte.")
        st.caption(
            f"Fuente: NASADEM (NASA LP DAAC), resolución de 1 segundo de arco (unos 30 m). "
            f"Ventana de unos {res['ventana_km']} × {res['ventana_km']} km alrededor de "
            f"{lat:.4f}, {lon:.4f}; relieve local de {res['relieve']:.0f} m; "
            f"{res['pct_validos']:.0f} % de la ventana con dato. Es una medición de la Tierra: "
            f"para comparar con otros cuerpos se usa la sección Descubrimiento, a la misma "
            f"escala; este panel no entra en el índice de similitud.")

    st.subheader("Clima estimado (NASA POWER)")
    cl = obtener_clima().get(id_c)
    if not cl:
        st.info("Sin dato climático para este candidato.")
    else:
        k1, k2, k3 = st.columns(3)
        k1.metric("Temperatura media anual",
                  "sin dato" if cl["t2m_c"] is None else f"{cl['t2m_c']:.1f} °C")
        k2.metric("Precipitación anual",
                  "sin dato" if cl["prec_mm_anio"] is None else f"{cl['prec_mm_anio']:.0f} mm/año")
        k3.metric("Humedad relativa media",
                  "sin dato" if cl["rh2m_pct"] is None else f"{cl['rh2m_pct']:.0f} %")
        st.caption(
            f"Fuente: {cl['fuente']}; consultado el {cl['consultado']}. Es un **estimado** de "
            f"reanálisis de resolución gruesa (decenas de km): describe la zona, no el punto "
            f"exacto, y en sitios de gran relieve (como Mauna Kea) puede diferir mucho del "
            f"punto. Cubre también los sitios fuera de NASADEM. No entra en el índice de "
            f"similitud y no se compara con la temperatura de Marte o la Luna: sus atmósferas "
            f"y presiones son muy distintas.")

elif seccion == "Descubrimiento":
    cuerpo = ref["cuerpo"]
    fuente = "LOLA" if cuerpo == "Luna" else "MOLA"
    st.header(f"Descubrimiento por topografía: {ref['nombre']}")
    st.write("Busca zonas de la Tierra cuya pendiente y relieve se parecen a los medidos en la "
             f"región de referencia ({fuente}, {cuerpo}), comparados a la misma escala "
             "(~470 m por píxel). Son zonas **nuevas, solo topografía**: no tienen análisis de "
             "composición ni son análogos validados.")

    if id_ref not in COORD_REF:
        st.warning("Esta región de referencia aún no tiene topografía medida en TerraTwin. "
                   "Elige Jezero, Gale, Gusev o Marius Hills en la barra lateral.")
    else:
        teselas = teselas_disponibles()
        if not teselas:
            st.info("No hay teselas NASADEM en data/processed.")
        else:
            col_a, col_b, col_c = st.columns(3)
            eleccion = col_a.selectbox("Zona de estudio", sorted(teselas, key=nombre_zona) + [TODAS],
                                       format_func=nombre_zona)
            col_a.caption("Cada zona es un cuadrado de 1° × 1° (unos 110 km) que contiene el sitio.")
            tol_pend = col_b.slider("Tolerancia de pendiente (±°)", 0.5, 5.0, 2.0, 0.5)
            tol_rel = col_c.slider("Tolerancia de relieve (±%)", 10, 60, 30, 5)
            seleccion = teselas if eleccion == TODAS else [eleccion]

            lat_r, lon_r = COORD_REF[id_ref]
            try:
                with st.spinner(f"Leyendo la referencia en {fuente} (internet; la primera vez "
                                f"puede tardar unos 20 s)…"):
                    ref_topo = referencia_topo(cuerpo, lat_r, lon_r)
            except Exception as e:
                ref_topo = None
                st.error(f"No pude leer {fuente} (¿hay internet?): {e}")

            if ref_topo is None:
                st.warning("Sin dato topográfico de la referencia.")
            else:
                conocidos = {perfiles[k]["nombre"]: v for k, v in obtener_coordenadas().items()
                             if k in perfiles}
                with st.spinner("Calculando ventanas de las zonas (la primera vez tarda)…"):
                    lista, resumen = buscar_en_teselas(seleccion, ventanas_tesela, ref_topo,
                                                       conocidos, tol_pend, tol_rel / 100)

                st.subheader(f"Referencia medida en {fuente} ({cuerpo})")
                r1, r2, r3 = st.columns(3)
                r1.metric("Pendiente mediana", f"{ref_topo['pend_mediana']:.1f}°")
                r2.metric("Relieve en la ventana", f"{ref_topo['relieve']:.0f} m")
                r3.metric("Elevación en el punto",
                          "sin dato" if ref_topo["elev_punto"] is None
                          else f"{ref_topo['elev_punto']:.0f} m")
                if cuerpo == "Luna":
                    st.caption(
                        f"Medida en la ventana de 10 × 10 km alrededor de {lat_r}, {lon_r}, "
                        f"coordenadas aproximadas de nuestro Excel: describe esa ventana, no "
                        f"necesariamente el rasgo completo. LOLA (118 m) se promedió a "
                        f"{ref_topo['resolucion_m']:.0f} m para acercarla a la escala de la "
                        f"Tierra procesada. La elevación lunar es relativa a una esfera de "
                        f"referencia, no al nivel del mar, y no se compara con la de la Tierra.")

                titulo = ("todas las zonas" if eleccion == TODAS
                          else f"la zona de {nombre_zona(eleccion)}")
                st.subheader(f"Resultado en {titulo}")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Ventanas evaluadas", sum(r["evaluadas"] for r in resumen))
                m2.metric("Excluidas por agua", sum(r["excluidas_agua"] for r in resumen))
                m3.metric("Ventanas que coinciden", sum(r["coinciden"] for r in resumen))
                m4.metric("Zonas", len(lista))

                sin_mascara = [n for n in seleccion if not Path(f"data/processed/{n}.swb").exists()]
                if sin_mascara:
                    st.warning(f"Sin máscara de agua (.swb) en "
                               f"{', '.join(nombre_zona(n) for n in sin_mascara)}: se usó "
                               f"una regla aproximada (más de la mitad de píxeles a 0 m).")
                pocas = [r["tesela"] for r in resumen if r["evaluadas"] < MIN_VENTANAS_TESELA]
                if pocas:
                    st.info(f"Zonas con muy pocas ventanas evaluables "
                            f"({', '.join(nombre_zona(p) for p in pocas)}): casi "
                            f"toda su superficie es agua o tiene huecos, así que su resultado "
                            f"casi no cuenta.")

                if len(seleccion) > 1:
                    df_res = pd.DataFrame(resumen)
                    df_res["tesela"] = df_res["tesela"].map(nombre_zona)
                    st.dataframe(df_res.rename(columns={
                        "tesela": "Zona de estudio", "evaluadas": "Ventanas evaluadas",
                        "excluidas_agua": "Excluidas por agua", "coinciden": "Coinciden",
                        "zonas": "Zonas"}), hide_index=True)

                mapa = crear_mapa_zonas(seleccion, lista, conocidos)
                st_folium(mapa, height=520, width=900, returned_objects=[])
                st.caption("Naranja: zonas nuevas, solo topografía · Naranja con línea "
                           "discontinua: zona extensa (50 ventanas o más: casi una tesela "
                           "entera) · Azul: análogo documentado · Gris: borde de la tesela. "
                           "Con varias teselas se añade un punto en el centro de cada zona.")

                nombre_arch = "todas" if eleccion == TODAS else eleccion
                if lista:
                    filas = [{
                        "Zona": z["id_zona"], "Tesela": z["tesela"],
                        "Distancia a la referencia": round(z["distancia"], 2),
                        "Ventanas": z["ventanas"],
                        "Aviso": ("zona extensa: la topografía no distingue aquí"
                                  if z["ventanas"] >= ZONA_EXTENSA else ""),
                        "Lat mín": round(z["lat_min"], 3), "Lat máx": round(z["lat_max"], 3),
                        "Lon mín": round(z["lon_min"], 3), "Lon máx": round(z["lon_max"], 3),
                        "Pendiente media (°)": round(z["pend_media"], 2),
                        "Relieve medio (m)": round(z["relieve_medio"]),
                        "Contiene análogo conocido": ", ".join(z["conocidos"]) or "ninguno",
                        "Referencia": ref["nombre"],
                        "Tolerancia pendiente (°)": tol_pend,
                        "Tolerancia relieve (%)": tol_rel,
                    } for z in lista]
                    df_z = pd.DataFrame(filas)
                    st.dataframe(df_z, hide_index=True)
                    st.caption("«Distancia a la referencia»: 0 = idéntica en pendiente y relieve; "
                               "cerca de 1 = en el borde de la tolerancia. Es una medida "
                               "definida por el equipo para ordenar las zonas, no una "
                               "probabilidad.")
                    st.download_button("Descargar zonas (.csv)",
                                       data=df_z.to_csv(index=False).encode("utf-8-sig"),
                                       file_name=f"zonas_{id_ref}_{nombre_arch}.csv",
                                       mime="text/csv")
                else:
                    st.info("Ninguna ventana coincide con estas tolerancias.")

                ficha = generar_informe_descubrimiento(
                    id_ref, ref, fuente, (lat_r, lon_r), ref_topo, seleccion, resumen, lista,
                    tol_pend, tol_rel, sin_mascara, ZONA_EXTENSA, NOTA)
                st.download_button("Descargar ficha del descubrimiento (.md)",
                                   data=ficha.encode("utf-8"),
                                   file_name=f"descubrimiento_{id_ref}_{nombre_arch}.md",
                                   mime="text/markdown")

            st.warning(
                "Límites que hay que tener presentes: (1) solo se compara topografía "
                "(pendiente mediana y relieve), no composición ni agua; (2) las tolerancias, el "
                "umbral de 5 % de agua y el umbral de zona extensa los definió el equipo, no "
                "son valores científicos; (3) con referencias llanas (Jezero, Gusev, Marius "
                "Hills) casi cualquier planicie coincide, y una zona de decenas de ventanas "
                "es una meseta, no un hallazgo; (4) solo se cubren las zonas descargadas; "
                "(5) los huecos entre pasadas de MOLA se rellenan por interpolación, así que "
                "las pendientes de Marte pueden salir algo suaves; (6) las escalas de Marte "
                "(463 m), la Luna (474 m) y la Tierra (463 m) son parecidas pero no idénticas.")

else:
    st.header(f"Informes: {ref['nombre']}")
    nombres = {f["id"]: f["nombre"] for f in tabla}
    id_c = st.selectbox("Candidato terrestre", list(nombres), format_func=lambda i: nombres[i])
    coords = obtener_coordenadas()
    res, mensaje = estado_topografia(id_c, coords)
    texto = generar_informe(id_ref, ref, id_c, perfiles[id_c], comparar(ref, perfiles[id_c]),
                            coords, res, mensaje, obtener_datos(), NOTA,
                            clima=obtener_clima().get(id_c))
    col1, col2 = st.columns(2)
    col1.download_button("Descargar ficha del candidato (.md)", data=texto.encode("utf-8"),
                         file_name=f"informe_{id_ref}_{id_c}.md", mime="text/markdown")
    ranking_csv = pd.DataFrame([{
        "Región de referencia": ref["nombre"],
        "Candidato": f["nombre"],
        "Criterios cumplidos": f["cumplidos"],
        "Criterios comparados": f["comparados"],
        "Criterios sin dato": len(CRITERIOS) - f["comparados"],
        "Índice de similitud (%)": f["indice"],
    } for f in tabla]).to_csv(index=False).encode("utf-8-sig")
    col2.download_button("Descargar ranking completo (.csv)", data=ranking_csv,
                         file_name=f"ranking_{id_ref}.csv", mime="text/csv")
    st.divider()
    st.markdown(texto)