TEST_TESTPHI_ENDPOINT

Attributes
- endpoint_name: testphi
- region: us-west-2
- profile: bedrock-561
- hf_task_expected: text-generation (required by Hugging Face DLC)

Project Structure Context
- Root: sagemaker-finetune/
- Relevant files: deploy_phi2_model.py (deployment), inference.py (custom handler, if used)

Goal
- Manually invoke the SageMaker endpoint `testphi` from terminal and verify learned behavior.

Commands
1) Ensure AWS profile/region
```bash
export AWS_PROFILE=bedrock-561
export AWS_DEFAULT_REGION=us-west-2
```

2) Confirm endpoint status is InService
```bash
aws sagemaker describe-endpoint \
  --endpoint-name testphi \
  --region us-west-2 \
  --profile bedrock-561 \
  | sed -n 's/.*"EndpointStatus": "\([^"]*\)".*/\1/p'
```

3) Create a payload (edit the prompt to your scenario)
```bash
cat > payload.json << 'JSON'
{
  "inputs": "Provide a geo-compliance analysis for an adult content site accessible from Florida. Outline age verification, data retention, and access restrictions.",
  "parameters": {
    "max_new_tokens": 256,
    "temperature": 0.2,
    "top_p": 0.9,
    "do_sample": true,
    "return_full_text": false
  }
}
JSON
```

4) Invoke normally (HF_TASK must be text-generation on the endpoint)
```bash
aws sagemaker-runtime invoke-endpoint \
  --endpoint-name testphi \
  --body fileb://payload.json \
  --content-type application/json \
  --accept application/json \
  --region us-west-2 \
  --profile bedrock-561 \
  response.json | cat

cat response.json
```

5) If you get an error about missing HF_TASK, invoke with a runtime override header
```bash
aws sagemaker-runtime invoke-endpoint \
  --endpoint-name testphi \
  --body fileb://payload.json \
  --content-type application/json \
  --accept application/json \
  --custom-attributes 'task=text-generation' \
  --region us-west-2 \
  --profile bedrock-561 \
  response.json | cat

cat response.json
```

6) Optional: quick Python snippet (boto3) if you prefer
```python
import json, boto3
runtime = boto3.client("sagemaker-runtime", region_name="us-west-2")
payload = {
  "inputs": "Provide a geo-compliance analysis for an adult content site accessible from Florida.",
  "parameters": {
    "max_new_tokens": 256,
    "temperature": 0.2,
    "top_p": 0.9,
    "do_sample": True,
    "return_full_text": False,
  },
}
resp = runtime.invoke_endpoint(
    EndpointName="testphi",
    Body=json.dumps(payload),
    ContentType="application/json",
    Accept="application/json",
    # If HF_TASK error occurs, uncomment next line:
    # CustomAttributes="task=text-generation",
)
print(json.loads(resp["Body"].read().decode("utf-8")))
```

What To Look For
- Learned behavior: responses reference compliance concepts (age-gating, geo-IP restrictions, statutory citations, risk ratings) rather than echoing the prompt.
- If it only paraphrases/echoes inputs, consider more epochs, better prompt formatting in training, and verifying LoRA adapter loading on the endpoint.

Notes / Insights
- Hugging Face DLCs require HF_TASK=text-generation for text gen. If the endpoint was created without it, you can override per-invocation via the `--custom-attributes 'task=text-generation'` header.
- For Phi-2 in this setup, lower temperature (≈0.2–0.4) is usually more factual and stable.




