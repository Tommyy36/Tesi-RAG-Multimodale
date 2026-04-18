import os
import sys
import base64
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add src to path per import del vectorstore_manager
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from scripts.index_Qdrant import get_vectorstore, get_embedder

# ----------------------------------
# Config
# ----------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "data", "dataset_built"))

# Usa il vectorstore manager (auto-indexing al primo utilizzo)
vectorstore = get_vectorstore()
embedder = get_embedder()

TOPK_CASES = 5
TOPK_GUIDES = 4

FRAMES_PER_SIMILAR_CASE = 3
MAX_QUERY_FRAMES = 12
MAX_SIMILAR_FRAMES_TOTAL = 12

MODEL_VISION = "gpt-4o"
# OpenAI client dal SDK ufficiale
from openai import OpenAI

# Lazy-load client to avoid import-time errors when API key is not set
_client = None

def get_openai_client() -> OpenAI:
    """Get or create the OpenAI client instance."""
    global _client
    if _client is None:
        _client = OpenAI()
    return _client

# ----------------------------------
# Helpers
# ----------------------------------
def image_to_data_url(path: str) -> str:
    """Encode local image as data URL for OpenAI image input."""
    with open(path, "rb") as f:
        b = f.read()
    b64 = base64.b64encode(b).decode("utf-8")
    mime = "image/png" if path.lower().endswith(".png") else "image/jpeg"
    return f"data:{mime};base64,{b64}"

def uniform_sample(items: List[str], n: int) -> List[str]:
    if n <= 0:
        return []
    if len(items) <= n:
        return items
    import numpy as np
    idxs = np.linspace(0, len(items) - 1, n, dtype=int)
    return [items[i] for i in idxs]

def list_frames_in_folder(folder: Optional[str]) -> List[str]:
    if not folder or not os.path.isdir(folder):
        return []
    exts = (".png", ".jpg", ".jpeg")
    return sorted(
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if f.lower().endswith(exts)
    )

def pick_frames_for_case(case_id: str, n: int) -> List[str]:
    case_dir = os.path.join(DATA_DIR, "images", case_id)
    frames = list_frames_in_folder(case_dir)
    return uniform_sample(frames, n)

def retrieve_similar_qdrant(
    collection_name: str,
    query_text: str,
    k: int
) -> Dict[str, Any]:
    """Retrieve similar documents from Qdrant collection."""
    # embed query
    q_emb = embedder.encode([query_text], normalize_embeddings=True).tolist()[0]
    
    try:
        # search in Qdrant (vector_name deve corrispondere a quello in index_Qdrant.py)
        hits = vectorstore.search(
            collection_name=collection_name,
            query_vector=q_emb,
            vector_name="text_embedding",  # allineato con index_Qdrant.py
            k=k
        )
    except Exception as e:
        print(f"[WARNING] Search failed for collection '{collection_name}': {e}")
        hits = []
    
    # gestisci risultati vuoti
    if not hits:
        return {
            "ids": [[]],
            "metadatas": [[]],
            "documents": [[]],
            "distances": [[]],
        }
    
    # convert to a structure similar a Chroma
    # vectorstore.search returns list of Chunk objects with .id, .metadata, .text
    # Note: score is not available in Chunk objects from datapizza, use placeholder
    return {
        "ids": [[hit.id for hit in hits]],
        "metadatas": [[hit.metadata for hit in hits]],
        "documents": [[hit.text for hit in hits]],
        "distances": [[0.0 for hit in hits]],  # score not available in Chunk objects
    }

