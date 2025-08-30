# AWS Setup Guide for Geo-Compliance Model Deployment

## 🔧 **Current Issues**

1. **AWS Account**: Using account `561947681110` as configured
2. **IAM Permissions**: Your user lacks SageMaker permissions
3. **Model Artifacts**: Need to find your actual fine-tuned model

## 🚀 **Quick Fix Steps**

### **Step 1: Configure AWS Credentials**
```bash
# Check current AWS identity
aws sts get-caller-identity

# Configure AWS credentials if needed
aws configure
```

### **Step 2: Add SageMaker Permissions**
You need to add these permissions to your IAM user:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "sagemaker:CreateEndpoint",
                "sagemaker:CreateEndpointConfig",
                "sagemaker:CreateModel",
                "sagemaker:DescribeEndpoint",
                "sagemaker:DescribeEndpointConfig",
                "sagemaker:DescribeModel",
                "sagemaker:ListEndpoints",
                "sagemaker:ListModels",
                "sagemaker:ListTrainingJobs",
                "sagemaker:InvokeEndpoint"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "iam:PassRole"
            ],
            "Resource": "arn:aws:iam::561947681110:role/SageMakerExecutionRole"
        }
    ]
}
```

### **Step 3: Create SageMaker Execution Role**
If the role doesn't exist, create it:

```bash
# Create the SageMaker execution role
aws iam create-role \
    --role-name SageMakerExecutionRole \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "sagemaker.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }'

# Attach necessary policies
aws iam attach-role-policy \
    --role-name SageMakerExecutionRole \
    --policy-arn arn:aws:iam::aws:policy/AmazonSageMakerFullAccess

aws iam attach-role-policy \
    --role-name SageMakerExecutionRole \
    --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
```

## 🎯 **Deployment Options**

### **Option A: Use Fixed Deployment Script**
```bash
cd sagemaker-finetune
python deploy_fixed.py
```

### **Option B: Manual Deployment**
```bash
# 1. Find your training job
aws sagemaker list-training-jobs --status-equals Completed

# 2. Get model artifacts path
# Look for: s3://arnav-finetune-1756054916/output/[job-name]/output/model.tar.gz

# 3. Deploy using AWS CLI
aws sagemaker create-model \
    --model-name geo-compliance-model \
    --primary-container '{
        "Image": "763104351884.dkr.ecr.us-west-2.amazonaws.com/huggingface-pytorch-training:2.1-transformers4.37.0-gpu-py310-cu118-ubuntu20.04",
        "ModelDataUrl": "s3://arnav-finetune-1756054916/output/[your-job-name]/output/model.tar.gz"
    }' \
    --execution-role-arn arn:aws:iam::561947681110:role/SageMakerExecutionRole

# 4. Create endpoint configuration
aws sagemaker create-endpoint-config \
    --endpoint-config-name geo-compliance-config \
    --production-variants '[
        {
            "VariantName": "AllTraffic",
            "ModelName": "geo-compliance-model",
            "InitialInstanceCount": 1,
            "InstanceType": "ml.g5.xlarge"
        }
    ]'

# 5. Create endpoint
aws sagemaker create-endpoint \
    --endpoint-name geo-compliance-model \
    --endpoint-config-name geo-compliance-config
```

## 🔍 **Troubleshooting**

### **Permission Denied Errors**
- Ensure your IAM user has SageMaker permissions
- Check that the SageMaker execution role exists and has proper policies
- Verify you're using the correct AWS account

### **Model Artifacts Not Found**
- Check if your training job completed successfully
- Verify the S3 bucket path is correct
- Ensure the model.tar.gz file exists in the expected location

### **Endpoint Creation Fails**
- Check SageMaker service quotas in your region
- Ensure you have sufficient IAM permissions
- Verify the model container image is compatible

## 📊 **Testing Your Deployment**

Once deployed, test with:

```bash
# Test the endpoint
python test_endpoint.py

# Or use AWS CLI
aws sagemaker-runtime invoke-endpoint \
    --endpoint-name geo-compliance-model \
    --content-type application/json \
    --body '{
        "inputs": "### Instruction:\nAnalyze the following software feature...\n\n### Response:\n",
        "parameters": {
            "max_new_tokens": 256,
            "temperature": 0.1,
            "do_sample": true
        }
    }' \
    response.json
```

## 💡 **Alternative: Use AWS Console**

If CLI deployment is challenging:
1. Go to AWS SageMaker Console
2. Navigate to "Models" → "Create model"
3. Upload your model artifacts
4. Create endpoint configuration
5. Deploy endpoint

## 🎯 **Next Steps**

1. **Fix permissions** using the steps above
2. **Run the fixed deployment script**
3. **Test the endpoint** with sample compliance queries
4. **Integrate** with your application for real-time analysis
