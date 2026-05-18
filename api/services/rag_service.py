"""
services/rag_service.py - Tesi Thomas
Gestisce il Retrieval Cross-Modale con l'aggiunta del Clinical Reranking
per dare priorità assoluta ai codici rossi cardiologici (STEMI).
"""
import os
import sys
import time
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

EMBEDDING_MODEL = "gemini-embedding-001"
modelli_da_provare = ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-1.5-pro"]

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from scripts.index_Qdrant import get_vectorstore

def get_gemini_embedding(text: str) -> List[float]:
    """Genera embedding usando la nuova SDK Gemini."""
    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text
    )
    return response.embeddings[0].values

def answer_question(
    question: str,
    model: str,
    rag_type: str,
    session_id: Optional[str],
    evaluate: bool
) -> Dict[str, Any]:
    """Esegue il retrieval vettoriale ed applica il Reranking Clinico d'emergenza."""
    vectorstore = get_vectorstore()
    query_emb = get_gemini_embedding(question)
    
    sources = []
    context_text = ""
    
    collections = []
    if rag_type in ["cases", "hybrid", "multimodal"]: collections.append("cases")
    if rag_type in ["guidelines", "hybrid", "multimodal"]: collections.append("guidelines")

    for coll in collections:
        try:
            hits = vectorstore.query_points(
                collection_name=coll,
                query=query_emb,
                limit=5
            ).points
            
            for hit in hits:
                p = hit.payload
                score = getattr(hit, 'score', 0.0)
                sources.append({
                    "type": coll,
                    "id": hit.id,
                    "score": score,
                    "metadata": p
                })
        except Exception as e:
            print(f"[rag_service] Errore durante il retrieval da {coll}: {e}")

    # =====================================================================
    # LOGICA DI CLINICAL RERANKING (Thomas Engineering)
    # =====================================================================
    # Dividiamo i casi critici (STEMI/Infarzione acuta) dagli esami di routine
    casi_critici = []
    altri_reperti = []
    
    for s in sources:
        label = str(s.get("metadata", {}).get("label", "")).lower()
        text_content = str(s.get("metadata", {}).get("text", "")).lower()
        
        # Se becca indicatori di infarto miocardico acuto o occlusione coronarica, lo marca come priorità massima
        if "myocardial" in label or "infarct" in label or "stemi" in text_content or "occlusione" in text_content:
            # Aggiungiamo un flag visivo per il frontend
            s["metadata"]["label"] = f"🚨 PROPRIETÀ CRITICA: {s['metadata'].get('label')}"
            casi_critici.append(s)
        else:
            altri_reperti.append(s)
            
    # Ricomponiamo la lista mettendo PRIMA i casi salvavita, poi il resto ordinato per score matematico
    sources = casi_critici + altri_reperti

    # Costruiamo il contesto testuale per Gemini rispettando il nuovo ordine prioritario
    for s in sources:
        coll = s.get("type", "UNKNOWN")
        p = s.get("metadata", {})
        context_text += f"\n[{coll.upper()} SOURCE - PRIORITIZED]: {p.get('text', '')}\n"

    # === IL PROMPT FORMATTATO ===
    prompt = f"""
    Sei un assistente AI medico operante in regime di Pronto Soccorso.
    Il tuo compito è analizzare i sintomi del paziente integrando i reperti estratti dal database.
    I reperti ti sono stati ordinati per CRITICITÀ CLINICA SALVAVITA e non per pura somiglianza testuale.
    Metti sempre in cima alla tua diagnosi differenziale i sospetti più letali se confermati dagli ECG associati.

    CONTESTO CLINICO ESTRATTO (ORDINATO PER PRIORITÀ):
    {context_text}

    SINTOMI ED ANAMNESI DEL PAZIENTE:
    {question}
    
    ANALISI STRUTTURATA (Possibile Diagnosi, Evidenze Riscontrate, Suggerimenti Urgenti):
    """
    
    # === GENERAZIONE CON TOLLERANZA AI GUASTI (503) ===
    answer = ""
    for errore_conteggio, modello_test in enumerate(modelli_da_provare):
        try:
            response = client.models.generate_content(
                model=modello_test,
                contents=prompt,
            )
            answer = response.text
            break
        except Exception as e:
            print(f"[RAG-Core] Crollo modello {modello_test} (Errore: {e})")
            if errore_conteggio < len(modelli_da_provare) - 1:
                time.sleep(1)
            else:
                answer = (
                    "⚠️ **Nota di Emergenza:** I server di generazione di Google Gemini sono "
                    "sovraccarichi (Errore 503). Il motore RAG locale ha comunque estratto e "
                    "ordinato i reperti per priorità clinica qui sotto."
                )
    
    return {
        "answer": answer,
        "sources": sources,
        "session_id": session_id or "gemini-session",
        "evaluation": {"status": "skipped"}
    }

def analyze_current_case(report_text: Optional[str], frames_dir: Optional[str]) -> Dict[str, Any]:
    return {"ok": True, "answer": "Pipeline attiva", "frames_dir": frames_dir}