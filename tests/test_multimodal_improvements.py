"""
Test improvements to multimodal RAG system for handling cases without detailed reports.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.multimodal_rag_openai import (
    is_generic_report,
    has_explicit_normal_findings,
    knn_vote_labels,
)


class TestGenericReportDetection:
    """Test detection of generic/minimal clinical reports."""
    
    def test_generic_short_report(self):
        """Short generic report should be detected as generic."""
        report = "Analyze this echocardiography case. Provide probable diagnosis."
        assert is_generic_report(report) is True
    
    def test_generic_analysis_instruction(self):
        """Generic analysis instruction should be detected."""
        report = "Analyze this case and provide differential diagnosis."
        assert is_generic_report(report) is True
    
    def test_detailed_clinical_report(self):
        """Detailed clinical report should not be generic."""
        report = """
        Patient presents with dyspnea on exertion for 3 months.
        Past medical history includes hypertension and diabetes.
        Physical exam reveals bilateral crackles and elevated JVP.
        Echocardiography shows reduced LVEF approximately 35-40%,
        with global hypokinesis and moderate mitral regurgitation.
        Left ventricular end-diastolic diameter is 6.2 cm.
        """
        assert is_generic_report(report) is False
    
    def test_borderline_report(self):
        """Report with some details but short should be detected."""
        report = "Patient with chest pain. Echo shows some wall motion abnormalities."
        # This is short (<100 chars after strip), so should be generic
        assert is_generic_report(report) is True


class TestExplicitNormalDetection:
    """Test detection of reports with explicit normal findings."""
    
    def test_detailed_normal_report(self):
        """Report with explicit normal findings should be detected."""
        report = """
        The patient is a 35-year-old male with no relevant past medical history.
        He reports no symptoms at rest or during daily activities.
        Blood pressure is 120/80 mmHg and heart rate is 72 beats per minute,
        both within normal physiological ranges.
        Routine laboratory tests are within normal limits.
        """
        assert has_explicit_normal_findings(report) is True
    
    def test_short_normal_mention(self):
        """Short report with single 'normal' mention should not trigger."""
        report = "Echo looks normal."
        assert has_explicit_normal_findings(report) is False
    
    def test_pathology_report(self):
        """Pathology report should not trigger normal detection."""
        report = """
        Patient presents with dyspnea and chest pain for 3 weeks.
        Echo shows reduced LVEF 35%, global hypokinesis, dilated LV.
        Moderate mitral regurgitation present.
        """
        assert has_explicit_normal_findings(report) is False
    
    def test_multiple_normal_indicators(self):
        """Report with multiple normal indicators should be detected."""
        report = """
        Patient asymptomatic, no complaints.
        Physical exam unremarkable.
        All vital signs within normal range.
        Laboratory results within normal limits.
        """
        assert has_explicit_normal_findings(report) is True


class TestKNNVoting:
    """Test KNN voting with threshold filtering."""
    
    def test_strong_candidates_pass_threshold(self):
        """Strong KNN candidates should pass threshold."""
        metas = [
            {"diagnosis_label_raw": "dilated_cardiomyopathy"},
            {"diagnosis_label_raw": "dilated_cardiomyopathy"},
            {"diagnosis_label_raw": "dilated_cardiomyopathy"},
            {"diagnosis_label_raw": "dilated_cardiomyopathy"},
            {"diagnosis_label_raw": "normal"},
        ]
        dists = [0.1, 0.15, 0.2, 0.25, 0.8]
        
        candidates = knn_vote_labels(metas, dists, topn=3, min_score_threshold=2.5)
        
        # Should have dilated_cardiomyopathy as top (4 cases with low distance)
        assert candidates[0][0] == "dilated_cardiomyopathy"
        assert candidates[0][1] > 2.5
    
    def test_weak_candidates_filtered(self):
        """Weak KNN candidates below threshold should be filtered."""
        metas = [
            {"diagnosis_label_raw": "pathology_a"},
            {"diagnosis_label_raw": "pathology_b"},
            {"diagnosis_label_raw": "pathology_c"},
        ]
        # High distances = low weights
        dists = [0.9, 0.95, 0.98]
        
        candidates = knn_vote_labels(metas, dists, topn=3, min_score_threshold=2.5)
        
        # Should return insufficient_evidence when all filtered
        assert candidates[0][0] == "insufficient_evidence"
    
    def test_empty_input(self):
        """Empty input should return unknown."""
        candidates = knn_vote_labels([], [], topn=3)
        assert candidates[0][0] == "unknown"
    
    def test_threshold_adjustment(self):
        """Higher threshold should filter more candidates."""
        metas = [
            {"diagnosis_label_raw": "diagnosis_a"},
            {"diagnosis_label_raw": "diagnosis_a"},
        ]
        dists = [0.4, 0.45]
        
        # With low threshold
        candidates_low = knn_vote_labels(metas, dists, topn=3, min_score_threshold=1.0)
        assert len(candidates_low) > 0 and candidates_low[0][0] == "diagnosis_a"
        
        # With high threshold (should filter out)
        candidates_high = knn_vote_labels(metas, dists, topn=3, min_score_threshold=5.0)
        assert candidates_high[0][0] == "insufficient_evidence"


class TestIntegrationScenarios:
    """Integration tests for realistic scenarios."""
    
    def test_normal_case_with_generic_report(self):
        """Normal case with generic report should handle gracefully."""
        # Simulate weak KNN matches
        metas = [
            {"diagnosis_label_raw": "some_pathology"},
            {"diagnosis_label_raw": "another_pathology"},
        ]
        dists = [0.7, 0.75]
        
        candidates = knn_vote_labels(metas, dists, topn=3, min_score_threshold=4.5)
        
        # Should indicate insufficient evidence
        assert candidates[0][0] == "insufficient_evidence"
    
    def test_normal_case_with_marginal_knn_score(self):
        """Normal case with marginal KNN score (like 4.0) should be rejected with generic report."""
        # This simulates the real case: score=4.0 with generic report
        metas = [
            {"diagnosis_label_raw": "apical_aneurysm"},
            {"diagnosis_label_raw": "apical_aneurysm"},
            {"diagnosis_label_raw": "apical_dyskinesia"},
        ]
        # Distances that produce score around 4.0
        dists = [0.25, 0.3, 0.35]
        
        # With high threshold for generic reports (4.5)
        candidates = knn_vote_labels(metas, dists, topn=3, min_score_threshold=4.5)
        
        # Should be filtered out as insufficient
        assert candidates[0][0] == "insufficient_evidence"
    
    def test_pathology_with_detailed_report(self):
        """Pathology with strong matches should be confident."""
        metas = [
            {"diagnosis_label_raw": "apical_aneurysm"},
            {"diagnosis_label_raw": "apical_aneurysm"},
            {"diagnosis_label_raw": "apical_aneurysm"},
            {"diagnosis_label_raw": "apical_aneurysm"},
            {"diagnosis_label_raw": "apical_aneurysm"},
            {"diagnosis_label_raw": "apical_dyskinesia"},
        ]
        dists = [0.05, 0.08, 0.1, 0.12, 0.15, 0.3]
        
        candidates = knn_vote_labels(metas, dists, topn=3, min_score_threshold=2.5)
        
        # Should have apical_aneurysm with high score (5 strong matches)
        assert candidates[0][0] == "apical_aneurysm"
        assert candidates[0][1] > 3.5  # Strong consensus


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
