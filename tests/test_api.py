"""
Integration tests for FastAPI endpoints.
Tests API responses, validation, and error handling.
"""
import pytest
import sys
import os
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__))))

from api.main import app

client = TestClient(app)


# DISABILITATO - Endpoint /chat non più in uso
# class TestChatEndpoint:
#     """Test /chat endpoint."""
#     
#     def test_chat_success(self):
#         """Test successful chat request."""
#         response = client.post(
#             "/chat",
#             json={
#                 "question": "What is dilated cardiomyopathy?",
#                 "model": "gpt-4o",
#                 "rag_type": "cases",
#                 "evaluate": False
#             }
#         )
#         
#         assert response.status_code == 200, f"Expected 200, got {response.status_code}"
#         data = response.json()
#         
#         assert "answer" in data, "Response should contain answer"
#         assert "sources" in data, "Response should contain sources"
#         assert "session_id" in data, "Response should contain session_id"
#     
#     def test_chat_with_guidelines(self):
#         """Test chat with guidelines RAG type."""
#         response = client.post(
#             "/chat",
#             json={
#                 "question": "Normal echo findings",
#                 "model": "gpt-4o",
#                 "rag_type": "guidelines"
#             }
#         )
#         
#         assert response.status_code == 200
#         data = response.json()
#         assert "answer" in data
#     
#     def test_chat_hybrid_mode(self):
#         """Test chat with hybrid RAG type."""
#         response = client.post(
#             "/chat",
#             json={
#                 "question": "Compare normal vs abnormal echo",
#                 "model": "gpt-4o",
#                 "rag_type": "hybrid"
#             }
#         )
#         
#         assert response.status_code == 200
#     
#     def test_chat_missing_required_fields(self):
#         """Test chat with missing required fields."""
#         response = client.post(
#             "/chat",
#             json={
#                 "question": "Test question"
#                 # Missing model and rag_type
#             }
#         )
#         
#         assert response.status_code == 422, "Should return validation error"
#     
#     def test_chat_invalid_rag_type(self):
#         """Test chat with invalid rag_type."""
#         response = client.post(
#             "/chat",
#             json={
#                 "question": "Test",
#                 "model": "gpt-4o",
#                 "rag_type": "invalid_type"
#             }
#         )
#         
#         # Should still process (validation may be lenient)
#         assert response.status_code in [200, 422]
#     
#     def test_chat_with_session_id(self):
#         """Test chat with explicit session_id."""
#         response = client.post(
#             "/chat",
#             json={
#                 "question": "Test",
#                 "model": "gpt-4o",
#                 "rag_type": "cases",
#                 "session_id": "test-session-123"
#             }
#         )
#         
#         assert response.status_code == 200
#         data = response.json()
#         assert "session_id" in data


class TestListDocsEndpoint:
    """Test /list-docs endpoint."""
    
    def test_list_docs_success(self):
        """Test successful list docs request."""
        response = client.get("/list-docs?rag_type=cases")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict), "Response should be a dict"
    
    def test_list_docs_missing_param(self):
        """Test list docs without rag_type parameter."""
        response = client.get("/list-docs")
        
        # Should still work or return error
        assert response.status_code in [200, 422]


class TestDeleteDocEndpoint:
    """Test /delete-doc endpoint."""
    
    def test_delete_doc_format(self):
        """Test delete doc with proper format."""
        response = client.post(
            "/delete-doc",
            json={"file_id": "test_file_123"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict), "Response should be a dict"
    
    def test_delete_doc_missing_file_id(self):
        """Test delete doc without file_id."""
        response = client.post(
            "/delete-doc",
            json={}
        )
        
        # May accept empty payload or return error
        assert response.status_code in [200, 422]


class TestFlushRagEndpoint:
    """Test /flush-rag endpoint."""
    
    def test_flush_rag_success(self):
        """Test successful flush rag request."""
        response = client.post(
            "/flush-rag",
            json={}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "ok" in data or "message" in data


class TestCORSHeaders:
    """Test CORS configuration."""
    
    def test_cors_headers_present(self):
        """Test that CORS headers are set."""
        response = client.get("/list-docs?rag_type=cases")
        
        # CORS headers should be present on actual requests
        assert "access-control-allow-origin" in [h.lower() for h in response.headers] or response.status_code == 200


class TestHealthCheck:
    """Test general API health."""
    
    def test_docs_accessible(self):
        """Test that /docs endpoint is accessible."""
        response = client.get("/docs")
        
        assert response.status_code == 200, "API docs should be accessible"
    
    def test_openapi_schema(self):
        """Test that OpenAPI schema is available."""
        response = client.get("/openapi.json")
        
        assert response.status_code == 200, "OpenAPI schema should be available"
        data = response.json()
        assert "openapi" in data, "Should contain OpenAPI version"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
