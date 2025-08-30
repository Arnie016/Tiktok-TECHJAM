#!/usr/bin/env python3
"""
Geo-Compliance Analyzer Lambda Function
=======================================

AWS Lambda function that provides structured geo-compliance analysis
for software features using a fine-tuned Phi-2 v5 model.

Deployed at: https://bvemy4jegpeyk3tf2asnihjn3a0kvwyq.lambda-url.us-west-2.on.aws/

Returns structured JSON with:
- need_geo_logic: bool
- jurisdictions: List[str] 
- legal_citations: List[Dict]
- data_categories: List[str]
- lawful_basis: List[str]
- consent_required: bool
- risks: List[Dict]
- implementation: List[Dict]
- confidence: float
"""

import json
import boto3
import logging
import re
import time
from typing import Dict, Any
from botocore.config import Config

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS Configuration
REGION = "us-west-2"
ENDPOINT_NAME = "phi2-v5-inference"

sagemaker_runtime = boto3.client(
    "sagemaker-runtime",
    region_name=REGION,
    config=Config(
        connect_timeout=5,
        read_timeout=25,
        retries={"max_attempts": 2, "mode": "adaptive"},
    ),
)

# Default structured response template
DEFAULT_COMPLIANCE = {
    "need_geo_logic": False,
    "jurisdictions": [],
    "legal_citations": [],
    "data_categories": [],
    "lawful_basis": [],
    "consent_required": False,
    "notes": "",
    "risks": [],
    "implementation": [],
    "confidence": 0.0,
}

# Prompt template for structured JSON output
FORMAT_HINT = (
    'Return ONLY valid minified JSON with keys: '
    'need_geo_logic,jurisdictions,legal_citations,data_categories,lawful_basis,'
    'consent_required,notes,risks,implementation,confidence. '
    'Example: {"need_geo_logic":true,"jurisdictions":["EU"],"legal_citations":[{"law":"GDPR","article":"7(1)","jurisdiction":"EU"}],"data_categories":["cookies"],"lawful_basis":["consent"],"consent_required":true,"notes":"...","risks":[{"risk":"...","severity":"high","mitigation":"..."}],"implementation":[{"step":"...","priority":1}],"confidence":0.8}'
)

def extract_json_from_text(text: str) -> str:
    """Extract JSON object from model-generated text."""
    if not text:
        return ""
    
    text = text.strip()
    
    # If already valid JSON structure
    if text.startswith("{") and text.endswith("}"):
        return text
    
    # Find JSON boundaries
    start = text.find("{")
    end = text.rfind("}")
    
    if start == -1 or end == -1 or end <= start:
        return ""
    
    candidate = text[start:end+1]
    
    # Balance braces if truncated
    open_count = candidate.count("{")
    close_count = candidate.count("}")
    
    if open_count > close_count:
        candidate += "}" * (open_count - close_count)
    
    return candidate

def parse_json_lenient(raw_json: str) -> Dict[str, Any]:
    """Parse JSON with error recovery for common issues."""
    try:
        return json.loads(raw_json)
    except Exception:
        if not raw_json:
            return None
        
        # Remove trailing commas (common model error)
        fixed_json = re.sub(r",(\s*[}\]])", r"\1", raw_json)
        
        try:
            return json.loads(fixed_json)
        except Exception:
            return None

def normalize_compliance_output(data: Any) -> Dict[str, Any]:
    """Normalize and validate compliance analysis output."""
    output = dict(DEFAULT_COMPLIANCE)
    
    if not isinstance(data, dict):
        return output
    
    # Boolean fields
    output["need_geo_logic"] = bool(data.get("need_geo_logic", False))
    output["consent_required"] = bool(data.get("consent_required", False))
    
    # List fields with type checking
    for field in ["jurisdictions", "data_categories", "lawful_basis"]:
        value = data.get(field, [])
        output[field] = list(value) if isinstance(value, list) else []
    
    # Legal citations with structure validation
    citations = data.get("legal_citations", [])
    if isinstance(citations, list):
        normalized_citations = []
        for citation in citations:
            if isinstance(citation, dict):
                normalized_citations.append({
                    "law": str(citation.get("law", "")),
                    "article": str(citation.get("article", "")),
                    "jurisdiction": str(citation.get("jurisdiction", ""))
                })
        output["legal_citations"] = normalized_citations
    
    # Risk assessment with structure validation
    risks = data.get("risks", [])
    if isinstance(risks, list):
        normalized_risks = []
        for risk in risks:
            if isinstance(risk, dict):
                normalized_risks.append({
                    "risk": str(risk.get("risk", "")),
                    "severity": str(risk.get("severity", "")).lower(),
                    "mitigation": str(risk.get("mitigation", ""))
                })
        output["risks"] = normalized_risks
    
    # Implementation steps with priority validation
    implementation = data.get("implementation", [])
    if isinstance(implementation, list):
        normalized_impl = []
        for step in implementation:
            if isinstance(step, dict):
                try:
                    priority = int(step.get("priority", 1))
                except (ValueError, TypeError):
                    priority = 1
                
                normalized_impl.append({
                    "step": str(step.get("step", "")),
                    "priority": priority
                })
        output["implementation"] = normalized_impl
    
    # String fields with length limits
    output["notes"] = str(data.get("notes", ""))[:400]
    
    # Confidence score validation
    try:
        confidence = float(data.get("confidence", 0.0))
        output["confidence"] = max(0.0, min(1.0, confidence))
    except (ValueError, TypeError):
        output["confidence"] = 0.0
    
    return output

