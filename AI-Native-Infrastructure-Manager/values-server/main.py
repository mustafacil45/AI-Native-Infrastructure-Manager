
from flask import Flask, send_from_directory, abort, request, jsonify
import os
import json

app = Flask(__name__)

import argparse

# Parse arguments
parser = argparse.ArgumentParser()
parser.add_argument('--schema-dir', dest='values_dir', default=os.environ.get('VALUES_DIR', '/data/values')) # Requirement calls it schema-dir but implies values
parser.add_argument('--listen', default='0.0.0.0:5002')
args = parser.parse_args()

VALUES_DIR = args.values_dir

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"success": True, "status": "healthy"}), 200

@app.route('/<app_name>', methods=['GET', 'POST'])
def handle_values(app_name):
    # Güvenlik: Sadece izin verilen karakterler
    if not app_name.isalnum():
        return jsonify({"error": "Invalid app name"}), 400

    file_path = os.path.join(VALUES_DIR, f"{app_name}.value.json")

    if request.method == 'POST':
        try:
            new_data = request.json
            with open(file_path, 'w') as f:
                json.dump(new_data, f, indent=2)
            return jsonify({"status": "success", "message": "Values updated"}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # GET Request
    try:
        if not os.path.exists(file_path):
             return jsonify({"error": "App not found"}), 404
        
        with open(file_path, 'r') as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    host, port = args.listen.split(':')
    app.run(host=host, port=int(port))
