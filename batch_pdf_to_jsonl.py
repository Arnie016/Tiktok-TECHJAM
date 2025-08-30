#!/usr/bin/env python3
"""
Batch PDF → JSONL generator with Amazon Kendra enrichment

What it does
- Scans one or more PDF directories
- Extracts text with PyMuPDF
- Heuristically identifies compliance-relevant features from PDF content
- For each candidate feature, queries Amazon Kendra to retrieve law snippets
- Produces positive and negative examples:
  - Positive: Law snippet(s) found for target jurisdictions → Needs Geo-Compliance
  - Negative: No relevant snippet found → Not Enough Information
- Always includes a "Law Context (structured JSON)" section in input
- Deduplicates by (input+output) hash and appends to output JSONL

CLI
  python batch_pdf_to_jsonl.py \
    --pdf-dirs pdfs /Users/hema/Desktop/pdf2 \
    --kendra-index-id KENDRA_INDEX_ID \
    --output sagemaker-finetune/data/train_refined_v3.jsonl \
    --region us-west-2 \
    --profile bedrock-561 \
    [--overwrite]

Notes
- Requires network access to Amazon Kendra.
- If Kendra returns nothing relevant, we still write a negative example with an empty law context array.
"""

import os
import re
import json
import time
import argparse
import hashlib
from pathlib import Path
from typing import List, Dict, Tuple, Optional

# PDF extraction backends
try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None
try:
    from pdfminer.high_level import extract_text as pdfminer_extract_text
except Exception:
    pdfminer_extract_text = None
try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None

try:
    import boto3
except Exception:
    boto3 = None  # Will error later if Kendra requested without boto3

DEFAULT_PDF_DIR = "pdfs"
DEFAULT_OUTPUT_FILE = "sagemaker-finetune/data/train.jsonl"

INSTRUCTION = (
    "Analyze the following software feature to determine its geo-compliance requirements. "
    "Provide the compliance flag, the relevant law, and the reason."
)

LAW_KEYWORDS = {
    "GDPR": [
        "gdpr", "general data protection regulation", "article 6", "article 7",
        "article 25", "article 33", "article 34", "article 44", "article 45",
        "article 46", "data portability", "controller", "processor", "supervisory authority"
    ],
    "DSA": [
        "digital services act", "dsa", "very large online platform", "vlop",
        "transparency report", "systemic risks", "algorithmic transparency",
        "content moderation", "notice and action"
    ],
    "AI Act": ["ai act", "high-risk ai", "general-purpose ai", "risk management", "conformity assessment"],
    "ePrivacy": ["eprivacy", "cookie", "consent for cookies", "electronic communications", "tracking"],
    "Child Safety": ["child sexual", "csam", "age verification", "minor", "youth", "age-appropriate"],
}

# Target jurisdictions for positive examples (matching hints)
TARGET_LAW_HINTS = {
    "EU DSA": ["digital services act", "dsa", "regulation (eu) 2022/2065", "vlop", "article 38", "article 34", "article 35", "article 16", "article 17", "article 40"],
    "CA Addiction/Minors": ["california", "protecting our kids", "minors", "addiction", "sb 976", "engagement", "infinite scroll", "autoplay"],
    "FL Online Protections": ["florida", "501.1737", "501.1738", "harmful to minors", "age verification"],
    "UT Social Media Regulation": ["utah", "hb 311", "social media regulation act", "curfew", "parental consent", "default privacy"],
    "US CSAM 2258A": ["18 u.s.c.", "2258a", "ncmec", "cybertipline", "preserve contents", "child sexual"],
}

