"""
Vectorstore Manager Evoluto - Integrazione Google Gemini API per Tesi Multimodale.
Versione ULTRA COMPATIBILE - Basata sul codice funzionante dell'altra IA.
"""
import sys
import os
import json
import glob
import uuid
from google import genai
from typing import Optional, List
from dotenv import load_dotenv

# Import del client ufficiale di Qdrant standard
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# Carica variabili d'ambiente (.env)
load_dotenv()

# Configurazione Google Gemini identica a quella funzionante
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# --- PATHS ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
GUIDELINES_DIR = os.path.join(DATA_DIR, "guidelines_txt")
JSONL_PATH = os.path.join(DATA_DIR, "dataset_built", "documents.jsonl") 

# Path dei file temporanei delle TAC e Unity generati oggi
TAC_ROWS_PATH = os.path.join(DATA_DIR, "dataset_built", "tac_rows.json")
UNITY_ROWS_PATH = os.path.join(DATA_DIR, "dataset_built", "unity_rows.json")

# --- CONFIGURAZIONE GOOGLE EMBEDDING ---
# Ripristinato il modello esatto che funzionava e non dava 404
EMB_MODEL_NAME = "gemini-embedding-001"
EMBEDDING_DIM = 3072  

# I tuoi 4 ECG originali stabili
ECG_CASES = [
    {"id": "ecg_normal_01", "image_path": "data/raw_data/ECG_Dataset/SELECTED_SAMPLES/Normal/Normal(1).jpg", "modality": "ECG", "label": "Normal Person", "description": "Tracciato elettrocardiografico (ECG) di un paziente sano. Ritmo sinusale normale, assenza di anomalie del tratto ST o dell'onda T. Parametri elettrici cardiaci nella norma."},
    {"id": "ecg_abnormal_01", "image_path": "data/raw_data/ECG_Dataset/SELECTED_SAMPLES/Normal/Normal(1).jpg", "modality": "ECG", "label": "Abnormal Heartbeat", "description": "Tracciato elettrocardiografico (ECG) che mostra anomalie del ritmo cardiaco. Presenza di battiti ectopici o irregolarità della conduzione elettrica, indicativi di aritmia da approfondire clinicamente."},
    {"id": "ecg_infarction_01", "image_path": "data/raw_data/ECG_Dataset/SELECTED_SAMPLES/Infarction/PMI(1).jpg", "modality": "ECG", "label": "History of MI", "description": "Tracciato elettrocardiografico (ECG) di un paziente con storia pregressa di infarto miocardico. Presenza di onde Q patologiche stabili, segno di una cicatrice miocardica da vecchio evento ischemico."},
    {"id": "ecg_mi_01", "image_path": "data/raw_data/ECG_Dataset/SELECTED_SAMPLES/MI/MI(1).jpg", "modality": "ECG", "label": "Myocardial Infarction", "description": "Tracciato elettrocardiografico (ECG) con evidenti segni di Infarto Miocardico Acuto in corso. Marcato sopralivellamento del tratto ST, indicativo di occlusione coronarica acuta."}
]

# -----------------------------
# Singleton Vectorstore
# -----------------------------
_vectorstore: Optional[QdrantClient] = None
_initialized = False

def get_gemini_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """Genera embeddings usando la sintassi esatta dell'altra IA."""
    print(f"[GeminiAPI] Generazione embedding per {len(texts)} documenti...")
    
    embeddings = []
    for text in texts:
        response = client.models.embed_content(
            model=EMB_MODEL_NAME,
            contents=text
        )
        embeddings.append(response.embeddings[0].values)
        
    return embeddings

def get_vectorstore() -> QdrantClient:
    """Ritorna il vectorstore singleton (Qdrant in-memory)."""
    global _vectorstore, _initialized
    
    if _vectorstore is None:
        print("[IndexQdrant] Inizializzazione Qdrant ufficiale in modalità IN-MEMORY...")
        _vectorstore = QdrantClient(location=":memory:")
    
    if not _initialized:
        print("[IndexQdrant] Auto-indicizzazione delle collezioni multimodali...")
        _ensure_collections_populated()
        _initialized = True
    
    return _vectorstore

def _ensure_collections_populated():
    """Controlla e popola le collection 'cases' e 'guidelines'."""
    global _vectorstore
    print(f"[IndexQdrant] Creazione e indicizzazione con dimensioni Gemini ({EMBEDDING_DIM})...")
    _create_and_index_all()

def _create_and_index_all():
    """Configura le collezioni Qdrant con le nuove specifiche di tesi."""
    global _vectorstore
    
    for collection in ["cases", "guidelines"]:
        try:
            _vectorstore.delete_collection(collection)
        except:
            pass
        _vectorstore.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE)
        )
    
    _pre_build_documents_jsonl()  # Esegue il merge dei file
    _index_cases()
    _index_guidelines()

