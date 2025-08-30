#!/usr/bin/env python3
"""
Cleanup Old Endpoints
=====================
List and delete old endpoints to free up resources for the new model.
"""

import boto3
import json

# AWS Configuration
CORRECT_ACCOUNT = "561947681110"
REGION = "us-west-2"

def get_aws_session():
    """Get AWS session with correct profile"""
    
    # Find profile that matches correct account
    profiles = boto3.Session().available_profiles
    correct_profile = None
    
    for profile in profiles:
        try:
            session = boto3.Session(profile_name=profile)
            sts = session.client('sts')
            identity = sts.get_caller_identity()
            account_id = identity['Account']
            
            if account_id == CORRECT_ACCOUNT:
                correct_profile = profile
                break
        except Exception as e:
            continue
    
    if not correct_profile:
        print(f"❌ No profile found for account {CORRECT_ACCOUNT}")
        return None
    
    return boto3.Session(profile_name=correct_profile)

def list_endpoints(session):
    """List all endpoints"""
    
    print("📋 Current Endpoints:")
    print("=" * 50)
    
    sagemaker_client = session.client('sagemaker', region_name=REGION)
    
    try:
        response = sagemaker_client.list_endpoints()
        endpoints = response['Endpoints']
        
        if not endpoints:
            print("No endpoints found.")
            return []
        
        for i, endpoint in enumerate(endpoints, 1):
            name = endpoint['EndpointName']
            status = endpoint['EndpointStatus']
            created = endpoint['CreationTime']
            print(f"{i}. {name}")
            print(f"   Status: {status}")
            print(f"   Created: {created}")
            print()
        
        return endpoints
        
    except Exception as e:
        print(f"❌ Error listing endpoints: {e}")
        return []

def delete_endpoint(session, endpoint_name):
    """Delete a specific endpoint"""
    
    print(f"🗑️ Deleting endpoint: {endpoint_name}")
    
    sagemaker_client = session.client('sagemaker', region_name=REGION)
    
    try:
        # Delete endpoint
        sagemaker_client.delete_endpoint(EndpointName=endpoint_name)
        print(f"✅ Endpoint deletion initiated: {endpoint_name}")
        
        # Wait for deletion to complete
        print(f"⏳ Waiting for deletion to complete...")
        waiter = sagemaker_client.get_waiter('endpoint_deleted')
        waiter.wait(EndpointName=endpoint_name)
        
        print(f"✅ Endpoint deleted: {endpoint_name}")
        return True
        
    except Exception as e:
        print(f"❌ Error deleting endpoint: {e}")
        return False

def cleanup_old_endpoints():
    """Clean up old endpoints"""
    
    print("🧹 Cleaning up old endpoints")
    print("=" * 50)
    
    # Get AWS session
    session = get_aws_session()
    if not session:
        return False
    
    # List current endpoints
    endpoints = list_endpoints(session)
    
    if not endpoints:
        print("No endpoints to clean up.")
        return True
    
    # Find old endpoints to delete
    old_endpoints = []
    for endpoint in endpoints:
        name = endpoint['EndpointName']
        # Skip the new endpoint we want to keep
        if 'fixed-lora' not in name:
            old_endpoints.append(name)
    
    if not old_endpoints:
        print("No old endpoints to delete.")
        return True
    
    print(f"\n🗑️ Found {len(old_endpoints)} old endpoints to delete:")
    for name in old_endpoints:
        print(f"  - {name}")
    
    # Delete old endpoints
    for endpoint_name in old_endpoints:
        delete_endpoint(session, endpoint_name)
        print()
    
    print("✅ Cleanup completed!")
    return True

if __name__ == "__main__":
    try:
        cleanup_old_endpoints()
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
        raise
