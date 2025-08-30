#!/usr/bin/env python3
import boto3
import json
from botocore.config import Config

# Configure with longer timeout
config = Config(read_timeout=300)  # 5 minutes
session = boto3.Session(profile_name='bedrock-561', region_name='us-west-2')
runtime = session.client('sagemaker-runtime', config=config)

print("Testing phi-2 endpoint with 5-minute timeout...")

try:
    response = runtime.invoke_endpoint(
        EndpointName='phi-2',
        ContentType='application/json',
        Body=json.dumps({"inputs": "Hello"})
    )
    result = response['Body'].read().decode()
    print(f"SUCCESS: {result}")
except Exception as e:
    print(f"ERROR: {e}")
    print(f"Error type: {type(e).__name__}")

