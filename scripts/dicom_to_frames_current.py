import os
import argparse
import numpy as np
import pydicom
from pydicom.pixel_data_handlers.util import convert_color_space
from PIL import Image


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def uniform_indices(num_frames: int, n: int):
    """Return n indices uniformly spaced in [0, num_frames-1]."""
    if num_frames <= 0:
        return []
    if n <= 0:
        return []
    if num_frames <= n:
        return list(range(num_frames))
    return np.linspace(0, num_frames - 1, n, dtype=int).tolist()


def to_rgb_if_needed(ds, frame):
    """Convert DICOM color space to RGB when needed (common in US: YBR_FULL_422)...."""
    photometric = getattr(ds, "PhotometricInterpretation", None)
    # Many ultrasound cine loops are already RGB or YBR_FULL_422
    if photometric == "YBR_FULL_422" and frame.ndim == 3 and frame.shape[-1] == 3:
        try:
            return convert_color_space(frame, "YBR_FULL_422", "RGB")
        except Exception:
            return frame
    return frame


def save_frame(frame, out_path: str):
    """Save numpy frame to PNG (handles grayscale and RGB)."""
    # If grayscale, ensure uint8
    if frame.ndim == 2:
        if frame.dtype != np.uint8:
            frame = np.clip(frame, 0, 255).astype(np.uint8)
        img = Image.fromarray(frame, mode="L")
    else:
        # RGB expected
        if frame.dtype != np.uint8:
            frame = np.clip(frame, 0, 255).astype(np.uint8)
        img = Image.fromarray(frame, mode="RGB")
    img.save(out_path)


def extract_frames(dicom_path: str, out_dir: str, n_frames: int = 12):
    ds = pydicom.dcmread(dicom_path)
    arr = ds.pixel_array  # triggers decompression if needed

    # Determine frames
    num_frames = int(getattr(ds, "NumberOfFrames", 1))
    if num_frames <= 1:
        # single frame case
        idxs = [0]
    else:
        idxs = uniform_indices(num_frames, n_frames)

    ensure_dir(out_dir)

    saved_paths = []
    for out_i, idx in enumerate(idxs, start=1):
        frame = arr[idx] if arr.ndim >= 3 else arr  # multiframe vs single
        frame = to_rgb_if_needed(ds, frame)
        out_path = os.path.join(out_dir, f"frame_{out_i:02d}.png")
        save_frame(frame, out_path)
        saved_paths.append(out_path)

    # Print a tiny summary (useful for debugging)
    view = getattr(ds, "ViewName", None)
    stage = getattr(ds, "StageName", None)
    fps = getattr(ds, "CineRate", getattr(ds, "RecommendedDisplayFrameRate", None))
    print("DICOM:", dicom_path)
    print("Frames in DICOM:", num_frames, "| Saved:", len(saved_paths))
    print("View:", view, "| Stage:", stage, "| FPS:", fps)
    print("Output folder:", out_dir)

    return saved_paths


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dicom", required=True, help="Path to input DICOM (.dcm)")
    ap.add_argument("--out", default=None, help="Output folder for sampled frames")
    ap.add_argument("--n", type=int, default=12, help="Number of frames to sample (default 12)")
    args = ap.parse_args()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    default_out = os.path.abspath(os.path.join(base_dir, "..", "data", "current_case_frames"))
    out_dir = args.out if args.out else default_out

    extract_frames(args.dicom, out_dir, n_frames=args.n)
