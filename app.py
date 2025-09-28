from flask import Flask, send_from_directory
from flask_cors import CORS
import os

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)  # Enable CORS for all routes by default


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    static_dir = app.static_folder
    full_path = os.path.join(static_dir, path)

    if path != "" and os.path.exists(full_path):
        return send_from_directory(static_dir, path)
    else:
        return send_from_directory(static_dir, 'index.html')


@app.route('/api/hello')
def hello():
    return {"message": "Hello from backend!"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
