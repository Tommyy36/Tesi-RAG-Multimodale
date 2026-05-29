"""
Interfaccia Grafica Streamlit Evoluta - Tesi Thomas
Dashboard di Controllo e Ricerca Cross-Modale (ECG, TAC, Unity, Linee Guida)
Versione REFACTORING: Visualizzazione Grafica Avanzata della Pipeline Multimodale
"""
import os
import requests
import streamlit as st
from dotenv import load_dotenv
from pathlib import Path
import re

load_dotenv()
backend_host = os.getenv("BACKEND_HOST", "localhost")
BASE_URL = f"http://{backend_host}:8000"

# Configurazione della pagina in modalità Wide
st.set_page_config(page_title="RAG Multimodale - Tesi Thomas", layout="wide")

# Sidebar di navigazione
with st.sidebar:
    
    st.markdown("### **Multimodal RAG Framework**")
    st.markdown("<p style='font-size: 13px; margin-top: -15px; color: #777777;'>Supporto Decisionale Clinico in Cardiologia</p>", unsafe_allow_html=True)
    st.divider()
    
    scelta_pagina = st.radio(
        "Seleziona la Dashboard:",
        ["Retrieval Cross-Modale", "Analisi Caso Clinico Corrente", "Amministrazione Database RAG"]
    )
    st.divider()

