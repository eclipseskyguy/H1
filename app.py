import streamlit as st
import rasterio
import numpy as np
from pathlib import Path  

st.title("🌿 NDVI & Deforestation Detection App")

# 📂 File uploaders
red_old = st.file_uploader("Upload Old Red Band (B4)", type=["tif"])
nir_old = st.file_uploader("Upload Old NIR Band (B5)", type=["tif"])
red_new = st.file_uploader("Upload New Red Band (B4)", type=["tif"])
nir_new = st.file_uploader("Upload New NIR Band (B5)", type=["tif"])

if st.button("Process NDVI"):
    if red_old and nir_old and red_new and nir_new:
        # Save uploaded files temporarily
        temp_dir = Path("temp")
        temp_dir.mkdir(exist_ok=True)

        old_red_path = temp_dir / red_old.name
        old_nir_path = temp_dir / nir_old.name
        new_red_path = temp_dir / red_new.name
        new_nir_path = temp_dir / nir_new.name

        with open(old_red_path, "wb") as f: f.write(red_old.getbuffer())
        with open(old_nir_path, "wb") as f: f.write(nir_old.getbuffer())
        with open(new_red_path, "wb") as f: f.write(red_new.getbuffer())
        with open(new_nir_path, "wb") as f: f.write(nir_new.getbuffer())

        def calculate_ndvi(red_path, nir_path):
            with rasterio.open(red_path) as red_src, rasterio.open(nir_path) as nir_src:
                red = red_src.read(1).astype(np.float32)
                nir = nir_src.read(1).astype(np.float32)

                ndvi = (nir - red) / (nir + red)
                return ndvi

        ndvi_old = calculate_ndvi(old_red_path, old_nir_path)
        ndvi_new = calculate_ndvi(new_red_path, new_nir_path)

        ndvi_change = ndvi_new - ndvi_old
        deforestation_percentage = np.sum(ndvi_change < -0.2) / ndvi_change.size * 100

        # Display results
        st.write(f"🌿 **Deforestation Detected in {deforestation_percentage:.2f}% of the area**")
        if deforestation_percentage > 5:
            st.error("🚨 Significant Deforestation Detected!")
        else:
            st.success("✅ No Significant Deforestation Detected.")

    else:
        st.warning("⚠️ Please upload all 4 required files!")