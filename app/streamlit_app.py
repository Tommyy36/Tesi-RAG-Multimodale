"""
Interfaccia Grafica Streamlit Evoluta - Tesi Thomas
Dashboard di Controllo e Ricerca Cross-Modale (ECG, TAC, Unity, Linee Guida)
"""
import os
import requests
import streamlit as st
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()
backend_host = os.getenv("BACKEND_HOST", "localhost")
BASE_URL = f"http://{backend_host}:8000"

# Configurazione della pagina in modalità Wide (schermo intero)
st.set_page_config(page_title="RAG Multimodale - Tesi Thomas", layout="wide")

# Sidebar di navigazione
with st.sidebar:
    st.image("https://img.icons8.com/fluent/100/000000/cardiovascular.png", width=70)
    st.title("Framework Core")
    st.subheader("Tesi Thomas")
    st.markdown("---")
    
    scelta_pagina = st.radio(
        "Seleziona la Dashboard:",
        ["🔍 Retrieval Cross-Modale", "🔬 Analisi Caso DICOM (Giorgio)", "📋 Gestione Database"]
    )
    st.markdown("---")
    st.caption("Backend Core: FastAPI (Port 8000)")
    st.caption("Vectorstore: Qdrant (In-Memory)")
    st.caption("Embedding Engine: Gemini v1")

# =====================================================================
# PAGINA 1: IL TUO MOTORE DI RICERCA CROSS-MODALE (OTTIMIZZATO)
# =====================================================================
if scelta_pagina == "🔍 Retrieval Cross-Modale":
    st.title("🩺 Dashboard di Consultazione Medica Cross-Modale")
    st.subheader("Allineamento Semantico nello Spazio Vettoriale di Segnali Elettrici, Radiologici e Simulazioni 3D")
    st.info(
        "Questa sezione dimostra la novità della tesi: interrogare un database unico in linguaggio naturale "
        "per recuperare istantaneamente ECG, TAC (estratte da DICOM) o simulazioni di Keypoints da Unity."
    )
    st.divider()

    # Input di ricerca principale
    query_medico = st.text_input(
        "✍️ Digita i sintomi, il sospetto diagnostico o il piano ecografico da cercare:",
        placeholder="Es: Paziente con forte dolore al petto, sospetto infarto acuto in corso..."
    )

    # Griglia di configurazione filtri
    col_filtri, col_num = st.columns([3, 1])
    with col_filtri:
        modalita = st.multiselect(
            "Filtra sorgenti diagnostiche:",
            options=["ECG", "CT", "Unity_Simulation"],
            default=["ECG", "CT", "Unity_Simulation"]
        )
    with col_num:
        top_k = st.slider("Numero max risultati:", min_value=1, max_value=5, value=2)

    if query_medico.strip():
        with st.spinner("Invio richiesta al server FastAPI e generazione analisi..."):
            payload_richiesta = {
                "question": query_medico,
                "model": "gemini",
                "rag_type": "hybrid",
                "evaluate": False
            }
            
            try:
                # Bussiamo alla porta del backend
                r = requests.post(f"{BASE_URL}/chat", json=payload_richiesta, timeout=60)
                
                if r.status_code == 200:
                    data = r.json()
                    risposta_clinica = data.get("answer", "")
                    sources = data.get("sources", [])
                    
                    # 1. Mostriamo subito l'analisi strutturata generata da Gemini
                    st.subheader("📊 Analisi Clinica Generata")
                    st.markdown(risposta_clinica)
                    st.divider()
                    
                    # 2. Mostriamo i documenti e le immagini recuperate dal database vettoriale
                    st.subheader("📁 Reperti Estratti dallo Spazio Vettoriale")
                    tab_esami, tab_guide = st.tabs(["🖼️ Esami Diagnostici", "📚 Letteratura Scientifica"])
                    
                    with tab_esami:
                        # Filtriamo i casi clinici (cases)
                        casi = [s for s in sources if s.get("type") == "cases" and s.get("metadata", {}).get("modality") in modalita][:top_k]
                        if casi:
                            for i, source in enumerate(casi):
                                p = source.get("metadata", {})
                                score = source.get("score", 0.0)
                                
                                with st.container(border=True):
                                    col_txt, col_view = st.columns([3, 2])
                                    with col_txt:
                                        st.markdown(f"### Match #{i+1} - {p.get('label')}")
                                        st.markdown(f"**Affinità Vettoriale:** `{score:.4f}`")
                                        st.write(f"**Modalità:** {p.get('modality')} | **ID:** `{p.get('case_id')}`")
                                        st.info(f"**Descrizione Diagnostica:** {p.get('text')}")
                                    
                                    with col_view:
                                        img_p = p.get("image_path")
                                        if img_p:
                                            # 1. Trova dinamicamente la root del progetto
                                            ROOT_DIR = Path(__file__).resolve().parent.parent
                                            percorso_immagine = ROOT_DIR / img_p
                                            
                                            # 2. Fallback universale (Thomas Fix ricorsivo per MI/Infarction invertiti)
                                            if not percorso_immagine.exists():
                                                nome_file = Path(img_p).name
                                                base_data_dir = ROOT_DIR / "data"
                                                match_trovati = list(base_data_dir.rglob(nome_file))
                                                if match_trovati:
                                                    percorso_immagine = match_trovati[0]
                                            
                                            # 3. Visualizzazione finale
                                            if percorso_immagine.exists():
                                                st.image(str(percorso_immagine), caption=f"Reperto {p.get('modality')}", use_container_width=True)
                                            else:
                                                st.warning("⚠️ Immagine non trovata nelle cartelle locali.")
                                                st.caption(f"Mancante: `{Path(img_p).name}`")
                                        else:
                                            st.warning("Path immagine non definito nel payload vettoriale.")
                        else:
                            st.info("Nessun esame corrispondente trovato per questa query.")
                                        
                    with tab_guide:
                        # Filtriamo le linee guida (guidelines)
                        guide = [s for s in sources if s.get("type") == "guidelines"][:top_k]
                        if guide:
                            for j, source in enumerate(guide):
                                p = source.get("metadata", {})
                                score = source.get("score", 0.0)
                                with st.expander(f"📖 Estratto Linea Guida #{j+1} (Score: {score:.4f}) - Fonte: {p.get('source')}"):
                                    st.markdown(p.get("text"))
                        else:
                            st.info("Nessuna linea guida rilevante estratta.")
                else:
                    st.error(f"❌ Il server backend ha risposto con un errore: {r.text}")
            except Exception as e:
                st.error(f"❌ Impossibile comunicare con il backend FastAPI: {e}")

