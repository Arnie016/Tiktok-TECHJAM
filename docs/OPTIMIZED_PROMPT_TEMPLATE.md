# 🚀 Ready-to-Use Optimized Prompt Template

## 📋 **For Your Deployed Model: `geo-compliance-endpoint-fixed-lora`**

### 🎯 **Optimized Prompt Template**

```python
# Copy-paste this template for your testing
prompt = """You are a compliance analyst. Analyze the software feature and output structured JSON only.

Output Format:
{
  "compliance_flag": "...",
  "law": "...",
  "reason": "..."
}

Example:
Input: Feature Name: Age Verification; Description: Blocks under-18 logins.
Output: {
  "compliance_flag": "Needs Geo-Compliance",
  "law": "Florida Online Protections for Minors Act",
  "reason": "The law requires under-18 protections"
}

Input: Feature Name: Data Export Tool; Description: Allows users to download their data.
Output: {
  "compliance_flag": "Needs Geo-Compliance",
  "law": "GDPR Article 20",
  "reason": "Right to data portability requires export functionality"
}

Now analyze this feature:

Feature Name: {YOUR_FEATURE_NAME}
Feature Description: {YOUR_FEATURE_DESCRIPTION}

Output:"""

# Optimized parameters for your model
parameters = {
    "max_new_tokens": 200,
    "temperature": 0.2,
    "top_p": 0.7,
    "do_sample": True,
    "return_full_text": False
}
```

### 🔧 **Quick Test Function**

```python
import boto3
import json

def test_compliance_feature(feature_name, feature_description, source=None):
    """Test a feature with optimized prompt"""
    
    # Optimized prompt
    prompt = f"""You are a compliance analyst. Analyze the software feature and output structured JSON only.

Output Format:
{{
  "compliance_flag": "...",
  "law": "...",
  "reason": "..."
}}

Example:
Input: Feature Name: Age Verification; Description: Blocks under-18 logins.
Output: {{
  "compliance_flag": "Needs Geo-Compliance",
  "law": "Florida Online Protections for Minors Act",
  "reason": "The law requires under-18 protections"
}}

Input: Feature Name: Data Export Tool; Description: Allows users to download their data.
Output: {{
  "compliance_flag": "Needs Geo-Compliance",
  "law": "GDPR Article 20",
  "reason": "Right to data portability requires export functionality"
}}

Now analyze this feature:

Feature Name: {feature_name}
Feature Description: {feature_description}"""

    if source:
        prompt += f"\nSource: {source}"
    
    prompt += "\n\nOutput:"
    
    # Optimized parameters
    parameters = {
        "max_new_tokens": 200,
        "temperature": 0.2,
        "top_p": 0.7,
        "do_sample": True,
        "return_full_text": False
    }
    
    # Test endpoint
    runtime_client = boto3.client('sagemaker-runtime', region_name='us-west-2')
    
    response = runtime_client.invoke_endpoint(
        EndpointName='geo-compliance-endpoint-fixed-lora',
        ContentType='application/json',
        Body=json.dumps({
            "inputs": prompt,
            "parameters": parameters
        })
    )
    
    result = json.loads(response['Body'].read().decode())
    return result[0].get('generated_text', '') if isinstance(result, list) else str(result)

# Example usage
response = test_compliance_feature(
    "Age Verification System",
    "Blocks under-18 users from accessing certain content and features",
    "Florida Online Protections for Minors Act"
)
print(response)
```

### 📊 **Current Model Performance**

Based on our testing, your model:

✅ **What's Working:**
- Responds to queries (not empty)
- Endpoint is healthy
- LoRA weights are loaded

⚠️ **Current Limitations:**
- Generates very short responses ("txt", "com", "jpg")
- Not producing structured JSON
- Limited task understanding

### 🎯 **Recommended Next Steps**

#### **Option 1: Immediate Testing**
Use the template above to test with your specific features. The model might work better with:
- Shorter, simpler prompts
- Features similar to your training data
- Different parameter combinations

#### **Option 2: Parameter Tuning**
Try these parameter variations:

```python
# Conservative (most likely to work)
parameters = {
    "max_new_tokens": 100,
    "temperature": 0.1,
    "top_p": 0.6,
    "do_sample": True,
    "return_full_text": False
}

# More creative
parameters = {
    "max_new_tokens": 300,
    "temperature": 0.4,
    "top_p": 0.8,
    "do_sample": True,
    "return_full_text": False
}
```

#### **Option 3: Model Upgrade**
For production use, consider:
1. **Larger base model**: DialoGPT-large/xl (774M-1.5B params)
2. **Instruction model**: Mistral-7B-Instruct or similar
3. **More training data**: 500-1000 diverse examples

### 🔍 **Testing Strategy**

1. **Start Simple**: Test with basic features first
2. **Gradual Complexity**: Add more context gradually
3. **Parameter Sweep**: Try different temperature/top_p values
4. **Post-processing**: Extract and validate JSON manually

### 📝 **Example Test Cases**

```python
# Test case 1: Simple feature
test_compliance_feature(
    "User Data Export",
    "Allows users to download their personal data"
)

# Test case 2: Age-related feature
test_compliance_feature(
    "Age Verification",
    "Requires users to verify they are 18+",
    "COPPA"
)

# Test case 3: Location-based feature
test_compliance_feature(
    "Geographic Content Filtering",
    "Filters content based on user location"
)
```

### 🎉 **Your Model Status**

**Endpoint**: `geo-compliance-endpoint-fixed-lora` ✅ **Deployed and Running**  
**Training**: ✅ **Successful** (62.8% loss reduction)  
**LoRA**: ✅ **Applied** (6.3M parameters)  
**Performance**: ⚠️ **Limited** (needs optimization)

**Ready for testing with the optimized prompts above!** 🚀


