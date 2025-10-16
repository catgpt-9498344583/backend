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

import uuid
import os
import boto3


class Agent:
    """
    AI Agent wrapper for AWS Bedrock Agent Runtime.

    This class handles initialization and communication with an
    AWS Bedrock agent using boto3. It reads credentials from a local
    file (../../env), sets up the client, and provides an `invoke()` method
    for sending prompts to the agent.

    Attributes:
        agent (boto3.client): The initialized Bedrock agent client.
        session_id (str): A unique session ID for managing conversation context.
    """

    def __init__(self):
        """
        Initializes the Bedrock agent client and session.

        Reads AWS credentials and configuration from a local `../../env` file.
        Then sets up a boto3 client for the Bedrock Agent Runtime API and
        creates a unique session ID.
        """

        # Read keys from env file
        try:
            with open("../../env") as f:
                for line in f:
                    key, value = line.strip().split("=")
                    if key and value:
                        os.environ[key] = value

            # Initialize the client
            self.agent = boto3.client(
                "bedrock-agent-runtime",
                region_name=os.getenv("AWS_DEFAULT_REGION"),
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            )

            # Create a unique session ID for the conversation
            self.session_id = str(uuid.uuid4())

        except Exception as e:
            print(f"Error initializing Agent: {e}")
            self.agent = None

    def invoke(self, prompt):
        """
        Sends a prompt to the Bedrock agent and returns the generated response.

        Args:
            prompt (str): The user's input message or question.

        Returns:
            str or None: The generated response text from the agent,
                         or None if an error occurred.
        """

        try:
            # Invoke the agent with the prompt
            response = self.agent.invoke_agent(
                agentId=os.getenv("AGENT_ID"),
                agentAliasId=os.getenv("AGENT_ALIAS_ID"),
                sessionId=self.session_id,
                inputText=prompt,
            )

            completion = ""
            for event in response.get("completion"):
                chunk = event["chunk"]
                completion += chunk["bytes"].decode()

            return completion

        except Exception as e:
            print(f"Error invoking agent: {e}")
            return None
