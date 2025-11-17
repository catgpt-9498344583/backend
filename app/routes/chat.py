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
from uuid import UUID, uuid4
from app.aws_agent import Agent


def register_chat_routes(app):
    """
    Registers chat-related API routes to the given Flask app.

    The route now obtains or creates the correct Agent instance
    using Agent.get_agent(session_id).
    """

    @app.route('/api/hello')
    def hello():
        return {"message": "Hello from backend!"}

    @app.route('/api/chat', methods=['POST'])
    def chat():
        # Parse JSON body
        data = request.get_json()
        print("Received request: ", data)

        if not data:
            return jsonify({"error": "Missing JSON body"}), 400

        prompt = data.get("prompt")
        session_id = data.get("sessionId")

        if not prompt:
            return jsonify({"error": "Missing 'prompt' in request body"}), 400

        # Get or create the correct agent for this session
        agent_instance = Agent.get_or_create(session_id)

        # Invoke AWS agent
        result = agent_instance.invoke(prompt)

        if result is None:
            return jsonify({"error": "Agent invocation failed"}), 500

        return jsonify(result), 200

    @app.route('/api/disconnect', methods=['POST'])
    def disconnect():
        data = request.get_json()
        if not data or 'sessionId' not in data:
            return jsonify({"error": "Missing sessionId"}), 400

        session_id = data['sessionId']
        try:
            session_uuid = UUID(session_id)
        except Exception:
            return jsonify({"error": "Invalid sessionId"}), 400

        Agent.mark_for_deletion(session_uuid)
        return jsonify({"status": "ok"}), 200