# =====================================================================
# PAGINA 1: MOTORE DI RICERCA CROSS-MODALE
# =====================================================================
if scelta_pagina == "Retrieval Cross-Modale":
    st.title("Dashboard di Consultazione Medica Cross-Modale")
    st.subheader("Allineamento Semantico nello Spazio Vettoriale di Segnali Elettrici, Radiologici e Simulazioni 3D")
    st.info(
        "Questa sezione dimostra la novità della tesi: interrogare un database unico in linguaggio naturale "
        "per recuperare istantaneamente ECG, TAC (estratte da DICOM) o simulazioni di Keypoints da Unity."
    )
    st.divider()

    # Creazione del Form per bloccare l'esecuzione automatica al tasto "Invio"
    with st.form("form_ricerca_rag"):
        # Input di ricerca principale
        query_medico = st.text_input(
            "Digita i sintomi, il sospetto diagnostico o il piano ecografico da cercare:",
            placeholder="Es: Sospetto infarto acuto in corso, forte dolore retrosternale..."
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
            top_k = st.slider("Numero max risultati:", min_value=1, max_value=5, value=5)
            
        st.markdown("<br>", unsafe_allow_html=True)
        # Pulsante unico di invio modulo
        bottone_invia = st.form_submit_button("Avvia Ricerca Clinica", type="primary", use_container_width=True)

    # La ricerca parte solo se l'utente clicca fisicamente sul pulsante ed ha inserito del testo
    if bottone_invia and query_medico.strip():
        with st.spinner("Invio richiesta al server e generazione analisi..."):
            payload_richiesta = {
                "question": query_medico,
                "model": "gemini",
                "rag_type": "hybrid",
                "evaluate": False
            }
            
            try:
                r = requests.post(f"{BASE_URL}/chat", json=payload_richiesta, timeout=60)
                
                if r.status_code == 200:
                    data = r.json()
                    risposta_clinica = data.get("answer", "")
                    sources = data.get("sources", [])
                    
                    st.subheader("Analisi Clinica Generata")
                    st.markdown(risposta_clinica)
                    st.divider()
                    
                    st.subheader("Reperti Estratti dallo Spazio Vettoriale")
                    tab_esami, tab_guide = st.tabs(["Esami Diagnostici", "Letteratura Scientifica"])
                    
                    with tab_esami:
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
                                            ROOT_DIR = Path(__file__).resolve().parent.parent
                                            percorso_immagine = ROOT_DIR / img_p
                                            nome_file_oriz = Path(img_p).name
                                            
                                            # STRATEGIA DI RECOVERY INTELLIGENTE
                                            if not percorso_immagine.exists():
                                                base_data_dir = ROOT_DIR / "data"
                                                match_trovati = list(base_data_dir.rglob(nome_file_oriz))
                                                if match_trovati:
                                                    percorso_immagine = match_trovati[0]
                                                else:
                                                    numeri_finali = re.findall(r'\d+', nome_file_oriz)
                                                    if numeri_finali:
                                                        ultimo_num = numeri_finali[-1]
                                                        for file_glob in base_data_dir.rglob(f"*{ultimo_num}*"):
                                                            if file_glob.suffix.lower() in ['.png', '.jpg', '.jpeg']:
                                                                percorso_immagine = file_glob
                                                                break
                                                                
                                                    if not percorso_immagine.exists() and p.get('modality') == 'CT':
                                                        for file_tac in base_data_dir.rglob("*slice*"):
                                                            percorso_immagine = file_tac
                                                            break
                                            
                                            if percorso_immagine.exists():
                                                st.image(str(percorso_immagine), caption=f"Reperto Allineato {p.get('modality')} (Risolto via Smart-Match)", use_container_width=True)
                                            else:
                                                st.warning("⚠️ Immagine non trovata nelle cartelle locali.")
                                                st.caption(f"Mancante originale: `{nome_file_oriz}`")
                                        else:
                                            st.warning("Path immagine non definito nel payload vettoriale.")
                        else:
                            st.info("Nessun esame corrispondente trovato per questa query.")
                                        
                    with tab_guide:
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
                
    elif bottone_invia and not query_medico.strip():
        st.warning("⚠️ Inserisci un testo nella barra di ricerca prima di premere Invia!")

# =====================================================================
# PAGINA 2: DIAGNOSTICA SPOT MULTIMODALE (INTERFACCIA OTTIMIZZATA)
# =====================================================================
elif scelta_pagina == "Analisi Caso Clinico Corrente":
    st.title("Diagnostica Integrata sul Caso Clinico Corrente")
    st.subheader("Analisi Multimodale Spot: Correlazione Immediata tra Reperto Grafico e Note del Triage")
    st.divider()
    
    st.info(
        "Carica un file diagnostico relativo al paziente attualmente in esame. Il sistema accetta file nativi DICOM (.dcm) "
        "della rete ospedaliera o esportazioni grafiche standard (PNG, JPG, JPEG) di ECG, TAC o frame del Simulatore Unity."
    )
    
    # Estensione dell'uploader a file DICOM + immagini standard
    file_clinico = st.file_uploader(
        "Seleziona il Reperto Diagnostico (DICOM, TAC, ECG o Frame Unity):", 
        type=["dcm", "png", "jpg", "jpeg"], 
        key="analyze_clinical_file"
    )
    
    report_text = st.text_area("Sintomi rilevati e Note Cliniche del Triage:", placeholder="Inserisci note sul paziente o sospetti...", height=120)
    
    if st.button("Avvia Pipeline di Analisi Concorsuale", type="primary") and file_clinico is not None:
        with st.spinner("Estrazione caratteristiche e interrogazione dello spazio vettoriale in corso..."):
            files = {"file": (file_clinico.name, file_clinico.getvalue(), "application/octet-stream")}
            data = {"report_text": report_text} if report_text.strip() else {}
            try:
                r = requests.post(f"{BASE_URL}/analyze-case", files=files, data=data, timeout=300)
                if r.status_code == 200:
                    result = r.json()
                    
                    # Notifica asincrona a scomparsa (UX pulita)
                    st.toast("Pipeline completata con successo!", icon="✅")
                    
                    # Estrazione e formattazione robusta del Report Medico di Gemini
                    analysis_data = result.get("analysis", {})
                    if isinstance(analysis_data, dict):
                        report_medico = analysis_data.get("answer", result.get("answer", "Nessun report generato."))
                    else:
                        report_medico = result.get("answer", "Nessun report generato.")
                        
                    # Dettagli identificativi minimali in linea (Niente blocchi grigi asettici)
                    f_id = result.get("file_id", "Analisi Spot Istantanea")
                    st.caption(f"**ID Unico Reperto:** `{f_id}` | ⚡ **Stato Core:** Elaborazione Multimodale Completata")
                    
                    # Il report clinico prende il palcoscenico principale con layout premium
                    with st.container(border=True):
                        st.markdown("## Report Diagnostico Integrato (Framework Core)")
                        st.markdown(report_medico)
                        
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    # Expander isolato per il tracciamento dei log di debug a fondo pagina
                    with st.expander("Dettagli Tecnici di Acquisizione (Log Interno)"):
                        st.write(f"**Directory dei frame estratti:** `{result.get('frames_dir', 'N/A')}`")
                        if "dicom_path" in result:
                            st.write(f"**File DICOM originale:** `{result.get('dicom_path')}`")
                        frames_estratti = result.get("frames", [])
                        st.write(f"**Frame letti dal file binario:** `{len(frames_estratti)}`")
                else:
                    st.error(f"Errore del server backend: {r.text}")
            except Exception as e:
                st.error(f"Eccezione durante la comunicazione con il backend: {e}")

# =====================================================================
# PAGINA 3: STRUMENTI DI AMMINISTRAZIONE DATABASE
# =====================================================================
elif scelta_pagina == "Amministrazione Database RAG":
    st.title("Amministrazione e Monitoraggio dell'Infrastruttura RAG")
    st.subheader("Stato dei nodi del Vector Store Qdrant e Gestione dei Documenti Indicizzati")
    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("Svuota Collezioni Vettoriali")
        st.caption("Esegue il flush e la reinizializzazione completa delle collezioni su Qdrant. Utile in fase di aggiornamento delle Linee Guida.")
        if st.button("Soft Reset Cluster Vettoriale", type="secondary", use_container_width=True):
            with st.spinner("Resetting..."):
                try:
                    rr = requests.post(f"{BASE_URL}/flush-rag", timeout=60)
                    if rr.status_code == 200:
                        st.success("Collezioni Qdrant ripulite e reinizializzate!")
                    else:
                        st.error(f"Errore: {rr.text}")
                except Exception as e:
                    st.error(f"Connessione fallita: {e}")
                    
    with col2:
        st.markdown("Documenti Attivi nel Sistema")
        st.caption("Visualizza l'elenco dei file di testo, linee guida o cartelle cliniche attualmente indicizzati nell'indice ibrido.")
        if st.button("Mostra Lista File Indicizzati", type="secondary", use_container_width=True):
            with st.spinner("Recupero documenti..."):
                try:
                    r = requests.get(f"{BASE_URL}/list-docs", params={"rag_type": "hybrid"}, timeout=60)
                    if r.status_code == 200:
                        st.json(r.json())
                    else:
                        st.error(f"Errore: {r.text}")
                except Exception as e:
                    st.error(f"Connessione fallita: {e}")