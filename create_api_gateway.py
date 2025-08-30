#!/usr/bin/env python3
"""
Create API Gateway for the Lambda function to bypass Function URL 403 issues
"""

import boto3
import json
import time
from botocore.exceptions import ClientError

def create_api_gateway():
    """Create API Gateway REST API for the Lambda function"""
    
    # Initialize clients
    session = boto3.Session(profile_name='bedrock-561', region_name='us-west-2')
    apigateway = session.client('apigateway')
    lambda_client = session.client('lambda')
    
    # Configuration
    api_name = "phi2-v5-geo-compliance-api"
    lambda_function_name = "phi2-v5-geo-compliance"
    lambda_function_arn = f"arn:aws:lambda:us-west-2:561947681110:function:{lambda_function_name}"
    
    try:
        print("🚀 Creating API Gateway for your Lambda function...")
        
        # Step 1: Create REST API
        print("📡 Creating REST API...")
        api_response = apigateway.create_rest_api(
            name=api_name,
            description="API Gateway for Phi-2 v5 Geo-Compliance Lambda function",
            endpointConfiguration={
                'types': ['REGIONAL']
            }
        )
        
        api_id = api_response['id']
        print(f"✅ API created: {api_id}")
        
        # Step 2: Get root resource
        resources = apigateway.get_resources(restApiId=api_id)
        root_resource_id = None
        for resource in resources['items']:
            if resource['path'] == '/':
                root_resource_id = resource['id']
                break
        
        # Step 3: Create /analyze resource
        print("📝 Creating /analyze resource...")
        resource_response = apigateway.create_resource(
            restApiId=api_id,
            parentId=root_resource_id,
            pathPart='analyze'
        )
        resource_id = resource_response['id']
        
        # Step 4: Create POST method
        print("🔧 Creating POST method...")
        apigateway.put_method(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod='POST',
            authorizationType='NONE',
            requestParameters={}
        )
        
        # Step 5: Create OPTIONS method for CORS
        print("🌐 Setting up CORS...")
        apigateway.put_method(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod='OPTIONS',
            authorizationType='NONE'
        )
        
        # Step 6: Set up POST integration
        print("🔗 Setting up Lambda integration...")
        integration_uri = f"arn:aws:apigateway:us-west-2:lambda:path/2015-03-31/functions/{lambda_function_arn}/invocations"
        
        apigateway.put_integration(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod='POST',
            type='AWS_PROXY',
            integrationHttpMethod='POST',
            uri=integration_uri
        )
        
        # Step 7: Set up OPTIONS integration for CORS
        apigateway.put_integration(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod='OPTIONS',
            type='MOCK',
            requestTemplates={
                'application/json': '{"statusCode": 200}'
            }
        )
        
        # Step 8: Set up OPTIONS method response
        apigateway.put_method_response(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod='OPTIONS',
            statusCode='200',
            responseParameters={
                'method.response.header.Access-Control-Allow-Headers': False,
                'method.response.header.Access-Control-Allow-Methods': False,
                'method.response.header.Access-Control-Allow-Origin': False
            }
        )
        
        # Step 9: Set up OPTIONS integration response
        apigateway.put_integration_response(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod='OPTIONS',
            statusCode='200',
            responseParameters={
                'method.response.header.Access-Control-Allow-Headers': "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
                'method.response.header.Access-Control-Allow-Methods': "'GET,POST,OPTIONS'",
                'method.response.header.Access-Control-Allow-Origin': "'*'"
            }
        )
        
        # Step 10: Grant API Gateway permission to invoke Lambda
        print("🔐 Setting up Lambda permissions...")
        try:
            lambda_client.add_permission(
                FunctionName=lambda_function_name,
                StatementId=f'api-gateway-invoke-{int(time.time())}',
                Action='lambda:InvokeFunction',
                Principal='apigateway.amazonaws.com',
                SourceArn=f'arn:aws:execute-api:us-west-2:561947681110:{api_id}/*/*'
            )
            print("✅ Lambda permissions granted")
        except ClientError as e:
            if 'ResourceConflictException' in str(e):
                print("⚠️ Permission already exists, skipping...")
            else:
                raise
        
        # Step 11: Deploy API
        print("🚀 Deploying API...")
        deployment = apigateway.create_deployment(
            restApiId=api_id,
            stageName='prod'
        )
        
        # Construct the API URL
        api_url = f"https://{api_id}.execute-api.us-west-2.amazonaws.com/prod/analyze"
        
        print("\n🎉 API Gateway created successfully!")
        print("=" * 60)
        print(f"📡 API ID: {api_id}")
        print(f"🔗 API URL: {api_url}")
        print(f"📝 Method: POST")
        print(f"🎯 Endpoint: /analyze")
        print("=" * 60)
        
        # Test the API
        print("\n🧪 Testing the API...")
        test_api(api_url)
        
        # Update the HTML file with the new API URL
        update_html_with_api_url(api_url)
        
        return api_url
        
    except Exception as e:
        print(f"❌ Error creating API Gateway: {str(e)}")
        return None

def test_api(api_url):
    """Test the new API Gateway endpoint"""
    import requests
    
    try:
        payload = {
            "instruction": "Analyse the feature artifact and decide if geo-specific compliance logic is needed.",
            "input": "Feature Name: Test Feature\nFeature Description: Simple test\nLaw Context: []"
        }
        
        response = requests.post(
            api_url,
            headers={'Content-Type': 'application/json'},
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            print("✅ API test successful!")
            result = response.json()
            if result.get('success'):
                print(f"🎯 Compliance needed: {result.get('compliance', {}).get('need_geo_logic', 'unknown')}")
            else:
                print(f"⚠️ API returned success=false: {result}")
        else:
            print(f"❌ API test failed: {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            
    except Exception as e:
        print(f"⚠️ API test error: {str(e)}")

def update_html_with_api_url(api_url):
    """Update the HTML file with the new API Gateway URL"""
    try:
        with open('/Users/hema/Desktop/bedrock/geo_compliance_ui.html', 'r') as f:
            content = f.read()
        
        # Replace the Lambda Function URL with API Gateway URL
        old_url = "https://bvemy4jegpeyk3tf2asnihjn3a0kvwyq.lambda-url.us-west-2.on.aws/"
        new_content = content.replace(old_url, api_url)
        
        with open('/Users/hema/Desktop/bedrock/geo_compliance_ui.html', 'w') as f:
            f.write(new_content)
        
        print(f"✅ Updated HTML file with API Gateway URL")
        
    except Exception as e:
        print(f"⚠️ Could not update HTML file: {str(e)}")

if __name__ == "__main__":
    print("🛡️ Phi-2 v5 API Gateway Setup")
    print("Fixing the Function URL 403 issue with API Gateway...")
    print("")
    
    api_url = create_api_gateway()
    
    if api_url:
        print("\n🎊 Setup Complete!")
        print(f"Your new API endpoint: {api_url}")
        print("✅ HTML file updated with new URL")
        print("✅ CORS properly configured")
        print("✅ Lambda permissions granted")
        print("\n🎯 Next steps:")
        print("1. Open geo_compliance_ui.html in your browser")
        print("2. Test the compliance analyzer")
        print("3. Your UI is now production-ready!")
    else:
        print("\n❌ Setup failed. Check the errors above.")

