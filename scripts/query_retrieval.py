import os
from sentence_transformers import SentenceTransformer

from datapizza.vectorstores.qdrant import QdrantVectorstore

# -----------------------------
# Setup
# -----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# use Qdrant in-memory
vectorstore = QdrantVectorstore(location=":memory:")

# if server Qdrant:
# vectorstore = QdrantVectorstore(host="localhost", port=6333)

# collection
COLLECTION_NAME = "cases"

# -----------------------------
# Model
# -----------------------------
model = SentenceTransformer("all-MiniLM-L6-v2")

print("Ready. Empty query to exit.")

while True:
    q = input("\nQuery: ").strip()
    if not q:
        break

    # 1) fai embedding alla query
    q_emb = model.encode([q], normalize_embeddings=True).tolist()[0]

    # 2) cerca nel vectorstore
    # `vector_name` deve essere il nome usato quando hai creato la collection
    results = vectorstore.search(
        collection_name=COLLECTION_NAME,
        query_vector=q_emb,
        vector_name="text_embeddings",  # o come si chiama il tuo vettore
        k=5
    )

    # 3) stampa
    if not results:
        print("No results found.")
        continue

    print(f"\nTop {len(results)} results:")

    for i, chunk in enumerate(results, start=1):
        meta = chunk.metadata
        text = chunk.text
        score = chunk.score

        print(f"\n#{i} id={chunk.id}  score={score:.4f}")
        print(text)
