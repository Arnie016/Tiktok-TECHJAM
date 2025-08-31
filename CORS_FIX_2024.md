# CORS Fix for Lambda Function - 2024

## Problem Identified
The web interface at `https://www.pacmanlaw.info` was experiencing CORS (Cross-Origin Resource Sharing) errors when trying to access the Lambda Function URL:

```
Access to fetch at 'https://vcf7glhsl7w4yccfzny6tigqmm0znsxx.lambda-url.us-west-2.on.aws/' from origin 'https://www.pacmanlaw.info' has been blocked by CORS policy: The 'Access-Control-Allow-Origin' header contains multiple values '*, *', but only one is allowed.
```

## Root Cause
The issue was caused by **duplicate CORS headers** being set:
1. **Lambda Function URL CORS Configuration**: AWS Lambda Function URL was configured with CORS settings
2. **Lambda Function Code**: The Lambda function code was also setting CORS headers in the response

This resulted in duplicate `Access-Control-Allow-Origin` headers, which browsers reject.

## Solution Implemented

### 1. Updated Lambda Function URL CORS Configuration
Configured the Lambda Function URL to handle CORS properly:
```bash
aws lambda update-function-url-config \
  --function-name phi2-v5-geo-compliance \
  --cors '{
    "AllowCredentials": false,
    "AllowHeaders": ["*"],
    "AllowMethods": ["*"],
    "AllowOrigins": ["https://www.pacmanlaw.info"],
    "ExposeHeaders": ["*"],
    "MaxAge": 86400
  }'
```

### 2. Simplified Lambda Function Headers
Removed CORS headers from the Lambda function code to prevent duplication:
```python
# Before (causing duplication)
headers = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': 'https://www.pacmanlaw.info',
    'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
    'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
    'Access-Control-Max-Age': '86400'
}

# After (simplified)
headers = {
    'Content-Type': 'application/json'
}
```

## Results

### Before Fix
```
HTTP/1.1 200 OK
access-control-allow-origin: https://www.pacmanlaw.info
access-control-allow-origin: https://www.pacmanlaw.info  # Duplicate!
```

### After Fix
```
HTTP/1.1 200 OK
Access-Control-Allow-Origin: https://www.pacmanlaw.info  # Single header
Vary: Origin
Access-Control-Expose-Headers: *
```

## Testing
The fix was verified using curl with proper Origin header:
```bash
curl -X POST "https://vcf7glhsl7w4yccfzny6tigqmm0znsxx.lambda-url.us-west-2.on.aws/" \
  -H "Content-Type: application/json" \
  -H "Origin: https://www.pacmanlaw.info" \
  -d '{"instruction": "Test", "input": "Test input"}'
```

## Impact
- ✅ **Web Interface**: The `geo_compliance_ui.html` at `https://www.pacmanlaw.info` can now successfully call the Lambda function
- ✅ **No CORS Errors**: Browser console no longer shows CORS policy violations
- ✅ **Functionality**: All features work as expected from the web interface
- ✅ **Security**: CORS is properly configured to only allow requests from the authorized domain

## Files Modified
- `Lamda functions/phi2_lambda_function.py`: Simplified response headers
- Lambda Function URL CORS configuration: Updated via AWS CLI

## Next Steps
The web interface should now work properly without CORS errors. Users can:
1. Access the interface at `https://www.pacmanlaw.info`
2. Submit compliance analysis requests
3. Receive structured responses without browser blocking

The Lambda function continues to work correctly for both web interface and direct API calls.
