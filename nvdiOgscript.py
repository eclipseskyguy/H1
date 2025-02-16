import rasterio
import numpy as np
import json
import sys
from pathlib import Path  
import cv2
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import time

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Get Folder Paths from Command Line
start_folder = Path(sys.argv[1])
end_folder = Path(sys.argv[2])

# Load Configuration
with open('config.json', 'r') as f:
    config = json.load(f)

L = config["L"]
NDVI_THRESHOLD = config["ndvi_threshold"]
SAVI_THRESHOLD = config["savi_threshold"]
DEFORESTATION_ALERT_THRESHOLD = config["deforestation_alert_threshold"]
CLOUD_SHADOW_THRESHOLD = config["cloud_shadow_threshold"]
BRIGHTNESS_THRESHOLD = config["brightness_threshold"]

def apply_cloud_shadow_mask(red, nir):
    """Applies cloud and shadow mask based on brightness threshold."""
    brightness = (red + nir) / 2
    mask = brightness > CLOUD_SHADOW_THRESHOLD
    red[mask] = np.nan
    nir[mask] = np.nan
    return red, nir

def dark_object_subtraction(band):
    """Applies Dark Object Subtraction (DOS) for atmospheric correction."""
    dark_object_value = np.nanpercentile(band, 1)
    corrected = band - dark_object_value
    corrected[corrected < 0] = 0
    return corrected

def save_as_png(data, output_png_path):
    """Normalizes and saves the data as a PNG image."""
    min_val, max_val = np.nanmin(data), np.nanmax(data)
    normalized = ((data - min_val) / (max_val - min_val) * 255).astype(np.uint8)
    cv2.imwrite(str(output_png_path), normalized)
    logging.info(f"Saved PNG: {output_png_path}")

def compute_indices(red_band_path, nir_band_path, output_ndvi_path, output_savi_path, ndvi_png_path, savi_png_path, L=L):
    """Computes NDVI and SAVI indices from the red and NIR bands."""
    try:
        with rasterio.open(red_band_path, mmap=True, num_threads="all_cpus") as red_src, \
             rasterio.open(nir_band_path, mmap=True, num_threads="all_cpus") as nir_src:

            red = red_src.read(1).astype(np.float32)
            nir = nir_src.read(1).astype(np.float32)

            # Apply Atmospheric Correction
            red = dark_object_subtraction(red)
            nir = dark_object_subtraction(nir)

            # Apply Cloud and Shadow Masking
            red, nir = apply_cloud_shadow_mask(red, nir)

            np.seterr(divide='ignore', invalid='ignore')
            ndvi = (nir - red) / (nir + red)
            savi = ((nir - red) / (nir + red + L)) * (1 + L)

            meta = red_src.meta
            meta.update(dtype=rasterio.float32, count=1)

            with rasterio.open(output_ndvi_path, 'w', **meta, num_threads="all_cpus") as ndvi_dst:
                ndvi_dst.write(ndvi, 1)
            with rasterio.open(output_savi_path, 'w', **meta, num_threads="all_cpus") as savi_dst:
                savi_dst.write(savi, 1)
            
            save_as_png(ndvi, ndvi_png_path)
            save_as_png(savi, savi_png_path)

        logging.info(f"Computed indices for: {red_band_path} and {nir_band_path}")
    except Exception as e:
        logging.error(f"Error in computing indices: {e}")

def compare_indices(old_path, new_path, output_change_path):
    """Compares two indices and calculates change."""
    try:
        with rasterio.open(old_path, mmap=True, num_threads="all_cpus") as old_src, \
             rasterio.open(new_path, mmap=True, num_threads="all_cpus") as new_src:
             
            old_data, new_data = old_src.read(1).astype(np.float32), new_src.read(1).astype(np.float32)
            min_rows, min_cols = min(old_data.shape[0], new_data.shape[0]), min(old_data.shape[1], new_data.shape[1])
            change = new_data[:min_rows, :min_cols] - old_data[:min_rows, :min_cols]

            meta = old_src.meta
            meta.update(dtype=rasterio.float32, count=1, height=min_rows, width=min_cols)
            with rasterio.open(output_change_path, 'w', **meta, num_threads="all_cpus") as dst:
                dst.write(change, 1)

        logging.info(f"Compared indices: {old_path} vs {new_path}")
    except Exception as e:
        logging.error(f"Error in comparing indices: {e}")

def detect_deforestation(ndvi_change_path, savi_change_path):
    """Detects deforestation using NDVI and SAVI change thresholds."""
    try:
        with rasterio.open(ndvi_change_path, mmap=True, num_threads="all_cpus") as ndvi_src, \
             rasterio.open(savi_change_path, mmap=True, num_threads="all_cpus") as savi_src:

            ndvi_change, savi_change = ndvi_src.read(1), savi_src.read(1)
            deforested_pixels = np.sum((ndvi_change < NDVI_THRESHOLD) & (savi_change < SAVI_THRESHOLD))
            deforestation_percentage = round((deforested_pixels / ndvi_change.size) * 100, 2)
            result = {
                "deforestation_percentage": deforestation_percentage,
                "status": "🚨 Significant deforestation detected!" if deforestation_percentage > DEFORESTATION_ALERT_THRESHOLD else "✅ No significant deforestation detected."
            }
        
        logging.info(json.dumps(result))
    except Exception as e:
        logging.error(f"Error in detecting deforestation: {e}")

