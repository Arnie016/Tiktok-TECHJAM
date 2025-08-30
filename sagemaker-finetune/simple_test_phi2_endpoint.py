#!/usr/bin/env python3
"""
Quick test script for endpoint name `phi-2`
"""

import boto3
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

ENDPOINT_NAME = "phi2-compliance-analyzer-20250830-0011"
REGION = "us-west-2"

def main():
    session = boto3.Session(profile_name='bedrock-561', region_name=REGION)
    rt = session.client('sagemaker-runtime')

    payload = {
        "inputs": "Analyze the following software feature to determine its geo-compliance requirements. Provide the compliance flag, the relevant law, and the reason.\n\nFeature Name: EU DSA Risk & Transparency Engine\nFeature Description: Automates systemic risk assessments and DSA transparency reporting for very large online platforms (VLOP), including recommender transparency.\n\nLaw Context (structured JSON):\n[]",
        "parameters": {"max_new_tokens": 256, "temperature": 0.7, "do_sample": True}
    }

    try:
        resp = rt.invoke_endpoint(
            EndpointName=ENDPOINT_NAME,
            ContentType='application/json',
            Body=json.dumps(payload)
        )
        result = json.loads(resp['Body'].read().decode())
        logger.info("✅ Success")
        logger.info(json.dumps(result, indent=2))
    except Exception as e:
        logger.error(f"❌ Invoke failed: {e}")

if __name__ == "__main__":
    main()





