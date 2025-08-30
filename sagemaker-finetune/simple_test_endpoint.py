#!/usr/bin/env python3
"""
Simple endpoint test with proper configuration
"""

import boto3
import json
import logging

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
    return sagemaker_client

def test_endpoint(sagemaker_client):
    """Test the endpoint with a sample request"""
    logger.info("🧪 Testing endpoint with sample request...")
    
    # Sample test case
    test_payload = {
        "inputs": "Analyze the following software feature to determine its geo-compliance requirements. Provide the compliance flag, the relevant law, and the reason.\n\nFeature Name: FL Anonymous Age Verification\nFeature Description: Provides anonymous/third-party age verification for adult/'harmful to minors' content and deletes verification data, limited to Florida users.\nSource: h0001z.RRS.pdf\n\nLaw Context (structured JSON):\n[{\"title\": \"Judiciary_JU0003ju_00003.pdf\", \"citation\": null, \"article\": null, \"section\": null, \"date\": null, \"uri\": \"https://arnav-finetune-1756053255.s3.us-west-2.amazonaws.com/data/law/Judiciary_JU0003ju_00003.pdf\", \"page\": null, \"source\": null, \"snippet\": \"...harmful to minors satisfies the bill's age requirements. If an anonymous age verification method is used, the verification must be conducted by a nongovernmental, independent third party organized under the laws of a state of the U.S. Any information used to verify age must be deleted once...\"}, {\"title\": \"PDF.pdf\", \"citation\": null, \"article\": null, \"section\": null, \"date\": null, \"uri\": \"https://arnav-finetune-1756053255.s3.us-west-2.amazonaws.com/data/law/PDF.pdf\", \"page\": null, \"source\": null, \"snippet\": \"...501.1737, Florida Statutes, is created 282 to read: 283 501.1737 Age verification for online access to materials 284 harmful to minors.— 285 (1) As used in this section, the term: 286 (a) \\\"Anonymous age verification\\\" has the same meaning as 287 in s. 501.1738. 288 (b...\"}]",
        "parameters": {
            "max_new_tokens": 256,
            "temperature": 0.7,
            "do_sample": True
        }
    }
    
    try:
        # Invoke endpoint with proper headers
        response = sagemaker_client.invoke_endpoint(
            EndpointName=ENDPOINT_NAME,
            ContentType='application/json',
            Body=json.dumps(test_payload),
            CustomAttributes='HF_TASK=text-generation'
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
    logger.info("🚀 Testing endpoint...")
    
    try:
        # Setup AWS session
        sagemaker_client = setup_aws_session()
        
        # Test endpoint
        test_endpoint(sagemaker_client)
            
    except Exception as e:
        logger.error(f"❌ Error in main: {e}")

if __name__ == "__main__":
    main()






