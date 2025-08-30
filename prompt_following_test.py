#!/usr/bin/env python3
"""
Focused test script for Phi-2 v5 prompt following and instruction adherence
Tests specific response format, decision-making clarity, and instruction compliance
"""

import boto3
import json
import time
from datetime import datetime
import re

class PromptFollowingTester:
    def __init__(self, endpoint_name='phi2-v5-inference'):
        # Setup client
        session = boto3.Session(profile_name='bedrock-561', region_name='us-west-2')
        self.sagemaker_runtime = session.client('sagemaker-runtime')
        self.endpoint_name = endpoint_name
        
        # Specific prompt following test cases
        self.test_cases = [
            {
                "id": "EXPLICIT_FORMAT_REQUEST",
                "name": "Explicit JSON Format Request",
                "instruction": "Analyse the feature and respond in JSON format with fields: compliance_flag, law, reason, jurisdiction.",
                "input": """Feature Name: GDPR Cookie Banner
Feature Description: Shows cookie consent for EU users.

Law Context (structured JSON):
[{"law": "GDPR Article 7", "jurisdiction": "EU", "requirement": "Valid consent"}]""",
                "expected_format": "JSON",
                "required_fields": ["compliance_flag", "law", "reason", "jurisdiction"]
            },
            {
                "id": "STEP_BY_STEP_REQUEST",
                "name": "Step-by-Step Analysis Request",
                "instruction": "Analyse this feature step by step: 1) Identify applicable laws, 2) Determine jurisdiction requirements, 3) Make compliance decision, 4) Provide reasoning.",
                "input": """Feature Name: California Privacy Rights Button
Feature Description: Opt-out button for California residents.

Law Context (structured JSON):
[{"law": "CCPA Section 1798.135", "jurisdiction": "US-CA", "requirement": "Right to opt-out"}]""",
                "expected_structure": ["step 1", "step 2", "step 3", "step 4", "applicable laws", "jurisdiction", "compliance", "reasoning"]
            },
            {
                "id": "YES_NO_QUESTION",
                "name": "Direct Yes/No Question",
                "instruction": "Does this feature require geo-specific compliance logic? Answer YES or NO, then explain why.",
                "input": """Feature Name: Weather Widget
Feature Description: Shows weather based on location.

Law Context (structured JSON):
[]""",
                "expected_start": ["yes", "no"],
                "required_explanation": True
            },
            {
                "id": "CITATION_SPECIFIC_REQUEST",
                "name": "Specific Citation Format Request",
                "instruction": "Cite only the laws provided in the Law Context. Do not reference any laws not explicitly listed.",
                "input": """Feature Name: Health Data Processor
Feature Description: Processes patient health records.

Law Context (structured JSON):
[{"law": "HIPAA Privacy Rule", "jurisdiction": "US", "requirement": "PHI protection"}]""",
                "forbidden_citations": ["GDPR", "CCPA", "SOX", "PCI-DSS"],
                "required_citations": ["HIPAA"]
            },
            {
                "id": "EMPTY_CONTEXT_HANDLING",
                "name": "Empty Context Handling",
                "instruction": "If no laws are provided in the Law Context, clearly state that no specific compliance requirements are identified.",
                "input": """Feature Name: Color Theme Selector
Feature Description: User can choose app color theme.

Law Context (structured JSON):
[]""",
                "expected_phrases": ["no laws", "no specific compliance", "no requirements identified", "empty context"],
                "forbidden_citations": ["GDPR", "CCPA", "SOX", "HIPAA", "PCI-DSS"]
            },
            {
                "id": "MULTI_JURISDICTION_HANDLING",
                "name": "Multi-Jurisdiction Handling",
                "instruction": "When multiple jurisdictions are involved, address each jurisdiction separately and clearly distinguish requirements.",
                "input": """Feature Name: Global Data Transfer System
Feature Description: Transfers user data between US and EU servers.

Law Context (structured JSON):
[{"law": "GDPR Article 44", "jurisdiction": "EU", "requirement": "Adequate protection for transfers"}, {"law": "CCPA Section 1798.145", "jurisdiction": "US-CA", "requirement": "Service provider agreements"}]""",
                "expected_jurisdictions": ["EU", "US-CA"],
                "expected_separation": True
            },
            {
                "id": "REASONING_DEPTH_TEST",
                "name": "Reasoning Depth Test",
                "instruction": "Provide detailed reasoning for your compliance decision, including why the specific law applies and what compliance measures would be needed.",
                "input": """Feature Name: Employee Performance Tracker
Feature Description: Tracks employee productivity metrics and generates reports for managers.

Law Context (structured JSON):
[{"law": "EU Privacy Directive Article 88", "jurisdiction": "EU", "requirement": "Employee data protection safeguards"}]""",
                "expected_depth_indicators": ["because", "therefore", "specifically", "measures needed", "applies because", "required due to"]
            },
            {
                "id": "CONFIDENCE_LEVEL_TEST",
                "name": "Confidence and Uncertainty Handling",
                "instruction": "If you are uncertain about compliance requirements, clearly state your uncertainty and suggest consulting legal experts.",
                "input": """Feature Name: Quantum Computing Research Data
Feature Description: Stores quantum computing research results with international collaboration data.

Law Context (structured JSON):
[{"law": "Export Administration Regulations", "jurisdiction": "US", "requirement": "Technology transfer controls"}]""",
                "expected_uncertainty_phrases": ["uncertain", "unclear", "consult legal", "legal expert", "may require", "should verify"]
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

    def analyze_prompt_following(self, response_text, test_case):
        """Analyze how well the response follows the specific prompt instructions"""
        response_lower = response_text.lower()
        
        analysis = {
            "format_compliance": False,
            "structure_compliance": False,
            "content_compliance": False,
            "instruction_following_score": 0,
            "detected_issues": [],
            "positive_indicators": [],
            "overall_score": 0
        }
        
        test_id = test_case["id"]
        
        if test_id == "EXPLICIT_FORMAT_REQUEST":
            # Check for JSON format
            try:
                json.loads(response_text)
                analysis["format_compliance"] = True
                analysis["positive_indicators"].append("✅ Valid JSON format")
            except:
                if any(indicator in response_lower for indicator in ["{", "}", "compliance_flag", "law", "reason"]):
                    analysis["format_compliance"] = True
                    analysis["positive_indicators"].append("✅ Attempts JSON-like structure")
                else:
                    analysis["detected_issues"].append("❌ No JSON format detected")
            
            # Check for required fields
            required_fields = test_case.get("required_fields", [])
            found_fields = sum(1 for field in required_fields if field in response_lower)
            field_score = found_fields / len(required_fields) if required_fields else 1
            analysis["content_compliance"] = field_score > 0.5
            analysis["positive_indicators"].append(f"✅ Found {found_fields}/{len(required_fields)} required fields")
        
        elif test_id == "STEP_BY_STEP_REQUEST":
            # Check for step-by-step structure
            step_indicators = ["step", "1)", "2)", "3)", "4)", "first", "second", "third", "fourth"]
            found_steps = sum(1 for indicator in step_indicators if indicator in response_lower)
            analysis["structure_compliance"] = found_steps >= 2
            
            expected_content = test_case.get("expected_structure", [])
            found_content = sum(1 for content in expected_content if content in response_lower)
            content_score = found_content / len(expected_content) if expected_content else 1
            analysis["content_compliance"] = content_score > 0.3
            
            if analysis["structure_compliance"]:
                analysis["positive_indicators"].append("✅ Step-by-step structure detected")
            else:
                analysis["detected_issues"].append("❌ No clear step structure")
        
        elif test_id == "YES_NO_QUESTION":
            # Check for direct Yes/No answer
            expected_starts = test_case.get("expected_start", [])
            starts_correctly = any(response_lower.strip().startswith(start) for start in expected_starts)
            analysis["format_compliance"] = starts_correctly
            
            # Check for explanation
            explanation_indicators = ["because", "since", "due to", "reason", "explain"]
            has_explanation = any(indicator in response_lower for indicator in explanation_indicators)
            analysis["content_compliance"] = has_explanation
            
            if starts_correctly:
                analysis["positive_indicators"].append("✅ Direct Yes/No answer provided")
            if has_explanation:
                analysis["positive_indicators"].append("✅ Explanation provided")
        
        elif test_id == "CITATION_SPECIFIC_REQUEST":
            # Check for forbidden citations
            forbidden = test_case.get("forbidden_citations", [])
            violations = [law for law in forbidden if law.lower() in response_lower]
            
            # Check for required citations
            required = test_case.get("required_citations", [])
            found_required = [law for law in required if law.lower() in response_lower]
            
            analysis["content_compliance"] = len(violations) == 0 and len(found_required) > 0
            
            if violations:
                analysis["detected_issues"].append(f"❌ Cited forbidden laws: {violations}")
            if found_required:
                analysis["positive_indicators"].append(f"✅ Correctly cited: {found_required}")
        
        elif test_id == "EMPTY_CONTEXT_HANDLING":
            # Check for appropriate empty context handling
            expected_phrases = test_case.get("expected_phrases", [])
            found_phrases = [phrase for phrase in expected_phrases if phrase in response_lower]
            
            forbidden = test_case.get("forbidden_citations", [])
            violations = [law for law in forbidden if law.lower() in response_lower]
            
            analysis["content_compliance"] = len(found_phrases) > 0 and len(violations) == 0
            
            if found_phrases:
                analysis["positive_indicators"].append(f"✅ Appropriate empty context handling: {found_phrases}")
            if violations:
                analysis["detected_issues"].append(f"❌ Hallucinated laws: {violations}")
        
        elif test_id == "MULTI_JURISDICTION_HANDLING":
            # Check for jurisdiction separation
            expected_jurisdictions = test_case.get("expected_jurisdictions", [])
            found_jurisdictions = [jur for jur in expected_jurisdictions if jur.lower() in response_lower]
            
            # Check for separation indicators
            separation_indicators = ["separately", "respectively", "each jurisdiction", "eu:", "us:", "california:"]
            has_separation = any(indicator in response_lower for indicator in separation_indicators)
            
            analysis["structure_compliance"] = has_separation
            analysis["content_compliance"] = len(found_jurisdictions) == len(expected_jurisdictions)
            
            if has_separation:
                analysis["positive_indicators"].append("✅ Addresses jurisdictions separately")
            if found_jurisdictions:
                analysis["positive_indicators"].append(f"✅ Found jurisdictions: {found_jurisdictions}")
        
        elif test_id == "REASONING_DEPTH_TEST":
            # Check for reasoning depth
            depth_indicators = test_case.get("expected_depth_indicators", [])
            found_indicators = [ind for ind in depth_indicators if ind in response_lower]
            
            word_count = len(response_text.split())
            has_depth = len(found_indicators) >= 2 and word_count > 50
            
            analysis["content_compliance"] = has_depth
            
            if has_depth:
                analysis["positive_indicators"].append(f"✅ Detailed reasoning with {len(found_indicators)} depth indicators")
            else:
                analysis["detected_issues"].append("❌ Shallow reasoning provided")
        
        elif test_id == "CONFIDENCE_LEVEL_TEST":
            # Check for appropriate uncertainty handling
            uncertainty_phrases = test_case.get("expected_uncertainty_phrases", [])
            found_uncertainty = [phrase for phrase in uncertainty_phrases if phrase in response_lower]
            
            analysis["content_compliance"] = len(found_uncertainty) > 0
            
            if found_uncertainty:
                analysis["positive_indicators"].append(f"✅ Appropriate uncertainty handling: {found_uncertainty}")
            else:
                analysis["detected_issues"].append("❌ No uncertainty acknowledgment")
        
        # Calculate overall instruction following score
        scores = [
            1 if analysis["format_compliance"] else 0,
            1 if analysis["structure_compliance"] else 0,
            1 if analysis["content_compliance"] else 0
        ]
        analysis["instruction_following_score"] = sum(scores) / len(scores)
        analysis["overall_score"] = analysis["instruction_following_score"] * 100
        
        return analysis

    def run_prompt_following_test(self):
        """Run all prompt following test cases"""
        print("📋 Phi-2 v5 Prompt Following & Instruction Adherence Test")
        print(f"📡 Endpoint: {self.endpoint_name}")
        print("🎯 Testing: Format compliance, structure following, instruction adherence")
        print("=" * 80)
        
        results = []
        
        for i, test_case in enumerate(self.test_cases, 1):
            print(f"\n📝 Test {i}/{len(self.test_cases)}: {test_case['name']}")
            print("-" * 60)
            print(f"🆔 ID: {test_case['id']}")
            print(f"📋 Instruction: {test_case['instruction'][:100]}...")
            
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
                
                # Analyze prompt following
                analysis = self.analyze_prompt_following(response_text, test_case)
                
                print(f"\n🔍 Prompt Following Analysis:")
                print(f"  📋 Format Compliance: {'✅' if analysis['format_compliance'] else '❌'}")
                print(f"  🏗️ Structure Compliance: {'✅' if analysis['structure_compliance'] else '❌'}")
                print(f"  📝 Content Compliance: {'✅' if analysis['content_compliance'] else '❌'}")
                print(f"  📊 Instruction Following Score: {analysis['instruction_following_score']:.0%}")
                
                print(f"\n✅ Positive Indicators:")
                for indicator in analysis["positive_indicators"]:
                    print(f"    {indicator}")
                
                if analysis["detected_issues"]:
                    print(f"\n❌ Issues Detected:")
                    for issue in analysis["detected_issues"]:
                        print(f"    {issue}")
                
                print(f"\n📊 Overall Score: {analysis['overall_score']:.0f}%")
                
                # Store results
                results.append({
                    "test_case": test_case,
                    "response_text": response_text,
                    "response_time": response_time,
                    "analysis": analysis,
                    "success": True
                })
                
            else:
                print(f"❌ Model invocation failed: {response_text}")
                results.append({
                    "test_case": test_case,
                    "response_text": response_text,
                    "response_time": 0,
                    "analysis": None,
                    "success": False
                })
            
            print("\n" + "=" * 80)
        
        return results

    def generate_prompt_following_report(self, results):
        """Generate detailed prompt following report"""
        successful_results = [r for r in results if r['success']]
        
        if not successful_results:
            print("\n❌ No successful tests to analyze!")
            return
        
        print("\n📋 PROMPT FOLLOWING ANALYSIS REPORT")
        print("=" * 80)
        
        # Overall statistics
        total_tests = len(results)
        successful_tests = len(successful_results)
        avg_response_time = sum(r['response_time'] for r in successful_results) / len(successful_results)
        avg_instruction_score = sum(r['analysis']['instruction_following_score'] for r in successful_results) / len(successful_results)
        
        print(f"📊 Test Summary:")
        print(f"  Total Tests: {total_tests}")
        print(f"  Successful Tests: {successful_tests}")
        print(f"  Success Rate: {successful_tests/total_tests:.0%}")
        print(f"  Average Response Time: {avg_response_time:.2f}s")
        print(f"  Average Instruction Following Score: {avg_instruction_score:.0%}")
        
        # Detailed analysis by category
        format_compliance_rate = sum(1 for r in successful_results if r['analysis']['format_compliance']) / len(successful_results)
        structure_compliance_rate = sum(1 for r in successful_results if r['analysis']['structure_compliance']) / len(successful_results)
        content_compliance_rate = sum(1 for r in successful_results if r['analysis']['content_compliance']) / len(successful_results)
        
        print(f"\n🎯 Compliance Metrics:")
        print(f"  📋 Format Compliance Rate: {format_compliance_rate:.0%}")
        print(f"  🏗️ Structure Compliance Rate: {structure_compliance_rate:.0%}")
        print(f"  📝 Content Compliance Rate: {content_compliance_rate:.0%}")
        
        # Test-specific analysis
        print(f"\n📝 Test-Specific Results:")
        for result in successful_results:
            test_name = result['test_case']['name']
            score = result['analysis']['overall_score']
            print(f"  {test_name}: {score:.0f}%")
        
        # Issues summary
        all_issues = []
        for result in successful_results:
            all_issues.extend(result['analysis']['detected_issues'])
        
        if all_issues:
            print(f"\n🚨 Common Issues:")
            issue_counts = {}
            for issue in all_issues:
                issue_type = issue.split(':')[0].strip()
                issue_counts[issue_type] = issue_counts.get(issue_type, 0) + 1
            
            for issue_type, count in sorted(issue_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"  {issue_type}: {count} occurrences")
        
        # Recommendations
        print(f"\n💡 Recommendations:")
        if avg_instruction_score >= 0.9:
            print("  🎉 EXCELLENT: Model shows outstanding prompt following capabilities!")
        elif avg_instruction_score >= 0.75:
            print("  👍 GOOD: Model generally follows instructions well")
        elif avg_instruction_score >= 0.6:
            print("  ⚠️ MODERATE: Model needs improvement in instruction following")
        else:
            print("  🚨 POOR: Model has significant issues with instruction adherence")
        
        if format_compliance_rate < 0.7:
            print("  📋 Focus on improving format compliance training")
        
        if structure_compliance_rate < 0.7:
            print("  🏗️ Work on structured response generation")
        
        if content_compliance_rate < 0.7:
            print("  📝 Improve content relevance and instruction adherence")
        
        return {
            "avg_instruction_score": avg_instruction_score,
            "format_compliance_rate": format_compliance_rate,
            "structure_compliance_rate": structure_compliance_rate,
            "content_compliance_rate": content_compliance_rate,
            "total_issues": len(all_issues)
        }

def main():
    """Main function"""
    print("📋 Phi-2 v5 Prompt Following & Instruction Adherence Testing")
    print("Testing format compliance, structure following, and instruction adherence")
    print("=" * 80)
    
    tester = PromptFollowingTester()
    
    # Run tests
    results = tester.run_prompt_following_test()
    
    # Generate report
    report_summary = tester.generate_prompt_following_report(results)
    
    # Save detailed results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = f"phi2_v5_prompt_following_report_{timestamp}.json"
    
    with open(report_filename, 'w') as f:
        json.dump({
            "timestamp": timestamp,
            "endpoint": "phi2-v5-inference",
            "summary": report_summary,
            "detailed_results": results
        }, f, indent=2, default=str)
    
    print(f"\n💾 Detailed results saved to: {report_filename}")
    print("🎉 Prompt following testing completed!")

if __name__ == "__main__":
    main()

