# Esempi Pratici - RAG Healthcare

> ⚠️ **Nota**: Gli esempi con `/chat` sono attualmente disabilitati. Il sistema è ottimizzato per analisi multimodale tramite `/analyze-case`. L'endpoint `/chat` sarà riabilitato in sviluppi futuri per query esplorative generiche.

## 1. Avvio Sistema

```bash
# Terminal 1: Avvia backend
export OPENAI_API_KEY="sk-..."
./start.sh

# Output atteso:
# [1/5] Checking Python environment... ✓
# [2/5] Checking dependencies... ✓
# [3/5] Building dataset from DICOM files... (se prima volta)
#       ✓ Dataset already exists (altrimenti)
# [4/5] Checking environment variables... ✓
# [5/5] Initializing vectorstore...
#       [VectorstoreManager] Indexed 26 cases. ✓
#       [VectorstoreManager] Indexed 13 guideline files. ✓
# === Starting FastAPI Backend ===
# INFO: Uvicorn running on http://0.0.0.0:8000
```

## 2. Query RAG - Casi Simili [DISABILITATO - Sviluppo futuro]

<details>
<summary>⚠️ Esempio per sviluppi futuri (endpoint attualmente disabilitato)</summary>

```bash
# Cerca casi simili a cardiomiopatia dilatata
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the echocardiographic findings in dilated cardiomyopathy?",
    "model": "gpt-4o",
    "rag_type": "cases",
    "evaluate": false
  }' | jq .

# Response:
# {
#   "answer": "[RAG stub - cases]\nQuery: ...\nRetrieved 5 sources...",
#   "sources": [
#     {
#       "type": "case",
#       "id": "a53a50ad3d3e",
#       "score": 0.789,
#       "snippet": "Ultrasound multiframe study. View: Unknown...",
#       "metadata": {
#         "diagnosis_label_pretty": "Dilated cardiomyopathy with global dysfunction",
#         "num_frames": 111,
#         "motion_energy": 0.0234,
#         ...
#       }
#     },
#     ...
#   ],
#   "session_id": "session-auto"
# }
```

</details>

## 3. Query RAG - Guidelines [DISABILITATO - Sviluppo futuro]

<details>
<summary>⚠️ Esempio per sviluppi futuri (endpoint attualmente disabilitato)</summary>

```bash
# Cerca nelle linee guida
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the normal echo appearance of the left ventricle?",
    "model": "gpt-4o",
    "rag_type": "guidelines"
  }' | jq .

# Recupera chunk rilevanti da:
# - normal_echo_background.txt
# - dilated_cardiomyopathy_background.txt (per contrasto)
```

</details>

## 4. Query RAG - Hybrid (Cases + Guidelines) [DISABILITATO - Sviluppo futuro]

<details>
<summary>⚠️ Esempio per sviluppi futuri (endpoint attualmente disabilitato)</summary>

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Compare normal vs pathological septal motion",
    "model": "gpt-4o",
    "rag_type": "hybrid"
  }' | jq .

# Recupera:
# - Casi normali e patologici dal vectorstore cases
# - Background teorico dal vectorstore guidelines
```

</details>

## 5. Upload DICOM e Estrazione Frame

```bash
# Upload nuovo caso DICOM
curl -X POST http://localhost:8000/upload-doc \
  -F "file=@data/raw_data/Normal/IM-0001-0032.dcm" \
  -F "model=gpt-4o" \
  -F "rag_type=multimodal" | jq .

# Response:
# {
#   "ok": true,
#   "file_id": "...",
#   "frames_saved": 12,
#   "output_folder": "data/current_case_frames"
# }
```

## 6. Lista Documenti Caricati

```bash
curl "http://localhost:8000/list-docs?rag_type=cases" | jq .

# Response:
# {
#   "files": [
#     {
#       "file_id": "current_case_123",
#       "uploaded_at": "2026-01-16T22:30:00",
#       "frames": 12
#     }
#   ]
# }
```

## 7. Cancella Documento

```bash
curl -X POST http://localhost:8000/delete-doc \
  -H "Content-Type: application/json" \
  -d '{"file_id": "current_case_123"}' | jq .

# Response:
# {
#   "ok": true,
#   "deleted": "current_case_123"
# }
```

## 8. Test Manuale Vectorstore

```bash
# Test retrieval diretto
python3 src/vectorstore_manager.py

# Output:
# === Vectorstore Manager Test ===
# [VectorstoreManager] Initializing Qdrant in-memory...
# [VectorstoreManager] Auto-indexing collections...
# [VectorstoreManager] ✓ Indexed 26 cases.
# [VectorstoreManager] ✓ Indexed 13 guideline files.
# 
# Test search: 'dilated cardiomyopathy with reduced ejection fraction'
# Found 3 results:
#   1. 36ff771bde40 - Normal
#      Ultrasound multiframe study. View: Unknown...
#   2. 02667f14217e - Normal
#      Ultrasound multiframe study. View: Unknown...
#   3. a53a50ad3d3e - Normal
#      Ultrasound multiframe study. View: Unknown...
```

## 9. Rigenerare Dataset

```bash
# Aggiungi nuovi DICOM in data/raw_data/
cp /path/to/new_study.dcm data/raw_data/Normal/

