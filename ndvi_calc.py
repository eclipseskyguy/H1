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

def calculate_savi(red_band_path, nir_band_path, output_path, L=0.5):
    with rasterio.open(red_band_path) as red_src, rasterio.open(nir_band_path) as nir_src:
        red = red_src.read(1).astype(np.float32)
        nir = nir_src.read(1).astype(np.float32)

        np.seterr(divide='ignore', invalid='ignore')
        savi = ((nir - red) / (nir + red + L)) * (1 + L)

        meta = red_src.meta
        meta.update(dtype=rasterio.float32, count=1)

        with rasterio.open(output_path, 'w', **meta) as dst:
            dst.write(savi, 1)
    
    print(f'✅ SAVI image saved at: {output_path}')

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

def compare_indices(old_path, new_path, output_change_path):
    with rasterio.open(old_path) as old_src, rasterio.open(new_path) as new_src:
        old_data = old_src.read(1).astype(np.float32)
        new_data = new_src.read(1).astype(np.float32)

       
        min_rows = min(old_data.shape[0], new_data.shape[0])
        min_cols = min(old_data.shape[1], new_data.shape[1])
        old_data = old_data[:min_rows, :min_cols]
        new_data = new_data[:min_rows, :min_cols]

        change = new_data - old_data

        meta = old_src.meta
        meta.update(dtype=rasterio.float32, count=1, height=min_rows, width=min_cols)

        with rasterio.open(output_change_path, 'w', **meta) as dst:
            dst.write(change, 1)
    
    print(f'✅ Change map saved at: {output_change_path}')

def detect_deforestation(ndvi_change_path, savi_change_path, ndvi_threshold=-0.2, savi_threshold=-0.2):
    with rasterio.open(ndvi_change_path) as ndvi_src, rasterio.open(savi_change_path) as savi_src:
        ndvi_change = ndvi_src.read(1)
        savi_change = savi_src.read(1)

        # Detect areas where both NDVI and SAVI indicate deforestation
        deforested_pixels = np.sum((ndvi_change < ndvi_threshold) & (savi_change < savi_threshold))
        total_pixels = ndvi_change.size
        deforestation_percentage = (deforested_pixels / total_pixels) * 100

        print(f'🌿 Deforestation detected in {deforestation_percentage:.2f}% of the area')

        if deforestation_percentage > 5: 
            print("🚨 Significant deforestation detected!")
        else:
            print("✅ No significant deforestation detected.")


base_path = Path("C:/Users/rajat/OneDrive/Documents/Coding Projects/H1")

red_band_old = base_path / "old/band4.TIF"
nir_band_old = base_path / "old/band5.TIF"
red_band_new = base_path / "new/band4o.TIF"
nir_band_new = base_path / "new/band5o.TIF"

output_ndvi_old = base_path / "ndvis/ndvi-older.tif"
output_ndvi_new = base_path / "ndvis/ndvi-new.tif"
output_ndvi_change = base_path / "ndvis/ndvi_change.tif"

output_savi_old = base_path / "savis/savi-older.tif"
output_savi_new = base_path / "savis/savi-new.tif"
output_savi_change = base_path / "savis/savi_change.tif"


calculate_ndvi(red_band_old, nir_band_old, output_ndvi_old)
calculate_ndvi(red_band_new, nir_band_new, output_ndvi_new)

calculate_savi(red_band_old, nir_band_old, output_savi_old)
calculate_savi(red_band_new, nir_band_new, output_savi_new)


print("⏳ Waiting for NDVI and SAVI files to be ready...")
if all(wait_for_file(path) for path in [output_ndvi_old, output_ndvi_new, output_savi_old, output_savi_new]):
    print("✅ NDVI and SAVI files found. Proceeding with comparison.")
    compare_indices(output_ndvi_old, output_ndvi_new, output_ndvi_change)
    compare_indices(output_savi_old, output_savi_new, output_savi_change)
    detect_deforestation(output_ndvi_change, output_savi_change)
else:
    print("❌ Error: One or more NDVI/SAVI files are missing. Aborting comparison.")
