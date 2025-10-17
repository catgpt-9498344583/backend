"""
Application entry point.

This script starts the Flask development server using the application
factory pattern defined in `app.create_app()`.

- Initializes the Flask app
- Runs the app on host 0.0.0.0 (accessible from outside containers)
- Sets the port to 5000
- Enables debug mode for development

Usage:
    python main.py
"""

from app import create_app

app = create_app()

if __name__ == "__main__":
    print("Starting Flask...")
    app.run(host="0.0.0.0", port=5000, debug=True)
