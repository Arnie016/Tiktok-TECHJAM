#!/usr/bin/env python3
"""
Generate CSV output file for deliverables
Runs the system on test dataset and outputs results to CSV
"""

import csv
import json
import time
import requests
from datetime import datetime
import pandas as pd

# Test dataset and API endpoint
FUNCTION_URL = "https://vcf7glhsl7w4yccfzny6tigqmm0znsxx.lambda-url.us-west-2.on.aws/"
TEST_CASES = [
    {
        "name": "GDPR Cookie Consent",
        "instruction": "Analyse the feature artifact and decide if geo-specific compliance logic is needed.",
        "input": "Feature Name: EU Cookie Consent Banner\nFeature Description: Display cookie consent banner for EU users accessing the website.\nLaw Context: [{\"law\": \"GDPR Article 7\", \"jurisdiction\": \"EU\", \"requirement\": \"Valid consent for data processing\"}]"
    },
    {
        "name": "US CCPA Privacy Rights",
        "instruction": "Analyse the feature artifact and decide if geo-specific compliance logic is needed.",
        "input": "Feature Name: California Do Not Sell Button\nFeature Description: Button for California residents to opt-out of data sales.\nLaw Context: [{\"law\": \"CCPA Section 1798.135\", \"jurisdiction\": \"US-CA\", \"requirement\": \"Right to opt-out of sale\"}]"
    },
    {
        "name": "Simple UI Feature - No Compliance",
        "instruction": "Analyse the feature artifact and decide if geo-specific compliance logic is needed.",
        "input": "Feature Name: Dark Mode Toggle\nFeature Description: UI toggle for switching between light and dark themes.\nLaw Context: []"
    },
    {
        "name": "Financial SOX Compliance",
        "instruction": "Analyse the feature artifact and decide if geo-specific compliance logic is needed.",
        "input": "Feature Name: Financial Audit Logger\nFeature Description: Logs financial transactions for compliance auditing.\nLaw Context: [{\"law\": \"SOX Section 404\", \"jurisdiction\": \"US\", \"requirement\": \"Internal controls over financial reporting\"}]"
    },
    {
        "name": "COPPA Children's Privacy",
        "instruction": "Analyse the feature artifact and decide if geo-specific compliance logic is needed.",
        "input": "Feature Name: Age Verification System\nFeature Description: System to verify user age and implement parental controls for users under 13.\nLaw Context: [{\"law\": \"COPPA\", \"jurisdiction\": \"US\", \"requirement\": \"Parental consent for children under 13\"}]"
    },
    {
        "name": "LGPD Brazil Data Processing",
        "instruction": "Analyse the feature artifact and decide if geo-specific compliance logic is needed.",
        "input": "Feature Name: Brazil Data Processing Consent\nFeature Description: Consent mechanism for data processing activities in Brazil.\nLaw Context: [{\"law\": \"LGPD Article 7\", \"jurisdiction\": \"Brazil\", \"requirement\": \"Legal basis for data processing\"}]"
    },
    {
        "name": "UK GDPR Age Appropriate Design",
        "instruction": "Analyse the feature artifact and decide if geo-specific compliance logic is needed.",
        "input": "Feature Name: UK Age Verification\nFeature Description: Age verification system for UK users with age-appropriate design principles.\nLaw Context: [{\"law\": \"UK Age Appropriate Design Code\", \"jurisdiction\": \"UK\", \"requirement\": \"Age-appropriate design for children\"}]"
    },
    {
        "name": "PIPEDA Canada Consent",
        "instruction": "Analyse the feature artifact and decide if geo-specific compliance logic is needed.",
        "input": "Feature Name: Canada Privacy Consent\nFeature Description: Privacy consent mechanism for Canadian users.\nLaw Context: [{\"law\": \"PIPEDA Principle 3\", \"jurisdiction\": \"Canada\", \"requirement\": \"Meaningful consent for data collection\"}]"
    }
]

def test_system(test_case):
    """Test the system with a given test case"""
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
            FUNCTION_URL,
            json=payload,
            headers=headers,
            timeout=60
        )
        response_time = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            return {
                "success": True,
                "response_time": round(response_time, 3),
                "result": result
            }
        else:
            return {
                "success": False,
                "response_time": round(response_time, 3),
                "error": f"HTTP {response.status_code}: {response.text}"
            }
            
    except Exception as e:
        return {
            "success": False,
            "response_time": 0,
            "error": str(e)
        }

def extract_compliance_data(result):
    """Extract compliance data from API response"""
    if not result.get("success"):
        return {
            "need_geo_logic": "ERROR",
            "jurisdictions": "ERROR",
            "legal_citations": "ERROR",
            "data_categories": "ERROR",
            "lawful_basis": "ERROR",
            "consent_required": "ERROR",
            "confidence": "ERROR"
        }
    
    compliance = result.get("compliance", {})
    return {
        "need_geo_logic": compliance.get("need_geo_logic", "N/A"),
        "jurisdictions": ", ".join(compliance.get("jurisdictions", [])),
        "legal_citations": str(compliance.get("legal_citations", [])),
        "data_categories": ", ".join(compliance.get("data_categories", [])),
        "lawful_basis": ", ".join(compliance.get("lawful_basis", [])),
        "consent_required": compliance.get("consent_required", "N/A"),
        "confidence": compliance.get("confidence", "N/A")
    }

def generate_csv_output():
    """Generate CSV output file with test results"""
    print("🧪 Testing system and generating CSV output...")
    
    results = []
    
    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"Testing {i}/{len(TEST_CASES)}: {test_case['name']}")
        
        # Test the system
        test_result = test_system(test_case)
        
        # Extract compliance data
        compliance_data = extract_compliance_data(test_result)
        
        # Create result row
        row = {
            "test_case_id": i,
            "test_case_name": test_case["name"],
            "input_feature_name": test_case["input"].split("\n")[0].replace("Feature Name: ", ""),
            "input_description": test_case["input"].split("\n")[1].replace("Feature Description: ", ""),
            "success": test_result["success"],
            "response_time_seconds": test_result["response_time"],
            "need_geo_logic": compliance_data["need_geo_logic"],
            "jurisdictions": compliance_data["jurisdictions"],
            "legal_citations": compliance_data["legal_citations"],
            "data_categories": compliance_data["data_categories"],
            "lawful_basis": compliance_data["lawful_basis"],
            "consent_required": compliance_data["consent_required"],
            "confidence": compliance_data["confidence"],
            "timestamp": datetime.now().isoformat()
        }
        
        results.append(row)
        
        # Add delay between requests
        time.sleep(1)
    
    # Write to CSV
    csv_filename = "system_outputs_test_dataset.csv"
    with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            "test_case_id", "test_case_name", "input_feature_name", "input_description",
            "success", "response_time_seconds", "need_geo_logic", "jurisdictions",
            "legal_citations", "data_categories", "lawful_basis", "consent_required",
            "confidence", "timestamp"
        ]
        
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    
    print(f"✅ CSV output generated: {csv_filename}")
    
    # Print summary
    successful_tests = sum(1 for r in results if r["success"])
    avg_response_time = sum(r["response_time_seconds"] for r in results if r["success"]) / successful_tests if successful_tests > 0 else 0
    
    print(f"\n📊 Summary:")
    print(f"Total tests: {len(results)}")
    print(f"Successful tests: {successful_tests}")
    print(f"Success rate: {(successful_tests/len(results)*100):.1f}%")
    print(f"Average response time: {avg_response_time:.3f} seconds")
    
    return csv_filename

if __name__ == "__main__":
    generate_csv_output()
