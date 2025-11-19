"""
routes/__init__.py

This module serves as the entry point for registering all API routes
in the Flask application. It imports individual route registration
functions and calls them in one place for centralized management.
"""

from .chat import register_chat_routes


# Register routes
def register_all_routes(app):
    """
    Registers all routes for the Flask app.

    Args:
        app (Flask): The Flask application instance.
        agent (Agent): An instance of the AI agent used for processing chat requests.

    This function should be called from the app factory (e.g., `create_app`)
    and will register all endpoint groups (e.g., chat routes).
    """

    print("Registering routes...")
    register_chat_routes(app)
