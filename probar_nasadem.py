import shutil
import zipfile
from pathlib import Path

import rasterio

descargas = Path("data/downloaded")
procesados = Path("data/processed")
procesados.mkdir(parents=True, exist_ok=True)

# 1. Descomprimir (si hay un .zip)
for z in descargas.glob("*.zip"):
    with zipfile.ZipFile(z) as zf:
        print("Contenido de", z.name, "->", zf.namelist())
        zf.extractall(descargas / z.stem)

# 2. Buscar el archivo de elevación (.hgt)
hgts = list(descargas.rglob("*.hgt"))
if not hgts:
    raise SystemExit("No encontré ningún .hgt en data/downloaded. Revisa que el archivo esté ahí.")
print("Elevación:", hgts[0].name)

# 3. Copia con el nombre estándar que GDAL reconoce (el original no se toca)
copia = procesados / "S25W070.hgt"
shutil.copy(hgts[0], copia)

# 4. Abrir y mostrar datos básicos
with rasterio.open(copia) as src:
    datos = src.read(1)
    print("Tamaño:", src.width, "x", src.height)
    print("Límites:", src.bounds)
    print("Sin dato:", src.nodata)
    print("Elevación mínima y máxima (m):", datos.min(), datos.max())