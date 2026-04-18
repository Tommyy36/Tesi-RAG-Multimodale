"""
Pytest configuration and fixtures.
"""
import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session")
def project_root():
    """Return project root directory."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="session")
def data_dir(project_root):
    """Return data directory path."""
    return os.path.join(project_root, "data")


@pytest.fixture(scope="session")
def dataset_dir(data_dir):
    """Return dataset_built directory path."""
    return os.path.join(data_dir, "dataset_built")


@pytest.fixture
def mock_dicom_metadata():
    """Return mock DICOM metadata for testing."""
    return {
        "case_id": "test123abc",
        "anonymized": True,
        "diagnosis_label_raw": "Normal",
        "diagnosis_label_short": "normal",
        "diagnosis_label_pretty": "Normal",
        "diagnosis_group": "normal",
        "source_path": "Normal/test.dcm",
        "modality": "US",
        "view": "4CH",
        "stage": "Basale",
        "num_frames": 100,
        "fps": 25,
        "effective_duration": 4.0,
        "heart_rate": 70,
        "manufacturer": "Test Manufacturer",
        "model": "Test Model",
        "rows": 480,
        "columns": 640,
        "photometric": "YBR_FULL_422",
        "mean_intensity": 0.45,
        "motion_energy": 0.023,
        "motion_std": 0.012,
        "feature_frames_used": 64
    }


# Configure pytest
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "privacy: marks tests related to data privacy/anonymization"
    )
