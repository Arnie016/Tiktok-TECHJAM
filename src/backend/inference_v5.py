import json
import os
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, TextIteratorStreamer
from peft import PeftModel
import logging

logger = logging.getLogger(__name__)

def model_fn(model_dir, context=None):
    """Load the model and tokenizer with proper LoRA handling"""
    logger.info("🔄 Loading Phi-2 v5 model with LoRA adapters...")
    
    # Get base model ID from environment variable
    base_model_id = os.environ.get('BASE_MODEL_ID', 'microsoft/phi-2')
    logger.info(f"📋 Base model: {base_model_id}")
    logger.info(f"📁 Model dir: {model_dir}")
    
    # Load tokenizer from base model
    tokenizer = AutoTokenizer.from_pretrained(base_model_id, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    # Load base model with optimized settings for memory efficiency
    logger.info("🤖 Loading base model...")
    model = AutoModelForCausalLM.from_pretrained(
        base_model_id,
        torch_dtype=torch.float16,  # Better for A10G GPU
        device_map="auto",
        trust_remote_code=True,
        attn_implementation="eager",  # More stable
        low_cpu_mem_usage=True  # Optimize memory usage
    )
    
    # Load LoRA adapters from the trained model artifacts
    logger.info("🔧 Loading LoRA adapters...")
    try:
        model = PeftModel.from_pretrained(model, model_dir)
        logger.info("✅ LoRA adapters loaded successfully")
    except Exception as e:
        logger.error(f"❌ Failed to load LoRA adapters: {e}")
        # Fallback to base model if LoRA loading fails
        logger.warning("⚠️ Using base model without LoRA adapters")
    
    # Set to evaluation mode
    model.eval()
    
    logger.info("✅ Model loaded successfully")
    return {"model": model, "tokenizer": tokenizer}

def input_fn(request_body, request_content_type):
    """Parse input data"""
    if request_content_type == "application/json":
        try:
            input_data = json.loads(request_body)
            return input_data
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON decode error: {e}")
            raise ValueError(f"Invalid JSON in request body: {e}")
    else:
        raise ValueError(f"Unsupported content type: {request_content_type}")

def predict_fn(input_data, model_dict):
    """Generate prediction with streaming support"""
    model = model_dict["model"]
    tokenizer = model_dict["tokenizer"]
    
    # Extract input
    instruction = input_data.get("instruction", "")
    feature_input = input_data.get("input", "")
    
    # Enhanced prompt format matching training data
    prompt = f"""<|user|>
{instruction}

{feature_input}
<|assistant|>
"""
    
    logger.info(f"📝 Prompt length: {len(prompt)} characters")
    
    # Tokenize with proper settings
    inputs = tokenizer(
        prompt,
        return_tensors="pt",
        truncation=True,
        max_length=512,
        padding=False  # Don't pad for single input
    )
    
    # Move to model device
    inputs = {k: v.to(model.device) for k, v in inputs.items()}
    
    # Generate with optimized settings for speed and quality
    try:
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=128,  # Reduced for faster response
                temperature=0.3,     # Lower temperature for more focused output
                do_sample=True,
                top_p=0.9,
                top_k=50,
                pad_token_id=tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id,
                repetition_penalty=1.1,
                use_cache=True,
                no_repeat_ngram_size=3
            )
    
        # Decode the response
        full_response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Extract only the generated part (after the prompt)
        generated_text = full_response[len(prompt):].strip()
        
        logger.info(f"✅ Generated {len(generated_text)} characters")
        
        return {
            "generated_text": generated_text,
            "prompt": prompt,
            "full_response": full_response
        }
        
    except Exception as e:
        logger.error(f"❌ Generation error: {e}")
        return {
            "generated_text": f"Error during generation: {str(e)}",
            "prompt": prompt,
            "full_response": ""
        }

def output_fn(prediction, content_type):
    """Format output"""
    if content_type == "application/json":
        return json.dumps(prediction, indent=2)
    else:
        raise ValueError(f"Unsupported content type: {content_type}")
