import math
import warnings

import numpy as np
import rasterio
from rasterio.windows import Window

URL_MOLA = "https://planetarymaps.usgs.gov/mosaic/Mars_MGS_MOLA_DEM_mosaic_global_463m.tif"
RADIO_MARTE_M = 3396190.0  # el del CRS del propio archivo

URL_LOLA = "https://planetarymaps.usgs.gov/mosaic/Lunar_LRO_LOLA_Global_LDEM_118m_Mar2014.tif"
RADIO_LUNA_M = 1737400.0   # el del CRS del propio archivo
FACTOR_LUNA = 4            # 118,45 m x 4 = 473,8 m, casi la escala de MOLA (463 m)


def ventana_mola(lat, lon, radio_km=5, url=URL_MOLA):
    """Elevación y pendiente de MOLA en una ventana cuadrada alrededor de (lat, lon).
    Longitud este positiva. Devuelve un diccionario con las mismas claves que
    resumen_topografico (Tierra), o None si la ventana no cabe o no tiene datos."""
    with rasterio.Env(GDAL_HTTP_TIMEOUT="60"):
        with rasterio.open(url) as src:
            lon180 = ((lon + 180) % 360) - 180
            x = math.radians(lon180) * RADIO_MARTE_M
            y = math.radians(lat) * RADIO_MARTE_M
            fila, col = src.index(x, y)

            px = abs(src.transform.a)  # metros por píxel (463.09)
            n = int(radio_km * 1000 / px)
            if fila - n < 0 or col - n < 0 or fila + n >= src.height or col + n >= src.width:
                return None  # la ventana se sale del mosaico
            elev = src.read(1, window=Window(col - n, fila - n, 2 * n + 1, 2 * n + 1))
            elev = elev.astype("float32")
            if src.nodata is not None:
                elev[elev == src.nodata] = np.nan

    validos = elev[~np.isnan(elev)]
    if validos.size == 0:
        return None
    dy = px
    dx = px * math.cos(math.radians(lat))  # los píxeles se acortan hacia los polos
    dzdy, dzdx = np.gradient(elev, dy, dx)
    pend = np.degrees(np.arctan(np.hypot(dzdx, dzdy)))
    vp = pend[~np.isnan(pend)]
    punto = elev[n, n]
    return {
        "elev_punto": None if np.isnan(punto) else float(punto),
        "elev_min": float(validos.min()),
        "elev_max": float(validos.max()),
        "elev_media": float(validos.mean()),
        "relieve": float(validos.max() - validos.min()),
        "pend_media": float(vp.mean()),
        "pend_mediana": float(np.median(vp)),
        "pct_suave": float(np.mean(vp < 5) * 100),
        "pct_validos": float(validos.size / elev.size * 100),
        "ventana_km": radio_km * 2,
        "resolucion_m": float(px),
    }


def ventana_luna(lat, lon, radio_km=5, url=URL_LOLA, factor=FACTOR_LUNA):
    """Elevación y pendiente de LOLA en una ventana cuadrada alrededor de (lat, lon).
    Longitud este positiva. Lee los píxeles originales (118 m), aplica la escala del
    archivo (metros = valor x 0,5) y promedia bloques de factor x factor para
    comparar con Marte a una escala parecida (~474 m). Mismas claves que ventana_mola;
    None si la ventana no cabe o no tiene datos."""
    with rasterio.Env(GDAL_HTTP_TIMEOUT="60"):
        with rasterio.open(url) as src:
            lon180 = ((lon + 180) % 360) - 180
            x = math.radians(lon180) * RADIO_LUNA_M
            y = math.radians(lat) * RADIO_LUNA_M
            fila, col = src.index(x, y)

            px = abs(src.transform.a)  # metros por píxel (118.45)
            escala = src.scales[0] if src.scales else 1.0
            offset = src.offsets[0] if src.offsets else 0.0
            ng = int(radio_km * 1000 / (px * factor))   # radio en píxeles gruesos
            medio = ng * factor + factor // 2           # centro de la ventana fina
            lado = (2 * ng + 1) * factor
            f0, c0 = fila - medio, col - medio
            if f0 < 0 or c0 < 0 or f0 + lado > src.height or c0 + lado > src.width:
                return None  # la ventana se sale del mosaico
            crudo = src.read(1, window=Window(c0, f0, lado, lado))
            nodata = src.nodata

    elev = crudo.astype("float32")
    if nodata is not None:
        elev[crudo == nodata] = np.nan          # sin dato antes de escalar
    elev = elev * escala + offset               # a metros

    bloques = elev.reshape(2 * ng + 1, factor, 2 * ng + 1, factor)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        grueso = np.nanmean(bloques, axis=(1, 3))

    validos = grueso[~np.isnan(grueso)]
    if validos.size == 0:
        return None
    paso = px * factor
    dy = paso
    dx = paso * math.cos(math.radians(lat))
    dzdy, dzdx = np.gradient(grueso, dy, dx)
    pend = np.degrees(np.arctan(np.hypot(dzdx, dzdy)))
    vp = pend[~np.isnan(pend)]
    punto = grueso[ng, ng]
    return {
        "elev_punto": None if np.isnan(punto) else float(punto),
        "elev_min": float(validos.min()),
        "elev_max": float(validos.max()),
        "elev_media": float(validos.mean()),
        "relieve": float(validos.max() - validos.min()),
        "pend_media": float(vp.mean()),
        "pend_mediana": float(np.median(vp)),
        "pct_suave": float(np.mean(vp < 5) * 100),
        "pct_validos": float(validos.size / grueso.size * 100),
        "ventana_km": radio_km * 2,
        "resolucion_m": float(paso),
    }