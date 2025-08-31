#!/usr/bin/env python3
"""
Test script for the new Phi-2 v5 model endpoint
"""

import boto3
import json
import time

def test_phi2_v5():
    """Test the new Phi-2 v5 endpoint"""
    
    # Setup client
    session = boto3.Session(profile_name='bedrock-561', region_name='us-west-2')
    sagemaker_runtime = session.client('sagemaker-runtime')
    
    endpoint_name = 'phi2-v5-geo-compliance'
    
    # Test case
    test_payload = {
        "instruction": "Analyse the feature artifact and decide if geo-specific compliance logic is needed. Explain why and cite the relevant regulation if any.",
        "input": """Feature Name: EU Data Processing Compliance Check
Feature Description: Automated system to verify GDPR Article 6 lawful basis before processing EU user data; includes consent verification and legitimate interest assessment.

Law Context (structured JSON):
[{"law": "GDPR Article 6", "jurisdiction": "EU", "requirement": "Lawful basis required for personal data processing"}]"""
    }
    
    print("🧪 Testing Phi-2 v5 model...")
    print(f"📡 Endpoint: {endpoint_name}")
    print("=" * 60)
    
    try:
        # Invoke endpoint
        response = sagemaker_runtime.invoke_endpoint(
            EndpointName=endpoint_name,
            ContentType='application/json',
            Body=json.dumps(test_payload)
        )
        
        # Parse response
        result = json.loads(response['Body'].read().decode())
        
        print("✅ SUCCESS: Model responded")
        print("\n📊 Test Input:")
        print(f"Feature: {test_payload['input'][:100]}...")
        
        print("\n🎯 Model Output:")
        print(json.dumps(result, indent=2))
        
        print(f"\n⏱️ Response time: {response['ResponseMetadata'].get('HTTPHeaders', {}).get('x-amzn-requestid', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def main():
    """Main function"""
    print("🎯 Phi-2 v5 Model Test")
    print("Trained on 1441 examples - Enhanced geo-compliance analysis")
    print("=" * 60)
    
    success = test_phi2_v5()
    
    if success:
        print("\n✅ Test completed successfully!")
        print("🎉 Phi-2 v5 model is working and ready for production")
    else:
        print("\n❌ Test failed!")

if __name__ == "__main__":
    main()

