#!/usr/bin/env python3
"""
Fix SageMaker Execution Role Permissions
Adds the missing S3 permissions needed for training jobs
"""

import boto3
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def fix_sagemaker_permissions():
    """Add missing S3 permissions to SageMaker execution role"""
    
    # Initialize IAM client
    session = boto3.Session(profile_name='bedrock-561', region_name='us-west-2')
    iam = session.client('iam')
    
    role_name = "SageMakerExecutionRole"
    bucket_name = "sagemaker-us-west-2-561947681110"
    
    logger.info(f"🔧 Adding S3 permissions to role: {role_name}")
    logger.info(f"📦 For bucket: {bucket_name}")
    
    # S3 permissions policy
    s3_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "s3:ListBucket",
                    "s3:GetBucketLocation"
                ],
                "Resource": f"arn:aws:s3:::{bucket_name}"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:DeleteObject"
                ],
                "Resource": f"arn:aws:s3:::{bucket_name}/*"
            }
        ]
    }
    
    policy_name = "SageMakerS3Access"
    
    try:
        # Create or update the policy
        try:
            # Try to create new policy
            response = iam.put_role_policy(
                RoleName=role_name,
                PolicyName=policy_name,
                PolicyDocument=json.dumps(s3_policy)
            )
            logger.info("✅ Created new S3 access policy")
        except Exception as existing_error:
            # Policy might exist, try to update it
            response = iam.put_role_policy(
                RoleName=role_name,
                PolicyName=policy_name,
                PolicyDocument=json.dumps(s3_policy)
            )
            logger.info("✅ Updated existing S3 access policy")
        
        logger.info("🎉 SageMaker execution role permissions fixed!")
        logger.info("📋 Added permissions:")
        logger.info("   - s3:ListBucket")
        logger.info("   - s3:GetBucketLocation") 
        logger.info("   - s3:GetObject")
        logger.info("   - s3:PutObject")
        logger.info("   - s3:DeleteObject")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to update permissions: {e}")
        return False

def verify_permissions():
    """Verify the role has the correct permissions"""
    logger.info("🔍 Verifying SageMaker role permissions...")
    
    session = boto3.Session(profile_name='bedrock-561', region_name='us-west-2')
    iam = session.client('iam')
    
    role_name = "SageMakerExecutionRole"
    
    try:
        # List role policies
        response = iam.list_role_policies(RoleName=role_name)
        policies = response['PolicyNames']
        
        logger.info(f"📋 Current inline policies: {policies}")
        
        if "SageMakerS3Access" in policies:
            # Get the policy document
            policy_response = iam.get_role_policy(
                RoleName=role_name,
                PolicyName="SageMakerS3Access"
            )
            
            logger.info("✅ SageMakerS3Access policy found")
            return True
        else:
            logger.warning("⚠️ SageMakerS3Access policy not found")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error verifying permissions: {e}")
        return False

def main():
    """Main function"""
    logger.info("🚀 SageMaker Permissions Fix Tool")
    logger.info("=" * 50)
    
    # First verify current permissions
    if verify_permissions():
        logger.info("✅ Permissions already configured correctly")
    else:
        logger.info("🔧 Fixing permissions...")
        if fix_sagemaker_permissions():
            logger.info("✅ Permissions fixed successfully!")
            logger.info("🎯 You can now run the training job")
        else:
            logger.error("❌ Failed to fix permissions")
            return False
    
    return True

if __name__ == "__main__":
    main()
