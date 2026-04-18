"""
Tests for anonymization verification.
Ensures no sensitive data leaks into public dataset.
"""
import pytest
import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__))))

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSONL_PATH = os.path.join(BASE_DIR, "data", "dataset_built", "documents.jsonl")


@pytest.mark.privacy
class TestAnonymizationVerification:
    """Test that dataset is properly anonymized."""
    
    @pytest.fixture
    def documents(self):
        """Load all documents from JSONL."""
        if not os.path.exists(JSONL_PATH):
            pytest.skip("Dataset not built yet")
        
        docs = []
        with open(JSONL_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                docs.append(json.loads(line))
        return docs
    
    def test_all_documents_have_anonymized_flag(self, documents):
        """Test that all documents have anonymized=True flag."""
        for doc in documents:
            meta = doc.get('metadata', {})
            assert 'anonymized' in meta, f"Document missing anonymized flag: {meta.get('case_id', '?')}"
            assert meta['anonymized'] is True, f"Document not marked as anonymized: {meta.get('case_id', '?')}"
    
    def test_no_patient_names(self, documents):
        """Test that no patient names are present."""
        sensitive_patterns = ['patient_name', 'patientname']
        
        for doc in documents:
            meta = doc.get('metadata', {})
            for key in meta.keys():
                key_lower = key.lower()
                for pattern in sensitive_patterns:
                    assert pattern not in key_lower, f"Found sensitive field: {key}"
    
    def test_no_patient_ids(self, documents):
        """Test that no patient IDs are present."""
        sensitive_patterns = ['patient_id', 'patientid']
        
        for doc in documents:
            meta = doc.get('metadata', {})
            for key in meta.keys():
                key_lower = key.lower()
                for pattern in sensitive_patterns:
                    assert pattern not in key_lower, f"Found sensitive field: {key}"
    
    def test_no_dates(self, documents):
        """Test that no date fields are present."""
        date_patterns = ['study_date', 'series_date', 'acquisition_date', 'birth_date']
        
        for doc in documents:
            meta = doc.get('metadata', {})
            for key in meta.keys():
                key_lower = key.lower()
                for pattern in date_patterns:
                    assert pattern not in key_lower, f"Found date field: {key}"
    
    def test_no_institution_info(self, documents):
        """Test that no institution information is present."""
        institution_patterns = ['institution', 'hospital', 'clinic']
        
        for doc in documents:
            meta = doc.get('metadata', {})
            for key in meta.keys():
                key_lower = key.lower()
                for pattern in institution_patterns:
                    # manufacturer is OK, institutionname is not
                    if pattern in key_lower and 'manufacturer' not in key_lower:
                        assert False, f"Found institution field: {key}"
    
    def test_no_physician_names(self, documents):
        """Test that no physician names are present."""
        physician_patterns = ['physician', 'doctor', 'operator']
        
        for doc in documents:
            meta = doc.get('metadata', {})
            for key in meta.keys():
                key_lower = key.lower()
                for pattern in physician_patterns:
                    assert pattern not in key_lower, f"Found physician field: {key}"
    
    def test_no_sop_instance_uid(self, documents):
        """Test that SOPInstanceUID is not exposed."""
        for doc in documents:
            meta = doc.get('metadata', {})
            assert 'sop_instance_uid' not in [k.lower() for k in meta.keys()], \
                "SOPInstanceUID should not be in metadata"
    
    def test_case_ids_are_hashes(self, documents):
        """Test that case IDs are cryptographic hashes."""
        for doc in documents:
            meta = doc.get('metadata', {})
            case_id = meta.get('case_id', '')
            
            # Should be 12-character hex string
            assert len(case_id) == 12, f"Case ID should be 12 chars: {case_id}"
            assert all(c in '0123456789abcdef' for c in case_id), \
                f"Case ID should be hex: {case_id}"
    
    def test_no_date_values(self, documents):
        """Test that no date-like values (YYYYMMDD) are present."""
        for doc in documents:
            meta = doc.get('metadata', {})
            for key, value in meta.items():
                if isinstance(value, str) and len(value) == 8 and value.isdigit():
                    year = int(value[:4])
                    # Likely a date if year is reasonable
                    assert not (1900 < year < 2100), \
                        f"Possible date value in {key}: {value}"
    
    def test_required_clinical_fields_present(self, documents):
        """Test that necessary clinical metadata is preserved."""
        case_cards = [d for d in documents if d.get('metadata', {}).get('document_type') == 'case_card']
        
        for doc in case_cards:
            meta = doc['metadata']
            # Should have clinical labels
            assert 'diagnosis_label_pretty' in meta or 'diagnosis_group' in meta, \
                "Clinical diagnosis information should be preserved"
            # Should have technical parameters
            assert 'modality' in meta or 'num_frames' in meta, \
                "Technical parameters should be preserved"


@pytest.mark.privacy
class TestFileSystemSecurity:
    """Test that sensitive files are properly protected."""
    
    def test_gitignore_covers_dicom(self):
        """Test that .gitignore excludes DICOM files."""
        gitignore_path = os.path.join(BASE_DIR, ".gitignore")
        
        if not os.path.exists(gitignore_path):
            pytest.skip(".gitignore not found")
        
        with open(gitignore_path, 'r') as f:
            gitignore_content = f.read().lower()
        
        assert '.dcm' in gitignore_content, ".gitignore should exclude .dcm files"
        assert 'raw_data' in gitignore_content, ".gitignore should exclude raw_data"
    
    def test_no_env_file_committed(self):
        """Test that .env file would be ignored."""
        gitignore_path = os.path.join(BASE_DIR, ".gitignore")
        
        if not os.path.exists(gitignore_path):
            pytest.skip(".gitignore not found")
        
        with open(gitignore_path, 'r') as f:
            gitignore_content = f.read()
        
        assert '.env' in gitignore_content, ".gitignore should exclude .env files"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
