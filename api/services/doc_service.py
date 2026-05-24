"""
services/doc_service.py - Tesi Thomas
Infrastruttura di Gestione Documentale e Pipeline di Estrazione Multimodale
Gestisce nativamente file DICOM ospedalieri e formati grafici standard (PNG/JPG).
"""
import os
import uuid
import shutil
import sys
from pathlib import Path
from typing import Dict, Any, List
from fastapi import UploadFile
import pydicom  # Fondamentale per la tesi clinica

# Aggiunge il root del progetto al path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from scripts.dicom_to_frames_current import extract_frames

# --- PATHS DI SISTEMA ---
DATA_DIR = Path("data")
CURRENT_DICOM_DIR = DATA_DIR / "current" / "dicom"
CURRENT_FRAMES_DIR = DATA_DIR / "current" / "frames"

def _ensure_dirs():
    """Garantisce l'esistenza delle cartelle necessarie per la gestione dati."""
    CURRENT_DICOM_DIR.mkdir(parents=True, exist_ok=True)
    CURRENT_FRAMES_DIR.mkdir(parents=True, exist_ok=True)

def anonimize_dicom(dicom_path: Path):
    """
    LOGICA DI TESI: Anonimizzazione PHI (Protected Health Information).
    Rimuove i dati sensibili prima dell'analisi per conformità GDPR/clinica.
    """
    try:
        ds = pydicom.dcmread(dicom_path)
        ds.PatientName = "ANON^PAZIENTE"
        ds.PatientID = "000-000-000"
        ds.PatientBirthDate = "00000101"
        ds.save_as(dicom_path)
        return True
    except Exception as e:
        print(f"[doc_service] Anonimizzazione fallita o file non DICOM: {e}")
        return False

async def save_current_dicom_and_extract_frames(file: UploadFile) -> Dict[str, Any]:
    """
    Pipeline Multimodale Agnostica (Thomas Russo):
    Rileva il formato (DICOM o Immagine standard) e prepara i dati per il RAG.
    """
    _ensure_dirs()
    file_id = str(uuid.uuid4())
    estensione = Path(file.filename).suffix.lower()
    
    out_dir = CURRENT_FRAMES_DIR / file_id
    out_dir.mkdir(parents=True, exist_ok=True)
    
    content = await file.read()

    # CASO A: Il file è un'immagine standard (PNG, JPG, JPEG) come ECG o Unity Frame
    if estensione in ['.png', '.jpg', '.jpeg']:
        nome_frame = f"frame_01{estensione}"
        percorso_immagine_diretta = out_dir / nome_frame
        percorso_immagine_diretta.write_bytes(content)
        
        # Simuliamo un percorso dicom virtuale per non rompere la retrocompatibilità del dizionario
        virtual_dicom = CURRENT_DICOM_DIR / f"{file_id}{estensione}"
        virtual_dicom.write_bytes(content)
        
        frames = [str(percorso_immagine_diretta)]
        print(f"[doc_service] Rilevato formato grafico standard. Salvato direttamente: {nome_frame}")

    # CASO B: Il file è un DICOM ospedaliero nativo
    else:
        dicom_path = CURRENT_DICOM_DIR / f"{file_id}.dcm"
        dicom_path.write_bytes(content)
        
        # Anonimizzazione obbligatoria
        anonimize_dicom(dicom_path)
        
        try:
            # Estraiamo i frame rappresentativi
            frames = extract_frames(str(dicom_path), str(out_dir), n_frames=12)
        except Exception as e:
            frames = []
            print(f"[doc_service] Errore estrazione frame da DICOM: {e}")
            
        virtual_dicom = dicom_path

    return {
        "file_id": file_id,
        "dicom_path": str(virtual_dicom),
        "frames_dir": str(out_dir),
        "frames": frames,
        "status": "Dati pronti per RAG Multimodale"
    }

def list_current_files():
    """Lista i file clinici pronti per l'analisi (estensioni multiple)."""
    _ensure_dirs()
    files = []
    for p in CURRENT_DICOM_DIR.iterdir():
        if p.is_file() and p.suffix.lower() in ['.dcm', '.png', '.jpg', '.jpeg']:
            files.append({"file_id": p.stem, "name": p.name, "path": str(p)})
    return {"files": files, "count": len(files)}

def delete_current_file(file_id: str = None):
    """Rimuove un caso clinico e tutti i relativi frame estratti."""
    _ensure_dirs()
    if not file_id:
        return {"ok": False, "error": "file_id richiesto"}
    
    frames_dir = CURRENT_FRAMES_DIR / file_id

    # Rimuove l'estensione corrispondente nella cartella dicom
    for p in CURRENT_DICOM_DIR.glob(f"{file_id}.*"):
        p.unlink()

    if frames_dir.exists() and frames_dir.is_dir():
        for child in frames_dir.glob("*"):
            child.unlink()
        frames_dir.rmdir()

    return {"ok": True, "deleted": file_id}