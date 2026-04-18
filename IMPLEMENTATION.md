# Sistema RAG Healthcare - Riepilogo Implementazione

## ✅ Implementato

### 1. Auto-indexing Dataset
- **Script**: `scripts/build_dataset.py`
- **Input**: 26 file DICOM in `data/raw_data/` (14 categorie diagnostiche)
- **Output**: 
  - `data/dataset_built/documents.jsonl` (286 documenti)
  - `data/dataset_built/labels.csv` (27 casi mappati → diagnosis)
  - `data/dataset_built/images/` (260 frame PNG estratti, ~10/caso)
- **Esecuzione**: automatica al primo avvio via `start.sh`, oppure manuale con `./rebuild_dataset.sh`

### 2. Vectorstore Manager (Singleton)
- **File**: `src/vectorstore_manager.py`
- **Caratteristiche**:
  - Qdrant in-memory (configurabile per server remoto)
  - Auto-indexing al primo utilizzo
  - Embedding locale: SentenceTransformer all-MiniLM-L6-v2 (384 dim)
  - Collection:
    - `cases`: 26 case cards (metadata + features estratte)
    - `guidelines`: chunk da 13 file guideline
  - UUID deterministici per ID documenti
  - Gestione errori e logging

### 3. Backend FastAPI
- **File**: `api/main.py`
- **Endpoint**:
  - `POST /chat`: query RAG (cases, guidelines, hybrid, multimodal)
  - `POST /upload-doc`: upload DICOM ed estrazione frame
  - `GET /list-docs`: lista documenti caricati
  - `POST /delete-doc`: rimuovi documento
  - `POST /flush-rag`: reset soft del sistema
- **CORS**: abilitato per sviluppo locale
- **Docs**: Swagger UI su http://localhost:8000/docs

### 4. RAG Service
- **File**: `api/services/rag_service.py`
- **Funzionalità**:
  - Retrieval semantico da vectorstore
  - Supporto per rag_type: cases, guidelines, hybrid
  - Ritorna answer + sources con metadata
  - Preparato per integrazione multimodale

### 5. Script di Avvio
- **File**: `start.sh` (eseguibile)
- **Flusso**:
  1. Verifica/crea ambiente virtuale
  2. Installa dipendenze da requirements.txt
  3. **Build dataset da DICOM** (se non esiste)
  4. Check OPENAI_API_KEY
  5. Inizializza vectorstore (auto-indexing)
  6. Avvia FastAPI backend (uvicorn, hot-reload)

### 6. Documentazione
- **README.md**: overview architettura + quick start
- **QUICKSTART.md**: guida API dettagliata con esempi curl
- **rebuild_dataset.sh**: script per rigenerare dataset

## 📊 Dati Indicizzati

### Cases (26 documenti)
- **Normal**: 10 casi
- **Normal with septal hypertrophy**: 1 caso
- **Normal function mitral valve prolapse**: 1 caso
- **Normal function septal hypertrophy athlete heart**: 1 caso
- **Normal function septal hypertrophy in aortic stenosis**: 1 caso
- **Normal function severe septal hypertrophy**: 1 caso
- **Normal tendinous cord function in apical region**: 1 caso
- **Dilated cardiomyopathy with global dysfunction**: 1 caso
- **Global left ventricular dysfunction**: 1 caso
- **Global left ventricular dysfunction and apical akinesia**: 1 caso
- **Inferoapical septal akinesia**: 4 casi
- **Left ventricular apical inferior septal aneurysm**: 1 caso
- **Left ventricular dilatation with apical dyskinesia**: 1 caso
- **Left ventricular dysfunction with apical akinesia and apical thrombosis**: 1 caso

### Guidelines (13 file)
- `dilated_cardiomyopathy_background.txt`
- `global_left_ventricular_dysfunction.txt`
- `global_left_ventricular_dysfunction_and_apical_akinesia.txt`
- `inferoapical_akinesia_background.txt`
- `Left_ventricular_apical_inferior_septal_aneurysm.txt`
- `Left_ventricular_dilatation_with_apical_dyskinesia.txt`
- `left_ventricular_dysfunction_with_apical_akinesia_and_apical_thrombosis.txt`
- `normal_echo_background.txt`
- `normal_function_mitral_valve_prolapse.txt`
- `normal_function_septal_hypertrophy_athlete_heart.txt`
- `normal_function_septal_hypertrophy_in_aortic_stenosis.txt`
- `normal_function_severe_septal_hypertrophy.txt`
- `normal_tendinous_cord_function_in_apical_region.txt`

