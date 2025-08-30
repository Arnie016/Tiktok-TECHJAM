#!/usr/bin/env python3
"""
Robust Inference Script for LLaMA-3.1-8B
Fixes all issues encountered with Phi-2 deployment
"""

import json
import logging
import os
import sys
import torch
from typing import Dict, List, Any
import tempfile
import shutil

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _setup_environment():
    """Setup environment variables to avoid read-only filesystem issues."""
    # Create writable cache directories
    cache_dirs = [
        "/tmp/transformers_cache",
        "/tmp/hf_home", 
        "/tmp/huggingface",
        "/tmp/torch_cache"
    ]
    
    for cache_dir in cache_dirs:
        os.makedirs(cache_dir, exist_ok=True)
    
    # Set environment variables
    env_vars = {
        "TRANSFORMERS_CACHE": "/tmp/transformers_cache",
        "HF_HOME": "/tmp/hf_home",
        "HUGGINGFACE_HUB_CACHE": "/tmp/huggingface",
        "XDG_CACHE_HOME": "/tmp",
        "TORCH_HOME": "/tmp/torch_cache",
        "HF_HUB_ENABLE_HF_TRANSFER": "0",  # Disable for stability
        "TOKENIZERS_PARALLELISM": "false"  # Avoid warnings
    }
    
    for key, value in env_vars.items():
        os.environ[key] = value
        logger.info(f"Set {key}={value}")

def _disable_flash_attention():
    """Disable flash attention to avoid compatibility issues."""
    os.environ["FLASH_ATTENTION"] = "0"
    os.environ["USE_FLASH_ATTENTION"] = "false"

def model_fn(model_dir):
    """
    Load model function - handles both base model and LoRA adapters.
    Robust implementation that avoids all Phi-2 issues.
    """
    logger.info("Starting model_fn...")
    
    # Setup environment first
    _setup_environment()
    _disable_flash_attention()
    
    # Get configuration
    base_model_id = os.environ.get("BASE_MODEL_ID", "meta-llama/Meta-Llama-3.1-8B-Instruct")
    hf_token = os.environ.get("HF_TOKEN")
    model_artifact_s3 = os.environ.get("MODEL_ARTIFACT_S3")
    
    logger.info(f"Base model: {base_model_id}")
    logger.info(f"HF token present: {bool(hf_token)}")
    logger.info(f"Model artifact S3: {model_artifact_s3}")
    
    try:
        from transformers import (
            AutoTokenizer, 
            AutoModelForCausalLM, 
            BitsAndBytesConfig
        )
        from peft import PeftModel
    except ImportError as e:
        logger.error(f"Import error: {e}")
        raise
    
    # Quantization config for 8B model on 24GB GPU
    quantization_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True
    )
    
    # Load tokenizer
    logger.info("Loading tokenizer...")
    try:
        tokenizer = AutoTokenizer.from_pretrained(
            base_model_id,
            token=hf_token,
            trust_remote_code=False,
            cache_dir="/tmp/transformers_cache"
        )
        
        # Ensure pad token exists
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        
        logger.info("Tokenizer loaded successfully")
    except Exception as e:
        logger.error(f"Tokenizer loading failed: {e}")
        raise
    
    # Load base model
    logger.info("Loading base model...")
    try:
        base_model = AutoModelForCausalLM.from_pretrained(
            base_model_id,
            token=hf_token,
            quantization_config=quantization_config,
            torch_dtype=torch.bfloat16,
            device_map="auto",
            trust_remote_code=False,
            cache_dir="/tmp/transformers_cache",
            low_cpu_mem_usage=True
        )
        
        logger.info("Base model loaded successfully")
    except Exception as e:
        logger.error(f"Base model loading failed: {e}")
        raise
    
    # Handle LoRA adapters if present
    model = base_model
    if model_artifact_s3 or os.path.exists(os.path.join(model_dir, "adapter_config.json")):
        logger.info("LoRA adapters detected, loading...")
        
        try:
            # Create writable adapter directory
            adapter_dir = "/tmp/llama_adapters"
            os.makedirs(adapter_dir, exist_ok=True)
            
            # Download S3 artifact if provided
            if model_artifact_s3:
                logger.info(f"Downloading adapters from {model_artifact_s3}")
                _download_and_extract_s3_artifact(model_artifact_s3, adapter_dir)
            else:
                # Copy from model_dir to writable location
                logger.info("Copying adapters from model_dir")
                _copy_adapters(model_dir, adapter_dir)
            
            # Sanitize adapter config
            _sanitize_adapter_config(adapter_dir)
            
            # Load LoRA model
            model = PeftModel.from_pretrained(
                base_model,
                adapter_dir,
                torch_dtype=torch.bfloat16,
                device_map="auto"
            )
            
            logger.info("LoRA adapters loaded successfully")
            
        except Exception as e:
            logger.warning(f"LoRA loading failed, using base model: {e}")
            model = base_model
    
    # Set model to evaluation mode
    model.eval()
    
    logger.info("Model loading complete")
    return {
        "model": model,
        "tokenizer": tokenizer
    }

