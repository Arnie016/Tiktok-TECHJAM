#!/usr/bin/env python3
"""
Delete and redeploy the endpoint with correct configuration
"""

import boto3
import json
import logging
import time
from sagemaker.huggingface import HuggingFaceModel
from sagemaker.serializers import JSONSerializer
from sagemaker.deserializers import JSONDeserializer

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Configuration
ENDPOINT_NAME = "geo-compliance-config-PHI2"
REGION = "us-west-2"
SAGEMAKER_ROLE = "arn:aws:iam::561947681110:role/service-role/AmazonSageMaker-ExecutionRole-20250829T182640"
MODEL_S3_PATH = "s3://sagemaker-us-west-2-561947681110/huggingface-pytorch-inference-2025-08-29-13-20-55-700/model.tar.gz"
INSTANCE_TYPE = "ml.g5.xlarge"

def setup_aws_session():
    """Setup AWS session with profile"""
    logger.info(f"🔧 Setting up AWS session with profile: bedrock-561")
    session = boto3.Session(profile_name='bedrock-561', region_name=REGION)
    sagemaker_client = session.client('sagemaker')
    
    # Create proper SageMaker session
    import sagemaker
    sagemaker_session = sagemaker.Session(boto_session=session)
    
    return session, sagemaker_session

def delete_endpoint(sagemaker_client):
    """Delete the existing endpoint"""
    logger.info(f"🗑️ Deleting endpoint: {ENDPOINT_NAME}")
    
    try:
        # Delete endpoint
        sagemaker_client.delete_endpoint(EndpointName=ENDPOINT_NAME)
        logger.info("✅ Endpoint deletion initiated")
        
        # Wait for deletion to complete
        while True:
            try:
                response = sagemaker_client.describe_endpoint(EndpointName=ENDPOINT_NAME)
                status = response['EndpointStatus']
                logger.info(f"📊 Endpoint Status: {status}")
                
                if status == 'Deleting':
                    time.sleep(30)
                else:
                    break
                    
            except sagemaker_client.exceptions.ClientError as e:
                if e.response['Error']['Code'] == 'ValidationException':
                    logger.info("✅ Endpoint deleted successfully")
                    break
                else:
                    raise e
                    
    except Exception as e:
        logger.error(f"❌ Error deleting endpoint: {e}")

def create_inference_script():
    """Create the inference script"""
    inference_code = '''import json
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
import logging

logger = logging.getLogger(__name__)

def model_fn(model_dir):
    """Load the model"""
    logger.info("Loading model...")
    
    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained("microsoft/phi-2")
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    # Load base model
    base_model = AutoModelForCausalLM.from_pretrained(
        "microsoft/phi-2",
        torch_dtype=torch.bfloat16,
        attn_implementation="eager",
        trust_remote_code=False,
        device_map="auto"
    )
    
    # Load LoRA adapters if they exist
    try:
        model = PeftModel.from_pretrained(base_model, model_dir)
        logger.info("LoRA adapters loaded successfully")
    except Exception as e:
        logger.warning(f"Could not load LoRA adapters: {e}")
        model = base_model
    
    return model, tokenizer

def input_fn(request_body, request_content_type):
    """Parse input data"""
    if request_content_type == "application/json":
        return json.loads(request_body)
    else:
        raise ValueError(f"Unsupported content type: {request_content_type}")

def predict_fn(input_data, model_and_tokenizer):
    """Generate prediction"""
    model, tokenizer = model_and_tokenizer
    
    # Extract inputs
    instruction = input_data.get("instruction", "")
    feature_input = input_data.get("input", "")
    
    # Build prompt
    prompt = f"{instruction}\\n\\n{feature_input}\\n\\n"
    
    # Tokenize
    inputs = tokenizer(
        prompt,
        return_tensors="pt",
        truncation=True,
        max_length=512,
        padding=True
    ).to(model.device)
    
    # Generate
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=256,
            temperature=0.7,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=tokenizer.eos_token_id
        )
    
    # Decode
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    generated_text = response[len(prompt):].strip()
    
    return {"generated_text": generated_text, "full_response": response}

def output_fn(prediction, content_type):
    """Format output"""
    if content_type == "application/json":
        return json.dumps(prediction)
    else:
        raise ValueError(f"Unsupported content type: {content_type}")
'''
    
    with open("inference.py", "w") as f:
        f.write(inference_code)
    
    logger.info("✅ Created inference script")

