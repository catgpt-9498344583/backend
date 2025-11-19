# pylint: disable=W0621
"""Tests for the backend Flask API and Agent class."""

import os
import uuid
from unittest.mock import patch, MagicMock

import pytest
from flask import Flask
from boto3.exceptions import Boto3Error

from app import create_app
from app.aws_agent.agent import Agent

# -----------------------------
# Fixtures
# -----------------------------


@pytest.fixture
def app_fixture() -> Flask:
    """Create a new Flask app for testing."""
    return create_app()


@pytest.fixture
def client_fixture(app_fixture) -> Flask.test_client:
    """Provide a test client for the Flask app."""
    return app_fixture.test_client()


@pytest.fixture(autouse=True)
def isolate_agent_state():
    """Ensure Agent global state does not leak between tests."""
    # pylint: disable=protected-access
    Agent._instances.clear()
    Agent._pending_delete.clear()
    yield
    Agent._instances.clear()
    Agent._pending_delete.clear()


@pytest.fixture(autouse=True)
def mock_boto3_client(monkeypatch):
    """
    Mock boto3 client so that Agents created in tests do not call AWS.
    This applies globally unless a test explicitly patches boto3.client.
    """
    fake_client = MagicMock()
    fake_client.invoke_agent.return_value = {
        "completion": [{"chunk": {"bytes": b"mock"}}]}
    monkeypatch.setattr("app.aws_agent.agent.boto3.client",
                        lambda *a, **kw: fake_client)


# -----------------------------
# /api/hello
# -----------------------------


def test_hello(client_fixture):
    """Test the /api/hello endpoint returns 200 and correct message."""
    response = client_fixture.get("/api/hello")
    assert response.status_code == 200
    assert response.json == {"message": "Hello from backend!"}


# -----------------------------
# /api/chat
# -----------------------------


@patch("app.routes.chat.Agent.invoke")
def test_chat_success(mock_invoke, client_fixture):
    """Test successful chat invocation returns response and sessionId."""
    mock_invoke.return_value = {
        "response": "Hello",
        "sessionId": str(uuid.uuid4())
    }
    payload = {"prompt": "Hi"}
    response = client_fixture.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json
    assert "response" in data
    assert "sessionId" in data
    mock_invoke.assert_called_once()


@patch("app.routes.chat.Agent.invoke")
def test_chat_invoke_failure(mock_invoke, client_fixture):
    """Ensure route returns 500 when Agent.invoke returns None."""
    mock_invoke.return_value = None
    payload = {"prompt": "Hi"}
    response = client_fixture.post("/api/chat", json=payload)
    assert response.status_code == 500
    assert "error" in response.json


# -----------------------------
# /api/disconnect
# -----------------------------


@patch.object(Agent, "mark_for_deletion")
def test_disconnect_success(mock_mark, client_fixture):
    """Test /api/disconnect successfully schedules deletion."""
    session_id = str(uuid.uuid4())
    payload = {"sessionId": session_id}
    response = client_fixture.post("/api/disconnect", json=payload)
    assert response.status_code == 200
    assert response.json["status"] == "ok"
    mock_mark.assert_called_once()
    called_uuid = mock_mark.call_args[0][0]
    assert str(called_uuid) == session_id


@pytest.mark.parametrize(
    "payload, expected_status, expected_error",
    [
        (None, 400, "Missing JSON body"),
        ({}, 400, "Missing JSON body"),
        ({"sessionId": "invalid-uuid"}, 400, "Invalid sessionId")
    ]
)
def test_disconnect_invalid_cases(
    client_fixture,
    payload,
    expected_status,
    expected_error
):
    """Test invalid /api/disconnect payloads."""
    if payload is None:
        response = client_fixture.post(
            "/api/disconnect", data="", content_type="application/json")
    else:
        response = client_fixture.post("/api/disconnect", json=payload)

    assert response.status_code == expected_status
    data = response.get_json()
    assert data is not None
    assert expected_error in data.get("error", "")


# -----------------------------
# Agent class
# -----------------------------


def test_agent_get_or_create_returns_instance():
    """Test that get_or_create returns an Agent instance."""
    agent = Agent.get_or_create(None)
    assert isinstance(agent, Agent)
    # pylint: disable=protected-access
    assert agent.session_id in Agent._instances


def test_agent_mark_for_deletion_removes_session(monkeypatch):
    """Test Agent.mark_for_deletion removes instance after timer."""
    agent = Agent.get_or_create(None)
    session_id = agent.session_id

    called = {}

    def fake_timer(_, func):
        func()
        called["deleted"] = True
        return MagicMock(start=lambda: None)

    monkeypatch.setattr("threading.Timer", fake_timer)
    Agent.mark_for_deletion(session_id)

    # pylint: disable=protected-access
    assert session_id not in Agent._instances
    assert called.get("deleted") is True


# -----------------------------
# boto3-dependent Agent.invoke tests
# -----------------------------

HAS_DOTENV = os.path.exists(".env")


@pytest.mark.skipif(not HAS_DOTENV, reason=".env not found, skipping AWS tests")
@patch("app.aws_agent.agent.boto3.client")
def test_agent_invoke_success(mock_boto_client):
    """Test successful Agent.invoke returns response and sessionId."""
    fake_response = {"completion": [{"chunk": {"bytes": b"Hello World"}}]}
    mock_client_instance = MagicMock()
    mock_client_instance.invoke_agent.return_value = fake_response
    mock_boto_client.return_value = mock_client_instance

    agent = Agent(uuid.uuid4())
    agent.client = mock_client_instance

    result = agent.invoke("Hi")
    assert result["response"] == "Hello World"
    assert "sessionId" in result


@pytest.mark.skipif(not HAS_DOTENV, reason=".env not found, skipping AWS tests")
@patch("app.aws_agent.agent.boto3.client")
def test_agent_invoke_failure(mock_boto_client):
    """Test Agent.invoke handles Boto3Error and returns error with sessionId."""
    mock_client_instance = MagicMock()
    mock_client_instance.invoke_agent.side_effect = Boto3Error("fail")
    mock_boto_client.return_value = mock_client_instance

    agent = Agent(uuid.uuid4())
    agent.client = mock_client_instance

    result = agent.invoke("Hi")
    assert "error" in result
    assert "sessionId" in result
