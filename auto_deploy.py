#!/usr/bin/env python3
"""
Automated deployment script for geo-compliance model
Creates model, endpoint config, and endpoint automatically
"""

import boto3
import json
import time
from sagemaker.huggingface import HuggingFaceModel
from sagemaker import Session

# Configuration
ROLE_ARN = "arn:aws:iam::561947681110:role/SageMakerExecutionRole"
REGION = "us-west-2"
BUCKET = "arnav-finetune-1756054916"

def get_latest_training_job():
    """Get the latest successful training job"""
    sagemaker_client = boto3.client('sagemaker', region_name=REGION)
    
    try:
        # List training jobs, sorted by creation time
        response = sagemaker_client.list_training_jobs(
            StatusEquals='Completed',
            SortBy='CreationTime',
            SortOrder='Descending',
            MaxResults=10
        )
        
        if response['TrainingJobSummaries']:
            latest_job = response['TrainingJobSummaries'][0]
            job_name = latest_job['TrainingJobName']
            print(f"📊 Latest training job: {job_name}")
            return job_name
        else:
            print("❌ No completed training jobs found")
            return None
            
    except Exception as e:
        print(f"❌ Error getting training jobs: {e}")
        return None

def get_model_artifacts(job_name):
    """Get model artifacts S3 path from training job"""
    sagemaker_client = boto3.client('sagemaker', region_name=REGION)
    
    try:
        response = sagemaker_client.describe_training_job(TrainingJobName=job_name)
        model_artifacts = response['ModelArtifacts']['S3ModelArtifacts']
        print(f"📦 Model artifacts: {model_artifacts}")
        return model_artifacts
    except Exception as e:
        print(f"❌ Error getting model artifacts: {e}")
        return None

def create_model(model_artifacts, model_name="geo-compliance-model"):
    """Create SageMaker model"""
    print(f"🔧 Creating model: {model_name}")
    
    boto_session = boto3.Session(region_name=REGION)
    sagemaker_session = Session(boto_session=boto_session)
    
    # Use training container for inference (we know it works)
    huggingface_model = HuggingFaceModel(
        model_data=model_artifacts,
        role=ROLE_ARN,
        transformers_version="4.36",  # Match training version
        pytorch_version="2.1",
        py_version="py310",
        sagemaker_session=sagemaker_session
    )
    
    try:
        # Create the model
        huggingface_model.create_model(name=model_name)
        print(f"✅ Model created: {model_name}")
        return True
    except Exception as e:
        print(f"❌ Error creating model: {e}")
        return False

def create_endpoint_config(model_name, config_name="geo-compliance-config"):
    """Create endpoint configuration"""
    print(f"⚙️ Creating endpoint config: {config_name}")
    
    sagemaker_client = boto3.client('sagemaker', region_name=REGION)
    
    try:
        response = sagemaker_client.create_endpoint_config(
            EndpointConfigName=config_name,
            ProductionVariants=[
                {
                    'VariantName': 'default',
                    'ModelName': model_name,
                    'InstanceType': 'ml.g5.xlarge',  # GPU instance
                    'InitialInstanceCount': 1,
                    'InitialVariantWeight': 1.0
                }
            ]
        )
        print(f"✅ Endpoint config created: {config_name}")
        return True
    except Exception as e:
        print(f"❌ Error creating endpoint config: {e}")
        return False

def create_endpoint(config_name, endpoint_name="geo-compliance-endpoint"):
    """Create and deploy endpoint"""
    print(f"🚀 Creating endpoint: {endpoint_name}")
    
    sagemaker_client = boto3.client('sagemaker', region_name=REGION)
    
    try:
        response = sagemaker_client.create_endpoint(
            EndpointName=endpoint_name,
            EndpointConfigName=config_name
        )
        print(f"✅ Endpoint creation started: {endpoint_name}")
        return endpoint_name
    except Exception as e:
        print(f"❌ Error creating endpoint: {e}")
        return None

