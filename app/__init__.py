"""
Flask application factory.

This module sets up and returns the Flask app instance, including:
- CORS configuration
- Static file serving (for frontend app)
- Agent initialization (e.g., AWS Bedrock)
- Route registration for all APIs
"""

import os
from flask import Flask, send_from_directory
from flask_cors import CORS

from app.routes import register_all_routes


def create_app():
    """
    Application factory for initializing and configuring the Flask app.

    This function performs the following tasks:
    - Creates the Flask app with static folder settings
    - Enables CORS for development frontend URLs
    - Initializes the AI Agent (e.g., AWS Bedrock wrapper)
    - Registers all API routes using the agent
    - Serves static frontend files (e.g., from a React build)

    Returns:
        Flask: The fully configured Flask app instance
    """

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
        """
        Serve static frontend files or fallback to index.html for SPA routing.

        Args:
            path (str): The path requested by the client (e.g., "/about")

        Returns:
            File: The requested static file, or index.html for unknown routes
        """

        static_dir = app.static_folder
        full_path = os.path.join(static_dir, path)

        # Reroute to index.html
        if path != "" and os.path.exists(full_path):
            return send_from_directory(static_dir, path)

        return send_from_directory(static_dir, 'index.html')

    return app
