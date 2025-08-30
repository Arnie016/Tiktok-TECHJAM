#!/usr/bin/env python3
"""
Qwen-1.5-7B LoRA Training Script
==================================
Optimized fine-tuning script for geo-compliance analysis.
"""

import os
import json
import logging
import torch
from datetime import datetime
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling,
)
from peft import LoraConfig, get_peft_model, TaskType
from datasets import Dataset
import numpy as np

# --- begin phi2-safety patch ---
try:
    torch.backends.cuda.enable_flash_sdp(False)
    torch.backends.cuda.enable_mem_efficient_sdp(False)
    torch.backends.cuda.enable_math_sdp(True)
except Exception:
    pass
# --- end phi2-safety patch ---

# ------------------------------
# Config from ENV
# ------------------------------
MODEL_ID = os.getenv("MODEL_ID", "microsoft/phi-2")  # Phi-2 - with surgical fixes applied
EPOCHS = int(os.getenv("EPOCHS", 3))
LR = float(os.getenv("LR", 1e-4))  # Good learning rate for 2.7B model
MAX_LEN = int(os.getenv("MAX_LEN", 512))  # Good length for Phi-2
HF_TOKEN = os.getenv("HF_TOKEN") or os.getenv("SM_HP_HF_TOKEN", "")
if not HF_TOKEN:
    raise ValueError("HF_TOKEN not found in environment variables. Please set it in the launch script.")

DATA_PATH = "/opt/ml/input/data/train/train_refined_v2.jsonl"
OUTPUT_DIR = "/opt/ml/model"

# ------------------------------
# Logging
# ------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


# ------------------------------
# Model + Tokenizer
# ------------------------------
def load_model_and_tokenizer():
    """Load model and tokenizer with Phi-2 surgical fixes"""
    logger.info(f"🔄 Loading model: {MODEL_ID}")
    
    # Force standard downloads to avoid hf_transfer issues
    os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"
    logger.info("📥 Using standard downloads (HF transfer disabled)")
    
    # Phi-2 specific loading with surgical fixes
    if "phi-2" in MODEL_ID or MODEL_ID == "microsoft/phi-2":
        logger.info("🔧 Applying Phi-2 surgical fixes...")
        
        # Load tokenizer with Phi-2 specific settings
        tokenizer = AutoTokenizer.from_pretrained(
            MODEL_ID,
            token=HF_TOKEN,
            use_fast=True,  # Use fast tokenizer for Phi-2
            padding_side="right",  # Important for Phi-2
        )
        
        # Add padding token if not present
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        
        # Load model with Phi-2 specific configuration
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_ID,
            token=HF_TOKEN,
            torch_dtype=torch.bfloat16,  # Use bfloat16 for Phi-2
            attn_implementation="eager",  # Force eager attention (CRITICAL)
            trust_remote_code=False,  # Don't trust remote code for Phi-2
        )
        
        # Disable cache and enable gradient checkpointing
        model.config.use_cache = False
        model.gradient_checkpointing_enable()
        
        logger.info("✅ Phi-2 model loaded with surgical fixes")
        
    else:
        # Fallback to original loading for other models
        logger.info("📥 Using standard model loading...")
        
        # Load tokenizer
        tokenizer = AutoTokenizer.from_pretrained(
            MODEL_ID,
            token=HF_TOKEN,
            trust_remote_code=True,
            use_fast=False,  # Use slow tokenizer for compatibility
        )
        
        # Add padding token if not present
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        
        # Load model with optimal configuration for stability
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_ID,
            token=HF_TOKEN,
            torch_dtype=torch.float16,
            device_map="auto",
            trust_remote_code=True,
            low_cpu_mem_usage=True,      # Reduce memory usage
            use_cache=False,             # Disable cache to prevent issues
            attn_implementation="eager", # Use eager attention for stability
        )
    
    logger.info("✅ Model and tokenizer loaded")
    return model, tokenizer


def setup_lora(model):
    logger.info("🔧 Applying LoRA adapters...")
    
    # Phi-2 specific LoRA configuration
    if "phi-2" in MODEL_ID or MODEL_ID == "microsoft/phi-2":
        logger.info("🔧 Using Phi-2 specific LoRA configuration...")
        lora_config = LoraConfig(
            r=8,                    # LoRA rank (smaller for Phi-2)
            lora_alpha=16,          # LoRA alpha
            lora_dropout=0.05,      # Dropout for regularization
            bias="none",            # Don't train bias terms
            task_type=TaskType.CAUSAL_LM,
            target_modules=[        # Target modules for Phi-2
                "q_proj", "k_proj", "v_proj", "o_proj", "fc1", "fc2",
            ],
        )
    else:
        # Fallback to original configuration for other models
        lora_config = LoraConfig(
            r=16,                   # LoRA rank
            lora_alpha=32,          # LoRA alpha
            lora_dropout=0.05,      # Dropout for regularization
            bias="none",            # Don't train bias terms
            task_type=TaskType.CAUSAL_LM,
            target_modules=[        # Target modules for other models
                "q_proj", "k_proj", "v_proj", "o_proj",
                "gate_proj", "up_proj", "down_proj",
            ],
        )
    
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    return model


