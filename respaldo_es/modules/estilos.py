from html import escape
from pathlib import Path

import streamlit as st

from modules.similarity_engine import _texto

# Si tu logo ya incluye el nombre "TerraTwin", pon True para ocultar el texto de arriba.
LOGO_REEMPLAZA_TEXTO = False

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap');
html { font-size: 18px; }  /* base más grande: todo lo que usa rem crece con esto */
html, body, .stApp { font-family: 'Poppins', 'Source Sans 3', sans-serif; }
.stApp {
  color: #e9e6ff;
  background: radial-gradient(1100px 560px at 85% -10%, #2c1685 0%, rgba(44,22,133,0) 60%),
              linear-gradient(180deg, #07041a 0%, #0c0730 55%, #150a45 100%);
}
[data-testid="stHeader"] { background: transparent; }
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #0b0629 0%, #1a0f55 100%);
  border-right: 1px solid #2c2190;
}
[data-testid="stSidebar"][aria-expanded="true"] { min-width: 310px; }

/* Texto: se fuerza para que se vea sobre el fondo oscuro */
.stApp h1 { font-size: 2.6rem !important; }
.stApp h2 { font-size: 2.0rem !important; }
.stApp h3 { font-size: 1.6rem !important; }
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5 { color: #ffffff !important; font-weight: 700; }
.stApp p, .stApp li, .stApp label, .stApp td, .stApp th,
.stApp [data-testid="stMarkdownContainer"] { color: #e9e6ff !important; font-size: 1.05rem; }
.stApp [data-testid="stCaptionContainer"], .stApp [data-testid="stCaptionContainer"] * {
  color: #c9c2ff !important; font-size: 0.95rem !important; }
.stApp [data-testid="stMetricValue"], .stApp [data-testid="stMetricValue"] * {
  color: #ffffff !important; font-size: 2.3rem !important; }
.stApp [data-testid="stMetricLabel"], .stApp [data-testid="stMetricLabel"] * {
  color: #c9c2ff !important; font-size: 1rem !important; }
[data-testid="stSidebar"] label, [data-testid="stSidebar"] p,
[data-testid="stSidebar"] [role="radiogroup"] label * { color: #e9e6ff !important; font-size: 1.1rem !important; }
.stApp table { background: transparent; }
.stApp [data-testid="stAlert"] * { font-size: 1.05rem !important; }

/* Selectores */
.stApp [data-baseweb="select"] > div { background: #1a1250 !important; border: 1px solid #3a2fc9 !important; }
.stApp [data-baseweb="select"] * { color: #ffffff !important; font-size: 1.05rem !important; }

[data-testid="stMetric"] {
  background: rgba(26, 15, 85, 0.55);
  border: 1.5px solid #3a2fc9;
  border-radius: 20px;
  padding: 14px 20px;
}
[data-testid="stDataFrame"] { border: 1.5px solid #3a2fc9; border-radius: 16px; overflow: hidden; }
[data-testid="stAlert"] { border-radius: 16px; }
.stButton > button, .stDownloadButton > button {
  background: linear-gradient(90deg, #6d28d9, #4f46e5);
  color: #ffffff !important;
  border: 0;
  border-radius: 999px;
  padding: 0.6rem 1.6rem;
  font-weight: 600;
  font-size: 1.05rem;
}
.stButton > button *, .stDownloadButton > button * { color: #ffffff !important; font-size: 1.05rem !important; }

[data-testid="stSidebar"] [role="radiogroup"] { gap: 6px; }
[data-testid="stSidebar"] [role="radiogroup"] > label {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid transparent;
  border-radius: 12px;
  padding: 10px 14px;
}
[data-testid="stSidebar"] [role="radiogroup"] > label:hover { background: rgba(124, 92, 255, 0.18); }
[data-testid="stSidebar"] [role="radiogroup"] > label:has(input:checked) {
  background: rgba(124, 92, 255, 0.28);
  border-color: #7c5cff;
}

/* Componentes propios */
.tt-brand { padding: 6px 0 10px 0; }
.tt-star { color: #ffffff !important; font-size: 1.5rem; }
.tt-brand-name { color: #ffffff !important; font-size: 1.7rem; font-weight: 700; }
.tt-side-label { color: #c4a8ff !important; font-size: .85rem; letter-spacing: .16em; font-weight: 700; margin: 14px 0 6px 0; }
.tt-kicker { color: #c4a8ff !important; font-size: .85rem; letter-spacing: .18em; font-weight: 600; }
.tt-hero {
  background: linear-gradient(135deg, rgba(60,30,140,.75), rgba(14,10,60,.85));
  border: 1.5px solid #5b46e0;
  border-radius: 28px;
  padding: 34px 40px;
}
.tt-hero h1 { color: #ffffff !important; font-size: 3rem !important; line-height: 1.15; margin: .4rem 0 1rem 0; }
.tt-hero p { color: #e9e6ff !important; font-size: 1.2rem !important; }
.tt-card {
  background: rgba(20, 12, 70, 0.55);
  border: 2px solid #3a2fc9;
  border-radius: 28px;
  padding: 20px 26px;
  margin-bottom: 14px;
}
.tt-card h2 { color: #ffffff !important; margin: .4rem 0 .2rem 0; }
.tt-card, .tt-card div { color: #e9e6ff !important; font-size: 1.1rem; }
.tt-card b, .tt-mini b { color: #ffffff !important; }
.tt-tag {
  display: inline-block;
  background: #6d4aff;
  color: #ffffff !important;
  border-radius: 999px;
  padding: 3px 14px;
  font-size: .95rem;
  font-weight: 600;
  margin-right: 6px;
}
.tt-item { display: flex; gap: 16px; align-items: flex-start; padding: 14px 0; }
.tt-item + .tt-item { border-top: 1px solid rgba(91, 70, 224, .35); }
.tt-num {
  min-width: 46px; height: 46px; border-radius: 50%;
  background: #5b2fd6; color: #ffffff !important; font-weight: 700; font-size: 1.2rem;
  display: flex; align-items: center; justify-content: center;
}
.tt-sub { color: #d4cfff !important; font-size: 1rem !important; margin-top: 4px; }
.tt-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 12px; }
.tt-mini {
  background: rgba(20, 12, 70, 0.55);
  border: 1.5px solid #3a2fc9;
  border-radius: 20px;
  padding: 18px 22px;
}
.tt-mini b { font-size: 1.15rem; }
.tt-mini p { color: #e2deff !important; font-size: 1rem !important; margin: 6px 0 0 0; }
.stApp h3.tt-acento, .tt-acento { color: #ff7a7f !important; }
</style>
"""


def aplicar_estilos():
    st.markdown(CSS, unsafe_allow_html=True)


def _buscar(patron):
    """Busca una imagen cuyo nombre contenga 'patron' en las carpetas habituales del proyecto."""
    for carpeta in ("assets", "imagenes", "img", "static", "data", "."):
        for ruta in sorted(Path(carpeta).glob(f"*{patron}*")):
            if ruta.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                return ruta
    return None


def buscar_imagen():
    """Imagen del alien."""
    return _buscar("alien")


def buscar_logo():
    """Logo del equipo/proyecto."""
    return _buscar("logo")


def marca_lateral(imagen=None):
    """Barra lateral: logo arriba, nombre y, debajo, el alien."""
    logo = buscar_logo()
    if logo:
        st.sidebar.image(str(logo))
    if not (logo and LOGO_REEMPLAZA_TEXTO):
        st.sidebar.markdown(
            "<div class='tt-brand'><div class='tt-star'>✦</div>"
            "<div class='tt-brand-name'>TerraTwin</div>"
            "<div class='tt-kicker'>PLANETARY EXPLORATION</div></div>",
            unsafe_allow_html=True)
    if imagen:
        st.sidebar.image(str(imagen))


def etiqueta_lateral(texto):
    st.sidebar.markdown(f"<div class='tt-side-label'>{escape(texto)}</div>",
                        unsafe_allow_html=True)


def hero(lineas_titulo, texto, etiquetas=()):
    """Tarjeta de portada (HTML en una sola línea, para que Markdown no lo tome como código)."""
    titulo = "<br>".join(escape(l) for l in lineas_titulo)
    tags = "".join(f"<span class='tt-tag'>{escape(e)}</span>" for e in etiquetas)
    return ("<div class='tt-hero'>"
            "<div class='tt-kicker'>EXPLORACIÓN PLANETARIA · ASTRALLIS</div>"
            f"<h1>{titulo}</h1>"
            f"<p>{escape(texto)}</p>"
            f"<div>{tags}</div></div>")


def tarjeta_region(nombre, cuerpo, descripcion=None):
    extra = f"<p class='tt-sub'>{escape(descripcion)}</p>" if descripcion else ""
    return ("<div class='tt-card'>"
            "<span class='tt-tag'>Región seleccionada</span>"
            f"<h2>{escape(nombre)}</h2>"
            f"<div>📍 {escape(cuerpo)}</div>" + extra + "</div>")


def tarjetas(items):
    """items = [(título, descripción), ...] en una fila de tarjetas."""
    celdas = "".join(f"<div class='tt-mini'><b>{escape(t)}</b><p>{escape(d)}</p></div>"
                     for t, d in items)
    return f"<div class='tt-grid'>{celdas}</div>"


def top_analogos(tabla, perfiles, n=3):
    """Los n primeros del ranking, con círculos numerados. Usa solo nuestro ranking y
    perfiles; el índice es una medida del algoritmo, no una probabilidad."""
    filas = []
    for i, f in enumerate(tabla[:n], start=1):
        p = perfiles[f["id"]]
        indice = "sin criterios comparables" if f["indice"] is None else f"{f['indice']} %"
        detalle = (f"{f['cumplidos']} de {f['comparados']} criterios cumplidos · "
                   f"Formación: {_texto(p['tipo_formacion'])} · "
                   f"Procesos: {_texto(p['procesos'])}")
        filas.append("<div class='tt-item'>"
                     f"<div class='tt-num'>{i}</div>"
                     "<div>"
                     f"<b>{escape(f['nombre'])}</b> <span class='tt-tag'>{indice}</span>"
                     f"<div class='tt-sub'>{escape(detalle)}</div>"
                     "</div></div>")
    return "<div class='tt-card'>" + "".join(filas) + "</div>"