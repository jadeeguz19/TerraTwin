import numpy as np
import rasterio
from modules.topography import leer_elevacion, calcular_pendiente

elev, transform, bounds = leer_elevacion("data/processed/S25W070.hgt")
lat_centro = (bounds.top + bounds.bottom) / 2
pend = calcular_pendiente(elev, transform, lat_centro)

fila, col = rasterio.transform.rowcol(transform, -69.88, -24.06)
fila, col = int(fila), int(col)
print("Yungay -> elevación (m):", elev[fila, col],
    "| pendiente (°):", round(float(pend[fila, col]), 2))
print("Pendiente media de la tesela (°):", round(float(np.nanmean(pend)), 2))
print("Percentiles 10/50/90 (°):", np.round(np.nanpercentile(pend, [10, 50, 90]), 2))
validos = pend[~np.isnan(pend)]
print("Porcentaje de la tesela con pendiente < 5°:", round(float(np.mean(validos < 5) * 100), 1), "%")