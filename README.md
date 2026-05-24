# RAG System for Multimodal Data Management

Sistema RAG (Retrieval-Augmented Generation) multimodale avanzato per la gestione, la comprensione e il supporto decisionale clinico in cardiologia. Il framework esegue un allineamento semantico cross-modale proiettando nello stesso spazio latente segnali elettrici (ECG), immagini radiologiche (TAC estratte da file DICOM) e simulazioni geometriche 3D di keypoints provenienti da Unity, integrando linee guida internazionali per generare risposte strutturate assistite da AI.

## 🚀 Innovazioni Introdotte (Contributo di Tesi)

Rispetto ai prototipi di retrieval tradizionali, questo framework introduce quattro avanzamenti ingegneristici core:

1. **Spazio Vettoriale ad Alta Risoluzione (3072 dim):** Utilizzo nativo del modello `gemini-embedding-001` via Google GenAI SDK, ottimizzando la granularità della comprensione semantica rispetto ai vecchi modelli a 384 dimensioni.
2. **Clinical Reranking Deterministico:** Algoritmo custom di post-retrieval che analizza i payload estratti da Qdrant e forza in cima ai risultati le emergenze tempo-dipendenti (es. STEMI, occlusioni acute della LAD, infarti in corso), anteponendo la priorità clinica salvavita alla pura somiglianza statistica del testo.
3. **Pipeline di Fault-Tolerance (DICOM Layer):** Gestione asincrona delle eccezioni sulla struttura binaria dei file. In caso di corruzione del file `.dcm`, il sistema evita il crash del server, isola il fallimento visivo restituendo un array di frame vuoto e attiva un paracadute clinico basato sulle sole note di triage e sulle linee guida.
4. **Zero-Chunking Strategy:** Caricamento della letteratura medica internazionale (ASE/ESC) a blocco integro all'interno della collezione vettoriale, preservando la coerenza scientifica e la fluidità di lettura senza troncamenti o spezzettamenti artificiali a metà parola.

## ⚠️ Privacy & Anonymization

**All patient data has been fully anonymized** in compliance with GDPR and HIPAA regulations.

- ✅ All DICOM metadata is anonymized at the ingestion layer (names, dates, IDs removed)
- ✅ Only non-identifiable clinical/technical data is preserved
- ✅ Safe for public repository publication

## 🚀 Quick Start (Manuale - Consigliato)

```bash
# 1. Setup ambiente
source .venv/bin/activate
```
# 2. Imposta API key Google Gemini
export GOOGLE_API_KEY="AIzaSy..."

# 3. Avvia il sistema (FastAPI Backend + Streamlit UI)
# Esegui in due terminali separati:
python3 -m uvicorn api.main:app --port 8000  
python3 -m streamlit run frontend/app.py --server.port 8501

# Il sistema mette a disposizione:

  - Backend FastAPI: http://localhost:8000

  - Streamlit UI: http://localhost:8501

  - Vectorstore con auto-indexing nativo

# Accedi a:

  - UI Streamlit: http://localhost:8501 (🔍 Retrieval Cross-Modale, 🔬 Analisi Caso Clinico Corrente, 📋 Amministrazione Database RAG)

  - API Docs: http://localhost:8000/docs

# UI Streamlit Dashboard Struttura
## Dashboard 1: 🔍 Retrieval Cross-Modale
  Interfaccia di ricerca semantica globale in linguaggio naturale su dati eterogenei:

  Interroga lo spazio vettoriale comune per trovare ECG, CT (TAC) e Simulazioni di Unity.

  Applica l'algoritmo di Clinical Reranking per forzare la prioritizzazione dei codici rossi in cima ai risultati.

  Mostra i match con i punteggi di affinità vettoriale reali e visualizza i reperti grafici collegati tramite Smart-Match.

## Dashboard 2: 🔬 Analisi Caso Clinico Corrente (PRINCIPALE)
  Upload immediato (Drag & Drop) di un file diagnostico (.dcm, .png, .jpg) + note del triage per analisi spot in tempo reale:

  Sfrutta la pipeline di Fault-Tolerance per gestire in modo sicuro eventuali file DICOM corrotti evitando il crash del server.

  Invia il contesto multimodale alle API di Gemini Core per generare un Report Diagnostico Integrato strutturato.

  Mostra l'ID univoco del reperto e isola i log tecnici di acquisizione in un expander inferiore.

