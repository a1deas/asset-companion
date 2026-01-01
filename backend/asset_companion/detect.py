"""Image type detection and bounding box operations."""
import enum
from typing import Optional, Tuple
import numpy as np
import cv2
from PIL import Image


class Kind(str, enum.Enum):
    """Image type classification."""
    auto = "auto"
    pixel_art = "pixel_art"
    illustration = "illustration"


def detect_kind(
    pil_img: Image.Image, 
    pixel_color_threshold: int = 80, 
    edge_threshold: float = 0.12
) -> Kind:
    """
    Detect if image is pixel art or illustration.
    
    Uses color count and edge detection heuristics.
    
    Args:
        pil_img: Input PIL Image
        pixel_color_threshold: Max unique colors for pixel art
        edge_threshold: Minimum edge ratio for pixel art
        
    Returns:
        Detected Kind
    """
    arr = np.array(pil_img.convert("RGB"))
    h, w, _ = arr.shape
    small = cv2.resize(
        arr, 
        (min(128, w), min(128, h)), 
        interpolation=cv2.INTER_AREA
    )
    
    # Estimate unique color count on downscaled image
    uniq = np.unique(small.reshape(-1, 3), axis=0)
    few_colors = len(uniq) < pixel_color_threshold
    
    # Detect sharp edge ratio using Canny
    gray = cv2.cvtColor(small, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 80, 140)
    edge_ratio = float((edges > 0).mean())
    
    if few_colors and edge_ratio > edge_threshold:
        return Kind.pixel_art
    return Kind.illustration


def bbox_from_alpha(
    pil_img: Image.Image, 
    alpha_threshold: int = 5
) -> Optional[Tuple[int, int, int, int]]:
    """
    Extract bounding box from alpha channel.
    
    Args:
        pil_img: Input PIL Image (must be RGBA)
        alpha_threshold: Minimum alpha value to consider opaque
        
    Returns:
        Bounding box (x0, y0, x1, y1) or None if no alpha
    """
    if pil_img.mode != "RGBA":
        return None
    a = np.array(pil_img.split()[-1])
    mask = a > alpha_threshold
    ys, xs = np.where(mask)
    if len(xs) == 0 or len(ys) == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def is_alpha_bbox_meaningful(
    pil_img: Image.Image,
    bbox: Tuple[int, int, int, int],
    min_trim_ratio: float = 0.05
) -> bool:
    """
    Check if alpha-based bbox trimming is meaningful (not too aggressive).
    
    Only trim if it removes a significant amount of transparent padding.
    This prevents aggressive cropping of assets with minimal transparency.
    
    Args:
        pil_img: Input PIL Image
        bbox: Bounding box (x0, y0, x1, y1)
        min_trim_ratio: Minimum ratio of area to trim (default 5%)
        
    Returns:
        True if trimming is meaningful, False otherwise
    """
    x0, y0, x1, y1 = bbox
    img_w, img_h = pil_img.size
    
    # Calculate area reduction
    original_area = img_w * img_h
    bbox_area = (x1 - x0 + 1) * (y1 - y0 + 1)
    trim_ratio = 1.0 - (bbox_area / original_area)
    
    # Also check if bbox is significantly smaller (not just edge trimming)
    width_ratio = (x1 - x0 + 1) / img_w
    height_ratio = (y1 - y0 + 1) / img_h
    
    # Only trim if we're removing meaningful transparent padding
    # (at least min_trim_ratio of area, or significant edge padding)
    return trim_ratio >= min_trim_ratio or width_ratio < 0.95 or height_ratio < 0.95


def bbox_from_saliency(pil_img: Image.Image) -> Tuple[int, int, int, int]:
    """
    Extract bounding box from saliency map.
    
    Args:
        pil_img: Input PIL Image
        
    Returns:
        Bounding box (x0, y0, x1, y1)
    """
    arr = np.array(pil_img.convert("RGB"))
    # Resize for fast estimation
    h, w, _ = arr.shape
    scale = 256.0 / max(h, w)
    new_w = max(1, int(w * scale))
    new_h = max(1, int(h * scale))
    small = cv2.resize(arr, (new_w, new_h), interpolation=cv2.INTER_AREA)
    
    # Check if saliency module is available (requires opencv-contrib-python)
    if not hasattr(cv2, 'saliency'):
        # Saliency module not available - fallback to full image
        return 0, 0, w - 1, h - 1
    
    try:
        sal = cv2.saliency.StaticSaliencySpectralResidual_create()  # type: ignore[attr-defined]
        success, sal_map = sal.computeSaliency(small)
        
        if not success:
            # Fallback to full image
            return 0, 0, w - 1, h - 1
        
        sal_bin = (sal_map * 255).astype(np.uint8)
        _, th = cv2.threshold(sal_bin, 0, 255, cv2.THRESH_OTSU)
        cnts, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not cnts:
            return 0, 0, w - 1, h - 1
        
        # Take largest contour
        c = max(cnts, key=cv2.contourArea)
        x, y, ww, hh = cv2.boundingRect(c)
        
        # Scale bbox to original coordinates
        inv = 1.0 / scale
        x0 = int(x * inv)
        y0 = int(y * inv)
        x1 = min(w - 1, int((x + ww) * inv))
        y1 = min(h - 1, int((y + hh) * inv))
        
        # Small safety margin
        m = int(0.01 * max(w, h))
        return (
            max(0, x0 - m), 
            max(0, y0 - m), 
            min(w - 1, x1 + m), 
            min(h - 1, y1 + m)
        )
    except (AttributeError, cv2.error):
        # Saliency module not available or failed - fallback to full image
        return 0, 0, w - 1, h - 1


def crop_to_bbox(
    pil_img: Image.Image, 
    bbox: Tuple[int, int, int, int], 
    margin: int = 0
) -> Image.Image:
    """
    Crop image to bounding box with optional margin.
    
    Args:
        pil_img: Input PIL Image
        bbox: Bounding box (x0, y0, x1, y1)
        margin: Additional margin pixels
        
    Returns:
        Cropped image
    """
    x0, y0, x1, y1 = bbox
    x0 = max(0, x0 - margin)
    y0 = max(0, y0 - margin)
    x1 = min(pil_img.width - 1, x1 + margin)
    y1 = min(pil_img.height - 1, y1 + margin)
    return pil_img.crop((x0, y0, x1 + 1, y1 + 1))
