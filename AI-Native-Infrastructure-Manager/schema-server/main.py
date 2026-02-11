
from flask import Flask, send_from_directory, abort
import os

app = Flask(__name__)

import argparse

# Parse arguments
parser = argparse.ArgumentParser()
parser.add_argument('--schema-dir', default=os.environ.get('SCHEMA_DIR', '/data/schemas'))
parser.add_argument('--listen', default='0.0.0.0:5001')
args = parser.parse_args()

SCHEMA_DIR = args.schema_dir

@app.route('/health', methods=['GET'])
def health():
    return {"status": "healthy", "success": True}, 200

@app.route('/<app_name>', methods=['GET'])
def get_schema(app_name):
    # Ensure the file exists
    filename = f"{app_name}.schema.json"
    if not os.path.exists(os.path.join(SCHEMA_DIR, filename)):
        abort(404)
    return send_from_directory(SCHEMA_DIR, filename)

if __name__ == '__main__':
    host, port = args.listen.split(':')
    app.run(host=host, port=int(port))
