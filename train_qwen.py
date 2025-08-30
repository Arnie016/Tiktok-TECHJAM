#!/usr/bin/env python3
"""
Fixed Training Script for Phi-2 - Proper Gradient Handling
Based on working phi2-fixed-2058 configuration
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
from peft import LoraConfig, get_peft_model, TaskType, prepare_model_for_kbit_training
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
    parser.add_argument("--learning_rate", type=float, default=1e-4)
    parser.add_argument("--per_device_train_batch_size", type=int, default=2)
    parser.add_argument("--gradient_accumulation_steps", type=int, default=4)
    
    # LoRA arguments
    parser.add_argument("--lora_r", type=int, default=16)
    parser.add_argument("--lora_alpha", type=int, default=32)
    parser.add_argument("--lora_dropout", type=float, default=0.05)
    
    # Paths
    parser.add_argument("--train_data_path", type=str, default="/opt/ml/input/data/train")
    parser.add_argument("--output_dir", type=str, default="/opt/ml/model")
    
    return parser.parse_args()

def load_and_prepare_data(data_path):
    """Load and prepare training data"""
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
    with open(data_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            try:
                example = json.loads(line.strip())
                
                # Create training text in chat format
                text = f"### Instruction:\n{example['instruction']}\n\n### Input:\n{example['input']}\n\n### Response:\n{example['output']}<|endoftext|>"
                data.append({"text": text})
                
            except Exception as e:
                logger.warning(f"⚠️ Skipping line {line_num}: {e}")
                continue
    
    logger.info(f"✅ Loaded {len(data)} examples")
    return Dataset.from_list(data)

def setup_model_and_tokenizer(model_id):
    """Setup model and tokenizer"""
    logger.info(f"🤖 Loading model: {model_id}")
    
    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.pad_token_id = tokenizer.eos_token_id
    
    # Load model in bfloat16 for better stability
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=torch.bfloat16,
        trust_remote_code=True,
        device_map="auto",
        use_cache=False  # Important for training
    )
    
    # Prepare model for training
    model = prepare_model_for_kbit_training(model)
    
    return model, tokenizer

def setup_lora(model, args):
    """Setup LoRA configuration"""
    logger.info(f"🔧 Setting up LoRA with r={args.lora_r}, alpha={args.lora_alpha}")
    
    # Enable gradient checkpointing
    model.gradient_checkpointing_enable()
    
    # LoRA config
    lora_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        target_modules=["q_proj", "k_proj", "v_proj", "dense"],
        lora_dropout=args.lora_dropout,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
    )
    
    model = get_peft_model(model, lora_config)
    
    # Print trainable parameters
    trainable_params = 0
    all_param = 0
    for _, param in model.named_parameters():
        all_param += param.numel()
        if param.requires_grad:
            trainable_params += param.numel()
    
    logger.info(f"Trainable params: {trainable_params:,} || All params: {all_param:,} || Trainable%: {100 * trainable_params / all_param:.2f}")
    
    return model

def main():
    """Main training function"""
    args = parse_args()
    
    logger.info("🚀 Starting Phi-2 LoRA training")
    logger.info("=" * 50)
    logger.info(f"📋 Model: {args.model_id}")
    logger.info(f"📋 Epochs: {args.num_train_epochs}")
    logger.info(f"📋 Learning rate: {args.learning_rate}")
    logger.info(f"📋 LoRA r: {args.lora_r}, alpha: {args.lora_alpha}")
    
    # Load data
    dataset = load_and_prepare_data(args.train_data_path)
    
    # Setup model and tokenizer
    model, tokenizer = setup_model_and_tokenizer(args.model_id)
    
    # Setup LoRA
    model = setup_lora(model, args)
    
    # Tokenize data
    def tokenize_function(examples):
        return tokenizer(
            examples["text"],
            truncation=True,
            max_length=args.max_seq_length,
            padding=False,
        )
    
    tokenized_dataset = dataset.map(
        tokenize_function,
        batched=True,
        remove_columns=dataset.column_names
    )
    
    # Training arguments
    training_args = TrainingArguments(
        output_dir=args.output_dir,
        num_train_epochs=args.num_train_epochs,
        per_device_train_batch_size=args.per_device_train_batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        learning_rate=args.learning_rate,
        fp16=False,  # Use bfloat16 instead
        bf16=True,
        logging_steps=10,
        save_steps=100,
        save_total_limit=2,
        remove_unused_columns=False,
        dataloader_drop_last=True,
        warmup_steps=20,
        report_to=None,
        load_best_model_at_end=False,
    )
    
    # Data collator
    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False,
    )
    
    # Create trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset,
        data_collator=data_collator,
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
