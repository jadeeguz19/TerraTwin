import rasterio

URL = "https://planetarymaps.usgs.gov/mosaic/Mars_MGS_MOLA_DEM_mosaic_global_463m.tif"

with rasterio.Env(GDAL_HTTP_TIMEOUT="30"):
    with rasterio.open(URL) as src:
        print("Tamaño:", src.width, "x", src.height)
        print("CRS:", src.crs)
        print("Límites:", src.bounds)
        print("Transformación:", src.transform)
        print("Tipo:", src.dtypes[0], "| sin dato:", src.nodata)
        print("Bloques:", src.block_shapes)