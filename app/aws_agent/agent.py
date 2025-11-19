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
    _client = None
    _instances: dict[UUID, "Agent"] = {}
    _pending_delete: set[UUID] = set()
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

    def __init__(self, session_id: UUID):
        self.session_id = session_id or uuid.uuid4()
        self.client = Agent._init_client()

    @classmethod
    def get_or_create(cls, session_id: str | UUID | None):
        try:
            session_id = UUID(str(session_id)) if session_id else uuid.uuid4()
        except Exception:
            session_id = uuid.uuid4()

        if session_id not in cls._instances:
            cls._instances[session_id] = Agent(session_id=session_id)

        return cls._instances[session_id]

    @classmethod
    def mark_for_deletion(cls, session_id: UUID):
        """Schedule this session to be deleted exactly 3 minutes after disconnect,
        regardless of any later incoming activity.
        """
        # Mark the session as scheduled for deletion
        cls._pending_delete.add(session_id)
        print(f"[Agent] Session {session_id} marked for deletion.")

        def delete_later():
            with cls._deletion_lock:
                if session_id in cls._pending_delete:
                    cls._instances.pop(session_id, None)
                    cls._pending_delete.discard(session_id)
                    print(f"[Agent] Session {session_id} deleted (3m timer).")

        # Schedule deletion 3 minutes from now
        timer = threading.Timer(180, delete_later)
        timer.daemon = True
        timer.start()

    def invoke(self, prompt: str) -> dict | None:
        """Invoke Bedrock Agent and return JSON for the frontend.

        Updates last_activity only if the session is NOT pending deletion.
        """
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
