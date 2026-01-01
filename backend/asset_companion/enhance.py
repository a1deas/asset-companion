"""Image enhancement operations."""
import numpy as np
from PIL import Image, ImageFilter


def unsharp_mask(
    pil_img: Image.Image, 
    radius: float = 1.0, 
    amount: float = 0.2,
    rgb_only: bool = False
) -> Image.Image:
    """
    Apply unsharp mask filter to enhance image sharpness.
    
    Uses a soft approach: Gaussian blur + merge instead of Pillow's
    aggressive UnsharpMask filter.
    
    Args:
        pil_img: Input PIL Image
        radius: Blur radius
        amount: Sharpening amount (0.0-1.0)
        rgb_only: If True and image is RGBA, only sharpen RGB channels,
                  leaving alpha unchanged (prevents edge artifacts)
        
    Returns:
        Enhanced PIL Image
    """
    blur = pil_img.filter(ImageFilter.GaussianBlur(radius))
    arr = np.array(pil_img).astype(np.float32)
    arr_blur = np.array(blur).astype(np.float32)
    
    if rgb_only and pil_img.mode == "RGBA":
        # Only sharpen RGB channels, preserve alpha
        rgb = arr[..., :3]
        rgb_blur = arr_blur[..., :3]
        rgb_sharp = np.clip(rgb + amount * (rgb - rgb_blur), 0, 255)
        arr[..., :3] = rgb_sharp
        # Alpha remains unchanged
    else:
        # Sharpen all channels
        arr = np.clip(arr + amount * (arr - arr_blur), 0, 255)
    
    return Image.fromarray(arr.astype(np.uint8), mode=pil_img.mode)
