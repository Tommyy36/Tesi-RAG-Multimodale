"""
Vectorstore Manager - Singleton con pipeline datapizza per Qdrant in-memory.
"""
import os
import json
import glob
import uuid
from typing import Optional
from datapizza.core.vectorstore import VectorConfig
from datapizza.vectorstores.qdrant import QdrantVectorstore
from datapizza.type.type import Chunk, DenseEmbedding
from sentence_transformers import SentenceTransformer

# --- PATHS ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DATASET_DIR = os.path.join(DATA_DIR, "dataset_built")
GUIDELINES_DIR = os.path.join(DATA_DIR, "guidelines_txt")
JSONL_PATH = os.path.join(DATASET_DIR, "documents.jsonl")

EMB_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384

# -----------------------------
# Singleton Vectorstore
# -----------------------------
_vectorstore: Optional[QdrantVectorstore] = None
_embedder: Optional[SentenceTransformer] = None
_initialized = False


class LocalEmbedder:
    """Adapter per SentenceTransformer -> embeddings."""
    def __init__(self, model: SentenceTransformer):
        self.model = model
    
    def embed(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(texts, normalize_embeddings=True).tolist()


def get_vectorstore() -> QdrantVectorstore:
    """Ritorna il vectorstore singleton, inizializzandolo se necessario."""
    global _vectorstore, _embedder, _initialized
    
    if _vectorstore is None:
        print("[IndexQdrant] Initializing Qdrant in-memory...")
        _vectorstore = QdrantVectorstore(location=":memory:")
        _embedder = SentenceTransformer(EMB_MODEL)
    
    if not _initialized:
        print("[IndexQdrant] Auto-indexing collections...")
        _ensure_collections_populated()
        _initialized = True
    
    return _vectorstore


def get_embedder() -> SentenceTransformer:
    """Ritorna il sentence transformer singleton."""
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(EMB_MODEL)
    return _embedder


def _ensure_collections_populated():
    """Controlla e popola le collection 'cases' e 'guidelines' se vuote."""
    global _vectorstore, _embedder
    
    # Collection 'cases'
    try:
        collections = _vectorstore.get_collections()
        collection_names = [c[0] if isinstance(c, tuple) else c for c in collections]
        if "cases" in collection_names:
            print("[IndexQdrant] Collection 'cases' exists, checking if populated...")
            try:
                test = _vectorstore.search(
                    collection_name="cases",
                    query_vector=[0.0] * EMBEDDING_DIM,
                    vector_name="text_embedding",
                    k=1
                )
                if test:
                    print(f"[IndexQdrant] Collection 'cases' already has data.")
                    return
            except:
                pass
    except:
        pass
    
    print("[IndexQdrant] Creating and indexing collections...")
    _create_and_index_all()


def _create_and_index_all():
    """Crea e indicizza tutte le collection."""
    global _vectorstore, _embedder
    
    # Crea collection 'cases'
    vector_config = [VectorConfig(name="text_embedding", dimensions=EMBEDDING_DIM)]
    
    try:
        _vectorstore.delete_collection("cases")
    except:
        pass
    
    _vectorstore.create_collection("cases", vector_config=vector_config)
    
    # Indicizza cases e frames
    _index_cases()
    
    # Crea collection 'guidelines'
    try:
        _vectorstore.delete_collection("guidelines")
    except:
        pass
    
    _vectorstore.create_collection("guidelines", vector_config=vector_config)
    _index_guidelines()


def _index_cases():
    """Indicizza cases e frames da documents.jsonl."""
    global _vectorstore, _embedder
    
    if not os.path.exists(JSONL_PATH):
        print(f"[IndexQdrant] WARNING: {JSONL_PATH} not found. Skipping cases indexing.")
        return
    
    print(f"[IndexQdrant] Loading documents from {JSONL_PATH}...")
    
    # Carica tutti i documenti (case_card + frame)
    docs_text = []
    docs_metadata = []
    
    with open(JSONL_PATH, "r", encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            doc_type = obj["metadata"].get("document_type")
            # Indicizza sia case_card che frame
            if doc_type not in ["case_card", "frame"]:
                continue
            docs_text.append(obj["content"])
            docs_metadata.append(obj["metadata"])
    
    if not docs_text:
        print("[IndexQdrant] No documents found.")
        return
    
    print(f"[IndexQdrant] Embedding {len(docs_text)} documents...")
    
    # Genera embeddings usando LocalEmbedder
    local_embedder = LocalEmbedder(_embedder)
    embeddings = local_embedder.embed(docs_text)
    
    # Aggiungi a Qdrant
    print(f"[IndexQdrant] Adding documents to Qdrant...")
    chunks = []
    for i in range(len(docs_text)):
        case_id = docs_metadata[i].get("case_id", f"unknown_{i}")
        doc_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"case_{case_id}_{i}"))
        emb = DenseEmbedding(name="text_embedding", vector=embeddings[i])
        
        metadata = docs_metadata[i].copy()
        metadata["original_id"] = case_id
        
        chunks.append(
            Chunk(
                id=doc_uuid,
                text=docs_text[i],
                embeddings=[emb],
                metadata=metadata
            )
        )
    
    _vectorstore.add(chunk=chunks, collection_name="cases")
    
    # Conta i tipi di documenti indicizzati
    doc_types = {}
    for m in docs_metadata:
        dt = m.get("document_type", "unknown")
        doc_types[dt] = doc_types.get(dt, 0) + 1
    
    types_str = ", ".join([f"{v} {k}s" for k, v in doc_types.items()])
    print(f"[IndexQdrant] ✓ Indexed {len(docs_text)} documents ({types_str}).")


