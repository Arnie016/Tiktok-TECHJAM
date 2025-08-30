# Manual Endpoint Update Guide (DNS Issue Workaround)

## Issue
Local DNS cannot resolve AWS endpoints (NXDOMAIN error for s3.us-west-2.amazonaws.com), preventing SDK-based deployment.

## Solution: AWS Console Manual Update

### Step 1: Access SageMaker Console
1. Go to [AWS SageMaker Console](https://us-west-2.console.aws.amazon.com/sagemaker/home?region=us-west-2)
2. Navigate to **Inference** → **Endpoints**
3. Find and click: `phi2-compliance-analyzer-20250830-0011`

### Step 2: Update Endpoint Configuration
1. Click **Update endpoint**
2. Create new model or select existing model
3. **Create New Model** with these settings:

#### Model Settings
- **Model name**: `phi2-fixed-inference-model`
- **IAM role**: `arn:aws:iam::561947681110:role/SageMakerExecutionRole`

#### Container Definition
- **Container image**: `763104351884.dkr.ecr.us-west-2.amazonaws.com/huggingface-pytorch-inference:2.5.1-transformers4.49.0-gpu-py311-cu124-ubuntu22.04`
- **Model data**: `s3://sagemaker-us-west-2-561947681110/phi2-inference-code/fixed_inference.tar.gz`

#### Environment Variables
```
BASE_MODEL_ID=microsoft/phi-2
MODEL_ARTIFACT_S3=s3://sagemaker-us-west-2-561947681110/phi2-fixed-2058/output/model.tar.gz
HF_TASK=text-generation
TRANSFORMERS_CACHE=/tmp/transformers_cache
HF_HOME=/tmp/hf_home
HUGGINGFACE_HUB_CACHE=/tmp/huggingface
XDG_CACHE_HOME=/tmp
HF_HUB_ENABLE_HF_TRANSFER=0
```

### Step 3: Create Endpoint Configuration
- **Configuration name**: `phi2-fixed-config`
- **Model**: Select the model created above
- **Instance type**: `ml.g5.2xlarge`
- **Instance count**: `1`

### Step 4: Update Endpoint
- Select the new configuration
- Click **Update endpoint**
- Wait for status to become **InService** (5-10 minutes)

### Step 5: Test the Updated Endpoint

#### Option A: SageMaker Console Test
1. Go to endpoint details page
2. Click **Test endpoint**
3. Use this test payload:
```json
{
    "inputs": "Analyze the following software feature to determine its geo-compliance requirements. Provide the compliance flag, the relevant law, and the reason.\n\nFeature Name: EU GDPR Data Processing\nFeature Description: Collects user personal data with consent for targeted advertising in EU markets.\n\nLaw Context (structured JSON):\n[]",
    "parameters": {
        "max_new_tokens": 128,
        "temperature": 0.7,
        "do_sample": true
    }
}
```

#### Option B: cURL Test (after DNS fixed)
```bash
curl -s -H "Content-Type: application/json" \
  --aws-sigv4 "aws:amz:us-west-2:sagemaker" \
  --user "ACCESS_KEY:SECRET_KEY" \
  --data '{
    "inputs": "Analyze compliance requirements for social media age verification in Utah.",
    "parameters": {"max_new_tokens": 128, "temperature": 0.7, "do_sample": true}
  }' \
  https://runtime.sagemaker.us-west-2.amazonaws.com/endpoints/phi2-compliance-analyzer-20250830-0011/invocations
```

## What This Fix Does
1. **Loads Base Model**: Downloads `microsoft/phi-2` at runtime
2. **Applies LoRA Adapters**: Loads your trained adapters from S3 and applies them to the base model
3. **Fixes Filesystem Issues**: Uses writable `/tmp` directories for all caches
4. **Proper Environment**: Sets all required HuggingFace environment variables

## Expected Result
The endpoint should now respond with compliance analysis like:
```
"Compliance Flag: REQUIRED
Relevant Law: EU GDPR Article 6 (Lawfulness of processing)
Reason: Personal data processing for advertising requires explicit consent under GDPR..."
```

## Network Issue Resolution
To fix DNS and use scripts again:
1. Check DNS settings: `System Preferences → Network → Advanced → DNS`
2. Add public DNS servers: `8.8.8.8`, `1.1.1.1`
3. Flush DNS cache: `sudo dscacheutil -flushcache`
4. Test: `nslookup s3.us-west-2.amazonaws.com`

## Files Ready for Testing (When Network Fixed)
- `sagemaker-finetune/simple_test_phi2_endpoint.py` - Python test script
- `update_phi2_endpoint.py` - Automated deployment script


