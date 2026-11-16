import zipfile
from pathlib import Path

import numpy as np

zip_path = Path("data/downloaded/NASADEM_HGT_n18w072.zip")
with zipfile.ZipFile(zip_path) as z:
    nombres = [n for n in z.namelist() if n.lower().endswith(".swb")]
    print("Archivos .swb en el zip:", nombres)
    datos = np.frombuffer(z.read(nombres[0]), dtype=np.uint8)

print("Bytes:", datos.size, "| esperado para 3601x3601:", 3601 * 3601)
if datos.size == 3601 * 3601:
    swb = datos.reshape(3601, 3601)
    valores, cuentas = np.unique(swb, return_counts=True)
    print("Valores y cantidad de píxeles:", dict(zip(valores.tolist(), cuentas.tolist())))
    # Punto de Lago Enriquillo en la tesela n18w072 (lat 18-19, lon -72 a -71)
    fila = int(round((19 - 18.5283) * 3600))
    col = int(round((-71.7152 + 72) * 3600))
    print("Valor en el punto del lago:", swb[fila, col])