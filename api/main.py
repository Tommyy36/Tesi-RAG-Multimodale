"""
Backend Core FastAPI - Tesi Thomas
Infrastruttura di Orchestrazione RAG Multimodale e Allineamento Spaziale Vettoriale
"""
import os
from fastapi import FastAPI, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, Any, Dict, List
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Caricamento delle variabili d'ambiente protette (.env)
load_dotenv()

from api.services.doc_service import save_current_dicom_and_extract_frames, list_current_files, delete_current_file
from api.services.rag_service import answer_question, analyze_current_case
from scripts.index_Qdrant import reset_collections

app = FastAPI(
    title="Multimodal RAG Framework API - Thomas Russo",
    description="Infrastruttura backend per l'allineamento semantico cross-modale di segnali clinici, immagini radiologiche e simulazioni 3D.",
    version="1.0.0"
)

# Configurazione delle policy CORS per l'interconnessione sicura con il frontend Streamlit
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- SCHEMI DI MODELLAZIONE DATI (PYDANTIC) ----

class ChatRequest(BaseModel):
    question: str
    model: str
    rag_type: str
    evaluate: bool = False
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    answer: str
    sources: Optional[List[Dict[str, Any]]] = None
    session_id: Optional[str] = None
    evaluation: Optional[Any] = None


# ---- ENDPOINTS CORE ----

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """
    POST /chat
    Endpoint principale di Retrieval Cross-Modale. Accetta una query in linguaggio naturale,
    interroga il Vector Store Qdrant applicando il Clinical Reranking e genera l'analisi diagnostica tramite LLM.
    """
    out = answer_question(
        question=req.question,
        model=req.model,
        rag_type=req.rag_type,
        session_id=req.session_id,
        evaluate=req.evaluate,
    )
    return ChatResponse(**out)


@app.post("/upload-doc")
async def upload_doc(
    file: UploadFile = File(...),
):
    """
    POST /upload-doc
    Riceve un file diagnostico multimediale, avvia la pipeline di estrazione e lo indicizza temporaneamente nel file system.
    """
    result = await save_current_dicom_and_extract_frames(file)
    return {"ok": True, **result}


@app.post("/analyze-case")
async def analyze_case(
    file: UploadFile = File(...),
    report_text: Optional[str] = Form(None)
):
    """
    POST /analyze-case
    Pipeline di Analisi Concorsuale Multimodale Spot. Riceve un reperto grafico (DICOM, TAC, ECG, Unity)
    e le note cliniche del triage, estrae le caratteristiche ed esegue il flusso RAG integrato per la diagnosi differenziale.
    """
    result = await save_current_dicom_and_extract_frames(file)
    analysis = analyze_current_case(report_text=report_text, frames_dir=result.get("frames_dir"))
    return {"ok": True, **result, "analysis": analysis}


@app.get("/list-docs")
def list_docs(rag_type: str):
    """
    GET /list-docs
    Restituisce l'elenco dei documenti e delle linee guida attualmente attive nella base di conoscenza del framework.
    """
    return list_current_files()


@app.post("/delete-doc")
def delete_doc(payload: Dict[str, Any]):
    """
    POST /delete-doc
    Rimuove in modo selettivo un documento o una cartella clinica dallo storage locale del sistema.
    """
    file_id = payload.get("file_id")
    return delete_current_file(file_id)


@app.post("/flush-rag")
def flush_rag():
    """
    POST /flush-rag
    Innesca un Soft Reset del Cluster Vettoriale, svuotando e reinizializzando le collezioni su Qdrant.
    """
    try:
        reset_collections()
        return {"ok": True, "message": "RAG collections reset."}
    except Exception as e:
        return {"ok": False, "error": str(e)}, 500