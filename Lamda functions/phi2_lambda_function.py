import json
import boto3
import logging
import re
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

def parse_compliance_response(text: str) -> Dict[str, Any]:
    """
    Parse the model's text response to extract structured compliance data
    """
    # Default response structure
    compliance_data = {
        'need_geo_logic': False,
        'jurisdictions': [],
        'legal_citations': [],
        'data_categories': [],
        'lawful_basis': [],
        'consent_required': False,
        'confidence': 0.5,
        'description': text  # Store the full description
    }
    
    text_lower = text.lower()
    
    # Check if geo-specific logic is needed - be more specific
    # Look for positive indicators of geo-compliance requirements
    positive_indicators = [
        'requires geo', 'needs geo', 'geo-specific', 'geo-based',
        'gdpr compliance', 'ccpa compliance', 'eu compliance',
        'california compliance', 'jurisdiction-specific',
        'location-based', 'region-specific'
    ]
    
    # Look for negative indicators that explicitly say no geo-compliance is needed
    negative_indicators = [
        'does not require geo', 'does not need geo', 'no geo-specific',
        'no geo-based', 'standard implementation', 'no jurisdiction-specific',
        'not location-based', 'not region-specific', 'no specific regulations',
        'no specific laws', 'no regulations', 'no laws'
    ]
    
    # Check for negative indicators first
    has_negative = any(phrase in text_lower for phrase in negative_indicators)
    
    # Check for positive indicators
    has_positive = any(phrase in text_lower for phrase in positive_indicators)
    
    # Set geo-compliance requirement based on indicators
    if has_positive and not has_negative:
        compliance_data['need_geo_logic'] = True
    elif has_negative:
        compliance_data['need_geo_logic'] = False
    else:
        # Fallback: check for specific jurisdiction mentions
        jurisdiction_mentions = text_lower.count('eu') + text_lower.count('gdpr') + text_lower.count('ccpa') + text_lower.count('california')
        compliance_data['need_geo_logic'] = jurisdiction_mentions > 0
    
    # Extract jurisdictions
    jurisdiction_patterns = {
        'EU': ['eu', 'europe', 'gdpr', 'european'],
        'US-CA': ['california', 'ccpa', 'ca'],
        'US': ['united states', 'us federal', 'coppa', 'sox'],
        'UK': ['uk', 'united kingdom', 'british'],
        'Canada': ['canada', 'canadian', 'pipeda'],
        'Brazil': ['brazil', 'brazilian', 'lgpd']
    }
    
    for jurisdiction, patterns in jurisdiction_patterns.items():
        if any(pattern in text_lower for pattern in patterns):
            if jurisdiction not in compliance_data['jurisdictions']:
                compliance_data['jurisdictions'].append(jurisdiction)
    
    # Enhanced legal citations extraction
    legal_patterns = [
        (r'gdpr\s+article\s+(\d+)', 'GDPR Article {}', 'EU'),
        (r'ccpa\s+section\s+(\d+)', 'CCPA Section {}', 'US-CA'),
        (r'coppa', 'COPPA', 'US'),
        (r'sox\s+section\s+(\d+)', 'SOX Section {}', 'US'),
        (r'lgpd\s+article\s+(\d+)', 'LGPD Article {}', 'Brazil'),
        (r'pipeda\s+principle\s+(\d+)', 'PIPEDA Principle {}', 'Canada')
    ]
    
    for pattern, format_str, jurisdiction in legal_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):
                article_num = match[0]
                law_name = format_str.format(article_num)
            else:
                law_name = format_str
            compliance_data['legal_citations'].append({
                'law': law_name.upper(),
                'jurisdiction': jurisdiction,
                'description': f'Applies to {jurisdiction} jurisdiction'
            })
    
    # Also extract laws mentioned in the original context
    if 'gdpr article 7' in text_lower:
        compliance_data['legal_citations'].append({
            'law': 'GDPR ARTICLE 7',
            'jurisdiction': 'EU',
            'description': 'Valid consent for data processing'
        })
    if 'gdpr article 6' in text_lower:
        compliance_data['legal_citations'].append({
            'law': 'GDPR ARTICLE 6',
            'jurisdiction': 'EU',
            'description': 'Lawful basis for processing personal data'
        })
    
    # Extract data categories
    data_patterns = {
        'personal data': ['personal data', 'personal information'],
        'cookies': ['cookies', 'cookie'],
        'analytics': ['analytics', 'tracking'],
        'financial data': ['financial', 'transaction'],
        'age data': ['age', 'birth date', 'date of birth']
    }
    
    for category, patterns in data_patterns.items():
        if any(pattern in text_lower for pattern in patterns):
            if category not in compliance_data['data_categories']:
                compliance_data['data_categories'].append(category)
    
    # Extract lawful basis
    basis_patterns = {
        'consent': ['consent', 'permission'],
        'legitimate interest': ['legitimate interest', 'business purpose'],
        'legal obligation': ['legal obligation', 'required by law'],
        'contract': ['contract', 'agreement']
    }
    
    for basis, patterns in basis_patterns.items():
        if any(pattern in text_lower for pattern in patterns):
            if basis not in compliance_data['lawful_basis']:
                compliance_data['lawful_basis'].append(basis)
    
    # Check if consent is required
    if any(phrase in text_lower for phrase in ['consent', 'permission', 'opt-in', 'agree']):
        compliance_data['consent_required'] = True
    
    # Calculate confidence based on response quality
    confidence_factors = 0
    if compliance_data['need_geo_logic']:
        confidence_factors += 1
    if compliance_data['jurisdictions']:
        confidence_factors += 1
    if compliance_data['legal_citations']:
        confidence_factors += 1
    if compliance_data['data_categories']:
        confidence_factors += 1
    
    compliance_data['confidence'] = min(0.95, 0.5 + (confidence_factors * 0.15))
    
    return compliance_data

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
        'Content-Type': 'application/json'
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
        
        # Parse compliance data from the response
        compliance_data = parse_compliance_response(generated_text)
        
        # Structure the response
        structured_response = {
            'success': True,
            'compliance': compliance_data,
            'raw_response': generated_text,  # Add the raw model response
            'metadata': {
                'model_version': 'phi2-v5',
                'endpoint': ENDPOINT_NAME,
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

