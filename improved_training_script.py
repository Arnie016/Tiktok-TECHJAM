#!/usr/bin/env python3
"""
Improved Training Script for Phi-2 - Compatible with SageMaker
"""

import os
import json
import torch
import logging
import argparse
from transformers import (
    AutoTokenizer, 
    AutoModelForCausalLM, 
    TrainingArguments, 
    Trainer,
    DataCollatorForLanguageModeling
)
from peft import LoraConfig, get_peft_model, TaskType
from datasets import Dataset

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser()
    
    # Model arguments
    parser.add_argument("--model_id", type=str, default="microsoft/phi-2")
    parser.add_argument("--max_seq_length", type=int, default=512)
    
    # Training arguments
    parser.add_argument("--num_train_epochs", type=int, default=3)
    parser.add_argument("--learning_rate", type=float, default=5e-5)
    parser.add_argument("--per_device_train_batch_size", type=int, default=4)
    parser.add_argument("--gradient_accumulation_steps", type=int, default=2)
    
    # LoRA arguments
    parser.add_argument("--lora_r", type=int, default=32)
    parser.add_argument("--lora_alpha", type=int, default=64)
    parser.add_argument("--lora_dropout", type=float, default=0.1)
    
    # Paths
    parser.add_argument("--train_data_path", type=str, default="/opt/ml/input/data/train")
    parser.add_argument("--output_dir", type=str, default="/opt/ml/model")
    
    return parser.parse_args()

def load_and_prepare_data(data_path):
    """Load and prepare training data with JSON format enforcement"""
    logger.info(f"📊 Loading data from {data_path}")
    
    # Find the jsonl file
    jsonl_files = []
    if os.path.isdir(data_path):
        for file in os.listdir(data_path):
            if file.endswith('.jsonl'):
                jsonl_files.append(os.path.join(data_path, file))
    else:
        jsonl_files = [data_path]
    
    if not jsonl_files:
        raise FileNotFoundError(f"No .jsonl files found in {data_path}")
    
    data_file = jsonl_files[0]
    logger.info(f"📖 Reading from: {data_file}")
    
    data = []
    with open(data_file, 'r') as f:
        for line_num, line in enumerate(f, 1):
            try:
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
                
            except Exception as e:
                logger.warning(f"⚠️ Skipping line {line_num}: {e}")
                continue
    
    logger.info(f"✅ Loaded {len(data)} examples")
    return Dataset.from_list(data)

def setup_model_and_tokenizer(model_id):
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
    
    return model, tokenizer

def setup_lora(model, args):
    """Setup LoRA configuration"""
    logger.info(f"🔧 Setting up LoRA with r={args.lora_r}, alpha={args.lora_alpha}")
    
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        target_modules=["q_proj", "k_proj", "v_proj", "dense"],
        bias="none"
    )
    
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    
    return model

def tokenize_data(dataset, tokenizer, max_length=512):
    """Tokenize dataset with proper formatting"""
    def tokenize_function(examples):
        # Tokenize without return_tensors to avoid shape issues
        tokenized = tokenizer(
            examples["text"],
            truncation=True,
            padding=False,
            max_length=max_length
        )
        return tokenized
    
    tokenized_dataset = dataset.map(
        tokenize_function,
        batched=True,
        remove_columns=dataset.column_names
    )
    
    return tokenized_dataset

def main():
    """Main training function"""
    args = parse_args()
    
    logger.info("🚀 Starting improved Phi-2 training")
    logger.info("=" * 50)
    logger.info(f"📋 Arguments: {args}")
    
    # Load data
    dataset = load_and_prepare_data(args.train_data_path)
    
    # Setup model
    model, tokenizer = setup_model_and_tokenizer(args.model_id)
    
    # Setup LoRA
    model = setup_lora(model, args)
    
    # Tokenize data
    tokenized_dataset = tokenize_data(dataset, tokenizer, args.max_seq_length)
    
    # Training arguments with improvements
    training_args = TrainingArguments(
        output_dir=args.output_dir,
        num_train_epochs=args.num_train_epochs,
        per_device_train_batch_size=args.per_device_train_batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        learning_rate=args.learning_rate,
        warmup_steps=100,
        logging_steps=50,
        save_steps=250,
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
    tokenizer.save_pretrained(args.output_dir)
    
    logger.info("✅ Training completed successfully!")

if __name__ == "__main__":
    main()
