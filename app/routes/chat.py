"""
routes/chat.py

This module registers all chat-related HTTP routes for the Flask backend.

It provides:
- A basic health/test endpoint (`/api/hello`)
- A chat endpoint (`/api/chat`) that forwards prompts to an AWS Bedrock agent
- A disconnect endpoint (`/api/disconnect`) that schedules session cleanup

The Agent class (from app.aws_agent) handles all agent lifecycle logic including:
session creation, reuse, timed deletion, and Bedrock invocation.
"""

from uuid import UUID

from flask import request, jsonify

from app.aws_agent import Agent


def register_chat_routes(app):
    """
    Attach chat-related API routes to a Flask application.

    Args:
        app (Flask): The application instance to register routes onto.

    Routes:
        GET  /api/hello       → simple health check
        POST /api/chat        → send a prompt to Bedrock agent
        POST /api/disconnect  → mark a session to be deleted in 3 minutes
    """

    # ----------------------------------------------------------------------
    # BASIC TEST ROUTE
    # ----------------------------------------------------------------------

    @app.route('/api/hello')
    def hello():
        """Simple endpoint used for health checks or quick connectivity tests."""
        return {"message": "Hello from backend!"}

    # ----------------------------------------------------------------------
    # CHAT ROUTE
    # ----------------------------------------------------------------------

    @app.route('/api/chat', methods=['POST'])
    def chat():
        """
        Chat endpoint that forwards a prompt to the AWS Bedrock agent.

        Expected JSON body:
            {
                "prompt": "...",
                "sessionId": "uuid-string"   # optional; auto-created if missing
            }

        Behavior:
        - Validates the incoming request
        - Retrieves (or creates) an Agent instance for the session
        - Invokes the Bedrock agent via Agent.invoke()
        - Returns a JSON response containing output text and sessionId
        """
        data = request.get_json()
        print("Received request: ", data)

        # Ensure JSON body exists
        if not data:
            return jsonify({"error": "Missing JSON body"}), 400

        prompt = data.get("prompt")
        session_id = data.get("sessionId")

        # Prompt is required; sessionId is optional
        if not prompt:
            return jsonify({"error": "Missing 'prompt' in request body"}), 400

        # Retrieve or create the Agent tied to this session
        agent_instance = Agent.get_or_create(session_id)

        # Send the prompt to AWS Bedrock
        result = agent_instance.invoke(prompt)

        # A None return indicates a hard failure in the agent call
        if result is None:
            return jsonify({"error": "Agent invocation failed"}), 500

        return jsonify(result), 200

    # ----------------------------------------------------------------------
    # DISCONNECT ROUTE
    # ----------------------------------------------------------------------

    @app.route('/api/disconnect', methods=['POST'])
    def disconnect():
        """
        Marks a given session for deletion 3 minutes after disconnect.

        This route should be explicitly called by the frontend when the user
        closes the tab, navigates away, or otherwise terminates a session.

        Expected JSON body:
            { "sessionId": "uuid-string" }

        Behavior:
        - Validates sessionId
        - Converts to UUID
        - Schedules delayed deletion using Agent.mark_for_deletion()
        """
        data = request.get_json()

        # Validate body and sessionId presence
        if not data or 'sessionId' not in data:
            return jsonify({"error": "Missing sessionId"}), 400

        session_id = data['sessionId']

        # Validate UUID format
        try:
            session_uuid = UUID(session_id)
        except ValueError:
            return jsonify({"error": "Invalid sessionId"}), 400

        # Schedule deletion (timer handled inside Agent class)
        Agent.mark_for_deletion(session_uuid)
        return jsonify({"status": "ok"}), 200
