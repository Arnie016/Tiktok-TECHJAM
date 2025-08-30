#!/usr/bin/env python3
"""
Retrain Phi-2 with existing v4 data - Simple Update Script
Uses existing infrastructure, just improves the training
"""

import boto3
import json
import time
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

class Phi2Retrainer:
    def __init__(self, profile_name='bedrock-561', region='us-west-2'):
        self.session = boto3.Session(profile_name=profile_name, region_name=region)
        self.sagemaker = self.session.client('sagemaker')
        self.region = region
        
        # Configuration - using your existing setup
        self.config = {
            "role_arn": "arn:aws:iam::561947681110:role/SageMakerExecutionRole",
            "bucket": "sagemaker-us-west-2-561947681110",
            "base_model": "microsoft/phi-2",
            "instance_type": "ml.g5.2xlarge",  # Training instance (using existing quota)
            "endpoint_instance": "ml.g5.4xlarge",  # Inference instance (your current)
            "training_data": "s3://sagemaker-us-west-2-561947681110/phi2-training-data/"
        }
        
        logger.info(f"🔧 Initialized retrainer for region {region}")
        logger.info(f"📊 Using training data: {self.config['training_data']}")

    def upload_training_data(self, job_name):
        """Upload v4 training data to S3"""
        logger.info("📤 Uploading training data to S3...")
        
        s3 = self.session.client('s3')
        
        try:
            # Upload the v4 data to the same working bucket
            s3.upload_file(
                '/Users/hema/Desktop/bedrock/sagemaker-finetune/data/train_refined_v4.jsonl',
                self.config['bucket'],
                'phi2-training-data/train_refined_v4.jsonl'
            )
            # Also upload the training script
            s3.upload_file(
                '/Users/hema/Desktop/bedrock/improved_training_script.py',
                self.config['bucket'],
                'phi2-training-data/train.py'
            )
            
            # Create and upload source directory
            import tempfile
            import tarfile
            
            with tempfile.NamedTemporaryFile(suffix='.tar.gz', delete=False) as tmp_file:
                with tarfile.open(tmp_file.name, 'w:gz') as tar:
                    tar.add('/Users/hema/Desktop/bedrock/improved_training_script.py', arcname='train.py')
                
                s3.upload_file(
                    tmp_file.name,
                    self.config['bucket'],
                    f'{job_name}/source/sourcedir.tar.gz'
                )
            logger.info("✅ Training data uploaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to upload training data: {e}")
            return False

    def create_training_job(self, job_name):
        """Create improved training job with better parameters"""
        logger.info(f"🚀 Starting training job: {job_name}")
        
        # Improved training parameters
        training_params = {
            'TrainingJobName': job_name,
            'RoleArn': self.config['role_arn'],
            'AlgorithmSpecification': {
                'TrainingImage': '763104351884.dkr.ecr.us-west-2.amazonaws.com/huggingface-pytorch-training:2.5.1-transformers4.49.0-gpu-py311-cu124-ubuntu22.04',
                'TrainingInputMode': 'File',
                'EnableSageMakerMetricsTimeSeries': True
            },
            'HyperParameters': {
                'model_id': f'"{self.config["base_model"]}"',
                'epochs': '3',
                'learning_rate': '5e-5',
                'max_seq_length': '512',
                'hf_hub_enable_hf_transfer': 'false',
                'sagemaker_container_log_level': '20',
                'sagemaker_job_name': f'"{job_name}"',
                'sagemaker_program': '"train.py"',
                'sagemaker_region': '"us-west-2"',
                'sagemaker_submit_directory': f'"s3://{self.config["bucket"]}/{job_name}/source/sourcedir.tar.gz"'
            },
            'InputDataConfig': [
                {
                    'ChannelName': 'train',
                    'DataSource': {
                        'S3DataSource': {
                            'S3DataType': 'S3Prefix',
                            'S3Uri': self.config['training_data'],
                            'S3DataDistributionType': 'FullyReplicated'
                        }
                    },
                    'CompressionType': 'None',
                    'RecordWrapperType': 'None'
                }
            ],
            'OutputDataConfig': {
                'S3OutputPath': f"s3://{self.config['bucket']}/phi2-retrain-v5-output/"
            },
            'ResourceConfig': {
                'InstanceType': self.config['instance_type'],
                'InstanceCount': 1,
                'VolumeSizeInGB': 30
            },
            'StoppingCondition': {
                'MaxRuntimeInSeconds': 3600  # 1 hour max
            },
            'Environment': {
                'HF_HOME': '/tmp/hf_home',
                'TRANSFORMERS_CACHE': '/tmp/transformers_cache',
                'HF_HUB_ENABLE_HF_TRANSFER': '0'
            }
        }
        
        try:
            response = self.sagemaker.create_training_job(**training_params)
            logger.info("✅ Training job created successfully")
            logger.info(f"📋 Job ARN: {response['TrainingJobArn']}")
            return job_name
            
        except Exception as e:
            logger.error(f"❌ Failed to create training job: {e}")
            return None

    def wait_for_training(self, job_name, check_interval=60):
        """Wait for training job to complete"""
        logger.info(f"⏳ Waiting for training job {job_name} to complete...")
        
        while True:
            try:
                response = self.sagemaker.describe_training_job(TrainingJobName=job_name)
                status = response['TrainingJobStatus']
                
                logger.info(f"📊 Training status: {status}")
                
                if status == 'Completed':
                    logger.info("✅ Training completed successfully!")
                    return response['ModelArtifacts']['S3ModelArtifacts']
                    
                elif status == 'Failed':
                    logger.error(f"❌ Training failed: {response.get('FailureReason', 'Unknown')}")
                    return None
                    
                elif status in ['InProgress', 'Starting']:
                    time.sleep(check_interval)
                    continue
                    
                else:
                    logger.warning(f"⚠️ Unexpected status: {status}")
                    time.sleep(check_interval)
                    
            except Exception as e:
                logger.error(f"❌ Error checking training status: {e}")
                return None

    def update_endpoint(self, model_artifacts_uri):
        """Update existing endpoint with new model"""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        model_name = f"phi2-retrained-v5-{timestamp}"
        config_name = f"phi2-retrained-config-{timestamp}"
        
        logger.info(f"🔄 Updating endpoint with new model: {model_name}")
        
        try:
            # Create new model
            self.sagemaker.create_model(
                ModelName=model_name,
                PrimaryContainer={
                    'Image': '763104351884.dkr.ecr.us-west-2.amazonaws.com/huggingface-pytorch-inference:2.1.0-transformers4.37.0-gpu-py310-cu118-ubuntu20.04',
                    'ModelDataUrl': model_artifacts_uri,
                    'Environment': {
                        'BASE_MODEL_ID': self.config['base_model'],
                        'HF_HOME': '/tmp/hf_home',
                        'TRANSFORMERS_CACHE': '/tmp/transformers_cache',
                        'MODEL_ARTIFACT_S3': model_artifacts_uri
                    }
                },
                ExecutionRoleArn=self.config['role_arn']
            )
            logger.info("✅ Model created")
            
            # Create new endpoint config
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
            logger.info("✅ Endpoint config created")
            
            # Update existing endpoint
            self.sagemaker.update_endpoint(
                EndpointName='phi-2',  # Your existing endpoint
                EndpointConfigName=config_name
            )
            logger.info("✅ Endpoint update initiated")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update endpoint: {e}")
            return False

    def wait_for_endpoint_update(self, endpoint_name='phi-2'):
        """Wait for endpoint update to complete"""
        logger.info("⏳ Waiting for endpoint update to complete...")
        
        while True:
            try:
                response = self.sagemaker.describe_endpoint(EndpointName=endpoint_name)
                status = response['EndpointStatus']
                
                logger.info(f"📊 Endpoint status: {status}")
                
                if status == 'InService':
                    logger.info("✅ Endpoint is ready!")
                    return True
                elif status == 'Failed':
                    logger.error("❌ Endpoint update failed")
                    return False
                else:
                    time.sleep(30)
                    
            except Exception as e:
                logger.error(f"❌ Error checking endpoint: {e}")
                return False

    def run_full_retrain(self):
        """Run complete retraining process"""
        logger.info("🚀 Starting Phi-2 retraining process...")
        logger.info("=" * 60)
        
        # Step 1: Generate job name
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        job_name = f"phi2-retrain-v5-{timestamp}"
        
        # Step 2: Upload training data
        if not self.upload_training_data(job_name):
            return False
        
        # Step 3: Start training
        if not self.create_training_job(job_name):
            return False
        
        # Step 3: Wait for training
        model_artifacts = self.wait_for_training(job_name)
        if not model_artifacts:
            return False
        
        # Step 4: Update endpoint
        if not self.update_endpoint(model_artifacts):
            return False
        
        # Step 5: Wait for endpoint
        if not self.wait_for_endpoint_update():
            return False
        
        logger.info("🎉 Retraining completed successfully!")
        logger.info(f"📊 Model artifacts: {model_artifacts}")
        logger.info("🔗 Endpoint 'phi-2' has been updated with the new model")
        
        return True

def main():
    """Main function"""
    retrainer = Phi2Retrainer()
    
    logger.info("🎯 Phi-2 Retraining with v4 Data")
    logger.info("Using existing infrastructure - just updating the model")
    logger.info("=" * 60)
    
    success = retrainer.run_full_retrain()
    
    if success:
        logger.info("\n✅ SUCCESS: Phi-2 has been retrained and deployed!")
        logger.info("🧪 Run your evaluation scripts to test the improvements")
    else:
        logger.error("\n❌ FAILED: Retraining process failed")

if __name__ == "__main__":
    main()