### Metadata Estratte da DICOM
- View, Stage, FPS, Durata effettiva, Heart rate
- Numero frame, Dimensioni, Photometric interpretation
- **Feature calcolate**:
  - `mean_intensity`: intensità media normalizzata
  - `motion_energy`: energia del movimento (diff frame consecutivi)
  - `motion_std`: deviazione standard movimento

## 🚀 Come Usare

### Avvio Rapido
```bash
export OPENAI_API_KEY="sk-..."
./start.sh
```

### Test API
```bash
# Query RAG sui casi
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the characteristics of dilated cardiomyopathy?",
    "model": "gpt-4o",
    "rag_type": "cases",
    "evaluate": false
  }'

# Risposta include:
# - answer: testo generato (stub)
# - sources: array con case/guideline recuperati
# - session_id: per conversazioni
```

### Rigenerare Dataset
```bash
# Se aggiungi nuovi DICOM in data/raw_data/
./rebuild_dataset.sh
# Poi riavvia il backend per re-indexing
```

## 🔧 Configurazione

### Passare a Qdrant Remoto
1. Avvia Qdrant server:
   ```bash
   docker run -d -p 6333:6333 qdrant/qdrant
   ```

2. Modifica `src/vectorstore_manager.py` riga 27:
   ```python
   _vectorstore = QdrantVectorstore(host="localhost", port=6333)
   ```

3. Riavvia backend

### Variabili d'Ambiente
- `OPENAI_API_KEY`: richiesta per LLM (obbligatoria)
- `QDRANT_HOST`: host Qdrant server (default: localhost)
- `QDRANT_PORT`: porta Qdrant (default: 6333)
- `USE_REMOTE_QDRANT`: "true" per usare server remoto (implementabile)

## 📁 Struttura Completa

```
Rag-system-4-healthcare/
├── api/
│   ├── main.py                         # FastAPI app (CORS, endpoints)
│   └── services/
│       ├── doc_service.py              # Upload DICOM, list/delete docs
│       └── rag_service.py              # RAG query logic + retrieval
├── app/
│   └── streamlit_app.py                # Frontend (WIP)
├── data/
│   ├── raw_data/                       # DICOM originali (INPUT)
│   │   ├── Normal/                     # 10 file .dcm
│   │   ├── Normal_with_septal_hypertrophy/  # 1 file
│   │   ├── dilated_cardiomyopathy_with_global_dysfunction/  # 1 file
│   │   ├── global_left_ventricular_dysfunction/  # 1 file
│   │   ├── global_left_ventricular_dysfunction_and_apical_akinesia/  # 1 file
│   │   ├── inferoapical_septal_akinesia/    # 4 file
│   │   ├── Left_ventricular_apical_inferior_septal_aneurysm/  # 1 file
│   │   ├── Left_ventricular_dilatation_with_apical_dyskinesia/  # 1 file
│   │   ├── left_ventricular_dysfunction_with_apical_akinesia_and_apical_thrombosis/  # 1 file
│   │   ├── normal_function_mitral_valve_prolapse/  # 1 file
│   │   ├── normal_function_septal_hypertrophy_athlete_heart/  # 1 file
│   │   ├── normal_function_septal_hypertrophy_in_aortic_stenosis/  # 1 file
│   │   ├── normal_function_severe_septal_hypertrophy/  # 1 file
│   │   └── normal_tendinous_cord_function_in_apical_region/  # 1 file
│   ├── dataset_built/                  # AUTO-GENERATO
│   │   ├── documents.jsonl             # 286 documenti (26 cases + 260 frames)
│   │   ├── labels.csv                  # Case ID → Label mapping (27 righe)
│   │   └── images/                     # Frame estratti (~10 per caso)
│   │       ├── <case_id_1>/
│   │       │   ├── frame_1.png ... frame_10.png
│   │       └── ...
│   └── guidelines_txt/                 # Linee guida (INPUT)
│       ├── dilated_cardiomyopathy_background.txt
│       ├── global_left_ventricular_dysfunction.txt
│       ├── global_left_ventricular_dysfunction_and_apical_akinesia.txt
│       ├── inferoapical_akinesia_background.txt
│       ├── Left_ventricular_apical_inferior_septal_aneurysm.txt
│       ├── Left_ventricular_dilatation_with_apical_dyskinesia.txt
│       ├── left_ventricular_dysfunction_with_apical_akinesia_and_apical_thrombosis.txt
│       ├── normal_echo_background.txt
│       ├── normal_function_mitral_valve_prolapse.txt
│       ├── normal_function_septal_hypertrophy_athlete_heart.txt
│       ├── normal_function_septal_hypertrophy_in_aortic_stenosis.txt
│       ├── normal_function_severe_septal_hypertrophy.txt
│       └── normal_tendinous_cord_function_in_apical_region.txt
├── scripts/
│   ├── build_dataset.py                # DICOM → documents.jsonl (pipeline completa)
│   ├── dicom_to_frames_current.py      # Estrazione frame singolo caso
│   ├── multimodal_rag_openai.py        # Pipeline RAG multimodale
│   ├── index_Qdrant.py                 # Indexing manuale (legacy, non più usato)
│   ├── index_guidelines.py             # Indexing manuale guidelines (legacy)
│   ├── query_retrieval.py              # Test retrieval (legacy)
│   └── eval_hitk_mrr.py                # Evaluation metrics (WIP)
├── src/
│   ├── __init__.py
│   └── vectorstore_manager.py          # ⭐ Singleton Qdrant + auto-indexing
├── .venv/                              # Ambiente virtuale Python
├── requirements.txt                    # Dipendenze
├── start.sh                            # ⭐ Script avvio completo (eseguibile)
├── rebuild_dataset.sh                  # ⭐ Rigenera dataset (eseguibile)
├── README.md                           # Overview progetto
├── QUICKSTART.md                       # Guida API + esempi
└── LICENSE
```

