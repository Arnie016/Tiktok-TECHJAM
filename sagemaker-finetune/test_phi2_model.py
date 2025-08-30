#!/usr/bin/env python3
"""
Test Fine-tuned Phi-2 Model Directly
"""

import os
import json
import torch
import tempfile
import boto3
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# AWS Configuration
AWS_PROFILE = "bedrock-561"
REGION = "us-west-2"

# Model Configuration
MODEL_S3_PATH = "s3://sagemaker-us-west-2-561947681110/phi2-fixed-2058/output/model.tar.gz"

def setup_aws_session():
    """Setup AWS session with profile"""
    logger.info(f"🔧 Setting up AWS session with profile: {AWS_PROFILE}")
    
    session = boto3.Session(profile_name=AWS_PROFILE, region_name=REGION)
    return session

def download_model():
    """Download the model from S3"""
    logger.info("📥 Downloading model from S3...")
    
    session = setup_aws_session()
    s3_client = session.client('s3')
    
    # Parse S3 path
    bucket = "sagemaker-us-west-2-561947681110"
    key = "phi2-fixed-2058/output/model.tar.gz"
    
    # Create temporary directory (don't use context manager)
    temp_dir = tempfile.mkdtemp()
    model_path = os.path.join(temp_dir, "model.tar.gz")
    
    # Download model
    logger.info(f"📥 Downloading from s3://{bucket}/{key}")
    s3_client.download_file(bucket, key, model_path)
    
    # Extract model
    import tarfile
    with tarfile.open(model_path, 'r:gz') as tar:
        tar.extractall(temp_dir)
    
    logger.info("✅ Model downloaded and extracted")
    return temp_dir

def load_model(model_dir):
    """Load the fine-tuned model"""
    logger.info("🔄 Loading Phi-2 model and tokenizer...")
    
    # Check what's in the model directory
    logger.info(f"📁 Model directory contents: {os.listdir(model_dir)}")
    
    # Look for the actual model files
    model_files = [f for f in os.listdir(model_dir) if os.path.isdir(os.path.join(model_dir, f))]
    logger.info(f"📁 Subdirectories: {model_files}")
    
    # Try to find the model path
    if "model" in model_files:
        actual_model_path = os.path.join(model_dir, "model")
    elif any(f.startswith("checkpoint-") for f in model_files):
        # Find the latest checkpoint
        checkpoints = [f for f in model_files if f.startswith("checkpoint-")]
        latest_checkpoint = sorted(checkpoints)[-1]
        actual_model_path = os.path.join(model_dir, latest_checkpoint)
    else:
        # Try the root directory
        actual_model_path = model_dir
    
    logger.info(f"📁 Using model path: {actual_model_path}")
    logger.info(f"📁 Model path contents: {os.listdir(actual_model_path)}")
    
    # Load tokenizer from the root directory (it should be there)
    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    # Load base Phi-2 model first with CPU to avoid memory issues
    logger.info("🔄 Loading base Phi-2 model...")
    base_model = AutoModelForCausalLM.from_pretrained(
        "microsoft/phi-2",
        torch_dtype=torch.bfloat16,
        attn_implementation="eager",
        trust_remote_code=False,
        device_map=None,  # Load on CPU first
        low_cpu_mem_usage=True
    )
    
    # Check if LoRA adapters exist
    if os.path.exists(os.path.join(actual_model_path, "adapter_config.json")):
        # Load LoRA adapters with proper error handling
        logger.info("🔄 Loading LoRA adapters...")
        try:
            model = PeftModel.from_pretrained(
                base_model, 
                actual_model_path,
                is_trainable=False,
                device_map=None  # Keep on CPU
            )
            logger.info("✅ LoRA adapters loaded")
        except Exception as e:
            logger.warning(f"⚠️ LoRA loading failed: {e}")
            logger.info("🔄 Using base model without LoRA adapters")
            model = base_model
    else:
        logger.info("ℹ️ No LoRA adapters found, using base model")
        model = base_model
    
    # Move to GPU if available
    if torch.cuda.is_available():
        logger.info("🔄 Moving model to GPU...")
        model = model.to("cuda")
    else:
        logger.info("ℹ️ Using CPU for inference")
    
    logger.info("✅ Model loaded successfully")
    return model, tokenizer

