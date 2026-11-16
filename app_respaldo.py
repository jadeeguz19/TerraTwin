
import re
from pathlib import Path

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from modules.estilos import aplicar_estilos
from modules.discovery import estadisticas_ventanas
from modules.discovery_ranking import buscar_en_teselas
from modules.discovery_report import generar_informe_descubrimiento
from modules.excel_reader import cargar_todo
from modules.map_visualization import coordenadas_analogos, crear_mapa
from modules.planetary_topography import ventana_luna, ventana_mola
from modules.report_generator import generar_informe
from modules.similarity_engine import (
    CRITERIOS, _texto, cargar_perfiles, comparar, ranking
)
from modules.topography import resumen_topografico, ruta_tesela


# =========================================================
# CONFIGURACIÓN GENERAL
# =========================================================

st.set_page_config(
    page_title="TerraTwin | Exploración planetaria",
    page_icon="🌌",
    layout="wide",
    initial_sidebar_state="expanded"
)

aplicar_estilos()

RUTA_MASCOTA = Path("assets/alien.jpeg")


# =========================================================
# IDENTIDAD VISUAL
# =========================================================

def encabezado(titulo, descripcion, etiqueta="TERRATWIN"):
    st.markdown(
        f"""
        <div class="tt-page-head">
            <div class="tt-eyebrow">{etiqueta}</div>
            <h1>{titulo}</h1>
            <p>{descripcion}</p>
        </div>
        """,
        unsafe_allow_html=True
    )


def separador():
    st.markdown(
        '<div class="tt-separator"></div>',
        unsafe_allow_html=True
    )


