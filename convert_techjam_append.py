#!/usr/bin/env python3
import json
import os
import hashlib
from typing import List, Dict, Optional

# Set environment
os.environ['AWS_PROFILE'] = 'bedrock-561'
os.environ['KENDRA_INDEX_ID'] = '2885d201-f5ab-4f85-96cf-555c1fc6ff07'

try:
    import boto3
except ImportError:
    import subprocess
    subprocess.run(['pip', 'install', 'boto3'], check=True)
    import boto3

INSTRUCTION = (
    "Analyze the following software feature to determine its geo-compliance requirements. "
    "Provide the compliance flag, the relevant law, and the reason."
)

TARGET_LAW_HINTS = {
    "EU DSA": ["digital services act", "dsa", "regulation (eu) 2022/2065", "vlop", "article 38", "article 34", "article 35", "article 16", "article 17", "article 40"],
    "CA Addiction/Minors": ["california", "protecting our kids", "minors", "addiction", "sb 976", "engagement", "infinite scroll", "autoplay"],
    "FL Online Protections": ["florida", "501.1737", "501.1738", "harmful to minors", "age verification"],
    "UT Social Media Regulation": ["utah", "hb 311", "social media regulation act", "curfew", "parental consent", "default privacy"],
    "US CSAM 2258A": ["18 u.s.c.", "2258a", "ncmec", "cybertipline", "preserve contents", "child sexual"],
}

def build_kendra_client(region: str, profile: str):
    session = boto3.Session(profile_name=profile, region_name=region)
    return session.client("kendra")

def query_kendra_for_feature(kendra, index_id: str, feature_name: str, description: str, max_items: int = 8) -> List[Dict[str, str]]:
    try:
        query_text = f"{feature_name}. {description}"
        resp = kendra.query(IndexId=index_id, QueryText=query_text, PageSize=max_items)
        
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
    except Exception as e:
        print(f"! Kendra query failed: {e}")
        return []

def match_target_law(law_context: List[Dict[str, str]]) -> Optional[str]:
    if not law_context:
        return None
    
    text_blob = " \n ".join([
        " ".join([c.get("title") or "", c.get("snippet") or ""]) for c in law_context
    ]).lower()
    
    for law_name, hints in TARGET_LAW_HINTS.items():
        matches = sum(1 for hint in hints if hint in text_blob)
        if matches >= 2:
            return law_name
    return None

def _shorten_snippet(txt: str, limit: int = 220) -> str:
    t = (txt or "").strip().replace("\n", " ")
    if len(t) <= limit:
        return t
    dot = t.find('.')
    if 60 < dot < limit:
        return t[:dot+1]
    return t[:limit].rstrip() + "…"

def map_techjam_to_compliance(techjam_entry: Dict, law_ctx: List[Dict[str, str]]) -> Dict:
    needs_geo = techjam_entry.get("needs_geo_logic", "no")
    regulations = techjam_entry.get("regulations", [])
    
    matched_law = match_target_law(law_ctx) if law_ctx else None
    
    if matched_law:
        compliance_flag = "Needs Geo-Compliance"
        law = matched_law
        if law_ctx:
            top = law_ctx[0]
            title = top.get("title") or matched_law
            snippet = _shorten_snippet(top.get("snippet", ""))
            reason = f"{title}: {snippet} Therefore, '{techjam_entry['title']}' must implement region-specific controls."
        else:
            reason = f"Relevant law indicates geo obligations; '{techjam_entry['title']}' needs region-specific controls."
    elif needs_geo == "yes":
        compliance_flag = "Needs Geo-Compliance"
        if regulations:
            for reg in regulations:
                if "DSA" in reg or "Digital Services Act" in reg:
                    law = "EU DSA"
                    break
                elif "California" in reg or "SB-976" in reg:
                    law = "CA Addiction/Minors"
                    break
                elif "Florida" in reg:
                    law = "FL Online Protections"
                    break
                elif "Utah" in reg:
                    law = "UT Social Media Regulation"
                    break
                elif "NCMEC" in reg or "CSAM" in reg:
                    law = "US CSAM 2258A"
                    break
            else:
                law = "Target Jurisdiction"
        else:
            law = "Target Jurisdiction"
        reason = techjam_entry.get("reasoning", "Region-specific legal obligation stated; requires geo logic.")
    elif needs_geo == "ambiguous":
        compliance_flag = "Needs Human Review"
        law = "N/A"
        if law_ctx:
            top = law_ctx[0]
            title = top.get("title") or "Law snippet"
            snippet = _shorten_snippet(top.get("snippet", ""))
            reason = f"{title}: {snippet} Regional scoping mentioned but legal intent not explicit; requires human review."
        else:
            reason = techjam_entry.get("reasoning", "Regional scoping mentioned but legal intent not explicit; requires human review.")
    else:
        compliance_flag = "Not Enough Information"
        law = "N/A"
        if law_ctx:
            top = law_ctx[0]
            title = top.get("title") or "Law snippet"
            snippet = _shorten_snippet(top.get("snippet", ""))
            reason = f"{title}: {snippet} No clear match to target jurisdictions; additional law context required."
        else:
            reason = "No relevant law snippet retrieved for target jurisdictions; more law context needed."
    
    return {
        "compliance_flag": compliance_flag,
        "law": law,
        "reason": reason,
    }

