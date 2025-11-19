# pylint: disable=redefined-outer-name
"""Tests for chat-related Flask routes including /api/hello, /api/chat, and /api/disconnect."""

import uuid
from unittest.mock import patch, MagicMock

import pytest
from flask import Flask
from botocore.exceptions import EndpointConnectionError, ClientError

from app.routes import chat as chat_routes
from app.aws_agent import Agent


# -----------------------------
# Fixtures
# -----------------------------
@pytest.fixture
def app() -> Flask:
    """Create a Flask app with chat routes registered."""
    flask_app = Flask(__name__)
    chat_routes.register_chat_routes(flask_app)
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def client(app):
    """Provide a Flask test client."""
    return app.test_client()


# -----------------------------
# HELLO ROUTE
# -----------------------------
def test_hello(client):
    """Test /api/hello returns 200 with expected JSON."""
    resp = client.get("/api/hello")
    assert resp.status_code == 200
    assert resp.get_json() == {"message": "Hello from backend!"}


# -----------------------------
# CHAT ROUTE
# -----------------------------
@pytest.mark.parametrize(
    "json_body,agent_return,agent_exception,expected_status,expected_json",
    [
        # Missing JSON body
        (None, None, None, 400, {"error": "Missing JSON body"}),
        # Missing prompt
        ({"sessionId": str(uuid.uuid4())}, None, None, 400,
         {"error": "Missing 'prompt' in request body"}),
        # Successful invocation with sessionId
        ({"prompt": "Hello", "sessionId": str(uuid.uuid4())},
         {"text": "Hi!"}, None, 200, {"text": "Hi!"}),
        # Successful invocation without sessionId
        ({"prompt": "Hello"}, {"text": "Hi!"}, None, 200, {"text": "Hi!"}),
        # Agent.invoke returns None
        ({"prompt": "Hello"}, None, None, 500,
         {"error": "Agent invocation failed"}),
        # ClientError with ResourceNotFoundException
        ({"prompt": "Hello"}, None, ClientError(
            {"Error": {"Code": "ResourceNotFoundException",
                       "Message": "Not Found"}}, "Invoke"),
         404, {"error": "AWS ClientError [ResourceNotFoundException]: Not Found"}),
        # ClientError other
        ({"prompt": "Hello"}, None, ClientError(
            {"Error": {"Code": "SomeError", "Message": "Oops"}}, "Invoke"),
         500, {"error": "AWS ClientError [SomeError]: Oops"}),
        # BotoCoreError
        (
            {"prompt": "Hello"},
            None,
            EndpointConnectionError(endpoint_url="https://example.com"),
            502,
            {
                "error":
                'AWS BotoCoreError: Could not connect to the endpoint URL: "https://example.com"'
            }
        ),
        # Python-level error
        ({"prompt": "Hello"}, None, RuntimeError("fail"), 500,
         {"error": "Agent invocation failed: RuntimeError: fail"}),
    ],
)
def test_chat_route(client, json_body, agent_return, agent_exception, expected_status, expected_json):  # pylint: disable=too-many-arguments,too-many-positional-arguments,line-too-long
    """Test /api/chat for various request and agent outcomes."""
    with patch.object(Agent, "get_or_create") as mock_get:
        mock_agent = MagicMock()
        if agent_exception:
            mock_agent.invoke.side_effect = agent_exception
        else:
            mock_agent.invoke.return_value = agent_return
        mock_get.return_value = mock_agent

        # Use json=None only if json_body is not None
        if json_body is None:
            resp = client.post("/api/chat")
        else:
            resp = client.post("/api/chat", json=json_body)

        assert resp.status_code == expected_status
        assert resp.get_json() == expected_json


# -----------------------------
# DISCONNECT ROUTE
# -----------------------------
@pytest.mark.parametrize(
    "json_body,expected_status,expected_json",
    [
        # Missing JSON body
        (None, 400, {"error": "Missing JSON body"}),
        # Missing sessionId
        ({}, 400, {"error": "Missing JSON body"}),
        # Invalid sessionId
        ({"sessionId": "not-a-uuid"}, 400, {"error": "Invalid sessionId"}),
        # Successful disconnect
        ({"sessionId": str(uuid.uuid4())}, 200, {"status": "ok"}),
    ],
)
def test_disconnect_route(client, json_body, expected_status, expected_json):
    """Test /api/disconnect route for missing or invalid sessionId."""
    with patch.object(Agent, "mark_for_deletion") as mock_mark:
        resp = client.post("/api/disconnect", json=json_body)
        assert resp.status_code == expected_status
        assert resp.get_json() == expected_json
        if expected_status == 200:
            assert mock_mark.called


# -----------------------------
# EDGE CASE: unexpected exception
# -----------------------------
def test_disconnect_unexpected_exception(client):
    """Test /api/disconnect handles unexpected exceptions gracefully."""
    with patch.object(Agent, "mark_for_deletion", side_effect=Exception("oops")):
        resp = client.post("/api/disconnect",
                           json={"sessionId": str(uuid.uuid4())})
        assert resp.status_code == 500
        assert "Unexpected error" in resp.get_json().get("error")
