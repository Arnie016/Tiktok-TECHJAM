"""
Legal and Technical Glossary for Geo-Compliance Fine-tuning
This file contains the terms, definitions, and examples that the model should learn.
"""

LEGAL_GLOSSARY = {
    "DSA": {
        "expansion": "Digital Services Act",
        "explanation": "EU regulation for online platforms requiring stricter content moderation and child protection",
        "example_usage": "DSA requires age verification for users under 18",
        "relevant_laws": ["EU DSA 2022", "Digital Services Act"],
        "jurisdiction": "European Union",
        "compliance_level": "mandatory"
    },
    "ASL": {
        "expansion": "Age-sensitive logic",
        "explanation": "Feature behavior changes based on user age to comply with age-related regulations",
        "example_usage": "ASL disables certain features for minors",
        "relevant_laws": ["COPPA", "GDPR", "Age-Appropriate Design Code"],
        "jurisdiction": "Global",
        "compliance_level": "recommended"
    },
    "Softblock": {
        "expansion": "Soft block",
        "explanation": "Silent user limitation without notification, often used for compliance violations",
        "example_usage": "Softblock applied due to compliance violation",
        "relevant_laws": ["DSA", "Content moderation policies"],
        "jurisdiction": "Platform-specific",
        "compliance_level": "operational"
    },
    "CDS": {
        "expansion": "Compliance Detection System",
        "explanation": "Automated system that flags compliance risks and policy violations",
        "example_usage": "CDS triggered a Softblock for policy violation",
        "relevant_laws": ["Platform terms of service", "Content policies"],
        "jurisdiction": "Platform-specific",
        "compliance_level": "operational"
    },
    "COPPA": {
        "expansion": "Children's Online Privacy Protection Act",
        "explanation": "US law protecting children's privacy online, requires parental consent for users under 13",
        "example_usage": "COPPA compliance requires parental consent for data collection",
        "relevant_laws": ["COPPA 1998", "Children's Privacy"],
        "jurisdiction": "United States",
        "compliance_level": "mandatory"
    },
    "GDPR": {
        "expansion": "General Data Protection Regulation",
        "explanation": "EU data privacy law requiring explicit consent and data minimization",
        "example_usage": "GDPR requires explicit consent for data processing",
        "relevant_laws": ["EU GDPR 2018", "Data Privacy"],
        "jurisdiction": "European Union",
        "compliance_level": "mandatory"
    },
    "PIPEDA": {
        "expansion": "Personal Information Protection and Electronic Documents Act",
        "explanation": "Canadian privacy law governing how private sector organizations collect, use and disclose personal information",
        "example_usage": "PIPEDA requires consent for cross-border data transfers",
        "relevant_laws": ["Canadian Privacy Law", "PIPEDA 2000"],
        "jurisdiction": "Canada",
        "compliance_level": "mandatory"
    },
    "ShadowMode": {
        "expansion": "Shadow mode deployment",
        "explanation": "Deploy feature in non-user-impacting way to collect analytics and compliance data",
        "example_usage": "Roll out CDS in ShadowMode to test compliance detection",
        "relevant_laws": ["Testing regulations", "A/B testing policies"],
        "jurisdiction": "Platform-specific",
        "compliance_level": "operational"
    }
}

def get_glossary():
    """Return the legal glossary"""
    return LEGAL_GLOSSARY

def get_terms_by_jurisdiction(jurisdiction):
    """Get terms relevant to a specific jurisdiction"""
    return {term: info for term, info in LEGAL_GLOSSARY.items() 
            if info['jurisdiction'] == jurisdiction}

def get_terms_by_compliance_level(level):
    """Get terms by compliance level (mandatory, recommended, operational)"""
    return {term: info for term, info in LEGAL_GLOSSARY.items() 
            if info['compliance_level'] == level}

def search_glossary(query):
    """Search glossary for terms matching a query"""
    query_lower = query.lower()
    matches = {}
    
    for term, info in LEGAL_GLOSSARY.items():
        if (query_lower in term.lower() or 
            query_lower in info['expansion'].lower() or
            query_lower in info['explanation'].lower()):
            matches[term] = info
    
    return matches

