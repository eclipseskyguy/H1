from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  # ✅ Allow all origins

@app.route('/')
def home():
    return jsonify({"message": "Hello from Flask!"})

@app.route('/data')
def get_data():
    return jsonify({"name": "Streamlit API", "status": "running"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
