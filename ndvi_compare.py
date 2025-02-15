import rasterio
import numpy as np

def compare_ndvi(ndvi_old_path, ndvi_new_path, output_change_path):
    with rasterio.open(ndvi_old_path) as old_src, rasterio.open(ndvi_new_path) as new_src:
        ndvi_old = old_src.read(1).astype(np.float32)
        ndvi_new = new_src.read(1).astype(np.float32)

        # Get the minimum common shape
        min_rows = min(ndvi_old.shape[0], ndvi_new.shape[0])
        min_cols = min(ndvi_old.shape[1], ndvi_new.shape[1])

        
        ndvi_old = ndvi_old[:min_rows, :min_cols]
        ndvi_new = ndvi_new[:min_rows, :min_cols]

        ndvi_change = ndvi_new - ndvi_old

        # Define output metadata
        meta = old_src.meta
        meta.update(dtype=rasterio.float32, count=1, height=min_rows, width=min_cols)

    
        with rasterio.open(output_change_path, 'w', **meta) as dst:
            dst.write(ndvi_change, 1)
    
    print(f'NDVI change map saved at: {output_change_path}')

def detect_deforestation(ndvi_change_path, threshold=-0.2):
    with rasterio.open(ndvi_change_path) as src:
        ndvi_change = src.read(1)

        deforested_pixels = np.sum(ndvi_change < threshold)
        total_pixels = ndvi_change.size
        deforestation_percentage = (deforested_pixels / total_pixels) * 100

        print(f'Deforestation detected in {deforestation_percentage:.2f}% of the area')
        
        if deforestation_percentage > 5: 
            print("Significant deforestation detected!")
        else:
            print("No significant deforestation detected.")


ndvi_old = "C:/Users/rajat/OneDrive/Documents/Coding Projects/H1/ndvis/ndvi-older.tif" 
ndvi_new = "C:/Users/rajat/OneDrive/Documents/Coding Projects/H1/ndvis/ndvi-new.tif" 
output_change = "ndvi_change.tif"

compare_ndvi(ndvi_old, ndvi_new, output_change)
detect_deforestation(output_change)
