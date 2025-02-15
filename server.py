from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import subprocess
import json
from pathlib import Path

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

BASE_PATH = Path(__file__).resolve().parent
STATIC_PATH = BASE_PATH / "static"

# Ensure static folder exists
STATIC_PATH.mkdir(exist_ok=True)

@app.route('/run-analysis', methods=['GET'])
def run_analysis():
    """Run the NDVI/SAVI analysis script and return JSON results with image links."""
    try:
        result = subprocess.run(['python', 'ndvi_calc.py'], capture_output=True, text=True)

        output_text = result.stdout.strip()

        if result.stderr:
            print("❌ Error in script:", result.stderr)

        if not output_text:
            return jsonify({"status": "error", "message": "No output received from script"}), 500

        try:
            output_json = json.loads(output_text)
        except json.JSONDecodeError:
            return jsonify({"status": "error", "message": "Invalid JSON output from script"}), 500

        # Add URLs for generated images
        image_urls = {
            "nadvi_new": request.host_url + "ndvis/ndvi-new.png",
            "nadvi_old": request.host_url + "ndvis/ndvi-old.png",
            "savi_new": request.host_url + "savis/savi-new.png",
            "savi_old": request.host_url + "savis/savi-old.png"
        }

        response_data = {
            "status": "success",
            "data": output_json,
            "images": image_urls
        }

        return jsonify(response_data)

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/ndvis/<path:filename>')
def serve_ndvis(filename):
    return send_from_directory(BASE_PATH / "ndvis", filename)

@app.route('/savis/<path:filename>')
def serve_savis(filename):
    return send_from_directory(BASE_PATH / "savis", filename)


if __name__ == '__main__':
    app.run(port=5000, debug=True)
