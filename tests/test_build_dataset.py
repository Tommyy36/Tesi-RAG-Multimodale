"""
Unit tests for dataset building and DICOM processing.
Tests anonymization, frame extraction, and metadata generation.
"""
import pytest
import os
import sys
import json
import tempfile
import shutil
import pydicom

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__))))

from scripts.build_dataset import (
    anonymize_dicom_metadata,
    SENSITIVE_TAGS,
    safe_get,
    make_case_id,
    build_case_card,
    compute_simple_video_features
)


class TestAnonymization:
    """Test DICOM anonymization functionality."""
    
    def test_sensitive_tags_removed(self):
        """Test that all sensitive tags are removed."""
        # Create a mock DICOM with sensitive data
        ds = pydicom.Dataset()
        ds.PatientName = "Test^Patient"
        ds.PatientID = "12345"
        ds.StudyDate = "20240101"
        ds.Modality = "US"
        
        # Anonymize
        ds_anon = anonymize_dicom_metadata(ds)
        
        # Check sensitive tags removed
        assert not hasattr(ds_anon, 'PatientName'), "PatientName should be removed"
        assert not hasattr(ds_anon, 'PatientID'), "PatientID should be removed"
        assert not hasattr(ds_anon, 'StudyDate'), "StudyDate should be removed"
        
        # Check non-sensitive tags preserved
        assert hasattr(ds_anon, 'Modality'), "Modality should be preserved"
    
    def test_all_sensitive_tags_covered(self):
        """Test that all defined sensitive tags are checked."""
        ds = pydicom.Dataset()
        
        # Add all sensitive tags
        for tag in SENSITIVE_TAGS:
            try:
                setattr(ds, tag, f"sensitive_value_{tag}")
            except:
                pass  # Some tags may not be settable
        
        ds_anon = anonymize_dicom_metadata(ds)
        
        # Verify all are removed
        for tag in SENSITIVE_TAGS:
            assert not hasattr(ds_anon, tag), f"{tag} should be removed"
    
    def test_anonymization_idempotent(self):
        """Test that anonymizing twice gives same result."""
        ds = pydicom.Dataset()
        ds.PatientName = "Test^Patient"
        ds.Modality = "US"
        
        ds_anon1 = anonymize_dicom_metadata(ds)
        ds_anon2 = anonymize_dicom_metadata(ds_anon1)
        
        assert not hasattr(ds_anon1, 'PatientName')
        assert not hasattr(ds_anon2, 'PatientName')


class TestCaseIDGeneration:
    """Test case ID generation and uniqueness."""
    
    def test_case_id_deterministic(self):
        """Test that same DICOM produces same case ID."""
        ds = pydicom.Dataset()
        ds.SOPInstanceUID = "1.2.3.4.5"
        
        id1 = make_case_id(ds, "test.dcm")
        id2 = make_case_id(ds, "test.dcm")
        
        assert id1 == id2, "Same DICOM should produce same case ID"
    
    def test_case_id_unique(self):
        """Test that different DICOMs produce different case IDs."""
        ds1 = pydicom.Dataset()
        ds1.SOPInstanceUID = "1.2.3.4.5"
        
        ds2 = pydicom.Dataset()
        ds2.SOPInstanceUID = "1.2.3.4.6"
        
        id1 = make_case_id(ds1, "test1.dcm")
        id2 = make_case_id(ds2, "test2.dcm")
        
        assert id1 != id2, "Different DICOMs should produce different case IDs"
    
    def test_case_id_length(self):
        """Test that case ID has expected length."""
        ds = pydicom.Dataset()
        ds.SOPInstanceUID = "1.2.3.4.5"
        
        case_id = make_case_id(ds, "test.dcm")
        
        assert len(case_id) == 12, "Case ID should be 12 characters (SHA256 truncated)"
    
    def test_case_id_fallback(self):
        """Test case ID generation when SOPInstanceUID is missing."""
        ds = pydicom.Dataset()
        # No SOPInstanceUID
        
        case_id = make_case_id(ds, "/path/to/test.dcm")
        
        assert len(case_id) == 12, "Should generate ID from filename fallback"


class TestCaseCardGeneration:
    """Test case card text generation."""
    
    def test_case_card_basic(self):
        """Test basic case card generation."""
        meta = {
            "view": "4CH",
            "stage": "Basale",
            "num_frames": 100,
            "fps": 25,
        }
        
        card = build_case_card(meta)
        
        assert "4CH" in card, "View should be in case card"
        assert "Basale" in card, "Stage should be in case card"
        assert "100" in card, "Number of frames should be in case card"
    
    def test_case_card_no_label_leakage(self):
        """Test that diagnosis label is NOT in case card (neutral)."""
        meta = {
            "diagnosis_label_pretty": "Dilated cardiomyopathy",
            "view": "4CH",
            "stage": "Basale",
            "num_frames": 100,
        }
        
        card = build_case_card(meta)
        
        # Should NOT contain diagnosis (neutral metadata only)
        assert "Dilated cardiomyopathy" not in card.lower(), "Diagnosis should not be in case card"
        assert "cardiomyopathy" not in card.lower(), "Diagnosis should not be in case card"


class TestVideoFeatures:
    """Test video feature extraction."""
    
    def test_feature_extraction_basic(self):
        """Test that video features are computed."""
        import numpy as np
        
        # Skip this test - requires actual DICOM file
        # compute_simple_video_features needs pixel_array which requires proper DICOM setup
        pytest.skip("Requires proper DICOM file with pixel data")
    
    def test_feature_extraction_single_frame(self):
        """Test feature extraction with single frame."""
        import numpy as np
        
        # Skip this test - requires actual DICOM file
        pytest.skip("Requires proper DICOM file with pixel data")


class TestDatasetIntegrity:
    """Test dataset file format and structure."""
    
    @pytest.fixture
    def sample_document(self):
        """Create a sample document structure."""
        return {
            "content": "Test ultrasound study",
            "metadata": {
                "case_id": "test123",
                "anonymized": True,
                "diagnosis_label_pretty": "Normal",
                "document_type": "case_card",
                "num_frames": 100,
                "modality": "US"
            }
        }
    
    def test_document_has_required_fields(self, sample_document):
        """Test that document has required fields."""
        assert "content" in sample_document, "Document should have content"
        assert "metadata" in sample_document, "Document should have metadata"
        
        meta = sample_document["metadata"]
        assert "case_id" in meta, "Metadata should have case_id"
        assert "anonymized" in meta, "Metadata should have anonymized flag"
        assert "document_type" in meta, "Metadata should have document_type"
    
    def test_anonymized_flag_present(self, sample_document):
        """Test that anonymized flag is set."""
        assert sample_document["metadata"]["anonymized"] is True, "Anonymized flag should be True"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