def to_jsonl(entry: Dict[str, str], law_context: List[Dict[str, str]]) -> str:
    law_ctx_str = json.dumps(law_context, ensure_ascii=False)
    feature_input = (
        f"Feature Name: {entry['feature_name']}\n"
        f"Feature Description: {entry['feature_description']}\n"
        f"Source: {entry.get('source', 'techjam_dataset.json')}\n\n"
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

def main():
    print("🚀 Starting techjam conversion and append...")

    # Load techjam data
    with open('sagemaker-finetune/data/techjam_dataset.json', 'r') as f:
        techjam_data = json.load(f)

    print(f"Loaded {len(techjam_data)} entries from techjam_dataset.json")

    # Build existing dedupe set from v4
    seen = set()
    with open('sagemaker-finetune/data/train_refined_v4.jsonl', "r") as f:
        for line in f:
            try:
                obj = json.loads(line)
                inp = obj.get("input", "")
                out = obj.get("output", "")
                key = hashlib.sha256((inp + out).encode("utf-8")).hexdigest()
                seen.add(key)
            except Exception:
                continue

    print(f"Found {len(seen)} existing entries for deduplication")

    # Kendra client
    kendra = build_kendra_client("us-west-2", "bedrock-561")
    index_id = "2885d201-f5ab-4f85-96cf-555c1fc6ff07"
    print(f"Kendra client initialized for index: {index_id}")

    new_lines: List[str] = []

    for i, techjam_entry in enumerate(techjam_data):
        if i % 50 == 0:
            print(f"Processing entry {i+1}/{len(techjam_data)}")
        
        # Enrich with Kendra
        law_ctx = query_kendra_for_feature(
            kendra,
            index_id,
            techjam_entry["title"],
            techjam_entry["description"],
            max_items=8,
        )
        
        # Map to our format
        compliance_info = map_techjam_to_compliance(techjam_entry, law_ctx)
        
        # Create entry
        entry = {
            "feature_name": techjam_entry["title"],
            "feature_description": techjam_entry["description"],
            "source": "techjam_dataset.json",
            **compliance_info
        }
        
        # Convert to JSONL
        jsonl_line = to_jsonl(entry, law_ctx)
        key = hashlib.sha256(jsonl_line.encode("utf-8")).hexdigest()
        
        if key in seen:
            continue
        seen.add(key)
        new_lines.append(jsonl_line)

    # Append new entries to v4 file
    with open('sagemaker-finetune/data/train_refined_v4.jsonl', 'a') as f:
        for line in new_lines:
            f.write(line + '\n')

    print(f"✅ Appended {len(new_lines)} new entries to train_refined_v4.jsonl")

    # Show stats
    yes_count = sum(1 for line in new_lines if '"compliance_flag": "Needs Geo-Compliance"' in line)
    no_count = sum(1 for line in new_lines if '"compliance_flag": "Not Enough Information"' in line)
    ambiguous_count = sum(1 for line in new_lines if '"compliance_flag": "Needs Human Review"' in line)

    print(f"📊 Breakdown of new entries:")
    print(f"  - Needs Geo-Compliance: {yes_count}")
    print(f"  - Not Enough Information: {no_count}")
    print(f"  - Needs Human Review: {ambiguous_count}")
    print(f"  - Total dataset now: {556 + len(new_lines)} entries")
    print(f"🎉 Conversion complete!")

if __name__ == "__main__":
    main()

