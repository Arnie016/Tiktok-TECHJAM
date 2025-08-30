#!/usr/bin/env python3
"""
Robust Evaluation Script for Phi-2 Geo-Compliance Endpoint
Tests accuracy, format consistency, jurisdiction hallucination, and response quality
"""

import json
import boto3
import time
import re
from datetime import datetime
from botocore.config import Config
from typing import Dict, List, Any, Tuple
import statistics

class GeoComplianceEvaluator:
    def __init__(self, endpoint_name: str = "phi-2", profile_name: str = "bedrock-561", region: str = "us-west-2"):
        self.endpoint_name = endpoint_name
        self.session = boto3.Session(profile_name=profile_name, region_name=region)
        self.runtime = self.session.client('sagemaker-runtime', config=Config(read_timeout=60))
        
        # Test cases with expected outputs
        self.test_cases = [
            {
                "name": "FL Anonymous Age Verification - Known Case",
                "input": {
                    "instruction": "Analyze the following software feature to determine its geo-compliance requirements. Provide the compliance flag, the relevant law, and the reason.",
                    "input": "Feature Name: FL Anonymous Age Verification\nFeature Description: Provides anonymous/third-party age verification for adult/'harmful to minors' content and deletes verification data, limited to Florida users.\nSource: Doe v. Roblox Corp., 602 F. Supp. 3d 1243.PDF\n\nLaw Context (structured JSON):\n[]"
                },
                "expected": {
                    "compliance_flag": "Not Enough Information",
                    "law": "N/A",
                    "reason": "Law context did not surface the relevant statute for this feature."
                },
                "expected_format": "json",
                "jurisdiction": "FL"
            },
            {
                "name": "Algorithmic Recommendation System - Complex Case",
                "input": {
                    "instruction": "Analyze the following software feature to determine its geo-compliance requirements. Provide the compliance flag, the relevant law, and the reason.",
                    "input": "Feature Name: Algorithmic Recommendation System\nFeature Description: Some attribute TikTok's success to the algorithm that selects content for the main feed, while others point to its innovative design as the primary driver of user engagement.\nSource: EPRS_BRI(2025)775837_EN.pdf\n\nLaw Context (structured JSON):\n[{\"title\": \"CELEX_32022R2065_EN_TXT.pdf\", \"citation\": null, \"snippet\": \"...the systemic risks referred to in paragraph 1: (a) the design of their recommender systems and any other relevant algorithmic system; (b) their content moderation systems; (c) the applicable terms and conditions and their enforcement; (d) systems for selecting and presenting...\", \"uri\": \"https://arnav-finetune-1756053255.s3.us-west-2.amazonaws.com/data/law/CELEX_32022R2065_EN_TXT.pdf\"}]"
                },
                "expected": {
                    "compliance_flag": "Needs Geo-Compliance",
                    "law": "EU DSA",
                    "reason": "Relevant law snippet found for target jurisdiction; feature requires geo-specific controls and auditability."
                },
                "expected_format": "json",
                "jurisdiction": "EU"
            },
            {
                "name": "Targeted Advertising Consent Manager - Multi-Jurisdiction",
                "input": {
                    "instruction": "Analyze the following software feature to determine its geo-compliance requirements. Provide the compliance flag, the relevant law, and the reason.",
                    "input": "Feature Name: Targeted Advertising Consent Manager\nFeature Description: THIS BILL WOULD AUTHORIZE THE COMMISSIONER TO EXEMPT, BY RULE OR ORDER, AN ADVERTISEMENT FROM THOSE REQUIREMENTS IF THE ADVERTISING MEDIUM LIMITS THE CHARACTERS OF AN ADVERTISEMENT OR OTHERWISE RENDERS COMPLIANCE WITH THOSE REQUIREMENTS IMPRACTICABLE.\nSource: 2019 Bill Text CA S.B. 472.PDF\n\nLaw Context (structured JSON):\n[{\"title\": \"CELEX_32022R2065_EN_TXT.pdf\", \"citation\": null, \"snippet\": \"...of the advertisement, in particular where targeted advertising is concerned. This information should include both information about targeting criteria and delivery criteria, in particular when advertisements are delivered to persons in vulnerable situations, such as minors.\", \"uri\": \"https://arnav-finetune-1756053255.s3.us-west-2.amazonaws.com/data/law/CELEX_32022R2065_EN_TXT.pdf\", \"score\": \"HIGH\"}]"
                },
                "expected": {
                    "compliance_flag": "Needs Geo-Compliance",
                    "law": "CA/FL Online Protections",
                    "reason": "Relevant law snippet found for target jurisdiction; feature requires geo-specific controls."
                },
                "expected_format": "json",
                "jurisdiction": "CA"
            }
        ]
        
        # Performance metrics
        self.results = {
            "total_tests": 0,
            "successful_responses": 0,
            "timeout_errors": 0,
            "format_errors": 0,
            "accuracy_scores": [],
            "response_times": [],
            "jurisdiction_hallucinations": 0,
            "wrong_law_citations": 0,
            "format_consistency": 0,
            "detailed_results": []
        }

    def invoke_endpoint(self, payload: Dict) -> Tuple[bool, Dict, float]:
        """Invoke the endpoint and return success status, response, and timing"""
        try:
            start_time = time.time()
            response = self.runtime.invoke_endpoint(
                EndpointName=self.endpoint_name,
                ContentType='application/json',
                Body=json.dumps(payload)
            )
            response_time = time.time() - start_time
            
            result = json.loads(response['Body'].read().decode())
            return True, result, response_time
            
        except Exception as e:
            return False, {"error": str(e)}, 0

    def validate_json_format(self, response: str) -> Tuple[bool, Dict]:
        """Validate if response is proper JSON format"""
        try:
            # Try to parse as JSON
            parsed = json.loads(response)
            
            # Check for required fields
            required_fields = ["compliance_flag", "law", "reason"]
            missing_fields = [field for field in required_fields if field not in parsed]
            
            if missing_fields:
                return False, {"error": f"Missing required fields: {missing_fields}"}
            
            return True, parsed
            
        except json.JSONDecodeError as e:
            return False, {"error": f"Invalid JSON format: {str(e)}"}

    def check_jurisdiction_hallucination(self, response: Dict, expected_jurisdiction: str) -> bool:
        """Check if the model hallucinates jurisdictions not mentioned in context"""
        law_field = response.get("law", "").upper()
        
        # Define jurisdiction patterns
        jurisdiction_patterns = {
            "FL": ["FLORIDA", "FL", "FLA"],
            "CA": ["CALIFORNIA", "CA", "CAL"],
            "EU": ["EU", "EUROPEAN", "EUROPEAN UNION", "DSA", "DMA"],
            "US": ["UNITED STATES", "US", "USA", "FEDERAL"],
            "TX": ["TEXAS", "TX"],
            "NY": ["NEW YORK", "NY"],
            "UK": ["UNITED KINGDOM", "UK", "BRITAIN", "ENGLAND"]
        }
        
        # Check if response cites jurisdictions not in expected
        for jurisdiction, patterns in jurisdiction_patterns.items():
            if any(pattern in law_field for pattern in patterns):
                if jurisdiction != expected_jurisdiction:
                    return True  # Hallucination detected
        
        return False

    def check_wrong_law_citation(self, response: Dict, test_case: Dict) -> bool:
        """Check if the model cites laws not present in the context"""
        law_field = response.get("law", "").lower()
        context = test_case["input"]["input"].lower()
        
        # Extract law mentions from context
        context_laws = re.findall(r'[A-Z]{2,}(?:\s+[A-Z]+)*', context)
        context_laws = [law.lower() for law in context_laws]
        
        # Check if cited law is not in context
        if law_field not in context_laws and law_field != "n/a":
            return True
        
        return False

    def calculate_accuracy_score(self, response: Dict, expected: Dict) -> float:
        """Calculate accuracy score based on field matching"""
        score = 0.0
        total_fields = len(expected)
        
        for field, expected_value in expected.items():
            if field in response:
                response_value = response[field]
                
                # Exact match
                if response_value == expected_value:
                    score += 1.0
                # Partial match (case insensitive)
                elif isinstance(response_value, str) and isinstance(expected_value, str):
                    if response_value.lower() in expected_value.lower() or expected_value.lower() in response_value.lower():
                        score += 0.5
                # Compliance flag logic
                elif field == "compliance_flag":
                    if "not enough" in response_value.lower() and "not enough" in expected_value.lower():
                        score += 1.0
                    elif "needs" in response_value.lower() and "needs" in expected_value.lower():
                        score += 1.0
                    elif "compliant" in response_value.lower() and "compliant" in expected_value.lower():
                        score += 1.0
        
        return score / total_fields

    def run_evaluation(self) -> Dict:
        """Run comprehensive evaluation of the endpoint"""
        print(f"🔍 Starting comprehensive evaluation of {self.endpoint_name}")
        print("=" * 80)
        
        for i, test_case in enumerate(self.test_cases, 1):
            print(f"\n📋 Test {i}: {test_case['name']}")
            print("-" * 60)
            
            # Invoke endpoint
            success, response, response_time = self.invoke_endpoint(test_case["input"])
            
            if not success:
                print(f"❌ Endpoint error: {response.get('error', 'Unknown error')}")
                self.results["timeout_errors"] += 1
                continue
            
            self.results["successful_responses"] += 1
            self.results["response_times"].append(response_time)
            
            print(f"⏱️  Response time: {response_time:.2f}s")
            
            # Validate format
            if "generated_text" in response:
                format_valid, parsed_response = self.validate_json_format(response["generated_text"])
            else:
                format_valid, parsed_response = self.validate_json_format(json.dumps(response))
            
            if not format_valid:
                print(f"❌ Format error: {parsed_response.get('error', 'Unknown format error')}")
                self.results["format_errors"] += 1
                continue
            
            # Calculate accuracy
            accuracy = self.calculate_accuracy_score(parsed_response, test_case["expected"])
            self.results["accuracy_scores"].append(accuracy)
            
            print(f"📊 Accuracy score: {accuracy:.2f}")
            print(f"📝 Response: {json.dumps(parsed_response, indent=2)}")
            
            # Check for hallucinations
            if self.check_jurisdiction_hallucination(parsed_response, test_case["jurisdiction"]):
                print(f"⚠️  JURISDICTION HALLUCINATION DETECTED!")
                self.results["jurisdiction_hallucinations"] += 1
            
            # Check for wrong law citations
            if self.check_wrong_law_citation(parsed_response, test_case):
                print(f"⚠️  WRONG LAW CITATION DETECTED!")
                self.results["wrong_law_citations"] += 1
            
            # Store detailed result
            self.results["detailed_results"].append({
                "test_name": test_case["name"],
                "success": success,
                "response_time": response_time,
                "accuracy": accuracy,
                "response": parsed_response,
                "expected": test_case["expected"],
                "jurisdiction_hallucination": self.check_jurisdiction_hallucination(parsed_response, test_case["jurisdiction"]),
                "wrong_law_citation": self.check_wrong_law_citation(parsed_response, test_case)
            })
            
            self.results["total_tests"] += 1
        
        return self.generate_report()

    def generate_report(self) -> Dict:
        """Generate comprehensive evaluation report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "endpoint_name": self.endpoint_name,
            "summary": {
                "total_tests": self.results["total_tests"],
                "successful_responses": self.results["successful_responses"],
                "success_rate": self.results["successful_responses"] / max(self.results["total_tests"], 1),
                "average_response_time": statistics.mean(self.results["response_times"]) if self.results["response_times"] else 0,
                "average_accuracy": statistics.mean(self.results["accuracy_scores"]) if self.results["accuracy_scores"] else 0,
                "jurisdiction_hallucinations": self.results["jurisdiction_hallucinations"],
                "wrong_law_citations": self.results["wrong_law_citations"],
                "format_errors": self.results["format_errors"]
            },
            "detailed_results": self.results["detailed_results"],
            "recommendations": self.generate_recommendations()
        }
        
        return report

    def generate_recommendations(self) -> List[str]:
        """Generate recommendations based on evaluation results"""
        recommendations = []
        
        success_rate = self.results["successful_responses"] / max(self.results["total_tests"], 1)
        avg_accuracy = statistics.mean(self.results["accuracy_scores"]) if self.results["accuracy_scores"] else 0
        avg_response_time = statistics.mean(self.results["response_times"]) if self.results["response_times"] else 0
        
        # Performance recommendations
        if avg_response_time > 10:
            recommendations.append("🚨 HIGH RESPONSE TIME: Consider model optimization or larger instance type")
        
        if success_rate < 0.8:
            recommendations.append("🚨 LOW SUCCESS RATE: Check endpoint stability and error handling")
        
        # Accuracy recommendations
        if avg_accuracy < 0.7:
            recommendations.append("📉 LOW ACCURACY: Consider retraining with more diverse examples")
        
        if self.results["jurisdiction_hallucinations"] > 0:
            recommendations.append("⚠️ JURISDICTION HALLUCINATIONS: Add more training data with clear jurisdiction boundaries")
        
        if self.results["wrong_law_citations"] > 0:
            recommendations.append("⚠️ WRONG LAW CITATIONS: Improve context understanding and law citation accuracy")
        
        if self.results["format_errors"] > 0:
            recommendations.append("⚠️ FORMAT ERRORS: Ensure consistent JSON output format in training")
        
        # Dataset recommendations
        if self.results["total_tests"] < 10:
            recommendations.append("📊 SMALL TEST SET: Expand test cases for better evaluation coverage")
        
        # Positive feedback
        if avg_accuracy > 0.8 and success_rate > 0.9:
            recommendations.append("✅ EXCELLENT PERFORMANCE: Model is ready for production use")
        
        return recommendations

    def print_report(self, report: Dict):
        """Print formatted evaluation report"""
        print("\n" + "=" * 80)
        print("📊 COMPREHENSIVE EVALUATION REPORT")
        print("=" * 80)
        
        summary = report["summary"]
        print(f"\n🎯 SUMMARY METRICS:")
        print(f"   Total Tests: {summary['total_tests']}")
        print(f"   Successful Responses: {summary['successful_responses']}")
        print(f"   Success Rate: {summary['success_rate']:.2%}")
        print(f"   Average Response Time: {summary['average_response_time']:.2f}s")
        print(f"   Average Accuracy: {summary['average_accuracy']:.2%}")
        print(f"   Jurisdiction Hallucinations: {summary['jurisdiction_hallucinations']}")
        print(f"   Wrong Law Citations: {summary['wrong_law_citations']}")
        print(f"   Format Errors: {summary['format_errors']}")
        
        print(f"\n🔍 DETAILED RESULTS:")
        for i, result in enumerate(report["detailed_results"], 1):
            print(f"\n   Test {i}: {result['test_name']}")
            print(f"     Success: {'✅' if result['success'] else '❌'}")
            print(f"     Response Time: {result['response_time']:.2f}s")
            print(f"     Accuracy: {result['accuracy']:.2%}")
            print(f"     Jurisdiction Hallucination: {'⚠️' if result['jurisdiction_hallucination'] else '✅'}")
            print(f"     Wrong Law Citation: {'⚠️' if result['wrong_law_citation'] else '✅'}")
        
        print(f"\n💡 RECOMMENDATIONS:")
        for rec in report["recommendations"]:
            print(f"   {rec}")
        
        # Save report to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"phi2_evaluation_report_{timestamp}.json"
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n💾 Report saved to: {filename}")

def main():
    """Main evaluation function"""
    evaluator = GeoComplianceEvaluator()
    report = evaluator.run_evaluation()
    evaluator.print_report(report)

if __name__ == "__main__":
    main()

