"""Asset Companion - Image processing pipeline for game assets."""
from asset_companion.pipeline import process_one, SuperRes
from asset_companion.detect import Kind, detect_kind
from asset_companion.io import load_image_rgba, save_image_with_icc
from asset_companion.realesrgan import check_realesrgan_available, run_realesrgan

__version__ = "0.1.0"
__all__ = [
    "process_one",
    "SuperRes",
    "Kind",
    "detect_kind",
    "load_image_rgba",
    "save_image_with_icc",
    "check_realesrgan_available",
    "run_realesrgan",
]