def _pre_build_documents_jsonl():
    """Costruisce il file unico documents.jsonl unendo ECG, TAC e Unity."""
    print("--- GENERAZIONE DATASET MULTIMODALE DEFINITIVO (documents.jsonl) ---")
    final_docs = []
    
    # 1. ECG
    final_docs.extend(ECG_CASES)
    
    # 2. TAC
    if os.path.exists(TAC_ROWS_PATH):
        with open(TAC_ROWS_PATH, "r", encoding="utf-8") as f:
            final_docs.extend(json.load(f))
            
    # 3. Campionamento Unity (primi 6 casi)
    if os.path.exists(UNITY_ROWS_PATH):
        with open(UNITY_ROWS_PATH, "r", encoding="utf-8") as f:
            unity_all = json.load(f)
            final_docs.extend(unity_all[:6])
            
    # Scrittura fisica
    os.makedirs(os.path.dirname(JSONL_PATH), exist_ok=True)
    with open(JSONL_PATH, "w", encoding="utf-8") as out_f:
        for doc in final_docs:
            out_f.write(json.dumps(doc, ensure_ascii=False) + "\n")
            
    print(f"[Dataset] Merge completato. {len(final_docs)} casi totali scritti in documents.jsonl")

def _index_cases():
    """Indicizza i casi clinici multimodali."""
    if not os.path.exists(JSONL_PATH):
        print(f"[IndexQdrant] ERROR: {JSONL_PATH} non trovato.")
        return
    
    docs_text = []
    docs_metadata = []
    
    with open(JSONL_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            obj = json.loads(line)
            
            docs_text.append(obj["description"])
            docs_metadata.append({
                "case_id": obj["id"],
                "image_path": obj["image_path"],
                "modality": obj["modality"],
                "label": obj["label"],
                "view": obj.get("view", "N/A")
            })
    
    if not docs_text: 
        print("[IndexQdrant] Nessun documento trovato nel file JSONL.")
        return

    embeddings = get_gemini_embeddings_batch(docs_text)
    
    points = []
    for i in range(len(docs_text)):
        case_id = docs_metadata[i].get("case_id", f"gen_{i}")
        doc_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"case_{case_id}_{i}"))
        
        points.append(
            PointStruct(
                id=doc_uuid,
                vector=embeddings[i],
                payload={
                    "text": docs_text[i],
                    **docs_metadata[i]
                }
            )
        )
    
    _vectorstore.upsert(collection_name="cases", points=points)
    print(f"[IndexQdrant] ✓ Successo! Indicizzati {len(docs_text)} esami multimodali nel database.")

def _index_guidelines():
    """Indicizza linee guida mediche (TXT) se presenti."""
    if not os.path.isdir(GUIDELINES_DIR):
        print("[IndexQdrant] Nessuna linea guida TXT trovata, salto la sezione.")
        return
    
    docs_text = []
    docs_metadata = []
    
    for path in glob.glob(os.path.join(GUIDELINES_DIR, "*.txt")):
        with open(path, "r", encoding="utf-8") as f:
            text = f.read().strip()
        
        chunks = [text[i:i+1000] for i in range(0, len(text), 800)]
        for j, chunk in enumerate(chunks):
            docs_text.append(chunk)
            docs_metadata.append({"source": os.path.basename(path), "document_type": "guideline"})
    
    if not docs_text: return
    
    embeddings = get_gemini_embeddings_batch(docs_text)
    
    points_guidelines = []
    for i in range(len(docs_text)):
        doc_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"guide_{i}"))
        
        points_guidelines.append(
            PointStruct(
                id=doc_uuid,
                vector=embeddings[i],
                payload={
                    "text": docs_text[i],
                    **docs_metadata[i]
                }
            )
        )
    
    _vectorstore.upsert(collection_name="guidelines", points=points_guidelines)
    print(f"[IndexQdrant] ✓ Indicizzate {len(docs_text)} sezioni di linee guida.")

def reset_collections():
    """
    Funzione esposta per il backend FastAPI.
    Svuota e reinizializza le collezioni Qdrant per il soft reset.
    """
    global _vectorstore
    print("[IndexQdrant] Richiesta di reset completo ricevuta da FastAPI...")
    # Se il client non è inizializzato, lo recuperiamo
    if _vectorstore is None:
        from qdrant_client import QdrantClient
        _vectorstore = QdrantClient(location=":memory:")
        
    # Chiamiamo la funzione interna che cancella e ricrea tutto da zero
    _create_and_index_all()
    print("[IndexQdrant] ✓ Reset completato con successo.")

if __name__ == "__main__":
    vs = get_vectorstore()
    print("\n[SUCCESS] Pipeline di indicizzazione Gemini completata con i dati.")