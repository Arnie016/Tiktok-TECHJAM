# Active Endpoint: phi-2

## Summary
- **Name**: `phi-2`
- **Status**: InService
- **Type**: Real-time
- **Region**: `us-west-2`
- **ARN**: `arn:aws:sagemaker:us-west-2:561947681110:endpoint/phi-2`
- **Invoke URL**: `https://runtime.sagemaker.us-west-2.amazonaws.com/endpoints/phi-2/invocations`
- **Logs**: `/aws/sagemaker/endpoints/phi-2`

## Python Invoke (boto3)
```python
import boto3, json

session = boto3.Session(profile_name='bedrock-561', region_name='us-west-2')
rt = session.client('sagemaker-runtime')

payload = {
  "inputs": "Analyze the following software feature to determine its geo-compliance requirements. Provide the compliance flag, the relevant law, and the reason.\n\nFeature Name: UT Parental Consent & Curfew\nFeature Description: Requires verified parental consent for minor accounts in Utah and enforces nightly curfew and default privacy settings.\n\nLaw Context (structured JSON):\n[]",
  "parameters": {"max_new_tokens": 256, "temperature": 0.7, "do_sample": True}
}

resp = rt.invoke_endpoint(
  EndpointName='phi-2',
  ContentType='application/json',
  Body=json.dumps(payload)
)
print(json.loads(resp['Body'].read().decode()))
```

## cURL Invoke
```bash
curl -s \
  -H "Content-Type: application/json" \
  -H "X-Amzn-SageMaker-Custom-Attributes: HF_TASK=text-generation" \
  --data '{
    "inputs": "Analyze the following software feature to determine its geo-compliance requirements. Provide the compliance flag, the relevant law, and the reason.\n\nFeature Name: US CSAM Reporting Pipeline\nFeature Description: Detects and reports apparent child sexual abuse material to NCMEC and preserves commingled content per federal law.\n\nLaw Context (structured JSON):\n[]",
    "parameters": {"max_new_tokens": 256, "temperature": 0.7, "do_sample": true}
  }' \
  https://runtime.sagemaker.us-west-2.amazonaws.com/endpoints/phi-2/invocations
```

## Notes
- Most existing test scripts expect an endpoint name; set it to `phi-2` to reuse them.
- If your model expects instruction/input fields instead of HF `inputs`, use the alternative in `test_current_endpoint.py`.