def tarjeta_texto(titulo, contenido):
    st.markdown(
        f"""
        <div class="tt-info-card">
            <div class="tt-card-title">{titulo}</div>
            <div class="tt-card-content">{contenido}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


# =========================================================
# CONFIGURACIÓN CIENTÍFICA
# =========================================================

COORD_REF = {
    "MAR-01": (18.4, 77.7),
    "MAR-02": (-5.44, 137.70),
    "MAR-03": (-14.53, 175.52),
    "LUN-09": (13.0, -53.0),
}

ZONA_EXTENSA = 50
MIN_VENTANAS_TESELA = 20
TODAS = "Todas las teselas"

NOTA = (
    "El índice es una medida definida por el algoritmo de TerraTwin: "
    "criterios cumplidos entre los criterios comparables. No es una "
    "probabilidad ni prueba de que un lugar sea un análogo validado. "
    "«Sin dato» significa no documentado en nuestra base, no ausente."
)


# =========================================================
# CARGA DE DATOS
# =========================================================

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
    """Carga estimaciones climáticas de NASA POWER."""

    ruta = Path("data/clima_analogos.csv")

    if not ruta.exists():
        return {}

    df = pd.read_csv(ruta, encoding="utf-8-sig")
    clima = {}

    for _, f in df.iterrows():

        def v(col):
            if col not in df.columns or pd.isna(f[col]):
                return None
            return float(f[col])

        clima[f["id"]] = {
            "t2m_c": v("t2m_c"),
            "prec_mm_anio": v("prec_mm_anio"),
            "rh2m_pct": v("rh2m_pct"),
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
    if cuerpo == "Luna":
        return ventana_luna(lat, lon)
    return ventana_mola(lat, lon)


# =========================================================
# FUNCIONES DE MAPAS Y TOPOGRAFÍA
# =========================================================

def teselas_disponibles():
    return sorted(
        p.stem.upper()
        for p in Path("data/processed").glob("*.hgt")
    )


def limites_tesela(nombre):
    m = re.fullmatch(r"([NS])(\d+)([EW])(\d+)", nombre)

    lat = int(m.group(2)) * (
        1 if m.group(1) == "N" else -1
    )

    lon = int(m.group(4)) * (
        1 if m.group(3) == "E" else -1
    )

    return [
        [lat, lon],
        [lat + 1, lon + 1]
    ]


def crear_mapa_zonas(nombres_teselas, lista_zonas, conocidos):

    limites = {
        n: limites_tesela(n)
        for n in nombres_teselas
    }

    mapa = folium.Map(tiles="OpenStreetMap")

    for n, lim in limites.items():
        folium.Rectangle(
            lim,
            color="gray",
            weight=1,
            fill=False,
            tooltip=f"Tesela NASADEM {n}"
        ).add_to(mapa)

    varias = len(nombres_teselas) > 1

    for z in lista_zonas:

        extensa = z["ventanas"] >= ZONA_EXTENSA

        etiqueta = (
            f"Zona {z['id_zona']} · nueva, solo topografía · "
            f"distancia {z['distancia']:.2f} · "
            f"{z['ventanas']} ventanas · "
            f"pendiente {z['pend_media']:.1f}° · "
            f"relieve {z['relieve_medio']:.0f} m"
            + (" · ZONA EXTENSA" if extensa else "")
        )

        folium.Rectangle(
            [
                [z["lat_min"], z["lon_min"]],
                [z["lat_max"], z["lon_max"]]
            ],
            color="orange",
            weight=2,
            fill=True,
            fill_opacity=0.12 if extensa else 0.35,
            dash_array="6,6" if extensa else None,
            tooltip=etiqueta,
            popup=etiqueta
        ).add_to(mapa)

        if varias:
            folium.CircleMarker(
                [
                    (z["lat_min"] + z["lat_max"]) / 2,
                    (z["lon_min"] + z["lon_max"]) / 2
                ],
                radius=5,
                color="orange",
                fill=True,
                fill_opacity=0.9,
                tooltip=etiqueta
            ).add_to(mapa)

    for nombre, (la, lo) in conocidos.items():

        for lim in limites.values():

            if (
                lim[0][0] <= la <= lim[1][0]
                and lim[0][1] <= lo <= lim[1][1]
            ):

                folium.CircleMarker(
                    [la, lo],
                    radius=7,
                    color="blue",
                    fill=True,
                    fill_opacity=0.8,
                    tooltip=f"Análogo documentado: {nombre}"
                ).add_to(mapa)

                break

    sur = min(l[0][0] for l in limites.values())
    oeste = min(l[0][1] for l in limites.values())
    norte = max(l[1][0] for l in limites.values())
    este = max(l[1][1] for l in limites.values())

    mapa.fit_bounds([
        [sur, oeste],
        [norte, este]
    ])

    return mapa


def estado_topografia(id_c, coords):

    if id_c not in coords:
        return None, "Sin coordenadas válidas para este candidato."

    lat, lon = coords[id_c]

    if lat > 60 or lat < -56:
        return None, (
            "Sin dato topográfico: este sitio está fuera de la "
            "cobertura de NASADEM (60° N a 56° S)."
        )

    nombre, ruta = ruta_tesela(lat, lon)

    if not ruta.exists():
        return None, (
            f"Sin dato topográfico: la tesela NASADEM {nombre} "
            "aún no se ha incorporado en esta versión."
        )

    res = topografia(str(ruta), lat, lon)

    if res is None:
        return None, "Sin dato topográfico válido en esta zona."

    return res, None


# =========================================================
# CARGA INICIAL
# =========================================================

perfiles = obtener_perfiles()

referencias = {
    pid: f"{p['nombre']} ({p['cuerpo']})"
    for pid, p in perfiles.items()
    if p["cuerpo"] != "Tierra"
}


# =========================================================
# BARRA LATERAL
# =========================================================

st.sidebar.markdown(
    """
    <div class="tt-brand">
        <div class="tt-brand-icon">✦</div>
        <div>
            <div class="tt-brand-name">TerraTwin</div>
            <div class="tt-brand-subtitle">PLANETARY EXPLORATION</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

if RUTA_MASCOTA.exists():
    st.sidebar.image(
        str(RUTA_MASCOTA),
        width=145
    )

st.sidebar.markdown("---")

st.sidebar.markdown(
    '<div class="tt-sidebar-label">NAVEGACIÓN</div>',
    unsafe_allow_html=True
)

seccion = st.sidebar.radio(
    "Sección",
    [
        "Inicio",
        "Explorador",
        "Mapa",
        "Análisis",
        "Descubrimiento",
        "Informes"
    ],
    label_visibility="collapsed"
)

st.sidebar.markdown("---")

st.sidebar.markdown(
    '<div class="tt-sidebar-label">REGIÓN DE REFERENCIA</div>',
    unsafe_allow_html=True
)

id_ref = st.sidebar.selectbox(
    "Seleccionar región",
    list(referencias),
    format_func=lambda i: referencias[i],
    label_visibility="collapsed"
)

ref = perfiles[id_ref]
tabla = ranking(perfiles, id_ref)

st.sidebar.markdown("---")

st.sidebar.caption(
    "TerraTwin · Herramienta de exploración "
    "y comparación planetaria"
)


# =========================================================
# INICIO
# =========================================================

if seccion == "Inicio":

    col_hero, col_mascota = st.columns(
        [3.2, 1],
        vertical_alignment="center"
    )

    with col_hero:

        st.markdown(
            """
            <div class="tt-hero">
                <div class="tt-hero-eyebrow">
                    EXPLORACIÓN PLANETARIA · ASTRALLIS
                </div>

                <h1>Explora otros mundos.<br>
                Encuentra conexiones en la Tierra.</h1>

                <p>
                    Una herramienta para comparar regiones de Marte y la Luna
                    con lugares terrestres documentados como posibles análogos,
                    a partir de características con fuente.
                </p>

                <div class="tt-hero-tag">
                    MARS &nbsp; · &nbsp; MOON &nbsp; · &nbsp; EARTH
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col_mascota:

        if RUTA_MASCOTA.exists():
            st.image(
                str(RUTA_MASCOTA),
                use_container_width=True
            )
        else:
            st.markdown(
                """
                <div class="tt-info-card">
                    <div class="tt-card-title">¡Bienvenido!</div>
                    <div class="tt-card-content">
                        Tu exploración planetaria comienza aquí.
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

    st.markdown("### Panel de exploración")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric(
            "Región de referencia",
            ref["nombre"]
        )

    with c2:
        st.metric(
            "Análogos documentados",
            len(tabla)
        )

    with c3:
        st.metric(
            "Criterios de comparación",
            len(CRITERIOS)
        )

    separador()

    st.markdown("### ¿Qué puedes explorar?")

    a, b, c = st.columns(3)

    with a:
        tarjeta_texto(
            "01 · Explorador",
            "Consulta perfiles de regiones y compara "
            "análogos terrestres documentados."
        )

    with b:
        tarjeta_texto(
            "02 · Análisis",
            "Examina criterios compartidos, contexto "
            "topográfico y estimaciones climáticas."
        )

    with c:
        tarjeta_texto(
            "03 · Descubrimiento",
            "Busca zonas terrestres con características "
            "topográficas similares a una región de referencia."
        )

    separador()

    st.markdown("### Región seleccionada")

    st.info(
        f"Actualmente estás explorando **{ref['nombre']}**, "
        f"ubicada en {ref['cuerpo']}. Puedes cambiar la región "
        "desde el selector de la barra lateral."
    )

    st.markdown("### Alcance científico")

    st.warning(
        "Esta versión contiene un ranking de 10 análogos terrestres "
        "documentados, no una búsqueda global. La sección Descubrimiento "
        "compara únicamente topografía y cubre las teselas descargadas. "
        "Los resultados no constituyen una validación definitiva "
        "de analogía planetaria."
    )


# =========================================================
# EXPLORADOR
# =========================================================

elif seccion == "Explorador":

    encabezado(
        "Explorador de regiones",
        "Consulta las características de una región de referencia "
        "y examina sus posibles análogos terrestres.",
        "EXPLORACIÓN"
    )

    st.markdown(
        f"### Región de referencia: **{ref['nombre']}**"
    )

    st.caption(
        f"Cuerpo celeste: {ref['cuerpo']} · ID: {id_ref}"
    )

    separador()

    st.markdown("### Perfil de la región")

    perfil_df = pd.DataFrame([
        {
            "Característica": etiqueta,
            "Valor": _texto(ref[clave])
        }
        for clave, etiqueta, _ in CRITERIOS
    ])

    st.dataframe(
        perfil_df,
        hide_index=True,
        use_container_width=True
    )

    separador()

    st.markdown("### Ranking de análogos terrestres documentados")

    ranking_df = pd.DataFrame([
        {
            "Candidato": f["nombre"],
            "Criterios cumplidos": (
                f"{f['cumplidos']} de {f['comparados']}"
            ),
            "Índice de similitud (%)": f["indice"],
            "Criterios sin dato": (
                len(CRITERIOS) - f["comparados"]
            )
        }
        for f in tabla
    ])

    st.dataframe(
        ranking_df,
        hide_index=True,
        use_container_width=True
    )

    st.caption(NOTA)


# =========================================================
# MAPA
# =========================================================

elif seccion == "Mapa":

    encabezado(
        "Mapa de análogos",
        f"Distribución geográfica de los análogos terrestres "
        f"frente a {ref['nombre']}.",
        "VISUALIZACIÓN GEOGRÁFICA"
    )

    coords = obtener_coordenadas()
    mapa = crear_mapa(tabla, coords)

    st.markdown("### Distribución de candidatos")

    st_folium(
        mapa,
        height=570,
        width=900,
        returned_objects=[]
    )

    faltan = [
        f["nombre"]
        for f in tabla
        if f["id"] not in coords
    ]

    if faltan:
        st.warning(
            f"Sin coordenadas válidas: {', '.join(faltan)}"
        )

    separador()

    st.markdown("### Leyenda e interpretación")

    st.caption(
        "Verde: 75 % o más · Naranja: 50–74 % · "
        "Rojo: menos de 50 % · Gris: sin criterios comparables. "
        "Los cortes solo sirven para visualizar."
    )

    st.info(
        "La región de referencia (Marte o Luna) no se dibuja aquí: "
        "este es un mapa de la Tierra y no debe usarse como "
        "cartografía de otros cuerpos."
    )

    st.caption(NOTA)


# =========================================================
# ANÁLISIS
# =========================================================

elif seccion == "Análisis":

    encabezado(
        "Análisis comparativo",
        f"Examina las diferencias y similitudes entre "
        f"{ref['nombre']} y un candidato terrestre.",
        "ANÁLISIS CIENTÍFICO"
    )

    nombres = {
        f["id"]: f["nombre"]
        for f in tabla
    }

    id_c = st.selectbox(
        "Selecciona un candidato terrestre",
        list(nombres),
        format_func=lambda i: nombres[i]
    )

    r = comparar(ref, perfiles[id_c])

    st.markdown("### Comparación de regiones")

    st.write(
        f"**{ref['nombre']}** frente a **{nombres[id_c]}**: "
        f"{r['cumplidos']} de {r['comparados']} "
        "criterios cumplidos."
    )

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "Criterios cumplidos",
            f"{r['cumplidos']} / {r['comparados']}"
        )

    with col2:
        st.metric(
            "Criterios sin dato",
            len(CRITERIOS) - r["comparados"]
        )

    detalle_df = pd.DataFrame(
        r["detalle"]
    ).rename(columns={
        "criterio": "Criterio",
        "referencia": "Referencia",
        "candidato": "Candidato",
        "en_comun": "En común",
        "estado": "Estado"
    })

    st.dataframe(
        detalle_df,
        hide_index=True,
        use_container_width=True
    )

    st.caption(NOTA)

    separador()

    # TOPOGRAFÍA

    st.markdown("### Contexto topográfico medido")
    st.caption("Fuente: NASADEM · Mediciones terrestres")

    coords = obtener_coordenadas()
    res, mensaje = estado_topografia(id_c, coords)

    if res is None:

        st.info(mensaje)

    else:

        lat, lon = coords[id_c]

        c1, c2, c3, c4 = st.columns(4)

        punto = res["elev_punto"]

        c1.metric(
            "Elevación en el punto",
            "sin dato" if punto is None else f"{punto:.0f} m"
        )

        c2.metric(
            "Rango de elevación",
            f"{res['elev_min']:.0f}–{res['elev_max']:.0f} m"
        )

        c3.metric(
            "Pendiente media",
            f"{res['pend_media']:.1f}°"
        )

        c4.metric(
            "Zona con pendiente < 5°",
            f"{res['pct_suave']:.0f} %"
        )

        if res["pct_validos"] < 99.5:

            st.warning(
                f"Solo el {res['pct_validos']:.0f} % de la ventana "
                "tiene dato. El resto queda fuera de la tesela "
                "descargada o sin medición."
            )

        st.caption(
            f"Fuente: NASADEM (NASA LP DAAC), resolución de "
            f"1 segundo de arco (unos 30 m). Ventana de unos "
            f"{res['ventana_km']} × {res['ventana_km']} km "
            f"alrededor de {lat:.4f}, {lon:.4f}; relieve local "
            f"de {res['relieve']:.0f} m; "
            f"{res['pct_validos']:.0f} % de la ventana con dato. "
            "Es una medición de la Tierra: para compararla con "
            "otros cuerpos se usa la sección Descubrimiento, "
            "a la misma escala. Este panel no entra en el "
            "índice de similitud."
        )

    separador()

    # CLIMA

    st.markdown("### Clima estimado")
    st.caption("Fuente: NASA POWER")

    cl = obtener_clima().get(id_c)

    if not cl:

        st.info(
            "Sin dato climático para este candidato."
        )

    else:

        k1, k2, k3 = st.columns(3)

        k1.metric(
            "Temperatura media anual",
            "sin dato" if cl["t2m_c"] is None
            else f"{cl['t2m_c']:.1f} °C"
        )

        k2.metric(
            "Precipitación anual",
            "sin dato" if cl["prec_mm_anio"] is None
            else f"{cl['prec_mm_anio']:.0f} mm/año"
        )

        k3.metric(
            "Humedad relativa media",
            "sin dato" if cl["rh2m_pct"] is None
            else f"{cl['rh2m_pct']:.0f} %"
        )

        st.caption(
            f"Fuente: {cl['fuente']}; consultado el "
            f"{cl['consultado']}. Es un estimado de reanálisis "
            "de resolución gruesa (decenas de km): describe "
            "la zona, no el punto exacto, y en sitios de gran "
            "relieve puede diferir mucho del punto. Cubre "
            "también los sitios fuera de NASADEM. No entra "
            "en el índice de similitud y no se compara con "
            "la temperatura de Marte o la Luna: sus atmósferas "
            "y presiones son muy distintas."
        )


# =========================================================
# DESCUBRIMIENTO
# =========================================================

elif seccion == "Descubrimiento":

    cuerpo = ref["cuerpo"]
    fuente = "LOLA" if cuerpo == "Luna" else "MOLA"

    encabezado(
        "Descubrimiento topográfico",
        f"Busca zonas terrestres con pendiente y relieve "
        f"similares a los medidos en {ref['nombre']}.",
        "BÚSQUEDA DE ZONAS"
    )

    st.info(
        f"Referencia: **{ref['nombre']}** · "
        f"Fuente topográfica: **{fuente} ({cuerpo})**"
    )

    st.write(
        "Busca zonas de la Tierra cuya pendiente y relieve "
        f"se parecen a los medidos en la región de referencia "
        f"({fuente}, {cuerpo}), comparados a la misma escala "
        "(~470 m por píxel). Son zonas **nuevas, solo topografía**: "
        "no tienen análisis de composición ni son análogos validados."
    )

    separador()

    if id_ref not in COORD_REF:

        st.warning(
            "Esta región de referencia aún no tiene topografía "
            "medida en TerraTwin. Elige Jezero, Gale, Gusev "
            "o Marius Hills en la barra lateral."
        )

    else:

        teselas = teselas_disponibles()

        if not teselas:

            st.info(
                "No hay teselas NASADEM en data/processed."
            )

        else:

            st.markdown("### Parámetros de búsqueda")

            col_a, col_b, col_c = st.columns(3)

            eleccion = col_a.selectbox(
                "Tesela NASADEM",
                teselas + [TODAS]
            )

            tol_pend = col_b.slider(
                "Tolerancia de pendiente (±°)",
                0.5, 5.0, 2.0, 0.5
            )

            tol_rel = col_c.slider(
                "Tolerancia de relieve (±%)",
                10, 60, 30, 5
            )

            seleccion = (
                teselas
                if eleccion == TODAS
                else [eleccion]
            )

            lat_r, lon_r = COORD_REF[id_ref]

            try:

                with st.spinner(
                    f"Leyendo la referencia en {fuente}..."
                ):

                    ref_topo = referencia_topo(
                        cuerpo,
                        lat_r,
                        lon_r
                    )

            except Exception as e:

                ref_topo = None

                st.error(
                    f"No pude leer {fuente} "
                    f"(¿hay internet?): {e}"
                )

            if ref_topo is None:

                st.warning(
                    "Sin dato topográfico de la referencia."
                )

            else:

                conocidos = {
                    perfiles[k]["nombre"]: v
                    for k, v in obtener_coordenadas().items()
                    if k in perfiles
                }

                with st.spinner(
                    "Calculando ventanas de las teselas..."
                ):

                    lista, resumen = buscar_en_teselas(
                        seleccion,
                        ventanas_tesela,
                        ref_topo,
                        conocidos,
                        tol_pend,
                        tol_rel / 100
                    )

                separador()

                st.markdown(
                    f"### Referencia medida en {fuente}"
                )

                r1, r2, r3 = st.columns(3)

                r1.metric(
                    "Pendiente mediana",
                    f"{ref_topo['pend_mediana']:.1f}°"
                )

                r2.metric(
                    "Relieve en la ventana",
                    f"{ref_topo['relieve']:.0f} m"
                )

                r3.metric(
                    "Elevación en el punto",
                    "sin dato"
                    if ref_topo["elev_punto"] is None
                    else f"{ref_topo['elev_punto']:.0f} m"
                )

                if cuerpo == "Luna":

                    st.caption(
                        f"Medida en la ventana de 10 × 10 km "
                        f"alrededor de {lat_r}, {lon_r}, "
                        "coordenadas aproximadas de nuestro Excel: "
                        "describe esa ventana, no necesariamente "
                        "el rasgo completo. LOLA (118 m) se "
                        f"promedió a {ref_topo['resolucion_m']:.0f} m "
                        "para acercarla a la escala de la Tierra "
                        "procesada. La elevación lunar es relativa "
                        "a una esfera de referencia, no al nivel "
                        "del mar, y no se compara con la de la Tierra."
                    )

                titulo = (
                    "todas las teselas"
                    if eleccion == TODAS
                    else f"la tesela {eleccion}"
                )

                separador()

                st.markdown(
                    f"### Resultados en {titulo}"
                )

                m1, m2, m3, m4 = st.columns(4)

                m1.metric(
                    "Ventanas evaluadas",
                    sum(r["evaluadas"] for r in resumen)
                )

                m2.metric(
                    "Excluidas por agua",
                    sum(r["excluidas_agua"] for r in resumen)
                )

                m3.metric(
                    "Ventanas que coinciden",
                    sum(r["coinciden"] for r in resumen)
                )

                m4.metric(
                    "Zonas encontradas",
                    len(lista)
                )

                sin_mascara = [
                    n for n in seleccion
                    if not Path(
                        f"data/processed/{n}.swb"
                    ).exists()
                ]

                if sin_mascara:

                    st.warning(
                        f"Sin máscara de agua (.swb) en "
                        f"{', '.join(sin_mascara)}: se usó una "
                        "regla aproximada (más de la mitad "
                        "de píxeles a 0 m)."
                    )

                pocas = [
                    r["tesela"]
                    for r in resumen
                    if r["evaluadas"] < MIN_VENTANAS_TESELA
                ]

                if pocas:

                    st.info(
                        f"Teselas con muy pocas ventanas "
                        f"evaluables ({', '.join(pocas)}): casi "
                        "toda su superficie es agua o tiene "
                        "huecos, así que su resultado casi no cuenta."
                    )

                if len(seleccion) > 1:

                    st.markdown(
                        "### Resumen por tesela"
                    )

                    st.dataframe(
                        pd.DataFrame(resumen).rename(
                            columns={
                                "tesela": "Tesela",
                                "evaluadas": "Ventanas evaluadas",
                                "excluidas_agua": "Excluidas por agua",
                                "coinciden": "Coinciden",
                                "zonas": "Zonas"
                            }
                        ),
                        hide_index=True,
                        use_container_width=True
                    )

                separador()

                st.markdown("### Mapa de zonas identificadas")

                mapa = crear_mapa_zonas(
                    seleccion,
                    lista,
                    conocidos
                )

                st_folium(
                    mapa,
                    height=570,
                    width=900,
                    returned_objects=[]
                )

                st.caption(
                    "Naranja: zonas nuevas, solo topografía · "
                    "Naranja con línea discontinua: zona extensa "
                    "(50 ventanas o más: casi una tesela entera) · "
                    "Azul: análogo documentado · "
                    "Gris: borde de la tesela. Con varias teselas "
                    "se añade un punto en el centro de cada zona."
                )

                nombre_arch = (
                    "todas"
                    if eleccion == TODAS
                    else eleccion
                )

                if lista:

                    st.markdown(
                        "### Detalle de zonas encontradas"
                    )

                    filas = [
                        {
                            "Zona": z["id_zona"],
                            "Tesela": z["tesela"],
                            "Distancia a la referencia": round(
                                z["distancia"], 2
                            ),
                            "Ventanas": z["ventanas"],
                            "Aviso": (
                                "zona extensa: la topografía "
                                "no distingue aquí"
                                if z["ventanas"] >= ZONA_EXTENSA
                                else ""
                            ),
                            "Lat mín": round(z["lat_min"], 3),
                            "Lat máx": round(z["lat_max"], 3),
                            "Lon mín": round(z["lon_min"], 3),
                            "Lon máx": round(z["lon_max"], 3),
                            "Pendiente media (°)": round(
                                z["pend_media"], 2
                            ),
                            "Relieve medio (m)": round(
                                z["relieve_medio"]
                            ),
                            "Contiene análogo conocido": (
                                ", ".join(z["conocidos"])
                                or "ninguno"
                            ),
                            "Referencia": ref["nombre"],
                            "Tolerancia pendiente (°)": tol_pend,
                            "Tolerancia relieve (%)": tol_rel,
                        }
                        for z in lista
                    ]

                    df_z = pd.DataFrame(filas)

                    st.dataframe(
                        df_z,
                        hide_index=True,
                        use_container_width=True
                    )

                    st.caption(
                        "«Distancia a la referencia»: 0 = idéntica "
                        "en pendiente y relieve; cerca de 1 = en "
                        "el borde de la tolerancia. Es una medida "
                        "definida por el equipo para ordenar las "
                        "zonas, no una probabilidad."
                    )

                    col_descarga1, col_descarga2 = st.columns(2)

                    with col_descarga1:

                        st.download_button(
                            "Descargar zonas (.csv)",
                            data=df_z.to_csv(
                                index=False
                            ).encode("utf-8-sig"),
                            file_name=(
                                f"zonas_{id_ref}_{nombre_arch}.csv"
                            ),
                            mime="text/csv",
                            use_container_width=True
                        )

                else:

                    st.info(
                        "Ninguna ventana coincide con estas tolerancias."
                    )

                ficha = generar_informe_descubrimiento(
                    id_ref,
                    ref,
                    fuente,
                    (lat_r, lon_r),
                    ref_topo,
                    seleccion,
                    resumen,
                    lista,
                    tol_pend,
                    tol_rel,
                    sin_mascara,
                    ZONA_EXTENSA,
                    NOTA
                )

                st.download_button(
                    "Descargar ficha del descubrimiento (.md)",
                    data=ficha.encode("utf-8"),
                    file_name=(
                        f"descubrimiento_{id_ref}_{nombre_arch}.md"
                    ),
                    mime="text/markdown",
                    use_container_width=True
                )

            separador()

            st.markdown("### Limitaciones de esta búsqueda")

            st.warning(
                "Límites que hay que tener presentes: "
                "(1) solo se compara topografía (pendiente mediana "
                "y relieve), no composición ni agua; "
                "(2) las tolerancias, el umbral de 5 % de agua "
                "y el umbral de zona extensa los definió el equipo, "
                "no son valores científicos; "
                "(3) con referencias llanas (Jezero, Gusev, "
                "Marius Hills) casi cualquier planicie coincide, "
                "y una zona de decenas de ventanas es una meseta, "
                "no un hallazgo; "
                "(4) solo se cubren las teselas descargadas; "
                "(5) los huecos entre pasadas de MOLA se rellenan "
                "por interpolación, así que las pendientes de Marte "
                "pueden salir algo suaves; "
                "(6) las escalas de Marte (463 m), la Luna (474 m) "
                "y la Tierra (463 m) son parecidas pero no idénticas."
            )


# =========================================================
# INFORMES
# =========================================================

else:

    encabezado(
        "Informes científicos",
        "Genera fichas de candidatos y descarga el ranking "
        "de análogos correspondiente a la región seleccionada.",
        "DOCUMENTACIÓN"
    )

    nombres = {
        f["id"]: f["nombre"]
        for f in tabla
    }

    id_c = st.selectbox(
        "Selecciona un candidato terrestre",
        list(nombres),
        format_func=lambda i: nombres[i]
    )

    coords = obtener_coordenadas()

    res, mensaje = estado_topografia(
        id_c,
        coords
    )

    texto = generar_informe(
        id_ref,
        ref,
        id_c,
        perfiles[id_c],
        comparar(ref, perfiles[id_c]),
        coords,
        res,
        mensaje,
        obtener_datos(),
        NOTA,
        clima=obtener_clima().get(id_c)
    )

    separador()

    st.markdown("### Descargas disponibles")

    col1, col2 = st.columns(2)

    with col1:

        st.download_button(
            "Descargar ficha del candidato (.md)",
            data=texto.encode("utf-8"),
            file_name=f"informe_{id_ref}_{id_c}.md",
            mime="text/markdown",
            use_container_width=True
        )

    ranking_csv = pd.DataFrame([
        {
            "Región de referencia": ref["nombre"],
            "Candidato": f["nombre"],
            "Criterios cumplidos": f["cumplidos"],
            "Criterios comparados": f["comparados"],
            "Criterios sin dato": (
                len(CRITERIOS) - f["comparados"]
            ),
            "Índice de similitud (%)": f["indice"],
        }
        for f in tabla
    ]).to_csv(
        index=False
    ).encode("utf-8-sig")

    with col2:

        st.download_button(
            "Descargar ranking completo (.csv)",
            data=ranking_csv,
            file_name=f"ranking_{id_ref}.csv",
            mime="text/csv",
            use_container_width=True
        )

    separador()

    st.markdown("### Vista previa del informe")

    st.markdown(texto)
