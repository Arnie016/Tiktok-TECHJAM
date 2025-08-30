#!/usr/bin/env python3
"""
Update the existing SageMaker endpoint with correct configuration
"""

import boto3
import json
import logging
import time

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
    return sagemaker_client

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

def update_endpoint(sagemaker_client):
    """Update the endpoint with correct configuration"""
    logger.info(f"🔄 Updating endpoint: {ENDPOINT_NAME}")
    
    # Create new model with correct configuration
    model_name = f"{ENDPOINT_NAME}-model-{int(time.time())}"
    
    # Create model
    create_model_response = sagemaker_client.create_model(
        ModelName=model_name,
        PrimaryContainer={
            'Image': '763104351884.dkr.ecr.us-west-2.amazonaws.com/huggingface-pytorch-inference:2.6.0-transformers4.49.0-gpu-py312-cu121-ubuntu20.04-ec2',
            'ModelDataUrl': MODEL_S3_PATH,
            'Environment': {
                'HF_TASK': 'text-generation',
                'HF_HUB_ENABLE_HF_TRANSFER': '0',
                'TRANSFORMERS_CACHE': '/tmp/transformers_cache'
            }
        },
        ExecutionRoleArn=SAGEMAKER_ROLE
    )
    
    logger.info(f"✅ Created model: {model_name}")
    
    # Create endpoint configuration
    config_name = f"{ENDPOINT_NAME}-config-{int(time.time())}"
    
    create_config_response = sagemaker_client.create_endpoint_config(
        EndpointConfigName=config_name,
        ProductionVariants=[
            {
                'VariantName': 'AllTraffic',
                'ModelName': model_name,
                'InitialInstanceCount': 1,
                'InstanceType': INSTANCE_TYPE,
                'InitialVariantWeight': 1.0
            }
        ]
    )
    
    logger.info(f"✅ Created endpoint config: {config_name}")
    
    # Update endpoint
    update_response = sagemaker_client.update_endpoint(
        EndpointName=ENDPOINT_NAME,
        EndpointConfigName=config_name
    )
    
    logger.info(f"✅ Endpoint update initiated")
    return config_name

def monitor_update(sagemaker_client):
    """Monitor endpoint update"""
    logger.info("🔍 Monitoring endpoint update...")
    
    while True:
        try:
            response = sagemaker_client.describe_endpoint(EndpointName=ENDPOINT_NAME)
            status = response['EndpointStatus']
            
            logger.info(f"📊 Endpoint Status: {status}")
            
            if status == 'InService':
                logger.info("✅ Endpoint update completed!")
                return True
            elif status == 'Failed':
                logger.error("❌ Endpoint update failed!")
                return False
            elif status in ['Updating', 'Creating']:
                logger.info("⏳ Endpoint is still updating...")
                time.sleep(30)
            else:
                logger.warning(f"⚠️ Unknown status: {status}")
                time.sleep(30)
                
        except Exception as e:
            logger.error(f"❌ Error checking endpoint status: {e}")
            time.sleep(30)

def main():
    """Main function"""
    logger.info("🚀 Starting endpoint update...")
    
    try:
        # Setup AWS session
        sagemaker_client = setup_aws_session()
        
        # Create deployment files
        create_inference_script()
        create_requirements_file()
        
        # Update endpoint
        config_name = update_endpoint(sagemaker_client)
        
        # Monitor update
        if monitor_update(sagemaker_client):
            logger.info("🎉 Endpoint update completed successfully!")
            logger.info(f"🔗 Monitor: https://{REGION}.console.aws.amazon.com/sagemaker/home?region={REGION}#/endpoints/{ENDPOINT_NAME}")
        else:
            logger.error("❌ Endpoint update failed")
            
    except Exception as e:
        logger.error(f"❌ Update failed: {e}")
        raise

if __name__ == "__main__":
    main()