def parallel_processes():
    """Manages parallel computation of indices and comparisons."""
    base_path = Path(__file__).resolve().parent
    input_folder = config["input_folder"]
    output_folder = config["output_folder"]
    
    # Define paths and ensure output directories exist
    paths = {
        "red_band_old": base_path / input_folder / start_folder / "band4.TIF",
        "nir_band_old": base_path / input_folder / start_folder / "band5.TIF",
        "ndvi_old": base_path / output_folder / start_folder / "ndvi.TIF",
        "savi_old": base_path / output_folder / start_folder / "savi.TIF",
        "red_band_new": base_path / input_folder / end_folder / "band4.TIF",
        "nir_band_new": base_path / input_folder / end_folder / "band5.TIF",
        "ndvi_new": base_path / output_folder / end_folder / "ndvi.TIF",
        "savi_new": base_path / output_folder / end_folder / "savi.TIF"
    }

    # Ensure output directories exist
    paths["ndvi_old"].parent.mkdir(parents=True, exist_ok=True)
    paths["ndvi_new"].parent.mkdir(parents=True, exist_ok=True)

    with ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(
                compute_indices, 
                paths["red_band_old"], 
                paths["nir_band_old"], 
                paths["ndvi_old"], 
                paths["savi_old"], 
                paths["ndvi_old"].with_suffix(".png"), 
                paths["savi_old"].with_suffix(".png")
            ),
            executor.submit(
                compute_indices, 
                paths["red_band_new"], 
                paths["nir_band_new"], 
                paths["ndvi_new"], 
                paths["savi_new"], 
                paths["ndvi_new"].with_suffix(".png"), 
                paths["savi_new"].with_suffix(".png")
            )
        ]

        for future in as_completed(futures):
            future.result()
            
import rasterio
import numpy as np
import json
import sys
from pathlib import Path  
import cv2
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import time

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Get Folder Paths from Command Line
start_folder = Path(sys.argv[1])
end_folder = Path(sys.argv[2])

# Load Configuration
with open('config.json', 'r') as f:
    config = json.load(f)

L = config["L"]
NDVI_THRESHOLD = config["ndvi_threshold"]
SAVI_THRESHOLD = config["savi_threshold"]
DEFORESTATION_ALERT_THRESHOLD = config["deforestation_alert_threshold"]
CLOUD_SHADOW_THRESHOLD = config["cloud_shadow_threshold"]
BRIGHTNESS_THRESHOLD = config["brightness_threshold"]

def apply_cloud_shadow_mask(red, nir):
    """Applies cloud and shadow mask based on brightness threshold."""
    brightness = (red + nir) / 2
    mask = brightness > CLOUD_SHADOW_THRESHOLD
    red[mask] = np.nan
    nir[mask] = np.nan
    return red, nir

def dark_object_subtraction(band):
    """Applies Dark Object Subtraction (DOS) for atmospheric correction."""
    dark_object_value = np.nanpercentile(band, 1)
    corrected = band - dark_object_value
    corrected[corrected < 0] = 0
    return corrected

def save_as_png(data, output_png_path):
    """Normalizes and saves the data as a PNG image."""
    min_val, max_val = np.nanmin(data), np.nanmax(data)
    normalized = ((data - min_val) / (max_val - min_val) * 255).astype(np.uint8)
    cv2.imwrite(str(output_png_path), normalized)
    logging.info(f"Saved PNG: {output_png_path}")

def compute_indices(red_band_path, nir_band_path, output_ndvi_path, output_savi_path, ndvi_png_path, savi_png_path, L=L):
    """Computes NDVI and SAVI indices from the red and NIR bands."""
    try:
        with rasterio.open(red_band_path, mmap=True, num_threads="all_cpus") as red_src, \
             rasterio.open(nir_band_path, mmap=True, num_threads="all_cpus") as nir_src:

            red = red_src.read(1).astype(np.float32)
            nir = nir_src.read(1).astype(np.float32)

            # Apply Atmospheric Correction
            red = dark_object_subtraction(red)
            nir = dark_object_subtraction(nir)

            # Apply Cloud and Shadow Masking
            red, nir = apply_cloud_shadow_mask(red, nir)

            np.seterr(divide='ignore', invalid='ignore')
            ndvi = (nir - red) / (nir + red)
            savi = ((nir - red) / (nir + red + L)) * (1 + L)

            meta = red_src.meta
            meta.update(dtype=rasterio.float32, count=1)

            # Write NDVI and SAVI to disk
            with rasterio.open(output_ndvi_path, 'w', **meta, num_threads="all_cpus") as ndvi_dst:
                ndvi_dst.write(ndvi, 1)
            with rasterio.open(output_savi_path, 'w', **meta, num_threads="all_cpus") as savi_dst:
                savi_dst.write(savi, 1)
            
            # Save PNGs for visualization
            save_as_png(ndvi, ndvi_png_path)
            save_as_png(savi, savi_png_path)

        logging.info(f"Computed indices for: {red_band_path} and {nir_band_path}")
    except Exception as e:
        logging.error(f"Error in computing indices: {e}")

