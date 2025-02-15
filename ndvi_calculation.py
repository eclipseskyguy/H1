import rasterio
import numpy as np
import time
from pathlib import Path  

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
    
    print(f'✅ NDVI image saved at: {output_path}')

def wait_for_file(file_path, timeout=10):
    """Waits until a file exists before proceeding."""
    file_path = Path(file_path)
    start_time = time.time()
    while not file_path.exists():
        if time.time() - start_time > timeout:
            print(f"❌ Error: Timed out waiting for {file_path}")
            return False
        time.sleep(1) 
    return True

def compare_ndvi(ndvi_old_path, ndvi_new_path, output_change_path):
    with rasterio.open(ndvi_old_path) as old_src, rasterio.open(ndvi_new_path) as new_src:
        ndvi_old = old_src.read(1).astype(np.float32)
        ndvi_new = new_src.read(1).astype(np.float32)

        
        min_rows = min(ndvi_old.shape[0], ndvi_new.shape[0])
        min_cols = min(ndvi_old.shape[1], ndvi_new.shape[1])

        ndvi_old = ndvi_old[:min_rows, :min_cols]
        ndvi_new = ndvi_new[:min_rows, :min_cols]

        ndvi_change = ndvi_new - ndvi_old

        
        meta = old_src.meta
        meta.update(dtype=rasterio.float32, count=1, height=min_rows, width=min_cols)

        with rasterio.open(output_change_path, 'w', **meta) as dst:
            dst.write(ndvi_change, 1)
    
    print(f'✅ NDVI change map saved at: {output_change_path}')

def detect_deforestation(ndvi_change_path, threshold=-0.2):
    with rasterio.open(ndvi_change_path) as src:
        ndvi_change = src.read(1)

        deforested_pixels = np.sum(ndvi_change < threshold)
        total_pixels = ndvi_change.size
        deforestation_percentage = (deforested_pixels / total_pixels) * 100

        print(f'🌿 Deforestation detected in {deforestation_percentage:.2f}% of the area')
        
        if deforestation_percentage > 5: 
            print("🚨 Significant deforestation detected!")
        else:
            print("✅ No significant deforestation detected.")


base_path = Path("C:/Users/rajat/OneDrive/Documents/Coding Projects/H1")

red_band = base_path / "old/band4.TIF"
nir_band = base_path / "old/band5.TIF"
red_bando = base_path / "new/band4o.TIF"
nir_bando = base_path / "new/band5o.TIF"

output_ndvi_old = base_path / "ndvis/ndvi-older.tif"
output_ndvi_new = base_path / "ndvis/ndvi-new.tif"
output_change = base_path / "ndvis/ndvi_change.tif"


calculate_ndvi(red_band, nir_band, output_ndvi_old)
calculate_ndvi(red_bando, nir_bando, output_ndvi_new)


print("⏳ Waiting for NDVI files to be ready...")
if wait_for_file(output_ndvi_old) and wait_for_file(output_ndvi_new):
    print("✅ NDVI files found. Proceeding with comparison.")
    compare_ndvi(output_ndvi_old, output_ndvi_new, output_change)
    detect_deforestation(output_change)
else:
    print("❌ Error: One or more NDVI files are missing. Aborting comparison.")
