#!/usr/bin/env python3
"""
Simple test for testphi endpoint using different approaches
"""

import boto3
import json
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Configuration
ENDPOINT_NAME = "testphi"
REGION = "us-west-2"

def setup_aws_session():
    """Setup AWS session with profile"""
    logger.info(f"🔧 Setting up AWS session with profile: bedrock-561")
    session = boto3.Session(profile_name='bedrock-561', region_name=REGION)
    sagemaker_client = session.client('sagemaker-runtime')
    return sagemaker_client

def test_with_custom_attributes(sagemaker_client):
    """Test with custom attributes"""
    logger.info("🧪 Testing with custom attributes...")
    
    test_payload = {
        "inputs": "What are the geo-compliance requirements for age verification features in Florida?",
        "parameters": {
            "max_new_tokens": 256,
            "temperature": 0.7,
            "do_sample": True
        }
    }
    
    try:
        response = sagemaker_client.invoke_endpoint(
            EndpointName=ENDPOINT_NAME,
            ContentType='application/json',
            Body=json.dumps(test_payload),
            CustomAttributes='HF_TASK=text-generation'
        )
        
        result = json.loads(response['Body'].read().decode())
        logger.info("✅ Custom attributes test successful!")
        logger.info(f"📊 Response: {json.dumps(result, indent=2)}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Custom attributes test failed: {e}")
        return False

def test_with_task_header(sagemaker_client):
    """Test with task in payload"""
    logger.info("🧪 Testing with task in payload...")
    
    test_payload = {
        "inputs": "What are the geo-compliance requirements for age verification features in Florida?",
        "parameters": {
            "max_new_tokens": 256,
            "temperature": 0.7,
            "do_sample": True,
            "task": "text-generation"
        }
    }
    
    try:
        response = sagemaker_client.invoke_endpoint(
            EndpointName=ENDPOINT_NAME,
            ContentType='application/json',
            Body=json.dumps(test_payload)
        )
        
        result = json.loads(response['Body'].read().decode())
        logger.info("✅ Task in payload test successful!")
        logger.info(f"📊 Response: {json.dumps(result, indent=2)}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Task in payload test failed: {e}")
        return False

def test_direct_text(sagemaker_client):
    """Test with direct text input"""
    logger.info("🧪 Testing with direct text input...")
    
    test_payload = "What are the geo-compliance requirements for age verification features in Florida?"
    
    try:
        response = sagemaker_client.invoke_endpoint(
            EndpointName=ENDPOINT_NAME,
            ContentType='text/plain',
            Body=test_payload
        )
        
        result = response['Body'].read().decode()
        logger.info("✅ Direct text test successful!")
        logger.info(f"📊 Response: {result}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Direct text test failed: {e}")
        return False

def test_alternative_format(sagemaker_client):
    """Test with alternative format"""
    logger.info("🧪 Testing with alternative format...")
    
    test_payload = {
        "instruction": "What are the geo-compliance requirements for age verification features in Florida?"
    }
    
    try:
        response = sagemaker_client.invoke_endpoint(
            EndpointName=ENDPOINT_NAME,
            ContentType='application/json',
            Body=json.dumps(test_payload)
        )
        
        result = json.loads(response['Body'].read().decode())
        logger.info("✅ Alternative format test successful!")
        logger.info(f"📊 Response: {json.dumps(result, indent=2)}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Alternative format test failed: {e}")
        return False

def main():
    """Main function"""
    logger.info("🚀 Testing testphi endpoint with different approaches...")
    
    try:
        # Setup AWS session
        sagemaker_client = setup_aws_session()
        
        # Test different approaches
        tests = [
            ("Custom Attributes", test_with_custom_attributes),
            ("Task in Payload", test_with_task_header),
            ("Direct Text", test_direct_text),
            ("Alternative Format", test_alternative_format)
        ]
        
        results = []
        for test_name, test_func in tests:
            logger.info(f"\n{'='*50}")
            logger.info(f"Testing: {test_name}")
            logger.info(f"{'='*50}")
            success = test_func(sagemaker_client)
            results.append((test_name, success))
        
        # Summary
        logger.info(f"\n{'='*50}")
        logger.info("SUMMARY")
        logger.info(f"{'='*50}")
        
        working_tests = []
        for test_name, success in results:
            status = "✅ PASS" if success else "❌ FAIL"
            logger.info(f"{test_name}: {status}")
            if success:
                working_tests.append(test_name)
        
        if working_tests:
            logger.info(f"\n🎉 Working approaches: {', '.join(working_tests)}")
            logger.info("🎯 Your endpoint is working! The model can generate responses.")
        else:
            logger.error("❌ No working approaches found. The endpoint may need to be redeployed with correct configuration.")
        
        logger.info(f"\n🔗 Endpoint URL: https://runtime.sagemaker.us-west-2.amazonaws.com/endpoints/{ENDPOINT_NAME}/invocations")
        
    except Exception as e:
        logger.error(f"❌ Error in main: {e}")

if __name__ == "__main__":
    main()






