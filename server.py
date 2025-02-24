from flask import Flask, request, redirect, url_for, send_from_directory
import os
from literature import process_file

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def index():
    return send_from_directory('.', 'interface.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'epubfile' not in request.files:
        return "No file part", 400
    file = request.files['epubfile']
    if file.filename == '':
        return "No selected file", 400
    if file:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)
        try:
            # Process the file using literature.py
            result = process_file(filepath)
            # Verify that the output map file exists
            if not os.path.exists("locations_map.html"):
                return "Map file not generated", 500
        except Exception as e:
            print("Error processing file:", e)
            return f"Error processing file: {e}", 500
        os.remove(filepath)
        return redirect(url_for('show_map'))
    return "File upload failed", 400

@app.route('/map')
def show_map():
    # Serve the generated map file (locations_map.html)
    return send_from_directory('.', 'locations_map.html')

if __name__ == '__main__':
    app.run(debug=True)