def generate_response(model, tokenizer, instruction, feature_input):
    """Generate compliance analysis"""
    # Build prompt
    prompt = f"{instruction}\n\n{feature_input}\n\n"
    
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
    
    # Extract the generated part (after the prompt)
    generated_text = response[len(prompt):].strip()
    
    return {
        "compliance_analysis": generated_text,
        "full_response": response
    }

def test_model():
    """Test the fine-tuned model"""
    logger.info("🧪 Testing fine-tuned Phi-2 model...")
    
    # Download and load model
    model_dir = download_model()
    model, tokenizer = load_model(model_dir)
    
    # Test cases
    test_cases = [
        {
            "name": "EU DSA Risk & Transparency Engine",
            "instruction": "Analyze the following software feature to determine its geo-compliance requirements. Provide the compliance flag, the relevant law, and the reason.",
            "input": "Feature Name: EU DSA Risk & Transparency Engine\nFeature Description: Automates systemic risk assessments and DSA transparency reporting for very large online platforms (VLOP), including recommender transparency.\nSource: Cal Civ Code § 1798.99.33.PDF\n\nLaw Context (structured JSON):\n[]"
        },
        {
            "name": "CA Teen Addictive-Design Controls",
            "instruction": "Analyze the following software feature to determine its geo-compliance requirements. Provide the compliance flag, the relevant law, and the reason.",
            "input": "Feature Name: CA Teen Addictive-Design Controls\nFeature Description: Implements controls to reduce addictive social-media features for minors in California, including limits on infinite scroll and autoplay.\nSource: h0001z.RRS.pdf\n\nLaw Context (structured JSON):\n[{\"title\": \"20230SB976_91.pdf\", \"citation\": null, \"article\": null, \"section\": null, \"date\": \"2018\", \"uri\": \"https://arnav-finetune-1756053255.s3.us-west-2.amazonaws.com/data/law/20230SB976_91.pdf\", \"page\": null, \"source\": null, \"snippet\": \"...related protections for minors, including under the California Consumer Privacy Act of 2018 and the California Privacy Rights Act of 2020. This bill, the Protecting Our Kids from Social Media Addiction Act, would make it unlawful for the operator of an addictive internet-based service or...\"}, {\"title\": \"Judiciary_JU0003ju_00003.pdf\", \"citation\": null, \"article\": null, \"section\": null, \"date\": null, \"uri\": \"https://arnav-finetune-1756053255.s3.us-west-2.amazonaws.com/data/law/Judiciary_JU0003ju_00003.pdf\", \"page\": null, \"source\": null, \"snippet\": \"...Have certain addictive features. With respect to all accounts belonging to minors younger than 14, and to those accounts belonging to minors who are 14 or 15 years of age but for whom parents or guardians have not provided consent, the bill requires regulated social media platforms to...\"}]"
        }
    ]
    
    # Run tests
    for i, test_case in enumerate(test_cases, 1):
        logger.info(f"\n🧪 Test {i}: {test_case['name']}")
        logger.info("=" * 50)
        
        try:
            response = generate_response(
                model, 
                tokenizer, 
                test_case['instruction'], 
                test_case['input']
            )
            
            logger.info("✅ Generation successful!")
            logger.info(f"📊 Compliance Analysis: {response['compliance_analysis']}")
            logger.info(f"📋 Full Response: {response['full_response']}")
            
        except Exception as e:
            logger.error(f"❌ Test {i} failed: {e}")
    
    logger.info("\n🎉 Model testing completed!")

def main():
    """Main function"""
    try:
        test_model()
    except Exception as e:
        logger.error(f"❌ Testing failed: {e}")
        raise

if __name__ == "__main__":
    main()
