#!/usr/bin/env python3
"""
Test the deployed geo-compliance model endpoint
"""

import boto3
import json
import time

# Configuration
REGION = "us-west-2"
ENDPOINT_NAME = "geo-compliance-config"

def test_endpoint():
    """Test the deployed endpoint with a sample query"""
    
    print(f"🧪 Testing endpoint: {ENDPOINT_NAME}")
    
    # Create runtime client
    runtime_client = boto3.client('sagemaker-runtime', region_name=REGION)
    
    # Test case - Content Moderation feature
    test_input = {
        "instruction": "Analyze the following software feature to determine its geo-compliance requirements. Provide the compliance flag, the relevant law, and the reason.",
        "input": """Feature Name: Content Moderation Dashboard
Feature Description: A dashboard for moderators to review and remove illegal content from the platform.

Law Context (structured JSON):
{
  "title": "Digital Services Act",
  "citation": "Regulation (EU) 2022/2065",
  "article": "Article 14",
  "section": "Notice and Action",
  "date": "2022",
  "uri": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32022R2065",
  "page": 45,
  "source": "EU Official Journal",
  "snippet": "Providers shall put in place mechanisms allowing users to notify them of illegal content and act expeditiously to remove such content."
}"""
    }
    
    # Format the input for the model (same format as training)
    prompt = f"### Instruction:\n{test_input['instruction']}\n\n### Input:\n{test_input['input']}\n\n### Response:\n"
    
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 256,
            "temperature": 0.1,
            "do_sample": True,
            "top_p": 0.9
        }
    }
    
    try:
        print("📤 Sending request...")
        response = runtime_client.invoke_endpoint(
            EndpointName=ENDPOINT_NAME,
            ContentType='application/json',
            Body=json.dumps(payload)
        )
        
        result = json.loads(response['Body'].read().decode())
        print("✅ Success!")
        print("\n🤖 Model Response:")
        print("=" * 50)
        print(result['generated_text'])
        print("=" * 50)
        
        return result
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def check_endpoint_status():
    """Check if endpoint is ready"""
    sagemaker_client = boto3.client('sagemaker', region_name=REGION)
    
    try:
        response = sagemaker_client.describe_endpoint(EndpointName=ENDPOINT_NAME)
        status = response['EndpointStatus']
        print(f"📊 Endpoint Status: {status}")
        return status == 'InService'
    except Exception as e:
        print(f"❌ Error checking status: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Testing Geo-Compliance Model Endpoint")
    print("=" * 50)
    
    # Check if endpoint is ready
    if not check_endpoint_status():
        print("⏳ Endpoint not ready yet. Please wait for 'InService' status.")
        return
    
    # Test the endpoint
    result = test_endpoint()
    
    if result:
        print("\n🎉 Endpoint test completed successfully!")
        print("📝 You can now use this endpoint for real-time compliance analysis")
    else:
        print("\n❌ Endpoint test failed")

if __name__ == "__main__":
    main()
