# PHI2 Training Job - phi2-fixed-2058

## Summary
- **Status**: Completed
- **Job name**: `phi2-fixed-2058`
- **Region**: `us-west-2`
- **Instance**: `ml.g5.2xlarge` (1)
- **Container**: `763104351884.dkr.ecr.us-west-2.amazonaws.com/huggingface-pytorch-training:2.5.1-transformers4.49.0-gpu-py311-cu124-ubuntu22.04`
- **Train time**: 340s (billable 340s)
- **IAM Role**: `arn:aws:iam::561947681110:role/SageMakerExecutionRole`

## Inputs
- **Training data (S3)**: `s3://arnav-finetune-1756054916/data/train_refined_v2.jsonl`
- **Program**: `train_qwen.py`
- **Base model**: `microsoft/phi-2`
- **Hyperparameters**:
  - `epochs=3`
  - `learning_rate=1e-4`
  - `max_seq_length=512`
  - `hf_hub_enable_hf_transfer=false`

## Outputs
- **Model artifact (S3)**:
  - `s3://sagemaker-us-west-2-561947681110/phi2-fixed-2058/output/model.tar.gz`

## Environment
- `HF_HUB_ENABLE_HF_TRANSFER=0`
- `HF_TOKEN` and `SM_HP_HF_TOKEN` set (masked)

## Next: Deploy Endpoint
1. Ensure AWS credentials can pass role `arn:aws:iam::561947681110:role/SageMakerExecutionRole`.
2. Use the deployment script:
   ```bash
   cd sagemaker-finetune
   python3 deploy_phi2_model.py --test
   ```
   - Uses:
     - `MODEL_S3_PATH`: `s3://sagemaker-us-west-2-561947681110/phi2-fixed-2058/output/model.tar.gz`
     - `ROLE`: `arn:aws:iam::561947681110:role/SageMakerExecutionRole`
     - Creates endpoint like `phi2-compliance-analyzer-YYYYMMDD-HHMM`

## Test Payload (example)
```json
{
  "instruction": "Analyze the following software feature to determine its geo-compliance requirements. Provide the compliance flag, the relevant law, and the reason.",
  "input": "Feature Name: EU DSA Risk & Transparency Engine\nFeature Description: Automates systemic risk assessments and DSA transparency reporting for very large online platforms (VLOP), including recommender transparency.\n\nLaw Context (structured JSON):\n[]"
}
```

## Notes
- Training image and Transformers version align with deployment pins (Transformers 4.49, Torch 2.6 runtime).
- If endpoint creation fails, verify `iam:PassRole` permission for `SageMakerExecutionRole`.




