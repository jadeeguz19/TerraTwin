import pandas as pd

from modules.analogs_en import ANALOGS_EN

# Internal column names and body names stay as in the CSV (Spanish codes);
# only what the user sees is in English.
CRITERIOS = [
    ("tipo_formacion", "Formation type", "lista"),
    ("litologia", "Lithology", "lista"),
    ("minerales", "Minerals", "lista"),
    ("agua_o_hielo", "Documented water or ice", "agua"),
    ("procesos", "Geomorphological processes", "lista"),
]

CUERPO_EN = {"Marte": "Mars", "Luna": "Moon", "Tierra": "Earth"}

MEETS, NOT_MEETS, NO_DATA = "meets", "does not meet", "no data"

VALORES_EN = {
    "litologia": {"ignea": "igneous", "sedimentaria": "sedimentary", "impacto": "impact rocks"},
    "tipo_formacion": {"impacto": "impact", "volcanico": "volcanic", "lacustre": "lacustrine",
                       "desierto_eolico": "aeolian desert", "polar": "polar"},
    "minerales": {"olivino": "olivine", "piroxeno": "pyroxene", "plagioclasa": "plagioclase",
                  "carbonatos": "carbonates", "arcillas": "clays", "sulfatos": "sulfates",
                  "oxidos_hierro": "iron oxides", "sales": "salts",
                  "cuarzo_feldespato": "quartz and feldspar"},
    "agua_o_hielo": {"documentada": "documented", "no_documentada": "not documented"},
    "procesos": {"impacto": "impact", "fluvial_lacustre": "fluvial/lacustrine",
                 "eolico": "aeolian", "volcanico": "volcanic", "evaporitico": "evaporitic",
                 "glacial_periglacial": "glacial/periglacial", "hidrotermal": "hydrothermal"},
}
# Used when a column is not given (the ambiguous word "impacto" is shown as "impact")
VALORES_GENERAL = {}
for _clave in ("litologia", "tipo_formacion", "minerales", "agua_o_hielo", "procesos"):
    VALORES_GENERAL.update(VALORES_EN[_clave])


def cuerpo_en(cuerpo):
    return CUERPO_EN.get(cuerpo, cuerpo)


def _parsear(texto):
    """'a|b' -> {'a','b'}. Empty or 'sin_dato' -> None (missing data, NOT zero)."""
    texto = (texto or "").strip()
    if texto in ("", "sin_dato"):
        return None
    return set(texto.split("|"))


def _texto(conjunto, clave=None):
    """Readable English text of a set of labels; 'no data' if there is none."""
    if not conjunto:
        return NO_DATA
    tabla = VALORES_EN.get(clave, VALORES_GENERAL)
    return ", ".join(sorted(tabla.get(v, v.replace("_", " ")) for v in conjunto))


def cargar_perfiles(ruta):
    df = pd.read_csv(ruta, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    perfiles = {}
    for _, fila in df.iterrows():
        pid = fila["id"].strip()
        nombre = ANALOGS_EN.get(pid, {}).get("name", fila["nombre"])  # English site name
        p = {"nombre": nombre, "cuerpo": fila["cuerpo"]}
        for clave, _, _ in CRITERIOS:
            p[clave] = _parsear(fila[clave])
        perfiles[pid] = p
    return perfiles


def _estado(ref, cand, tipo):
    if ref is None or cand is None:
        return NO_DATA
    if tipo == "agua":
        # The Excel only records presence: if the reference has no documented
        # evidence, the criterion is not evaluated.
        if "documentada" not in ref:
            return NO_DATA
        return MEETS if "documentada" in cand else NOT_MEETS
    return MEETS if ref & cand else NOT_MEETS


def comparar(ref, cand):
    detalle = []
    for clave, etiqueta, tipo in CRITERIOS:
        r, c = ref[clave], cand[clave]
        if r and c and tipo == "lista":
            en_comun = _texto(r & c, clave) if (r & c) else "none"
        else:
            en_comun = "—"
        detalle.append({
            "criterio": etiqueta,
            "referencia": _texto(r, clave),
            "candidato": _texto(c, clave),
            "en_comun": en_comun,
            "estado": _estado(r, c, tipo),
        })
    comparados = sum(d["estado"] != NO_DATA for d in detalle)
    cumplidos = sum(d["estado"] == MEETS for d in detalle)
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