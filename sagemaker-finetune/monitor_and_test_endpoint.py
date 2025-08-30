#!/usr/bin/env python3
"""
Monitor and test the SageMaker endpoint
"""

import boto3
import json
import time
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Configuration
ENDPOINT_NAME = "geo-compliance-config-PHI2"
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
    """Test the endpoint with a sample request"""
    logger.info("🧪 Testing endpoint with sample request...")
    
    # Sample test case
    test_payload = {
        "instruction": "Analyze the following software feature to determine its geo-compliance requirements. Provide the compliance flag, the relevant law, and the reason.",
        "input": "Feature Name: FL Anonymous Age Verification\nFeature Description: Provides anonymous/third-party age verification for adult/'harmful to minors' content and deletes verification data, limited to Florida users.\nSource: h0001z.RRS.pdf\n\nLaw Context (structured JSON):\n[{\"title\": \"Judiciary_JU0003ju_00003.pdf\", \"citation\": null, \"article\": null, \"section\": null, \"date\": null, \"uri\": \"https://arnav-finetune-1756053255.s3.us-west-2.amazonaws.com/data/law/Judiciary_JU0003ju_00003.pdf\", \"page\": null, \"source\": null, \"snippet\": \"...harmful to minors satisfies the bill's age requirements. If an anonymous age verification method is used, the verification must be conducted by a nongovernmental, independent third party organized under the laws of a state of the U.S. Any information used to verify age must be deleted once...\"}, {\"title\": \"PDF.pdf\", \"citation\": null, \"article\": null, \"section\": null, \"date\": null, \"uri\": \"https://arnav-finetune-1756053255.s3.us-west-2.amazonaws.com/data/law/PDF.pdf\", \"page\": null, \"source\": null, \"snippet\": \"...501.1737, Florida Statutes, is created 282 to read: 283 501.1737 Age verification for online access to materials 284 harmful to minors.— 285 (1) As used in this section, the term: 286 (a) \\\"Anonymous age verification\\\" has the same meaning as 287 in s. 501.1738. 288 (b...\"}]"
    }
    
    try:
        # Invoke endpoint
        response = sagemaker_client.invoke_endpoint(
            EndpointName=ENDPOINT_NAME,
            ContentType='application/json',
            Body=json.dumps(test_payload)
        )
        
        # Parse response
        result = json.loads(response['Body'].read().decode())
        
        logger.info("✅ Endpoint test successful!")
        logger.info(f"📊 Response: {json.dumps(result, indent=2)}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Endpoint test failed: {e}")
        return False

def main():
    """Main function"""
    logger.info("🚀 Starting endpoint monitoring and testing...")
    
    try:
        # Setup AWS session
        sagemaker_client, sagemaker_management = setup_aws_session()
        
        # Monitor endpoint status
        if monitor_endpoint_status(sagemaker_management):
            # Test endpoint
            test_endpoint(sagemaker_client)
        else:
            logger.error("❌ Endpoint is not ready for testing")
            
    except Exception as e:
        logger.error(f"❌ Error in main: {e}")

if __name__ == "__main__":
    main()