FEATURE_PATTERNS: List[Tuple[str, List[str], str]] = [
    (
        "User Data Processing System",
        ["personal data", "data processing", "data collection", "data storage", "data transfer", "lawful basis", "data subject"],
        "Processing personal data of users requires strong data protection controls and lawful bases."
    ),
    (
        "Content Moderation Engine",
        ["content moderation", "illegal content", "notice and action", "remove content", "harmful content", "hate speech", "takedown"],
        "Large platforms must moderate illegal and harmful content and report on enforcement."
    ),
    (
        "Algorithmic Recommendation System",
        ["algorithm", "recommendation", "ranking", "personalization", "feed", "recommender"],
        "Recommendation systems require transparency and risk assessment for systemic risks."
    ),
    (
        "Age Verification Gateway",
        ["age verification", "minor", "underage", "youth", "age-appropriate", "parental consent"],
        "Age gates are required to protect minors and restrict access to certain content."
    ),
    (
        "Parental Consent Workflow",
        ["parental consent", "guardian", "verify parent", "consent workflow", "consent verification"],
        "Verified parental consent is required in some jurisdictions for minors' accounts."
    ),
    (
        "Curfew & Quiet Hours Enforcement",
        ["curfew", "quiet hours", "nightly", "default privacy", "sleep", "time window"],
        "Curfew and quiet hours may be mandated for minors; enforce time-based restrictions."
    ),
    (
        "Recommender Transparency Panel",
        ["recommender", "ranking parameters", "transparency", "explain", "modify parameters"],
        "Recommender systems require transparency and user controls in some regions (e.g., DSA)."
    ),
    (
        "Notice-and-Action Portal",
        ["illegal content", "notice", "action", "submit notice", "status tracking"],
        "Platforms must provide mechanisms to notify illegal content and track actions."
    ),
    (
        "Statement of Reasons Generator",
        ["statement of reasons", "inform the user", "decision justification", "removal notice"],
        "Users must receive a statement of reasons for moderation decisions (e.g., DSA)."
    ),
    (
        "Researcher Data Access",
        ["vetted researchers", "data access", "research api", "data sharing", "access framework"],
        "VLOPs must provide vetted researchers with access under defined conditions (DSA)."
    ),
    (
        "CSAM Reporting & Preservation",
        ["ncmec", "cybertipline", "child sexual", "preserve contents", "reporting pipeline"],
        "US law requires reporting apparent CSAM and preserving content upon request."
    ),
    (
        "Targeted Advertising Consent Manager",
        ["advertising", "ads", "targeting", "profiling", "consent", "opt-out", "opt in", "withdraw"],
        "Targeted ads require explicit, informed consent and easy withdrawal."
    ),
    (
        "Transparency Reporting Dashboard",
        ["transparency report", "reporting", "disclosure", "enforcement statistics", "risk assessment"],
        "Platforms must publish periodic transparency reports on content moderation and risks."
    ),
    (
        "Data Breach Notification System",
        ["breach", "incident", "notification", "supervisory authority", "72 hours", "notify"],
        "Personal data breaches must be assessed and reported within strict timelines."
    ),
    (
        "Risk Assessment Framework",
        ["risk assessment", "systemic risk", "risk management", "risk analysis", "risk evaluation"],
        "Platforms must assess and mitigate systemic risks to society and democracy."
    ),
    (
        "Audit Trail & Logging System",
        ["audit", "logging", "audit trail", "records", "documentation", "traceability"],
        "Compliance requires comprehensive audit trails and record-keeping."
    ),
    (
        "Data Retention Policy Engine",
        ["retention", "storage period", "data retention", "delete", "archival", "purge"],
        "Data retention policies must comply with legal requirements and user rights."
    ),
    (
        "Cross-Border Data Transfer Controls",
        ["cross-border", "international transfer", "data transfer", "adequacy", "safeguards"],
        "International data transfers require specific legal bases and safeguards."
    ),
    (
        "User Rights Management Portal",
        ["data subject rights", "access", "rectification", "erasure", "portability", "objection"],
        "Users have rights to access, correct, and delete their personal data."
    ),
    (
        "Consent Management Platform",
        ["consent", "opt-in", "opt-out", "withdraw consent", "consent withdrawal"],
        "Consent must be freely given, specific, informed, and easily withdrawable."
    ),
    (
        "Data Protection Impact Assessment",
        ["dpia", "impact assessment", "privacy impact", "risk to rights"],
        "High-risk processing requires formal impact assessments."
    ),
    (
        "Third-Party Data Sharing Controls",
        ["third party", "data sharing", "processor", "sub-processor", "vendor"],
        "Data sharing with third parties requires contracts and safeguards."
    ),
    (
        "Automated Decision-Making Controls",
        ["automated decision", "profiling", "algorithmic decision", "ai decision"],
        "Automated decisions affecting individuals require safeguards and human review."
    ),
    (
        "Data Minimization Engine",
        ["data minimization", "purpose limitation", "necessity", "proportionality"],
        "Data collection must be limited to what is necessary for the purpose."
    ),
    (
        "Security Controls & Encryption",
        ["security", "encryption", "access control", "authentication", "authorization"],
        "Appropriate technical and organizational security measures are required."
    ),
    (
        "Incident Response & Recovery",
        ["incident response", "recovery", "business continuity", "disaster recovery"],
        "Organizations must have incident response and recovery procedures."
    ),
    (
        "Compliance Monitoring Dashboard",
        ["compliance", "monitoring", "governance", "oversight", "compliance framework"],
        "Ongoing compliance monitoring and governance is required."
    ),
    (
        "User Notification System",
        ["notify user", "user notification", "inform user", "user communication"],
        "Users must be informed about data processing and their rights."
    ),
    (
        "Data Quality & Accuracy Controls",
        ["data quality", "accuracy", "data accuracy", "data integrity", "validation"],
        "Personal data must be accurate and kept up to date."
    ),
    (
        "Purpose Limitation Engine",
        ["purpose limitation", "original purpose", "new purpose", "compatible purpose"],
        "Data must only be processed for specified, explicit, and legitimate purposes."
    ),
    (
        "Accountability & Documentation",
        ["accountability", "documentation", "records", "demonstrate compliance"],
        "Organizations must demonstrate compliance and maintain documentation."
    ),
    (
        "Data Subject Request Handler",
        ["data subject request", "user request", "rights request", "access request"],
        "Organizations must respond to data subject requests within timelines."
    ),
    (
        "Breach Detection & Response",
        ["breach detection", "security incident", "data breach", "incident response"],
        "Organizations must detect and respond to security incidents promptly."
    ),
    (
        "Privacy by Design Controls",
        ["privacy by design", "privacy by default", "data protection by design"],
        "Privacy and data protection must be built into systems by design."
    ),
    (
        "Data Processing Register",
        ["processing register", "record of processing", "data inventory", "processing activities"],
        "Organizations must maintain records of processing activities."
    ),
    (
        "Supervisory Authority Communication",
        ["supervisory authority", "data protection authority", "regulator", "authority"],
        "Organizations must cooperate with supervisory authorities."
    ),
    (
        "Data Export & Portability",
        ["data export", "portability", "data portability", "export data"],
        "Users have the right to receive their data in a portable format."
    ),
    (
        "Consent Granularity Controls",
        ["granular consent", "specific consent", "separate consent", "consent granularity"],
        "Consent must be granular and specific to different processing purposes."
    ),
    (
        "Data Anonymization Engine",
        ["anonymization", "pseudonymization", "de-identification", "anonymize"],
        "Data anonymization can reduce compliance obligations."
    ),
    (
        "Legitimate Interest Assessment",
        ["legitimate interest", "balancing test", "interest assessment", "necessity"],
        "Legitimate interest processing requires balancing tests."
    ),
    (
        "Contract Management System",
        ["contract", "agreement", "data processing agreement", "dpa", "service agreement"],
        "Data processing contracts must include specific clauses."
    ),
    (
        "Training & Awareness Platform",
        ["training", "awareness", "staff training", "compliance training"],
        "Staff must be trained on data protection and compliance."
    ),
    (
        "Vendor Risk Assessment",
        ["vendor assessment", "supplier assessment", "third party risk", "vendor risk"],
        "Third-party vendors must be assessed for compliance risks."
    ),
    (
        "Data Classification Engine",
        ["data classification", "sensitive data", "special categories", "personal data"],
        "Data must be classified to determine appropriate safeguards."
    ),
    (
        "Access Control & Authentication",
        ["access control", "authentication", "authorization", "identity verification"],
        "Access to personal data must be controlled and authenticated."
    ),
    (
        "Data Loss Prevention",
        ["data loss prevention", "dlp", "data leakage", "prevent data loss"],
        "Organizations must prevent unauthorized data loss or leakage."
    ),
    (
        "Compliance Reporting System",
        ["compliance report", "regulatory report", "reporting", "compliance metrics"],
        "Organizations must report on compliance activities and metrics."
    ),
]

