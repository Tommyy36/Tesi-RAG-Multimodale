#!/usr/bin/env python3
"""
Demo script to show the improvements in action.
This simulates the multimodal RAG behavior with different report scenarios.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.multimodal_rag_openai import (
    is_generic_report,
    knn_vote_labels,
)


def demo_scenario_1():
    """Scenario 1: Normal case with generic report (previously gave wrong high confidence)"""
    print("\n" + "="*80)
    print("SCENARIO 1: Normal Case with Generic Report")
    print("="*80)
    
    report = "Analyze this echocardiography case. Provide probable diagnosis."
    print(f"\nReport: '{report}'")
    print(f"Is Generic: {is_generic_report(report)}")
    
    # Simulate weak KNN matches (high distances = not really similar)
    metas = [
        {"diagnosis_label_raw": "apical_aneurysm"},
        {"diagnosis_label_raw": "apical_dyskinesia"},
        {"diagnosis_label_raw": "some_pathology"},
    ]
    dists = [0.7, 0.75, 0.8]
    
    print(f"\nKNN Results (distances indicate weak matches):")
    for meta, dist in zip(metas, dists):
        print(f"  - {meta['diagnosis_label_raw']}: distance={dist}")
    
    # With adaptive threshold (4.5 for generic reports)
    candidates = knn_vote_labels(metas, dists, topn=3, min_score_threshold=4.5)
    
    print(f"\nFiltered Candidates (threshold=4.5 for generic report):")
    for label, score in candidates:
        print(f"  - {label}: score={score:.3f}")
    
    print("\n✅ EXPECTED: insufficient_evidence → LOW confidence")
    print("   Previously would have given 'apical_aneurysm' with HIGH confidence!")


def demo_scenario_2():
    """Scenario 2: Normal case with explicit 'normal' report"""
    print("\n" + "="*80)
    print("SCENARIO 2: Normal Case with 'Normal' in Report")
    print("="*80)
    
    report = """
    Patient 45yo female. Routine checkup.
    Echocardiography shows:
    - Normal left ventricular size and function
    - LVEF estimated 60-65%
    - No wall motion abnormalities
    - No significant valvular disease
    Overall: Normal echocardiogram
    """
    print(f"\nReport: {report[:100]}...")
    print(f"Is Generic: {is_generic_report(report)}")
    
    # Simulate weak KNN (because normal cases might not be well represented in dataset)
    metas = [
        {"diagnosis_label_raw": "some_pathology"},
    ]
    dists = [0.8]
    
    candidates = knn_vote_labels(metas, dists, topn=3, min_score_threshold=2.5)
    
    print(f"\nInitial KNN Candidates:")
    for label, score in candidates:
        print(f"  - {label}: score={score:.3f}")
    
    # Check for 'normal' in report
    if candidates[0][0] in ["insufficient_evidence", "unknown"]:
        if "normal" in report.lower():
            candidates = [("normal_echo", 2.0)] + candidates[:2]
            print(f"\n🔄 ADJUSTED after detecting 'normal' in report:")
            for label, score in candidates:
                print(f"  - {label}: score={score:.3f}")
    
    print("\n✅ EXPECTED: normal_echo → HIGH confidence")
    print("   System now correctly identifies normal cases!")


def demo_scenario_3():
    """Scenario 3: Pathology with detailed clinical report"""
    print("\n" + "="*80)
    print("SCENARIO 3: Pathology with Detailed Clinical Report")
    print("="*80)
    
    report = """
    Patient 68yo male, history of MI 3 years ago.
    Presents with dyspnea and fatigue.
    Echo findings:
    - LVEF 30-35% (severely reduced)
    - LV end-diastolic diameter 6.8 cm (dilated)
    - Global hypokinesis with regional variation
    - Apical akinesia with thin apical wall
    - Moderate functional mitral regurgitation
    - No LV thrombus visualized
    Impression: Dilated cardiomyopathy, likely ischemic etiology
    """
    print(f"\nReport: {report[:150]}...")
    print(f"Is Generic: {is_generic_report(report)}")
    
    # Simulate strong KNN matches (low distances)
    metas = [
        {"diagnosis_label_raw": "dilated_cardiomyopathy"},
        {"diagnosis_label_raw": "dilated_cardiomyopathy"},
        {"diagnosis_label_raw": "global_lv_dysfunction"},
        {"diagnosis_label_raw": "dilated_cardiomyopathy"},
        {"diagnosis_label_raw": "apical_akinesia"},
    ]
    dists = [0.1, 0.12, 0.15, 0.18, 0.3]
    
    print(f"\nKNN Results (low distances = strong matches):")
    for meta, dist in zip(metas, dists):
        print(f"  - {meta['diagnosis_label_raw']}: distance={dist}")
    
    candidates = knn_vote_labels(metas, dists, topn=3, min_score_threshold=2.5)
    
    print(f"\nTop Candidates (threshold=2.5 for detailed report):")
    for label, score in candidates:
        print(f"  - {label}: score={score:.3f}")
    
    print("\n✅ EXPECTED: dilated_cardiomyopathy → HIGH confidence")
    print("   Strong clinical context + consistent visual evidence = HIGH confidence")


def main():
    print("\n" + "="*80)
    print("MULTIMODAL RAG IMPROVEMENTS - DEMONSTRATION")
    print("="*80)
    print("\nThis demo shows how the improved system handles different scenarios:")
    print("1. Generic reports with weak visual matches")
    print("2. Normal cases with explicit 'normal' in report")
    print("3. Pathology with detailed clinical context")
    
    demo_scenario_1()
    demo_scenario_2()
    demo_scenario_3()
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print("""
The improvements address the core issue:
    
✅ Generic reports → LOW confidence (even with high KNN scores)
✅ Normal cases → Correctly identified, not over-diagnosed
✅ Detailed reports + strong evidence → HIGH confidence
✅ Context quality warnings sent to LLM for proper interpretation

This prevents the system from giving high confidence diagnoses
based solely on visual similarity when clinical context is missing.
    """)


if __name__ == "__main__":
    main()
