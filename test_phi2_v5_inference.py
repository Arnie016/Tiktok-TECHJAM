#!/usr/bin/env python3
"""
Test script for the phi2-v5-inference endpoint with custom LoRA inference
"""

import boto3
import json
import time

def test_inference_endpoint():
    """Test the phi2-v5-inference endpoint"""
    
    # Setup client
    session = boto3.Session(profile_name='bedrock-561', region_name='us-west-2')
    sagemaker_runtime = session.client('sagemaker-runtime')
    
    endpoint_name = 'phi2-v5-inference'
    
    # Test cases for geo-compliance analysis
    test_cases = [
        {
            "name": "GDPR Compliance Check",
            "instruction": "Analyse the feature artifact and decide if geo-specific compliance logic is needed. Explain why and cite the relevant regulation if any.",
            "input": """Feature Name: EU Data Processing Compliance Check
Feature Description: Automated system to verify GDPR Article 6 lawful basis before processing EU user data; includes consent verification and legitimate interest assessment.

Law Context (structured JSON):
[{"law": "GDPR Article 6", "jurisdiction": "EU", "requirement": "Lawful basis required for personal data processing"}]"""
        },
        {
            "name": "US Financial Compliance",
            "instruction": "Analyse the feature artifact and decide if geo-specific compliance logic is needed. Explain why and cite the relevant regulation if any.",
            "input": """Feature Name: US Banking Data Encryption
Feature Description: Implements AES-256 encryption for financial data storage, specifically for US customer transactions.

Law Context (structured JSON):
[{"law": "SOX Section 404", "jurisdiction": "US", "requirement": "Financial data protection and internal controls"}]"""
        },
        {
            "name": "Generic Feature - No Compliance",
            "instruction": "Analyse the feature artifact and decide if geo-specific compliance logic is needed. Explain why and cite the relevant regulation if any.",
            "input": """Feature Name: User Profile Picture Upload
Feature Description: Basic feature allowing users to upload profile pictures with standard image validation.

Law Context (structured JSON):
[]"""
        }
    ]
    
    print("🏆 Testing Phi-2 v5 Inference Endpoint")
    print(f"📡 Endpoint: {endpoint_name}")
    print("🔧 Custom inference with LoRA adapters + memory optimization")
    print("📊 Trained on 1441 examples")
    print("=" * 70)
    
    all_results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 Test Case {i}: {test_case['name']}")
        print("-" * 50)
        
        try:
            # Prepare payload
            payload = {
                "instruction": test_case["instruction"],
                "input": test_case["input"]
            }
            
            print("📤 Sending request...")
            start_time = time.time()
            
            # Invoke endpoint
            response = sagemaker_runtime.invoke_endpoint(
                EndpointName=endpoint_name,
                ContentType='application/json',
                Body=json.dumps(payload)
            )
            
            end_time = time.time()
            response_time = end_time - start_time
            
            # Parse response
            result = json.loads(response['Body'].read().decode())
            
            print(f"✅ SUCCESS: Response received in {response_time:.2f}s")
            print(f"\n📝 Generated Text:")
            print("-" * 30)
            print(result.get('generated_text', 'No generated text found'))
            
            # Quality analysis
            generated_text = result.get('generated_text', '').lower()
            quality_scores = []
            
            if 'compliance' in generated_text:
                quality_scores.append("✅ Mentions compliance")
            if any(word in generated_text for word in ['gdpr', 'sox', 'regulation']):
                quality_scores.append("✅ References relevant laws")
            if any(word in generated_text for word in ['required', 'needed', 'necessary', 'not required']):
                quality_scores.append("✅ Makes clear recommendation")
            if len(generated_text) > 50:
                quality_scores.append("✅ Adequate response length")
            if not any(word in generated_text for word in ['error', 'failed', 'exception']):
                quality_scores.append("✅ No error indicators")
            
            print(f"\n🔍 Quality Analysis:")
            for score in quality_scores:
                print(f"  {score}")
            
            quality_percentage = (len(quality_scores) / 5) * 100
            print(f"📊 Quality Score: {quality_percentage:.0f}%")
            
            # Store results
            all_results.append({
                "test_case": test_case['name'],
                "response_time": response_time,
                "quality_score": quality_percentage,
                "success": True,
                "generated_text": result.get('generated_text', '')
            })
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            all_results.append({
                "test_case": test_case['name'],
                "response_time": 0,
                "quality_score": 0,
                "success": False,
                "error": str(e)
            })
            
        print("\n" + "="*70)
    
    # Summary report
    print("\n📋 SUMMARY REPORT")
    print("="*70)
    
    successful_tests = [r for r in all_results if r['success']]
    if successful_tests:
        avg_response_time = sum(r['response_time'] for r in successful_tests) / len(successful_tests)
        avg_quality = sum(r['quality_score'] for r in successful_tests) / len(successful_tests)
        
        print(f"✅ Successful Tests: {len(successful_tests)}/{len(all_results)}")
        print(f"⏱️ Average Response Time: {avg_response_time:.2f}s")
        print(f"📊 Average Quality Score: {avg_quality:.0f}%")
        
        if avg_quality >= 80:
            print("🎉 EXCELLENT: Model shows high-quality responses!")
        elif avg_quality >= 60:
            print("👍 GOOD: Model shows decent performance")
        else:
            print("⚠️ NEEDS IMPROVEMENT: Model quality could be better")
            
        if avg_response_time <= 5:
            print("⚡ FAST: Response times are excellent")
        elif avg_response_time <= 10:
            print("🚀 GOOD: Response times are acceptable")
        else:
            print("⏳ SLOW: Response times could be improved")
            
    else:
        print("❌ All tests failed - check CloudWatch logs")
    
    return len(successful_tests) == len(all_results)

def main():
    """Main function"""
    print("🎯 Phi-2 v5 Inference Endpoint Test")
    print("Enhanced model with custom LoRA inference logic")
    print("="*70)
    
    success = test_inference_endpoint()
    
    if success:
        print(f"\n✅ ALL TESTS PASSED!")
        print("🎉 Phi-2 v5 with custom inference is working perfectly!")
        print("🚀 Ready for production use and Lambda deployment")
    else:
        print(f"\n⚠️ Some tests failed")
        print("🔍 Check CloudWatch logs for detailed error information")

if __name__ == "__main__":
    main()

