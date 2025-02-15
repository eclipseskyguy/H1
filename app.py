import streamlit as st
import rasterio
import numpy as np
import os
import tempfile
import matplotlib.pyplot as plt

st.set_page_config(page_title="NDVI Change Detection", layout="wide")

def calculate_ndvi(red_band, nir_band):
    """Computes NDVI from Red & NIR bands."""
    red = red_band.read(1).astype(np.float32)
    nir = nir_band.read(1).astype(np.float32)

    np.seterr(divide="ignore", invalid="ignore")
    ndvi = (nir - red) / (nir + red)

    return ndvi

def compare_ndvi(ndvi_old, ndvi_new):
    """Computes NDVI change map."""
    min_rows = min(ndvi_old.shape[0], ndvi_new.shape[0])
    min_cols = min(ndvi_old.shape[1], ndvi_new.shape[1])

    ndvi_old = ndvi_old[:min_rows, :min_cols]
    ndvi_new = ndvi_new[:min_rows, :min_cols]

    return ndvi_new - ndvi_old

def detect_deforestation(ndvi_change, threshold=-0.2):
    """Detects deforestation based on NDVI change."""
    deforested_pixels = np.sum(ndvi_change < threshold)
    total_pixels = ndvi_change.size
    return (deforested_pixels / total_pixels) * 100

st.title("🌿 NDVI Change Detection")

# File uploaders
st.sidebar.header("Upload Satellite Images")
old_red_files = st.sidebar.file_uploader("Upload Old Red Band(s)", accept_multiple_files=True, type=["tif"])
old_nir_files = st.sidebar.file_uploader("Upload Old NIR Band(s)", accept_multiple_files=True, type=["tif"])
new_red_files = st.sidebar.file_uploader("Upload New Red Band(s)", accept_multiple_files=True, type=["tif"])
new_nir_files = st.sidebar.file_uploader("Upload New NIR Band(s)", accept_multiple_files=True, type=["tif"])

# Check if all files are uploaded
if old_red_files and old_nir_files and new_red_files and new_nir_files:
    if len(old_red_files) != len(old_nir_files) or len(new_red_files) != len(new_nir_files):
        st.sidebar.error("Mismatch in number of red and NIR files.")
    else:
        results = []
        st.sidebar.success("All files uploaded. Click 'Process Data' to continue.")
        if st.sidebar.button("Process Data"):
            for i in range(len(old_red_files)):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".tif") as old_red_tmp, \
                     tempfile.NamedTemporaryFile(delete=False, suffix=".tif") as old_nir_tmp, \
                     tempfile.NamedTemporaryFile(delete=False, suffix=".tif") as new_red_tmp, \
                     tempfile.NamedTemporaryFile(delete=False, suffix=".tif") as new_nir_tmp:

                    old_red_tmp.write(old_red_files[i].getvalue())
                    old_nir_tmp.write(old_nir_files[i].getvalue())
                    new_red_tmp.write(new_red_files[i].getvalue())
                    new_nir_tmp.write(new_nir_files[i].getvalue())

                    with rasterio.open(old_red_tmp.name) as old_red_src, \
                         rasterio.open(old_nir_tmp.name) as old_nir_src, \
                         rasterio.open(new_red_tmp.name) as new_red_src, \
                         rasterio.open(new_nir_tmp.name) as new_nir_src:

                        # Compute NDVI for old and new images
                        ndvi_old = calculate_ndvi(old_red_src, old_nir_src)
                        ndvi_new = calculate_ndvi(new_red_src, new_nir_src)

                        # Compute NDVI change
                        ndvi_change = compare_ndvi(ndvi_old, ndvi_new)

                        # Detect deforestation
                        deforestation_percent = detect_deforestation(ndvi_change)

                        results.append({
                            "ndvi_old": ndvi_old,
                            "ndvi_new": ndvi_new,
                            "ndvi_change": ndvi_change,
                            "deforestation": deforestation_percent
                        })

                        # Display results
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.subheader(f"🛰️ NDVI (Old) - Image {i+1}")
                            plt.imshow(ndvi_old, cmap='RdYlGn', vmin=-1, vmax=1)
                            plt.colorbar()
                            st.pyplot(plt.gcf())

                        with col2:
                            st.subheader(f"🛰️ NDVI (New) - Image {i+1}")
                            plt.imshow(ndvi_new, cmap='RdYlGn', vmin=-1, vmax=1)
                            plt.colorbar()
                            st.pyplot(plt.gcf())

                        with col3:
                            st.subheader(f"🌍 NDVI Change - Image {i+1}")
                            plt.imshow(ndvi_change, cmap='coolwarm', vmin=-1, vmax=1)
                            plt.colorbar()
                            st.pyplot(plt.gcf())

                        st.write(f"🚨 **Deforestation Detected: {deforestation_percent:.2f}%**")