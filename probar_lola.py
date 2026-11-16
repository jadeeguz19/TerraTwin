import time
import rasterio
from rasterio.windows import Window

URL = "https://planetarymaps.usgs.gov/mosaic/Lunar_LRO_LOLA_Global_LDEM_118m_Mar2014.tif"

with rasterio.Env(GDAL_HTTP_TIMEOUT="60"):
    with rasterio.open(URL) as src:
        print("Tamaño (ancho x alto):", src.width, "x", src.height)
        print("CRS:", src.crs)
        print("Transformación:", src.transform)
        print("Tipo de dato:", src.dtypes)
        print("Nodata:", src.nodata)
        print("Escala:", src.scales, "| Offset:", src.offsets)
        print("Bloques:", src.block_shapes)
        print("Overviews:", src.overviews(1))

        # Lee un trozo pequeño del centro del mosaico
        f, c = src.height // 2, src.width // 2
        t0 = time.time()
        datos = src.read(1, window=Window(c, f, 200, 200))
        print("Ventana 200x200 leída en", round(time.time() - t0, 1), "s")
        print("Mínimo/máximo crudos:", datos.min(), datos.max())