def wait_for_endpoint(endpoint_name, timeout_minutes=15):
    """Wait for endpoint to be InService"""
    print(f"⏳ Waiting for endpoint to be ready...")
    
    sagemaker_client = boto3.client('sagemaker', region_name=REGION)
    
    start_time = time.time()
    timeout_seconds = timeout_minutes * 60
    
    while time.time() - start_time < timeout_seconds:
        try:
            response = sagemaker_client.describe_endpoint(EndpointName=endpoint_name)
            status = response['EndpointStatus']
            print(f"📊 Status: {status}")
            
            if status == 'InService':
                print(f"🎉 Endpoint is ready: {endpoint_name}")
                return True
            elif status == 'Failed':
                print(f"❌ Endpoint failed: {response.get('FailureReason', 'Unknown')}")
                return False
                
            time.sleep(30)  # Check every 30 seconds
            
        except Exception as e:
            print(f"❌ Error checking status: {e}")
            time.sleep(30)
    
    print(f"⏰ Timeout waiting for endpoint")
    return False

def test_endpoint(endpoint_name):
    """Test the deployed endpoint"""
    print(f"🧪 Testing endpoint: {endpoint_name}")
    
    runtime_client = boto3.client('sagemaker-runtime', region_name=REGION)
    
    # Test payload
    test_input = {
        "instruction": "Analyze the following software feature to determine its geo-compliance requirements.",
        "input": """Feature Name: Content Moderation Dashboard
Feature Description: A dashboard for moderators to review and remove illegal content.

Law Context (structured JSON):
{
  "title": "Digital Services Act",
  "citation": "Regulation (EU) 2022/2065",
  "article": "Article 14",
  "section": "Notice and Action",
  "date": "2022",
  "snippet": "Providers shall put in place mechanisms allowing users to notify them of illegal content."
}"""
    }
    
    prompt = f"### Instruction:\n{test_input['instruction']}\n\n### Input:\n{test_input['input']}\n\n### Response:\n"
    
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 256,
            "temperature": 0.1,
            "do_sample": True
        }
    }
    
    try:
        response = runtime_client.invoke_endpoint(
            EndpointName=endpoint_name,
            ContentType='application/json',
            Body=json.dumps(payload)
        )
        
        result = json.loads(response['Body'].read().decode())
        print("✅ Test successful!")
        print(f"🤖 Response: {result['generated_text'][:200]}...")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def main():
    """Main automated deployment function"""
    print("🚀 Automated Geo-Compliance Model Deployment")
    print("=" * 50)
    
    # Step 1: Get latest training job
    job_name = get_latest_training_job()
    if not job_name:
        return
    
    # Step 2: Get model artifacts
    model_artifacts = get_model_artifacts(job_name)
    if not model_artifacts:
        return
    
    # Step 3: Create model
    model_name = f"geo-compliance-model-{job_name[-8:]}"  # Include job timestamp
    if not create_model(model_artifacts, model_name):
        return
    
    # Step 4: Create endpoint config
    config_name = f"geo-compliance-config-{job_name[-8:]}"
    if not create_endpoint_config(model_name, config_name):
        return
    
    # Step 5: Create endpoint
    endpoint_name = f"geo-compliance-endpoint-{job_name[-8:]}"
    endpoint_name = create_endpoint(config_name, endpoint_name)
    if not endpoint_name:
        return
    
    # Step 6: Wait for endpoint to be ready
    if wait_for_endpoint(endpoint_name):
        # Step 7: Test endpoint
        test_endpoint(endpoint_name)
        
        print(f"\n🎉 Deployment completed successfully!")
        print(f"📊 Model: {model_name}")
        print(f"⚙️ Config: {config_name}")
        print(f"🚀 Endpoint: {endpoint_name}")
        print(f"🌐 Region: {REGION}")
    else:
        print(f"\n❌ Deployment failed")

if __name__ == "__main__":
    main()
