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
        ds = pydicom.dcmread(dicom_path) [cite: 370]
        ds.PatientName = "ANON^PAZIENTE" [cite: 382]
        ds.PatientID = "000-000-000"
        ds.PatientBirthDate = "00000101"
        ds.save_as(dicom_path) [cite: 372, 385]
        return True
    except Exception as e:
        print(f"[doc_service] Anonimizzazione fallita: {e}")
        return False

def import_all_rawdata_dicoms():
    """
    Copia e prepara tutti i DICOM grezzi per l'elaborazione.
    """
    rawdata_root = Path("data/raw_data")
    _ensure_dirs()
    count = 0
    for p in rawdata_root.rglob("*.dcm"):
        dest = CURRENT_DICOM_DIR / p.name
        if not dest.exists():
            shutil.copy2(p, dest)
            # Ogni file importato viene subito anonimizzato per sicurezza
            anonimize_dicom(dest) [cite: 320]
            count += 1
    return {"imported": count, "from": str(rawdata_root), "to": str(CURRENT_DICOM_DIR)}

async def save_current_dicom_and_extract_frames(file: UploadFile) -> Dict[str, Any]:
    """
    Pipeline Multimodale:
    1) Salvataggio e Anonimizzazione
    2) Estrazione frame (Comprensione Visiva) [cite: 353]
    """
    _ensure_dirs()
    file_id = str(uuid.uuid4())
    dicom_path = CURRENT_DICOM_DIR / f"{file_id}.dcm"

    # Salvataggio fisico
    content = await file.read()
    dicom_path.write_bytes(content)

    # 1. Anonimizzazione immediata (Requisito di Tesi) [cite: 631, 656]
    anonimize_dicom(dicom_path)

    # 2. Estrazione Frame (Il "cuore" della visione multimodale)
    out_dir = CURRENT_FRAMES_DIR / file_id
    out_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Estraiamo 12 frame rappresentativi per dare a Gemini una visione completa [cite: 353]
        frames = extract_frames(str(dicom_path), str(out_dir), n_frames=12)
    except Exception as e:
        frames = []
        print(f"[doc_service] Errore estrazione frame: {e}")

    return {
        "file_id": file_id,
        "dicom_path": str(dicom_path),
        "frames_dir": str(out_dir),
        "frames": frames,
        "status": "Dati pronti per RAG Multimodale"
    }

def list_current_files():
    """Lista i file DICOM pronti per l'analisi."""
    _ensure_dirs()
    files = []
    for p in CURRENT_DICOM_DIR.glob("*.dcm"):
        files.append({"file_id": p.stem, "name": p.name, "path": str(p)})
    return {"files": files, "count": len(files)}

def delete_current_file(file_id: str = None):
    """Rimuove un caso clinico e tutti i relativi frame estratti."""
    _ensure_dirs()
    if not file_id:
        return {"ok": False, "error": "file_id richiesto"}
    
    dicom_path = CURRENT_DICOM_DIR / f"{file_id}.dcm"
    frames_dir = CURRENT_FRAMES_DIR / file_id

    if dicom_path.exists():
        dicom_path.unlink()

    if frames_dir.exists() and frames_dir.is_dir():
        for child in frames_dir.glob("*"):
            child.unlink()
        frames_dir.rmdir()

    return {"ok": True, "deleted": file_id}