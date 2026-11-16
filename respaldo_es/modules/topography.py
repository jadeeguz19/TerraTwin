import math
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import rowcol

CARPETA_PROCESADOS = Path("data/processed")


def nombre_tesela(lat, lon):
    """Nombre NASADEM de la tesela que contiene el punto (esquina inferior izquierda).
    Ejemplo: (18.5283, -71.7152) -> 'N18W072'."""
    f_lat, f_lon = math.floor(lat), math.floor(lon)
    ns = "N" if f_lat >= 0 else "S"
    ew = "E" if f_lon >= 0 else "W"
    return f"{ns}{abs(f_lat):02d}{ew}{abs(f_lon):03d}"


def ruta_tesela(lat, lon):
    nombre = nombre_tesela(lat, lon)
    return nombre, CARPETA_PROCESADOS / f"{nombre}.hgt"


def leer_elevacion(ruta):
    """Lee el DEM y marca los valores 'sin dato' como NaN (no como cero)."""
    with rasterio.open(ruta) as src:
        elev = src.read(1).astype("float32")
        if src.nodata is not None:
            elev[elev == src.nodata] = np.nan
        return elev, src.transform, src.bounds


def calcular_pendiente(elev, transform, lat_centro):
    """Pendiente en grados. El tamaño del pixel se convierte de grados a metros (aprox.)."""
    dy = abs(transform.e) * 111_320
    dx = abs(transform.a) * 111_320 * np.cos(np.radians(lat_centro))
    dzdy, dzdx = np.gradient(elev, dy, dx)
    return np.degrees(np.arctan(np.hypot(dzdx, dzdy)))


def resumen_topografico(ruta, lat, lon, radio_km=5):
    """Estadísticas de elevación y pendiente en una ventana cuadrada alrededor del punto.
    Devuelve None si el punto cae fuera de la tesela o la ventana no tiene datos.
    'pct_validos' es el porcentaje de la ventana completa que tiene dato: baja de 100
    si la ventana sale de la tesela o tiene huecos."""
    elev, transform, bounds = leer_elevacion(ruta)
    if not (bounds.left <= lon <= bounds.right and bounds.bottom <= lat <= bounds.top):
        return None
    pend = calcular_pendiente(elev, transform, (bounds.top + bounds.bottom) / 2)

    fila, col = rowcol(transform, lon, lat)
    fila, col = int(fila), int(col)
    n = int(radio_km * 1000 / (abs(transform.e) * 111_320))  # radio en píxeles
    f0, f1 = max(fila - n, 0), min(fila + n + 1, elev.shape[0])
    c0, c1 = max(col - n, 0), min(col + n + 1, elev.shape[1])
    v, p = elev[f0:f1, c0:c1], pend[f0:f1, c0:c1]

    validos_v, validos_p = v[~np.isnan(v)], p[~np.isnan(p)]
    if validos_v.size == 0 or validos_p.size == 0:
        return None
    punto = elev[fila, col]
    return {
        "elev_punto": None if np.isnan(punto) else float(punto),
        "elev_min": float(validos_v.min()),
        "elev_max": float(validos_v.max()),
        "elev_media": float(validos_v.mean()),
        "relieve": float(validos_v.max() - validos_v.min()),
        "pend_media": float(validos_p.mean()),
        "pend_mediana": float(np.median(validos_p)),
        "pct_suave": float(np.mean(validos_p < 5) * 100),
        "pct_validos": float(validos_v.size / ((2 * n + 1) ** 2) * 100),
        "ventana_km": radio_km * 2,
    }