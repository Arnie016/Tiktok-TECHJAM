import json
import boto3
import logging
from typing import Dict, Any

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize SageMaker client
sagemaker_runtime = boto3.client('sagemaker-runtime', region_name='us-west-2')

# Constants
ENDPOINT_NAME = 'phi2-v5-inference'
MAX_TOKENS = 256
TIMEOUT = 30  # seconds

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda function to invoke Phi-2 v5 SageMaker endpoint for geo-compliance analysis
    
    Expected input format:
    {
        "instruction": "Analyse the feature artifact and decide if geo-specific compliance logic is needed...",
        "input": "Feature Name: ...\nFeature Description: ...\nLaw Context: ..."
    }
    
    Returns structured response with compliance analysis
    """
    
    # Set CORS headers for web access
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
    }
    
    try:
        # Handle preflight CORS requests
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({'message': 'CORS preflight successful'})
            }
        
        # Parse input
        body = event.get('body', '{}')
        if isinstance(body, str):
            try:
                request_data = json.loads(body)
            except json.JSONDecodeError:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({
                        'error': 'Invalid JSON in request body',
                        'message': 'Please provide valid JSON input'
                    })
                }
        else:
            request_data = body
        
        # Extract parameters
        instruction = request_data.get('instruction', '')
        feature_input = request_data.get('input', '')
        
        # Validate required fields
        if not instruction or not feature_input:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({
                    'error': 'Missing required fields',
                    'message': 'Both "instruction" and "input" fields are required',
                    'received': {
                        'instruction': bool(instruction),
                        'input': bool(feature_input)
                    }
                })
            }
        
        # Log the request (without sensitive data)
        logger.info(f"Processing request - Instruction length: {len(instruction)}, Input length: {len(feature_input)}")
        
        # Prepare payload for SageMaker
        sagemaker_payload = {
            "instruction": instruction,
            "input": feature_input
        }
        
        # Invoke SageMaker endpoint
        logger.info(f"Invoking SageMaker endpoint: {ENDPOINT_NAME}")
        
        response = sagemaker_runtime.invoke_endpoint(
            EndpointName=ENDPOINT_NAME,
            ContentType='application/json',
            Body=json.dumps(sagemaker_payload)
        )
        
        # Parse SageMaker response
        result = json.loads(response['Body'].read().decode())
        
        # Extract generated text
        generated_text = result.get('generated_text', '')
        
        # Log response info
        logger.info(f"SageMaker response received - Generated text length: {len(generated_text)}")
        
        # Structure the response
        structured_response = {
            'success': True,
            'model_version': 'phi2-v5',
            'endpoint': ENDPOINT_NAME,
            'analysis': {
                'generated_text': generated_text,
                'raw_response': result
            },
            'metadata': {
                'instruction_length': len(instruction),
                'input_length': len(feature_input),
                'response_length': len(generated_text),
                'model_info': {
                    'name': 'Phi-2 v5',
                    'training_examples': 1441,
                    'capabilities': ['geo-compliance', 'jurisdiction-analysis', 'law-citation']
                }
            }
        }
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(structured_response, indent=2)
        }
        
    except Exception as e:
        # Log the error
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        
        # Return error response
        error_response = {
            'success': False,
            'error': {
                'type': type(e).__name__,
                'message': str(e),
                'endpoint': ENDPOINT_NAME
            },
            'metadata': {
                'model_version': 'phi2-v5',
                'error_occurred': True
            }
        }
        
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps(error_response, indent=2)
        }

# Test function for local testing
def test_lambda_locally():
    """Test function for local development"""
    test_event = {
        'httpMethod': 'POST',
        'body': json.dumps({
            'instruction': 'Analyse the feature artifact and decide if geo-specific compliance logic is needed. Explain why and cite the relevant regulation if any.',
            'input': '''Feature Name: EU Cookie Consent Banner
Feature Description: Display cookie consent banner for EU users accessing the website, with options to accept or reject non-essential cookies.

Law Context (structured JSON):
[{"law": "GDPR Article 7", "jurisdiction": "EU", "requirement": "Valid consent for data processing"}]'''
        })
    }
    
    result = lambda_handler(test_event, None)
    print("Test Result:")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    test_lambda_locally()

