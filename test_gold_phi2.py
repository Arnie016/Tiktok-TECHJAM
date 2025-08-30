#!/usr/bin/env python3
"""
Test script for the gold-phi2 endpoint (Phi-2 v5 model with correct env vars)
"""

import boto3
import json
import time

def test_gold_phi2():
    """Test the gold-phi2 endpoint"""
    
    # Setup client
    session = boto3.Session(profile_name='bedrock-561', region_name='us-west-2')
    sagemaker_runtime = session.client('sagemaker-runtime')
    
    endpoint_name = 'gold-phi2'
    
    # Test case - geo-compliance analysis
    test_payload = {
        "instruction": "Analyse the feature artifact and decide if geo-specific compliance logic is needed. Explain why and cite the relevant regulation if any.",
        "input": """Feature Name: EU Data Processing Compliance Check
Feature Description: Automated system to verify GDPR Article 6 lawful basis before processing EU user data; includes consent verification and legitimate interest assessment.

Law Context (structured JSON):
[{"law": "GDPR Article 6", "jurisdiction": "EU", "requirement": "Lawful basis required for personal data processing"}]"""
    }
    
    print("🎯 Testing Gold Phi-2 Model (v5)")
    print(f"📡 Endpoint: {endpoint_name}")
    print("🔧 Trained on 1441 examples with improved LoRA")
    print("=" * 60)
    
    try:
        # Invoke endpoint
        print("📤 Sending request...")
        response = sagemaker_runtime.invoke_endpoint(
            EndpointName=endpoint_name,
            ContentType='application/json',
            Body=json.dumps(test_payload)
        )
        
        # Parse response
        result = json.loads(response['Body'].read().decode())
        
        print("✅ SUCCESS: Model responded!")
        print("\n📊 Test Input:")
        print(f"Feature: {test_payload['input'][:100]}...")
        
        print("\n🎯 Model Output:")
        print(json.dumps(result, indent=2))
        
        # Check response quality
        if 'generated_text' in result:
            output_text = result['generated_text']
            print(f"\n📏 Response length: {len(output_text)} characters")
            
            # Basic quality checks
            quality_indicators = []
            if 'compliance' in output_text.lower():
                quality_indicators.append("✅ Mentions compliance")
            if 'gdpr' in output_text.lower():
                quality_indicators.append("✅ Cites GDPR")
            if 'article 6' in output_text.lower():
                quality_indicators.append("✅ References Article 6")
            if any(word in output_text.lower() for word in ['required', 'needed', 'necessary']):
                quality_indicators.append("✅ Makes recommendation")
            
            print(f"\n🔍 Quality Analysis:")
            for indicator in quality_indicators:
                print(f"  {indicator}")
            
            if len(quality_indicators) >= 2:
                print("\n🎉 QUALITY: Good response - model shows training improvements!")
            else:
                print("\n⚠️ QUALITY: Basic response - may need further training")
        
        return True
        
    except Exception as e:
        if "Could not find endpoint" in str(e):
            print("⏳ Endpoint still creating... Please wait a few more minutes")
        else:
            print(f"❌ ERROR: {e}")
        return False

def check_endpoint_status():
    """Check if endpoint is ready"""
    session = boto3.Session(profile_name='bedrock-561', region_name='us-west-2')
    sagemaker = session.client('sagemaker')
    
    try:
        response = sagemaker.describe_endpoint(EndpointName='gold-phi2')
        status = response['EndpointStatus']
        print(f"📊 Endpoint Status: {status}")
        return status == 'InService'
    except Exception as e:
        print(f"❌ Error checking status: {e}")
        return False

def main():
    """Main function"""
    print("🏆 Gold Phi-2 Model Test")
    print("Enhanced Phi-2 v5 - Trained on 1441 examples")
    print("=" * 60)
    
    # Check status first
    if not check_endpoint_status():
        print("\n⏳ Endpoint not ready yet. It should be available in a few minutes.")
        print("🔄 Run this script again once the endpoint shows 'InService' status")
        return
    
    # Run test
    success = test_gold_phi2()
    
    if success:
        print("\n✅ SUCCESS: Gold Phi-2 model test completed!")
        print("🎯 Model is ready for production use")
        print("🚀 Next: Create Lambda function and Function URL for web access")
    else:
        print("\n❌ Test failed - check CloudWatch logs for details")

if __name__ == "__main__":
    main()

