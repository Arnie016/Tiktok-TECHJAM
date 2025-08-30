#!/usr/bin/env python3
"""
Robust test for testphi endpoint to check if it learned from the dataset
"""

import boto3
import json
import logging
import time

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Configuration
ENDPOINT_NAME = "testphi"
REGION = "us-west-2"

def setup_aws_session():
    """Setup AWS session with profile"""
    logger.info(f"🔧 Setting up AWS session with profile: bedrock-561")
    session = boto3.Session(profile_name='bedrock-561', region_name=REGION)
    sagemaker_client = session.client('sagemaker-runtime')
    return sagemaker_client

def test_basic_functionality(sagemaker_client):
    """Test basic functionality"""
    logger.info("🧪 Testing basic functionality...")
    
    test_cases = [
        {
            "name": "Simple Question",
            "input": "What is geo-compliance?",
            "expected_keywords": ["compliance", "geographic", "law", "regulation", "requirement"]
        },
        {
            "name": "Florida Specific",
            "input": "What are Florida's age verification requirements?",
            "expected_keywords": ["Florida", "age", "verification", "requirement", "law"]
        },
        {
            "name": "Data Deletion",
            "input": "What are the data deletion requirements in Florida?",
            "expected_keywords": ["data", "deletion", "Florida", "requirement", "law"]
        }
    ]
    
    results = []
    for test_case in test_cases:
        try:
            payload = {
                "inputs": test_case["input"],
                "parameters": {
                    "max_new_tokens": 256,
                    "temperature": 0.7,
                    "do_sample": True
                }
            }
            
            response = sagemaker_client.invoke_endpoint(
                EndpointName=ENDPOINT_NAME,
                ContentType='application/json',
                Body=json.dumps(payload)
            )
            
            result = json.loads(response['Body'].read().decode())
            generated_text = result[0]['generated_text']
            
            # Check if response is meaningful (not just echoing input)
            is_meaningful = len(generated_text) > len(test_case["input"]) + 10
            contains_keywords = any(keyword.lower() in generated_text.lower() for keyword in test_case["expected_keywords"])
            
            results.append({
                "test": test_case["name"],
                "input": test_case["input"],
                "output": generated_text,
                "is_meaningful": is_meaningful,
                "contains_keywords": contains_keywords,
                "success": is_meaningful and contains_keywords
            })
            
            logger.info(f"✅ {test_case['name']}: {'PASS' if is_meaningful and contains_keywords else 'FAIL'}")
            logger.info(f"   Input: {test_case['input']}")
            logger.info(f"   Output: {generated_text[:200]}...")
            
        except Exception as e:
            logger.error(f"❌ {test_case['name']} failed: {e}")
            results.append({
                "test": test_case["name"],
                "input": test_case["input"],
                "output": str(e),
                "is_meaningful": False,
                "contains_keywords": False,
                "success": False
            })
    
    return results