def compare_indices(old_path, new_path, output_change_path):
    """Compares two indices and calculates change."""
    try:
        with rasterio.open(old_path, mmap=True, num_threads="all_cpus") as old_src, \
             rasterio.open(new_path, mmap=True, num_threads="all_cpus") as new_src:
             
            old_data, new_data = old_src.read(1).astype(np.float32), new_src.read(1).astype(np.float32)
            min_rows, min_cols = min(old_data.shape[0], new_data.shape[0]), min(old_data.shape[1], new_data.shape[1])
            change = new_data[:min_rows, :min_cols] - old_data[:min_rows, :min_cols]

            meta = old_src.meta
            meta.update(dtype=rasterio.float32, count=1, height=min_rows, width=min_cols)
            with rasterio.open(output_change_path, 'w', **meta, num_threads="all_cpus") as dst:
                dst.write(change, 1)

        logging.info(f"Compared indices: {old_path} vs {new_path}")
    except Exception as e:
        logging.error(f"Error in comparing indices: {e}")

def detect_deforestation(ndvi_change_path, savi_change_path):
    """Detects deforestation using NDVI and SAVI change thresholds."""
    try:
        with rasterio.open(ndvi_change_path, mmap=True, num_threads="all_cpus") as ndvi_src, \
             rasterio.open(savi_change_path, mmap=True, num_threads="all_cpus") as savi_src:

            ndvi_change, savi_change = ndvi_src.read(1), savi_src.read(1)
            deforested_pixels = np.sum((ndvi_change < NDVI_THRESHOLD) & (savi_change < SAVI_THRESHOLD))
            deforestation_percentage = round((deforested_pixels / ndvi_change.size) * 100, 2)
            result = {
                "deforestation_percentage": deforestation_percentage,
                "status": "🚨 Significant deforestation detected!" if deforestation_percentage > DEFORESTATION_ALERT_THRESHOLD else "✅ No significant deforestation detected."
            }
        
        logging.info(json.dumps(result))
    except Exception as e:
        logging.error(f"Error in detecting deforestation: {e}")

def parallel_processes():
    """Manages parallel computation of indices and comparisons."""
    base_path = Path(__file__).resolve().parent
    input_folder = config["input_folder"]
    output_folder = config["output_folder"]
    
    # Define paths and ensure output directories exist
    paths = {
        "red_band_old": base_path / input_folder / start_folder / "band4.TIF",
        "nir_band_old": base_path / input_folder / start_folder / "band5.TIF",
        "ndvi_old": base_path / output_folder / start_folder / "ndvi.TIF",
        "savi_old": base_path / output_folder / start_folder / "savi.TIF",
        "red_band_new": base_path / input_folder / end_folder / "band4.TIF",
        "nir_band_new": base_path / input_folder / end_folder / "band5.TIF",
        "ndvi_new": base_path / output_folder / end_folder / "ndvi.TIF",
        "savi_new": base_path / output_folder / end_folder / "savi.TIF"
    }

    # Ensure output directories exist
    paths["ndvi_old"].parent.mkdir(parents=True, exist_ok=True)
    paths["ndvi_new"].parent.mkdir(parents=True, exist_ok=True)

    with ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(
                compute_indices, 
                paths["red_band_old"], 
                paths["nir_band_old"], 
                paths["ndvi_old"], 
                paths["savi_old"], 
                paths["ndvi_old"].with_suffix(".png"), 
                paths["savi_old"].with_suffix(".png")
            ),
            executor.submit(
                compute_indices, 
                paths["red_band_new"], 
                paths["nir_band_new"], 
                paths["ndvi_new"], 
                paths["savi_new"], 
                paths["ndvi_new"].with_suffix(".png"), 
                paths["savi_new"].with_suffix(".png")
            )
        ]

        for future in as_completed(futures):
            future.result()
            
    ndvi_change_path = base_path / output_folder / "ndvi_change.TIF"
    savi_change_path = base_path / output_folder / "savi_change.TIF"

    compare_indices(paths["ndvi_old"], paths["ndvi_new"], ndvi_change_path)
    compare_indices(paths["savi_old"], paths["savi_new"], savi_change_path)

    # Detect Deforestation
    detect_deforestation(ndvi_change_path, savi_change_path)            


            

if __name__ == "__main__":
    start_time = time.time()
    parallel_processes()
    logging.info(f"Processing completed in {time.time() - start_time:.2f} seconds.")
