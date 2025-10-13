from .chat import register_chat_routes


# Register routes
def register_all_routes(app):
    print("Registering routes...")
    register_chat_routes(app)