# =====================================================================
# PAGINA 2: L'INTERFACCIA ORIGINALE DI GIORGIO (PRESERVATA PER LA TESI)
# =====================================================================
elif scelta_pagina == "🔬 Analisi Caso DICOM (Giorgio)":
    st.title("🔬 Analisi Monomodale Ecocardiografica")
    st.subheader("Infrastruttura di lettura ed estrazione frame da file DICOM")
    st.divider()
    
    st.info("Carica un file DICOM (.dcm) singolo per effettuarne l'analisi visiva tramite i servizi FastAPI.")
    dicom_analyze = st.file_uploader("Seleziona il file DICOM", type=["dcm"], key="analyze_dicom")
    report_text = st.text_area("Note Cliniche opzionali", placeholder="Inserisci note...", height=100)
    
    if st.button("🔍 Avvia Analisi Pipeline", type="primary") and dicom_analyze is not None:
        with st.spinner("Elaborazione del file in corso..."):
            files = {"file": (dicom_analyze.name, dicom_analyze.getvalue(), "application/dicom")}
            data = {"report_text": report_text} if report_text.strip() else {}
            try:
                r = requests.post(f"{BASE_URL}/analyze-case", files=files, data=data, timeout=300)
                if r.status_code == 200:
                    result = r.json()
                    st.success("✅ Analisi completata dal Server!")
                    st.json(result)
                else:
                    st.error(f"Errore del server backend: {r.text}")
            except Exception as e:
                st.error(f"Eccezione: {e}")

# =====================================================================
# PAGINA 3: STRUMENTI DI MANUTENZIONE
# =====================================================================
elif scelta_pagina == "📋 Gestione Database":
    st.title("📋 Amministrazione e Monitoraggio Cluster")
    st.subheader("Stato dei nodi Qdrant e file temporanei")
    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🧹 Svuota Collezioni Vettoriali")
        if st.button("🔄 Soft Reset Qdrant"):
            with st.spinner("Resetting..."):
                try:
                    rr = requests.post(f"{BASE_URL}/flush-rag", timeout=60)
                    if rr.status_code == 200:
                        st.success("✅ Collezioni Qdrant ripulite e reinizializzate!")
                    else:
                        st.error(f"Errore: {rr.text}")
                except Exception as e:
                    st.error(f"Connessione fallita: {e}")
                    
    with col2:
        st.markdown("### 📁 File Attivi nel Sistema")
        if st.button("🔄 Mostra Lista File"):
            try:
                r = requests.get(f"{BASE_URL}/list-docs", params={"rag_type": "hybrid"}, timeout=60)
                if r.status_code == 200:
                    st.json(r.json())
                else:
                    st.error(f"Errore: {r.text}")
            except Exception as e:
                st.error(f"Connessione fallita: {e}")