# Endpoint Deployment (phi2-fixed-2058)

## Attributes
- **Region**: `us-west-2`
- **Training job**: `phi2-fixed-2058`
- **Artifact (S3)**: `s3://sagemaker-us-west-2-561947681110/phi2-fixed-2058/output/model.tar.gz`
- **Role**: `arn:aws:iam::561947681110:role/SageMakerExecutionRole`
- **Image (train)**: `763104351884.dkr.ecr.us-west-2.amazonaws.com/huggingface-pytorch-training:2.5.1-transformers4.49.0-gpu-py311-cu124-ubuntu22.04`
- **Script used**: `sagemaker-finetune/deploy_phi2_model.py`
- **Instance (inference)**: `ml.g5.xlarge`

## Deploy Command
```bash
# From repo root
python3 -m venv .venv_phi && source .venv_phi/bin/activate
python -m pip install boto3 sagemaker
python sagemaker-finetune/deploy_phi2_model.py --test
```
- Creates endpoint: `phi2-compliance-analyzer-YYYYMMDD-HHMM`
- Tests with a sample request automatically

## Invoke Examples
```python
# Python (boto3)
import boto3, json
rt=boto3.Session(profile_name='bedrock-561',region_name='us-west-2').client('sagemaker-runtime')
body={"inputs":"Analyze...","parameters":{"max_new_tokens":256,"temperature":0.7,"do_sample":True}}
print(json.loads(rt.invoke_endpoint(EndpointName='<ENDPOINT>',ContentType='application/json',Body=json.dumps(body))['Body'].read()))
```
```bash
# cURL
curl -s -H "Content-Type: application/json" \
  --data '{"inputs":"Analyze...","parameters":{"max_new_tokens":256,"temperature":0.7,"do_sample":true}}' \
  https://runtime.sagemaker.us-west-2.amazonaws.com/endpoints/<ENDPOINT>/invocations
```

## Troubleshooting
- **400 ModelError: /opt/ml/model missing config.json**: Endpoint was created without proper model files/env. Redeploy using the script above to point `model_data` to your `model.tar.gz`.
- **S3 EndpointConnectionError**: Ensure `AWS_PROFILE=bedrock-561` and region `us-west-2`; verify with `aws s3 ls s3://sagemaker-us-west-2-561947681110/`.




