#!/usr/bin/env python3
"""
Simple test script for the Lambda Function URL
Run this to validate your Function URL is working properly
"""

import json
import requests
import time
from typing import Dict, Any

# ⚠️ REPLACE WITH YOUR ACTUAL LAMBDA FUNCTION URL
LAMBDA_FUNCTION_URL = "https://bvemy4jegpeyk3tf2asnihjn3a0kvwyq.lambda-url.us-west-2.on.aws/"

def test_gdpr_scenario():
    """Test GDPR cookie compliance scenario"""
    payload = {
        "instruction": "Analyse the feature artifact and decide if geo-specific compliance logic is needed. Explain why and cite the relevant regulation if any.",
        "input": """Feature Name: EU Cookie Consent Banner
Feature Description: Display cookie consent banner for EU users accessing the website with options to accept or reject non-essential cookies for analytics and marketing purposes.

Law Context (structured JSON):
[{"law": "GDPR Article 7", "jurisdiction": "EU", "requirement": "Valid consent for data processing"}, {"law": "GDPR Article 6", "jurisdiction": "EU", "requirement": "Lawful basis for processing personal data"}]"""
    }
    
    return test_lambda_function("GDPR Cookie Compliance", payload)

def test_ccpa_scenario():
    """Test CCPA compliance scenario"""
    payload = {
        "instruction": "Analyse the feature artifact and decide if geo-specific compliance logic is needed. Explain why and cite the relevant regulation if any.",
        "input": """Feature Name: California Do Not Sell Button
Feature Description: Provides California residents with a prominent button to opt-out of the sale of their personal information as required by state privacy law.

Law Context (structured JSON):
[{"law": "CCPA Section 1798.135", "jurisdiction": "US-CA", "requirement": "Right to opt-out of sale of personal information"}]"""
    }
    
    return test_lambda_function("CCPA Compliance", payload)

def test_no_compliance_scenario():
    """Test scenario that shouldn't need compliance"""
    payload = {
        "instruction": "Analyse the feature artifact and decide if geo-specific compliance logic is needed. Explain why and cite the relevant regulation if any.",
        "input": """Feature Name: Dark Mode Theme Toggle
Feature Description: Simple UI toggle button that allows users to switch between light and dark color themes for better visual comfort.

Law Context (structured JSON):
[]"""
    }
    
    return test_lambda_function("No Compliance Needed", payload)

def test_lambda_function(test_name: str, payload: Dict[str, Any]) -> bool:
    """Test the Lambda function with given payload"""
    print(f"\n🧪 Testing: {test_name}")
    print("=" * 50)
    
    if not LAMBDA_FUNCTION_URL or LAMBDA_FUNCTION_URL == "YOUR_FUNCTION_URL_HERE":
        print("❌ Error: Please update LAMBDA_FUNCTION_URL with your actual Function URL")
        return False
    
    try:
        start_time = time.time()
        
        response = requests.post(
            LAMBDA_FUNCTION_URL,
            headers={
                'Content-Type': 'application/json'
            },
            json=payload,
            timeout=30
        )
        
        response_time = round((time.time() - start_time) * 1000, 2)
        
        print(f"⚡ Response Time: {response_time}ms")
        print(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('success'):
                compliance = result.get('compliance', {})
                
                print(f"✅ Success: {result.get('success')}")
                print(f"🌍 Geo-Logic Needed: {compliance.get('need_geo_logic')}")
                print(f"🏛️ Jurisdictions: {compliance.get('jurisdictions', [])}")
                print(f"📚 Legal Citations: {len(compliance.get('legal_citations', []))} found")
                print(f"📊 Data Categories: {compliance.get('data_categories', [])}")
                print(f"🎯 Confidence: {compliance.get('confidence', 0):.2f}")
                print(f"⚠️ Risks: {len(compliance.get('risks', []))} identified")
                print(f"🛠️ Implementation Steps: {len(compliance.get('implementation', []))} provided")
                
                if compliance.get('notes'):
                    print(f"📝 Notes: {compliance.get('notes')[:100]}...")
                
                print(f"🤖 Model: {result.get('metadata', {}).get('model_version', 'unknown')}")
                print(f"🔗 Endpoint: {result.get('endpoint', 'unknown')}")
                
                return True
            else:
                print(f"❌ Lambda Error: {result.get('error', 'Unknown error')}")
                return False
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network Error: {str(e)}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ JSON Error: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Unexpected Error: {str(e)}")
        return False

def test_cors():
    """Test CORS preflight request"""
    print(f"\n🧪 Testing: CORS Preflight")
    print("=" * 50)
    
    try:
        response = requests.options(
            LAMBDA_FUNCTION_URL,
            headers={
                'Origin': 'https://example.com',
                'Access-Control-Request-Method': 'POST',
                'Access-Control-Request-Headers': 'Content-Type'
            },
            timeout=10
        )
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"🔗 CORS Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            print("✅ CORS working correctly")
            return True
        else:
            print("❌ CORS failed")
            return False
            
    except Exception as e:
        print(f"❌ CORS Error: {str(e)}")
        return False

def main():
    """Run all tests"""
    print("🚀 Lambda Function URL Test Suite")
    print(f"🔗 Testing URL: {LAMBDA_FUNCTION_URL}")
    
    if not LAMBDA_FUNCTION_URL or LAMBDA_FUNCTION_URL == "YOUR_FUNCTION_URL_HERE":
        print("\n❌ Configuration Error:")
        print("Please update the LAMBDA_FUNCTION_URL variable with your actual Function URL")
        print("You can find it in the AWS Lambda console under your function's Configuration > Function URL")
        return
    
    tests = [
        test_cors,
        test_gdpr_scenario,
        test_ccpa_scenario,
        test_no_compliance_scenario
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ Test failed with exception: {str(e)}")
    
    print(f"\n📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! Your Lambda Function URL is working perfectly!")
        print("\n🎯 Next Steps:")
        print("1. Update the HTML file with your Function URL")
        print("2. Open geo_compliance_ui.html in your browser")
        print("3. Test the interactive UI")
    else:
        print("⚠️ Some tests failed. Check the errors above.")

if __name__ == "__main__":
    main()