GENERIC_NAME_RE = re.compile(r"(Management System)$", re.IGNORECASE)
URL_RE = re.compile(r"https?://|www\.")


def extract_text(pdf_path: str) -> str:
    # Prefer PyMuPDF if available (faster, structured)
    if fitz is not None:
        try:
            doc = fitz.open(pdf_path)
            text = "".join(page.get_text() for page in doc)
            doc.close()
            if text:
                return text
        except Exception as e:
            print(f"! PyMuPDF failed for {pdf_path}: {e}")
    # Fallback to pdfminer.six if available
    if pdfminer_extract_text is not None:
        try:
            return pdfminer_extract_text(pdf_path) or ""
        except Exception as e:
            print(f"! pdfminer failed for {pdf_path}: {e}")
    # Fallback to pypdf if available
    if PdfReader is not None:
        try:
            reader = PdfReader(pdf_path)
            text_chunks = []
            for page in reader.pages:
                try:
                    text_chunks.append(page.extract_text() or "")
                except Exception:
                    continue
            text = "".join(text_chunks)
            if text:
                return text
        except Exception as e:
            print(f"! pypdf failed for {pdf_path}: {e}")
    print(f"! No PDF backend available for {pdf_path} (install PyMuPDF or pdfminer.six)")
    return ""


