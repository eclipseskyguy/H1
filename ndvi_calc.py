import rasterio
import numpy as np
import time
import json
import sys
from pathlib import Path  
from PIL import Image

def save_as_png(data, output_png_path):
    """Convert a NumPy array (NDVI/SAVI) to a PNG image."""
    min_val, max_val = np.nanmin(data), np.nanmax(data)
    normalized = ((data - min_val) / (max_val - min_val) * 255).astype(np.uint8)

    img = Image.fromarray(normalized)
    img.save(output_png_path)

def calculate_ndvi(red_band_path, nir_band_path, output_tif_path, output_png_path):
    with rasterio.open(red_band_path) as red_src, rasterio.open(nir_band_path) as nir_src:
        red = red_src.read(1).astype(np.float32)
        nir = nir_src.read(1).astype(np.float32)

        np.seterr(divide='ignore', invalid='ignore')
        ndvi = (nir - red) / (nir + red)

        meta = red_src.meta
        meta.update(dtype=rasterio.float32, count=1)

        with rasterio.open(output_tif_path, 'w', **meta) as dst:
            dst.write(ndvi, 1)
    
    save_as_png(ndvi, output_png_path)

def calculate_savi(red_band_path, nir_band_path, output_tif_path, output_png_path, L=0.5):
    with rasterio.open(red_band_path) as red_src, rasterio.open(nir_band_path) as nir_src:
        red = red_src.read(1).astype(np.float32)
        nir = nir_src.read(1).astype(np.float32)

        np.seterr(divide='ignore', invalid='ignore')
        savi = ((nir - red) / (nir + red + L)) * (1 + L)

        meta = red_src.meta
        meta.update(dtype=rasterio.float32, count=1)

        with rasterio.open(output_tif_path, 'w', **meta) as dst:
            dst.write(savi, 1)
    
    save_as_png(savi, output_png_path)

def wait_for_file(file_path, timeout=10):
    """Waits until a file exists before proceeding."""
    file_path = Path(file_path)
    start_time = time.time()
    while not file_path.exists():
        if time.time() - start_time > timeout:
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

def detect_deforestation(ndvi_change_path, savi_change_path, ndvi_threshold=-0.2, savi_threshold=-0.2):
    with rasterio.open(ndvi_change_path) as ndvi_src, rasterio.open(savi_change_path) as savi_src:
        ndvi_change = ndvi_src.read(1)
        savi_change = savi_src.read(1)

        deforested_pixels = np.sum((ndvi_change < ndvi_threshold) & (savi_change < savi_threshold))
        total_pixels = ndvi_change.size
        deforestation_percentage = (deforested_pixels / total_pixels) * 100

        result = {
            "deforestation_percentage": round(deforestation_percentage, 2),
            "status": "🚨 Significant deforestation detected!" if deforestation_percentage > 5 else "✅ No significant deforestation detected."
        }

        print(json.dumps(result))  # ✅ Print output in JSON format
        sys.stdout.flush()  # ✅ Ensure output is sent immediately

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

calculate_ndvi(red_band_old, nir_band_old, output_ndvi_old, output_ndvi_old.with_suffix(".png"))
calculate_ndvi(red_band_new, nir_band_new, output_ndvi_new, output_ndvi_new.with_suffix(".png"))

calculate_savi(red_band_old, nir_band_old, output_savi_old, output_savi_old.with_suffix(".png"))
calculate_savi(red_band_new, nir_band_new, output_savi_new, output_savi_new.with_suffix(".png"))

if all(wait_for_file(path) for path in [output_ndvi_old, output_ndvi_new, output_savi_old, output_savi_new]):
    compare_indices(output_ndvi_old, output_ndvi_new, output_ndvi_change)
    compare_indices(output_savi_old, output_savi_new, output_savi_change)
    detect_deforestation(output_ndvi_change, output_savi_change)
else:
    print(json.dumps({"status": "error", "message": "❌ NDVI/SAVI files are missing, aborting analysis."}))
    sys.stdout.flush()
