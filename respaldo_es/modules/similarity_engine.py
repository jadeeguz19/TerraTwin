import pandas as pd

# (columna, etiqueta, tipo de regla)
CRITERIOS = [
    ("tipo_formacion", "Tipo de formación", "lista"),
    ("litologia", "Litología", "lista"),
    ("minerales", "Minerales", "lista"),
    ("agua_o_hielo", "Agua o hielo documentados", "agua"),
    ("procesos", "Procesos geomorfológicos", "lista"),
]


def _parsear(texto):
    """'a|b' -> {'a','b'}. Vacío o 'sin_dato' -> None (dato faltante, NO cero)."""
    texto = (texto or "").strip()
    if texto in ("", "sin_dato"):
        return None
    return set(texto.split("|"))


def _texto(conjunto):
    return ", ".join(sorted(conjunto)) if conjunto else "sin dato"


def cargar_perfiles(ruta):
    df = pd.read_csv(ruta, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    perfiles = {}
    for _, fila in df.iterrows():
        p = {"nombre": fila["nombre"], "cuerpo": fila["cuerpo"]}
        for clave, _, _ in CRITERIOS:
            p[clave] = _parsear(fila[clave])
        perfiles[fila["id"].strip()] = p
    return perfiles


def _estado(ref, cand, tipo):
    if ref is None or cand is None:
        return "sin dato"
    if tipo == "agua":
        # El Excel solo registra presencia: si la referencia no tiene evidencia
        # documentada, el criterio no se evalúa.
        if "documentada" not in ref:
            return "sin dato"
        return "cumple" if "documentada" in cand else "no cumple"
    return "cumple" if ref & cand else "no cumple"


def comparar(ref, cand):
    detalle = []
    for clave, etiqueta, tipo in CRITERIOS:
        r, c = ref[clave], cand[clave]
        detalle.append({
            "criterio": etiqueta,
            "referencia": _texto(r),
            "candidato": _texto(c),
                        "en_comun": (("ninguno" if not (r & c) else _texto(r & c))
                        if (r and c and tipo == "lista") else "—"),
            "estado": _estado(r, c, tipo),
        })
    comparados = sum(d["estado"] != "sin dato" for d in detalle)
    cumplidos = sum(d["estado"] == "cumple" for d in detalle)
    indice = round(100 * cumplidos / comparados, 1) if comparados else None
    return {"cumplidos": cumplidos, "comparados": comparados,
            "indice": indice, "detalle": detalle}


def ranking(perfiles, id_ref):
    ref = perfiles[id_ref]
    filas = []
    for pid, cand in perfiles.items():
        if cand["cuerpo"] != "Tierra":
            continue
        r = comparar(ref, cand)
        filas.append({"id": pid, "nombre": cand["nombre"], **r})
    filas.sort(key=lambda f: (-(f["indice"] if f["indice"] is not None else -1),
                            -f["comparados"]))
    return filas