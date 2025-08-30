#!/usr/bin/env python3
"""
Minimal Working Training Script for Phi-2 with LoRA
Based on proven working examples from Hugging Face
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
from peft import LoraConfig, get_peft_model
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

def load_data(data_path):
    """Load training data"""
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
                
                # Simple conversation format
                conversation = f"""<|user|>
{example['instruction']}

{example['input']}
<|assistant|>
{example['output']}"""
                
                data.append({"text": conversation})
                
            except Exception as e:
                logger.warning(f"⚠️ Skipping line {line_num}: {e}")
                continue
    
    logger.info(f"✅ Loaded {len(data)} examples")
    return Dataset.from_list(data)

def main():
    """Main training function"""
    args = parse_args()
    
    logger.info("🚀 Starting minimal Phi-2 training")
    logger.info("=" * 50)
    
    # Load data
    dataset = load_data(args.train_data_path)
    
    # Load tokenizer
    logger.info(f"🔤 Loading tokenizer: {args.model_id}")
    tokenizer = AutoTokenizer.from_pretrained(args.model_id, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    # Load model
    logger.info(f"🤖 Loading model: {args.model_id}")
    model = AutoModelForCausalLM.from_pretrained(
        args.model_id,
        torch_dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True
    )
    
    # Setup LoRA - MINIMAL CONFIG
    logger.info("🔧 Setting up LoRA")
    lora_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        target_modules=["q_proj", "k_proj", "v_proj", "dense"],
        bias="none",
        task_type="CAUSAL_LM"
    )
    
    # Apply LoRA
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    
    # Tokenize data
    def tokenize_function(examples):
        return tokenizer(
            examples["text"],
            truncation=True,
            padding=False,
            max_length=args.max_seq_length
        )
    
    tokenized_dataset = dataset.map(
        tokenize_function,
        batched=True,
        remove_columns=dataset.column_names
    )
    
    # Training arguments - MINIMAL
    training_args = TrainingArguments(
        output_dir=args.output_dir,
        num_train_epochs=args.num_train_epochs,
        per_device_train_batch_size=args.per_device_train_batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        learning_rate=args.learning_rate,
        warmup_steps=50,
        logging_steps=10,
        save_steps=500,
        save_total_limit=1,
        fp16=True,
        dataloader_drop_last=True,
        report_to=None
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