def test_training_data_scenarios(sagemaker_client):
    """Test scenarios similar to training data"""
    logger.info("🧪 Testing training data scenarios...")
    
    test_cases = [
        {
            "name": "Age Verification Analysis",
            "input": """Analyze the following software feature to determine its geo-compliance requirements. Provide the compliance flag, the relevant law, and the reason.

Feature Name: FL Anonymous Age Verification
Feature Description: Provides anonymous/third-party age verification for adult/'harmful to minors' content and deletes verification data, limited to Florida users.""",
            "expected_keywords": ["Florida", "age verification", "compliance", "law", "requirement", "data deletion"]
        },
        {
            "name": "Data Processing Analysis",
            "input": """Analyze the following software feature to determine its geo-compliance requirements. Provide the compliance flag, the relevant law, and the reason.

Feature Name: EU Data Processing Engine
Feature Description: Processes personal data of EU users for targeted advertising and analytics.""",
            "expected_keywords": ["EU", "data processing", "GDPR", "compliance", "personal data", "law"]
        },
        {
            "name": "Content Moderation Analysis",
            "input": """Analyze the following software feature to determine its geo-compliance requirements. Provide the compliance flag, the relevant law, and the reason.

Feature Name: CA Content Moderation
Feature Description: Automatically moderates user-generated content for California users based on community guidelines.""",
            "expected_keywords": ["California", "content moderation", "compliance", "law", "requirement"]
        }
    ]
    
    results = []
    for test_case in test_cases:
        try:
            payload = {
                "inputs": test_case["input"],
                "parameters": {
                    "max_new_tokens": 512,
                    "temperature": 0.7,
                    "do_sample": True
                }
            }
            
            response = sagemaker_client.invoke_endpoint(
                EndpointName=ENDPOINT_NAME,
                ContentType='application/json',
                Body=json.dumps(payload)
            )
            
            result = json.loads(response['Body'].read().decode())
            generated_text = result[0]['generated_text']
            
            # Check if response shows learning
            is_analysis = "compliance" in generated_text.lower() or "law" in generated_text.lower()
            contains_keywords = any(keyword.lower() in generated_text.lower() for keyword in test_case["expected_keywords"])
            is_detailed = len(generated_text) > 100
            
            results.append({
                "test": test_case["name"],
                "input": test_case["input"][:100] + "...",
                "output": generated_text,
                "is_analysis": is_analysis,
                "contains_keywords": contains_keywords,
                "is_detailed": is_detailed,
                "success": is_analysis and contains_keywords and is_detailed
            })
            
            logger.info(f"✅ {test_case['name']}: {'PASS' if is_analysis and contains_keywords and is_detailed else 'FAIL'}")
            logger.info(f"   Output: {generated_text[:300]}...")
            
        except Exception as e:
            logger.error(f"❌ {test_case['name']} failed: {e}")
            results.append({
                "test": test_case["name"],
                "input": test_case["input"][:100] + "...",
                "output": str(e),
                "is_analysis": False,
                "contains_keywords": False,
                "is_detailed": False,
                "success": False
            })
    
    return results

def test_edge_cases(sagemaker_client):
    """Test edge cases and error handling"""
    logger.info("🧪 Testing edge cases...")
    
    test_cases = [
        {
            "name": "Empty Input",
            "input": "",
            "should_fail": True
        },
        {
            "name": "Very Long Input",
            "input": "What is geo-compliance? " * 100,
            "should_fail": False
        },
        {
            "name": "Special Characters",
            "input": "What are the requirements for data processing in EU? (GDPR compliance)",
            "should_fail": False
        },
        {
            "name": "Non-English",
            "input": "¿Cuáles son los requisitos de cumplimiento en Florida?",
            "should_fail": False
        }
    ]
    
    results = []
    for test_case in test_cases:
        try:
            payload = {
                "inputs": test_case["input"],
                "parameters": {
                    "max_new_tokens": 128,
                    "temperature": 0.7,
                    "do_sample": True
                }
            }
            
            response = sagemaker_client.invoke_endpoint(
                EndpointName=ENDPOINT_NAME,
                ContentType='application/json',
                Body=json.dumps(payload)
            )
            
            result = json.loads(response['Body'].read().decode())
            generated_text = result[0]['generated_text']
            
            success = not test_case["should_fail"] or len(generated_text) > 0
            
            results.append({
                "test": test_case["name"],
                "input": test_case["input"][:50] + "..." if len(test_case["input"]) > 50 else test_case["input"],
                "output": generated_text,
                "success": success
            })
            
            logger.info(f"✅ {test_case['name']}: {'PASS' if success else 'FAIL'}")
            logger.info(f"   Output: {generated_text[:100]}...")
            
        except Exception as e:
            logger.error(f"❌ {test_case['name']} failed: {e}")
            results.append({
                "test": test_case["name"],
                "input": test_case["input"][:50] + "..." if len(test_case["input"]) > 50 else test_case["input"],
                "output": str(e),
                "success": test_case["should_fail"]  # Expected to fail
            })
    
    return results

