import math
import warnings
from pathlib import Path

import numpy as np

from modules.topography import leer_elevacion

FACTOR = 15   # NASADEM (~31 m) -> ~463 m, la misma escala que MOLA
LADO = 21     # ventana de 21 píxeles gruesos = unos 9,7 km (igual que ventana_mola)
PASO = 10     # las ventanas avanzan de a 10 píxeles (se traslapan)
MAX_AGUA = 0.05   # se descartan ventanas con más de 5 % de agua (parámetro del equipo)
VALOR_AGUA = 255  # valor de agua en la máscara .swb (comprobado en el punto de Lago Enriquillo)


def a_escala_gruesa(elev, factor=FACTOR):
    """Promedia bloques de factor x factor. Descarta el sobrante del borde."""
    filas = (elev.shape[0] // factor) * factor
    cols = (elev.shape[1] // factor) * factor
    bloques = elev[:filas, :cols].reshape(filas // factor, factor, cols // factor, factor)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        return np.nanmean(bloques, axis=(1, 3))


def leer_agua(ruta_hgt, forma):
    """Lee la máscara de agua (.swb) junto al .hgt. Devuelve un arreglo booleano
    (True = agua) con la misma forma que el DEM, o None si no existe o no coincide."""
    ruta_swb = Path(ruta_hgt).with_suffix(".swb")
    if not ruta_swb.exists():
        return None
    datos = np.fromfile(ruta_swb, dtype=np.uint8)
    if datos.size != forma[0] * forma[1]:
        return None          # tamaño distinto al DEM: no se usa
    return datos.reshape(forma) == VALOR_AGUA


def fraccion_agua_gruesa(agua, factor=FACTOR):
    """Fracción de agua (0 a 1) en cada bloque de factor x factor."""
    filas = (agua.shape[0] // factor) * factor
    cols = (agua.shape[1] // factor) * factor
    bloques = agua[:filas, :cols].reshape(filas // factor, factor, cols // factor, factor)
    return bloques.mean(axis=(1, 3))


def estadisticas_ventanas(ruta, lado=LADO, paso=PASO):
    """Pendiente mediana y relieve de cada ventana de la tesela, a escala MOLA.
    Con máscara .swb descarta ventanas con más de 5 % de agua; sin ella, usa la
    regla de más de la mitad de píxeles a 0 m."""
    elev, tr, bounds = leer_elevacion(ruta)
    grueso = a_escala_gruesa(elev)
    agua = leer_agua(ruta, elev.shape)
    frac_agua = fraccion_agua_gruesa(agua) if agua is not None else None

    lat_c = (bounds.top + bounds.bottom) / 2
    dy = abs(tr.e) * FACTOR * 111_320
    dx = abs(tr.a) * FACTOR * 111_320 * math.cos(math.radians(lat_c))
    dzdy, dzdx = np.gradient(grueso, dy, dx)
    pend = np.degrees(np.arctan(np.hypot(dzdx, dzdy)))

    n_f = (grueso.shape[0] - lado) // paso + 1
    n_c = (grueso.shape[1] - lado) // paso + 1
    forma = (n_f, n_c)
    s = {k: np.full(forma, np.nan) for k in
         ("pend_med", "relieve", "elev_media", "lat_top", "lat_bot", "lon_left", "lon_right")}
    excluidas_agua = 0
    for i in range(n_f):
        for j in range(n_c):
            f0, c0 = i * paso, j * paso
            v = grueso[f0:f0 + lado, c0:c0 + lado]
            p = pend[f0:f0 + lado, c0:c0 + lado]
            s["lat_top"][i, j] = tr.f + f0 * FACTOR * tr.e
            s["lat_bot"][i, j] = tr.f + (f0 + lado) * FACTOR * tr.e
            s["lon_left"][i, j] = tr.c + c0 * FACTOR * tr.a
            s["lon_right"][i, j] = tr.c + (c0 + lado) * FACTOR * tr.a
            if np.isnan(v).any():
                continue                      # ventana con huecos: no se evalúa
            if frac_agua is not None:
                if frac_agua[f0:f0 + lado, c0:c0 + lado].mean() > MAX_AGUA:
                    excluidas_agua += 1
                    continue                  # demasiada agua: no es superficie sólida
            elif np.mean(v == 0) > 0.5:
                continue                      # sin máscara: más de la mitad a 0 m, probablemente mar
            s["pend_med"][i, j] = np.median(p)
            s["relieve"][i, j] = v.max() - v.min()
            s["elev_media"][i, j] = v.mean()
    s["n_evaluadas"] = int(np.sum(~np.isnan(s["pend_med"])))
    s["excluidas_agua"] = excluidas_agua
    s["usa_mascara"] = agua is not None
    return s


def buscar_ventanas(s, ref, tol_pend=2.0, tol_relieve=0.30, relieve_min=50.0):
    """Ventanas cuya pendiente y relieve se parecen a los de la referencia.
    Los márgenes son parámetros definidos por el equipo, no valores científicos."""
    ok_pend = np.abs(s["pend_med"] - ref["pend_mediana"]) <= tol_pend
    margen = max(tol_relieve * ref["relieve"], relieve_min)
    ok_rel = np.abs(s["relieve"] - ref["relieve"]) <= margen
    return ok_pend & ok_rel          # las ventanas sin dato (NaN) nunca coinciden


def agrupar(match):
    """Une ventanas vecinas (8 direcciones) en zonas. Devuelve (etiquetas, cantidad)."""
    etiquetas = np.zeros(match.shape, dtype=int)
    actual = 0
    for i, j in zip(*np.nonzero(match)):
        if etiquetas[i, j]:
            continue
        actual += 1
        etiquetas[i, j] = actual
        pila = [(i, j)]
        while pila:
            a, b = pila.pop()
            for da in (-1, 0, 1):
                for db in (-1, 0, 1):
                    x, y = a + da, b + db
                    if (0 <= x < match.shape[0] and 0 <= y < match.shape[1]
                            and match[x, y] and not etiquetas[x, y]):
                        etiquetas[x, y] = actual
                        pila.append((x, y))
    return etiquetas, actual


def zonas(s, match, conocidos=None):
    """Resumen de cada zona. 'conocidos' = {nombre: (lat, lon)} de análogos ya documentados."""
    etiquetas, total = agrupar(match)
    salida = []
    for k in range(1, total + 1):
        m = etiquetas == k
        lat_max, lat_min = np.max(s["lat_top"][m]), np.min(s["lat_bot"][m])
        lon_min, lon_max = np.min(s["lon_left"][m]), np.max(s["lon_right"][m])
        dentro = [n for n, (la, lo) in (conocidos or {}).items()
                  if lat_min <= la <= lat_max and lon_min <= lo <= lon_max]
        salida.append({
            "id": k, "ventanas": int(m.sum()),
            "lat_min": float(lat_min), "lat_max": float(lat_max),
            "lon_min": float(lon_min), "lon_max": float(lon_max),
            "pend_media": float(np.mean(s["pend_med"][m])),
            "relieve_medio": float(np.mean(s["relieve"][m])),
            "elev_media": float(np.mean(s["elev_media"][m])),
            "conocidos": dentro,
        })
    salida.sort(key=lambda z: -z["ventanas"])
    return salida