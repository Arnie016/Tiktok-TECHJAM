#!/usr/bin/env python3
"""
Test script to demonstrate glossary integration for geo-compliance fine-tuning
"""

from glossary import get_glossary, get_terms_by_jurisdiction, search_glossary

def test_glossary_integration():
    """Test the glossary functionality"""
    
    print("🔍 Testing Legal/Technical Glossary Integration\n")
    
    # 1. Load full glossary
    glossary = get_glossary()
    print(f"✅ Loaded {len(glossary)} glossary terms\n")
    
    # 2. Show sample terms
    print("📚 Sample Glossary Terms:")
    for term, info in list(glossary.items())[:3]:
        print(f"  • {term} ({info['expansion']})")
        print(f"    {info['explanation']}")
        print(f"    Jurisdiction: {info['jurisdiction']}")
        print(f"    Compliance: {info['compliance_level']}\n")
    
    # 3. Test jurisdiction filtering
    print("🌍 EU-Specific Terms:")
    eu_terms = get_terms_by_jurisdiction("European Union")
    for term in eu_terms:
        print(f"  • {term}: {eu_terms[term]['expansion']}")
    print()
    
    # 4. Test compliance level filtering
    print("⚠️  Mandatory Compliance Terms:")
    mandatory_terms = get_terms_by_compliance_level("mandatory")
    for term in mandatory_terms:
        print(f"  • {term}: {mandatory_terms[term]['expansion']}")
    print()
    
    # 5. Test search functionality
    print("🔎 Search Results for 'age':")
    age_results = search_glossary("age")
    for term in age_results:
        print(f"  • {term}: {age_results[term]['explanation']}")
    print()
    
    # 6. Test prompt enhancement simulation
    print("📝 Simulated Enhanced Prompt:")
    sample_input = "Feature: Age verification system for users in Quebec accessing adult content"
    print(f"Input: {sample_input}")
    
    # Find relevant terms
    relevant_terms = {}
    for term, info in glossary.items():
        if any(word in sample_input.lower() for word in [term.lower(), "age", "verification", "quebec"]):
            relevant_terms[term] = info
    
    print("\nRelevant Legal Terms:")
    for term, info in relevant_terms.items():
        print(f"  • {term} ({info['expansion']}): {info['explanation']}")
    
    print("\n✅ Glossary integration test completed!")

if __name__ == "__main__":
    test_glossary_integration()