def infer_law(text_lower: str) -> Tuple[str, int]:
    best_law, best_score = "Unknown", 0
    for law, kws in LAW_KEYWORDS.items():
        score = sum(1 for kw in kws if kw in text_lower)
        if score > best_score:
            best_law, best_score = law, score
    return best_law, best_score


def detect_features(text: str) -> List[Dict[str, str]]:
    text_lower = text.lower()
    law, law_score = infer_law(text_lower)

    # MUCH MORE AGGRESSIVE: extract even with minimal law signal
    # Only skip if absolutely no law keywords found
    if law_score < 1:
        # Try to infer law from broader context
        if any(word in text_lower for word in ["platform", "online", "digital", "social media", "app", "service"]):
            law = "DSA"  # Default to DSA for online platforms
            law_score = 1
        else:
            return []

    features: List[Dict[str, str]] = []
    for feature_name, kws, generic_reason in FEATURE_PATTERNS:
        hits = sum(1 for kw in kws if kw in text_lower)
        # MUCH MORE AGGRESSIVE: require only 1 hit instead of 2
        if hits < 1:
            continue
        # Build a concise description from nearby sentences containing strongest keywords
        description = feature_name
        try:
            sentences = re.split(r"(?<=[.!?])\s+", text)
            matched = [s for s in sentences if any(kw in s.lower() for kw in kws)]
            if matched:
                snippet = matched[0].strip()
                description = snippet
        except Exception:
            pass

        # Filters - MUCH MORE PERMISSIVE
        if URL_RE.search(description):
            continue
        # Much more permissive bounds
        if len(description) < 20 or len(description) > 600:
            continue
        # Remove the generic name filter entirely
        # if GENERIC_NAME_RE.search(feature_name) and law_score < 2:
        #     continue

        if law == "GDPR":
            compliance_flag = "Needs Geo-Compliance"
            reason = "Feature touches personal data; GDPR imposes strict obligations across the EU."
        elif law == "DSA":
            compliance_flag = "Needs Geo-Compliance"
            reason = "Large platform obligations under DSA apply in the EU, requiring governance controls."
        elif law == "AI Act":
            compliance_flag = "Needs Human Review"
            reason = "Potentially within AI Act scope; risk classification requires expert review."
        elif law == "Child Safety":
            compliance_flag = "Needs Geo-Compliance"
            reason = "Child safety obligations mandate proactive detection and reporting in the EU."
        elif law == "ePrivacy":
            compliance_flag = "Needs Geo-Compliance"
            reason = "Tracking/communications require consent and safeguards under ePrivacy rules."
        else:
            # Should not happen due to law_score gate
            continue

        features.append({
            "feature_name": feature_name,
            "feature_description": description,
            "compliance_flag": compliance_flag,
            "law": law,
            "reason": reason,
        })

    return features