def _index_guidelines():
    """Indicizza guidelines da file .txt."""
    global _vectorstore, _embedder
    
    if not os.path.isdir(GUIDELINES_DIR):
        print(f"[IndexQdrant] WARNING: {GUIDELINES_DIR} not found. Skipping guidelines indexing.")
        return
    
    print(f"[IndexQdrant] Loading guidelines from {GUIDELINES_DIR}...")
    
    def chunk_text(text: str, chunk_size: int = 800, overlap: int = 150):
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start = end - overlap
        return chunks
    
    docs_text = []
    docs_metadata = []
    idx = 0
    
    for path in glob.glob(os.path.join(GUIDELINES_DIR, "*.txt")):
        fname = os.path.basename(path)
        with open(path, "r", encoding="utf-8") as f:
            text = f.read().strip()
        
        if not text:
            continue
        
        chunks = chunk_text(text)
        for j, chunk in enumerate(chunks):
            docs_text.append(chunk)
            docs_metadata.append({
                "source": fname,
                "chunk_id": j,
                "document_type": "guideline",
                "original_id": f"guideline_{idx}"
            })
            idx += 1
    
    if not docs_text:
        print("[IndexQdrant] No guidelines found.")
        return
    
    print(f"[IndexQdrant] Embedding {len(docs_text)} guideline chunks...")
    
    # Genera embeddings
    local_embedder = LocalEmbedder(_embedder)
    embeddings = local_embedder.embed(docs_text)
    
    # Aggiungi a Qdrant
    print(f"[IndexQdrant] Adding guidelines to Qdrant...")
    chunks = []
    for i in range(len(docs_text)):
        doc_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"guideline_{i}"))
        emb = DenseEmbedding(name="text_embedding", vector=embeddings[i])
        chunks.append(
            Chunk(
                id=doc_uuid,
                text=docs_text[i],
                embeddings=[emb],
                metadata=docs_metadata[i]
            )
        )
    
    _vectorstore.add(chunk=chunks, collection_name="guidelines")
    print(f"[IndexQdrant] ✓ Indexed {len(docs_text)} guideline chunks from {len(set(m['source'] for m in docs_metadata))} files.")


def reset_collections():
    """Elimina e ricrea tutte le collection (per testing/soft reset)."""
    global _vectorstore, _initialized
    
    if _vectorstore is None:
        return
    
    print("[IndexQdrant] Resetting all collections...")
    
    try:
        _vectorstore.delete_collection("cases")
    except:
        pass
    
    try:
        _vectorstore.delete_collection("guidelines")
    except:
        pass
    
    _initialized = False
    _ensure_collections_populated()
    
    print("[IndexQdrant] ✓ Collections reset complete.")


# -----------------------------
# CLI per test manuale
# -----------------------------
if __name__ == "__main__":
    print("=== Index Qdrant - Pipeline Test ===")
    print(f"JSONL_PATH: {JSONL_PATH}")
    
    vs = get_vectorstore()
    print("\n✓ Vectorstore ready and populated!")
    
    # Test search
    emb = get_embedder()
    test_query = "dilated cardiomyopathy with reduced ejection fraction"
    test_emb = emb.encode([test_query], normalize_embeddings=True).tolist()[0]
    
    print(f"\nTest search: '{test_query}'")
    results = vs.search(
        collection_name="cases",
        query_vector=test_emb,
        vector_name="text_embedding",
        k=3
    )
    
    print(f"Found {len(results)} results:")
    for i, hit in enumerate(results, 1):
        case_id = hit.metadata.get("original_id", hit.id)
        label = hit.metadata.get("diagnosis_label_pretty", "Unknown")
        doc_type = hit.metadata.get("document_type", "unknown")
        print(f"  {i}. {case_id} ({doc_type}) - {label}")
        print(f"     {hit.text[:100]}...")
