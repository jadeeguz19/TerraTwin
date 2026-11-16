import pandas as pd
import re

COLUMNAS_REQUERIDAS = {
    "regiones": ["ID", "Cuerpo planetario", "Nombre de la región", "Coordenadas"],
    "analogos": ["ID", "Nombre de Región", "País", "Latitud", "Longitud"],
    "variables": ["ID Región", "Nombre de Región", "Variable", "Valor",
                    "Unidad", "Tipo de dato", "Fuente"],
}
TIPOS_VALIDOS = {"numérico", "categórico", "estado de información"}


def _a_numero(valor):
    if pd.isna(valor):
        return None
    try:
        return float(str(valor).strip().replace(",", "."))
    except ValueError:
        return None


def parsear_coordenada(valor):
    """Acepta -24.06378, '18.5283° N' o '71.7152° O'. Devuelve grados decimales o None."""
    if pd.isna(valor):
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    m = re.fullmatch(r"(-?\d+(?:[.,]\d+)?)\s*°?\s*([NSEWO])?", str(valor).strip().upper())
    if not m:
        return None
    numero = float(m.group(1).replace(",", "."))
    if m.group(2) in ("S", "W", "O"):  # en español, O = oeste
        numero = -abs(numero)
    return numero

def validar(datos):
    problemas = []

    def avisar(nivel, hoja, mensaje):
        problemas.append({"nivel": nivel, "hoja": hoja, "mensaje": mensaje})

    # 1. Columnas necesarias
    for clave, cols in COLUMNAS_REQUERIDAS.items():
        faltan = [c for c in cols if c not in datos[clave].columns]
        if faltan:
            avisar("ERROR", clave, f"Faltan columnas: {faltan}")
    if problemas:
        return problemas  # sin las columnas no se puede seguir

    reg, ana, var = datos["regiones"], datos["analogos"], datos["variables"]

    # 2. IDs vacíos o repetidos
    for clave, df in [("regiones", reg), ("analogos", ana)]:
        vacios = int(df["ID"].isna().sum())
        if vacios:
            avisar("ERROR", clave, f"{vacios} fila(s) sin ID válido")
        repetidos = df["ID"][df["ID"].duplicated() & df["ID"].notna()].unique().tolist()
        if repetidos:
            avisar("ERROR", clave, f"IDs repetidos: {repetidos}")

    # 3. Relación entre variables y regiones
    sin_id = int(var["ID Región"].isna().sum())
    if sin_id:
        avisar("ERROR", "variables", f"{sin_id} fila(s) sin ID de región válido")
    ids_reg = set(reg["ID"].dropna())
    ids_var = set(var["ID Región"].dropna())
    sin_region = sorted(ids_var - ids_reg)
    if sin_region:
        avisar("ERROR", "variables", f"IDs de variables que no existen en regiones: {sin_region}")
    sin_variables = sorted(ids_reg - ids_var)
    if sin_variables:
        avisar("AVISO", "regiones", f"Regiones sin ninguna variable: {sin_variables}")

    # 4. Tipo de dato
    tipo = var["Tipo de dato"].fillna("(vacío)").astype(str).str.strip().str.lower()
    for i in var.index[~tipo.isin(TIPOS_VALIDOS)]:
        avisar("AVISO", "variables",
                f"{var.loc[i, 'ID Región']} · {var.loc[i, 'Variable']}: "
                f"tipo de dato no válido ('{var.loc[i, 'Tipo de dato']}')")

    # 5. Valores numéricos: deben ser números y tener unidad
    for i in var.index[tipo == "numérico"]:
        etiqueta = f"{var.loc[i, 'ID Región']} · {var.loc[i, 'Variable']}"
        if _a_numero(var.loc[i, "Valor"]) is None:
            avisar("AVISO", "variables", f"{etiqueta}: el valor '{var.loc[i, 'Valor']}' no es un número")
        unidad = var.loc[i, "Unidad"]
        if pd.isna(unidad) or str(unidad).strip() in ("", "—"):
            avisar("AVISO", "variables", f"{etiqueta}: valor numérico sin unidad")

    # 6. Valores vacíos (un dato faltante no es un cero)
    for i in var.index[var["Valor"].isna()]:
        avisar("AVISO", "variables",
                f"{var.loc[i, 'ID Región']} · {var.loc[i, 'Variable']}: sin valor")

    # 7. Coordenadas de los análogos
    for _, f in ana.iterrows():
        lat, lon = parsear_coordenada(f["Latitud"]), parsear_coordenada(f["Longitud"])
        nombre = f"{f['ID']} {f['Nombre de Región']}"
        if lat is None or lon is None:
            avisar("AVISO", "analogos",
                f"{nombre}: coordenadas no numéricas ('{f['Latitud']}', '{f['Longitud']}')")
        elif not (-90 <= lat <= 90 and -180 <= lon <= 180):
            avisar("ERROR", "analogos", f"{nombre}: coordenadas fuera de rango ({lat}, {lon})")

    return problemas