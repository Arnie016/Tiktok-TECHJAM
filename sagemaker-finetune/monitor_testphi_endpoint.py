#!/usr/bin/env python3
"""
Monitor and test the new testphi endpoint
"""

import boto3
import json
import time
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
    sagemaker_management = session.client('sagemaker')
    return sagemaker_client, sagemaker_management

def monitor_endpoint_status(sagemaker_management):
    """Monitor endpoint status until it's InService"""
    logger.info(f"🔍 Monitoring endpoint: {ENDPOINT_NAME}")
    
    while True:
        try:
            response = sagemaker_management.describe_endpoint(EndpointName=ENDPOINT_NAME)
            status = response['EndpointStatus']
            
            logger.info(f"📊 Endpoint Status: {status}")
            
            if status == 'InService':
                logger.info("✅ Endpoint is ready!")
                return True
            elif status == 'Failed':
                logger.error("❌ Endpoint creation failed!")
                return False
            elif status in ['Creating', 'Updating']:
                logger.info("⏳ Endpoint is still being created/updated...")
                time.sleep(30)  # Wait 30 seconds before checking again
            else:
                logger.warning(f"⚠️ Unknown status: {status}")
                time.sleep(30)
                
        except Exception as e:
            logger.error(f"❌ Error checking endpoint status: {e}")
            time.sleep(30)

def test_endpoint(sagemaker_client):
    """Test the endpoint with different formats"""
    logger.info("🧪 Testing endpoint with different formats...")
    
    # Test formats that worked with the previous endpoint
    test_cases = [
        {
            "name": "Simple Question",
            "payload": {
                "inputs": "What are the geo-compliance requirements for age verification features in Florida?"
            }
        },
        {
            "name": "Detailed Analysis Request",
            "payload": {
                "inputs": "Analyze the following software feature to determine its geo-compliance requirements. Provide the compliance flag, the relevant law, and the reason.\n\nFeature Name: FL Anonymous Age Verification\nFeature Description: Provides anonymous/third-party age verification for adult/'harmful to minors' content and deletes verification data, limited to Florida users."
            }
        },
        {
            "name": "With Parameters",
            "payload": {
                "inputs": "What are the key compliance requirements for data deletion in Florida?",
                "parameters": {
                    "max_new_tokens": 256,
                    "temperature": 0.7,
                    "do_sample": True
                }
            }
        }
    ]
    
    results = []
    for i, test_case in enumerate(test_cases, 1):
        logger.info(f"\n{'='*50}")
        logger.info(f"Test {i}: {test_case['name']}")
        logger.info(f"{'='*50}")
        
        try:
            response = sagemaker_client.invoke_endpoint(
                EndpointName=ENDPOINT_NAME,
                ContentType='application/json',
                Body=json.dumps(test_case['payload'])
            )
            
            result = json.loads(response['Body'].read().decode())
            logger.info("✅ Test successful!")
            logger.info(f"📊 Response: {json.dumps(result, indent=2)}")
            results.append((test_case['name'], True, result))
            
        except Exception as e:
            logger.error(f"❌ Test failed: {e}")
            results.append((test_case['name'], False, str(e)))
    
    return results

def main():
    """Main function"""
    logger.info("🚀 Starting testphi endpoint monitoring and testing...")
    
    try:
        # Setup AWS session
        sagemaker_client, sagemaker_management = setup_aws_session()
        
        # Monitor endpoint status
        if monitor_endpoint_status(sagemaker_management):
            # Test endpoint
            results = test_endpoint(sagemaker_client)
            
            # Summary
            logger.info(f"\n{'='*50}")
            logger.info("TEST SUMMARY")
            logger.info(f"{'='*50}")
            
            successful_tests = 0
            for test_name, success, result in results:
                status = "✅ PASS" if success else "❌ FAIL"
                logger.info(f"{test_name}: {status}")
                if success:
                    successful_tests += 1
            
            logger.info(f"\n🎉 {successful_tests}/{len(results)} tests passed!")
            logger.info(f"🔗 Endpoint URL: https://runtime.sagemaker.us-west-2.amazonaws.com/endpoints/{ENDPOINT_NAME}/invocations")
            
        else:
            logger.error("❌ Endpoint is not ready for testing")
            
    except Exception as e:
        logger.error(f"❌ Error in main: {e}")

if __name__ == "__main__":
    main()
