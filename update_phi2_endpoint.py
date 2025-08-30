#!/usr/bin/env python3
"""
Quick script to update the phi2 endpoint with fixed inference code
"""
import boto3
import time
from sagemaker import Session
from sagemaker.huggingface import HuggingFaceModel

def main():
    # Configuration
    profile = 'bedrock-561'
    region = 'us-west-2'
    endpoint_name = 'phi2-compliance-analyzer-20250830-0011'
    role = 'arn:aws:iam::561947681110:role/SageMakerExecutionRole'
    
    # Use fixed inference code from S3
    model_data = 's3://sagemaker-us-west-2-561947681110/phi2-inference-code/fixed_inference.tar.gz'
    
    print(f"🔄 Updating endpoint {endpoint_name} with fixed inference...")
    
    session = boto3.Session(profile_name=profile, region_name=region)
    sm_session = Session(boto_session=session)
    
    # Create model with fixed inference code and env pointing to adapters
    model = HuggingFaceModel(
        model_data=model_data,
        role=role,
        transformers_version="4.49.0",
        pytorch_version="2.6.0", 
        py_version="py312",
        entry_point="inference.py",
        sagemaker_session=sm_session,
        env={
            'HF_HUB_ENABLE_HF_TRANSFER': '0',
            'TRANSFORMERS_CACHE': '/tmp/transformers_cache',
            'HF_HOME': '/tmp/hf_home',
            'HUGGINGFACE_HUB_CACHE': '/tmp/huggingface',
            'XDG_CACHE_HOME': '/tmp',
            'HF_TASK': 'text-generation',
            'BASE_MODEL_ID': 'microsoft/phi-2',
            'MODEL_ARTIFACT_S3': 's3://sagemaker-us-west-2-561947681110/phi2-fixed-2058/output/model.tar.gz',
            'HF_TOKEN': ''  # Will be set from env if needed
        }
    )
    
    print("🔄 Deploying updated model...")
    model.deploy(
        initial_instance_count=1,
        instance_type='ml.g5.2xlarge',
        endpoint_name=endpoint_name,
        update_endpoint=True
    )
    
    print("✅ Endpoint update initiated. Waiting for InService...")
    
    # Wait for endpoint to be ready
    sm_client = session.client('sagemaker')
    waiter = sm_client.get_waiter('endpoint_in_service')
    waiter.wait(EndpointName=endpoint_name)
    
    print(f"✅ Endpoint {endpoint_name} is now InService with fixed inference!")

if __name__ == "__main__":
    main()