## Dashboard 3: 📋 Amministrazione Database RAG
  Soft Reset Cluster Vettoriale: Svuota completamente la RAM di Qdrant e riesegue da zero l'auto-indexing a 3072 dimensioni (utile per aggiornare le linee guida).

  Mostra Lista File Indicizzati: Interroga il backend per elencare in formato strutturato i documenti e le fonti attive nel sistema.

# Architettura e Pipeline
Dataset Base
Casi clinici multimodali (ECG originali stabili, segmenti di TAC e campionamenti da Unity) indicizzati nel file documents.jsonl.

Zero-Chunking Strategy: Caricamento delle linee guida mediche intere (.txt) nella collezione dedicata per preservare l'integrità del testo senza tagli artificiali.

Auto-indexing: Il vectorstore Qdrant in-memory viene popolato automaticamente all'avvio o durante il Soft Reset eseguendo il file scripts/index_Qdrant.py.

# Pipeline Logica
Vectorstore Manager: scripts/index_Qdrant.py configura le collezioni Qdrant in memoria (cases e guidelines) con dimensione fissa a 3072.

RAG Service: api/services/rag_service.py gestisce il retrieval semantico su Qdrant, applica l'algoritmo di Clinical Reranking per dare priorità ai codici rossi e costruisce il prompt ibrido per l'LLM.

FastAPI Backend: api/main.py espone le REST API per la chat (/chat), l'upload e analisi dei file (/analyze-case) e il reset del database (/flush-rag).

# API Endpoints & Esempi di Comandi
POST /analyze-case ✅ [PRINCIPALE]
Endpoint per l'upload del file clinico (DICOM o Immagine) + optional report per l'analisi multimodale spot.

# Bash
curl -X POST http://localhost:8000/analyze-case \
  -F "file=@/path/to/file.dcm" \
  -F "report_text=Optional clinical findings"
Esempio di Risposta (JSON Response):

# Test rapidi da Terminale
Bash
# Test /analyze-case inviando un file campione locale
curl -X POST http://localhost:8000/analyze-case \
  -F "file=@data/current/dicom/case_sample.dcm"

# Test della chat RAG globale con Clinical Reranking
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Sospetto infarto acuto", "model": "gemini", "rag_type": "hybrid", "evaluate": false}'

# Reset completo del database vettoriale in-memory
curl -X POST http://localhost:8000/flush-rag
Dettagli Tecnici dello Stack
Embeddings: Google GenAI SDK - gemini-embedding-001 (3072 dimensioni, nativo via API).

Vectorstore: Qdrant client in-memory (collezioni isolate cases e guidelines).

LLM / Vision: Google Gemini Core API (gemini-2.5-flash / gemini-1.5-flash per analisi multimodale).

DICOM & Images: pydicom + PIL per la lettura dei file e la pipeline di Fault-Tolerance.

Backend & UI: FastAPI + Streamlit Frontend.

# Struttura delle Cartelle
  ├── api/
  │   ├── main.py                    # FastAPI app (router ed endpoint core)
  │   └── services/
  │       ├── doc_service.py         # Gestione documenti, upload e cancellazioni
  │       └── rag_service.py         # Pipeline RAG e Clinical Reranking
  ├── app/
  │   └── streamlit_app.py           # Interfaccia Grafica Streamlit Core
  ├── scripts/
  │   ├── build_dataset.py           # Pipeline DICOM → documents.jsonl
  │   ├── index_guidelines.py        # Ingestion e indicizzazione Linee Guida
  │   ├── index_Qdrant.py            # Singleton Qdrant, auto-indexing e soft reset
  │   └── query_retrieval.py         # Utility per stress-test di retrieval diretto
  ├── data/
  │   ├── raw_data/                  # ECG, TAC e Unity originari (divisi per cartelle)
  │   ├── current/                   # File temporanei caricati dal triage spot
  │   └── dataset_built/             # Dataset strutturato finale (documents.jsonl)
  └── tests/                         # Suite di test automatici (API, Ingestion, Anonymization)


# Requisiti di Sistema
Python 3.11+
Google Gemini API key (configurata nel file .env locale come GOOGLE_API_KEY)
~4GB RAM (vectorstore volatile in-memory e allocazione risorse locali)


