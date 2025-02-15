import requests
import json
import time

# ✅ 1. Set your USGS ESPA credentials
USERNAME = "Rajat"  # Replace with your USGS username
PASSWORD = "QRx/4d2qa-UD3Ra"  # Replace with your USGS password

# ✅ 2. Set your Scene ID (Get this from EarthExplorer)
SCENE_ID = "LC08_L2SP_041027_20231215_02_T1"  # Replace with your real Scene ID

# ✅ 3. Define the API URL
ORDER_URL = "https://espa.cr.usgs.gov/api/v1/order"

# ✅ 4. Define order request payload
order_payload = {
    "format": "gtiff",
    "resampling_method": "cc",
    "resize": None,
    "note": "Landsat NDVI request",
    "products": ["sr"],
    "scenes": ["LC08_L2SP_041027_20231215_02_T1"],  # Request for the specific scene
    "bands": ["sr_b4", "sr_b5"],  # Only request B4 (Red) & B5 (NIR)
    "email": "your-email@example.com"  # Replace with your email to receive status updates
}

# ✅ 5. Send order request to ESPA API
response = requests.post(ORDER_URL, auth=(USERNAME, PASSWORD), headers={"Content-Type": "application/json"}, data=json.dumps(order_payload))

# ✅ 6. Check API Response
if response.status_code == 200:
    order_response = response.json()
    order_id = order_response.get("orderid")
    print(f"✅ Order submitted successfully! Order ID: {order_id}")
else:
    print(f"❌ Failed to submit order: {response.text}")
    exit()

# ✅ 7. Check order status until it's ready for download
STATUS_URL = f"https://espa.cr.usgs.gov/api/v1/order-status/{order_id}"

while True:
    status_response = requests.get(STATUS_URL, auth=(USERNAME, PASSWORD))
    status_data = status_response.json()
    status = status_data.get(order_id, {}).get("status")

    if status == "complete":
        print("✅ Order is ready for download!")
        break
    elif status in ["failed", "cancelled"]:
        print(f"❌ Order failed or was cancelled: {status}")
        exit()
    else:
        print(f"⏳ Order is still processing... Current status: {status}")
    
    time.sleep(60)  # Wait 60 seconds before checking again

# ✅ 8. Retrieve Download Links for B4 & B5
download_urls = []
for scene in status_data[order_id]["products"].values():
    for band, url in scene.items():
        if band in ["sr_b4", "sr_b5"]:  # Only get B4 & B5
            download_urls.append(url)

# ✅ 9. Download the GeoTIFF files
for url in download_urls:
    filename = url.split("/")[-1]  # Extract filename from URL
    print(f"⬇️ Downloading {filename}...")
    
    file_response = requests.get(url, auth=(USERNAME, PASSWORD), stream=True)
    with open(filename, "wb") as file:
        for chunk in file_response.iter_content(chunk_size=1024):
            file.write(chunk)
    
    print(f"✅ Downloaded: {filename}")

print("🎉 All requested Landsat bands (B4 & B5) downloaded successfully!")