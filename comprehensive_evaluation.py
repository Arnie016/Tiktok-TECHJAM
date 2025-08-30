#!/usr/bin/env python3
"""
Comprehensive Evaluation Script for Phi-2 Geo-Compliance Endpoint
Analyzes text-based responses for quality, accuracy, and compliance issues
"""

import json
import boto3
import time
import re
from datetime import datetime
from botocore.config import Config
from typing import Dict, List, Any, Tuple
import statistics

class ComprehensiveEvaluator:
    def __init__(self, endpoint_name: str = "phi-2", profile_name: str = "bedrock-561", region: str = "us-west-2"):
        self.endpoint_name = endpoint_name
        self.session = boto3.Session(profile_name=profile_name, region_name=region)
        self.runtime = self.session.client('sagemaker-runtime', config=Config(read_timeout=60))
        
        # Test cases with expected outputs
        self.test_cases = [
            {
                "name": "FL Anonymous Age Verification - Empty Context",
                "input": {
                    "instruction": "Analyze the following software feature to determine its geo-compliance requirements. Provide the compliance flag, the relevant law, and the reason.",
                    "input": "Feature Name: FL Anonymous Age Verification\nFeature Description: Provides anonymous/third-party age verification for adult/'harmful to minors' content and deletes verification data, limited to Florida users.\nSource: Doe v. Roblox Corp., 602 F. Supp. 3d 1243.PDF\n\nLaw Context (structured JSON):\n[]"
                },
                "expected_keywords": ["not enough information", "n/a", "no relevant statute"],
                "expected_jurisdiction": "FL",
                "should_have_json": False
            },
            {
                "name": "Algorithmic Recommendation System - EU Context",
                "input": {
                    "instruction": "Analyze the following software feature to determine its geo-compliance requirements. Provide the compliance flag, the relevant law, and the reason.",
                    "input": "Feature Name: Algorithmic Recommendation System\nFeature Description: Some attribute TikTok's success to the algorithm that selects content for the main feed, while others point to its innovative design as the primary driver of user engagement.\nSource: EPRS_BRI(2025)775837_EN.pdf\n\nLaw Context (structured JSON):\n[{\"title\": \"CELEX_32022R2065_EN_TXT.pdf\", \"citation\": null, \"snippet\": \"...the systemic risks referred to in paragraph 1: (a) the design of their recommender systems and any other relevant algorithmic system; (b) their content moderation systems; (c) the applicable terms and conditions and their enforcement; (d) systems for selecting and presenting...\", \"uri\": \"https://arnav-finetune-1756053255.s3.us-west-2.amazonaws.com/data/law/CELEX_32022R2065_EN_TXT.pdf\"}]"
                },
                "expected_keywords": ["needs geo-compliance", "eu", "dsa", "recommender"],
                "expected_jurisdiction": "EU",
                "should_have_json": True
            },
            {
                "name": "Targeted Advertising Consent Manager - CA Context",
                "input": {
                    "instruction": "Analyze the following software feature to determine its geo-compliance requirements. Provide the compliance flag, the relevant law, and the reason.",
                    "input": "Feature Name: Targeted Advertising Consent Manager\nFeature Description: THIS BILL WOULD AUTHORIZE THE COMMISSIONER TO EXEMPT, BY RULE OR ORDER, AN ADVERTISEMENT FROM THOSE REQUIREMENTS IF THE ADVERTISING MEDIUM LIMITS THE CHARACTERS OF AN ADVERTISEMENT OR OTHERWISE RENDERS COMPLIANCE WITH THOSE REQUIREMENTS IMPRACTICABLE.\nSource: 2019 Bill Text CA S.B. 472.PDF\n\nLaw Context (structured JSON):\n[{\"title\": \"CELEX_32022R2065_EN_TXT.pdf\", \"citation\": null, \"snippet\": \"...of the advertisement, in particular where targeted advertising is concerned. This information should include both information about targeting criteria and delivery criteria, in particular when advertisements are delivered to persons in vulnerable situations, such as minors.\", \"uri\": \"https://arnav-finetune-1756053255.s3.us-west-2.amazonaws.com/data/law/CELEX_32022R2065_EN_TXT.pdf\", \"score\": \"HIGH\"}]"
                },
                "expected_keywords": ["needs geo-compliance", "targeted advertising", "consent"],
                "expected_jurisdiction": "CA",
                "should_have_json": True
            }
        ]
        
        # Performance metrics
        self.results = {
            "total_tests": 0,
            "successful_responses": 0,
            "timeout_errors": 0,
            "response_times": [],
            "content_quality_scores": [],
            "jurisdiction_hallucinations": 0,
            "format_issues": 0,
            "repetition_issues": 0,
            "incomplete_responses": 0,
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

    def analyze_content_quality(self, text: str) -> Dict:
        """Analyze the quality of the generated text"""
        analysis = {
            "length": len(text),
            "word_count": len(text.split()),
            "has_json_structure": False,
            "has_repetition": False,
            "is_incomplete": False,
            "contains_expected_keywords": [],
            "jurisdiction_mentions": [],
            "law_mentions": [],
            "compliance_flags": []
        }
        
        # Check for JSON structure
        json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
        if json_match:
            analysis["has_json_structure"] = True
        
        # Check for repetition
        sentences = text.split('.')
        if len(sentences) > 3:
            unique_sentences = set(sentences)
            if len(unique_sentences) / len(sentences) < 0.7:
                analysis["has_repetition"] = True
        
        # Check if response is incomplete
        if text.strip().endswith('...') or len(text.split()) < 10:
            analysis["is_incomplete"] = True
        
        # Extract jurisdiction mentions
        jurisdiction_patterns = {
            "FL": ["florida", "fl", "fla"],
            "CA": ["california", "ca", "cal"],
            "EU": ["eu", "european", "european union", "dsa", "dma"],
            "US": ["united states", "us", "usa", "federal"],
            "TX": ["texas", "tx"],
            "NY": ["new york", "ny"],
            "UK": ["united kingdom", "uk", "britain", "england"]
        }
        
        text_lower = text.lower()
        for jurisdiction, patterns in jurisdiction_patterns.items():
            if any(pattern in text_lower for pattern in patterns):
                analysis["jurisdiction_mentions"].append(jurisdiction)
        
        # Extract law mentions
        law_patterns = [
            r'\b[A-Z]{2,}(?:\s+[A-Z]+)*\b',  # Acronyms like GDPR, DSA, etc.
            r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Act|Law|Regulation|Directive)\b'
        ]
        
        for pattern in law_patterns:
            matches = re.findall(pattern, text)
            analysis["law_mentions"].extend(matches)
        
        # Extract compliance flags
        compliance_patterns = [
            r'\b(?:not enough information|needs geo-compliance|compliant|non-compliant)\b',
            r'\b(?:requires|must|should)\s+(?:geo|compliance|regulation)\b'
        ]
        
        for pattern in compliance_patterns:
            matches = re.findall(pattern, text.lower())
            analysis["compliance_flags"].extend(matches)
        
        return analysis

    def check_jurisdiction_hallucination(self, analysis: Dict, expected_jurisdiction: str) -> bool:
        """Check if the model hallucinates jurisdictions not mentioned in context"""
        mentioned_jurisdictions = analysis["jurisdiction_mentions"]
        
        # If no expected jurisdiction, any mention is hallucination
        if expected_jurisdiction == "NONE":
            return len(mentioned_jurisdictions) > 0
        
        # Check if unexpected jurisdictions are mentioned
        for jurisdiction in mentioned_jurisdictions:
            if jurisdiction != expected_jurisdiction:
                return True
        
        return False

    def calculate_content_quality_score(self, analysis: Dict, expected_keywords: List[str]) -> float:
        """Calculate a quality score based on various factors"""
        score = 0.0
        max_score = 10.0
        
        # Length score (0-2 points)
        if analysis["length"] > 100:
            score += 1.0
        if analysis["length"] > 200:
            score += 1.0
        
        # JSON structure score (0-2 points)
        if analysis["has_json_structure"]:
            score += 2.0
        
        # No repetition score (0-2 points)
        if not analysis["has_repetition"]:
            score += 2.0
        
        # Completeness score (0-2 points)
        if not analysis["is_incomplete"]:
            score += 2.0
        
        # Keyword matching score (0-2 points)
        text_lower = analysis.get("text", "").lower()
        keyword_matches = sum(1 for keyword in expected_keywords if keyword.lower() in text_lower)
        score += min(2.0, keyword_matches * 0.5)
        
        return min(max_score, score) / max_score

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
            
            # Extract generated text
            if "generated_text" in response:
                generated_text = response["generated_text"]
            else:
                generated_text = str(response)
            
            print(f"📝 Generated text length: {len(generated_text)} characters")
            print(f"📝 Generated text: {generated_text[:200]}...")
            
            # Analyze content quality
            analysis = self.analyze_content_quality(generated_text)
            analysis["text"] = generated_text
            
            # Calculate quality score
            quality_score = self.calculate_content_quality_score(analysis, test_case["expected_keywords"])
            self.results["content_quality_scores"].append(quality_score)
            
            print(f"📊 Quality score: {quality_score:.2f}")
            
            # Check for issues
            if self.check_jurisdiction_hallucination(analysis, test_case["expected_jurisdiction"]):
                print(f"⚠️  JURISDICTION HALLUCINATION DETECTED!")
                self.results["jurisdiction_hallucinations"] += 1
            
            if analysis["has_repetition"]:
                print(f"⚠️  REPETITION ISSUE DETECTED!")
                self.results["repetition_issues"] += 1
            
            if analysis["is_incomplete"]:
                print(f"⚠️  INCOMPLETE RESPONSE DETECTED!")
                self.results["incomplete_responses"] += 1
            
            if not analysis["has_json_structure"] and test_case["should_have_json"]:
                print(f"⚠️  MISSING JSON STRUCTURE!")
                self.results["format_issues"] += 1
            
            # Store detailed result
            self.results["detailed_results"].append({
                "test_name": test_case["name"],
                "success": success,
                "response_time": response_time,
                "quality_score": quality_score,
                "generated_text": generated_text,
                "analysis": analysis,
                "expected_keywords": test_case["expected_keywords"],
                "expected_jurisdiction": test_case["expected_jurisdiction"],
                "jurisdiction_hallucination": self.check_jurisdiction_hallucination(analysis, test_case["expected_jurisdiction"]),
                "has_repetition": analysis["has_repetition"],
                "is_incomplete": analysis["is_incomplete"],
                "missing_json": not analysis["has_json_structure"] and test_case["should_have_json"]
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
                "average_quality_score": statistics.mean(self.results["content_quality_scores"]) if self.results["content_quality_scores"] else 0,
                "jurisdiction_hallucinations": self.results["jurisdiction_hallucinations"],
                "repetition_issues": self.results["repetition_issues"],
                "incomplete_responses": self.results["incomplete_responses"],
                "format_issues": self.results["format_issues"]
            },
            "detailed_results": self.results["detailed_results"],
            "recommendations": self.generate_recommendations()
        }
        
        return report

    def generate_recommendations(self) -> List[str]:
        """Generate recommendations based on evaluation results"""
        recommendations = []
        
        success_rate = self.results["successful_responses"] / max(self.results["total_tests"], 1)
        avg_quality = statistics.mean(self.results["content_quality_scores"]) if self.results["content_quality_scores"] else 0
        avg_response_time = statistics.mean(self.results["response_times"]) if self.results["response_times"] else 0
        
        # Performance recommendations
        if avg_response_time > 10:
            recommendations.append("🚨 HIGH RESPONSE TIME: Consider model optimization or larger instance type")
        
        if success_rate < 0.8:
            recommendations.append("🚨 LOW SUCCESS RATE: Check endpoint stability and error handling")
        
        # Quality recommendations
        if avg_quality < 0.6:
            recommendations.append("📉 LOW QUALITY SCORE: Consider retraining with better examples and prompt engineering")
        
        if self.results["jurisdiction_hallucinations"] > 0:
            recommendations.append("⚠️ JURISDICTION HALLUCINATIONS: Add more training data with clear jurisdiction boundaries")
        
        if self.results["repetition_issues"] > 0:
            recommendations.append("⚠️ REPETITION ISSUES: Improve model training to reduce repetitive outputs")
        
        if self.results["incomplete_responses"] > 0:
            recommendations.append("⚠️ INCOMPLETE RESPONSES: Adjust generation parameters or improve training")
        
        if self.results["format_issues"] > 0:
            recommendations.append("⚠️ FORMAT ISSUES: Train model to consistently output structured JSON responses")
        
        # Dataset recommendations
        if self.results["total_tests"] < 10:
            recommendations.append("📊 SMALL TEST SET: Expand test cases for better evaluation coverage")
        
        # Positive feedback
        if avg_quality > 0.8 and success_rate > 0.9:
            recommendations.append("✅ EXCELLENT PERFORMANCE: Model is ready for production use")
        
        # Specific recommendations based on findings
        if self.results["format_issues"] > 0:
            recommendations.append("🔧 IMMEDIATE FIX NEEDED: Model is not generating proper JSON format - retrain with JSON examples")
        
        if self.results["repetition_issues"] > 0:
            recommendations.append("🔧 TRAINING ISSUE: Model shows repetitive behavior - improve training data diversity")
        
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
        print(f"   Average Quality Score: {summary['average_quality_score']:.2%}")
        print(f"   Jurisdiction Hallucinations: {summary['jurisdiction_hallucinations']}")
        print(f"   Repetition Issues: {summary['repetition_issues']}")
        print(f"   Incomplete Responses: {summary['incomplete_responses']}")
        print(f"   Format Issues: {summary['format_issues']}")
        
        print(f"\n🔍 DETAILED RESULTS:")
        for i, result in enumerate(report["detailed_results"], 1):
            print(f"\n   Test {i}: {result['test_name']}")
            print(f"     Success: {'✅' if result['success'] else '❌'}")
            print(f"     Response Time: {result['response_time']:.2f}s")
            print(f"     Quality Score: {result['quality_score']:.2%}")
            print(f"     Jurisdiction Hallucination: {'⚠️' if result['jurisdiction_hallucination'] else '✅'}")
            print(f"     Repetition Issue: {'⚠️' if result['has_repetition'] else '✅'}")
            print(f"     Incomplete Response: {'⚠️' if result['is_incomplete'] else '✅'}")
            print(f"     Missing JSON: {'⚠️' if result['missing_json'] else '✅'}")
            print(f"     Text Length: {len(result['generated_text'])} chars")
        
        print(f"\n💡 RECOMMENDATIONS:")
        for rec in report["recommendations"]:
            print(f"   {rec}")
        
        # Save report to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"phi2_comprehensive_report_{timestamp}.json"
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n💾 Report saved to: {filename}")

def main():
    """Main evaluation function"""
    evaluator = ComprehensiveEvaluator()
    report = evaluator.run_evaluation()
    evaluator.print_report(report)

if __name__ == "__main__":
    main()

