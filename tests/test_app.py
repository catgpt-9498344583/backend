# tests/test_app.py
import uuid
import pytest
from unittest.mock import patch, MagicMock
from flask import Flask
from app import create_app
from app.aws_agent.agent import Agent
from boto3.exceptions import Boto3Error

# -----------------------------
# Fixtures
# -----------------------------


@pytest.fixture
def app() -> Flask:
    """Create a new Flask app for testing."""
    return create_app()


@pytest.fixture
def client(app) -> Flask.test_client:
    """Provide a test client for the Flask app."""
    return app.test_client()


@pytest.fixture(autouse=True)
def isolate_agent_state():
    """Ensure Agent global state does not leak between tests."""
    Agent._instances.clear()
    Agent._pending_delete.clear()
    yield
    Agent._instances.clear()
    Agent._pending_delete.clear()

# -----------------------------
# /api/hello
# -----------------------------


def test_hello(client):
    response = client.get("/api/hello")
    assert response.status_code == 200
    assert response.json == {"message": "Hello from backend!"}

# -----------------------------
# /api/chat
# -----------------------------


@patch("app.routes.chat.Agent.invoke")
def test_chat_success(mock_invoke, client):
    mock_invoke.return_value = {
        "response": "Hello",
        "sessionId": str(uuid.uuid4())
    }
    payload = {"prompt": "Hi"}
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json
    assert "response" in data
    assert "sessionId" in data
    mock_invoke.assert_called_once()


@pytest.mark.parametrize(
    "payload, expected_status, expected_error",
    [
        (None, 415, "Unsupported Media Type"),
        ({}, 400, "Missing JSON body")
    ]
)
def test_chat_invalid_payload(client, payload, expected_status, expected_error):
    if payload is None:
        response = client.post("/api/chat", data="")
    else:
        response = client.post("/api/chat", json=payload)

    assert response.status_code == expected_status
    if response.status_code != 415:  # 415 response has no JSON body
        data = response.get_json()
        assert expected_error in data.get("error", "")


@patch("app.routes.chat.Agent.invoke")
def test_chat_invoke_failure(mock_invoke, client):
    """Ensure route returns 500 when Agent.invoke returns None."""
    mock_invoke.return_value = None
    payload = {"prompt": "Hi"}
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 500
    assert "error" in response.json

# -----------------------------
# /api/disconnect
# -----------------------------


@patch.object(Agent, "mark_for_deletion")
def test_disconnect_success(mock_mark, client):
    session_id = str(uuid.uuid4())
    payload = {"sessionId": session_id}
    response = client.post("/api/disconnect", json=payload)
    assert response.status_code == 200
    assert response.json["status"] == "ok"
    mock_mark.assert_called_once()
    called_uuid = mock_mark.call_args[0][0]
    assert str(called_uuid) == session_id


@pytest.mark.parametrize(
    "payload, expected_status, expected_error",
    [
        (None, 400, "Unsupported Media Type"),
        ({}, 400, "Missing sessionId"),
        ({"sessionId": "invalid-uuid"}, 400, "Invalid sessionId")
    ]
)
def test_disconnect_invalid_cases(client, payload, expected_status, expected_error):
    if payload is None:
        response = client.post("/api/disconnect", data="",
                               content_type="application/json")
    else:
        response = client.post("/api/disconnect", json=payload)

    assert response.status_code == expected_status

    if response.status_code != 400:
        data = response.get_json()
        assert data is not None
        assert expected_error in data.get("error", "")

# -----------------------------
# Frontend fallback route
# -----------------------------


# def test_frontend_fallback(client):
#     """Unknown paths should return index.html (SPA fallback)."""
#     response = client.get("/some/random/path")
#     assert response.status_code == 200
#     assert b"<html" in response.data  # simple check for HTML content

# -----------------------------
# Agent class
# -----------------------------


def test_agent_get_or_create_returns_instance():
    agent = Agent.get_or_create(None)
    assert isinstance(agent, Agent)
    assert agent.session_id in Agent._instances


def test_agent_mark_for_deletion_removes_session(monkeypatch):
    agent = Agent.get_or_create(None)
    session_id = agent.session_id

    called = {}

    def fake_timer(_, func):
        func()
        called["deleted"] = True
        return MagicMock(start=lambda: None)

    monkeypatch.setattr("threading.Timer", fake_timer)
    Agent.mark_for_deletion(session_id)

    assert session_id not in Agent._instances
    assert called.get("deleted") is True


@patch("app.aws_agent.agent.boto3.client")
def test_agent_invoke_success(mock_boto_client):
    fake_response = {"completion": [{"chunk": {"bytes": b"Hello World"}}]}
    mock_client_instance = MagicMock()
    mock_client_instance.invoke_agent.return_value = fake_response
    mock_boto_client.return_value = mock_client_instance

    agent = Agent(uuid.uuid4())
    agent.client = mock_client_instance

    result = agent.invoke("Hi")
    assert result["response"] == "Hello World"
    assert "sessionId" in result


@patch("app.aws_agent.agent.boto3.client")
def test_agent_invoke_failure(mock_boto_client):
    mock_client_instance = MagicMock()
    mock_client_instance.invoke_agent.side_effect = Boto3Error("fail")
    mock_boto_client.return_value = mock_client_instance

    agent = Agent(uuid.uuid4())
    agent.client = mock_client_instance

    result = agent.invoke("Hi")
    assert "error" in result
    assert "sessionId" in result
