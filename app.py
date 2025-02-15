from flask import Flask, request, jsonify
import os

app = Flask(__name__)

# Define the upload folder
UPLOAD_FOLDER = '/Users/kartik/Downloads/NDVI output'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files["file"]
    
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(filepath)
    
    # Perform operations on the file (example: return filename)
    return jsonify({"message": "File uploaded successfully", "filename": file.filename})

if __name__ == "__main__":
    app.run(debug=True)