#!/usr/bin/env python3
"""
Debug script to see actual raw responses from phi-2 endpoint
"""

import json
import boto3
from botocore.config import Config

def debug_responses():
    session = boto3.Session(profile_name='bedrock-561', region_name='us-west-2')
    runtime = session.client('sagemaker-runtime', config=Config(read_timeout=60))
    
    test_cases = [
        {
            "name": "Simple Test",
            "input": {
                "instruction": "Analyze the following software feature to determine its geo-compliance requirements. Provide the compliance flag, the relevant law, and the reason.",
                "input": "Feature Name: FL Anonymous Age Verification\nFeature Description: Provides anonymous/third-party age verification for adult/'harmful to minors' content and deletes verification data, limited to Florida users.\nSource: Doe v. Roblox Corp., 602 F. Supp. 3d 1243.PDF\n\nLaw Context (structured JSON):\n[]"
            }
        }
    ]
    
    for test_case in test_cases:
        print(f"\n🔍 Testing: {test_case['name']}")
        print("-" * 50)
        
        try:
            response = runtime.invoke_endpoint(
                EndpointName='phi-2',
                ContentType='application/json',
                Body=json.dumps(test_case["input"])
            )
            
            raw_response = response['Body'].read().decode()
            print(f"Raw response type: {type(raw_response)}")
            print(f"Raw response length: {len(raw_response)}")
            print(f"Raw response:\n{raw_response}")
            
            # Try to parse as JSON
            try:
                parsed = json.loads(raw_response)
                print(f"\nParsed JSON: {json.dumps(parsed, indent=2)}")
            except json.JSONDecodeError as e:
                print(f"\nJSON parse error: {e}")
                
                # Check if it's in generated_text format
                if "generated_text" in raw_response:
                    try:
                        parsed = json.loads(raw_response)
                        generated_text = parsed.get("generated_text", "")
                        print(f"\nGenerated text: {generated_text}")
                        
                        # Try to extract JSON from generated text
                        import re
                        json_match = re.search(r'\{.*\}', generated_text, re.DOTALL)
                        if json_match:
                            try:
                                extracted_json = json.loads(json_match.group())
                                print(f"\nExtracted JSON: {json.dumps(extracted_json, indent=2)}")
                            except:
                                print("Could not extract valid JSON from generated text")
                    except:
                        print("Could not parse as JSON even with generated_text")
                
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    debug_responses()

