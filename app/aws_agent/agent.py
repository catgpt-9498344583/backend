"""
agent.py

This module defines the Agent class, a lightweight wrapper around the AWS
Bedrock Agent Runtime API using boto3. It encapsulates session management,
agent invocation, cleanup logic, and environment configuration.

Key Responsibilities:
- Load AWS credentials/configuration from a local `.env` file
- Initialize a shared Bedrock Agent Runtime client
- Maintain per-session Agent instances identified by UUID
- Allow external callers to invoke an agent via natural-language prompts
- Support session cleanup triggered by an external `/disconnect` call
"""

from uuid import UUID
import uuid
import os
import threading
import boto3


class Agent:
    """Manages AWS Bedrock agent sessions, invocation, and delayed cleanup.

    Each Agent instance is tied to a session UUID and shares a single
    Bedrock client. Sessions can be marked for deletion by an external
    disconnect call, triggering a 3-minute timer for cleanup.
    """
    # Shared Bedrock client (lazily initialized once)
    _client = None

    # Mapping of session UUID → Agent instance
    _instances: dict[UUID, "Agent"] = {}

    # Sessions marked for deletion (after 3 minutes)
    _pending_delete: set[UUID] = set()

    # Prevent race conditions between timer threads
    _deletion_lock = threading.Lock()

    # ----------------------------------------------------------------------
    # ENVIRONMENT + CLIENT INITIALIZATION
    # ----------------------------------------------------------------------

    @classmethod
    def _load_env(cls):
        """Load environment variables manually from a local `.env` file.

        This avoids external dependencies like python-dotenv while still
        making local development convenient.
        """
        try:
            with open(".env", encoding="utf-8") as f:
                for line in f:
                    key, value = line.strip().split("=")
                    os.environ[key] = value
        except FileNotFoundError:
            print("Error .env file not found")
        except ValueError:
            print("Error parsing .env file")

    @classmethod
    def _init_client(cls):
        """Initialize (or return existing) boto3 Bedrock Agent Runtime client.

        Returns:
            boto3.Client: The initialized client.
            None: Setup failed.
        """
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
        except boto3.exceptions.Boto3Error as e:
            print(f"[Agent] Error initializing Bedrock client: {e}")
            cls._client = None

        return cls._client

    # ----------------------------------------------------------------------
    # AGENT INSTANCE CREATION + SESSION MANAGEMENT
    # ----------------------------------------------------------------------

    def __init__(self, session_id: UUID):
        """Create an agent instance tied to a specific session UUID."""
        self.session_id = session_id or uuid.uuid4()
        self.client = Agent._init_client()

    @classmethod
    def get_or_create(cls, session_id: str | UUID | None):
        """Retrieve an existing Agent instance for a session, or create one.

        Args:
            session_id: A string UUID, UUID object, or None.

        Returns:
            Agent: The associated Agent instance.
        """
        # Safely normalize input into a UUID
        try:
            session_id = UUID(str(session_id)) if session_id else uuid.uuid4()
        except ValueError:
            session_id = uuid.uuid4()

        # Create a new agent if one doesn't exist yet
        if session_id not in cls._instances:
            cls._instances[session_id] = Agent(session_id=session_id)

        return cls._instances[session_id]

    @classmethod
    def mark_for_deletion(cls, session_id: UUID):
        """Mark a session for deletion exactly 3 minutes after disconnect.

        This function is triggered only by the `/disconnect` backend route.
        A timer thread will delete the session from memory after the delay
        unless the session has already been removed.
        """
        cls._pending_delete.add(session_id)
        print(f"[Agent] Session {session_id} marked for deletion.")

        def delete_later():
            """Delete the session if it is still pending after the timer."""
            with cls._deletion_lock:
                if session_id in cls._pending_delete:
                    cls._instances.pop(session_id, None)
                    cls._pending_delete.discard(session_id)
                    print(f"[Agent] Session {session_id} deleted (3m timer).")

        # Schedule deletion 3 minutes from now
        timer = threading.Timer(180, delete_later)
        timer.daemon = True
        timer.start()

    # ----------------------------------------------------------------------
    # BEDROCK INVOCATION
    # ----------------------------------------------------------------------

    def invoke(self, prompt: str) -> dict | None:
        """Send a natural-language prompt to the AWS Bedrock agent.

        Args:
            prompt: The user's input text.

        Returns:
            dict: Response payload including agent output and sessionId.
                  Contains {"error": "..."} if invocation failed.
        """
        if not self.client:
            print(f"[Agent] Bedrock not initialized {self.session_id}.")
            return {"error": "Bedrock client not initialized."}

        try:
            # Send prompt to Bedrock agent (streaming enabled)
            response = self.client.invoke_agent(
                agentId=os.getenv("AGENT_ID"),
                agentAliasId=os.getenv("AGENT_ALIAS_ID"),
                sessionId=str(self.session_id),
                inputText=prompt,
            )

            # Parse streaming text chunks into a single output string
            output = ""
            for event in response.get("completion", []):
                chunk_data = event.get("chunk", {}).get("bytes")
                if chunk_data:
                    output += chunk_data.decode(errors="ignore")

            return {
                "response": output,
                "sessionId": str(self.session_id),
            }

        except boto3.exceptions.Boto3Error as e:
            print(f"[Agent] Error invoking agent {self.session_id}: {e}")
            return {"error": str(e), "sessionId": str(self.session_id)}