# ------------------------------
# Data
# ------------------------------
def load_training_data():
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(f"Training data not found at {DATA_PATH}")

    with open(DATA_PATH, "r") as f:
        data = [json.loads(line) for line in f if line.strip()]

    logger.info(f"📊 Loaded {len(data)} examples")
    return data


def build_prompt(example):
    """Simple instruction → input → output format"""
    if isinstance(example, dict):
        instr = example.get("instruction", "")
        inp = example.get("input", "")
        out = example.get("output", "")
    else:
        # Handle case where example might be a string
        return str(example)
    return f"{instr}\n\n{inp}\n\n{out}"


def tokenize_function(batch, tokenizer):
    prompts = [build_prompt(ex) for ex in batch]
    tokenized = tokenizer(
        prompts,
        truncation=True,
        padding="max_length",
        max_length=MAX_LEN,
        return_tensors=None,  # Return lists, not tensors
    )
    tokenized["labels"] = tokenized["input_ids"].copy()
    return tokenized


# ------------------------------
# Metrics
# ------------------------------
def compute_metrics(eval_pred, tokenizer=None):
    preds, labels = eval_pred
    preds = np.argmax(preds, axis=-1)

    if tokenizer is None:
        # Fallback if tokenizer not provided
        return {"json_accuracy": 0.0, "valid_json_count": 0, "total_count": len(preds)}

    decoded_preds = tokenizer.batch_decode(preds, skip_special_tokens=True)

    valid_json = 0
    for pred in decoded_preds:
        try:
            if "{" in pred and "}" in pred:
                json.loads(pred[pred.find("{") : pred.rfind("}") + 1])
                valid_json += 1
        except Exception:
            continue

    json_acc = valid_json / len(decoded_preds) if decoded_preds else 0
    return {
        "json_accuracy": json_acc,
        "valid_json_count": valid_json,
        "total_count": len(decoded_preds),
    }


# ------------------------------
# Main
# ------------------------------
def validate_hf_token():
    """Validate HF token is available"""
    if not HF_TOKEN:
        raise ValueError("HF_TOKEN not found. Please set HF_TOKEN environment variable.")
    logger.info(f"🔑 Using HF token: {HF_TOKEN[:10]}...")

def main():
    logger.info("🚀 Starting Qwen fine-tuning job")
    validate_hf_token()

    model, tokenizer = load_model_and_tokenizer()
    
    # Apply LoRA
    model = setup_lora(model)
    
    # Test forward pass for Phi-2 to verify surgical fixes
    if "phi-2" in MODEL_ID or MODEL_ID == "microsoft/phi-2":
        logger.info("🧪 Testing forward pass to verify Phi-2 surgical fixes...")
        try:
            sample = tokenizer("Test sample.", return_tensors="pt").to(model.device)
            with torch.no_grad():
                _ = model(**sample)
            logger.info("✅ Forward pass successful - Phi-2 surgical fixes working!")
        except Exception as e:
            logger.error(f"❌ Forward pass failed: {e}")
            raise e

    data = load_training_data()
    dataset = Dataset.from_list(data)

    tokenized_dataset = dataset.map(
        tokenize_function,
        fn_kwargs={"tokenizer": tokenizer},
        remove_columns=dataset.column_names,
        batched=True,
        batch_size=1000,
    )

    split = tokenized_dataset.train_test_split(test_size=0.1, seed=42)
    train_ds, eval_ds = split["train"], split["test"]

    logger.info(f"Training size: {len(train_ds)}, Validation size: {len(eval_ds)}")

    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        num_train_epochs=EPOCHS,
        per_device_train_batch_size=4,  # Good batch size for 0.5B model
        per_device_eval_batch_size=4,   # Good batch size for 0.5B model
        gradient_accumulation_steps=2,  # Good for 0.5B model
        learning_rate=LR,
        warmup_ratio=0.1,
        logging_steps=10,
        evaluation_strategy="steps",
        eval_steps=50,
        save_steps=100,
        save_total_limit=2,
        load_best_model_at_end=True,
        metric_for_best_model="json_accuracy",
        greater_is_better=True,
        fp16=False,  # Disable fp16 for Phi-2 to avoid tensor issues
        gradient_checkpointing=False,  # Disabled to avoid tensor issues
        dataloader_pin_memory=False,   # Disabled to avoid memory issues
        remove_unused_columns=False,   # Important for custom datasets
        report_to=None,                # Disable wandb logging
    )

    # Use Phi-2 specific data collator to ensure 2D masks
    if "phi-2" in MODEL_ID or MODEL_ID == "microsoft/phi-2":
        logger.info("🔧 Using Phi-2 specific data collator...")
        collator = DataCollatorForLanguageModeling(
            tokenizer=tokenizer, 
            mlm=False, 
            pad_to_multiple_of=8
        )
    else:
        collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        data_collator=collator,
        compute_metrics=lambda eval_pred: compute_metrics(eval_pred, tokenizer),
    )

    logger.info("🎯 Training started...")
    trainer.train()

    logger.info("💾 Saving final model + tokenizer")
    trainer.save_model(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)

    eval_results = trainer.evaluate()
    logger.info(f"📊 Final eval results: {eval_results}")


if __name__ == "__main__":
    main()