def knn_vote_labels(
    case_metas: List[Dict[str, Any]],
    case_dists: List[float],
    topn: int = 3,
    min_score_threshold: float = 2.5
) -> List[Tuple[str, float]]:
    """Vote on diagnosis labels weighted by distance.
    
    Args:
        case_metas: Metadata of retrieved cases
        case_dists: Distances of retrieved cases
        topn: Number of top candidates to return
        min_score_threshold: Minimum score to accept a candidate (filters weak matches)
    """
    if not case_metas or not case_dists:
        return [("unknown", 0.0)]
    
    scores: Dict[str, float] = {}
    for meta, dist in zip(case_metas, case_dists):
        lab = meta.get("diagnosis_label_raw", "unknown")
        # Weight inversely proportional to distance
        w = 1.0 / (1.0 + float(dist))
        scores[lab] = scores.get(lab, 0.0) + w
    
    # Filter out weak candidates below threshold
    scores = {lab: score for lab, score in scores.items() if score >= min_score_threshold}
    
    if not scores:
        return [("insufficient_evidence", 0.0)]
    
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return ranked[:topn]

# ----------------------------
# Prompting
# ----------------------------
SYSTEM_PROMPT = """You are a cardiology clinical decision support assistant.

Goal:
- Suggest a PROBABLE DIAGNOSIS (not definitive) and a DIFFERENTIAL (2 alternatives)
based ONLY on:
1) the provided clinical report text,
2) the provided visual evidence (sampled frames),
3) retrieved similar cases,
4) retrieved guideline chunks (if provided).

Rules:
- Do NOT invent measurements, findings, or patient details.
- If evidence is insufficient, state it explicitly and list what is missing.
- Provide confidence: low / medium / high, with a short justification.
- **CRITICAL for confidence**:
  * If the clinical report is generic/minimal (e.g., "Analyze this case"), assign LOW confidence even if KNN scores are high.
  * If visual evidence alone suggests a diagnosis but lacks clinical context, use MEDIUM confidence at most.
  * HIGH confidence requires BOTH strong clinical context AND supporting visual/retrieved evidence.
  * If KNN candidates show low scores (<3.0), "insufficient_evidence", or marginal scores (<5.0 with generic report), explicitly state LOW confidence.
  * **When in doubt with generic reports: prefer "Insufficient evidence for diagnosis" over speculating.**
  * **EXCEPTION for normal findings**: If clinical report explicitly describes normal parameters (BP, HR, labs normal, no symptoms) AND visual evidence shows no abnormalities, use MEDIUM-HIGH confidence for "Normal echocardiogram" even with marginal KNN scores.
- **For "normal" diagnosis**:
  * If retrieved cases or clinical report suggest normal findings, consider "Normal echocardiogram" as a valid diagnosis.
  * Do not over-diagnose pathology based on visual similarity alone.
  * **When report has explicit normal clinical findings (vitals normal, no symptoms, labs normal), this provides strong evidence for normal diagnosis.**
  * **Absence of clear abnormalities in a generic report context should suggest possible normal findings.**
- Separate evidence from text vs evidence from images.
- For each key claim, cite either a CASE (case_id) or a GUIDELINE (source+chunk).
- Always include a Sources section:
  - list case_id(s) used
  - list guideline sources/chunks if present

Output format:
1) Suggested diagnosis (confidence)
2) Differential (2 alternatives) + why
3) Evidence (bullets)
   - From report/retrieved context
   - From images/frames
4) Missing info / recommended next checks
5) Sources
"""



def is_generic_report(report_text: str) -> bool:
    """Check if report is generic/minimal without specific clinical information."""
    generic_phrases = [
        "analyze this",
        "provide probable diagnosis",
        "analyze the case",
        "clinical analysis",
        "echocardiography case"
    ]
    text_lower = report_text.lower().strip()
    
    # If report is very short or contains generic phrases, it's likely generic
    if len(text_lower) < 100 or any(phrase in text_lower for phrase in generic_phrases):
        return True
    return False

def has_explicit_normal_findings(report_text: str) -> bool:
    """Check if report explicitly describes normal clinical findings."""
    text_lower = report_text.lower()
    
    # Keywords indicating normal findings
    normal_indicators = [
        "no symptoms",
        "no relevant",
        "within normal",
        "normal range",
        "normal limit",
        "unremarkable",
        "asymptomatic",
        "normal physiological"
    ]
    
    # Count how many normal indicators are present
    normal_count = sum(1 for indicator in normal_indicators if indicator in text_lower)
    
    # If report has 2+ normal indicators and is detailed (>150 chars), likely explicit normal
    return normal_count >= 2 and len(text_lower) > 150

