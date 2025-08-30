# Phi-2 SageMaker Endpoint Test Results

## Overview
Testing of the deployed phi-2 SageMaker endpoint for geo-compliance analysis model.

## Endpoint Details
- **Name**: phi-2
- **Status**: InService (with persistent timeout issues)
- **Region**: us-west-2
- **Account**: 561947681110
- **Instance Type**: ml.g5.4xlarge (upgraded from ml.g5.2xlarge)
- **Model**: microsoft/phi-2 with LoRA adapters

## Issues Encountered

### 1. Initial Syntax Error ✅ RESOLVED
- **Problem**: Malformed f-string in deployed inference.py
- **Error**: `SyntaxError: unterminated string literal (detected at line 101)`
- **Fix**: Corrected the f-string syntax in input_fn function

### 2. Model Function Signature ✅ RESOLVED
- **Problem**: `model_fn() takes 1 positional argument but 2 were given`
- **Error**: SageMaker was passing a context parameter
- **Fix**: Updated model_fn to accept optional context parameter

### 3. PEFT Configuration Sanitization ✅ RESOLVED
- **Problem**: `KeyError: 'peft_type'` - adapter config sanitization was removing required field
- **Error**: PEFT library requires peft_type field in adapter config
- **Fix**: Added 'peft_type' to allowed keys list in _sanitize_adapter_config

### 4. Instance Size Upgrade ✅ COMPLETED
- **Problem**: Endpoint timing out on ml.g5.2xlarge
- **Action**: Upgraded to ml.g5.4xlarge (quota increased to 1)
- **Result**: Still timing out (5+ minutes)

### 5. Persistent Timeout Issue ❌ UNRESOLVED
- **Problem**: Endpoint times out during inference even with larger instance
- **Status**: Model loads successfully but inference never completes
- **Timeouts Tested**: 120s, 300s (5 minutes)
- **Possible Root Causes**: 
  - Model architecture issue
  - Adapter loading problem
  - Memory/GPU configuration issue
  - Inference code logic error

## Test Results

### CLI Testing
```bash
# Initial smoke test - failed with syntax error
aws sagemaker-runtime invoke-endpoint --endpoint-name phi-2 --profile bedrock-561

# After fixes - endpoint responds but times out
aws sagemaker-runtime invoke-endpoint --endpoint-name phi-2 --profile bedrock-561

# After ml.g5.4xlarge upgrade - still times out
aws sagemaker-runtime invoke-endpoint --endpoint-name phi-2 --profile bedrock-561
```

### Python Testing
```python
# Created test_phi2_endpoint.py with multiple test cases
# All tests timeout after 120 seconds (ml.g5.2xlarge)
# All tests timeout after 300 seconds (ml.g5.4xlarge)
# Model appears to be loading but inference never completes
```

## Deployment History
1. **Initial deployment**: Failed with syntax error
2. **First fix**: Corrected f-string syntax
3. **Second fix**: Added context parameter to model_fn
4. **Third fix**: Fixed PEFT config sanitization
5. **Fourth fix**: Upgraded to ml.g5.4xlarge instance
6. **Current**: Endpoint InService but persistent timeout

## CloudWatch Logs Analysis
- ✅ Model loads successfully: "Model model loaded"
- ✅ Adapters extract correctly: "Extracting artifact to /tmp/phi2_adapters"
- ✅ PEFT config sanitization works: "Sanitized adapter_config.json"
- ❌ **No inference logs**: Only ping requests visible, no actual inference processing

## Next Steps
1. **Investigate model architecture**: Check if phi-2 + LoRA combination is problematic
2. **Review inference code**: Look for infinite loops or blocking operations
3. **Test base model**: Try without LoRA adapters to isolate the issue
4. **Check GPU utilization**: Monitor CloudWatch metrics for GPU usage
5. **Consider alternative approach**: Use different model or deployment strategy

## Key Insights
- Endpoint deployment process works correctly
- Model loading is successful (no more syntax/import errors)
- PEFT adapter configuration requires careful handling
- Instance size upgrade didn't resolve the timeout issue
- **Critical finding**: No inference processing logs suggest the issue is in the inference code itself
- SageMaker inference code needs proper error handling and timeout management

## Files Created
- `test_phi2_endpoint.py`: Python test script for endpoint
- `simple_test.py`: Extended timeout test script
- `phi2_endpoint_test_results.md`: This documentation
- Updated `inference.py`: Fixed syntax and PEFT issues

## Current Status Summary
- **Endpoint**: InService ✅
- **Model Loading**: Successful ✅
- **Code Issues**: All Fixed ✅
- **Instance Size**: Upgraded to ml.g5.4xlarge ✅
- **Inference**: **Still Timing Out** ❌
- **Root Cause**: **Unknown - requires deeper investigation** ❌
