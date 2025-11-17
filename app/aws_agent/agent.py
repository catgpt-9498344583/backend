"""
agent.py

This module defines the Agent class, which wraps the AWS Bedrock Agent Runtime
API using boto3. It allows sending natural language prompts to a Bedrock agent
and receiving streamed responses.

Features:
- Loads AWS credentials and config from a local `.env`-style file
- Connects to the AWS Bedrock Agent Runtime
- Maintains a unique session ID per agent instance
- Supports invocation of Bedrock agents with prompt input
"""

from uuid import UUID
import uuid
import os
import boto3
from datetime import datetime, timedelta
import threading


class Agent:
    _instances: dict[UUID, "Agent"] = {}
    _last_activity: dict[UUID, datetime] = {}
    _client = None
    _deletion_lock = threading.Lock()

    # ---------------------------
    # ENV + CLIENT INITIALIZATION
    # ---------------------------

    @classmethod
    def _load_env(cls):
        try:
            with open(".env") as f:
                for line in f:
                    key, value = line.strip().split("=")
                    os.environ[key] = value
        except Exception:
            pass

    @classmethod
    def _init_client(cls):
        if cls._client is not None:
            return cls._client

        cls._load_env()

        try:
            cls._client = boto3.client(
                "bedrock-agent-runtime",
                region_name=os.getenv("AWS_DEFAULT_REGION"),
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            )
        except Exception as e:
            print(f"[Agent] Error initializing Bedrock client: {e}")
            cls._client = None

        return cls._client

    # ---------------------------
    # AGENT INSTANCES
    # ---------------------------

    def __init__(self, session_id: UUID = None):
        self.session_id = session_id or uuid.uuid4()
        self.client = Agent._init_client()

    @classmethod
    def _cleanup_old_instances(cls):
        """Remove any agents that haven't been accessed for more than TTL."""
        now = datetime.utcnow()
        expired = [sid for sid, ts in cls._last_access.items()
                   if now - ts > cls._TTL]
        for sid in expired:
            print(f"[Agent] Removing expired session {sid}")
            cls._instances.pop(sid, None)
            cls._last_access.pop(sid, None)

    @classmethod
    def get_or_create(cls, session_id: str | UUID | None):
        try:
            session_id = UUID(str(session_id)) if session_id else uuid.uuid4()
        except Exception:
            session_id = uuid.uuid4()

        if session_id not in cls._instances:
            cls._instances[session_id] = Agent(session_id=session_id)

        cls._last_activity[session_id] = datetime.utcnow()
        return cls._instances[session_id]

    @classmethod
    def mark_for_deletion(cls, session_id: UUID):
        """Schedule agent deletion 3 minutes after last activity."""
        def delete_later():
            with cls._deletion_lock:
                last_time = cls._last_activity.get(session_id)
                if not last_time:
                    return  # already deleted

                if datetime.utcnow() - last_time >= timedelta(minutes=3):
                    cls._instances.pop(session_id, None)
                    cls._last_activity.pop(session_id, None)
                    print(f"[Agent] Session {session_id} deleted.")

        # Schedule the check in 3 minutes
        timer = threading.Timer(180, delete_later)
        timer.daemon = True
        timer.start()

    def invoke(self, prompt: str) -> dict | None:
        """Invoke Bedrock Agent and return JSON for the frontend.

        Updates the last access time to prevent premature deletion.
        """
        # Update last activity timestamp
        Agent._last_activity[self.session_id] = datetime.utcnow()

        if not self.client:
            print(f"[Agent] Bedrock not initialized {self.session_id}.")
            return {"error": "Bedrock client not initialized."}

        try:
            response = self.client.invoke_agent(
                agentId=os.getenv("AGENT_ID"),
                agentAliasId=os.getenv("AGENT_ALIAS_ID"),
                sessionId=str(self.session_id),
                inputText=prompt,
            )

            output = ""
            # Some events may not have 'chunk' or 'bytes', so safeguard
            for event in response.get("completion", []):
                chunk_data = event.get("chunk", {}).get("bytes")
                if chunk_data:
                    output += chunk_data.decode(errors="ignore")

            return {
                "response": output,
                "sessionId": str(self.session_id),
            }

        except Exception as e:
            print(f"[Agent] Error invoking agent {self.session_id}: {e}")
            return {"error": str(e), "sessionId": str(self.session_id)}