def build_user_payload(
    report_text: str,
    knn_candidates: List[Tuple[str, float]],
    cases_res: Dict[str, Any],
    guides_res: Optional[Dict[str, Any]],
) -> str:
    case_ids = cases_res["ids"][0]
    case_metas = cases_res["metadatas"][0]
    case_docs = cases_res["documents"][0]
    case_dists = cases_res["distances"][0]

    cases_block = ""
    for i, cid in enumerate(case_ids):
        meta = case_metas[i]
        cases_block += (
            f"\n[CASE {cid} | label={meta.get('diagnosis_label_raw', '?')} | dist={case_dists[i]:.4f}]\n"
            f"{case_docs[i]}\n"
        )

    if not guides_res:
        guides_block = "(no guidelines retrieved)"
    else:
        guides_block = ""
        g_ids = guides_res["ids"][0]
        g_docs = guides_res["documents"][0]
        g_metas = guides_res["metadatas"][0]
        g_dists = guides_res["distances"][0]
        for i in range(len(g_ids)):
            meta = g_metas[i]
            src = meta.get("source", "unknown")
            chunk = meta.get("chunk_id", meta.get("chunk", "?"))
            guides_block += (
                f"\n[GUIDELINE {src} chunk={chunk} dist={g_dists[i]:.4f}]\n"
                f"{g_docs[i]}\n"
            )

    diag_lines = "\n".join([f"- {lab}: score={sc:.3f}" for lab, sc in knn_candidates])
    
    # Add context quality warning
    context_warning = ""
    has_explicit_normal = has_explicit_normal_findings(report_text)
    
    if is_generic_report(report_text):
        context_warning = "\n⚠️ CRITICAL: Clinical report is generic/minimal with NO specific clinical findings.\n"
        context_warning += "   → Use LOW confidence. Consider 'Insufficient evidence' or 'possibly Normal' if no clear abnormalities.\n"
    elif has_explicit_normal:
        context_warning = "\n✅ NOTE: Clinical report contains explicit NORMAL findings (no symptoms, parameters within normal ranges).\n"
        context_warning += "   → If visual evidence shows no clear abnormalities, 'Normal echocardiogram' with MEDIUM-HIGH confidence is appropriate.\n"
    
    max_knn_score = knn_candidates[0][1] if knn_candidates else 0.0
    if max_knn_score < 5.0 and max_knn_score > 0:
        severity = "marginal" if max_knn_score >= 3.0 else "low"
        context_warning += f"\n⚠️ NOTE: KNN score is {severity} ({max_knn_score:.2f}). "
        if has_explicit_normal:
            context_warning += "However, with explicit normal clinical findings, visual similarity is less critical.\n"
        else:
            context_warning += "Visual similarity alone is insufficient for confident diagnosis.\n"
    elif max_knn_score < 3.0:
        context_warning += "\n⚠️ NOTE: KNN scores are very low, indicating weak visual similarity. Prefer 'insufficient evidence'.\n"

    return f"""CLINICAL REPORT:
{report_text}{context_warning}

KNN DIAGNOSIS CANDIDATES (from similar retrieved cases):
{diag_lines}

RETRIEVED SIMILAR CASES:
{cases_block}

RETRIEVED GUIDELINES:
{guides_block}
"""

