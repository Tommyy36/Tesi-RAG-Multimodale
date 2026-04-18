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
# Chunking
# -----------------------------
def chunk_text(text, chunk_size=800, overlap=150):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks

# -----------------------------
# SETUP: Qdrant Vectorstore
# -----------------------------
# puoi usare location=":memory:" per test o:
# vectorstore = QdrantVectorstore(host="localhost", port=6333)
vectorstore = QdrantVectorstore(location=":memory:")

# config: dimensioni dell’embedding
vector_config = [
    VectorConfig(name="text_embeddings", dimensions=384)
    # 384 è la dimensione di "all-MiniLM-L6-v2"
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
# definisce un “adapter” che prende il testo e genera embeddings
# usando SentenceTransformers e poi li passa a Qdrant
class LocalEmbedder:
    def embed(self, texts: list[str]) -> list[list[float]]:
        # normalize_embeddings=True come nel tuo script Chroma
        return embedder_local.encode(texts, normalize_embeddings=True).tolist()

local_embedder = LocalEmbedder()

# -----------------------------
# Load + index
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

    chunks = chunk_text(text)

    for j, chunk in enumerate(chunks):
        doc_id = f"guideline_{idx}"

        documents.append(chunk)
        metadatas.append({
            "source": fname,
            "chunk_id": j,
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

print("Guidelines indexed successfully!")
print("Files:", len(set(m["source"] for m in metadatas)))
print("Chunks:", len(ids))
