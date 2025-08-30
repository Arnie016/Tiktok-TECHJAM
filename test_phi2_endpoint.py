#!/usr/bin/env python3
"""
Test the actual phi-2 endpoint to understand its format
"""

import boto3
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

ENDPOINT_NAME = "phi-2"
REGION = "us-west-2"

def test_format_1():
    """Test with Hugging Face format"""
    logger.info("🧪 Testing Hugging Face format...")
    session = boto3.Session(profile_name='bedrock-561', region_name=REGION)
    rt = session.client('sagemaker-runtime')

    payload = {
        "inputs": "Analyze this feature: User authentication system",
        "parameters": {"max_new_tokens": 100, "temperature": 0.7, "do_sample": True}
    }

    try:
        resp = rt.invoke_endpoint(
            EndpointName=ENDPOINT_NAME,
            ContentType='application/json',
            Body=json.dumps(payload)
        )
        result = json.loads(resp['Body'].read().decode())
        logger.info("✅ Hugging Face format works!")
        logger.info(json.dumps(result, indent=2))
        return True
    except Exception as e:
        logger.error(f"❌ Hugging Face format failed: {e}")
        return False

def test_format_2():
    """Test with instruction/input format"""
    logger.info("🧪 Testing instruction/input format...")
    session = boto3.Session(profile_name='bedrock-561', region_name=REGION)
    rt = session.client('sagemaker-runtime')

    payload = {
        "instruction": "Analyze the following software feature to determine its geo-compliance requirements.",
        "input": "Feature Name: User Authentication\nFeature Description: System that collects user location data."
    }

    try:
        resp = rt.invoke_endpoint(
            EndpointName=ENDPOINT_NAME,
            ContentType='application/json',
            Body=json.dumps(payload)
        )
        result = json.loads(resp['Body'].read().decode())
        logger.info("✅ Instruction/input format works!")
        logger.info(json.dumps(result, indent=2))
        return True
    except Exception as e:
        logger.error(f"❌ Instruction/input format failed: {e}")
        return False

def main():
    logger.info("🎯 Testing phi-2 endpoint formats...")
    
    # Test both formats
    format1_works = test_format_1()
    format2_works = test_format_2()
    
    if format1_works:
        logger.info("✅ Use Hugging Face format: {'inputs': '...', 'parameters': {...}}")
    elif format2_works:
        logger.info("✅ Use instruction/input format: {'instruction': '...', 'input': '...'}")
    else:
        logger.error("❌ Both formats failed - endpoint might have issues")

if __name__ == "__main__":
    main()