def generate_learning_report(basic_results, training_results, edge_results):
    """Generate a comprehensive learning report"""
    logger.info("\n" + "="*80)
    logger.info("🎯 LEARNING ANALYSIS REPORT")
    logger.info("="*80)
    
    # Basic functionality
    basic_success = sum(1 for r in basic_results if r["success"])
    basic_total = len(basic_results)
    basic_rate = (basic_success / basic_total) * 100 if basic_total > 0 else 0
    
    # Training data scenarios
    training_success = sum(1 for r in training_results if r["success"])
    training_total = len(training_results)
    training_rate = (training_success / training_total) * 100 if training_total > 0 else 0
    
    # Edge cases
    edge_success = sum(1 for r in edge_results if r["success"])
    edge_total = len(edge_results)
    edge_rate = (edge_success / edge_total) * 100 if edge_total > 0 else 0
    
    # Overall
    total_success = basic_success + training_success + edge_success
    total_tests = basic_total + training_total + edge_total
    overall_rate = (total_success / total_tests) * 100 if total_tests > 0 else 0
    
    logger.info(f"📊 BASIC FUNCTIONALITY: {basic_success}/{basic_total} ({basic_rate:.1f}%)")
    logger.info(f"📊 TRAINING DATA SCENARIOS: {training_success}/{training_total} ({training_rate:.1f}%)")
    logger.info(f"📊 EDGE CASES: {edge_success}/{edge_total} ({edge_rate:.1f}%)")
    logger.info(f"📊 OVERALL SUCCESS RATE: {total_success}/{total_tests} ({overall_rate:.1f}%)")
    
    # Learning assessment
    if overall_rate >= 80:
        logger.info("🎉 EXCELLENT: Model shows strong learning from the dataset!")
    elif overall_rate >= 60:
        logger.info("✅ GOOD: Model shows moderate learning from the dataset")
    elif overall_rate >= 40:
        logger.info("⚠️ FAIR: Model shows some learning but may need more training")
    else:
        logger.info("❌ POOR: Model shows minimal learning from the dataset")
    
    # Detailed analysis
    logger.info("\n📋 DETAILED ANALYSIS:")
    
    # Check if model generates meaningful responses
    meaningful_responses = sum(1 for r in basic_results + training_results if r.get("is_meaningful", False))
    total_responses = len([r for r in basic_results + training_results if "is_meaningful" in r])
    
    if total_responses > 0:
        meaningful_rate = (meaningful_responses / total_responses) * 100
        logger.info(f"   • Meaningful responses: {meaningful_responses}/{total_responses} ({meaningful_rate:.1f}%)")
        
        if meaningful_rate >= 70:
            logger.info("   ✅ Model generates meaningful responses (not just echoing input)")
        else:
            logger.info("   ⚠️ Model may be echoing input rather than generating new content")
    
    # Check keyword recognition
    keyword_responses = sum(1 for r in basic_results + training_results if r.get("contains_keywords", False))
    if total_responses > 0:
        keyword_rate = (keyword_responses / total_responses) * 100
        logger.info(f"   • Keyword recognition: {keyword_responses}/{total_responses} ({keyword_rate:.1f}%)")
        
        if keyword_rate >= 70:
            logger.info("   ✅ Model recognizes domain-specific keywords")
        else:
            logger.info("   ⚠️ Model may not be recognizing domain-specific terms")
    
    logger.info(f"\n🔗 Endpoint URL: https://runtime.sagemaker.us-west-2.amazonaws.com/endpoints/{ENDPOINT_NAME}/invocations")
    
    return {
        "basic_rate": basic_rate,
        "training_rate": training_rate,
        "edge_rate": edge_rate,
        "overall_rate": overall_rate,
        "meaningful_rate": meaningful_rate if total_responses > 0 else 0,
        "keyword_rate": keyword_rate if total_responses > 0 else 0
    }

def main():
    """Main function"""
    logger.info("🚀 Starting robust testphi endpoint testing...")
    
    try:
        # Setup AWS session
        sagemaker_client = setup_aws_session()
        
        # Run all tests
        logger.info("\n" + "="*60)
        logger.info("PHASE 1: Basic Functionality Testing")
        logger.info("="*60)
        basic_results = test_basic_functionality(sagemaker_client)
        
        logger.info("\n" + "="*60)
        logger.info("PHASE 2: Training Data Scenario Testing")
        logger.info("="*60)
        training_results = test_training_data_scenarios(sagemaker_client)
        
        logger.info("\n" + "="*60)
        logger.info("PHASE 3: Edge Case Testing")
        logger.info("="*60)
        edge_results = test_edge_cases(sagemaker_client)
        
        # Generate comprehensive report
        report = generate_learning_report(basic_results, training_results, edge_results)
        
        logger.info("\n🎯 TESTING COMPLETED!")
        
    except Exception as e:
        logger.error(f"❌ Error in main: {e}")

if __name__ == "__main__":
    main()
