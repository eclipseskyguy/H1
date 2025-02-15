import rasterio
import numpy as np

# Function to compare two NDVI images and detect changes
def compare_ndvi(ndvi_old_path, ndvi_new_path, output_change_path):
    with rasterio.open(ndvi_old_path) as old_src, rasterio.open(ndvi_new_path) as new_src:
        ndvi_old = old_src.read(1).astype(np.float32)
        ndvi_new = new_src.read(1).astype(np.float32)

        # Get the minimum common shape
        min_rows = min(ndvi_old.shape[0], ndvi_new.shape[0])
        min_cols = min(ndvi_old.shape[1], ndvi_new.shape[1])

        # Crop both images to the same size
        ndvi_old = ndvi_old[:min_rows, :min_cols]
        ndvi_new = ndvi_new[:min_rows, :min_cols]

        # Compute NDVI difference
        ndvi_change = ndvi_new - ndvi_old

        # Define output metadata
        meta = old_src.meta
        meta.update(dtype=rasterio.float32, count=1, height=min_rows, width=min_cols)

        # Save NDVI change map as a new TIFF file
        with rasterio.open(output_change_path, 'w', **meta) as dst:
            dst.write(ndvi_change, 1)
    
    print(f'NDVI change map saved at: {output_change_path}')

# Function to determine if deforestation has occurred
def detect_deforestation(ndvi_change_path, threshold=-0.2):
    with rasterio.open(ndvi_change_path) as src:
        ndvi_change = src.read(1)

        # Count the number of pixels with significant NDVI decrease
        deforested_pixels = np.sum(ndvi_change < threshold)
        total_pixels = ndvi_change.size
        deforestation_percentage = (deforested_pixels / total_pixels) * 100

        print(f'Deforestation detected in {deforestation_percentage:.2f}% of the area')
        
        if deforestation_percentage > 5:  # Example threshold for significant deforestation
            print("Significant deforestation detected!")
        else:
            print("No significant deforestation detected.")

# Example usage
ndvi_old = "C:/Users/rajat/OneDrive/Documents/Coding Projects/H1/ndvis/ndvi-older.tif"  # Update with your old NDVI file path
ndvi_new = "C:/Users/rajat/OneDrive/Documents/Coding Projects/H1/ndvis/ndvi-new.tif" 
output_change = "ndvi_change.tif"

compare_ndvi(ndvi_old, ndvi_new, output_change)
detect_deforestation(output_change)
