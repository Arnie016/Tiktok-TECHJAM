#!/usr/bin/env python3
"""
Model Recommendation Script for SageMaker Fine-tuning
Analyzes dataset size, available models, and recommends optimal GPU instances.
"""

import json
import os
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

try:
    import boto3
    from transformers import AutoTokenizer, AutoConfig
except ImportError:
    print("Installing required packages...")
    import subprocess
    subprocess.run(['pip', 'install', 'boto3', 'transformers'], check=True)
    import boto3
    from transformers import AutoTokenizer, AutoConfig

@dataclass
class ModelRecommendation:
    model_id: str
    parameters: str
    memory_gb: int
    recommended_instance: str
    instance_cost_per_hour: float
    training_time_estimate: str
    pros: List[str]
    cons: List[str]
    suitable_for_dataset_size: str

# Model configurations for compliance/legal tasks
RECOMMENDED_MODELS = {
    # Small-Medium Models (Good for your dataset size)
    "microsoft/DialoGPT-medium": {
        "parameters": "355M",
        "memory_gb": 4,
        "context_length": 1024,
        "good_for": "Conversational AI, compliance reasoning",
        "training_complexity": "Low"
    },
    "microsoft/DialoGPT-large": {
        "parameters": "762M", 
        "memory_gb": 6,
        "context_length": 1024,
        "good_for": "Better reasoning, still fast",
        "training_complexity": "Low-Medium"
    },
    "EleutherAI/gpt-neo-1.3B": {
        "parameters": "1.3B",
        "memory_gb": 8,
        "context_length": 2048,
        "good_for": "Good reasoning, legal text understanding",
        "training_complexity": "Medium"
    },
    "EleutherAI/gpt-neo-2.7B": {
        "parameters": "2.7B",
        "memory_gb": 12,
        "context_length": 2048,
        "good_for": "Strong reasoning, complex compliance logic",
        "training_complexity": "Medium"
    },
    "microsoft/DialoGPT-large": {
        "parameters": "762M",
        "memory_gb": 6,
        "context_length": 1024,
        "good_for": "Dialogue/reasoning tasks",
        "training_complexity": "Medium"
    },
    "bigscience/bloom-1b1": {
        "parameters": "1.1B",
        "memory_gb": 8,
        "context_length": 2048,
        "good_for": "Multilingual, good reasoning",
        "training_complexity": "Medium"
    },
    "bigscience/bloom-3b": {
        "parameters": "3B",
        "memory_gb": 14,
        "context_length": 2048,
        "good_for": "Strong performance, multilingual",
        "training_complexity": "Medium-High"
    },
    # Larger models (if you want more performance)
    "EleutherAI/gpt-j-6B": {
        "parameters": "6B",
        "memory_gb": 24,
        "context_length": 2048,
        "good_for": "Very strong reasoning, complex legal analysis",
        "training_complexity": "High"
    },
    "EleutherAI/pythia-6.9b": {
        "parameters": "6.9B", 
        "memory_gb": 28,
        "context_length": 2048,
        "good_for": "Research-grade model, excellent for legal tasks",
        "training_complexity": "High"
    }
}

# SageMaker GPU instances and their capabilities
SAGEMAKER_INSTANCES = {
    "ml.g4dn.xlarge": {
        "gpu": "T4 (16GB)",
        "gpu_memory": 16,
        "cpu_memory": 16,
        "vcpus": 4,
        "cost_per_hour": 0.736,
        "good_for": "Small-medium models up to 2B params"
    },
    "ml.g4dn.2xlarge": {
        "gpu": "T4 (16GB)",
        "gpu_memory": 16,
        "cpu_memory": 32,
        "vcpus": 8,
        "cost_per_hour": 1.044,
        "good_for": "Medium models up to 3B params"
    },
    "ml.g5.xlarge": {
        "gpu": "A10G (24GB)",
        "gpu_memory": 24,
        "cpu_memory": 16,
        "vcpus": 4,
        "cost_per_hour": 1.408,
        "good_for": "Medium-large models up to 4B params"
    },
    "ml.g5.2xlarge": {
        "gpu": "A10G (24GB)",
        "gpu_memory": 24,
        "cpu_memory": 32,
        "vcpus": 8,
        "cost_per_hour": 2.03,
        "good_for": "Large models up to 6B params"
    },
    "ml.g5.4xlarge": {
        "gpu": "A10G (24GB)",
        "gpu_memory": 24,
        "cpu_memory": 64,
        "vcpus": 16,
        "cost_per_hour": 2.944,
        "good_for": "Large models with complex data"
    },
    "ml.g5.8xlarge": {
        "gpu": "A10G (24GB)",
        "gpu_memory": 24,
        "cpu_memory": 128,
        "vcpus": 32,
        "cost_per_hour": 4.352,
        "good_for": "Very large models or multi-GPU training"
    },
    "ml.p3.2xlarge": {
        "gpu": "V100 (32GB)",
        "gpu_memory": 32,
        "cpu_memory": 61,
        "vcpus": 8,
        "cost_per_hour": 4.284,
        "good_for": "Large models up to 8B params"
    },
    "ml.p4d.24xlarge": {
        "gpu": "8x A100 (40GB each)",
        "gpu_memory": 320,
        "cpu_memory": 1152,
        "vcpus": 96,
        "cost_per_hour": 43.39,
        "good_for": "Massive models, distributed training"
    }
}

