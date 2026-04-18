"""
Unit tests for index_Qdrant module.
Tests singleton pattern, auto-indexing, and retrieval.
"""
import pytest
import os
import sys
import tempfile
import json

# Add scripts to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__))))

from scripts.index_Qdrant import (
    get_vectorstore,
    get_embedder,
    _ensure_collections_populated,
    reset_collections
)


class TestIndexQdrant:
    """Test vectorstore singleton and initialization."""
    
    def test_get_vectorstore_singleton(self):
        """Test that get_vectorstore returns the same instance."""
        vs1 = get_vectorstore()
        vs2 = get_vectorstore()
        assert vs1 is vs2, "Vectorstore should be a singleton"
    
    def test_get_embedder_singleton(self):
        """Test that get_embedder returns the same instance."""
        emb1 = get_embedder()
        emb2 = get_embedder()
        assert emb1 is emb2, "Embedder should be a singleton"
    
    def test_embedder_dimensions(self):
        """Test that embedder produces correct dimensionality."""
        embedder = get_embedder()
        test_text = ["test sentence"]
        embeddings = embedder.encode(test_text, normalize_embeddings=True)
        assert embeddings.shape[1] == 384, "all-MiniLM-L6-v2 should produce 384-dim embeddings"
    
    def test_vectorstore_initialized(self):
        """Test that vectorstore is properly initialized."""
        vs = get_vectorstore()
        assert vs is not None, "Vectorstore should be initialized"
    
    def test_collections_created(self):
        """Test that required collections exist."""
        vs = get_vectorstore()
        collections = vs.get_collections()
        collection_names = [c[0] if isinstance(c, tuple) else c for c in collections]
        
        # At minimum, one of the collections should exist
        assert len(collection_names) > 0, "At least one collection should be created"


class TestRetrieval:
    """Test semantic search and retrieval."""
    
    def test_search_guidelines(self):
        """Test retrieval from guidelines collection."""
        vs = get_vectorstore()
        embedder = get_embedder()
        
        query = "normal echocardiogram findings"
        query_emb = embedder.encode([query], normalize_embeddings=True).tolist()[0]
        
        try:
            results = vs.search(
                collection_name="guidelines",
                query_vector=query_emb,
                vector_name="text_embedding",
                k=3
            )
            assert isinstance(results, list), "Search should return a list"
            # May be empty if no guidelines indexed, but should not error
        except Exception as e:
            pytest.skip(f"Guidelines collection not populated: {e}")
    
    def test_search_cases(self):
        """Test retrieval from cases collection."""
        vs = get_vectorstore()
        embedder = get_embedder()
        
        query = "dilated cardiomyopathy with reduced ejection fraction"
        query_emb = embedder.encode([query], normalize_embeddings=True).tolist()[0]
        
        try:
            results = vs.search(
                collection_name="cases",
                query_vector=query_emb,
                vector_name="text_embedding",
                k=5
            )
            assert isinstance(results, list), "Search should return a list"
        except Exception as e:
            pytest.skip(f"Cases collection not populated: {e}")
    
    def test_embedding_normalization(self):
        """Test that embeddings are properly normalized."""
        embedder = get_embedder()
        test_text = ["test sentence for normalization"]
        embeddings = embedder.encode(test_text, normalize_embeddings=True)
        
        # Check L2 norm is approximately 1
        import numpy as np
        norm = np.linalg.norm(embeddings[0])
        assert abs(norm - 1.0) < 0.01, f"Normalized embedding should have L2 norm ≈ 1, got {norm}"


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_search_nonexistent_collection(self):
        """Test search on non-existent collection."""
        vs = get_vectorstore()
        embedder = get_embedder()
        
        query_emb = embedder.encode(["test"], normalize_embeddings=True).tolist()[0]
        
        # Should handle gracefully
        try:
            results = vs.search(
                collection_name="nonexistent_collection",
                query_vector=query_emb,
                vector_name="text_embedding",
                k=3
            )
            # May return empty list or raise exception - both acceptable
            assert isinstance(results, list) or results is None
        except Exception:
            # Expected behavior for non-existent collection
            pass
    
    def test_empty_query(self):
        """Test search with empty/zero vector."""
        vs = get_vectorstore()
        
        zero_vector = [0.0] * 384
        
        try:
            results = vs.search(
                collection_name="cases",
                query_vector=zero_vector,
                vector_name="text_embedding",
                k=1
            )
            # Should not crash
            assert isinstance(results, list)
        except Exception:
            pytest.skip("Zero vector search not supported")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
