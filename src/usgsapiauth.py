import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

import base64
import json

def authenticate():
    url = "https://m2m.cr.usgs.gov/api/api/json/stable/login-token"
    payload = {
        "username": os.getenv("USGS_USERNAME"),
        "token": os.getenv("USGS_API_TOKEN")
    }

    try:
        print("Authenticating with USGS API...")
        response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
        print("Raw Response Status Code:", response.status_code)
        print("Raw Response Text:", response.text)
        response.raise_for_status()

        data = response.json()
        print("Auth Response:", data)

        if data.get("errorCode"):
            raise ValueError(f"Auth Failed: {data.get('errorMessage')}")

        # Decode Base64 data field
        decoded_data = base64.b64decode(data["data"]).decode("utf-8")
        json_data = json.loads(decoded_data)  # Convert to JSON

        print("Decoded Auth Data:", json.dumps(json_data, indent=2))
        return json_data  # Return decoded JSON object

    except requests.RequestException as error:
        print("Authentication Error:", error)
        return None
    
def search_datasets(api_key):
    url = "https://m2m.cr.usgs.gov/api/api/json/stable/dataset-search"
    payload = {"datasetName": "Landsat"}
    
    try:
        print("Searching for datasets...")
        response = requests.post(url, json=payload, headers={
            "Content-Type": "application/json",
            "X-Auth-Token": api_key
        })
        print("Raw Response Status Code:", response.status_code)
        print("Raw Response Text:", response.text)
        response.raise_for_status()
        data = response.json()
        
        with open("datasets.json", "w") as file:
            json.dump(data.get("data"), file, indent=2)
        
        print("Available Datasets:", data)
    except requests.RequestException as error:
        print("Dataset Search Error:", error)

if __name__ == "__main__":
    api_key = authenticate()
    if api_key:
        search_datasets(api_key)
