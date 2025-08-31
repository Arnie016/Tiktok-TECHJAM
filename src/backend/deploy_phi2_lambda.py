#!/usr/bin/env python3
"""
Deploy Phi-2 v5 Lambda function with Function URL for easy testing
"""

import boto3
import json
import time
import zipfile
import os
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

class Phi2LambdaDeployer:
    def __init__(self, profile_name='bedrock-561', region='us-west-2'):
        self.session = boto3.Session(profile_name=profile_name, region_name=region)
        self.iam = self.session.client('iam')
        self.lambda_client = self.session.client('lambda')
        self.region = region
        self.account_id = "561947681110"
        
        # Configuration
        self.config = {
            "function_name": "phi2-v5-geo-compliance",
            "role_name": "phi2-v5-lambda-role",
            "description": "Phi-2 v5 model for geo-compliance analysis via SageMaker",
            "timeout": 60,
            "memory_size": 256,
            "endpoint_name": "phi2-v5-inference"
        }
        
        logger.info(f"🔧 Initialized Lambda deployer for region {region}")

    def create_iam_role(self):
        """Create IAM role for Lambda function"""
        role_name = self.config['role_name']
        
        logger.info(f"🔐 Creating IAM role: {role_name}")
        
        try:
            # Try to get existing role
            try:
                response = self.iam.get_role(RoleName=role_name)
                logger.info("✅ IAM role already exists")
                return response['Role']['Arn']
            except self.iam.exceptions.NoSuchEntityException:
                pass
            
            # Read trust policy
            with open('/Users/hema/Desktop/bedrock/phi2_lambda_trust_policy.json', 'r') as f:
                trust_policy = f.read()
            
            # Create role
            response = self.iam.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=trust_policy,
                Description="Role for Phi-2 v5 Lambda function to access SageMaker endpoint"
            )
            
            role_arn = response['Role']['Arn']
            logger.info(f"✅ Created IAM role: {role_arn}")
            
            # Read permissions policy
            with open('/Users/hema/Desktop/bedrock/phi2_lambda_role_policy.json', 'r') as f:
                permissions_policy = f.read()
            
            # Attach permissions policy
            self.iam.put_role_policy(
                RoleName=role_name,
                PolicyName='Phi2SageMakerInvokePolicy',
                PolicyDocument=permissions_policy
            )
            
            # Attach basic Lambda execution policy
            self.iam.attach_role_policy(
                RoleName=role_name,
                PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
            )
            
            logger.info("✅ Attached policies to role")
            
            # Wait for role propagation
            logger.info("⏳ Waiting for role propagation...")
            time.sleep(15)
            
            return role_arn
            
        except Exception as e:
            logger.error(f"❌ Failed to create IAM role: {e}")
            return None

    def create_lambda_package(self):
        """Create Lambda deployment package"""
        logger.info("📦 Creating Lambda deployment package...")
        
        try:
            # Create temporary zip file
            zip_path = '/tmp/phi2_lambda.zip'
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add Lambda function code
                zipf.write('/Users/hema/Desktop/bedrock/Lamda functions/phi2_lambda_function.py', 'lambda_function.py')
            
            # Read zip file content
            with open(zip_path, 'rb') as f:
                zip_content = f.read()
            
            # Cleanup
            os.remove(zip_path)
            
            logger.info("✅ Lambda package created successfully")
            return zip_content
            
        except Exception as e:
            logger.error(f"❌ Failed to create Lambda package: {e}")
            return None

    def deploy_lambda_function(self, role_arn, zip_content):
        """Deploy Lambda function"""
        function_name = self.config['function_name']
        
        logger.info(f"🚀 Deploying Lambda function: {function_name}")
        
        try:
            # Check if function exists
            try:
                response = self.lambda_client.get_function(FunctionName=function_name)
                logger.info("🔄 Function exists, updating code...")
                
                # Update function code
                response = self.lambda_client.update_function_code(
                    FunctionName=function_name,
                    ZipFile=zip_content
                )
                
                # Update function configuration
                self.lambda_client.update_function_configuration(
                    FunctionName=function_name,
                    Role=role_arn,
                    Description=self.config['description'],
                    Timeout=self.config['timeout'],
                    MemorySize=self.config['memory_size'],
                    Environment={
                        'Variables': {
                            'ENDPOINT_NAME': self.config['endpoint_name'],
                            'REGION': self.region
                        }
                    }
                )
                
            except self.lambda_client.exceptions.ResourceNotFoundException:
                logger.info("🆕 Creating new function...")
                
                # Create new function
                response = self.lambda_client.create_function(
                    FunctionName=function_name,
                    Runtime='python3.9',
                    Role=role_arn,
                    Handler='lambda_function.lambda_handler',
                    Code={'ZipFile': zip_content},
                    Description=self.config['description'],
                    Timeout=self.config['timeout'],
                    MemorySize=self.config['memory_size'],
                    Environment={
                        'Variables': {
                            'ENDPOINT_NAME': self.config['endpoint_name'],
                            'REGION': self.region
                        }
                    }
                )
            
            function_arn = response['FunctionArn']
            logger.info(f"✅ Lambda function deployed: {function_arn}")
            
            return function_name
            
        except Exception as e:
            logger.error(f"❌ Failed to deploy Lambda function: {e}")
            return None

    def create_function_url(self, function_name):
        """Create Function URL for easy access"""
        logger.info(f"🔗 Creating Function URL for: {function_name}")
        
        try:
            # Check if Function URL already exists
            try:
                response = self.lambda_client.get_function_url_config(FunctionName=function_name)
                function_url = response['FunctionUrl']
                logger.info(f"✅ Function URL already exists: {function_url}")
                return function_url
            except self.lambda_client.exceptions.ResourceNotFoundException:
                pass
            
            # Create Function URL
            response = self.lambda_client.create_function_url_config(
                FunctionName=function_name,
                AuthType='NONE',  # Public access for testing
                Cors={
                    'AllowCredentials': False,
                    'AllowHeaders': ['*'],
                    'AllowMethods': ['*'],
                    'AllowOrigins': ['*'],
                    'MaxAge': 86400
                }
            )
            
            function_url = response['FunctionUrl']
            logger.info(f"✅ Function URL created: {function_url}")
            
            return function_url
            
        except Exception as e:
            logger.error(f"❌ Failed to create Function URL: {e}")
            return None

    def test_lambda_function(self, function_name):
        """Test the deployed Lambda function"""
        logger.info(f"🧪 Testing Lambda function: {function_name}")
        
        try:
            # Test payload
            test_payload = {
                'instruction': 'Analyse the feature artifact and decide if geo-specific compliance logic is needed. Explain why and cite the relevant regulation if any.',
                'input': '''Feature Name: EU Cookie Consent Banner
Feature Description: Display cookie consent banner for EU users accessing the website.

Law Context (structured JSON):
[{"law": "GDPR Article 7", "jurisdiction": "EU", "requirement": "Valid consent for data processing"}]'''
            }
            
            # Invoke function
            response = self.lambda_client.invoke(
                FunctionName=function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps({
                    'httpMethod': 'POST',
                    'body': json.dumps(test_payload)
                })
            )
            
            # Parse response
            response_payload = json.loads(response['Payload'].read().decode())
            
            if response_payload.get('statusCode') == 200:
                logger.info("✅ Lambda function test successful!")
                body = json.loads(response_payload.get('body', '{}'))
                if body.get('success'):
                    logger.info(f"🎯 Model response length: {len(body.get('analysis', {}).get('generated_text', ''))}")
                return True
            else:
                logger.error(f"❌ Lambda function test failed: {response_payload}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Lambda function test error: {e}")
            return False

    def deploy_full_pipeline(self):
        """Deploy complete Lambda pipeline"""
        logger.info("🚀 Starting Phi-2 v5 Lambda deployment...")
        logger.info("=" * 70)
        
        # Step 1: Create IAM role
        role_arn = self.create_iam_role()
        if not role_arn:
            return False
        
        # Step 2: Create Lambda package
        zip_content = self.create_lambda_package()
        if not zip_content:
            return False
        
        # Step 3: Deploy Lambda function
        function_name = self.deploy_lambda_function(role_arn, zip_content)
        if not function_name:
            return False
        
        # Step 4: Create Function URL
        function_url = self.create_function_url(function_name)
        if not function_url:
            return False
        
        # Step 5: Test the function
        if not self.test_lambda_function(function_name):
            logger.warning("⚠️ Function deployed but test failed")
        
        logger.info("🎉 Lambda deployment completed successfully!")
        logger.info(f"🔗 Function Name: {function_name}")
        logger.info(f"🌐 Function URL: {function_url}")
        logger.info(f"📡 SageMaker Endpoint: {self.config['endpoint_name']}")
        logger.info("🧪 Ready for testing!")
        
        return {
            'function_name': function_name,
            'function_url': function_url,
            'role_arn': role_arn,
            'endpoint_name': self.config['endpoint_name']
        }

def main():
    """Main function"""
    deployer = Phi2LambdaDeployer()
    
    logger.info("🎯 Phi-2 v5 Lambda Function Deployment")
    logger.info("Creates Function URL for easy web access to SageMaker endpoint")
    logger.info("=" * 70)
    
    result = deployer.deploy_full_pipeline()
    
    if result:
        logger.info("\n✅ SUCCESS: Phi-2 v5 Lambda function deployed!")
        logger.info("🌐 You can now test via Function URL or direct Lambda invoke")
        logger.info("🔧 CORS enabled for web browser testing")
        
        # Create test curl command
        test_curl = f'''
# Test with curl:
curl -X POST {result['function_url']} \\
  -H "Content-Type: application/json" \\
  -d '{{
    "instruction": "Analyse the feature artifact and decide if geo-specific compliance logic is needed.",
    "input": "Feature Name: Test Feature\\nFeature Description: Test description\\nLaw Context: []"
  }}'
'''
        logger.info(f"\n🧪 Test Command:{test_curl}")
        
    else:
        logger.error("\n❌ FAILED: Lambda deployment failed")

if __name__ == "__main__":
    main()
