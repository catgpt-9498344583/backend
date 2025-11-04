"""
chat_routes.py

This module defines chat-related API routes for the Flask application.
It includes:

- A simple test route (`/api/hello`)
- A POST route (`/api/chat`) that sends prompts to an AWS Bedrock-powered agent

The `agent` instance must be passed in from the app factory and is expected
to have an `invoke(prompt: str) -> str` method that returns AI-generated responses.
"""

from flask import request, jsonify


def register_chat_routes(app, agent):
    """
    Registers chat-related API routes to the given Flask app.

    Args:
        app (Flask): The Flask application instance.
        agent (Agent): An instance of a class capable of processing prompts and
                       returning responses (e.g., using AWS Bedrock).
    """

    @app.route("/api/hello")
    def hello():
        return {"message": "Hello from backend!"}

    @app.route("/api/chat", methods=["POST"])
    def chat():
        """
        Handles user chat prompts and returns AI-generated responses.

        Request:
            Method: POST
            Content-Type: application/json
            Body: { "prompt": "<user prompt>" }

        Responses:
            200: JSON { "response": "<AI-generated response>" }
                 - Returned when the prompt is successfully processed.
            400: JSON { "error": "Missing 'prompt'" }
                 - Returned when the request body is invalid or prompt is missing.
            500: JSON { "error": "Internal server error message" }
                 - Returned on any unexpected exception (e.g., agent failure).
        """

        data = request.get_json()

        # Error 400
        if not data or "prompt" not in data:
            return jsonify({"error": 'Missing "prompt" in request body'})

        user_prompt = data["prompt"]

        try:
            agent_response = agent.invoke(user_prompt)
            if agent_response is None:
                raise Exception("Error invoking agent.")
            return jsonify({"response": str(agent_response)})
        # Error 500
        except Exception as e:
            # TODO: change to error
            return jsonify({"error": f"An error occurred: {str(e)}"})
