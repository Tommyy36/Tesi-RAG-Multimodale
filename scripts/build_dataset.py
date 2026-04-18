import os
import json
import csv
import re
import hashlib
import numpy as np
import pydicom
from pydicom.pixel_data_handlers.util import convert_color_space
from PIL import Image
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

RAW_ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", "data", "raw_data"))

OUT_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "data", "dataset_built"))
JSONL_PATH = os.path.join(OUT_DIR, "documents.jsonl")
LABELS_CSV = os.path.join(OUT_DIR, "labels.csv")
IMAGES_DIR = os.path.join(OUT_DIR, "images")

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)

print("RAW_ROOT:", RAW_ROOT)
print("OUT_DIR:", OUT_DIR)
print("\n[ANONYMIZATION] Removing sensitive patient data from DICOM metadata...\n")

# --- SENSITIVE DATA TO EXCLUDE (GDPR/HIPAA compliance) ---
# These DICOM tags contain patient-identifiable information
SENSITIVE_TAGS = [
    'PatientName', 'PatientID', 'PatientBirthDate', 'PatientAge', 'PatientSex',
    'StudyDate', 'StudyTime', 'SeriesDate', 'SeriesTime', 'AcquisitionDate', 'AcquisitionTime',
    'ContentDate', 'ContentTime', 'AccessionNumber', 'InstitutionName', 'InstitutionAddress',
    'ReferringPhysicianName', 'PerformingPhysicianName', 'OperatorsName',
    'StudyID', 'SeriesNumber', 'InstanceNumber', 'StudyInstanceUID', 'SeriesInstanceUID',
    'PatientComments', 'ImageComments', 'RequestingPhysician', 'RequestedProcedureDescription'
]

def anonymize_dicom_metadata(ds):
    """Remove all sensitive patient data from DICOM dataset."""
    for tag in SENSITIVE_TAGS:
        if hasattr(ds, tag):
            delattr(ds, tag)
    return ds

# --- mapping for clean label ---
LABEL_MAP = {
    "Normal": {
        "short": "normal",
        "pretty": "Normal",
        "group": "normal"
    },
    "Normal_with_septal_hypertrophy": {
        "short": "normal_sep_hyp",
        "pretty": "Normal with septal hypertrophy",
        "group": "pathology"
    },
    "dilated_cardiomyopathy_with_global_dysfunction": {
        "short": "dcm_global_dysf",
        "pretty": "Dilated cardiomyopathy with global dysfunction",
        "group": "pathology"
    },
    "inferoapical_septal_akinesia": {
        "short": "inferoapical_sep_ak",
        "pretty": "Inferoapical septal akinesia",
        "group": "pathology"
    }
}

def safe_get(ds, tag, default=None):
    return getattr(ds, tag, default)

def slugify(s: str) -> str:
    s = s.strip()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^A-Za-z0-9_]+", "", s)
    return s.lower()

def make_case_id(ds, fallback_path: str) -> str:
    sop_uid = safe_get(ds, "SOPInstanceUID", None)
    base = sop_uid if sop_uid else os.path.basename(fallback_path)
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:12]

def build_case_card(meta: dict) -> str:
    # neutral text: NO label/
    txt = (
        f"Ultrasound multiframe study. View: {meta.get('view','Unknown')}. "
        f"Stage: {meta.get('stage','Unknown')}. Frames: {meta.get('num_frames',1)}. "
    )
    if meta.get("fps"):
        txt += f"Frame rate: {meta['fps']} fps. "
    if meta.get("effective_duration") is not None:
        txt += f"Duration: {meta['effective_duration']} s. "
    if meta.get("heart_rate") is not None:
        txt += f"Heart rate (device): {meta['heart_rate']} bpm. "
    if meta.get("mean_intensity") is not None:
        txt += f" Mean intensity: {meta['mean_intensity']:.4f}."
    if meta.get("motion_energy") is not None:
        txt += f" Motion energy: {meta['motion_energy']:.4f}."
    if meta.get("motion_std") is not None:
        txt += f" Motion std: {meta['motion_std']:.4f}."

    txt += "Findings: not provided (metadata-only)."
    return txt

def export_representative_frames(ds, case_id: str, n=10):
    try:
        pixel_array = ds.pixel_array
        num_frames = int(safe_get(ds, "NumberOfFrames", 1))
        if num_frames <= 1:
            return []

        k = min(n, num_frames)
        idxs = np.linspace(0, num_frames - 1, k, dtype=int)

        case_img_dir = os.path.join(IMAGES_DIR, case_id)
        os.makedirs(case_img_dir, exist_ok=True)

        saved = []
        photometric = safe_get(ds, "PhotometricInterpretation", None)

        for idx in idxs:
            frame = pixel_array[idx]

            # color conversion if RGB
            if photometric == "YBR_FULL_422" and frame.ndim == 3 and frame.shape[-1] == 3:
                frame = convert_color_space(frame, "YBR_FULL_422", "RGB")

            img = Image.fromarray(frame)
            path = os.path.join(case_img_dir, f"frame_{idx+1}.png")
            img.save(path)
            saved.append({"frame_index": int(idx+1), "image_path": path})

        return saved
    except Exception:
        return []

