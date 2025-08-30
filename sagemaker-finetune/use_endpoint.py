#!/usr/bin/env python3
"""
Simple script to use the deployed endpoint
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
    session = boto3.Session(profile_name='bedrock-561', region_name=REGION)
    sagemaker_client = session.client('sagemaker-runtime')
    return sagemaker_client

def query_endpoint(sagemaker_client, prompt, max_tokens=256, temperature=0.7):
    """Query the endpoint with a prompt"""
    
    # Use the working format (Format 1)
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": max_tokens,
            "temperature": temperature,
            "do_sample": True
        }
    }
    
    try:
        response = sagemaker_client.invoke_endpoint(
            EndpointName=ENDPOINT_NAME,
            ContentType='application/json',
            Body=json.dumps(payload)
        )
        
        result = json.loads(response['Body'].read().decode())
        return result
        
    except Exception as e:
        logger.error(f"❌ Error querying endpoint: {e}")
        return None

def main():
    """Main function with example queries"""
    logger.info("🚀 Setting up endpoint connection...")
    
    try:
        sagemaker_client = setup_aws_session()
        
        # Example queries
        test_queries = [
            "What are the geo-compliance requirements for age verification features in Florida?",
            "Analyze the following software feature to determine its geo-compliance requirements. Provide the compliance flag, the relevant law, and the reason.\n\nFeature Name: FL Anonymous Age Verification\nFeature Description: Provides anonymous/third-party age verification for adult/'harmful to minors' content and deletes verification data, limited to Florida users.",
            "What are the key compliance requirements for data deletion in Florida?",
            "Explain the requirements for third-party age verification in Florida law."
        ]
        
        for i, query in enumerate(test_queries, 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"Query {i}:")
            logger.info(f"{'='*60}")
            logger.info(f"📝 Input: {query}")
            
            result = query_endpoint(sagemaker_client, query)
            
            if result:
                logger.info("✅ Response received!")
                logger.info(f"📊 Generated text: {result[0]['generated_text']}")
            else:
                logger.error("❌ No response received")
        
        logger.info(f"\n{'='*60}")
        logger.info("🎉 Endpoint testing completed!")
        logger.info(f"🔗 Endpoint URL: https://runtime.sagemaker.us-west-2.amazonaws.com/endpoints/{ENDPOINT_NAME}/invocations")
        logger.info(f"📋 Working format: Hugging Face standard format with 'inputs' field")
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
