from pathlib import Path
import re
import pandas as pd

# Cada hoja se identifica por su nombre y por columnas "ancla" que sirven
# para encontrar la fila de encabezados (no está en la fila 1).
HOJAS = {
    "regiones": {
        "hoja": "Regiones de referencia",
        "ancla": {"id", "cuerpo planetario"},
    },
    "analogos": {
        "hoja": "Análogos terrestres",
        "ancla": {"id", "nombre de región", "país"},
    },
    "variables": {
        "hoja": "Variables científicas",
        "ancla": {"id región", "variable", "valor"},
    },
}


def _norm(x):
    return str(x).strip().lower() if pd.notna(x) else ""


def _buscar_encabezado(crudo, ancla, max_filas=15):
    for i in range(min(max_filas, len(crudo))):
        celdas = {_norm(c) for c in crudo.iloc[i]}
        if ancla <= celdas:
            return i
    return None


def cargar_hoja(ruta, clave):
    """Lee una hoja sin modificar el archivo original."""
    cfg = HOJAS[clave]
    nombres = pd.ExcelFile(ruta, engine="openpyxl").sheet_names
    if cfg["hoja"] not in nombres:
        raise ValueError(f"No existe la hoja '{cfg['hoja']}'. Hojas encontradas: {nombres}")

    crudo = pd.read_excel(ruta, sheet_name=cfg["hoja"], header=None, engine="openpyxl")
    fila = _buscar_encabezado(crudo, cfg["ancla"])
    if fila is None:
        raise ValueError(f"No encontré la fila de encabezados en '{cfg['hoja']}'. "
                        f"Busco las columnas: {sorted(cfg['ancla'])}")

    df = crudo.iloc[fila + 1:].copy()
    df.columns = [str(c).strip() if pd.notna(c) else f"sin_nombre_{j}"
                for j, c in enumerate(crudo.iloc[fila])]
    df = df.dropna(how="all").reset_index(drop=True)
    vacias = [c for c in df.columns if c.startswith("sin_nombre_") and df[c].isna().all()]
    return df.drop(columns=vacias)


def normalizar_id(valor):
    """Convierte IDs a un formato único: MAR-01, LUN-01, EAR-01."""
    if pd.isna(valor):
        return None
    if hasattr(valor, "month"):  # fecha creada por error (mar-01 -> 1 de marzo)
        return f"MAR-{valor.day:02d}" if valor.month == 3 else None
    texto = str(valor).strip().upper()
    m = re.fullmatch(r"([A-Z]+)-0*(\d+)", texto)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}"
    return texto


def cargar_todo(ruta):
    ruta = Path(ruta)
    datos = {clave: cargar_hoja(ruta, clave) for clave in HOJAS}
    datos["regiones"]["ID"] = datos["regiones"]["ID"].map(normalizar_id)
    datos["analogos"]["ID"] = datos["analogos"]["ID"].map(normalizar_id)
    datos["variables"]["ID Región"] = datos["variables"]["ID Región"].map(normalizar_id)
    return datos