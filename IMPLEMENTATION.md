# Sistema RAG Healthcare - Riepilogo Implementazione (Thomas Refactoring)

## ✅ Implementato e Attivo

### 1. Ingestion & Alignment Layer
- **Script**: `scripts/build_dataset.py`
- **Input**: File diagnostici storici (ECG originali, blocchi TAC e metadati di Unity)
- **Output**: `data/dataset_built/documents.jsonl` (unione consolidata dei casi clinici multimodali)
- **Esecuzione**: Automatizzata all'avvio del sistema o richiamabile manualmente.

### 2. Moduli di Indicizzazione e Controllo Vettoriale
- **File**: `src/vectorstore_manager.py` (Singleton Qdrant Client configurato in In-Memory Isolation Mode)
- **Script Attivi**:
  - `scripts/index_Qdrant.py`: Gestisce l'auto-indexing, il flush completo delle tabelle vettoriali e la riconfigurazione dello spazio metrico.
  - `scripts/index_guidelines.py`: Script dedicato al caricamento massivo e all'indicizzazione delle linee guida internazionali (ASE/ESC) con strategia *Zero-Chunking*.
  - `scripts/query_retrieval.py`: Utility standalone per eseguire stress-test di retrieval diretto e calcolo delle distanze del coseno fuori dal server web.
- **Risoluzione Spazio Vettoriale**: Configurazione nativa fissa a **3072 dimensioni** adattata per l'embedding pesante di Google.

### 3. Backend FastAPI Core
- **File**: `api/main.py`
- **Endpoint Core**:
  - `POST /chat`: Interrogazione RAG globale cross-modale accoppiata all'algoritmo di **Clinical Reranking** per la prioritizzazione automatica dei codici rossi.
  - `POST /analyze-case`: Endpoint principale di triage spot (Vision + Testo) dotato di pipeline di **Fault-Tolerance** per la gestione resiliente di file DICOM corrotti.
  - `GET /list-docs`: Ispezione dei flussi e monitoraggio dei documenti attivi nel cluster.
  - `POST /flush-rag`: Reset software istantaneo delle collezioni in memoria volatile.

### 4. RAG Service & Interfaccia Frontend
- **File**: `api/services/rag_service.py` (Orchestratore del retrieval concorrente dalle collezioni `cases` e `guidelines` e costruttore dei prompt ibridi).
- **File**: `frontend/app.py` (Dashboard Streamlit evoluta divisa nelle tre viste operative: Consultazione Semantica, Analisi Spot d'Urgenza e Console Admin).

---

## 📊 Dati e Contesti Indicizzati

### Collezioni Vettoriali in RAM (3072 dim)
- **Collection `cases`**: Mappatura densa dei casi clinici eterogenei (ECG, TAC e Keypoints spaziali di Unity) e delle relative annotazioni diagnostiche strutturate.
- **Collection `guidelines`**: Caricamento integrale e non frammentato di 13 file di letteratura scientifica internazionale (sfondi teorici su cardiomiopatie, disfunzioni ventricolari, acinesie e pattern normali).

### Metadati Estratti e Sincronizzati
- Frequenza cardiaca, numero di frame, dimensioni dei pixel e orientamento delle viste.
- **Feature Computate**: `mean_intensity` (intensità media dei pixel), `motion_energy` (energia cinetica tra frame consecutivi del flusso binario) e `motion_std`.

---

## 🛠️ Tecnologie dello Stack Principale

- **Embeddings Engine**: Google GenAI SDK - `gemini-embedding-001` (3072 dimensioni).
- **LLM / Vision Core**: Generative Model Family (`gemini-2.5-flash` / `gemini-1.5-flash`).
- **Vector Database**: Qdrant Client (In-Memory Isolation).
- **Data Layer**: `pydicom` + `PIL` con cattura delle eccezioni a livello di blocco per la tolleranza ai guasti.
- **Web Layer**: FastAPI (Porta 8000) + Streamlit (Porta 8501).