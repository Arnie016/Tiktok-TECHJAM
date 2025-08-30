#!/usr/bin/env python3
"""
Direct SageMaker model update using existing S3 artifacts.
Bypasses S3 upload by using pre-uploaded inference code.
"""
import boto3
import os
from datetime import datetime

def main():
    # Setup
    session = boto3.Session(profile_name='bedrock-561', region_name='us-west-2')
    sm = session.client('sagemaker')
    
    endpoint_name = "phi2-compliance-analyzer-20250830-0011"
    timestamp = datetime.now().strftime("%Y%m%d-%H%M")
    model_name = f"phi2-fixed-model-{timestamp}"
    config_name = f"phi2-fixed-config-{timestamp}"
    
    print(f"🔄 Creating new model: {model_name}")
    
    # Create model with existing S3 artifacts
    model_response = sm.create_model(
        ModelName=model_name,
        ExecutionRoleArn="arn:aws:iam::561947681110:role/SageMakerExecutionRole",
        PrimaryContainer={
            'Image': '763104351884.dkr.ecr.us-west-2.amazonaws.com/huggingface-pytorch-inference:2.1.0-transformers4.37.0-gpu-py310-cu118-ubuntu20.04',
            'ModelDataUrl': 's3://sagemaker-us-west-2-561947681110/phi2-inference-code/fixed_inference.tar.gz',
            'Environment': {
                'BASE_MODEL_ID': 'microsoft/phi-2',
                'MODEL_ARTIFACT_S3': 's3://sagemaker-us-west-2-561947681110/phi2-fixed-2058/output/model.tar.gz',
                'HF_TASK': 'text-generation',
                'TRANSFORMERS_CACHE': '/tmp/transformers_cache',
                'HF_HOME': '/tmp/hf_home',
                'HUGGINGFACE_HUB_CACHE': '/tmp/huggingface',
                'XDG_CACHE_HOME': '/tmp',
                'HF_HUB_ENABLE_HF_TRANSFER': '0'
            }
        }
    )
    print(f"✅ Model created: {model_response['ModelArn']}")
    
    print(f"🔄 Creating endpoint configuration: {config_name}")
    
    # Create endpoint configuration
    config_response = sm.create_endpoint_config(
        EndpointConfigName=config_name,
        ProductionVariants=[
            {
                'VariantName': 'primary',
                'ModelName': model_name,
                'InitialInstanceCount': 1,
                'InstanceType': 'ml.g5.2xlarge',
                'InitialVariantWeight': 1.0
            }
        ]
    )
    print(f"✅ Endpoint config created: {config_response['EndpointConfigArn']}")
    
    print(f"🔄 Updating endpoint: {endpoint_name}")
    
    # Update endpoint
    update_response = sm.update_endpoint(
        EndpointName=endpoint_name,
        EndpointConfigName=config_name
    )
    print(f"✅ Endpoint update initiated: {update_response['EndpointArn']}")
    
    print("🕐 Waiting for endpoint to become InService...")
    print("This will take 5-10 minutes. Check status with:")
    print(f"   aws sagemaker describe-endpoint --endpoint-name {endpoint_name} --profile bedrock-561")
    
    # Monitor status
    waiter = sm.get_waiter('endpoint_in_service')
    try:
        waiter.wait(
            EndpointName=endpoint_name,
            WaiterConfig={'Delay': 30, 'MaxAttempts': 20}
        )
        print("✅ Endpoint is now InService with fixed inference!")
    except Exception as e:
        print(f"⏰ Timeout waiting, but update is in progress. Status: {e}")

if __name__ == "__main__":
    main()