def to_jsonl(entry: Dict[str, str], law_context: List[Dict[str, str]]) -> str:
    law_ctx_str = json.dumps(law_context, ensure_ascii=False)
    feature_input = (
        f"Feature Name: {entry['feature_name']}\n"
        f"Feature Description: {entry['feature_description']}\n"
        f"Source: {entry.get('source', 'N/A')}\n\n"
        f"Law Context (structured JSON):\n{law_ctx_str}"
    )
    output_obj = {
        "compliance_flag": entry["compliance_flag"],
        "law": entry["law"],
        "reason": entry["reason"],
    }
    line = {
        "instruction": INSTRUCTION,
        "input": feature_input,
        "output": json.dumps(output_obj, ensure_ascii=False),
    }
    return json.dumps(line, ensure_ascii=False)


def build_kendra_client(region: str, profile: Optional[str]):
    if boto3 is None:
        raise RuntimeError("boto3 is required for Kendra enrichment but is not installed.")
    if profile:
        session = boto3.Session(profile_name=profile, region_name=region)
    else:
        session = boto3.Session(region_name=region)
    return session.client("kendra")


def query_kendra_for_feature(kendra, index_id: str, 
                            feature_name: str, description: str, 
                            max_items: int = 5) -> List[Dict[str, str]]:
    q = f"{feature_name}. {description}"
    try:
        resp = kendra.query(IndexId=index_id, QueryText=q, PageSize=max_items)
    except Exception as e:
        print(f"! Kendra query failed: {e}")
        return []

    contexts: List[Dict[str, str]] = []
    for item in resp.get("ResultItems", []):
        attrs = item.get("DocumentAttributes", [])
        title = item.get("DocumentTitle", {}).get("Text") or None
        excerpt = item.get("DocumentExcerpt", {}).get("Text") or ""
        source_uri = None
        score = (item.get("ScoreAttributes", {}) or {}).get("ScoreConfidence") or None
        for a in attrs:
            if a.get("Key") == "_source_uri":
                source_uri = a.get("Value", {}).get("StringValue")
                break
        if excerpt:
            contexts.append({
                "title": title or "",
                "citation": None,
                "snippet": excerpt.strip(),
                "uri": source_uri,
                "score": score,
            })
    return contexts


