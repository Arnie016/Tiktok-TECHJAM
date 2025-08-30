#!/usr/bin/env python3
"""
Test script for Phi-2 v5 Lambda function with various compliance scenarios
"""

import requests
import json
import time
from datetime import datetime

class Phi2LambdaTester:
    def __init__(self, function_url=None, function_name=None):
        self.function_url = function_url
        self.function_name = function_name
        
        # Test cases for Lambda testing
        self.test_cases = [
            {
                "name": "GDPR Cookie Consent",
                "instruction": "Analyse the feature artifact and decide if geo-specific compliance logic is needed. Explain why and cite the relevant regulation if any.",
                "input": """Feature Name: EU Cookie Consent Banner
Feature Description: Display cookie consent banner for EU users accessing the website.

Law Context (structured JSON):
[{"law": "GDPR Article 7", "jurisdiction": "EU", "requirement": "Valid consent for data processing"}]""",
                "expected_compliance": True
            },
            {
                "name": "US CCPA Privacy Rights",
                "instruction": "Analyse the feature artifact and decide if geo-specific compliance logic is needed. Explain why and cite the relevant regulation if any.",
                "input": """Feature Name: California Do Not Sell Button
Feature Description: Button for California residents to opt-out of data sales.

Law Context (structured JSON):
[{"law": "CCPA Section 1798.135", "jurisdiction": "US-CA", "requirement": "Right to opt-out of sale"}]""",
                "expected_compliance": True
            },
            {
                "name": "Simple UI Feature - No Compliance",
                "instruction": "Analyse the feature artifact and decide if geo-specific compliance logic is needed. Explain why and cite the relevant regulation if any.",
                "input": """Feature Name: Dark Mode Toggle
Feature Description: UI toggle for switching between light and dark themes.

Law Context (structured JSON):
[]""",
                "expected_compliance": False
            },
            {
                "name": "Financial SOX Compliance",
                "instruction": "Analyse the feature artifact and decide if geo-specific compliance logic is needed. Explain why and cite the relevant regulation if any.",
                "input": """Feature Name: Financial Audit Logger
Feature Description: Logs financial transactions for compliance auditing.

Law Context (structured JSON):
[{"law": "SOX Section 404", "jurisdiction": "US", "requirement": "Internal controls over financial reporting"}]""",
                "expected_compliance": True
            }
        ]

    def test_via_function_url(self, test_case):
        """Test via Function URL (HTTP)"""
        if not self.function_url:
            return None, "No Function URL provided"
        
        try:
            payload = {
                "instruction": test_case["instruction"],
                "input": test_case["input"]
            }
            
            headers = {
                'Content-Type': 'application/json'
            }
            
            start_time = time.time()
            response = requests.post(
                self.function_url,
                json=payload,
                headers=headers,
                timeout=60
            )
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                return response.json(), response_time
            else:
                return None, f"HTTP {response.status_code}: {response.text}"
                
        except Exception as e:
            return None, f"Request error: {str(e)}"

    def test_via_lambda_invoke(self, test_case):
        """Test via direct Lambda invoke (boto3)"""
        if not self.function_name:
            return None, "No function name provided"
        
        try:
            import boto3
            session = boto3.Session(profile_name='bedrock-561', region_name='us-west-2')
            lambda_client = session.client('lambda')
            
            payload = {
                'httpMethod': 'POST',
                'body': json.dumps({
                    "instruction": test_case["instruction"],
                    "input": test_case["input"]
                })
            }
            
            start_time = time.time()
            response = lambda_client.invoke(
                FunctionName=self.function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            response_time = time.time() - start_time
            
            result = json.loads(response['Payload'].read().decode())
            
            if result.get('statusCode') == 200:
                body = json.loads(result.get('body', '{}'))
                return body, response_time
            else:
                return None, f"Lambda error: {result}"
                
        except Exception as e:
            return None, f"Lambda invoke error: {str(e)}"

    def analyze_response(self, response, test_case):
        """Analyze the response quality"""
        if not response or not response.get('success'):
            return {
                'quality_score': 0,
                'issues': ['Failed response or no success flag'],
                'strengths': []
            }
        
        analysis = response.get('analysis', {})
        generated_text = analysis.get('generated_text', '').lower()
        
        strengths = []
        issues = []
        score = 0
        
        # Check for compliance awareness
        if test_case.get('expected_compliance'):
            if any(word in generated_text for word in ['compliance', 'required', 'needed', 'necessary']):
                strengths.append("✅ Correctly identifies compliance need")
                score += 25
            else:
                issues.append("❌ Misses compliance requirement")
        else:
            if any(word in generated_text for word in ['no compliance', 'not required', 'not needed']):
                strengths.append("✅ Correctly identifies no compliance need")
                score += 25
            else:
                issues.append("❌ Incorrectly suggests compliance for simple feature")
        
        # Check for law references
        law_context = test_case['input'].lower()
        if 'gdpr' in law_context and 'gdpr' in generated_text:
            strengths.append("✅ Correctly references GDPR")
            score += 25
        elif 'ccpa' in law_context and 'ccpa' in generated_text:
            strengths.append("✅ Correctly references CCPA")
            score += 25
        elif 'sox' in law_context and 'sox' in generated_text:
            strengths.append("✅ Correctly references SOX")
            score += 25
        elif '[]' in law_context:
            # No laws provided - should not cite any
            if not any(law in generated_text for law in ['gdpr', 'ccpa', 'sox', 'hipaa']):
                strengths.append("✅ No law hallucination")
                score += 25
            else:
                issues.append("❌ Hallucinates laws not in context")
        
        # Check response quality
        if len(generated_text) > 30:
            strengths.append("✅ Adequate response length")
            score += 25
        else:
            issues.append("❌ Response too short")
        
        # Check for reasoning
        if any(word in generated_text for word in ['because', 'since', 'due to', 'therefore']):
            strengths.append("✅ Provides reasoning")
            score += 25
        else:
            issues.append("❌ Lacks clear reasoning")
        
        return {
            'quality_score': min(score, 100),
            'strengths': strengths,
            'issues': issues
        }

    def run_comprehensive_test(self):
        """Run comprehensive test suite"""
        print("🧪 Phi-2 v5 Lambda Function Comprehensive Test")
        print(f"🌐 Function URL: {self.function_url or 'Not provided'}")
        print(f"📡 Function Name: {self.function_name or 'Not provided'}")
        print("=" * 70)
        
        results = []
        
        for i, test_case in enumerate(self.test_cases, 1):
            print(f"\n🧪 Test {i}/{len(self.test_cases)}: {test_case['name']}")
            print("-" * 50)
            
            # Test via Function URL if available
            if self.function_url:
                print("🌐 Testing via Function URL...")
                response, response_time = self.test_via_function_url(test_case)
                
                if response:
                    print(f"✅ Function URL test successful ({response_time:.2f}s)")
                    
                    # Show response
                    analysis = response.get('analysis', {})
                    generated_text = analysis.get('generated_text', '')
                    print(f"\n📝 Generated Response:")
                    print("-" * 30)
                    print(generated_text[:300] + "..." if len(generated_text) > 300 else generated_text)
                    print("-" * 30)
                    
                    # Analyze quality
                    quality_analysis = self.analyze_response(response, test_case)
                    print(f"\n🔍 Quality Analysis:")
                    print(f"  📊 Quality Score: {quality_analysis['quality_score']}%")
                    
                    for strength in quality_analysis['strengths']:
                        print(f"  {strength}")
                    
                    for issue in quality_analysis['issues']:
                        print(f"  {issue}")
                    
                    results.append({
                        'test_case': test_case['name'],
                        'method': 'function_url',
                        'success': True,
                        'response_time': response_time,
                        'quality_score': quality_analysis['quality_score'],
                        'response': response
                    })
                    
                else:
                    print(f"❌ Function URL test failed: {response_time}")
                    results.append({
                        'test_case': test_case['name'],
                        'method': 'function_url',
                        'success': False,
                        'error': response_time
                    })
            
            # Test via Lambda invoke if available
            elif self.function_name:
                print("📡 Testing via Lambda invoke...")
                response, response_time = self.test_via_lambda_invoke(test_case)
                
                if response:
                    print(f"✅ Lambda invoke test successful ({response_time:.2f}s)")
                    
                    # Show response
                    analysis = response.get('analysis', {})
                    generated_text = analysis.get('generated_text', '')
                    print(f"\n📝 Generated Response:")
                    print("-" * 30)
                    print(generated_text[:300] + "..." if len(generated_text) > 300 else generated_text)
                    print("-" * 30)
                    
                    # Analyze quality
                    quality_analysis = self.analyze_response(response, test_case)
                    print(f"\n🔍 Quality Analysis:")
                    print(f"  📊 Quality Score: {quality_analysis['quality_score']}%")
                    
                    for strength in quality_analysis['strengths']:
                        print(f"  {strength}")
                    
                    for issue in quality_analysis['issues']:
                        print(f"  {issue}")
                    
                    results.append({
                        'test_case': test_case['name'],
                        'method': 'lambda_invoke',
                        'success': True,
                        'response_time': response_time,
                        'quality_score': quality_analysis['quality_score'],
                        'response': response
                    })
                    
                else:
                    print(f"❌ Lambda invoke test failed: {response_time}")
                    results.append({
                        'test_case': test_case['name'],
                        'method': 'lambda_invoke',
                        'success': False,
                        'error': response_time
                    })
            
            print("\n" + "=" * 70)
        
        return results

    def generate_test_report(self, results):
        """Generate comprehensive test report"""
        successful_results = [r for r in results if r.get('success', False)]
        
        print("\n📋 LAMBDA FUNCTION TEST REPORT")
        print("=" * 70)
        
        if not successful_results:
            print("❌ No successful tests to analyze!")
            return
        
        # Overall statistics
        total_tests = len(results)
        successful_tests = len(successful_results)
        avg_response_time = sum(r.get('response_time', 0) for r in successful_results) / len(successful_results)
        avg_quality_score = sum(r.get('quality_score', 0) for r in successful_results) / len(successful_results)
        
        print(f"📊 Test Summary:")
        print(f"  Total Tests: {total_tests}")
        print(f"  Successful Tests: {successful_tests}")
        print(f"  Success Rate: {successful_tests/total_tests:.0%}")
        print(f"  Average Response Time: {avg_response_time:.2f}s")
        print(f"  Average Quality Score: {avg_quality_score:.0f}%")
        
        # Test results by case
        print(f"\n📝 Individual Test Results:")
        for result in successful_results:
            score = result.get('quality_score', 0)
            time_taken = result.get('response_time', 0)
            print(f"  {result['test_case']}: {score}% ({time_taken:.2f}s)")
        
        # Overall assessment
        print(f"\n🎯 Overall Assessment:")
        if avg_quality_score >= 80:
            print("  🎉 EXCELLENT: Lambda function performs very well!")
        elif avg_quality_score >= 60:
            print("  👍 GOOD: Lambda function shows solid performance")
        elif avg_quality_score >= 40:
            print("  ⚠️ MODERATE: Lambda function needs improvement")
        else:
            print("  🚨 POOR: Lambda function has significant issues")
        
        if avg_response_time <= 5:
            print("  ⚡ Response times are excellent")
        elif avg_response_time <= 10:
            print("  🚀 Response times are good")
        else:
            print("  ⏳ Response times could be improved")
        
        return {
            'success_rate': successful_tests/total_tests,
            'avg_response_time': avg_response_time,
            'avg_quality_score': avg_quality_score
        }

def main():
    """Main function"""
    print("🧪 Phi-2 v5 Lambda Function Testing")
    print("Tests both Function URL and direct Lambda invoke methods")
    print("=" * 70)
    
    # Get test parameters
    function_url = input("🌐 Enter Function URL (or press Enter to skip): ").strip()
    function_name = input("📡 Enter Function Name (or press Enter to skip): ").strip()
    
    if not function_url and not function_name:
        print("❌ Please provide either Function URL or Function Name")
        return
    
    # Run tests
    tester = Phi2LambdaTester(
        function_url=function_url if function_url else None,
        function_name=function_name if function_name else None
    )
    
    results = tester.run_comprehensive_test()
    summary = tester.generate_test_report(results)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = f"phi2_lambda_test_report_{timestamp}.json"
    
    with open(report_filename, 'w') as f:
        json.dump({
            'timestamp': timestamp,
            'function_url': function_url,
            'function_name': function_name,
            'summary': summary,
            'detailed_results': results
        }, f, indent=2, default=str)
    
    print(f"\n💾 Detailed results saved to: {report_filename}")
    print("🎉 Lambda testing completed!")

if __name__ == "__main__":
    main()

