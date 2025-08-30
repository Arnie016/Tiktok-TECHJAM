#!/usr/bin/env python3
"""
Simple Training Script for Phi-2 - Uses proven HuggingFace approach
Based on the working phi2-fixed-2058 configuration
"""

import os
import json
import logging
from transformers import AutoTokenizer, AutoModelForCausalLM, Trainer, TrainingArguments
from peft import LoraConfig, get_peft_model, TaskType
from datasets import Dataset, load_dataset
import torch

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Main training function using environment variables"""
    
    # Get parameters from environment (SageMaker sets these)
    model_id = os.environ.get("SM_HP_MODEL_ID", "microsoft/phi-2")
    epochs = int(os.environ.get("SM_HP_EPOCHS", "3"))
    learning_rate = float(os.environ.get("SM_HP_LEARNING_RATE", "5e-5"))
    max_seq_length = int(os.environ.get("SM_HP_MAX_SEQ_LENGTH", "512"))
    
    # Paths
    train_dir = os.environ.get("SM_CHANNEL_TRAIN", "/opt/ml/input/data/train")
    model_dir = os.environ.get("SM_MODEL_DIR", "/opt/ml/model")
    
    logger.info(f"🚀 Starting Phi-2 training")
    logger.info(f"📋 Model: {model_id}")
    logger.info(f"📋 Epochs: {epochs}")
    logger.info(f"📋 Learning rate: {learning_rate}")
    logger.info(f"📋 Train dir: {train_dir}")
    logger.info(f"📋 Output dir: {model_dir}")
    
    # Find training file
    train_file = None
    for file in os.listdir(train_dir):
        if file.endswith('.jsonl'):
            train_file = os.path.join(train_dir, file)
            break
    
    if not train_file:
        raise FileNotFoundError(f"No .jsonl file found in {train_dir}")
    
    logger.info(f"📖 Using training file: {train_file}")
    
    # Load dataset
    dataset = load_dataset('json', data_files=train_file, split='train')
    logger.info(f"✅ Loaded {len(dataset)} examples")
    
    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    # Load model
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=torch.float16,
        trust_remote_code=True,
        device_map="auto"
    )
    
    # Setup LoRA - simple configuration
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=16,  # Smaller rank for stability
        lora_alpha=32,
        lora_dropout=0.1,
        target_modules=["q_proj", "k_proj", "v_proj", "dense"],
        bias="none"
    )
    
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    
    # Prepare data - simple approach
    def prepare_sample(example):
        instruction = example['instruction']
        input_text = example['input'] 
        output_text = example['output']
        
        # Simple prompt format
        prompt = f"Instruction: {instruction}\n\nInput: {input_text}\n\nOutput: {output_text}"
        
        # Tokenize
        tokens = tokenizer(
            prompt,
            truncation=True,
            padding=False,
            max_length=max_seq_length,
            return_tensors="pt"
        )
        
        # Set labels for language modeling
        tokens["labels"] = tokens["input_ids"].clone()
        
        return {
            "input_ids": tokens["input_ids"].squeeze(),
            "attention_mask": tokens["attention_mask"].squeeze(),
            "labels": tokens["labels"].squeeze()
        }
    
    # Process dataset
    train_dataset = dataset.map(prepare_sample, remove_columns=dataset.column_names)
    
    # Training arguments - simple and proven
    training_args = TrainingArguments(
        output_dir=model_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        learning_rate=learning_rate,
        warmup_steps=50,
        logging_steps=25,
        save_steps=100,
        save_total_limit=2,
        fp16=True,
        dataloader_drop_last=True,
        remove_unused_columns=False,
        report_to=None,
        load_best_model_at_end=False
    )
    
    # Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        tokenizer=tokenizer
    )
    
    # Train
    logger.info("🎯 Starting training...")
    trainer.train()
    
    # Save
    logger.info("💾 Saving model...")
    trainer.save_model()
    tokenizer.save_pretrained(model_dir)
    
    logger.info("✅ Training completed!")

if __name__ == "__main__":
    main()