def match_target_law(law_context: List[Dict[str, str]]) -> Optional[str]:
    """Match law context to target jurisdictions for positive examples."""
    if not law_context:
        return None
    
    text_blob = " \n ".join([
        " ".join([c.get("title") or "", c.get("snippet") or ""]) for c in law_context
    ]).lower()
    
    # STRICT MATCHING: Only return positive if we have strong evidence of target jurisdiction
    for law_name, hints in TARGET_LAW_HINTS.items():
        # Count how many hints match
        matches = sum(1 for hint in hints if hint in text_blob)
        # Require at least 2 hints for positive match to avoid false positives
        if matches >= 2:
            return law_name
    
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf-dirs", nargs="+", default=[DEFAULT_PDF_DIR], help="One or more PDF directories to scan")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_FILE, help="Output JSONL path")
    parser.add_argument("--kendra-index-id", default=os.environ.get("KENDRA_INDEX_ID"), help="Amazon Kendra IndexId")
    parser.add_argument("--region", default=os.environ.get("AWS_REGION", "us-west-2"))
    parser.add_argument("--profile", default=os.environ.get("AWS_PROFILE"))
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    # Validate inputs
    pdf_dirs = [Path(p) for p in args.pdf_dirs]
    for d in pdf_dirs:
        if not d.exists():
            print(f"! Folder not found: {d}")
            return

    output_file = args.output
    index_id = args.kendra_index_id
    if not index_id:
        raise RuntimeError("Kendra IndexId is required. Pass --kendra-index-id or set KENDRA_INDEX_ID.")

    # Kendra client
    kendra = build_kendra_client(args.region, args.profile)

    # Build existing dedupe set from current output file
    seen = set()
    if os.path.exists(output_file) and not args.overwrite:
        with open(output_file, "r") as f:
            for line in f:
                try:
                    obj = json.loads(line)
                    inp = obj.get("input", "")
                    out = obj.get("output", "")
                    key = hashlib.sha256((inp + out).encode("utf-8")).hexdigest()
                    seen.add(key)
                except Exception:
                    continue

    new_lines: List[str] = []

    for pdf_dir in pdf_dirs:
        pdf_paths = list(pdf_dir.glob("*.pdf")) + list(pdf_dir.glob("*.PDF"))
        for pdf_path in sorted(pdf_paths):
            print(f"→ Processing {pdf_path.name}")
            text = extract_text(str(pdf_path))
            if not text:
                continue
            features = detect_features(text)
            print(f"  Accepted {len(features)} high-confidence features")

            for feat in features:
                # Enrich with Kendra
                law_ctx = query_kendra_for_feature(
                    kendra,
                    index_id,
                    feat["feature_name"],
                    feat["feature_description"],
                    max_items=8,
                )

                # Decide label (positive/negative) based on target law match
                matched_law = match_target_law(law_ctx) if law_ctx else None
                def _shorten_snippet(txt: str, limit: int = 220) -> str:
                    t = (txt or "").strip().replace("\n", " ")
                    if len(t) <= limit:
                        return t
                    # try cut at sentence end
                    dot = t.find('.')
                    if 60 < dot < limit:
                        return t[:dot+1]
                    return t[:limit].rstrip() + "…"

                if matched_law:
                    feat["compliance_flag"] = "Needs Geo-Compliance"
                    feat["law"] = matched_law
                    if law_ctx:
                        top = law_ctx[0]
                        title = top.get("title") or matched_law
                        snippet = _shorten_snippet(top.get("snippet", ""))
                        feat["reason"] = f"{title}: {snippet} Therefore, '{feat['feature_name']}' must implement region-specific controls."
                    else:
                        feat["reason"] = "Relevant law indicates geo obligations; feature needs region-specific controls."
                else:
                    feat["compliance_flag"] = "Not Enough Information"
                    feat["law"] = "N/A"
                    if law_ctx:
                        top = law_ctx[0]
                        title = top.get("title") or "Law snippet"
                        snippet = _shorten_snippet(top.get("snippet", ""))
                        feat["reason"] = f"{title}: {snippet} No clear match to target jurisdictions; additional law context required."
                    else:
                        feat["reason"] = "No relevant law snippet retrieved for target jurisdictions; more law context needed."

                feat["source"] = pdf_path.name

                jsonl_line = to_jsonl(feat, law_ctx or [])
                key = hashlib.sha256(jsonl_line.encode("utf-8")).hexdigest()
                if key in seen:
                    continue
                seen.add(key)
                new_lines.append(jsonl_line)

    if not new_lines:
        print("No new entries to add.")
        return

    # Write output (append or overwrite)
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    mode = "w" if args.overwrite else "a"
    with open(output_file, mode) as f:
        for line in new_lines:
            f.write(line + "\n")

    print(f"\n✅ Added {len(new_lines)} new high-quality entries to {output_file}")

if __name__ == "__main__":
    main()
