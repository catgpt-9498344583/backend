import boto3
import os
import uuid

with open(".env") as f:
    for line in f:
        key, value = line.strip().split("=")
        if key and value:
            # print(f"Setting {key}={value} from .env")
            # Set environment variables for boto3 to pick up
            os.environ[key] = value

print(os.environ.get("AWS_DEFAULT_REGION"))
print(os.environ.get("AWS_ACCESS_KEY_ID"))
print(os.environ.get("AWS_SECRET_ACCESS_KEY"))
print(os.environ.get("AGENT_ID"))
print(os.environ.get("AGENT_ALIAS_ID"))

# Initialize the client
bedrock_agent_runtime = boto3.client(
    "bedrock-agent-runtime",
    region_name=os.getenv("AWS_DEFAULT_REGION"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)

# Create a unique session ID for the conversation
session_id = str(uuid.uuid4())

# Your prompt
prompt = "Hello, can you help me with something?"

try:
    # Invoke the agent
    response = bedrock_agent_runtime.invoke_agent(
        agentId=os.getenv("AGENT_ID"),
        agentAliasId=os.getenv("AGENT_ALIAS_ID"),
        sessionId=session_id,
        inputText=prompt,
    )

    # Process the streaming response
    completion = ""
    for event in response.get("completion"):
        chunk = event["chunk"]
        completion += chunk["bytes"].decode()

    print("Agent Response:", completion)

except Exception as e:
    print(f"Error invoking agent: {e}")
