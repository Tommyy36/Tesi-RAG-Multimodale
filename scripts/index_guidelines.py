"""
Script di Indicizzazione Linee Guida - Tesi Thomas
Carica i file di testo interi senza chunking artificiale per evitare testi troncati.
"""
import os
import glob
from sentence_transformers import SentenceTransformer
from datapizza.core.vectorstore import VectorConfig
from datapizza.vectorstores.qdrant import QdrantVectorstore

# -----------------------------
# Paths
# -----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

GUIDELINES_DIR = os.path.abspath(
    os.path.join(BASE_DIR, "..", "data", "guidelines_txt")
)

# -----------------------------
# Models
# -----------------------------
EMB_MODEL = "all-MiniLM-L6-v2"
embedder_local = SentenceTransformer(EMB_MODEL)

# -----------------------------
# SETUP: Qdrant Vectorstore
# -----------------------------
vectorstore = QdrantVectorstore(location=":memory:")

# config: dimensioni dell’embedding (384 per all-MiniLM-L6-v2)
vector_config = [
    VectorConfig(name="text_embeddings", dimensions=384)
]

# crea la collection "guidelines" (se già esiste la ricrea)
try:
    vectorstore.delete_collection("guidelines")
except Exception:
    pass

vectorstore.create_collection(
    collection_name="guidelines",
    vector_config=vector_config
)

# --- EMBEDDING (local) ---
class LocalEmbedder:
    def embed(self, texts: list[str]) -> list[list[float]]:
        return embedder_local.encode(texts, normalize_embeddings=True).tolist()

local_embedder = LocalEmbedder()

# -----------------------------
# Load + index ( Thomas Refactoring: No Chunking )
# -----------------------------
documents = []
metadatas = []
ids = []

idx = 0

for path in glob.glob(os.path.join(GUIDELINES_DIR, "*.txt")):
    fname = os.path.basename(path)

    with open(path, "r", encoding="utf-8") as f:
        text = f.read().strip()

    if not text:
        continue

    # STRATEGIA DI TESI: Carichiamo il file intero per garantire la fluidità di lettura
    doc_id = f"guideline_{idx}"
    documents.append(text)
    metadatas.append({
        "source": fname,
        "chunk_id": 0, # Unico blocco integro
        "document_type": "guideline"
    })
    ids.append(doc_id)
    idx += 1

# --- GENERA EMBEDDING (local) ---
embeddings = local_embedder.embed(documents)

# --- insert in Qdrant ---
vectorstore.add(
    collection_name="guidelines",
    ids=ids,
    vectors=embeddings,
    metadatas=metadatas
)

print("Guidelines indexed successfully without truncation!")
print("Files totali indicizzati:", len(set(m["source"] for m in metadatas)))
print("Documenti pronti su Qdrant:", len(ids))