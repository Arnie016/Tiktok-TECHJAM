#!/usr/bin/env python3
"""
Comprehensive test script for Phi-2 v5 jurisdiction awareness and law citation accuracy
Tests for jurisdiction mixups, prompt following, and compliance logic
"""

import boto3
import json
import time
from datetime import datetime
import re

class JurisdictionTester:
    def __init__(self, endpoint_name='phi2-v5-inference'):
        # Setup client
        session = boto3.Session(profile_name='bedrock-561', region_name='us-west-2')
        self.sagemaker_runtime = session.client('sagemaker-runtime')
        self.endpoint_name = endpoint_name
        
        # Test cases designed to catch jurisdiction mixups
        self.test_cases = [
            {
                "id": "EU_GDPR_PURE",
                "name": "Pure EU GDPR Case",
                "instruction": "Analyse the feature artifact and decide if geo-specific compliance logic is needed. Explain why and cite the relevant regulation if any.",
                "input": """Feature Name: EU Cookie Consent Banner
Feature Description: Display cookie consent banner for EU users accessing the website, with options to accept or reject non-essential cookies.

Law Context (structured JSON):
[{"law": "GDPR Article 7", "jurisdiction": "EU", "requirement": "Valid consent for data processing"}]""",
                "expected_jurisdiction": ["EU"],
                "expected_laws": ["GDPR", "Article 7"],
                "should_need_compliance": True
            },
            {
                "id": "US_CCPA_PURE", 
                "name": "Pure US CCPA Case",
                "instruction": "Analyse the feature artifact and decide if geo-specific compliance logic is needed. Explain why and cite the relevant regulation if any.",
                "input": """Feature Name: California Do Not Sell Button
Feature Description: Provides California residents with a button to opt-out of personal information sales as required by state law.

Law Context (structured JSON):
[{"law": "CCPA Section 1798.135", "jurisdiction": "US-CA", "requirement": "Right to opt-out of sale of personal information"}]""",
                "expected_jurisdiction": ["US", "CA", "California"],
                "expected_laws": ["CCPA", "1798.135"],
                "should_need_compliance": True
            },
            {
                "id": "MIXED_JURISDICTION_TRAP",
                "name": "Mixed Jurisdiction Trap Test",
                "instruction": "Analyse the feature artifact and decide if geo-specific compliance logic is needed. Explain why and cite the relevant regulation if any.",
                "input": """Feature Name: Global User Registration
Feature Description: Standard user registration form collecting name, email, and basic preferences for global users.

Law Context (structured JSON):
[{"law": "GDPR Article 6", "jurisdiction": "EU", "requirement": "Lawful basis for processing"}, {"law": "CCPA Section 1798.100", "jurisdiction": "US-CA", "requirement": "Right to know about personal information"}]""",
                "expected_jurisdiction": ["EU", "US", "CA"],
                "expected_laws": ["GDPR", "CCPA", "Article 6", "1798.100"],
                "should_need_compliance": True
            },
            {
                "id": "NO_LAW_CONTEXT_TRAP",
                "name": "No Law Context - Should Say No Compliance",
                "instruction": "Analyse the feature artifact and decide if geo-specific compliance logic is needed. Explain why and cite the relevant regulation if any.",
                "input": """Feature Name: Dark Mode Toggle
Feature Description: Simple UI toggle allowing users to switch between light and dark themes for better user experience.

Law Context (structured JSON):
[]""",
                "expected_jurisdiction": [],
                "expected_laws": [],
                "should_need_compliance": False
            },
            {
                "id": "WRONG_JURISDICTION_TRAP",
                "name": "Wrong Jurisdiction Trap - Should Only Reference Provided Laws",
                "instruction": "Analyse the feature artifact and decide if geo-specific compliance logic is needed. Explain why and cite the relevant regulation if any.",
                "input": """Feature Name: Employee Payroll System
Feature Description: Internal system for processing employee salaries and tax withholdings for Canadian employees.

Law Context (structured JSON):
[{"law": "Privacy Act Section 8", "jurisdiction": "CA", "requirement": "Protection of personal information"}]""",
                "expected_jurisdiction": ["CA", "Canada"],
                "expected_laws": ["Privacy Act", "Section 8"],
                "should_need_compliance": True,
                "forbidden_laws": ["GDPR", "CCPA", "SOX"]  # Should not cite these
            },
            {
                "id": "FINANCIAL_SOX_TEST",
                "name": "US Financial SOX Compliance",
                "instruction": "Analyse the feature artifact and decide if geo-specific compliance logic is needed. Explain why and cite the relevant regulation if any.",
                "input": """Feature Name: Financial Audit Trail Logger
Feature Description: Logs all financial transactions and database changes for compliance auditing in US public companies.

Law Context (structured JSON):
[{"law": "SOX Section 404", "jurisdiction": "US", "requirement": "Internal controls over financial reporting"}]""",
                "expected_jurisdiction": ["US"],
                "expected_laws": ["SOX", "Section 404", "Sarbanes-Oxley"],
                "should_need_compliance": True
            },
            {
                "id": "HALLUCINATION_TRAP",
                "name": "Hallucination Test - Empty Context Should Not Invent Laws",
                "instruction": "Analyse the feature artifact and decide if geo-specific compliance logic is needed. Explain why and cite the relevant regulation if any.",
                "input": """Feature Name: Weather Widget
Feature Description: Displays current weather information based on user's location for better user experience.

Law Context (structured JSON):
[]""",
                "expected_jurisdiction": [],
                "expected_laws": [],
                "should_need_compliance": False,
                "forbidden_laws": ["GDPR", "CCPA", "SOX", "HIPAA", "PCI-DSS"]  # Should not hallucinate these
            }
        ]

    def invoke_model(self, instruction, input_text):
        """Invoke the model with given instruction and input"""
        try:
            payload = {
                "instruction": instruction,
                "input": input_text
            }
            
            response = self.sagemaker_runtime.invoke_endpoint(
                EndpointName=self.endpoint_name,
                ContentType='application/json',
                Body=json.dumps(payload)
            )
            
            result = json.loads(response['Body'].read().decode())
            return result.get('generated_text', ''), True
            
        except Exception as e:
            return f"ERROR: {str(e)}", False

    def analyze_response(self, response_text, test_case):
        """Analyze response for jurisdiction awareness, law citation accuracy, and compliance logic"""
        response_lower = response_text.lower()
        
        analysis = {
            "prompt_following": False,
            "jurisdiction_accuracy": 0,
            "law_citation_accuracy": 0,
            "compliance_logic_correct": False,
            "hallucination_detected": False,
            "mentioned_jurisdictions": [],
            "mentioned_laws": [],
            "forbidden_law_violations": [],
            "reasoning": []
        }
        
        # Check prompt following - should analyze and decide
        if any(word in response_lower for word in ['compliance', 'required', 'needed', 'necessary', 'analyze', 'decision']):
            analysis["prompt_following"] = True
            analysis["reasoning"].append("✅ Follows prompt structure")
        else:
            analysis["reasoning"].append("❌ Does not follow prompt structure")
        
        # Check jurisdiction accuracy
        expected_jurisdictions = test_case.get("expected_jurisdiction", [])
        for jurisdiction in expected_jurisdictions:
            if jurisdiction.lower() in response_lower:
                analysis["mentioned_jurisdictions"].append(jurisdiction)
        
        if expected_jurisdictions:
            analysis["jurisdiction_accuracy"] = len(analysis["mentioned_jurisdictions"]) / len(expected_jurisdictions)
        else:
            # For no-jurisdiction cases, accuracy is 1 if no jurisdictions mentioned
            analysis["jurisdiction_accuracy"] = 1.0 if not analysis["mentioned_jurisdictions"] else 0.0
            
        # Check law citation accuracy
        expected_laws = test_case.get("expected_laws", [])
        for law in expected_laws:
            if law.lower() in response_lower:
                analysis["mentioned_laws"].append(law)
        
        if expected_laws:
            analysis["law_citation_accuracy"] = len(analysis["mentioned_laws"]) / len(expected_laws)
        else:
            # For no-law cases, accuracy is 1 if no laws mentioned
            analysis["law_citation_accuracy"] = 1.0 if not analysis["mentioned_laws"] else 0.0
        
        # Check for forbidden law hallucinations
        forbidden_laws = test_case.get("forbidden_laws", [])
        for forbidden_law in forbidden_laws:
            if forbidden_law.lower() in response_lower:
                analysis["forbidden_law_violations"].append(forbidden_law)
                analysis["hallucination_detected"] = True
        
        # Check compliance logic correctness
        should_need_compliance = test_case.get("should_need_compliance", False)
        
        compliance_indicators = ["compliance required", "compliance needed", "compliance logic", "geo-specific", "must comply"]
        no_compliance_indicators = ["no compliance", "not required", "no geo-specific", "not needed", "n/a"]
        
        has_compliance_language = any(indicator in response_lower for indicator in compliance_indicators)
        has_no_compliance_language = any(indicator in response_lower for indicator in no_compliance_indicators)
        
        if should_need_compliance and has_compliance_language:
            analysis["compliance_logic_correct"] = True
            analysis["reasoning"].append("✅ Correctly identifies compliance need")
        elif not should_need_compliance and has_no_compliance_language:
            analysis["compliance_logic_correct"] = True
            analysis["reasoning"].append("✅ Correctly identifies no compliance need")
        else:
            analysis["reasoning"].append("❌ Incorrect compliance logic")
        
        return analysis

    def run_comprehensive_test(self):
        """Run all test cases and generate comprehensive report"""
        print("🎯 Phi-2 v5 Comprehensive Jurisdiction & Law Citation Test")
        print(f"📡 Endpoint: {self.endpoint_name}")
        print("🔍 Testing: Jurisdiction awareness, law citation accuracy, prompt following")
        print("⚠️ Looking for: Jurisdiction mixups, law hallucinations, compliance logic errors")
        print("=" * 80)
        
        results = []
        
        for i, test_case in enumerate(self.test_cases, 1):
            print(f"\n🧪 Test {i}/{len(self.test_cases)}: {test_case['name']}")
            print("-" * 60)
            print(f"📝 ID: {test_case['id']}")
            print(f"🎯 Expected Jurisdictions: {test_case.get('expected_jurisdiction', [])}")
            print(f"⚖️ Expected Laws: {test_case.get('expected_laws', [])}")
            print(f"🚨 Forbidden Laws: {test_case.get('forbidden_laws', [])}")
            
            # Invoke model
            start_time = time.time()
            response_text, success = self.invoke_model(test_case["instruction"], test_case["input"])
            response_time = time.time() - start_time
            
            if success:
                print(f"⏱️ Response Time: {response_time:.2f}s")
                print(f"\n📤 Model Response:")
                print("-" * 30)
                print(response_text)
                print("-" * 30)
                
                # Analyze response
                analysis = self.analyze_response(response_text, test_case)
                
                print(f"\n🔍 Analysis Results:")
                print(f"  📋 Prompt Following: {'✅' if analysis['prompt_following'] else '❌'}")
                print(f"  🌍 Jurisdiction Accuracy: {analysis['jurisdiction_accuracy']:.0%}")
                print(f"  ⚖️ Law Citation Accuracy: {analysis['law_citation_accuracy']:.0%}")
                print(f"  🎯 Compliance Logic: {'✅' if analysis['compliance_logic_correct'] else '❌'}")
                print(f"  🚨 Hallucination Detected: {'❌' if analysis['hallucination_detected'] else '✅'}")
                
                if analysis["mentioned_jurisdictions"]:
                    print(f"  🌍 Found Jurisdictions: {analysis['mentioned_jurisdictions']}")
                if analysis["mentioned_laws"]:
                    print(f"  ⚖️ Found Laws: {analysis['mentioned_laws']}")
                if analysis["forbidden_law_violations"]:
                    print(f"  🚨 VIOLATION - Forbidden Laws: {analysis['forbidden_law_violations']}")
                
                print(f"  💭 Reasoning:")
                for reason in analysis["reasoning"]:
                    print(f"    {reason}")
                
                # Calculate overall score
                overall_score = (
                    (1 if analysis['prompt_following'] else 0) +
                    analysis['jurisdiction_accuracy'] +
                    analysis['law_citation_accuracy'] +
                    (1 if analysis['compliance_logic_correct'] else 0) +
                    (1 if not analysis['hallucination_detected'] else 0)
                ) / 5 * 100
                
                print(f"\n📊 Overall Score: {overall_score:.0f}%")
                
                # Store results
                results.append({
                    "test_case": test_case,
                    "response_text": response_text,
                    "response_time": response_time,
                    "analysis": analysis,
                    "overall_score": overall_score,
                    "success": True
                })
                
            else:
                print(f"❌ Model invocation failed: {response_text}")
                results.append({
                    "test_case": test_case,
                    "response_text": response_text,
                    "response_time": 0,
                    "analysis": None,
                    "overall_score": 0,
                    "success": False
                })
            
            print("\n" + "=" * 80)
        
        return results

    def generate_report(self, results):
        """Generate comprehensive analysis report"""
        successful_results = [r for r in results if r['success']]
        
        if not successful_results:
            print("\n❌ No successful tests to analyze!")
            return
        
        print("\n📋 COMPREHENSIVE ANALYSIS REPORT")
        print("=" * 80)
        
        # Overall statistics
        total_tests = len(results)
        successful_tests = len(successful_results)
        avg_response_time = sum(r['response_time'] for r in successful_results) / len(successful_results)
        avg_overall_score = sum(r['overall_score'] for r in successful_results) / len(successful_results)
        
        print(f"📊 Test Summary:")
        print(f"  Total Tests: {total_tests}")
        print(f"  Successful Tests: {successful_tests}")
        print(f"  Success Rate: {successful_tests/total_tests:.0%}")
        print(f"  Average Response Time: {avg_response_time:.2f}s")
        print(f"  Average Overall Score: {avg_overall_score:.0f}%")
        
        # Detailed analysis
        prompt_following_rate = sum(1 for r in successful_results if r['analysis']['prompt_following']) / len(successful_results)
        avg_jurisdiction_accuracy = sum(r['analysis']['jurisdiction_accuracy'] for r in successful_results) / len(successful_results)
        avg_law_citation_accuracy = sum(r['analysis']['law_citation_accuracy'] for r in successful_results) / len(successful_results)
        compliance_logic_rate = sum(1 for r in successful_results if r['analysis']['compliance_logic_correct']) / len(successful_results)
        hallucination_rate = sum(1 for r in successful_results if r['analysis']['hallucination_detected']) / len(successful_results)
        
        print(f"\n🎯 Performance Metrics:")
        print(f"  📋 Prompt Following Rate: {prompt_following_rate:.0%}")
        print(f"  🌍 Jurisdiction Accuracy: {avg_jurisdiction_accuracy:.0%}")
        print(f"  ⚖️ Law Citation Accuracy: {avg_law_citation_accuracy:.0%}")
        print(f"  🎯 Compliance Logic Accuracy: {compliance_logic_rate:.0%}")
        print(f"  🚨 Hallucination Rate: {hallucination_rate:.0%} (lower is better)")
        
        # Critical issues
        print(f"\n🚨 Critical Issues Detected:")
        critical_issues = []
        
        for result in successful_results:
            if result['analysis']['hallucination_detected']:
                critical_issues.append(f"  ❌ {result['test_case']['name']}: Law hallucination - {result['analysis']['forbidden_law_violations']}")
            
            if not result['analysis']['compliance_logic_correct']:
                critical_issues.append(f"  ❌ {result['test_case']['name']}: Incorrect compliance logic")
            
            if result['analysis']['jurisdiction_accuracy'] < 0.5:
                critical_issues.append(f"  ❌ {result['test_case']['name']}: Poor jurisdiction awareness")
        
        if critical_issues:
            for issue in critical_issues:
                print(issue)
        else:
            print("  ✅ No critical issues detected!")
        
        # Recommendations
        print(f"\n💡 Recommendations:")
        if avg_overall_score >= 90:
            print("  🎉 EXCELLENT: Model shows outstanding jurisdiction and law awareness!")
            print("  🚀 Ready for production deployment")
        elif avg_overall_score >= 75:
            print("  👍 GOOD: Model shows solid performance with minor areas for improvement")
            print("  🔧 Consider additional training on edge cases")
        elif avg_overall_score >= 60:
            print("  ⚠️ MODERATE: Model needs improvement in jurisdiction awareness")
            print("  📚 Recommend additional training with jurisdiction-specific examples")
        else:
            print("  🚨 POOR: Model has significant issues with jurisdiction and law awareness")
            print("  🔄 Requires substantial retraining with better data")
        
        if hallucination_rate > 0.2:
            print("  🚨 HIGH PRIORITY: Address law hallucination issues")
        
        if avg_jurisdiction_accuracy < 0.7:
            print("  🌍 Focus training on jurisdiction-specific scenarios")
        
        if compliance_logic_rate < 0.8:
            print("  🎯 Improve compliance decision-making logic")
        
        return {
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "avg_overall_score": avg_overall_score,
            "prompt_following_rate": prompt_following_rate,
            "avg_jurisdiction_accuracy": avg_jurisdiction_accuracy,
            "avg_law_citation_accuracy": avg_law_citation_accuracy,
            "compliance_logic_rate": compliance_logic_rate,
            "hallucination_rate": hallucination_rate,
            "critical_issues": len(critical_issues)
        }

def main():
    """Main function"""
    print("🎯 Phi-2 v5 Comprehensive Jurisdiction & Law Citation Testing")
    print("Testing for jurisdiction mixups, law hallucinations, and compliance accuracy")
    print("=" * 80)
    
    tester = JurisdictionTester()
    
    # Run tests
    results = tester.run_comprehensive_test()
    
    # Generate report
    report_summary = tester.generate_report(results)
    
    # Save detailed results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = f"phi2_v5_jurisdiction_test_report_{timestamp}.json"
    
    with open(report_filename, 'w') as f:
        json.dump({
            "timestamp": timestamp,
            "endpoint": "phi2-v5-inference",
            "summary": report_summary,
            "detailed_results": results
        }, f, indent=2, default=str)
    
    print(f"\n💾 Detailed results saved to: {report_filename}")
    print("🎉 Comprehensive testing completed!")

if __name__ == "__main__":
    main()
