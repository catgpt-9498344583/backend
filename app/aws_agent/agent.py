import boto3
import uuid
import os

class Agent:

    def __init__(self):

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
