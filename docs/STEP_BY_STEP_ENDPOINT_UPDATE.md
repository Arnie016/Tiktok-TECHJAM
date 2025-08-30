# Step-by-Step Endpoint Update Guide

## Network Issue: Connect to VPN First!
**Problem**: NUS WiFi blocks AWS domains (DNS resolution fails)
**Solution**: Connect to your VPN before proceeding

Test connectivity:
```bash
# After connecting VPN, this should work:
nslookup s3.us-west-2.amazonaws.com
```

## Option 1: Automated Update (After VPN Connected)
```bash
cd /Users/hema/Desktop/bedrock
source .venv_phi/bin/activate
AWS_PROFILE=bedrock-561 python update_phi2_endpoint.py
```

## Option 2: Manual AWS Console Update

### Step 1: Access SageMaker Console
Go to: https://us-west-2.console.aws.amazon.com/sagemaker/home?region=us-west-2

### Step 2: Find Your Endpoint
1. Click **Inference** → **Endpoints**
2. Find: `phi2-compliance-analyzer-20250830-0011`
3. Click on the endpoint name

### Step 3: Update Endpoint
1. Click **Update endpoint** (orange button)
2. Select **Create a new model**

### Step 4: Create New Model
**Model Settings:**
- **Model name**: `phi2-fixed-inference-model-v2`
- **IAM role**: `arn:aws:iam::561947681110:role/SageMakerExecutionRole`

**Container Definition:**
- **Provide model artifacts**: ✅ Yes
- **Location of inference code**: Select **Amazon ECR image location**

**Critical Settings:**
```
Container image URI: 763104351884.dkr.ecr.us-west-2.amazonaws.com/huggingface-pytorch-inference:2.5.1-transformers4.49.0-gpu-py311-cu124-ubuntu22.04

Model artifacts: s3://sagemaker-us-west-2-561947681110/phi2-inference-code/fixed_inference.tar.gz
```

**Environment Variables** (Click "Add environment variable" for each):
```
BASE_MODEL_ID = microsoft/phi-2
MODEL_ARTIFACT_S3 = s3://sagemaker-us-west-2-561947681110/phi2-fixed-2058/output/model.tar.gz
HF_TASK = text-generation
TRANSFORMERS_CACHE = /tmp/transformers_cache
HF_HOME = /tmp/hf_home
HUGGINGFACE_HUB_CACHE = /tmp/huggingface
XDG_CACHE_HOME = /tmp
HF_HUB_ENABLE_HF_TRANSFER = 0
```

### Step 5: Create Endpoint Configuration
1. Click **Create model** → **Next**
2. **Configuration name**: `phi2-fixed-config-v2`
3. **Model**: Select the model you just created
4. **Instance type**: `ml.g5.2xlarge`
5. **Instance count**: `1`
6. Click **Create endpoint configuration**

### Step 6: Update Endpoint
1. **Endpoint configuration**: Select `phi2-fixed-config-v2`
2. Click **Update endpoint**
3. Wait 5-10 minutes for status: **InService**

## What Each Component Does

### Inference Image
```
763104351884.dkr.ecr.us-west-2.amazonaws.com/huggingface-pytorch-inference:2.5.1-transformers4.49.0-gpu-py311-cu124-ubuntu22.04
```
- **763104351884**: AWS's Deep Learning Container registry
- **huggingface-pytorch-inference**: Pre-built container with HuggingFace + PyTorch
- **2.5.1-transformers4.49.0**: PyTorch 2.5.1 + Transformers 4.49.0
- **gpu-py311-cu124**: GPU support, Python 3.11, CUDA 12.4

### S3 Paths
```
Model Artifacts: s3://sagemaker-us-west-2-561947681110/phi2-inference-code/fixed_inference.tar.gz
```
- Contains: `inference.py` (custom loading script) + `requirements.txt`

```
Original Training: s3://sagemaker-us-west-2-561947681110/phi2-fixed-2058/output/model.tar.gz
```
- Contains: LoRA adapter weights from your training

### Environment Variables Explained
- **BASE_MODEL_ID**: Downloads `microsoft/phi-2` from HuggingFace Hub
- **MODEL_ARTIFACT_S3**: Downloads your trained LoRA adapters
- **Cache paths**: Use writable `/tmp` directories (fixes read-only filesystem errors)

## Testing After Update
Once endpoint shows **InService**:

### Test Payload
```json
{
    "inputs": "Analyze compliance requirements for social media age verification in Utah.",
    "parameters": {
        "max_new_tokens": 128,
        "temperature": 0.7,
        "do_sample": true
    }
}
```

### Expected Response (Proof of Training)
```
"Compliance Flag: REQUIRED
Relevant Law: Utah Code Ann. § 76-5b-206 (Social Media Usage Amendments)
Reason: Utah requires social media platforms to implement age verification..."
```

## Why This Works
1. **Base Model**: Downloads fresh `microsoft/phi-2` from HuggingFace
2. **LoRA Adapters**: Applies your trained compliance-analysis weights
3. **Fixed Environment**: All cache directories point to writable `/tmp`
4. **Runtime Download**: Fetches both base model and adapters at inference time

**Connect VPN first, then proceed with either automated or manual update!**

