### HF_TASK fix for `phi-2` endpoint

- **Account / Region**: 561947681110 / us-west-2 (profile: `bedrock-561`)
- **Endpoint**: `phi-2`
- **Previous Status**: InService, but invocation returned 400 ModelError
- **Observed Error**: Container required env `HF_TASK` to be set for the inference pipeline
- **Image in use**: `763104351884.dkr.ecr.us-west-2.amazonaws.com/huggingface-pytorch-inference:1.13.1-transformers4.26.0-gpu-py39-cu117-ubuntu20.04`
- **Model artifact**: `s3://sagemaker-us-west-2-561947681110/phi2-fixed-2058/output/model.tar.gz`

Project structure (relevant)
- `sagemaker-finetune/update_endpoint.py`: CLI-based update path
- `sagemaker-finetune/monitor_and_test_endpoint.py`: runtime test helper
- `docs/MODEL_DEPLOYMENT_STATUS.md`: rolling deployment status

Proposed change / implementation
- Create a new SageMaker Model with environment:
  - `HF_TASK=text-generation`
  - `HF_HUB_ENABLE_HF_TRANSFER=0`
  - `TRANSFORMERS_CACHE=/tmp/transformers_cache`
- Create a new EndpointConfig referencing the new Model
- Update `phi-2` to use the new EndpointConfig

Key points and insights
- The HF 4.26 inference container expects `HF_TASK` to route to the correct pipeline; missing it yields a 400 InternalServerException with a list of supported tasks.
- Re-using the existing model artifact is fine; only the environment needed adjustment.
- Instance currently `ml.m5.2xlarge`; consider `ml.g5.xlarge` if generation latency is high post-fix.

Next steps
- Wait until endpoint status returns to InService
- Re-test invocation via CLI (JSON body) and capture response
