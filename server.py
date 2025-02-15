from flask import Flask, jsonify
from flask_cors import CORS
import subprocess
import json
from pathlib import Path

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

BASE_PATH = Path(__name__).resolve().parent

@app.route('/run-analysis', methods=['GET'])
def run_analysis():
    """Run the NDVI/SAVI analysis script and return JSON results."""
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

        return jsonify(output_json)

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000)