# Rigenera dataset
./rebuild_dataset.sh

# Output:
# === Rebuild Dataset ===
# Dataset already exists. This will DELETE and REBUILD it.
# Continue? (y/N): y
# Removing old dataset...
# Building dataset from DICOM files...
# ✓ Dataset built successfully!
#   Total documents: 297  (se aggiungi 1 caso)
#   Case cards: 27
#   Frames: 270

# Riavvia backend per re-indexing
./start.sh
```

## 10. Swagger UI - Docs Interattive

```bash
# Apri browser su:
open http://localhost:8000/docs

# Interfaccia grafica per:
# - Testare tutti gli endpoint
# - Vedere schema Request/Response
# - Eseguire query direttamente dal browser
```

## 11. Health Check

```bash
# Verifica che il backend sia attivo
curl http://localhost:8000/docs | head -5

# Output: HTML della pagina Swagger (status 200)
```

## 12. Script Multimodale Standalone

```bash
# Test pipeline RAG multimodale (fuori dal backend)
python3 scripts/multimodal_rag_openai.py

# Input interattivo:
# Paste the clinical report (finish with an empty line):
# > Patient presents with dyspnea on exertion.
# > Echo shows dilated LV with reduced EF.
# >
# Optional: folder containing CURRENT exam frames (press Enter to skip):
# > data/current_case_frames
#
# --- MODEL OUTPUT ---
# (GPT-4o response con diagnosis + differential + evidence + sources)
```

## 13. Analizza Dataset Generato

```bash
# Conta documenti per tipo
jq -r '.metadata.document_type' data/dataset_built/documents.jsonl | sort | uniq -c

# Output:
#  26 case_card
# 260 frame

# Conta casi per diagnosis
jq -r '.metadata.diagnosis_label_pretty' data/dataset_built/documents.jsonl | \
  grep -v null | sort | uniq -c

# Output:
# 100 Normal
#  10 Normal with septal hypertrophy
#  10 Normal function mitral valve prolapse
#  10 Dilated cardiomyopathy with global dysfunction
#  40 Inferoapical septal akinesia
# ... (14 categorie totali)
#  40 Inferoapical septal akinesia
```

## 14. Estrai Frame da Singolo DICOM

```bash
# Estrai 12 frame uniformemente spaziati
python3 scripts/dicom_to_frames_current.py \
  --dicom data/raw_data/Normal/IM-0001-0032.dcm \
  --out data/test_frames \
  --n 12

# Output:
# DICOM: data/raw_data/Normal/IM-0001-0032.dcm
# Frames in DICOM: 143 | Saved: 12
# View: None | Stage: None | FPS: 63
# Output folder: data/test_frames
```

## 15. Debugging

```bash
# Check logs backend
tail -f uvicorn_log.txt  # (se rediretti output)

# Check vectorstore in memoria
python3 -c "
from src.vectorstore_manager import get_vectorstore
vs = get_vectorstore()
print('Vectorstore ready')
"

# Check documenti indicizzati
wc -l data/dataset_built/documents.jsonl

# Check immagini estratte
find data/dataset_built/images -name "*.png" | wc -l

# Check dipendenze
pip list | grep -E "qdrant|datapizza|sentence"
```

## 16. Performance Tips

```bash
# Ridurre memoria: riduci numero di frame estratti
# In scripts/build_dataset.py, riga export_representative_frames:
export_representative_frames(ds, case_id, n=5)  # invece di 10

# Velocizzare indexing: riduci max_frames per feature extraction
# In scripts/build_dataset.py, compute_simple_video_features:
compute_simple_video_features(ds, max_frames=32)  # invece di 64

# Passare a Qdrant persistente (evita re-indexing ogni restart)
docker run -d -p 6333:6333 -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant
# Poi modifica vectorstore_manager.py per usare host="localhost"
```

## 17. Common Errors

### Error: "No module named 'sentence_transformers'"
```bash
# Soluzione: attiva ambiente e reinstalla
source .venv/bin/activate
pip install -r requirements.txt
```

### Error: "documents.jsonl not found"
```bash
# Soluzione: genera dataset
python3 scripts/build_dataset.py
```

### Error: "OPENAI_API_KEY not set"
```bash
# Soluzione: imposta variabile
export OPENAI_API_KEY="sk-..."
# Verifica
echo $OPENAI_API_KEY
```

### Error: "Port 8000 already in use"
```bash
# Soluzione: cambia porta o killa processo
lsof -ti:8000 | xargs kill -9
# Oppure usa altra porta
uvicorn api.main:app --port 8001
```
