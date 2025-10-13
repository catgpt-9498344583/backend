import os
from flask import Flask, send_from_directory
from flask_cors import CORS

from app.routes import register_all_routes


def create_app():
    print("Creating app...")
    app = Flask(__name__, static_folder="static", static_url_path="")

    CORS(app, origins=[
        "http://localhost:5173",
        "http://172.18.0.3:5173"
    ])
    register_all_routes(app)

    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_frontend(path):
        static_dir = app.static_folder
        full_path = os.path.join(static_dir, path)

        # Reroute to index.html
        if path != "" and os.path.exists(full_path):
            return send_from_directory(static_dir, path)
        else:
            return send_from_directory(static_dir, 'index.html')

    return app
