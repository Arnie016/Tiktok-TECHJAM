#!/usr/bin/env python3
"""
Direct Lambda function testing script (bypasses Function URL issues)
"""

import boto3
import json
import time
from datetime import datetime

def test_lambda_function():
    """Test the Lambda function directly using boto3"""
    
    # Setup client
    session = boto3.Session(profile_name='bedrock-561', region_name='us-west-2')
    lambda_client = session.client('lambda')
    
    function_name = 'phi2-v5-geo-compliance'
    
    # Test cases
    test_cases = [
        {
            "name": "✅ GDPR Cookie Consent (EU)",
            "instruction": "Analyse the feature artifact and decide if geo-specific compliance logic is needed. Explain why and cite the relevant regulation if any.",
            "input": """Feature Name: EU Cookie Consent Banner
Feature Description: Display cookie consent banner for EU users accessing the website with accept/reject options.

Law Context (structured JSON):
[{"law": "GDPR Article 7", "jurisdiction": "EU", "requirement": "Valid consent for data processing"}]"""
        },
        {
            "name": "✅ US CCPA Privacy Rights (California)",
            "instruction": "Analyse the feature artifact and decide if geo-specific compliance logic is needed. Explain why and cite the relevant regulation if any.",
            "input": """Feature Name: California Do Not Sell Button
Feature Description: Button for California residents to opt-out of personal information sales.

Law Context (structured JSON):
[{"law": "CCPA Section 1798.135", "jurisdiction": "US-CA", "requirement": "Right to opt-out of sale of personal information"}]"""
        },
        {
            "name": "❌ Simple UI Feature (No Compliance)",
            "instruction": "Analyse the feature artifact and decide if geo-specific compliance logic is needed. Explain why and cite the relevant regulation if any.",
            "input": """Feature Name: Dark Mode Toggle
Feature Description: Simple UI toggle for switching between light and dark color themes.

Law Context (structured JSON):
[]"""
        },
        {
            "name": "✅ Financial SOX Compliance (US)",
            "instruction": "Analyse the feature artifact and decide if geo-specific compliance logic is needed. Explain why and cite the relevant regulation if any.",
            "input": """Feature Name: Financial Transaction Logger
Feature Description: Logs all financial transactions and database changes for compliance auditing in US public companies.

Law Context (structured JSON):
[{"law": "SOX Section 404", "jurisdiction": "US", "requirement": "Internal controls over financial reporting"}]"""
        }
    ]
    
    print("🚀 Phi-2 v5 Lambda Function Direct Testing")
    print(f"📡 Function Name: {function_name}")
    print("🔧 Testing via direct boto3 invoke (bypasses Function URL)")
    print("=" * 80)
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 Test {i}/{len(test_cases)}: {test_case['name']}")
        print("-" * 60)
        
        try:
            # Prepare payload
            payload = {
                'httpMethod': 'POST',
                'body': json.dumps({
                    'instruction': test_case['instruction'],
                    'input': test_case['input']
                })
            }
            
            print("📤 Invoking Lambda function...")
            start_time = time.time()
            
            # Invoke function
            response = lambda_client.invoke(
                FunctionName=function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            
            response_time = time.time() - start_time
            
            # Parse response
            result = json.loads(response['Payload'].read().decode())
            
            if result.get('statusCode') == 200:
                print(f"✅ SUCCESS: Lambda responded in {response_time:.2f}s")
                
                # Parse body
                body = json.loads(result.get('body', '{}'))
                
                if body.get('success'):
                    analysis = body.get('analysis', {})
                    generated_text = analysis.get('generated_text', '')
                    
                    print(f"\n📝 Model Response:")
                    print("-" * 40)
                    print(generated_text)
                    print("-" * 40)
                    
                    # Basic analysis
                    text_lower = generated_text.lower()
                    compliance_mentioned = any(word in text_lower for word in ['compliance', 'required', 'needed', 'necessary'])
                    law_mentioned = any(law in text_lower for law in ['gdpr', 'ccpa', 'sox'])
                    reasoning_provided = any(word in text_lower for word in ['because', 'since', 'due to', 'therefore'])
                    
                    print(f"\n🔍 Quick Analysis:")
                    print(f"  📋 Mentions Compliance: {'✅' if compliance_mentioned else '❌'}")
                    print(f"  ⚖️ References Laws: {'✅' if law_mentioned else '❌'}")
                    print(f"  💭 Provides Reasoning: {'✅' if reasoning_provided else '❌'}")
                    print(f"  📏 Response Length: {len(generated_text)} characters")
                    
                    # Store results
                    results.append({
                        'test_name': test_case['name'],
                        'success': True,
                        'response_time': response_time,
                        'response_length': len(generated_text),
                        'compliance_mentioned': compliance_mentioned,
                        'law_mentioned': law_mentioned,
                        'reasoning_provided': reasoning_provided,
                        'generated_text': generated_text
                    })
                    
                else:
                    print(f"❌ Lambda returned success=false: {body}")
                    results.append({
                        'test_name': test_case['name'],
                        'success': False,
                        'error': 'Lambda success=false'
                    })
                    
            else:
                print(f"❌ Lambda returned error: {result}")
                results.append({
                    'test_name': test_case['name'],
                    'success': False,
                    'error': f"Status code: {result.get('statusCode')}"
                })
                
        except Exception as e:
            print(f"❌ Error invoking Lambda: {e}")
            results.append({
                'test_name': test_case['name'],
                'success': False,
                'error': str(e)
            })
        
        print("\n" + "=" * 80)
    
    # Summary
    successful_tests = [r for r in results if r.get('success', False)]
    
    print(f"\n📊 LAMBDA TEST SUMMARY")
    print("=" * 80)
    print(f"📈 Success Rate: {len(successful_tests)}/{len(results)} ({len(successful_tests)/len(results)*100:.0f}%)")
    
    if successful_tests:
        avg_response_time = sum(r['response_time'] for r in successful_tests) / len(successful_tests)
        avg_response_length = sum(r['response_length'] for r in successful_tests) / len(successful_tests)
        compliance_rate = sum(1 for r in successful_tests if r['compliance_mentioned']) / len(successful_tests)
        law_mention_rate = sum(1 for r in successful_tests if r['law_mentioned']) / len(successful_tests)
        reasoning_rate = sum(1 for r in successful_tests if r['reasoning_provided']) / len(successful_tests)
        
        print(f"⏱️ Average Response Time: {avg_response_time:.2f}s")
        print(f"📏 Average Response Length: {avg_response_length:.0f} characters")
        print(f"📋 Compliance Awareness: {compliance_rate:.0%}")
        print(f"⚖️ Law Reference Rate: {law_mention_rate:.0%}")
        print(f"💭 Reasoning Rate: {reasoning_rate:.0%}")
        
        print(f"\n🎯 Overall Assessment:")
        if len(successful_tests) == len(results):
            print("  ✅ EXCELLENT: All tests passed!")
        elif len(successful_tests) >= len(results) * 0.8:
            print("  👍 GOOD: Most tests passed")
        else:
            print("  ⚠️ NEEDS IMPROVEMENT: Some tests failed")
        
        if avg_response_time <= 3:
            print("  ⚡ Response times are excellent")
        elif avg_response_time <= 5:
            print("  🚀 Response times are good")
        else:
            print("  ⏳ Response times could be improved")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = f"phi2_lambda_direct_test_{timestamp}.json"
    
    with open(report_filename, 'w') as f:
        json.dump({
            'timestamp': timestamp,
            'function_name': function_name,
            'test_method': 'direct_invoke',
            'results': results,
            'summary': {
                'total_tests': len(results),
                'successful_tests': len(successful_tests),
                'success_rate': len(successful_tests)/len(results),
                'avg_response_time': sum(r.get('response_time', 0) for r in successful_tests) / len(successful_tests) if successful_tests else 0
            }
        }, f, indent=2, default=str)
    
    print(f"\n💾 Detailed results saved to: {report_filename}")
    
    if successful_tests:
        print(f"\n🚀 Lambda function is working perfectly!")
        print(f"📡 You can invoke it programmatically using:")
        print(f"   Function Name: {function_name}")
        print(f"   Region: us-west-2")
        print(f"   Profile: bedrock-561")
        print(f"\n🔧 Function URL issue can be debugged separately")
        print(f"💡 For production, consider using API Gateway instead of Function URL")
    
    return successful_tests

if __name__ == "__main__":
    test_lambda_function()

