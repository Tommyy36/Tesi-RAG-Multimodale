# RAG Healthcare System - Quick Start

## Setup

1. **Attiva l'ambiente virtuale**:
   ```bash
   source .venv/bin/activate
   ```

2. **Imposta la chiave API OpenAI**:
   ```bash
   export OPENAI_API_KEY="sk-..."
   ```

3. **Avvia il sistema**:
   ```bash
   make start
   # oppure
   ./start.sh
   ```
   
   Lo script automaticamente:
   - Verifica e attiva l'ambiente
   - Installa dipendenze
   - **Genera dataset da file DICOM** (se non esiste `documents.jsonl`)
   - Inizializza e popola il vectorstore (auto-indexing)
   - **Avvia il backend FastAPI** su http://localhost:8000
   - **Avvia Streamlit UI** su http://localhost:8501

## UI Streamlit

Una volta avviato, accedi a **http://localhost:8501**

### Tab 1: 🔬 Analyze Case (PRINCIPALE)
Upload un file DICOM + optional clinical report per analisi multimodale completa:
- Estrae frame dall'ecografia
- Recupera casi simili tramite RAG semantico
- Genera risposta clinica assistita da GPT-4o con vision
- Mostra fonti (case retrieval) e valutazione

### Tab 2: 📤 Upload DICOM
Upload e storage di un file DICOM senza analisi immediata.

### Tab 3: 📋 Manage Files
- Lista file caricati nel sistema
- Elimina file specifici

### Bottom Actions
- 🔄 **Reset RAG Collections**: Soft reset (ricrea tutte le collezioni)
- 🗑️ **Clear Session**: Pulisce lo stato della UI

## Dataset Base

Al primo avvio, lo script esegue automaticamente:

```bash
python3 scripts/build_dataset.py
```

Questo processa i file DICOM in `data/raw_data/` e genera:
- **documents.jsonl**: 26 case cards + 260 frame metadata (286 documenti totali)
- **labels.csv**: mapping case_id → diagnosis label
- **images/**: frame estratti da ogni caso (~10 frame per DICOM)

**Cartelle raw_data** (14 categorie diagnostiche):
- Normal (10 casi)
- Normal variations: septal hypertrophy, mitral valve prolapse, athlete heart, etc. (6 casi)
- Pathological: dilated cardiomyopathy, global LV dysfunction, inferoapical akinesia, etc. (10 casi)

### Rigenerare il dataset

Se aggiungi nuovi file DICOM o vuoi rigenerare:

```bash
./rebuild_dataset.sh
```

Questo cancella e ricrea `documents.jsonl` e le immagini.

## Struttura

- **Backend API**: FastAPI su porta 8000
- **Vectorstore**: Qdrant in-memory con auto-indexing
- **Dataset base**: 26 casi cardiologici (DICOM) processati automaticamente
- **Collection indicizzate**:
  - `cases`: 26 case_cards da `data/dataset_built/documents.jsonl` (generato da raw DICOM)
  - `guidelines`: chunk da 13 file guideline in `data/guidelines_txt/*.txt`

## API Endpoints

### POST /analyze-case ✅ [PRINCIPALE]
Endpoint principale: upload DICOM + optional report per analisi multimodale completa.

```bash
curl -X POST http://localhost:8000/analyze-case \
  -F "file=@/path/to/file.dcm" \
  -F "report_text=Optional clinical findings"
```

**Parametri**:
- `file`: file DICOM (required)
- `report_text`: clinical report in testo (optional)

**Response**:
```json
{
  "ok": true,
  "filename": "IM-0001-0032.dcm",
  "num_frames": 10,
  "frames_dir": "/path/to/extracted/frames",
  "analysis": {
    "answer": "Clinical analysis text from GPT-4o...",
    "sources": [
      {
        "type": "case",
        "id": "case_123",
        "score": 0.87,
        "snippet": "...",
        "metadata": {...}
      }
    ],
    "evaluation": null
  }
}
```
## Test rapido

```bash
# Test /analyze-case (endpoint principale) da file DICOM locale
curl -X POST http://localhost:8000/analyze-case \
  -F "file=@data/raw_data/Normal/IM-0001-0032.dcm"

# Con report opzionale
curl -X POST http://localhost:8000/analyze-case \
  -F "file=@data/raw_data/Normal/IM-0001-0032.dcm" \
  -F "report_text=Normal cardiac function"

# Test /list-docs per vedere file caricati
curl "http://localhost:8000/list-docs?rag_type=cases"

# Reset RAG collections
curl -X POST http://localhost:8000/flush-rag
```

## Docs interattive

Apri http://localhost:8000/docs per Swagger UI con tutti gli endpoint.

## Note

- **documents.jsonl**: se manca, la collection `cases` sarà vuota (solo guidelines saranno indicizzate)
- **Auto-indexing**: al primo avvio il vectorstore viene popolato automaticamente
- **In-memory**: i dati sono persi al restart (puoi passare a Qdrant remoto modificando `vectorstore_manager.py`)

## Passare a Qdrant remoto

1. Avvia Qdrant server:
   ```bash
   docker run -d -p 6333:6333 qdrant/qdrant
   ```

2. Modifica `src/vectorstore_manager.py`:
   ```python
   vectorstore = QdrantVectorstore(host="localhost", port=6333)
   ```
