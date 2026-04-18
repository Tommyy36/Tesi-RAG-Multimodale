import os
import csv
import chromadb
from collections import defaultdict
from sentence_transformers import SentenceTransformer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "data", "dataset_built"))
LABELS_CSV = os.path.join(DATA_DIR, "labels.csv")
CHROMA_DIR = os.path.join(DATA_DIR, "chroma_db")

MODEL_NAME = "all-MiniLM-L6-v2"
K_LIST = [1, 3, 5]
N_RESULTS = max(K_LIST) + 1  # +1 per poter escludere self

model = SentenceTransformer(MODEL_NAME)
client = chromadb.PersistentClient(path=CHROMA_DIR)
col = client.get_collection("cases")

# labels: case_id -> label_raw
case_label = {}
with open(LABELS_CSV, "r", encoding="utf-8") as f:
    r = csv.DictReader(f)
    for row in r:
        case_label[row["case_id"]] = row["label_raw"]

case_ids = list(case_label.keys())

# micro metrics (globali)
hits = {k: 0 for k in K_LIST}
mrr_sum = 0.0
valid = 0

# per-label (per macro average)
per_label_total = defaultdict(int)
per_label_hits = {k: defaultdict(int) for k in K_LIST}
per_label_mrr_sum = defaultdict(float)

for cid in case_ids:
    got = col.get(ids=[cid], include=["documents"])
    if not got["documents"] or not got["documents"][0]:
        continue

    query_text = got["documents"][0]
    q_emb = model.encode([query_text], normalize_embeddings=True).tolist()

    res = col.query(
        query_embeddings=q_emb,
        n_results=N_RESULTS,
        include=["metadatas"]
    )

    retrieved = res["ids"][0]
    retrieved = [x for x in retrieved if x != cid]  # exclude self

    if len(retrieved) == 0:
        continue

    true_label = case_label[cid]
    valid += 1
    per_label_total[true_label] += 1

    # Hit@K
    for k in K_LIST:
        topk = retrieved[:k]
        ok = any(case_label.get(x) == true_label for x in topk)
        if ok:
            hits[k] += 1
            per_label_hits[k][true_label] += 1

    # MRR
    rr = 0.0
    for rank, rid in enumerate(retrieved, start=1):
        if case_label.get(rid) == true_label:
            rr = 1.0 / rank
            break
    mrr_sum += rr
    per_label_mrr_sum[true_label] += rr

def safe_div(a, b):
    return a / b if b else 0.0

print("\n=== Retrieval Evaluation (query_embeddings, same model) ===")
print("Model:", MODEL_NAME)
print("Cases evaluated:", valid)

# Micro
for k in K_LIST:
    print(f"Micro Hit@{k}: {safe_div(hits[k], valid):.4f} ({hits[k]}/{valid})")
print(f"Micro MRR:   {safe_div(mrr_sum, valid):.4f}")

# Macro (media delle performance per label)
labels = sorted(per_label_total.keys())
for k in K_LIST:
    macro = sum(safe_div(per_label_hits[k][lab], per_label_total[lab]) for lab in labels) / len(labels) if labels else 0.0
    print(f"Macro Hit@{k}: {macro:.4f}")

macro_mrr = sum(safe_div(per_label_mrr_sum[lab], per_label_total[lab]) for lab in labels) / len(labels) if labels else 0.0
print(f"Macro MRR:   {macro_mrr:.4f}")

print("\n=== Per-label breakdown ===")
for lab in labels:
    denom = per_label_total[lab]
    line = [f"{lab}: n={denom}"]
    for k in K_LIST:
        line.append(f"Hit@{k}={safe_div(per_label_hits[k][lab], denom):.4f}")
    line.append(f"MRR={safe_div(per_label_mrr_sum[lab], denom):.4f}")
    print(" | ".join(line))
