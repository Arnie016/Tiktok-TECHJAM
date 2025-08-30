#!/usr/bin/env python3
"""
Convert TechJam_2.jsonl to match the main training file format and append to train_refined_v4.jsonl
"""

import json
import os

def convert_techjam_format_to_main_format(techjam_entry):
    """
    Convert TechJam_2.jsonl format to match train_refined_v4.jsonl format
    """
    # Extract data from TechJam format
    title = techjam_entry.get('title', '')
    instruction = techjam_entry.get('instruction', '')
    input_text = techjam_entry.get('input', '')
    output_data = techjam_entry.get('output', {})
    
    # Convert to main format
    main_format = {
        "instruction": instruction,
        "input": f"Feature Name: {title}\nFeature Description: {input_text}\n\nLaw Context (structured JSON):\n[]",  # Empty law context for now
        "output": json.dumps({
            "compliance_flag": "Needs Geo-Compliance" if output_data.get('needs_geo_logic') == 'yes' else "No Geo-Compliance Required",
            "law": output_data.get('regulations', ['Unknown'])[0] if output_data.get('regulations') else "Unknown",
            "reason": f"{output_data.get('reasoning', '')} Jurisdiction: {output_data.get('jurisdiction', 'Unknown')}."
        })
    }
    
    return main_format

def main():
    # File paths
    techjam_file = "sagemaker-finetune/data/TechJam_2.jsonl"
    main_file = "sagemaker-finetune/data/train_refined_v4.jsonl"
    output_file = "sagemaker-finetune/data/train_refined_v5.jsonl"
    
    # Read TechJam data
    print("Reading TechJam_2.jsonl...")
    techjam_entries = []
    with open(techjam_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                techjam_entries.append(json.loads(line))
    
    print(f"Found {len(techjam_entries)} entries in TechJam_2.jsonl")
    
    # Convert TechJam entries to main format
    print("Converting TechJam entries to main format...")
    converted_entries = []
    for entry in techjam_entries:
        try:
            converted = convert_techjam_format_to_main_format(entry)
            converted_entries.append(converted)
        except Exception as e:
            print(f"Error converting entry {entry.get('id', 'unknown')}: {e}")
    
    print(f"Successfully converted {len(converted_entries)} entries")
    
    # Read existing main training data
    print("Reading existing train_refined_v4.jsonl...")
    main_entries = []
    with open(main_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                main_entries.append(json.loads(line))
    
    print(f"Found {len(main_entries)} entries in train_refined_v4.jsonl")
    
    # Combine and write to new file
    print("Combining datasets...")
    all_entries = main_entries + converted_entries
    
    print(f"Writing {len(all_entries)} total entries to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        for entry in all_entries:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    
    print(f"✅ Successfully created {output_file}")
    print(f"📊 Summary:")
    print(f"   - Original training data: {len(main_entries)} entries")
    print(f"   - TechJam data added: {len(converted_entries)} entries")
    print(f"   - Total combined: {len(all_entries)} entries")
    
    # Create backup of original
    backup_file = "sagemaker-finetune/data/train_refined_v4_backup.jsonl"
    print(f"Creating backup of original file as {backup_file}...")
    with open(backup_file, 'w', encoding='utf-8') as f:
        for entry in main_entries:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    
    print("✅ Backup created successfully!")

if __name__ == "__main__":
    main()
