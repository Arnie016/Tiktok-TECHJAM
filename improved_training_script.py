#!/usr/bin/env python3
"""
Improved Training Script for Phi-2 - Better Precision & JSON Output
"""

import os
import json
import torch
import logging
from transformers import (
    AutoTokenizer, 
    AutoModelForCausalLM, 
    TrainingArguments, 
    Trainer,
    DataCollatorForLanguageModeling
)
from peft import LoraConfig, get_peft_model, TaskType
from datasets import Dataset
import argparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_and_prepare_data(data_path):
    """Load and prepare training data with JSON format enforcement"""
    logger.info(f"📊 Loading data from {data_path}")
    
    data = []
    with open(data_path, 'r') as f:
        for line in f:
            example = json.loads(line.strip())
            
            # Enhanced prompt with JSON format enforcement
            enhanced_instruction = f"""Analyze the following software feature to determine its geo-compliance requirements. 

CRITICAL INSTRUCTIONS:
1. Respond ONLY with valid JSON
2. Use exactly these fields: compliance_flag, law, reason
3. If no relevant law is found in context, use "Not Enough Information" and "N/A"
4. Only cite laws that appear in the Law Context section

{example['instruction']}"""
            
            # Ensure output is properly formatted JSON
            try:
                # Validate existing output is JSON
                output_json = json.loads(example['output'])
                formatted_output = json.dumps(output_json, indent=2)
            except:
                # If not valid JSON, create proper format
                formatted_output = json.dumps({
                    "compliance_flag": "Needs Review",
                    "law": "Format Error",
                    "reason": "Original output was not valid JSON"
                }, indent=2)
            
            # Create conversation format
            conversation = f"""<|user|>
{enhanced_instruction}

{example['input']}
<|assistant|>
{formatted_output}"""
            
            data.append({"text": conversation})
    
    logger.info(f"✅ Loaded {len(data)} examples")
    return Dataset.from_list(data)

def setup_model_and_tokenizer(model_id="microsoft/phi-2"):
    """Setup model and tokenizer with improved configuration"""
    logger.info(f"🤖 Loading model: {model_id}")
    
    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    # Load model with better precision
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=torch.float16,  # Better precision for g5 instances
        device_map="auto",
        trust_remote_code=True,
        attn_implementation="eager"  # More stable
    )
    
    # Enhanced LoRA configuration
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=int(os.getenv("LORA_RANK", 32)),
        lora_alpha=int(os.getenv("LORA_ALPHA", 64)),
        lora_dropout=float(os.getenv("LORA_DROPOUT", 0.1)),
        target_modules=["q_proj", "k_proj", "v_proj", "dense"],
        bias="none"
    )
    
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    
    return model, tokenizer

def tokenize_data(dataset, tokenizer, max_length=512):
    """Tokenize dataset with proper formatting"""
    def tokenize_function(examples):
        return tokenizer(
            examples["text"],
            truncation=True,
            padding=False,
            max_length=max_length,
            return_tensors="pt"
        )
    
    tokenized_dataset = dataset.map(
        tokenize_function,
        batched=True,
        remove_columns=dataset.column_names
    )
    
    return tokenized_dataset

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-id", default="microsoft/phi-2")
    parser.add_argument("--data-path", default="/opt/ml/input/data/training/train_refined_v4.jsonl")
    parser.add_argument("--output-path", default="/opt/ml/model")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--learning-rate", type=float, default=5e-5)
    
    args = parser.parse_args()
    
    logger.info("🚀 Starting improved Phi-2 training")
    logger.info("=" * 50)
    
    # Load data
    dataset = load_and_prepare_data(args.data_path)
    
    # Setup model
    model, tokenizer = setup_model_and_tokenizer(args.model_id)
    
    # Tokenize data
    tokenized_dataset = tokenize_data(dataset, tokenizer)
    
    # Training arguments with improvements
    training_args = TrainingArguments(
        output_dir=args.output_path,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=2,
        learning_rate=args.learning_rate,
        warmup_steps=int(os.getenv("WARMUP_STEPS", 100)),
        logging_steps=int(os.getenv("LOGGING_STEPS", 50)),
        save_steps=int(os.getenv("SAVE_STEPS", 250)),
        eval_steps=500,
        save_total_limit=2,
        remove_unused_columns=False,
        dataloader_drop_last=True,
        fp16=True,  # Better precision
        gradient_checkpointing=True,
        report_to=None,
        load_best_model_at_end=False,
        metric_for_best_model="loss",
        greater_is_better=False
    )
    
    # Data collator
    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False
    )
    
    # Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset,
        data_collator=data_collator,
        tokenizer=tokenizer
    )
    
    # Train
    logger.info("🎯 Starting training...")
    trainer.train()
    
    # Save model
    logger.info("💾 Saving model...")
    trainer.save_model()
    tokenizer.save_pretrained(args.output_path)
    
    logger.info("✅ Training completed successfully!")

if __name__ == "__main__":
    main()
