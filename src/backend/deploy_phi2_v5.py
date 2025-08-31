#!/usr/bin/env python3
"""
Deploy the newly trained Phi-2 v5 model as a fresh endpoint
"""

import boto3
import json
import time
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

class Phi2V5Deployer:
    def __init__(self, profile_name='bedrock-561', region='us-west-2'):
        self.session = boto3.Session(profile_name=profile_name, region_name=region)
        self.sagemaker = self.session.client('sagemaker')
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

    def create_model(self):
        """Create SageMaker model from training artifacts"""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        model_name = f"phi2-v5-model-{timestamp}"
        
        logger.info(f"🤖 Creating model: {model_name}")
        
        try:
            self.sagemaker.create_model(
                ModelName=model_name,
                PrimaryContainer={
                    'Image': '763104351884.dkr.ecr.us-west-2.amazonaws.com/huggingface-pytorch-inference:2.1.0-transformers4.37.0-gpu-py310-cu118-ubuntu20.04',
                    'ModelDataUrl': self.config['model_artifacts'],
                    'Environment': {
                        'HF_TASK': 'text-generation',  # CRITICAL: Required by HF inference toolkit
                        'BASE_MODEL_ID': self.config['base_model'],
                        'HF_HOME': '/tmp/hf_home',
                        'TRANSFORMERS_CACHE': '/tmp/transformers_cache',
                        'MODEL_ARTIFACT_S3': self.config['model_artifacts']
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
        config_name = f"phi2-v5-config-{timestamp}"
        
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
        endpoint_name = "phi2-v5-geo-compliance"
        
        logger.info(f"🚀 Creating endpoint: {endpoint_name}")
        
        try:
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
        """Deploy complete pipeline"""
        logger.info("🚀 Starting Phi-2 v5 deployment...")
        logger.info("=" * 60)
        
        # Step 1: Create model
        model_name = self.create_model()
        if not model_name:
            return False
        
        # Step 2: Create endpoint config
        config_name = self.create_endpoint_config(model_name)
        if not config_name:
            return False
        
        # Step 3: Create endpoint
        endpoint_name = self.create_endpoint(config_name)
        if not endpoint_name:
            return False
        
        # Step 4: Wait for endpoint
        if not self.wait_for_endpoint(endpoint_name):
            return False
        
        logger.info("🎉 Deployment completed successfully!")
        logger.info(f"🔗 Endpoint name: {endpoint_name}")
        logger.info(f"📊 Model artifacts: {self.config['model_artifacts']}")
        logger.info(f"🔧 Instance type: {self.config['endpoint_instance']}")
        
        return True

def main():
    """Main function"""
    deployer = Phi2V5Deployer()
    
    logger.info("🎯 Phi-2 v5 Model Deployment")
    logger.info("Trained on 1441 examples with improved LoRA configuration")
    logger.info("=" * 60)
    
    success = deployer.deploy_full_pipeline()
    
    if success:
        logger.info("\n✅ SUCCESS: Phi-2 v5 model deployed successfully!")
        logger.info("🧪 You can now test the improved model")
        logger.info("🔗 Endpoint: phi2-v5-geo-compliance")
    else:
        logger.error("\n❌ FAILED: Deployment failed")

if __name__ == "__main__":
    main()
