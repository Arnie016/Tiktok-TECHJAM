# HuggingFace Token Setup

## Current Issue
The training job needs a valid HuggingFace token to access the DeepSeek model.

## Required Action
Replace the placeholder token in `sagemaker-finetune/launch_job.py`:

```python
env = {
    "HF_TOKEN": "hf_XXXXXXXXXXXXXXXX",  # ← Replace with your actual token
    "HF_HUB_ENABLE_HF_TRANSFER": "1"
}
```

## How to Get Your Token

1. **Go to HuggingFace**: https://huggingface.co/settings/tokens
2. **Create New Token**: 
   - Name: `sagemaker-training`
   - Role: `Read`
   - Copy the token (starts with `hf_`)

3. **Update the Script**: Replace `hf_XXXXXXXXXXXXXXXX` with your actual token

## Alternative: Use DeepSeek-R1-Distill-Llama-8B

If you prefer the newer reasoning model, change the MODEL_ID to:
```python
MODEL_ID = "deepseek-ai/DeepSeek-R1-Distill-Llama-8B"
```

## Security Note
- Never commit tokens to version control
- Consider using AWS Secrets Manager for production
- The token only needs read access to download models

## Next Steps
1. Get your HF token
2. Update the launch script
3. Run the training job again