def generate_heuristic_analysis(text: str, feature_input: str) -> Dict[str, Any]:
    """Generate compliance analysis using heuristic rules when model fails."""
    combined_text = f"{text} {feature_input}".lower()
    result = dict(DEFAULT_COMPLIANCE)
    
    # Detect jurisdictions from text patterns
    jurisdictions = set()
    if any(keyword in combined_text for keyword in ["gdpr", "eprivacy", "eu cookie", "eu users"]):
        jurisdictions.add("EU")
    if any(keyword in combined_text for keyword in ["ccpa", "cpra", "california"]):
        jurisdictions.add("US-CA")
    if "uk" in combined_text and "gdpr" in combined_text:
        jurisdictions.add("UK")
    if any(keyword in combined_text for keyword in ["pdpa", "singapore"]):
        jurisdictions.add("SG")
    
    # Detect data categories
    categories = set()
    if "cookie" in combined_text:
        categories.add("cookies")
    if "analytics" in combined_text:
        categories.add("analytics")
    if any(keyword in combined_text for keyword in ["identifier", "idfa", "gaid", "uuid"]):
        categories.add("identifiers")
    
    # Detect lawful basis
    basis = set()
    if "consent" in combined_text:
        basis.add("consent")
    if "legitimate interest" in combined_text:
        basis.add("legitimate_interests")
    
    # Determine consent requirements
    consent_required = (
        "eu" in " ".join(jurisdictions).lower() and 
        any(keyword in combined_text for keyword in ["non-essential", "analytics", "marketing"])
    )
    
    # Determine geo-logic need
    need_geo_logic = (
        len(jurisdictions) > 1 or 
        ("geo" in combined_text and "logic" in combined_text) or 
        "eu users" in combined_text
    )
    
    # Generate notes
    notes = []
    if "EU" in jurisdictions:
        notes.append("EU non-essential cookies typically require opt-in consent.")
    if "US-CA" in jurisdictions:
        notes.append("California requires disclosures and limited use; consent norms differ from EU.")
    if not notes:
        notes.append("Apply jurisdiction-specific banner and blocking rules if targeting regulated regions.")
    
    # Generate legal citations
    citations = []
    if "EU" in jurisdictions:
        citations.append({"law": "GDPR", "article": "7(1)", "jurisdiction": "EU"})
        if "eprivacy" in combined_text or "cookie" in combined_text:
            citations.append({"law": "ePrivacy Directive", "article": "5(3)", "jurisdiction": "EU"})
    if "US-CA" in jurisdictions:
        citations.append({"law": "CCPA/CPRA", "article": "1798.100+", "jurisdiction": "US-CA"})
    if "SG" in jurisdictions:
        citations.append({"law": "PDPA", "article": "Consent/Notification", "jurisdiction": "SG"})
    
    # Generate implementation steps
    implementation = []
    if jurisdictions:
        implementation = [
            {"step": "Detect user jurisdiction (IP/residency/self-declare)", "priority": 1},
            {"step": "Block non-essential cookies until consent where required", "priority": 1},
            {"step": "Provide granular toggles and store consent timestamp", "priority": 1},
        ]
    
    # Generate risks
    risks = []
    if "EU" in jurisdictions:
        risks.append({
            "risk": "drop cookies pre-consent in EU",
            "severity": "high",
            "mitigation": "implement prior opt-in"
        })
    
    # Confidence based on detection quality
    confidence = 0.55 if (jurisdictions or categories or basis or consent_required) else 0.3
    
    result.update({
        "need_geo_logic": need_geo_logic or bool(jurisdictions),
        "jurisdictions": sorted(jurisdictions),
        "legal_citations": citations,
        "data_categories": sorted(categories),
        "lawful_basis": sorted(basis),
        "consent_required": consent_required,
        "notes": " ".join(notes)[:400],
        "risks": risks,
        "implementation": implementation,
        "confidence": confidence,
    })
    
    return result

