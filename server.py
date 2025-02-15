from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import subprocess
import json
from pathlib import Path
import os
import shutil
import atexit

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

BASE_PATH = Path(__file__).resolve().parent
DATA_FOLDER = BASE_PATH / "NDVI B4 B5"
STATIC_PATH = BASE_PATH / "static"

# Ensure static folder exists
STATIC_PATH.mkdir(exist_ok=True)

# Store the selected folder globally
selected_folder = None
image_request_count = 0
TOTAL_IMAGES = 4

@app.route('/set-folder', methods=['POST'])
def set_folder():
    global selected_folder, start_folder, end_folder

    data = request.get_json()
    selected_folder = data.get("folder")

    if not selected_folder:
        return jsonify({"error": "No folder provided"}), 400

    parts = selected_folder.split("_")

    if len(parts) != 2:
        return jsonify({"error": "Invalid folder format. Expected 'start_end' format."}), 400

    start_folder, end_folder = parts

    return jsonify({
        "message": "Folders selected successfully",
        "start_folder": start_folder,
        "end_folder": end_folder
    })


@app.route('/run-analysis', methods=['GET'])
def run_analysis():
    """Run the NDVI/SAVI analysis script and return JSON results with image links."""
    if not selected_folder:
        return jsonify({"status": "error", "message": "No folder selected"}), 400
    
    try:
        ndvi_script = str(BASE_PATH / "ndvi_calc.py")
        result = subprocess.run(
            ['python', ndvi_script, start_folder, end_folder], 
            capture_output=True, text=True
        )

        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)

        if result.stderr:
            return jsonify({"status": "error", "message": result.stderr}), 500
        
        output_text = result.stdout.strip()
        if not output_text:
            return jsonify({"status": "error", "message": "No output received from script"}), 500

        try:
            output_json = json.loads(output_text)
        except json.JSONDecodeError:
            return jsonify({"status": "error", "message": "Invalid JSON output from script"}), 500
        
        image_urls = {
            "ndvi_new": request.host_url + "temp_results/ndvis/ndvi-new.png",
            "ndvi_old": request.host_url + "temp_results/ndvis/ndvi-old.png",
            "savi_new": request.host_url + "temp_results/savis/savi-new.png",
            "savi_old": request.host_url + "temp_results/savis/savi-old.png"
        }


        response_data = {
            "status": "success",
            "data": output_json,
            "images": image_urls
        }

        return jsonify(response_data)

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

import time

def delete_temp_results():
    temp_results_path = BASE_PATH / "temp_results"
    if temp_results_path.exists():
        try:
            # Close all open file handles (Windows issue)
            for file in temp_results_path.rglob("*"):
                try:
                    with open(file, 'rb') as f:
                        pass  # Just attempt to open and close it
                except Exception:
                    pass

            # Give time for release
            time.sleep(1)

            # Now try deleting
            shutil.rmtree(temp_results_path)
            print("Deleted temp_results folder after all images served.")
        except Exception as e:
            print(f"Error deleting temp_results: {e}")


@app.route('/temp_results/savis/<path:filename>')
def serve_savis(filename):
    global image_request_count
    response = send_from_directory(BASE_PATH / "temp_results/savis", filename)
    image_request_count += 1
    if image_request_count >= TOTAL_IMAGES:
        delete_temp_results()
    return response

@app.route('/temp_results/ndvis/<path:filename>')
def serve_ndvis(filename):
    global image_request_count
    response = send_from_directory(BASE_PATH / "temp_results/ndvis", filename)
    image_request_count += 1
    if image_request_count >= TOTAL_IMAGES:
        delete_temp_results()
    return response


@app.route('/get-folders', methods=['GET'])
def get_folders():
    try:
        folders = [f for f in os.listdir(DATA_FOLDER) if os.path.isdir(os.path.join(DATA_FOLDER, f))]
        return jsonify({"folders": sorted(folders)})  # Sorted for consistency
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(port=5000, debug=True)