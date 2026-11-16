import numpy as np

from modules.discovery import buscar_ventanas, zonas

RELIEVE_MIN_M = 50.0  # el mismo margen mínimo de relieve que usa buscar_ventanas


def distancia_zona(z, ref, tol_pend, tol_rel):
    """Cercanía de una zona a la referencia: 0 = idéntica; cerca de 1 = en el borde de
    la tolerancia. Combina pendiente y relieve, cada uno medido en unidades de su
    tolerancia. Es una medida definida por el equipo, no una probabilidad."""
    margen = max(tol_rel * ref["relieve"], RELIEVE_MIN_M)
    dp = (z["pend_media"] - ref["pend_mediana"]) / tol_pend
    dr = (z["relieve_medio"] - ref["relieve"]) / margen
    return float(np.hypot(dp, dr))


def buscar_en_teselas(teselas, obtener_stats, ref, conocidos, tol_pend, tol_rel):
    """Busca en varias teselas. 'obtener_stats(ruta)' devuelve las estadísticas de ventanas
    (en la app, la versión con caché). 'tol_rel' es una fracción (0.30 = 30 %).
    Devuelve (zonas ordenadas por cercanía, resumen por tesela)."""
    todas, resumen = [], []
    for nombre in teselas:
        s = obtener_stats(f"data/processed/{nombre}.hgt")
        match = buscar_ventanas(s, ref, tol_pend=tol_pend, tol_relieve=tol_rel)
        lista = zonas(s, match, conocidos)
        resumen.append({"tesela": nombre, "evaluadas": s["n_evaluadas"],
                        "excluidas_agua": s["excluidas_agua"],
                        "coinciden": int(match.sum()), "zonas": len(lista)})
        for z in lista:
            z = dict(z)
            z["tesela"] = nombre
            z["id_zona"] = f"{nombre}-{z['id']}"
            z["distancia"] = distancia_zona(z, ref, tol_pend, tol_rel)
            todas.append(z)
    todas.sort(key=lambda z: (z["distancia"], -z["ventanas"]))
    return todas, resumen