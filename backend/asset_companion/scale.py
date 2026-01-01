"""Image scaling operations."""
from typing import Tuple
from PIL import Image
from PIL.Image import Resampling

# Resampling constants
LANCZOS = Resampling.LANCZOS
NEAREST = Resampling.NEAREST


def choose_integer_scale(src_wh: Tuple[int, int], target: int) -> int:
    """
    Choose the best integer scale factor to fit within target size.
    
    Args:
        src_wh: Source (width, height) tuple
        target: Target size (square side length)
        
    Returns:
        Integer scale factor
    """
    w, h = src_wh
    sf = max(1, min(target // max(1, w), target // max(1, h)))
    return max(sf, 1)


def resize_nearest(pil_img: Image.Image, scale: int) -> Image.Image:
    """
    Resize image using nearest-neighbor interpolation (for pixel art).
    
    Args:
        pil_img: Input PIL Image
        scale: Integer scale factor
        
    Returns:
        Scaled image
    """
    return pil_img.resize(
        (pil_img.width * scale, pil_img.height * scale), 
        resample=NEAREST
    )


def resize_lanczos_to_box(
    pil_img: Image.Image, 
    target_wh: Tuple[int, int]
) -> Image.Image:
    """
    Resize image to exact dimensions using Lanczos resampling.
    
    Args:
        pil_img: Input PIL Image
        target_wh: Target (width, height) tuple
        
    Returns:
        Resized image
    """
    return pil_img.resize(target_wh, resample=LANCZOS)


def resize_lanczos_fit_long(
    pil_img: Image.Image, 
    target_long: int
) -> Image.Image:
    """
    Resize image to fit long side to target, maintaining aspect ratio.
    Only downscales - if image is already smaller, returns as-is.
    
    Args:
        pil_img: Input PIL Image
        target_long: Target long side length
        
    Returns:
        Resized image (guaranteed: max(w, h) <= target_long)
    """
    w, h = pil_img.size
    long_side = max(w, h)
    
    # If already fits, return as-is (no upscaling)
    if long_side <= target_long:
        return pil_img
    
    # Downscale to fit long side to target
    if w >= h:
        new_w = target_long
        new_h = max(1, int(h * (target_long / w)))
    else:
        new_h = target_long
        new_w = max(1, int(w * (target_long / h)))
    return pil_img.resize((new_w, new_h), resample=LANCZOS)