def create_requirements_file():
    """Create requirements file"""
    requirements = """transformers==4.49.0
accelerate>=0.31,<0.34
peft==0.10.0
torch>=2.6.0
numpy>=1.21.0
"""
    
    with open("requirements.txt", "w") as f:
        f.write(requirements)
    
    logger.info("✅ Created requirements file")

def deploy_model(sagemaker_session):
    """Deploy the model to SageMaker endpoint"""
    logger.info(f"🚀 Deploying model to endpoint: {ENDPOINT_NAME}")
    
    # Create HuggingFace model
    huggingface_model = HuggingFaceModel(
        model_data=MODEL_S3_PATH,
        role=SAGEMAKER_ROLE,
        transformers_version="4.49.0",
        pytorch_version="2.6.0",
        py_version="py312",
        entry_point="inference.py",
        source_dir=".",
        sagemaker_session=sagemaker_session,
        env={
            "HF_HUB_ENABLE_HF_TRANSFER": "0",
            "TRANSFORMERS_CACHE": "/tmp/transformers_cache",
            "HF_TASK": "text-generation"
        }
    )
    
    # Deploy to endpoint
    logger.info(f"📦 Deploying to instance: {INSTANCE_TYPE}")
    predictor = huggingface_model.deploy(
        initial_instance_count=1,
        instance_type=INSTANCE_TYPE,
        endpoint_name=ENDPOINT_NAME,
        serializer=JSONSerializer(),
        deserializer=JSONDeserializer()
    )
    
    logger.info(f"✅ Model deployed successfully!")
    logger.info(f"🔗 Endpoint: {ENDPOINT_NAME}")
    
    return predictor

def monitor_deployment(sagemaker_session):
    """Monitor endpoint deployment"""
    logger.info("🔍 Monitoring endpoint deployment...")
    
    while True:
        try:
            response = sagemaker_session.describe_endpoint(EndpointName=ENDPOINT_NAME)
            status = response['EndpointStatus']
            
            logger.info(f"📊 Endpoint Status: {status}")
            
            if status == 'InService':
                logger.info("✅ Endpoint deployment completed!")
                return True
            elif status == 'Failed':
                logger.error("❌ Endpoint deployment failed!")
                return False
            elif status in ['Creating', 'Updating']:
                logger.info("⏳ Endpoint is still being created...")
                time.sleep(30)
            else:
                logger.warning(f"⚠️ Unknown status: {status}")
                time.sleep(30)
                
        except Exception as e:
            logger.error(f"❌ Error checking endpoint status: {e}")
            time.sleep(30)

def main():
    """Main function"""
    logger.info("🚀 Starting endpoint redeployment...")
    
    try:
        # Setup AWS session
        session, sagemaker_session = setup_aws_session()
        
        # Delete existing endpoint
        delete_endpoint(sagemaker_session)
        
        # Create deployment files
        create_inference_script()
        create_requirements_file()
        
        # Deploy model
        predictor = deploy_model(sagemaker_session)
        
        # Monitor deployment
        if monitor_deployment(sagemaker_session):
            logger.info("🎉 Endpoint redeployment completed successfully!")
            logger.info(f"🔗 Monitor: https://{REGION}.console.aws.amazon.com/sagemaker/home?region={REGION}#/endpoints/{ENDPOINT_NAME}")
        else:
            logger.error("❌ Endpoint redeployment failed")
            
    except Exception as e:
        logger.error(f"❌ Redeployment failed: {e}")
        raise

if __name__ == "__main__":
    main()
