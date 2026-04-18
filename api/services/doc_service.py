import os
import uuid
from pathlib import Path
from fastapi import UploadFile
import sys

# Ensure project root is on path to import scripts
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from scripts.dicom_to_frames_current import extract_frames

DATA_DIR = Path("data")
CURRENT_DICOM_DIR = DATA_DIR / "current" / "dicom"
CURRENT_FRAMES_DIR = DATA_DIR / "current" / "frames"

def _ensure_dirs():
    CURRENT_DICOM_DIR.mkdir(parents=True, exist_ok=True)
    CURRENT_FRAMES_DIR.mkdir(parents=True, exist_ok=True)

# Nuova funzione: importa tutti i DICOM da raw_data a current/dicom
import shutil
def import_all_rawdata_dicoms():
    """
    Copia tutti i file .dcm da data/raw_data (ricorsivamente) a data/current/dicom/
    Salta i file già presenti con lo stesso nome.
    """
    rawdata_root = Path("data/raw_data")
    _ensure_dirs()
    count = 0
    for p in rawdata_root.rglob("*.dcm"):
        dest = CURRENT_DICOM_DIR / p.name
        if not dest.exists():
            shutil.copy2(p, dest)
            count += 1
    return {"imported": count, "from": str(rawdata_root), "to": str(CURRENT_DICOM_DIR)}

async def save_current_dicom_and_extract_frames(file: UploadFile):
    """
    1) salva il DICOM in data/current/dicom/<id>.dcm
    2) genera frame in data/current/frames/<id>/frame_*.png usando il tuo script/func
    """
    _ensure_dirs()
    file_id = str(uuid.uuid4())
    dicom_path = CURRENT_DICOM_DIR / f"{file_id}.dcm"

    content = await file.read()
    dicom_path.write_bytes(content)

    # Estrarre frame dal DICOM appena caricato
    out_dir = CURRENT_FRAMES_DIR / file_id
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        frames = extract_frames(str(dicom_path), str(out_dir), n_frames=12)
    except Exception as e:
        # Se l'estrazione fallisce, restituisce comunque i path base
        frames = []
        print(f"[doc_service] Frame extraction failed: {e}")

    return {
        "file_id": file_id,
        "dicom_path": str(dicom_path),
        "frames_dir": str(out_dir),
        "frames": frames,
        "note": "Frames extracted via scripts/dicom_to_frames_current.extract_frames"
    }

def list_current_files():
    _ensure_dirs()
    files = []
    for p in CURRENT_DICOM_DIR.glob("*.dcm"):
        files.append({"file_id": p.stem, "name": p.name, "path": str(p)})
    return {"files": files, "count": len(files)}

def delete_current_file(file_id: str = None):
    _ensure_dirs()
    if not file_id:
        return {"ok": False, "error": "file_id required"}
    
    dicom_path = CURRENT_DICOM_DIR / f"{file_id}.dcm"
    frames_dir = CURRENT_FRAMES_DIR / file_id

    if dicom_path.exists():
        dicom_path.unlink()

    if frames_dir.exists() and frames_dir.is_dir():
        for child in frames_dir.glob("*"):
            child.unlink()
        frames_dir.rmdir()

    return {"ok": True, "deleted": file_id}
