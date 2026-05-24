# RAG Healthcare System - Quick Start

## 1. Setup Ambiente

Attiva l'ambiente virtuale ed esporta la chiave API di Google Gemini nel tuo terminale:

```bash
source .venv/bin/activate
export GOOGLE_API_KEY="AIzaSy..."
```

2. Avvio dell'Infrastruttura
Esegui i comandi di avvio in due finestre del terminale separate:

Bash
# Terminale 1 (Backend Core FastAPI)
python3 -m uvicorn api.main:app --port 8000

# Terminale 2 (Frontend UI Streamlit)
python3 -m streamlit run frontend/app.py --server.port 8501
All'avvio, il sistema configurerà automaticamente lo spazio vettoriale in memoria a 3072 dimensioni e genererà il file di interscambio documents.jsonl.

3. Test Rapidi di Diagnostica (da Terminale)
Puoi inviare delle richieste rapide tramite curl per verificare che i singoli moduli stiano rispondendo correttamente:

Bash
# Test 1: Verifica l'endpoint principale di analisi multimodale (Vision + Note)
curl -X POST http://localhost:8000/analyze-case \
  -F "file=@data/current/dicom/case_sample.dcm" \
  -F "report_text=Paziente con dolore retrosternale oppressivo"

# Test 2: Verifica l'endpoint della chat RAG globale (Clinical Reranking)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Sospetto infarto acuto", "model": "gemini", "rag_type": "hybrid", "evaluate": false}'

# Test 3: Forza un Soft Reset completo di Qdrant pulendo la memoria volatile
curl -X POST http://localhost:8000/flush-rag
4. Riferimenti Utili
Interfaccia Grafica: http://localhost:8501

Documentazione Interattiva Swagger: http://localhost:8000/docs
