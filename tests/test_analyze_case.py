"""
Tests for the end-to-end analyze-case flow:
- Uploads a real DICOM from data/raw_data
- Extracts frames
- Runs multimodal analysis via a stubbed run_multimodal_rag
"""
import os
import sys
import io
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from api.main import app


client = TestClient(app)


@pytest.fixture(scope="module")
def sample_dicom_path() -> str:
    base = os.path.dirname(os.path.dirname(__file__))
    # Use an existing DICOM from raw_data
    candidate = os.path.join(base, "data", "raw_data", "Normal", "IM-0001-0032.dcm")
    if not os.path.exists(candidate):
        pytest.skip("Sample DICOM not found: data/raw_data/Normal/IM-0001-0032.dcm")
    return candidate


def test_upload_doc_and_extract_frames(sample_dicom_path):
    with open(sample_dicom_path, "rb") as f:
        files = {"file": ("test.dcm", f, "application/dicom")}
        resp = client.post(
            "/upload-doc",
            files=files,
            data={
                "model": "gpt-4o",
                "rag_type": "multimodal",
            },
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("ok") is True
    assert "file_id" in data
    assert "frames_dir" in data
    # Frames list should exist (may be empty if extraction fails on environment)
    assert "frames" in data


def test_analyze_case_with_stubbed_rag(sample_dicom_path, monkeypatch):
    # Stub multimodal rag to avoid external OpenAI dependency
    from api.services import rag_service

    def stub_run_multimodal_rag(report_text: str, query_frames_folder: str = None, query_frame_paths=None):
        return f"TEST_OUTPUT for {os.path.basename(query_frames_folder or '')} | report: {report_text[:30]}"

    monkeypatch.setattr(rag_service, "run_multimodal_rag", stub_run_multimodal_rag, raising=True)

    with open(sample_dicom_path, "rb") as f:
        files = {"file": ("test.dcm", f, "application/dicom")}
        resp = client.post(
            "/analyze-case",
            files=files,
            data={
                "report_text": "Analizza questo caso con sospetta cardiomiopatia."
            },
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("ok") is True
    assert "analysis" in data
    analysis = data["analysis"]
    assert analysis.get("ok") is True
    assert isinstance(analysis.get("answer"), str)
    assert "TEST_OUTPUT" in analysis.get("answer")


if __name__ == "__main__":
    pytest.main([__file__, "-q"]) 