def compute_simple_video_features(ds, max_frames=64):
    """
    Estrae feature semplici dal cine US:
    - mean_intensity: media intensità normalizzata
    - motion_energy: differenza media tra frame consecutivi
    - motion_std: deviazione standard del movimento
    """
    try:
        arr = ds.pixel_array  # shape: (frames, H, W) o (frames, H, W, 3)
        num_frames = int(safe_get(ds, "NumberOfFrames", 1))
        if num_frames <= 1:
            return {}

        # sottocampiona per velocità
        use_n = min(num_frames, max_frames)
        idxs = np.linspace(0, num_frames - 1, use_n, dtype=int)
        x = arr[idxs]

        # se colore -> converti a grayscale semplice (mean sui canali)
        if x.ndim == 4 and x.shape[-1] == 3:
            x = x.mean(axis=-1)

        x = x.astype(np.float32)

        # normalizza [0,1] se sembra 8-bit
        maxv = x.max()
        if maxv > 1.5:
            x = x / 255.0

        mean_intensity = float(x.mean())

        # movimento: differenza assoluta tra frame consecutivi
        diffs = np.abs(x[1:] - x[:-1])
        motion_per_step = diffs.mean(axis=(1, 2))  # (use_n-1,)
        motion_energy = float(motion_per_step.mean())
        motion_std = float(motion_per_step.std())

        return {
            "mean_intensity": mean_intensity,
            "motion_energy": motion_energy,
            "motion_std": motion_std,
            "feature_frames_used": int(use_n)
        }
    except Exception:
        return {}

# clean build
open(JSONL_PATH, "w", encoding="utf-8").close()
labels_rows = []

for label_folder in sorted(os.listdir(RAW_ROOT)):
    label_dir = os.path.join(RAW_ROOT, label_folder)
    if not os.path.isdir(label_dir):
        continue

    # if not in map, manage anyway
    lm = LABEL_MAP.get(label_folder, {
        "short": slugify(label_folder),
        "pretty": label_folder.replace("_", " "),
        "group": "unknown"
    })

    for fname in os.listdir(label_dir):
        if not fname.lower().endswith(".dcm"):
            continue

        fpath = os.path.join(label_dir, fname)
        ds = pydicom.dcmread(fpath)
        
        # ANONYMIZE: remove patient-identifiable data
        ds = anonymize_dicom_metadata(ds)

        case_id = make_case_id(ds, fpath)
        view = safe_get(ds, "ViewName", None) or safe_get(ds, "View", None) or safe_get(ds, "SeriesDescription",None) or "Unknown"
        stage = safe_get(ds, "StageName", None) or safe_get(ds, "ProtocolName", None) or "Unknown"



        meta = {
            "case_id": case_id,
            "anonymized": True,  # Flag indicating data has been anonymized

            "diagnosis_label_raw": label_folder,
            "diagnosis_label_short": lm["short"],
            "diagnosis_label_pretty": lm["pretty"],
            "diagnosis_group": lm["group"],

            "source_path": f"{label_folder}/{fname}",
            "modality": safe_get(ds, "Modality"),
            # sop_class_uid removed for anonymization
            "view": view,
            "stage": stage,
            "num_frames": int(safe_get(ds, "NumberOfFrames", 1)),
            "fps": safe_get(ds, "CineRate", safe_get(ds, "RecommendedDisplayFrameRate", None)),
            "effective_duration": safe_get(ds, "EffectiveDuration", None),
            "heart_rate": safe_get(ds, "HeartRate", None),
            "manufacturer": safe_get(ds, "Manufacturer", None),
            "model": safe_get(ds, "ManufacturerModelName", None),
            "rows": safe_get(ds, "Rows", None),
            "columns": safe_get(ds, "Columns", None),
            "photometric": safe_get(ds, "PhotometricInterpretation", None),
        }
        feat = compute_simple_video_features(ds)
        meta.update(feat)

        meta = {k: v for k, v in meta.items() if v is not None}

        # 1) index case-card (neutral)
        case_doc = {
            "content": build_case_card(meta),
            "metadata": {**meta, "document_type": "case_card"}
        }
        with open(JSONL_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(case_doc, ensure_ascii=False) + "\n")

        # 2) frames
        frames = export_representative_frames(ds, case_id, n=10)
        for fr in frames:
            fr_doc = {
                "content": f"Representative ultrasound frame from cine loop. View: {meta['view']}, Stage: {meta['stage']}.",
                "metadata": {**meta, **fr, "document_type": "frame"}
            }
            with open(JSONL_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(fr_doc, ensure_ascii=False) + "\n")

        # 3) labels.csv for validation/split
        labels_rows.append({
            "case_id": case_id,
            "label_raw": label_folder,
            "label_short": lm["short"],
            "label_pretty": lm["pretty"],
            "group": lm["group"],
            "file": f"{label_folder}/{fname}"
        })

with open(LABELS_CSV, "w", newline="", encoding="utf-8") as cf:
    w = csv.DictWriter(cf, fieldnames=["case_id", "label_raw", "label_short", "label_pretty", "group", "file"])
    w.writeheader()
    w.writerows(labels_rows)

print("Build complete!")
print("JSONL:", JSONL_PATH)
print("Labels:", LABELS_CSV)
print("Images dir:", IMAGES_DIR)
