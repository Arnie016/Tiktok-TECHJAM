
import json
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
import logging

logger = logging.getLogger(__name__)

def model_fn(model_dir):
    """Load the model and tokenizer"""
    logger.info("🔄 Loading Phi-2 model and tokenizer...")
    
    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    # Load base model
    model = AutoModelForCausalLM.from_pretrained(
        model_dir,
        torch_dtype=torch.bfloat16,
        attn_implementation="eager",
        trust_remote_code=False,
        device_map="auto"
    )
    
    # Load LoRA adapters
    model = PeftModel.from_pretrained(model, model_dir)
    
    logger.info("✅ Model loaded successfully")
    return {"model": model, "tokenizer": tokenizer}

def input_fn(request_body, request_content_type):
    """Parse input data"""
    if request_content_type == "application/json":
        input_data = json.loads(request_body)
        return input_data
    else:
        raise ValueError(f"Unsupported content type: {request_content_type}")

def predict_fn(input_data, model_dict):
    """Generate prediction"""
    model = model_dict["model"]
    tokenizer = model_dict["tokenizer"]
    
    # Extract input
    instruction = input_data.get("instruction", "")
    feature_input = input_data.get("input", "")
    
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

def output_fn(prediction, content_type):
    """Format output"""
    if content_type == "application/json":
        return json.dumps(prediction)
    else:
        raise ValueError(f"Unsupported content type: {content_type}")