## 🔄 Workflow Completo

```
[DICOM files in raw_data/]
         ↓
    build_dataset.py
         ↓
    documents.jsonl (286 docs) + images/ (260 frames)
         ↓
    vectorstore_manager.py (auto-indexing)
         ↓
    Qdrant collections (26 cases + 13 guidelines)
         ↓
    rag_service.py (retrieval)
         ↓
    FastAPI /chat endpoint
         ↓
    [Response con answer + sources]
```

## 🎯 Prossimi Step

### Priorità Alta
- [ ] Integrare `multimodal_rag_openai.py` completamente in `rag_service.py`
- [ ] Implementare gestione frame del caso corrente in upload-doc
- [ ] Aggiungere chiamata effettiva a OpenAI GPT-4o (attualmente stub)

### Priorità Media
- [ ] Implementare sessioni/conversazioni con memoria
- [ ] Aggiungere metriche evaluation (ragas)
- [ ] Completare frontend Streamlit
- [ ] Logging strutturato (JSON)

### Priorità Bassa
- [ ] Passare a Qdrant persistente (Docker)
- [ ] Caching risposte
- [ ] Rate limiting API
- [ ] Autenticazione/autorizzazione

## 🐛 Known Issues

1. **Ricerca semantica casi**: attualmente recupera casi "Normal" anche per query su patologie (embedding troppo generico per metadata, serve prompt engineering o fine-tuning)
2. **OpenAI call**: stub, non ancora integrata la chiamata vera
3. **Session management**: non implementato (session_id ignorato)
4. **Evaluation**: metriche non collegate

## 💡 Note Tecniche

- **UUID deterministici**: usiamo `uuid.uuid5` con namespace DNS per generare ID riproducibili da case_id/guideline_id
- **DenseEmbedding**: datapizza richiede oggetti `DenseEmbedding(name, vector)`, non dict/list
- **Chunk API**: `QdrantVectorstore.add()` accetta `Chunk` objects, non parametri separati
- **Search results**: ritorna lista di `Chunk`, non oggetti con `.score` (score è interno)
- **Embedding dimensioni**: 384 per all-MiniLM-L6-v2 (non 1536 di OpenAI)

## 📞 Supporto

Per problemi o domande:
1. Controlla i log del backend (stdout di uvicorn)
2. Verifica che documents.jsonl esista e non sia vuoto
3. Testa vectorstore manualmente: `python3 src/vectorstore_manager.py`
4. Controlla che OPENAI_API_KEY sia settata
