#!/usr/bin/env python3
"""
Launch Qwen-1.5-7B Training Job
=================================
Training script for geo-compliance analysis with Qwen model on SageMaker.
"""

import argparse
import logging
import os
from datetime import datetime

import boto3
import sagemaker
from botocore.exceptions import BotoCoreError, NoCredentialsError
from sagemaker.huggingface import HuggingFace

# ------------------------------
# Configuration Defaults
# ------------------------------
DEFAULT_MODEL_ID = "Qwen/Qwen1.5-7B-Chat"
DEFAULT_ROLE_ARN = "arn:aws:iam::561947681110:role/SageMakerExecutionRole"
DEFAULT_REGION = "us-west-2"
DEFAULT_BUCKET = "arnav-finetune-1756054916"
DEFAULT_INSTANCE = "ml.g5.4xlarge"

# Default Hyperparameters (HF Trainer expects lowercase keys)
DEFAULT_HYPERPARAMS = {
    "epochs": 3,
    "learning_rate": 5e-5,
    "max_seq_length": 1024,
    "model_id": DEFAULT_MODEL_ID,
    "hf_hub_enable_hf_transfer": False,
}


# ------------------------------
# Helpers
# ------------------------------
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )


def get_aws_session(account_id="561947681110"):
    """Return a boto3 session for the given account_id if available."""
    for profile in boto3.Session().available_profiles:
        try:
            session = boto3.Session(profile_name=profile)
            identity = session.client("sts").get_caller_identity()
            if identity.get("Account") == account_id:
                return session
        except (BotoCoreError, NoCredentialsError):
            continue
    logging.error("No valid AWS session found for account %s", account_id)
    return None


# ------------------------------
# Main Logic
# ------------------------------
def verify_hf_token_access(model_id):
    """Verify HF token has access to the specified model"""
    hf_token = os.getenv("HF_TOKEN")
    if not hf_token:
        raise ValueError("HF_TOKEN environment variable not found. Please set it before running.")
    
    logging.info(f"🔑 Verifying access to {model_id}...")
    
    # Try using requests first (no transformers dependency)
    try:
        import requests
        headers = {"Authorization": f"Bearer {hf_token}"}
        url = f"https://huggingface.co/api/models/{model_id}"
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            logging.info(f"✅ SUCCESS: You have access to {model_id}")
            return True
        elif response.status_code == 401:
            logging.error(f"❌ FAILED: Unauthorized - token invalid")
            return False
        elif response.status_code == 403:
            logging.error(f"❌ FAILED: Forbidden - model requires special access")
            return False
        else:
            logging.error(f"❌ FAILED: HTTP {response.status_code}")
            return False
            
    except ImportError:
        logging.warning("⚠️ requests not available, skipping verification")
        return True
    except Exception as e:
        logging.warning(f"⚠️ Could not verify access: {str(e)}")
        logging.info("💡 Proceeding anyway - verification will happen during training")
        return True

def main(args):
    """Main function to launch training job"""
    
    # Configuration
    MODEL_ID = "microsoft/phi-2"  # Phi-2 - with tensor fixes applied
    JOB_NAME = f"phi2-fixed-{datetime.now().strftime('%H%M')}"  # Updated job name
    INSTANCE_TYPE = "ml.g5.2xlarge"  # Perfect for Phi-2
    
    setup_logging()

    # Verify HF token access
    logging.info(f"🔑 Verifying access to {MODEL_ID}...")
    if not verify_hf_token_access(MODEL_ID):
        raise RuntimeError(f"Cannot access model {MODEL_ID}. Check your HF token permissions.")

    s3_train_path = f"s3://{args.bucket}/data/train_refined_v2.jsonl"
    s3_output_path = f"s3://{args.bucket}/output/{JOB_NAME}"

    logging.info("🚀 Launching training job")
    logging.info("Model: %s", MODEL_ID)
    logging.info("Job Name: %s", JOB_NAME)
    logging.info("Instance: %s", INSTANCE_TYPE)
    logging.info("Training Data: %s", s3_train_path)

    session = get_aws_session()
    if not session:
        raise RuntimeError("AWS session not found. Check credentials/profiles.")

    sm_session = sagemaker.Session(boto_session=session)

    # Get HF token
    hf_token = os.getenv("HF_TOKEN")
    if not hf_token:
        raise ValueError("HF_TOKEN environment variable not found. Please set it before running.")

    # Create estimator
    estimator = HuggingFace(
        entry_point="train_qwen.py",
        source_dir="scripts",
        instance_type=INSTANCE_TYPE,
        instance_count=1,
        role=args.role_arn,
        transformers_version="4.49.0",
        pytorch_version="2.5.1",
        py_version="py311",
        hyperparameters={
            "model_id": MODEL_ID,  # Pass the correct model ID
            "epochs": 3,
            "learning_rate": 1e-4,  # Good LR for 2.7B model
            "max_seq_length": 512,  # Good length for Phi-2
            "hf_hub_enable_hf_transfer": False,
        },
        environment={
            "HF_TOKEN": hf_token,
            "SM_HP_HF_TOKEN": hf_token,
            "HF_HUB_ENABLE_HF_TRANSFER": "0",
        },
    )

    # Launch training
    logging.info("📤 Starting training job...")
    estimator.fit(
        inputs={"train": s3_train_path},
        job_name=JOB_NAME,
    )

    logging.info("✅ Training job launched successfully!")
    logging.info("🔗 Monitor: https://%s.console.aws.amazon.com/sagemaker/home?region=%s#/jobs/%s",
                 args.region, args.region, JOB_NAME)


# ------------------------------
# CLI Entry Point
# ------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Launch Qwen Training Job on SageMaker")
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID, help="HF model ID to fine-tune")
    parser.add_argument("--role-arn", default=DEFAULT_ROLE_ARN, help="SageMaker execution role ARN")
    parser.add_argument("--region", default=DEFAULT_REGION, help="AWS region")
    parser.add_argument("--bucket", default=DEFAULT_BUCKET, help="S3 bucket for input/output")
    parser.add_argument("--instance-type", default=DEFAULT_INSTANCE, help="Instance type")
    parser.add_argument("--job-name", default=None, help="Custom training job name")

    args = parser.parse_args()
    main(args)
