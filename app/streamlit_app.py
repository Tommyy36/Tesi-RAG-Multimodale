import os
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
backend_host = os.getenv("BACKEND_HOST", "localhost")
BASE_URL = f"http://{backend_host}:8000"

st.set_page_config(page_title="Multimodal RAG", layout="wide")

rag_type = "hybrid"  # Default RAG type

if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []

st.title("Multimodal RAG (DICOM)")

# Tab principale
tab1, tab2, tab3 = st.tabs(["🔬 Analyze Case", "📤 Upload DICOM", "📋 Manage Files"])

with tab1:
    st.header("Analyze Echocardiography Case")
    st.info("Upload a DICOM file with optional clinical report for multimodal RAG analysis.")
    
    dicom_analyze = st.file_uploader("Upload DICOM file", type=["dcm"], key="analyze_dicom")
    report_text = st.text_area(
        "Clinical Report (optional)", 
        placeholder="Enter clinical report or leave empty for generic analysis...",
        height=150
    )
    
    if st.button("🔍 Analyze Case", type="primary") and dicom_analyze is not None:
        with st.spinner("Analyzing case..."):
            files = {"file": (dicom_analyze.name, dicom_analyze.getvalue(), "application/dicom")}
            data = {"report_text": report_text} if report_text.strip() else {}
            
            try:
                r = requests.post(f"{BASE_URL}/analyze-case", files=files, data=data, timeout=300)
                if r.status_code == 200:
                    result = r.json()
                    st.success("✅ Analysis complete!")
                    
                    # Show file info
                    with st.expander("📁 File Info"):
                        st.json({
                            "filename": result.get("filename"),
                            "frames_extracted": result.get("num_frames"),
                            "frames_dir": result.get("frames_dir")
                        })
                    
                    # Show analysis result
                    analysis = result.get("analysis", {})
                    if analysis:
                        st.subheader("📊 Clinical Analysis")
                        st.markdown(analysis.get("answer", "No answer generated"))
                        
                        # Show sources
                        sources = analysis.get("sources", [])
                        if sources:
                            with st.expander(f"🔗 Sources ({len(sources)})"):
                                st.json(sources)
                        
                        # Show evaluation if present
                        evaluation = analysis.get("evaluation")
                        if evaluation:
                            with st.expander("📈 Evaluation"):
                                st.json(evaluation)
                else:
                    st.error(f"❌ Error: {r.text}")
            except Exception as e:
                st.error(f"❌ Exception: {str(e)}")

with tab2:
    st.header("Upload DICOM Only")
    st.info("Upload and store DICOM file without immediate analysis.")
    
    dicom_upload = st.file_uploader("Upload DICOM file", type=["dcm"], key="upload_dicom")
    if st.button("📤 Upload") and dicom_upload is not None:
        with st.spinner("Uploading..."):
            files = {"file": (dicom_upload.name, dicom_upload.getvalue(), "application/dicom")}
            try:
                r = requests.post(f"{BASE_URL}/upload-doc", files=files, timeout=300)
                if r.status_code == 200:
                    st.success("✅ File uploaded successfully!")
                    st.json(r.json())
                else:
                    st.error(f"❌ Error: {r.text}")
            except Exception as e:
                st.error(f"❌ Exception: {str(e)}")

with tab3:
    st.header("Manage Current Files")
    
    col_list, col_delete = st.columns(2)
    
    with col_list:
        st.subheader("📋 List Files")
        if st.button("🔄 Refresh File List"):
            try:
                r = requests.get(f"{BASE_URL}/list-docs", params={"rag_type": rag_type}, timeout=60)
                if r.status_code == 200:
                    files_list = r.json()
                    if files_list:
                        st.json(files_list)
                    else:
                        st.info("No files found")
                else:
                    st.error(f"Error: {r.text}")
            except Exception as e:
                st.error(f"Exception: {str(e)}")
    
    with col_delete:
        st.subheader("🗑️ Delete File")
        file_id_to_delete = st.text_input("File ID to delete")
        if st.button("Delete File") and file_id_to_delete:
            try:
                r = requests.post(f"{BASE_URL}/delete-doc", json={"file_id": file_id_to_delete}, timeout=60)
                if r.status_code == 200:
                    st.success("✅ File deleted!")
                    st.json(r.json())
                else:
                    st.error(f"Error: {r.text}")
            except Exception as e:
                st.error(f"Exception: {str(e)}")

st.divider()

# Actions at the bottom
col1, col2 = st.columns(2)
with col1:
    if st.button("🔄 Reset RAG Collections"):
        with st.spinner("Resetting..."):
            try:
                rr = requests.post(f"{BASE_URL}/flush-rag", timeout=60)
                if rr.status_code == 200:
                    st.success("✅ RAG collections reset!")
                    st.json(rr.json())
                else:
                    st.error(f"Error: {rr.text}")
            except Exception as e:
                st.error(f"Exception: {str(e)}")

with col2:
    if st.button("🗑️ Clear Session"):
        st.session_state.messages = []
        st.session_state.session_id = None
        st.rerun()