def _download_and_extract_s3_artifact(s3_path: str, target_dir: str):
    """Download and extract S3 artifact to target directory."""
    import boto3
    import tarfile
    from urllib.parse import urlparse
    
    # Parse S3 path
    parsed = urlparse(s3_path)
    bucket = parsed.netloc
    key = parsed.path.lstrip('/')
    
    # Download to temp file
    s3_client = boto3.client('s3')
    temp_file = "/tmp/model_artifact.tar.gz"
    
    logger.info(f"Downloading {bucket}/{key} to {temp_file}")
    s3_client.download_file(bucket, key, temp_file)
    
    # Extract
    logger.info(f"Extracting to {target_dir}")
    with tarfile.open(temp_file, 'r:gz') as tar:
        tar.extractall(target_dir)
    
    # Cleanup
    os.remove(temp_file)

def _copy_adapters(source_dir: str, target_dir: str):
    """Copy adapter files from source to target directory."""
    adapter_files = [
        "adapter_config.json",
        "adapter_model.bin",
        "adapter_model.safetensors"
    ]
    
    for filename in adapter_files:
        source_path = os.path.join(source_dir, filename)
        if os.path.exists(source_path):
            target_path = os.path.join(target_dir, filename)
            shutil.copy2(source_path, target_path)
            logger.info(f"Copied {filename}")

def _sanitize_adapter_config(adapter_dir: str):
    """Remove unsupported keys from adapter_config.json."""
    config_path = os.path.join(adapter_dir, "adapter_config.json")
    
    if not os.path.exists(config_path):
        return
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Remove potentially problematic keys
        keys_to_remove = ["auto_mapping", "custom_models"]
        for key in keys_to_remove:
            if key in config:
                del config[key]
                logger.info(f"Removed {key} from adapter config")
        
        # Write back
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
            
    except Exception as e:
        logger.warning(f"Could not sanitize adapter config: {e}")

def input_fn(request_body, content_type):
    """
    Parse input - handles multiple formats robustly.
    """
    logger.info(f"Processing input with content_type: {content_type}")
    
    if content_type != "application/json":
        raise ValueError(f"Unsupported content type: {content_type}")
    
    try:
        data = json.loads(request_body)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")
    
    # Handle different input formats
    if isinstance(data, dict):
        if "inputs" in data:
            # HuggingFace format
            return str(data["inputs"])
        elif "instruction" in data:
            # Instruction format
            instruction = data.get("instruction", "")
            input_text = data.get("input", "")
            return f"{instruction}\n\n{input_text}".strip()
        elif "messages" in data:
            # Chat format
            messages = data["messages"]
            if isinstance(messages, list) and messages:
                return messages[-1].get("content", "")
        else:
            # Direct text
            return str(data.get("text", data.get("prompt", "")))
    elif isinstance(data, str):
        return data
    else:
        raise ValueError(f"Unsupported input format: {type(data)}")

def predict_fn(input_data, model_tokenizer):
    """
    Generate prediction with robust error handling.
    """
    logger.info("Starting prediction...")
    
    model = model_tokenizer["model"]
    tokenizer = model_tokenizer["tokenizer"]
    
    if not input_data or not input_data.strip():
        return {"generated_text": ""}
    
    try:
        # Tokenize input
        inputs = tokenizer(
            input_data,
            return_tensors="pt",
            truncation=True,
            max_length=2048,
            padding=True
        )
        
        # Move to model device
        device = next(model.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        # Generate
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=512,
                temperature=0.7,
                do_sample=True,
                top_p=0.9,
                top_k=50,
                repetition_penalty=1.1,
                pad_token_id=tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id,
                use_cache=True
            )
        
        # Decode output
        input_length = inputs["input_ids"].shape[1]
        generated_tokens = outputs[0][input_length:]
        generated_text = tokenizer.decode(generated_tokens, skip_special_tokens=True)
        
        logger.info("Prediction completed successfully")
        return {"generated_text": generated_text.strip()}
        
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        return {"error": str(e), "generated_text": ""}

def output_fn(prediction, accept):
    """
    Format output with proper content type.
    """
    if accept == "application/json":
        return json.dumps(prediction), accept
    else:
        # Default to JSON
        return json.dumps(prediction), "application/json"