def analyze_dataset(jsonl_path: str) -> Dict:
    """Analyze the dataset to understand size and complexity."""
    with open(jsonl_path, 'r') as f:
        lines = f.readlines()
    
    total_entries = len(lines)
    
    # Sample a few entries to analyze
    sample_size = min(10, total_entries)
    samples = []
    
    for i in range(0, total_entries, max(1, total_entries // sample_size)):
        try:
            entry = json.loads(lines[i])
            samples.append(entry)
        except:
            continue
    
    # Analyze input/output lengths
    input_lengths = []
    output_lengths = []
    
    for sample in samples:
        input_text = sample.get('input', '')
        output_text = sample.get('output', '')
        input_lengths.append(len(input_text.split()))
        output_lengths.append(len(output_text.split()))
    
    avg_input_len = sum(input_lengths) / len(input_lengths) if input_lengths else 0
    avg_output_len = sum(output_lengths) / len(output_lengths) if output_lengths else 0
    max_input_len = max(input_lengths) if input_lengths else 0
    max_output_len = max(output_lengths) if output_lengths else 0
    
    return {
        "total_entries": total_entries,
        "avg_input_length": avg_input_len,
        "avg_output_length": avg_output_len,
        "max_input_length": max_input_len,
        "max_output_length": max_output_len,
        "estimated_tokens_per_example": avg_input_len + avg_output_len,
        "complexity": "High" if max_input_len > 500 else "Medium" if max_input_len > 200 else "Low"
    }

def check_model_availability(model_id: str, hf_token: str) -> bool:
    """Check if model is available on HuggingFace."""
    try:
        config = AutoConfig.from_pretrained(model_id, token=hf_token)
        return True
    except Exception as e:
        print(f"❌ {model_id} not accessible: {e}")
        return False

def estimate_training_time(dataset_size: int, model_params: str, instance_type: str) -> str:
    """Estimate training time based on dataset size and model complexity."""
    param_multiplier = {
        "355M": 1.0,
        "762M": 1.5,
        "1.1B": 2.0,
        "1.3B": 2.2,
        "2.7B": 3.5,
        "3B": 4.0,
        "6B": 8.0,
        "6.9B": 9.0
    }
    
    instance_multiplier = {
        "ml.g4dn.xlarge": 2.0,
        "ml.g4dn.2xlarge": 1.8,
        "ml.g5.xlarge": 1.0,
        "ml.g5.2xlarge": 0.8,
        "ml.g5.4xlarge": 0.6,
        "ml.p3.2xlarge": 0.5,
        "ml.p4d.24xlarge": 0.2
    }
    
    base_time_hours = (dataset_size / 1000) * 2  # 2 hours per 1k examples baseline
    model_factor = param_multiplier.get(model_params, 1.0)
    instance_factor = instance_multiplier.get(instance_type, 1.0)
    
    estimated_hours = base_time_hours * model_factor * instance_factor
    
    if estimated_hours < 1:
        return f"{int(estimated_hours * 60)} minutes"
    elif estimated_hours < 24:
        return f"{estimated_hours:.1f} hours"
    else:
        return f"{estimated_hours/24:.1f} days"

def get_recommendations(dataset_analysis: Dict, hf_token: str) -> List[ModelRecommendation]:
    """Generate model recommendations based on dataset analysis."""
    recommendations = []
    
    dataset_size = dataset_analysis["total_entries"]
    complexity = dataset_analysis["complexity"]
    avg_length = dataset_analysis["estimated_tokens_per_example"]
    
    print(f"📊 Dataset Analysis:")
    print(f"  - Size: {dataset_size} entries")
    print(f"  - Complexity: {complexity}")
    print(f"  - Avg tokens per example: {avg_length:.0f}")
    print(f"  - Max input length: {dataset_analysis['max_input_length']} words")
    print()
    
    for model_id, model_info in RECOMMENDED_MODELS.items():
        if not check_model_availability(model_id, hf_token):
            continue
            
        params = model_info["parameters"]
        memory_needed = model_info["memory_gb"]
        
        # Find suitable instance
        suitable_instances = []
        for instance_name, instance_info in SAGEMAKER_INSTANCES.items():
            if instance_info["gpu_memory"] >= memory_needed * 1.5:  # 1.5x safety margin
                suitable_instances.append((instance_name, instance_info))
        
        if not suitable_instances:
            continue
            
        # Pick the most cost-effective instance
        best_instance = min(suitable_instances, key=lambda x: x[1]["cost_per_hour"])
        instance_name, instance_info = best_instance
        
        # Generate pros/cons
        pros = []
        cons = []
        
        if "355M" in params or "762M" in params:
            pros.extend(["Fast training", "Low cost", "Good for prototyping"])
            cons.extend(["Limited reasoning capability"])
            suitability = "Perfect for 1.5k dataset"
        elif "1.1B" in params or "1.3B" in params:
            pros.extend(["Good balance of performance/cost", "Reasonable training time", "Strong reasoning"])
            cons.extend(["Moderate resource requirements"])
            suitability = "Excellent for 1.5k dataset"
        elif "2.7B" in params or "3B" in params:
            pros.extend(["Strong performance", "Excellent reasoning", "Good for complex tasks"])
            cons.extend(["Higher cost", "Longer training time"])
            suitability = "Very good for 1.5k dataset"
        elif "6B" in params or "6.9B" in params:
            pros.extend(["Excellent performance", "State-of-the-art reasoning", "Research-grade quality"])
            cons.extend(["High cost", "Long training time", "May overfit on small datasets"])
            suitability = "Overkill for 1.5k dataset, but highest quality"
        
        training_time = estimate_training_time(dataset_size, params, instance_name)
        
        recommendation = ModelRecommendation(
            model_id=model_id,
            parameters=params,
            memory_gb=memory_needed,
            recommended_instance=instance_name,
            instance_cost_per_hour=instance_info["cost_per_hour"],
            training_time_estimate=training_time,
            pros=pros,
            cons=cons,
            suitable_for_dataset_size=suitability
        )
        
        recommendations.append(recommendation)
    
    # Sort by suitability and cost-effectiveness
    def score_recommendation(rec):
        size_score = 10 if "Perfect" in rec.suitable_for_dataset_size else \
                    8 if "Excellent" in rec.suitable_for_dataset_size else \
                    6 if "Very good" in rec.suitable_for_dataset_size else 3
        cost_score = max(0, 10 - rec.instance_cost_per_hour)
        return size_score + cost_score
    
    recommendations.sort(key=score_recommendation, reverse=True)
    return recommendations

def print_recommendations(recommendations: List[ModelRecommendation]):
    """Print formatted recommendations."""
    print("🚀 MODEL RECOMMENDATIONS FOR YOUR 1.5K DATASET:")
    print("=" * 80)
    
    for i, rec in enumerate(recommendations[:5], 1):  # Top 5 recommendations
        print(f"\n🏆 RANK #{i}: {rec.model_id}")
        print(f"   📊 Parameters: {rec.parameters}")
        print(f"   💻 Recommended Instance: {rec.recommended_instance}")
        print(f"   💰 Cost: ${rec.instance_cost_per_hour:.2f}/hour")
        print(f"   ⏱️  Estimated Training Time: {rec.training_time_estimate}")
        print(f"   🎯 Suitability: {rec.suitable_for_dataset_size}")
        print(f"   ✅ Pros: {', '.join(rec.pros)}")
        print(f"   ⚠️  Cons: {', '.join(rec.cons)}")
        
        if i == 1:
            print(f"   🌟 RECOMMENDED: This is your best choice!")
        
        print("-" * 60)

def generate_deployment_script(recommendation: ModelRecommendation):
    """Generate a deployment script for the recommended model."""
    script_content = f'''#!/usr/bin/env python3
"""
Deploy {recommendation.model_id} for geo-compliance training
Auto-generated recommendation script
"""

import boto3
import sagemaker
from sagemaker.huggingface import HuggingFace

# Configuration
MODEL_ID = "{recommendation.model_id}"
INSTANCE_TYPE = "{recommendation.recommended_instance}"
TRAINING_DATA_PATH = "s3://your-bucket/train_refined_v4.jsonl"
OUTPUT_PATH = "s3://your-bucket/output/"
ROLE = "arn:aws:iam::561947681110:role/SageMakerExecutionRole"

# Hyperparameters optimized for your dataset size
hyperparameters = {{
    'model_name_or_path': MODEL_ID,
    'dataset_name': 'json',
    'dataset_config_name': 'default',
    'do_train': True,
    'do_eval': True,
    'fp16': True,
    'per_device_train_batch_size': 4 if '{recommendation.parameters}' in ['6B', '6.9B'] else 8,
    'per_device_eval_batch_size': 4 if '{recommendation.parameters}' in ['6B', '6.9B'] else 8,
    'gradient_accumulation_steps': 2,
    'learning_rate': 5e-5,
    'num_train_epochs': 3,
    'warmup_steps': 100,
    'logging_steps': 10,
    'save_steps': 500,
    'eval_steps': 500,
    'output_dir': '/opt/ml/model',
    'overwrite_output_dir': True,
    'save_strategy': 'steps',
    'evaluation_strategy': 'steps',
    'load_best_model_at_end': True,
    'metric_for_best_model': 'eval_loss',
    'greater_is_better': False,
    'report_to': 'none'
}}

# Create HuggingFace estimator
huggingface_estimator = HuggingFace(
    entry_point='train.py',
    source_dir='.',
    instance_type=INSTANCE_TYPE,
    instance_count=1,
    role=ROLE,
    transformers_version='4.49.0',
    pytorch_version='2.6.0',
    py_version='py312',
    hyperparameters=hyperparameters,
    environment={{
        'HF_TOKEN': 'your_hf_token_here'
    }}
)

print(f"🚀 Starting training of {{MODEL_ID}} on {{INSTANCE_TYPE}}")
print(f"💰 Estimated cost: ${{hyperparameters.get('num_train_epochs', 3) * {recommendation.instance_cost_per_hour:.2f}:.2f}} for {recommendation.training_time_estimate}")

# Start training
huggingface_estimator.fit({{'train': TRAINING_DATA_PATH}})

print("✅ Training complete!")
print(f"📍 Model artifacts: {{huggingface_estimator.model_data}}")
'''
    
    with open(f"deploy_{recommendation.model_id.replace('/', '_')}.py", 'w') as f:
        f.write(script_content)
    
    print(f"💾 Generated deployment script: deploy_{recommendation.model_id.replace('/', '_')}.py")

def main():
    # Check for HF token
    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token:
        print("⚠️  HF_TOKEN environment variable not found. Some models may not be accessible.")
        hf_token = ""
    
    # Analyze dataset
    dataset_path = "sagemaker-finetune/data/train_refined_v4.jsonl"
    if not os.path.exists(dataset_path):
        print(f"❌ Dataset not found at {dataset_path}")
        return
    
    print("🔍 Analyzing your dataset...")
    dataset_analysis = analyze_dataset(dataset_path)
    
    print("🤖 Checking model availability and generating recommendations...")
    recommendations = get_recommendations(dataset_analysis, hf_token)
    
    if not recommendations:
        print("❌ No suitable models found. Check your HF_TOKEN.")
        return
    
    print_recommendations(recommendations)
    
    # Generate deployment script for top recommendation
    if recommendations:
        print(f"\n🎯 Generating deployment script for top recommendation...")
        generate_deployment_script(recommendations[0])
        
        print(f"\n💡 QUICK START:")
        print(f"   1. Export your HF token: export HF_TOKEN=your_token_here")
        print(f"   2. Update the S3 paths in the generated script")
        print(f"   3. Run: python deploy_{recommendations[0].model_id.replace('/', '_')}.py")

if __name__ == "__main__":
    main()

