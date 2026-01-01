"""Image I/O operations with ICC profile preservation."""
from pathlib import Path
from typing import Optional
import numpy as np
from PIL import Image


def load_image_rgba(path: Path) -> Image.Image:
    """
    Load an image and convert it to RGBA mode.
    
    Args:
        path: Path to the image file
        
    Returns:
        PIL Image in RGBA mode
    """
    img = Image.open(path)
    if img.mode in ("P", "L"):
        img = img.convert("RGBA")
    elif img.mode == "RGB":
        img = img.convert("RGB")
    elif img.mode == "RGBA":
        pass
    else:
        img = img.convert("RGBA")
    return img


def save_image_with_icc(
    img: Image.Image, 
    output_path: Path, 
    icc_profile: Optional[bytes] = None
) -> None:
    """
    Save an image with optional ICC profile preservation.
    
    Args:
        img: PIL Image to save
        output_path: Destination path
        icc_profile: Optional ICC profile bytes to embed
    """
    params = {}
    if icc_profile:
        params["icc_profile"] = icc_profile
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, **params)


def get_icc_profile(pil_img: Image.Image) -> Optional[bytes]:
    """
    Extract ICC profile from a PIL Image.
    
    Args:
        pil_img: PIL Image
        
    Returns:
        ICC profile bytes or None if not available
    """
    try:
        return pil_img.info.get("icc_profile", None)
    except Exception:
        return None


def pil_to_numpy(img: Image.Image) -> np.ndarray:
    """
    Convert PIL Image to numpy array.
    
    Args:
        img: PIL Image
        
    Returns:
        numpy array representation
    """
    return np.array(img)


def np_to_pil(arr: np.ndarray) -> Image.Image:
    """
    Convert numpy array to PIL Image.
    
    Args:
        arr: numpy array
        
    Returns:
        PIL Image
    """
    return Image.fromarray(arr)
