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
from botocore.exceptions import BotoCoreError, ClientError
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
        print("Received hello request")
        return jsonify({"message": "Hello from backend!"}), 200

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
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "Missing JSON body"}), 400

            prompt = data.get("prompt")
            session_id = data.get("sessionId")

            # Prompt is required, sessionId is optional
            if not prompt:
                return jsonify({"error": "Missing 'prompt' in request body"}), 400

            # Retrieve or create (sessionId is None) the Agent tied to this session
            agent_instance = Agent.get_or_create(session_id)

            # Send the prompt to AWS Bedrock
            result = agent_instance.invoke(prompt)
            if result is None:
                return jsonify({"error": "Agent invocation failed"}), 500

            return jsonify(result), 200

        except ClientError as e:
            # Handles AWS service errors (including ResourceNotFoundException)
            code = e.response.get("Error", {}).get("Code", type(e).__name__)
            msg = e.response.get("Error", {}).get("Message", str(e))
            status = 404 if code == "ResourceNotFoundException" else 500
            return jsonify({"error": f"AWS ClientError [{code}]: {msg}"}), status

        except BotoCoreError as e:
            # Handles network or configuration errors (EndpointConnectionError etc.)
            return jsonify({"error": f"AWS BotoCoreError: {str(e)}"}), 502

        except (ValueError, TypeError, RuntimeError) as e:
            # Expected Python-level errors
            return jsonify({"error": f"Agent invocation failed: {type(e).__name__}: {str(e)}"}), 500

        except Exception as e:  # pylint: disable=broad-except
            # Fallback for any unexpected errors
            return jsonify({"error": f"Unexpected error: {type(e).__name__}: {str(e)}"}), 500

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
        try:
            data = request.get_json(silent=True)
            if not data:
                return jsonify({"error": "Missing JSON body"}), 400
            if "sessionId" not in data:
                return jsonify({"error": "Missing sessionId"}), 400

            session_id = data["sessionId"]

            try:
                session_uuid = UUID(session_id)
            except ValueError:
                return jsonify({"error": "Invalid sessionId"}), 400

            Agent.mark_for_deletion(session_uuid)
            return jsonify({"status": "ok"}), 200

        except Exception as e:  # pylint: disable=broad-except
            return jsonify({"error": f"Unexpected error: {type(e).__name__}: {str(e)}"}), 500
