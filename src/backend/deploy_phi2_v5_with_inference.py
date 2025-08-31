#!/usr/bin/env python3
"""
Deploy Phi-2 v5 model with custom inference script for proper LoRA handling
"""

import boto3
import json
import time
import tarfile
import os
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

class Phi2V5InferenceDeployer:
    def __init__(self, profile_name='bedrock-561', region='us-west-2'):
        self.session = boto3.Session(profile_name=profile_name, region_name=region)
        self.sagemaker = self.session.client('sagemaker')
        self.s3 = self.session.client('s3')
        self.region = region
        
        # Configuration
        self.config = {
            "role_arn": "arn:aws:iam::561947681110:role/SageMakerExecutionRole",
            "bucket": "sagemaker-us-west-2-561947681110",
            "base_model": "microsoft/phi-2",
            "endpoint_instance": "ml.g5.4xlarge",  # Your working instance type
            "training_job_name": "phi2-retrain-v5-20250831-010009",  # The completed job
            "model_artifacts": "s3://sagemaker-us-west-2-561947681110/phi2-retrain-v5-output/phi2-retrain-v5-20250831-010009/output/model.tar.gz"
        }
        
        logger.info(f"🔧 Initialized deployer for region {region}")

    def create_inference_package(self):
        """Create a tarball with model artifacts + custom inference script"""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        temp_dir = f"/tmp/phi2_v5_model_{timestamp}"
        tarball_path = f"/tmp/phi2_v5_model_{timestamp}.tar.gz"
        
        logger.info("📦 Creating inference package with custom script...")
        
        try:
            # Create temporary directory
            os.makedirs(temp_dir, exist_ok=True)
            
            # Download original model artifacts
            logger.info("⬇️ Downloading original model artifacts...")
            original_model_path = f"{temp_dir}/original_model.tar.gz"
            bucket = self.config['bucket']
            key = self.config['model_artifacts'].replace(f"s3://{bucket}/", "")
            
            self.s3.download_file(bucket, key, original_model_path)
            
            # Extract original model
            logger.info("📂 Extracting model artifacts...")
            with tarfile.open(original_model_path, 'r:gz') as tar:
                tar.extractall(temp_dir)
            
            # Create code directory and add custom inference script
            logger.info("📝 Adding custom inference script...")
            import shutil
            code_dir = f"{temp_dir}/code"
            os.makedirs(code_dir, exist_ok=True)
            
            shutil.copy('/Users/hema/Desktop/bedrock/inference_v5.py', f"{code_dir}/inference.py")
            
            # Create requirements.txt for inference dependencies
            requirements_content = """torch>=1.9.0
transformers>=4.21.0
peft>=0.4.0
accelerate>=0.20.0
"""
            with open(f"{code_dir}/requirements.txt", 'w') as f:
                f.write(requirements_content)
            
            # Create new tarball with everything
            logger.info("🗜️ Creating new model package...")
            with tarfile.open(tarball_path, 'w:gz') as tar:
                # Add all files from temp_dir, but skip the original tarball
                for item in os.listdir(temp_dir):
                    if item != 'original_model.tar.gz':
                        item_path = os.path.join(temp_dir, item)
                        tar.add(item_path, arcname=item)
            
            # Upload to S3
            upload_key = f"phi2-v5-inference-models/model-{timestamp}.tar.gz"
            upload_s3_uri = f"s3://{bucket}/{upload_key}"
            
            logger.info(f"⬆️ Uploading to {upload_s3_uri}...")
            self.s3.upload_file(tarball_path, bucket, upload_key)
            
            # Cleanup
            shutil.rmtree(temp_dir)
            os.remove(tarball_path)
            
            logger.info("✅ Inference package created successfully")
            return upload_s3_uri
            
        except Exception as e:
            logger.error(f"❌ Failed to create inference package: {e}")
            # Cleanup on error
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            if os.path.exists(tarball_path):
                os.remove(tarball_path)
            return None

    def create_model_with_inference(self, model_data_url):
        """Create SageMaker model with custom inference"""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        model_name = f"phi2-v5-inference-{timestamp}"
        
        logger.info(f"🤖 Creating model with inference: {model_name}")
        
        try:
            self.sagemaker.create_model(
                ModelName=model_name,
                PrimaryContainer={
                    'Image': '763104351884.dkr.ecr.us-west-2.amazonaws.com/huggingface-pytorch-inference:2.1.0-transformers4.37.0-gpu-py310-cu118-ubuntu20.04',
                    'ModelDataUrl': model_data_url,
                    'Environment': {
                        'BASE_MODEL_ID': self.config['base_model'],
                        'HF_HOME': '/tmp/hf_home',
                        'TRANSFORMERS_CACHE': '/tmp/transformers_cache',
                        'SAGEMAKER_PROGRAM': 'inference.py',  # Use our custom script
                        'SAGEMAKER_SUBMIT_DIRECTORY': '/opt/ml/code',
                        'MMS_DEFAULT_RESPONSE_TIMEOUT': '900'  # 15 minutes timeout
                    }
                },
                ExecutionRoleArn=self.config['role_arn']
            )
            logger.info("✅ Model created successfully")
            return model_name
            
        except Exception as e:
            logger.error(f"❌ Failed to create model: {e}")
            return None

    def create_endpoint_config(self, model_name):
        """Create endpoint configuration"""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        config_name = f"phi2-v5-inference-config-{timestamp}"
        
        logger.info(f"⚙️ Creating endpoint config: {config_name}")
        
        try:
            self.sagemaker.create_endpoint_config(
                EndpointConfigName=config_name,
                ProductionVariants=[
                    {
                        'VariantName': 'primary',
                        'ModelName': model_name,
                        'InitialInstanceCount': 1,
                        'InstanceType': self.config['endpoint_instance'],
                        'InitialVariantWeight': 1.0
                    }
                ]
            )
            logger.info("✅ Endpoint config created successfully")
            return config_name
            
        except Exception as e:
            logger.error(f"❌ Failed to create endpoint config: {e}")
            return None

    def create_endpoint(self, config_name):
        """Create new endpoint"""
        endpoint_name = "phi2-v5-inference"
        
        logger.info(f"🚀 Creating endpoint: {endpoint_name}")
        
        try:
            # Delete existing endpoints to free up quota
            for old_endpoint in ["phi2-v5-inference", "gold-phi2", "phi2-v5-geo-compliance"]:
                try:
                    self.sagemaker.describe_endpoint(EndpointName=old_endpoint)
                    logger.info(f"🗑️ Deleting existing endpoint: {old_endpoint}")
                    self.sagemaker.delete_endpoint(EndpointName=old_endpoint)
                    time.sleep(10)  # Brief wait between deletions
                except:
                    pass  # Endpoint doesn't exist
            
            # Wait for all deletions to complete
            logger.info("⏳ Waiting for endpoint deletions to complete...")
            time.sleep(60)
            
            self.sagemaker.create_endpoint(
                EndpointName=endpoint_name,
                EndpointConfigName=config_name
            )
            logger.info("✅ Endpoint creation initiated")
            return endpoint_name
            
        except Exception as e:
            logger.error(f"❌ Failed to create endpoint: {e}")
            return None

    def wait_for_endpoint(self, endpoint_name):
        """Wait for endpoint to be InService"""
        logger.info(f"⏳ Waiting for endpoint {endpoint_name} to be ready...")
        
        while True:
            try:
                response = self.sagemaker.describe_endpoint(EndpointName=endpoint_name)
                status = response['EndpointStatus']
                
                logger.info(f"📊 Endpoint status: {status}")
                
                if status == 'InService':
                    logger.info("✅ Endpoint is ready!")
                    return True
                elif status == 'Failed':
                    logger.error(f"❌ Endpoint creation failed: {response.get('FailureReason', 'Unknown')}")
                    return False
                else:
                    time.sleep(30)
                    
            except Exception as e:
                logger.error(f"❌ Error checking endpoint: {e}")
                return False

    def deploy_full_pipeline(self):
        """Deploy complete pipeline with custom inference"""
        logger.info("🚀 Starting Phi-2 v5 deployment with custom inference...")
        logger.info("=" * 70)
        
        # Step 1: Create inference package
        model_data_url = self.create_inference_package()
        if not model_data_url:
            return False
        
        # Step 2: Create model
        model_name = self.create_model_with_inference(model_data_url)
        if not model_name:
            return False
        
        # Step 3: Create endpoint config
        config_name = self.create_endpoint_config(model_name)
        if not config_name:
            return False
        
        # Step 4: Create endpoint
        endpoint_name = self.create_endpoint(config_name)
        if not endpoint_name:
            return False
        
        # Step 5: Wait for endpoint
        if not self.wait_for_endpoint(endpoint_name):
            return False
        
        logger.info("🎉 Deployment completed successfully!")
        logger.info(f"🔗 Endpoint name: {endpoint_name}")
        logger.info(f"📊 Model data: {model_data_url}")
        logger.info(f"🔧 Instance type: {self.config['endpoint_instance']}")
        logger.info("🧪 Ready for testing with custom inference logic!")
        
        return True

def main():
    """Main function"""
    deployer = Phi2V5InferenceDeployer()
    
    logger.info("🎯 Phi-2 v5 Deployment with Custom Inference")
    logger.info("Includes LoRA adapters + optimized inference script")
    logger.info("=" * 70)
    
    success = deployer.deploy_full_pipeline()
    
    if success:
        logger.info("\n✅ SUCCESS: Phi-2 v5 with custom inference deployed!")
        logger.info("🧪 Test endpoint: phi2-v5-inference")
        logger.info("🎯 Should fix memory issues and LoRA loading problems")
    else:
        logger.error("\n❌ FAILED: Deployment failed")

if __name__ == "__main__":
    main()
