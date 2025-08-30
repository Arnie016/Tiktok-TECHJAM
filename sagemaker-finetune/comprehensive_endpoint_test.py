#!/usr/bin/env python3
"""
Comprehensive endpoint testing with different input formats
"""

import boto3
import json
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Configuration
ENDPOINT_NAME = "geo-compliance-endpoint-fixed-lora"
REGION = "us-west-2"

def setup_aws_session():
    """Setup AWS session with profile"""
    logger.info(f"🔧 Setting up AWS session with profile: bedrock-561")
    session = boto3.Session(profile_name='bedrock-561', region_name=REGION)
    sagemaker_client = session.client('sagemaker-runtime')
    return sagemaker_client

def test_format_1(sagemaker_client):
    """Test with Hugging Face standard format"""
    logger.info("🧪 Testing Format 1: Hugging Face standard format")
    
    test_payload = {
        "inputs": "Analyze the following software feature to determine its geo-compliance requirements. Provide the compliance flag, the relevant law, and the reason.\n\nFeature Name: FL Anonymous Age Verification\nFeature Description: Provides anonymous/third-party age verification for adult/'harmful to minors' content and deletes verification data, limited to Florida users.",
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
            Body=json.dumps(test_payload)
        )
        result = json.loads(response['Body'].read().decode())
        logger.info(f"✅ Format 1 Response: {json.dumps(result, indent=2)}")
        return True
    except Exception as e:
        logger.error(f"❌ Format 1 failed: {e}")
        return False

def test_format_2(sagemaker_client):
    """Test with instruction format"""
    logger.info("🧪 Testing Format 2: Instruction format")
    
    test_payload = {
        "instruction": "Analyze the following software feature to determine its geo-compliance requirements. Provide the compliance flag, the relevant law, and the reason.",
        "input": "Feature Name: FL Anonymous Age Verification\nFeature Description: Provides anonymous/third-party age verification for adult/'harmful to minors' content and deletes verification data, limited to Florida users."
    }
    
    try:
        response = sagemaker_client.invoke_endpoint(
            EndpointName=ENDPOINT_NAME,
            ContentType='application/json',
            Body=json.dumps(test_payload)
        )
        result = json.loads(response['Body'].read().decode())
        logger.info(f"✅ Format 2 Response: {json.dumps(result, indent=2)}")
        return True
    except Exception as e:
        logger.error(f"❌ Format 2 failed: {e}")
        return False

def test_format_3(sagemaker_client):
    """Test with simple text input"""
    logger.info("🧪 Testing Format 3: Simple text input")
    
    test_payload = {
        "inputs": "What are the geo-compliance requirements for age verification features in Florida?"
    }
    
    try:
        response = sagemaker_client.invoke_endpoint(
            EndpointName=ENDPOINT_NAME,
            ContentType='application/json',
            Body=json.dumps(test_payload)
        )
        result = json.loads(response['Body'].read().decode())
        logger.info(f"✅ Format 3 Response: {json.dumps(result, indent=2)}")
        return True
    except Exception as e:
        logger.error(f"❌ Format 3 failed: {e}")
        return False

def test_format_4(sagemaker_client):
    """Test with raw text"""
    logger.info("🧪 Testing Format 4: Raw text")
    
    test_payload = "Analyze the following software feature to determine its geo-compliance requirements. Provide the compliance flag, the relevant law, and the reason.\n\nFeature Name: FL Anonymous Age Verification\nFeature Description: Provides anonymous/third-party age verification for adult/'harmful to minors' content and deletes verification data, limited to Florida users."
    
    try:
        response = sagemaker_client.invoke_endpoint(
            EndpointName=ENDPOINT_NAME,
            ContentType='application/json',
            Body=json.dumps(test_payload)
        )
        result = json.loads(response['Body'].read().decode())
        logger.info(f"✅ Format 4 Response: {json.dumps(result, indent=2)}")
        return True
    except Exception as e:
        logger.error(f"❌ Format 4 failed: {e}")
        return False

def test_format_5(sagemaker_client):
    """Test with training data format"""
    logger.info("🧪 Testing Format 5: Training data format")
    
    test_payload = {
        "instruction": "Analyze the following software feature to determine its geo-compliance requirements. Provide the compliance flag, the relevant law, and the reason.",
        "input": "Feature Name: FL Anonymous Age Verification\nFeature Description: Provides anonymous/third-party age verification for adult/'harmful to minors' content and deletes verification data, limited to Florida users.\nSource: h0001z.RRS.pdf\n\nLaw Context (structured JSON):\n[{\"title\": \"Judiciary_JU0003ju_00003.pdf\", \"citation\": null, \"article\": null, \"section\": null, \"date\": null, \"uri\": \"https://arnav-finetune-1756053255.s3.us-west-2.amazonaws.com/data/law/Judiciary_JU0003ju_00003.pdf\", \"page\": null, \"source\": null, \"snippet\": \"...harmful to minors satisfies the bill's age requirements. If an anonymous age verification method is used, the verification must be conducted by a nongovernmental, independent third party organized under the laws of a state of the U.S. Any information used to verify age must be deleted once...\"}]",
        "output": ""
    }
    
    try:
        response = sagemaker_client.invoke_endpoint(
            EndpointName=ENDPOINT_NAME,
            ContentType='application/json',
            Body=json.dumps(test_payload)
        )
        result = json.loads(response['Body'].read().decode())
        logger.info(f"✅ Format 5 Response: {json.dumps(result, indent=2)}")
        return True
    except Exception as e:
        logger.error(f"❌ Format 5 failed: {e}")
        return False

def main():
    """Main function"""
    logger.info("🚀 Starting comprehensive endpoint testing...")
    
    try:
        # Setup AWS session
        sagemaker_client = setup_aws_session()
        
        # Test different formats
        formats = [
            test_format_1,
            test_format_2,
            test_format_3,
            test_format_4,
            test_format_5
        ]
        
        results = []
        for i, test_func in enumerate(formats, 1):
            logger.info(f"\n{'='*50}")
            logger.info(f"Testing Format {i}")
            logger.info(f"{'='*50}")
            success = test_func(sagemaker_client)
            results.append((f"Format {i}", success))
        
        # Summary
        logger.info(f"\n{'='*50}")
        logger.info("SUMMARY")
        logger.info(f"{'='*50}")
        for format_name, success in results:
            status = "✅ PASS" if success else "❌ FAIL"
            logger.info(f"{format_name}: {status}")
        
        working_formats = [name for name, success in results if success]
        if working_formats:
            logger.info(f"\n🎉 Working formats: {', '.join(working_formats)}")
            logger.info(f"🔗 Endpoint URL: https://runtime.sagemaker.us-west-2.amazonaws.com/endpoints/{ENDPOINT_NAME}/invocations")
        else:
            logger.error("❌ No working formats found")
            
    except Exception as e:
        logger.error(f"❌ Error in main: {e}")

if __name__ == "__main__":
    main()






