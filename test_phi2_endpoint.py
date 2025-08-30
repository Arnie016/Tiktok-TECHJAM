#!/usr/bin/env python3
"""
Test script for phi-2 SageMaker endpoint
"""

import json
import boto3
import time
from botocore.config import Config

def test_phi2_endpoint():
    """Test the phi-2 SageMaker endpoint"""
    
    # Configure boto3 with the bedrock profile
    session = boto3.Session(profile_name='bedrock-561', region_name='us-west-2')
    runtime = session.client('sagemaker-runtime', config=Config(read_timeout=120))
    
    endpoint_name = 'phi-2'
    
    # Test cases
    test_cases = [
        {
            "name": "Simple hello",
            "payload": {"inputs": "Hello, how are you?"}
        },
        {
            "name": "Instruction format", 
            "payload": {"instruction": "Say hello", "input": "Test input"}
        },
        {
            "name": "Training data format",
            "payload": {
                "instruction": "Analyze the following software feature to determine its geo-compliance requirements. Provide the compliance flag, the relevant law, and the reason.",
                "input": "Feature Name: FL Anonymous Age Verification\nFeature Description: Provides anonymous/third-party age verification for adult/'harmful to minors' content and deletes verification data, limited to Florida users.\nSource: Doe v. Roblox Corp., 602 F. Supp. 3d 1243.PDF\n\nLaw Context (structured JSON):\n[]"
            }
        }
    ]
    
    print(f"Testing endpoint: {endpoint_name}")
    print("=" * 50)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test_case['name']}")
        print("-" * 30)
        
        try:
            # Convert payload to JSON string
            body = json.dumps(test_case['payload'])
            
            print(f"Request: {body[:100]}...")
            
            # Invoke endpoint
            start_time = time.time()
            response = runtime.invoke_endpoint(
                EndpointName=endpoint_name,
                ContentType='application/json',
                Body=body
            )
            
            # Parse response
            result = json.loads(response['Body'].read().decode())
            end_time = time.time()
            
            print(f"Response time: {end_time - start_time:.2f}s")
            print(f"Response: {json.dumps(result, indent=2)}")
            
        except Exception as e:
            print(f"Error: {str(e)}")
            print(f"Error type: {type(e).__name__}")
            
        print()

if __name__ == "__main__":
    test_phi2_endpoint()