def is_debug_enabled(event: Dict[str, Any]) -> bool:
    """Check if debug mode is enabled via query parameters."""
    query_params = event.get("queryStringParameters") or {}
    debug_value = str(query_params.get("debug", "false")).lower()
    return debug_value in ("1", "true", "yes")

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for geo-compliance analysis.
    
    Expected input:
    {
        "instruction": "Analyse the feature artifact and decide if geo-specific compliance logic is needed.",
        "input": "Feature Name: ...\nFeature Description: ...\nLaw Context: [...]"
    }
    
    Returns structured compliance analysis with legal citations, risks, and implementation guidance.
    """
    
    # CORS headers for web integration
    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
    }
    
    # Handle CORS preflight requests
    if event.get("httpMethod") == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps({"message": "CORS preflight successful"})
        }
    
    try:
        # Parse request body
        body = event.get("body", "{}")
        try:
            request_data = json.loads(body) if isinstance(body, str) else (body or {})
        except json.JSONDecodeError:
            return {
                "statusCode": 400,
                "headers": headers,
                "body": json.dumps({"error": "Invalid JSON in request body"})
            }
        
        # Extract and validate required fields
        instruction = (request_data.get("instruction") or "").strip()
        feature_input = (request_data.get("input") or "").strip()
        
        if not instruction or not feature_input:
            return {
                "statusCode": 400,
                "headers": headers,
                "body": json.dumps({
                    "error": "Missing required fields",
                    "received": {
                        "instruction": bool(instruction),
                        "input": bool(feature_input)
                    }
                })
            }
        
        # Prepare model instruction with structured output hint
        model_instruction = instruction + "\n\n" + "You are a compliance analyst. " + FORMAT_HINT
        
        # Prepare SageMaker payload
        sagemaker_payload = {
            "instruction": model_instruction,
            "input": feature_input,
            "temperature": 0.1,  # Low temperature for consistent output
            "max_new_tokens": 350,  # Sufficient for structured JSON
        }
        
        # Invoke SageMaker endpoint with timing
        start_time = time.perf_counter()
        
        sagemaker_response = sagemaker_runtime.invoke_endpoint(
            EndpointName=ENDPOINT_NAME,
            ContentType="application/json",
            Body=json.dumps(sagemaker_payload),
        )
        
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        
        # Parse SageMaker response
        sagemaker_result = json.loads(sagemaker_response["Body"].read().decode() or "{}")
        generated_text = sagemaker_result.get("generated_text", "")
        
        # Extract and parse JSON from model output
        extracted_json = extract_json_from_text(generated_text)
        parsed_data = parse_json_lenient(extracted_json) if extracted_json else None
        
        # Generate compliance analysis (model output or heuristic fallback)
        compliance_analysis = (
            normalize_compliance_output(parsed_data) 
            if parsed_data 
            else generate_heuristic_analysis(generated_text, feature_input)
        )
        
        # Prepare response
        response_data = {
            "success": True,
            "endpoint": ENDPOINT_NAME,
            "compliance": compliance_analysis,
            "metadata": {
                "model_version": "phi2-v5",
                "instruction_length": len(instruction),
                "input_length": len(feature_input),
                "latency_ms": latency_ms,
                "request_id": getattr(context, "aws_request_id", None),
            },
        }
        
        # Add debug information if requested
        if is_debug_enabled(event):
            response_data["debug"] = {
                "model_generated_text": generated_text[:4000],
                "raw_response": sagemaker_result,
                "extracted_json": extracted_json,
            }
        
        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps(response_data, separators=(",", ":"), ensure_ascii=False)
        }
        
    except Exception as e:
        # Log error for debugging
        logger.error(f"Error in lambda_handler: {str(e)}", exc_info=True)
        
        # Return structured error response
        error_response = {
            "success": False,
            "error": {
                "type": type(e).__name__,
                "message": str(e),
                "endpoint": ENDPOINT_NAME
            },
            "metadata": {
                "model_version": "phi2-v5",
                "error_occurred": True
            }
        }
        
        return {
            "statusCode": 500,
            "headers": headers,
            "body": json.dumps(error_response, separators=(",", ":"))
        }
