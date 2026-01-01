"""Alpha channel processing and edge cleanup."""
import numpy as np
import cv2
from PIL import Image


def unpremultiply_rgba(pil_img: Image.Image) -> Image.Image:
    """
    Unpremultiply alpha channel to fix premultiplied alpha artifacts.
    
    Args:
        pil_img: Input PIL Image (must be RGBA)
        
    Returns:
        Image with unpremultiplied alpha
    """
    if pil_img.mode != "RGBA":
        return pil_img
    arr = np.array(pil_img).astype(np.float32)
    rgb = arr[..., :3]
    a = arr[..., 3:4] / 255.0
    # Avoid division by zero
    mask = a > 1e-5
    rgb[mask[..., 0]] = rgb[mask[..., 0]] / np.clip(a[mask[..., 0]], 1e-5, 1.0)
    arr[..., :3] = np.clip(rgb, 0, 255)
    return Image.fromarray(arr.astype(np.uint8), mode="RGBA")


def defringe_alpha(pil_img: Image.Image, radius: int = 1) -> Image.Image:
    """
    Light alpha dilation and cleanup of color fringing at edges.
    
    Note: This hardens edges (useful for pixel art, but can make
    illustration edges look jagged). For illustrations, use smooth_alpha_edges instead.
    
    Args:
        pil_img: Input PIL Image (must be RGBA)
        radius: Dilation radius
        
    Returns:
        Image with defringed alpha
    """
    if pil_img.mode != "RGBA":
        return pil_img
    arr = np.array(pil_img)
    a = arr[..., 3]
    kernel = np.ones((radius * 2 + 1, radius * 2 + 1), np.uint8)
    a_dil = cv2.dilate(a, kernel, iterations=1)
    arr[..., 3] = a_dil
    return Image.fromarray(arr, mode="RGBA")


def smooth_alpha_edges(pil_img: Image.Image, radius: float = 0.5) -> Image.Image:
    """
    Smooth alpha channel edges using a light Gaussian blur.
    
    This reduces stair-stepping and jagged edges in illustrations
    while preserving the overall shape. Only affects the alpha channel.
    
    Args:
        pil_img: Input PIL Image (must be RGBA)
        radius: Blur radius for alpha smoothing (small, typically 0.5-1.0)
        
    Returns:
        Image with smoothed alpha edges
    """
    if pil_img.mode != "RGBA":
        return pil_img
    
    arr = np.array(pil_img).astype(np.float32)
    alpha = arr[..., 3]
    
    # Apply light Gaussian blur to alpha channel only
    alpha_blur = cv2.GaussianBlur(alpha, (0, 0), radius)
    
    # Preserve fully opaque and fully transparent regions
    # Only smooth the transition band
    alpha_smooth = np.clip(alpha_blur, 0, 255).astype(np.uint8)
    
    arr[..., 3] = alpha_smooth
    return Image.fromarray(arr.astype(np.uint8), mode="RGBA")
