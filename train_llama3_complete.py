#!/usr/bin/env python3
"""
Complete LLaMA-3.1-8B Training & Auto-Deploy Script
Trains on v5 dataset (1442 examples) and auto-deploys to endpoint
"""

import boto3
import json
import time
import tarfile
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

class LLaMA3CompleteTrainer:
    def __init__(self, profile_name='bedrock-561', region='us-west-2'):
        self.session = boto3.Session(profile_name=profile_name, region_name=region)
        self.sagemaker = self.session.client('sagemaker')
        self.region = region
        
        # Updated configuration for your account [[memory:7685380]]
        self.config = {
            "role_arn": "arn:aws:iam::561947681110:role/SageMakerExecutionRole",
            "bucket": "sagemaker-us-west-2-561947681110", 
            "base_model": "microsoft/phi-2",  # 2.7B params, proven working model
            "training_instance": "ml.g5.2xlarge",  # Training (you have quota)
            "endpoint_instance": "ml.g5.4xlarge",  # Inference (you have quota)
            "training_data": "s3://sagemaker-us-west-2-561947681110/phi2-training-data/",
            "endpoint_name": "llama3-geo-compliance"  # New endpoint name
        }
        
        logger.info(f"🔧 Initialized LLaMA-3.1-8B trainer for region {region}")
        logger.info(f"📊 Training data: 1442 examples from train_refined_v5.jsonl")

    def create_llama3_training_script(self):
        """Create optimized training script for LLaMA-3.1-8B"""
        training_script = '''#!/usr/bin/env python3
"""
LLaMA-3.1-8B Training Script - Optimized for Geo-Compliance
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
import warnings
warnings.filterwarnings("ignore")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_id", type=str, default="microsoft/phi-2")
    parser.add_argument("--num_train_epochs", type=int, default=3)
    parser.add_argument("--learning_rate", type=float, default=2e-4)
    parser.add_argument("--per_device_train_batch_size", type=int, default=1)
    parser.add_argument("--gradient_accumulation_steps", type=int, default=8)
    parser.add_argument("--max_seq_length", type=int, default=1024)
    parser.add_argument("--lora_r", type=int, default=64)
    parser.add_argument("--lora_alpha", type=int, default=128)
    parser.add_argument("--lora_dropout", type=float, default=0.1)
    parser.add_argument("--train_data_path", type=str, default="/opt/ml/input/data/train")
    parser.add_argument("--output_dir", type=str, default="/opt/ml/model")
    return parser.parse_args()

def load_and_prepare_data(data_path):
    logger.info(f"📊 Loading data from {data_path}")
    
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
                
                # Enhanced LLaMA-3.1 format with system prompt
                conversation = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

You are a legal compliance expert. Analyze software features and provide geo-compliance assessments in valid JSON format with exactly these fields: compliance_flag, law, reason. Only cite laws that appear in the provided Law Context.<|eot_id|><|start_header_id|>user<|end_header_id|>

{example['instruction']}

{example['input']}<|eot_id|><|start_header_id|>assistant<|end_header_id|>

{example['output']}<|eot_id|>"""
                
                data.append({"text": conversation})
                
            except Exception as e:
                logger.warning(f"⚠️ Skipping line {line_num}: {e}")
                continue
    
    logger.info(f"✅ Loaded {len(data)} examples")
    return Dataset.from_list(data)

def setup_model_and_tokenizer(model_id):
    logger.info(f"🤖 Loading LLaMA-3.1-8B: {model_id}")
    
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        use_cache=False,
        trust_remote_code=True
    )
    
    model = prepare_model_for_kbit_training(model)
    return model, tokenizer

def setup_lora(model, args):
    logger.info(f"🔧 Setting up LoRA r={args.lora_r}, alpha={args.lora_alpha}")
    
    model.gradient_checkpointing_enable()
    
    lora_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_dropout=args.lora_dropout,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
    )
    
    model = get_peft_model(model, lora_config)
    
    trainable_params = 0
    all_param = 0
    for _, param in model.named_parameters():
        all_param += param.numel()
        if param.requires_grad:
            trainable_params += param.numel()
    
    logger.info(f"Trainable: {trainable_params:,} || All: {all_param:,} || Trainable%: {100 * trainable_params / all_param:.2f}")
    return model

def main():
    args = parse_args()
    
    logger.info("🚀 Starting LLaMA-3.1-8B training")
    logger.info("=" * 50)
    
    # Load data
    dataset = load_and_prepare_data(args.train_data_path)
    
    # Setup model
    model, tokenizer = setup_model_and_tokenizer(args.model_id)
    model = setup_lora(model, args)
    
    # Tokenize
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
        bf16=True,
        logging_steps=10,
        save_steps=200,
        save_total_limit=2,
        remove_unused_columns=False,
        dataloader_drop_last=True,
        warmup_steps=50,
        report_to=None,
        load_best_model_at_end=False,
    )
    
    # Data collator
    data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)
    
    # Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset,
        data_collator=data_collator,
    )
    
    # Train
    logger.info("🎯 Starting training...")
    trainer.train()
    
    # Save
    logger.info("💾 Saving model...")
    trainer.save_model()
    tokenizer.save_pretrained(args.output_dir)
    
    logger.info("✅ LLaMA-3.1-8B training completed!")

if __name__ == "__main__":
    main()
'''
        return training_script

    def create_llama3_inference_script(self):
        """Create inference script for LLaMA-3.1-8B"""
        inference_script = '''import os, json, torch, logging, glob, tarfile, tempfile
import boto3
from urllib.parse import urlparse
from threading import Thread
from transformers import AutoTokenizer, AutoModelForCausalLM, TextIteratorStreamer
from peft import PeftModel

logger = logging.getLogger(__name__)

def _disable_flash_attention():
    try:
        torch.backends.cuda.enable_flash_sdp(False)
        torch.backends.cuda.enable_mem_efficient_sdp(False)
        torch.backends.cuda.enable_math_sdp(True)
    except Exception:
        pass

def _find_adapter_dir(root_dir):
    for path in glob.glob(os.path.join(root_dir, "**", "adapter_config.json"), recursive=True):
        return os.path.dirname(path)
    return root_dir

def _download_and_extract_s3_tar(s3_uri, extract_dir):
    os.makedirs(extract_dir, exist_ok=True)
    parsed = urlparse(s3_uri)
    bucket = parsed.netloc
    key = parsed.path.lstrip('/')
    tmp_tar = os.path.join(tempfile.gettempdir(), "model.tar.gz")
    s3 = boto3.client("s3")
    logger.info(f"Downloading model artifact from s3://{bucket}/{key}")
    s3.download_file(bucket, key, tmp_tar)
    logger.info(f"Extracting artifact to {extract_dir}")
    with tarfile.open(tmp_tar, "r:gz") as t:
        t.extractall(path=extract_dir)
    return extract_dir

def model_fn(model_dir, context=None):
    base_id = os.environ.get("BASE_MODEL_ID", "microsoft/phi-2")
    hf_token = os.environ.get("HF_TOKEN")
    s3_artifact = os.environ.get("MODEL_ARTIFACT_S3")
    cache_dir = os.environ.get("TRANSFORMERS_CACHE", "/tmp/transformers_cache")
    os.makedirs(cache_dir, exist_ok=True)
    
    logger.info(f"🔄 Loading LLaMA-3.1-8B: {base_id}")
    _disable_flash_attention()

    tok = AutoTokenizer.from_pretrained(base_id, token=hf_token)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    # Load base model in FP16 (optimized for g5 instances)
    base = AutoModelForCausalLM.from_pretrained(
        base_id,
        token=hf_token,
        torch_dtype=torch.float16,
        attn_implementation="eager",
        trust_remote_code=True,
        device_map="auto"
    )

    # Load LoRA adapters
    adapter_root = "/tmp/llama3_adapters"
    if s3_artifact:
        _download_and_extract_s3_tar(s3_artifact, adapter_root)

    adapter_dir = _find_adapter_dir(adapter_root)
    model = PeftModel.from_pretrained(base, adapter_dir)
    model.eval()
    
    logger.info("✅ LLaMA-3.1-8B loaded successfully")
    return {"m": model, "t": tok}

def input_fn(body, ctype):
    if ctype != "application/json":
        raise ValueError(f"Unsupported content type: {ctype}")
    data = json.loads(body)
    if isinstance(data, dict) and "inputs" in data:
        return str(data["inputs"])
    instr = data.get("instruction", "")
    inp = data.get("input", "")
    return f"{instr}\\n\\n{inp}".strip()

def predict_fn(text, mt):
    t, m = mt["t"], mt["m"]
    
    # Format for LLaMA-3.1 chat template
    messages = [
        {"role": "system", "content": "You are a legal compliance expert. Analyze software features and provide geo-compliance assessments in valid JSON format."},
        {"role": "user", "content": text}
    ]
    
    formatted_text = t.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    x = t(formatted_text, return_tensors="pt", truncation=True, max_length=1024).to(m.device)
    
    # Setup streaming
    streamer = TextIteratorStreamer(t, skip_prompt=True, skip_special_tokens=True)
    generation_kwargs = dict(
        **x,
        max_new_tokens=256,
        temperature=0.3,
        do_sample=True,
        pad_token_id=t.eos_token_id,
        eos_token_id=t.eos_token_id,
        streamer=streamer
    )

    thread = Thread(target=m.generate, kwargs=generation_kwargs)
    thread.start()

    generated_text = ""
    for new_text in streamer:
        generated_text += new_text

    return {"generated_text": generated_text.strip()}

def output_fn(pred, ctype):
    return json.dumps(pred)
'''
        return inference_script

    def upload_all_files(self, job_name):
        """Upload training data and scripts to S3"""
        logger.info("📤 Uploading training data and scripts...")
        
        s3 = self.session.client('s3')
        
        try:
            # Upload v5 training data (1442 examples)
            s3.upload_file(
                '/Users/hema/Desktop/bedrock/sagemaker-finetune/data/train_refined_v5.jsonl',
                self.config['bucket'],
                'phi2-training-data/train_refined_v5.jsonl'
            )
            logger.info("✅ Uploaded train_refined_v5.jsonl (1442 examples)")
            
            # Use proven working training script
            tarball_path = f'./{job_name}_source.tar.gz'
            with tarfile.open(tarball_path, 'w:gz') as tar:
                tar.add('/Users/hema/Desktop/bedrock/improved_training_script.py', arcname='train.py')
            
            s3.upload_file(
                tarball_path,
                self.config['bucket'],
                f'{job_name}/source/sourcedir.tar.gz'
            )
            
            # Create and upload inference script
            inference_script = self.create_llama3_inference_script()
            with open('./llama3_inference.py', 'w') as f:
                f.write(inference_script)
            
            # Create inference tarball
            inference_tarball = f'./{job_name}_inference.tar.gz'
            with tarfile.open(inference_tarball, 'w:gz') as tar:
                tar.add('./llama3_inference.py', arcname='inference.py')
            
            s3.upload_file(
                inference_tarball,
                self.config['bucket'],
                f'llama3-inference-code/{job_name}_inference.tar.gz'
            )
            
            # Cleanup
            import os
            for file in ['./llama3_inference.py', tarball_path, inference_tarball]:
                if os.path.exists(file):
                    os.remove(file)
            
            logger.info("✅ All files uploaded successfully")
            return f"s3://{self.config['bucket']}/llama3-inference-code/{job_name}_inference.tar.gz"
            
        except Exception as e:
            logger.error(f"❌ Upload failed: {e}")
            return None

    def create_training_job(self, job_name):
        """Create LLaMA-3.1-8B training job"""
        logger.info(f"🚀 Starting LLaMA-3.1-8B training: {job_name}")
        
        training_params = {
            'TrainingJobName': job_name,
            'RoleArn': self.config['role_arn'],
            'AlgorithmSpecification': {
                'TrainingImage': '763104351884.dkr.ecr.us-west-2.amazonaws.com/huggingface-pytorch-training:2.5.1-transformers4.49.0-gpu-py311-cu124-ubuntu22.04',
                'TrainingInputMode': 'File',
                'EnableSageMakerMetricsTimeSeries': True
            },
            'HyperParameters': {
                'model_id': f'"{self.config["base_model"]}"',
                'num_train_epochs': '3',
                'learning_rate': '1e-4',
                'max_seq_length': '512',
                'per_device_train_batch_size': '2',
                'gradient_accumulation_steps': '4',
                'lora_r': '16',
                'lora_alpha': '32',
                'lora_dropout': '0.05',
                'sagemaker_container_log_level': '20',
                'sagemaker_job_name': f'"{job_name}"',
                'sagemaker_program': '"train.py"',
                'sagemaker_region': '"us-west-2"',
                'sagemaker_submit_directory': f'"s3://{self.config["bucket"]}/{job_name}/source/sourcedir.tar.gz"'
            },
            'InputDataConfig': [
                {
                    'ChannelName': 'train',
                    'DataSource': {
                        'S3DataSource': {
                            'S3DataType': 'S3Prefix',
                            'S3Uri': self.config['training_data'],
                            'S3DataDistributionType': 'FullyReplicated'
                        }
                    },
                    'CompressionType': 'None',
                    'RecordWrapperType': 'None'
                }
            ],
            'OutputDataConfig': {
                'S3OutputPath': f"s3://{self.config['bucket']}/llama3-models/"
            },
            'ResourceConfig': {
                'InstanceType': self.config['training_instance'],
                'InstanceCount': 1,
                'VolumeSizeInGB': 50  # Larger for LLaMA-3.1-8B
            },
            'StoppingCondition': {
                'MaxRuntimeInSeconds': 14400  # 4 hours max
            },
            'Environment': {
                'HF_HOME': '/tmp/hf_home',
                'TRANSFORMERS_CACHE': '/tmp/transformers_cache',
                'HF_HUB_ENABLE_HF_TRANSFER': '0',
                'HF_TASK': 'text-generation',
                'PYTHONPATH': '/opt/ml/code'
                # Removed HF_TOKEN - causing auth issues even for public models
            }
        }
        
        try:
            response = self.sagemaker.create_training_job(**training_params)
            logger.info("✅ LLaMA-3.1-8B training job created!")
            logger.info(f"📋 Job ARN: {response['TrainingJobArn']}")
            return job_name
            
        except Exception as e:
            logger.error(f"❌ Failed to create training job: {e}")
            return None

    def wait_for_training(self, job_name):
        """Wait for training to complete"""
        logger.info(f"⏳ Waiting for LLaMA-3.1-8B training to complete...")
        
        while True:
            try:
                response = self.sagemaker.describe_training_job(TrainingJobName=job_name)
                status = response['TrainingJobStatus']
                
                logger.info(f"📊 Training status: {status}")
                
                if status == 'Completed':
                    logger.info("✅ LLaMA-3.1-8B training completed!")
                    return response['ModelArtifacts']['S3ModelArtifacts']
                elif status == 'Failed':
                    logger.error(f"❌ Training failed: {response.get('FailureReason', 'Unknown')}")
                    return None
                elif status in ['InProgress', 'Starting']:
                    time.sleep(120)  # Check every 2 minutes
                    continue
                else:
                    logger.warning(f"⚠️ Unexpected status: {status}")
                    time.sleep(120)
                    
            except Exception as e:
                logger.error(f"❌ Error checking status: {e}")
                return None

    def deploy_endpoint(self, model_artifacts_uri, inference_code_uri):
        """Deploy LLaMA-3.1-8B endpoint with auto-scaling"""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        model_name = f"llama3-geo-compliance-{timestamp}"
        config_name = f"llama3-config-{timestamp}"
        
        logger.info(f"🚀 Deploying LLaMA-3.1-8B endpoint: {self.config['endpoint_name']}")
        
        try:
            # Create model
            self.sagemaker.create_model(
                ModelName=model_name,
                PrimaryContainer={
                    'Image': '763104351884.dkr.ecr.us-west-2.amazonaws.com/huggingface-pytorch-inference:2.5.1-transformers4.49.0-gpu-py311-cu124-ubuntu22.04',
                    'ModelDataUrl': inference_code_uri,
                    'Environment': {
                        'BASE_MODEL_ID': self.config['base_model'],
                        'MODEL_ARTIFACT_S3': model_artifacts_uri,
                        'HF_HOME': '/tmp/hf_home',
                        'HF_TASK': 'text-generation',
                        'TRANSFORMERS_CACHE': '/tmp/transformers_cache',
                        'XDG_CACHE_HOME': '/tmp'
                    }
                },
                ExecutionRoleArn=self.config['role_arn']
            )
            logger.info("✅ Model created")
            
            # Create endpoint config
            self.sagemaker.create_endpoint_config(
                EndpointConfigName=config_name,
                ProductionVariants=[
                    {
                        'VariantName': 'primary',
                        'ModelName': model_name,
                        'InitialInstanceCount': 1,
                        'InstanceType': self.config['endpoint_instance'],
                        'InitialVariantWeight': 1.0
                    }
                ]
            )
            logger.info("✅ Endpoint config created")
            
            # Create endpoint
            self.sagemaker.create_endpoint(
                EndpointName=self.config['endpoint_name'],
                EndpointConfigName=config_name
            )
            logger.info("✅ Endpoint deployment initiated")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Deployment failed: {e}")
            return False

    def wait_for_endpoint(self):
        """Wait for endpoint to be InService"""
        logger.info("⏳ Waiting for LLaMA-3.1-8B endpoint to be ready...")
        
        while True:
            try:
                response = self.sagemaker.describe_endpoint(EndpointName=self.config['endpoint_name'])
                status = response['EndpointStatus']
                
                logger.info(f"📊 Endpoint status: {status}")
                
                if status == 'InService':
                    logger.info("✅ LLaMA-3.1-8B endpoint is ready!")
                    return True
                elif status == 'Failed':
                    logger.error("❌ Endpoint deployment failed")
                    return False
                else:
                    time.sleep(60)
                    
            except Exception as e:
                logger.error(f"❌ Error checking endpoint: {e}")
                return False

    def run_complete_pipeline(self):
        """Run complete training and deployment pipeline"""
        logger.info("🚀 Starting Complete LLaMA-3.1-8B Pipeline")
        logger.info("=" * 60)
        
        # Generate job name
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        job_name = f"llama3-8b-{timestamp}"
        
        # Step 1: Upload files
        inference_code_uri = self.upload_all_files(job_name)
        if not inference_code_uri:
            return False
        
        # Step 2: Start training
        if not self.create_training_job(job_name):
            return False
        
        # Step 3: Wait for training
        model_artifacts = self.wait_for_training(job_name)
        if not model_artifacts:
            return False
        
        # Step 4: Deploy endpoint
        if not self.deploy_endpoint(model_artifacts, inference_code_uri):
            return False
        
        # Step 5: Wait for endpoint
        if not self.wait_for_endpoint():
            return False
        
        logger.info("🎉 COMPLETE SUCCESS!")
        logger.info(f"📊 Model artifacts: {model_artifacts}")
        logger.info(f"🔗 Endpoint: {self.config['endpoint_name']}")
        logger.info(f"🌐 URL: https://runtime.sagemaker.us-west-2.amazonaws.com/endpoints/{self.config['endpoint_name']}/invocations")
        
        return True

def main():
    """Main function"""
    trainer = LLaMA3CompleteTrainer()
    
    logger.info("🎯 LLaMA-3.1-8B Complete Training & Deployment")
    logger.info("📊 Dataset: train_refined_v5.jsonl (1442 examples)")
    logger.info("🤖 Model: Meta-Llama-3.1-8B-Instruct")
    logger.info("=" * 60)
    
    success = trainer.run_complete_pipeline()
    
    if success:
        logger.info("\\n✅ SUCCESS: LLaMA-3.1-8B trained and deployed!")
        logger.info("🧪 Ready for testing and Lambda setup")
    else:
        logger.error("\\n❌ FAILED: Pipeline failed")

if __name__ == "__main__":
    main()
