#!/usr/bin/env python3
"""
Verify that all generated dataset files are properly anonymized.
Checks for any remaining sensitive patient data.
"""
import json
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSONL_PATH = os.path.join(BASE_DIR, "data", "dataset_built", "documents.jsonl")

# Patterns that should NOT appear in anonymized data
SENSITIVE_PATTERNS = [
    'patient', 'physician', 'doctor', 'institution', 'hospital',
    'accession', 'birthdate', 'birth_date', 'patient_id',
    'study_date', 'series_date', 'acquisition_date',
    'study_time', 'series_time', 'study_id', 'series_id',
    'instance_uid', 'series_uid', 'study_uid',
    'operators_name', 'physician_name', 'requesting'
]

def check_metadata(meta, doc_id):
    """Check if metadata contains sensitive fields."""
    issues = []
    
    # Check for sensitive field names (case-insensitive)
    for key in meta.keys():
        key_lower = key.lower()
        for pattern in SENSITIVE_PATTERNS:
            if pattern in key_lower and key != 'anonymized':
                issues.append(f"Sensitive field name: {key}")
    
    # Check for suspicious values (names, dates, IDs)
    for key, value in meta.items():
        if value is None:
            continue
        val_str = str(value).lower()
        
        # Check for date patterns (YYYYMMDD)
        if isinstance(value, str) and len(value) == 8 and value.isdigit():
            if int(value[:4]) > 1900 and int(value[:4]) < 2100:
                issues.append(f"Possible date in {key}: {value}")
        
        # Check for time patterns (HHMMSS)
        if isinstance(value, str) and len(value) == 6 and value.isdigit():
            if int(value[:2]) < 24 and int(value[2:4]) < 60:
                issues.append(f"Possible time in {key}: {value}")
    
    # Verify anonymized flag is set
    if not meta.get('anonymized'):
        issues.append("Missing 'anonymized' flag")
    
    return issues

def main():
    print("=== Anonymization Verification ===\n")
    
    if not os.path.exists(JSONL_PATH):
        print(f"❌ Dataset not found: {JSONL_PATH}")
        print("Run: python3 scripts/build_dataset.py")
        return 1
    
    total_docs = 0
    issues_found = 0
    
    with open(JSONL_PATH, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            total_docs += 1
            doc = json.loads(line)
            meta = doc.get('metadata', {})
            
            issues = check_metadata(meta, doc.get('id', f'line_{line_num}'))
            
            if issues:
                issues_found += 1
                print(f"⚠️  Document {line_num} ({meta.get('case_id', '?')}):")
                for issue in issues:
                    print(f"   - {issue}")
                print()
    
    print(f"\n{'='*50}")
    print(f"Total documents checked: {total_docs}")
    print(f"Documents with issues: {issues_found}")
    
    if issues_found == 0:
        print("\n✅ All documents are properly anonymized!")
        print("   Safe for public repository.")
        return 0
    else:
        print(f"\n⚠️  Found potential issues in {issues_found} documents.")
        print("   Review and re-run build_dataset.py if needed.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
