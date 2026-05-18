# RAG System for Healthcare

Sistema RAG (Retrieval-Augmented Generation) multimodale per supporto decisionale clinico in cardiologia. Combina analisi di immagini ecografiche DICOM, retrieval semantico di casi simili e linee guida per generare risposte diagnostiche assistite da AI.

> **📌 Nota API**: Il sistema è attualmente ottimizzato per l'analisi multimodale di casi specifici tramite `/analyze-case`. L'endpoint `/chat` per query generiche è temporaneamente disabilitato e sarà disponibile in future release.

## ⚠️ Privacy & Anonymization

**All patient data has been fully anonymized** in compliance with GDPR and HIPAA regulations.

- ✅ All DICOM metadata is anonymized (names, dates, IDs removed)
- ✅ Only non-identifiable clinical/technical data is preserved
- ✅ Safe for public repository publication

📖 See [ANONYMIZATION.md](ANONYMIZATION.md) for details.

## 🚀 Quick Start (Manuale - Consigliato)

```bash
# 1. Setup ambiente
source .venv/bin/activate

# 2. Imposta API key OpenAI
export OPENAI_API_KEY="sk-..."

# 3. Avvia il sistema (auto-build dataset + auto-indexing + Streamlit)
make start
```

Il sistema avvia **automaticamente**:
- ✅ Backend FastAPI: http://localhost:8000
- ✅ Streamlit UI: http://localhost:8501  
- ✅ Vectorstore con auto-indexing

**Accedi a**:
- **UI Streamlit**: http://localhost:8501 (🔬 Analyze, 📤 Upload, 📋 Manage)
- **API Docs**: http://localhost:8000/docs

📖 Guida completa: [QUICKSTART.md](QUICKSTART.md)

## 🐳 Quick Start (Docker)

```bash
# Avvia con Docker
./start-docker.sh
# oppure
make docker-up
```

```bash
# Spegni tutto
make docker-down
```

📖 **Guida completa API**: vedi [QUICKSTART.md](QUICKSTART.md)

## Architettura

### Dataset Base (Auto-generato)
- **26 casi cardiologici** (file DICOM) → 286 documenti indicizzati
  - Normal (10), Normal variations (6), Pathological cases (10)
  - 14 categorie diagnostiche diverse
- **Frame extraction**: ~10 frame/caso + metadata (view, fps, motion features)
- **Auto-indexing**: vectorstore Qdrant popolato automaticamente all'avvio

### Pipeline
1. **Build Dataset**: `scripts/build_dataset.py` processa DICOM → `documents.jsonl`
2. **Vectorstore Manager**: auto-indexing con SentenceTransformer (all-MiniLM-L6-v2)
3. **RAG Service**: retrieval semantico + prompt augmentation
4. **FastAPI Backend**: REST API per chat, upload DICOM, gestione documenti

## Comandi Utili

```bash
# Rigenerare dataset (se aggiungi DICOM in data/raw_data/)
./rebuild_dataset.sh

# Test API endpoint - Analyze case
curl -X POST http://localhost:8000/analyze-case \
  -F "file=@data/raw_data/Normal/IM-0001-0032.dcm" \
  -F "report_text=Optional clinical report"

# Vedere tutti gli endpoint disponibili
# Visita http://localhost:8000/docs
```

## Dettagli Tecnici

- **Embeddings**: SentenceTransformer all-MiniLM-L6-v2 (384 dim, locale, no API)
- **Vectorstore**: Qdrant in-memory (26 cases + 13 guidelines)
- **LLM**: OpenAI GPT-4o con vision (multimodale)
- **DICOM**: pydicom + PIL per frame extraction + metadata
- **Backend**: FastAPI + Pydantic + CORS

## Struttura

```
├── api/main.py                    # FastAPI app
├── src/vectorstore_manager.py     # Singleton Qdrant + auto-indexing
├── scripts/
│   ├── build_dataset.py           # DICOM → documents.jsonl
│   └── multimodal_rag_openai.py   # Pipeline RAG multimodale
├── data/
│   ├── raw_data/                  # DICOM originali (26 file, 14 categorie)
│   ├── dataset_built/             # Auto-generato (documents.jsonl + images/)
│   └── guidelines_txt/            # Linee guida (13 file .txt)
├── start.sh                       # Avvio completo
└── rebuild_dataset.sh             # Rigenera dataset
```

## Requisiti

- Python 3.9+
- OpenAI API key
- ~2GB RAM (embeddings + vectorstore in-memory)

## Privacy Notice

⚠️ **Original DICOM files are NOT included** in this repository.

Only the anonymized derived dataset is provided. All patient-identifiable information has been removed in compliance with privacy regulations.

To verify anonymization:
```bash
python3 scripts/verify_anonymization.py
```