# ----------------------------------
# Main pipeline
# ----------------------------------
def run_multimodal_rag(
    report_text: str,
    query_frames_folder: Optional[str] = None,
    query_frame_paths: Optional[List[str]] = None,
) -> str:
    """Main RAG pipeline: retrieve cases/guidelines, build multimodal prompt, call OpenAI."""
    # 1) Retrieve similar cases
    cases_res = retrieve_similar_qdrant("cases", report_text, TOPK_CASES)
    if not cases_res["ids"][0]:
        print("[WARNING] No similar cases found. Check if 'cases' collection is populated.")

    # 2) Retrieve guidelines (optional)
    guides_res = retrieve_similar_qdrant("guidelines", report_text, TOPK_GUIDES)
    if not guides_res["ids"][0]:
        print("[INFO] No guidelines found. Continuing without guideline context.")
        guides_res = None

    # 3) kNN vote with adaptive threshold
    # If report is generic, require higher evidence
    is_generic = is_generic_report(report_text)
    threshold = 4.5 if is_generic else 2.5
    
    knn_candidates = knn_vote_labels(
        cases_res["metadatas"][0],
        cases_res["distances"][0],
        topn=3,
        min_score_threshold=threshold
    )
    
    # Additional check: even if threshold is passed, if score is marginal (<5.0) and report is generic,
    # treat as insufficient evidence to avoid over-diagnosis
    top_score = knn_candidates[0][1] if knn_candidates and knn_candidates[0][0] != "insufficient_evidence" else 0.0
    if is_generic and top_score < 5.0 and top_score > 0:
        print(f"[INFO] Generic report with marginal KNN score ({top_score:.2f}). Treating as insufficient evidence.")
        knn_candidates = [("insufficient_evidence", top_score)] + knn_candidates[:2]
    
    # If kNN returns "insufficient_evidence" or very low scores, check for "normal" in report
    if knn_candidates[0][0] in ["insufficient_evidence", "unknown"]:
        report_lower = report_text.lower()
        has_normal_keywords = any(term in report_lower for term in ["normal", "no abnormalities", "unremarkable"])
        has_explicit_normal = has_explicit_normal_findings(report_text)
        
        if has_normal_keywords or has_explicit_normal:
            # Give higher score if report explicitly describes normal findings
            score = 4.0 if has_explicit_normal else 2.0
            knn_candidates = [("normal_echo", score)] + knn_candidates[:2]
            if has_explicit_normal:
                print(f"[INFO] Report has explicit normal findings. Score boosted to {score:.1f} for 'normal_echo' candidate.")

    # 4) Frames
    if query_frame_paths is None:
        query_frame_paths = list_frames_in_folder(query_frames_folder)
    query_frame_paths = uniform_sample(query_frame_paths, MAX_QUERY_FRAMES)

    # 5) Supporting frames from similar cases
    case_ids = cases_res["ids"][0]
    similar_frames: List[str] = []
    for cid in case_ids:
        similar_frames.extend(pick_frames_for_case(cid, FRAMES_PER_SIMILAR_CASE))
    similar_frames = uniform_sample(similar_frames, MAX_SIMILAR_FRAMES_TOTAL)

    # 6) Build prompt context
    user_text = build_user_payload(report_text, knn_candidates, cases_res, guides_res)

    # 7) Build multimodal content
    content: List[Dict[str, Any]] = [{"type": "input_text", "text": user_text}]
    for p in query_frame_paths:
        content.append({"type": "input_image", "image_url": image_to_data_url(p)})
    for p in similar_frames:
        content.append({"type": "input_image", "image_url": image_to_data_url(p)})

    # 8) OpenAI call
    client = get_openai_client()
    resp = client.responses.create(
        model=MODEL_VISION,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ],
        max_output_tokens=900,
    )
    return resp.output_text

# ----------------------------------
# CLI
# ----------------------------------
if __name__ == "__main__":
    print("Paste the clinical report (finish with an empty line):")
    lines = []
    while True:
        line = input()
        if not line.strip():
            break
        lines.append(line)
    report = "\n".join(lines).strip()
    if not report:
        raise SystemExit("No report text provided.")

    frames_folder = input("Optional: folder containing CURRENT exam frames (press Enter to skip): ").strip()
    frames_folder = frames_folder if frames_folder else None

    output = run_multimodal_rag(report_text=report, query_frames_folder=frames_folder)
    print("\n--- MODEL OUTPUT ---\n")
    print(output)
