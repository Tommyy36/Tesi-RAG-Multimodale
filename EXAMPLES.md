# Esempi Pratici di Esecuzione e Testing - RAG Healthcare

Questo documento raccoglie gli esempi d'uso, i comandi di testing tramite `curl` e le procedure diagnostiche per verificare l'allineamento semantico e la robustezza del sistema.

---

## 1. Avvio Manuale dell'Infrastruttura

Esegui i comandi di attivazione e avvio all'interno di due terminali separati:

```bash
# Terminale 1: Configurazione ed esecuzione del Backend FastAPI
source .venv/bin/activate
export GOOGLE_API_KEY="AIzaSy..."
python3 -m uvicorn api.main:app --reload --port 8000
```

# Terminale 2: Esecuzione dell'Interfaccia Utente Streamlit
source .venv/bin/activate
python3 -m streamlit run frontend/app.py --server.port 8501

2. Query RAG Cross-Modale (Endpoint /chat)
Invia una query in linguaggio naturale per estrarre i casi allineati nello spazio vettoriale a 3072 dimensioni. L'algoritmo applica il Clinical Reranking automatico per portare le emergenze tempo-dipendenti in cima.

Bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Sospetto infarto acuto in corso con dolore retrosternale oppressivo",
    "model": "gemini",
    "rag_type": "hybrid",
    "evaluate": false
  }'
3. Analisi Caso Clinico Corrente (Endpoint /analyze-case)
Endpoint principale per l'upload di un reperto diagnostico (.dcm, .png, .jpg) accoppiato alle note del triage. La pipeline integra la logica di Fault-Tolerance per resistere a file binari DICOM corrotti.

Bash
curl -X POST http://localhost:8000/analyze-case \
  -F "file=@data/current/dicom/case_sample.dcm" \
  -F "report_text=Paziente in codice rosso, alterazione del tratto ST rilevata"
Risposta JSON Attesa (Response)
JSON
{
  "file_id": "5ae93346-96d0-4979-9884-b59002e9a043",
  "status": "Dati pronti per RAG Multimodale",
  "frames_dir": "data/current/frames/5ae93346-96d0-4979-9884-b59002e9a043",
  "dicom_path": "data/current/dicom/5ae93346-96d0-4979-9884-b59002e9a043.dcm",
  "frames": ["frame_0.png"],
  "analysis": {
    "answer": "Report diagnostico integrato generato dal framework core..."
  }
}
4. Monitoraggio e Ispezione dei Documenti
Lista dei file indicizzati attivi nelle collezioni
Bash
curl "http://localhost:8000/list-docs?rag_type=cases"
Reset totale delle Collezioni Vettoriali (Soft Reset)
Svuota la memoria volatile di Qdrant e riesegue l'auto-indexing a 3072 dimensioni delle linee guida intere (Zero-Chunking).

Bash
curl -X POST http://localhost:8000/flush-rag
5. Test Standalone dei Moduli Ausiliari
È possibile lanciare i singoli script python da terminale per testare i componenti al di fuori del ciclo di vita del server web.

Bash
# Sincronizzazione e rigenerazione manuale delle collezioni Qdrant
python3 scripts/index_Qdrant.py

# Caricamento e indicizzazione isolata delle linee guida internazionali (.txt)
python3 scripts/index_guidelines.py

# Stress-test di retrieval diretto e verifica della distanza del coseno
python3 scripts/query_retrieval.py
6. Risoluzione dei Problemi Comuni (Common Errors)
Error: "Port 8000 already in use"
Il server backend è rimasto appeso in background su una sessione precedente.

Soluzione: Rilascia la porta forzatamente da terminale:

Bash
lsof -ti:8000 | xargs kill -9
Error: "GOOGLE_API_KEY not set"
La chiave di autenticazione per le API di Google non è stata esportata correttamente nell'ambiente di runtime corrente.

Soluzione: Esporta nuovamente la chiave e verifica la presenza del file .env:

Bash
export GOOGLE_API_KEY="La_Tua_Chiave_AI_Studio"
echo $GOOGLE_API_KEY