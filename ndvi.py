import rasterio
import numpy as np

def calculate_ndvi(red_band_path, nir_band_path, output_path):
    with rasterio.open(red_band_path) as red_src, rasterio.open(nir_band_path) as nir_src:
        red = red_src.read(1).astype(np.float32)
        nir = nir_src.read(1).astype(np.float32)

        np.seterr(divide='ignore', invalid='ignore')
        ndvi = (nir - red) / (nir + red)

        meta = red_src.meta
        meta.update(dtype=rasterio.float32, count=1)
        with rasterio.open(output_path, 'w', **meta) as dst:
            dst.write(ndvi, 1)
    
    print(f'NDVI image saved at: {output_path}')

red_band = "C:/Users/rajat/OneDrive/Documents/Coding Projects/H1/new/band4o.TIF"
nir_band = "C:/Users/rajat/OneDrive/Documents/Coding Projects/H1/new/band5o.TIF"

output_ndvi = "ndvi-new.tif"

calculate_ndvi(red_band, nir_band, output_ndvi)
