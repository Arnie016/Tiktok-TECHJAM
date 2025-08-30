# AWS Credentials Guide for Account 561947681110

## 🔍 **Where to Find Your AWS Credentials**

### **Option 1: AWS Console (Recommended)**
1. **Go to AWS Console**: https://console.aws.amazon.com/
2. **Sign in** to account `561947681110`
3. **Navigate to IAM**:
   - Go to Services → IAM
   - Click on "Users" in the left sidebar
   - Find your username
4. **Create Access Keys**:
   - Click on your username
   - Go to "Security credentials" tab
   - Click "Create access key"
   - Choose "Command Line Interface (CLI)"
   - Download the CSV file with your credentials

### **Option 2: AWS CLI Profiles**
Check if you already have profiles configured:
```bash
# List all AWS profiles
aws configure list-profiles

# Check specific profile
aws configure list --profile account-561947681110
```

### **Option 3: Environment Variables**
Check if credentials are already set:
```bash
# Check current environment
echo $AWS_ACCESS_KEY_ID
echo $AWS_SECRET_ACCESS_KEY
echo $AWS_SESSION_TOKEN
```

### **Option 4: AWS SSO (Single Sign-On)**
If your organization uses AWS SSO:
```bash
# List available profiles
aws configure list-profiles

# Login to SSO
aws sso login --profile your-sso-profile

# Use the profile
export AWS_PROFILE=your-sso-profile
```

## 🚀 **Quick Setup Commands**

### **Method 1: AWS Configure**
```bash
# Configure credentials interactively
aws configure --profile account-561947681110

# You'll be prompted for:
# AWS Access Key ID: [Enter your access key]
# AWS Secret Access Key: [Enter your secret key]
# Default region name: us-west-2
# Default output format: json
```

### **Method 2: Environment Variables**
```bash
# Set credentials directly
export AWS_ACCESS_KEY_ID=AKIA...your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
export AWS_SESSION_TOKEN=your-session-token  # Only if using temporary credentials
export AWS_DEFAULT_REGION=us-west-2
```

### **Method 3: AWS Credentials File**
Edit `~/.aws/credentials`:
```ini
[account-561947681110]
aws_access_key_id = AKIA...your-access-key
aws_secret_access_key = your-secret-key
aws_session_token = your-session-token  # Only if using temporary credentials
```

Edit `~/.aws/config`:
```ini
[profile account-561947681110]
region = us-west-2
output = json
```

## 🔧 **Verify Your Setup**

### **Check Current Account**
```bash
# Verify you're using the correct account
aws sts get-caller-identity --profile account-561947681110

# Should show:
# {
#   "UserId": "...",
#   "Account": "561947681110",
#   "Arn": "arn:aws:iam::561947681110:user/..."
# }
```

### **Test SageMaker Access**
```bash
# Test if you can access SageMaker
aws sagemaker list-training-jobs --profile account-561947681110 --region us-west-2
```

## 🎯 **Common Sources for Credentials**

### **1. AWS Console**
- **IAM Users**: Your personal access keys
- **IAM Roles**: Temporary credentials for EC2/ECS
- **Federated Access**: SAML/SSO credentials

### **2. AWS Organizations**
- **Cross-account roles**: If you're accessing from another account
- **SSO profiles**: If using AWS Single Sign-On

### **3. Development Tools**
- **AWS CLI**: Already configured profiles
- **AWS SDK**: Environment variables or config files
- **CloudFormation**: IAM roles for deployment

### **4. CI/CD Systems**
- **GitHub Actions**: Repository secrets
- **Jenkins**: Credential stores
- **AWS CodePipeline**: Service roles

## 🚨 **Security Best Practices**

### **✅ Do's**
- Use IAM users with minimal required permissions
- Rotate access keys regularly
- Use temporary credentials when possible
- Store credentials securely (not in code)

### **❌ Don'ts**
- Don't commit credentials to version control
- Don't use root account credentials
- Don't share credentials between users
- Don't use long-lived credentials for automation

## 🔍 **Troubleshooting**

### **Permission Denied**
```bash
# Check if credentials are valid
aws sts get-caller-identity

# Check SageMaker permissions
aws sagemaker list-training-jobs --region us-west-2
```

### **Wrong Account**
```bash
# Switch to correct profile
export AWS_PROFILE=account-561947681110

# Or use profile in commands
aws sagemaker list-training-jobs --profile account-561947681110
```

### **Expired Credentials**
```bash
# For SSO, refresh login
aws sso login --profile your-sso-profile

# For temporary credentials, get new ones
aws sts get-session-token --profile your-profile
```

## 🎯 **Next Steps**

1. **Find your credentials** using one of the methods above
2. **Configure them** using AWS CLI or environment variables
3. **Verify access** to account `561947681110`
4. **Run the deployment script**:
   ```bash
   cd sagemaker-finetune
   python switch_and_deploy.py
   ```

## 💡 **Need Help?**

If you can't find your credentials:
1. **Contact your AWS administrator**
2. **Check your organization's AWS documentation**
3. **Look for existing AWS CLI configurations**
4. **Check if you have AWS SSO access**



