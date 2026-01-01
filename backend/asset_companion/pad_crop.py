"""Image padding, cropping, and smart square operations."""
import numpy as np
import cv2
from PIL import Image
from asset_companion.scale import resize_lanczos_fit_long, resize_lanczos_to_box
from asset_companion.detect import bbox_from_saliency


def aspect_delta(w: int, h: int) -> float:
    """
    Calculate aspect ratio difference from square (1:1).
    
    Args:
        w: Width
        h: Height
        
    Returns:
        Absolute difference from 1.0
    """
    return abs((w / max(1.0, h)) - 1.0)


def pad_to_square(
    pil_img: Image.Image, 
    side: int, 
    inpaint: bool = False, 
    method: str = "telea"
) -> Image.Image:
    """
    Pad image to square, optionally using inpainting.
    
    IMPORTANT: This function assumes the invariant w <= side AND h <= side.
    Caller must ensure this before calling pad_to_square().
    
    Args:
        pil_img: Input PIL Image (must have w <= side AND h <= side)
        side: Target square side length
        inpaint: Whether to inpaint transparent areas
        method: Inpainting method ("telea" or "ns")
        
    Returns:
        Square image
    """
    w, h = pil_img.size
    
    # Assert invariant (for debugging - should never fail if used correctly)
    assert w <= side and h <= side, f"pad_to_square invariant violated: {w}x{h} > {side}x{side}"
    
    if w == side and h == side:
        return pil_img
    
    # Center on new canvas
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    x = (side - w) // 2
    y = (side - h) // 2
    canvas.paste(pil_img, (x, y))
    
    if not inpaint:
        return canvas
    
    # Inpaint transparent areas
    arr = np.array(canvas)
    alpha = arr[..., 3]
    mask = (alpha == 0).astype(np.uint8) * 255
    # Inpaint works on 3-channel image
    bgr = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
    if method == "telea":
        out = cv2.inpaint(bgr, mask, 3, cv2.INPAINT_TELEA)
    else:
        out = cv2.inpaint(bgr, mask, 3, cv2.INPAINT_NS)
    rgba = cv2.cvtColor(out, cv2.COLOR_BGR2RGBA)
    return Image.fromarray(rgba, mode="RGBA")


def smart_square(
    pil_img: Image.Image, 
    side: int, 
    use_saliency: bool = False,
    allow_crop: bool = False
) -> Image.Image:
    """
    Intelligently make image square using padding (default) or cropping (optional).
    
    Default behavior: Always pad to preserve full asset content.
    Only crops if allow_crop=True and both dimensions exceed target.
    
    IMPORTANT: Before calling pad_to_square(), ensures invariant: w <= side AND h <= side.
    If image is larger, downscales first using fit-to-box.
    
    Args:
        pil_img: Input PIL Image
        side: Target square side length
        use_saliency: Whether to use saliency for cropping (only if allow_crop=True)
        allow_crop: If True, allows cropping when image is larger than target.
                    If False (default), always pads to preserve full content.
        
    Returns:
        Square image
    """
    w, h = pil_img.size
    
    # If already square and correct size, return as-is
    if w == side and h == side:
        return pil_img
    
    # If aspect difference is small, check if we need to downscale first
    if aspect_delta(w, h) < 0.1:
        # If max(w, h) > side, downscale first, then pad
        if max(w, h) > side:
            img_fit = resize_lanczos_fit_long(pil_img, side)
            # Now guaranteed: max(w, h) <= side, so w <= side AND h <= side
            return pad_to_square(img_fit, side, inpaint=False)
        else:
            # Already fits, just pad
            return pad_to_square(pil_img, side, inpaint=False)
    
    # For non-square images: scale long side to target (fit-to-box downscale)
    img_fit = resize_lanczos_fit_long(pil_img, side)
    w, h = img_fit.size
    
    # After resize_lanczos_fit_long, we have: max(w, h) <= side
    # But we need: w <= side AND h <= side
    # This is guaranteed because if long side <= side, then both sides <= side
    
    # Default: always pad to preserve full content
    if not allow_crop:
        return pad_to_square(img_fit, side, inpaint=False)
    
    # Optional cropping path (only if explicitly allowed)
    if w >= side and h >= side:
        # Crop by saliency/center (only if use_saliency is True)
        if use_saliency:
            bbox = bbox_from_saliency(img_fit)
            cx = (bbox[0] + bbox[2]) // 2
            cy = (bbox[1] + bbox[3]) // 2
        else:
            cx, cy = w // 2, h // 2
        
        x0 = max(0, min(w - side, cx - side // 2))
        y0 = max(0, min(h - side, cy - side // 2))
        return img_fit.crop((x0, y0, x0 + side, y0 + side))
    else:
        # If one side is smaller, pad (invariant already guaranteed by resize_lanczos_fit_long)
        return pad_to_square(img_fit, side, inpaint=False)


def fit_to_size(
    pil_img: Image.Image,
    target_w: int,
    target_h: int,
    allow_crop: bool = False
) -> Image.Image:
    """
    Fit image to target dimensions, preserving aspect ratio.
    
    Default behavior: Always downscale and pad to preserve full asset content.
    Only crops if allow_crop=True and image is larger than target.
    
    IMPORTANT: Before calling pad_to_size(), ensures invariant: w <= target_w AND h <= target_h.
    If image is larger, downscales first using fit-to-box.
    
    Args:
        pil_img: Input PIL Image
        target_w: Target width
        target_h: Target height
        allow_crop: If True, allows cropping when image is larger than target.
                    If False (default), always pads to preserve full content.
        
    Returns:
        Image fitted to target dimensions
    """
    w, h = pil_img.size
    
    # If already correct size, return as-is
    if w == target_w and h == target_h:
        return pil_img
    
    # Calculate aspect ratios
    img_aspect = w / h if h > 0 else 1.0
    target_aspect = target_w / target_h if target_h > 0 else 1.0
    
    # Determine if we need to downscale
    needs_downscale = w > target_w or h > target_h
    
    if needs_downscale:
        # Downscale to fit within target dimensions
        # Fit long side to target, maintaining aspect ratio
        if img_aspect >= target_aspect:
            # Image is wider or same aspect - fit to width
            scale = target_w / w
            new_w = target_w
            new_h = max(1, int(h * scale))
        else:
            # Image is taller - fit to height
            scale = target_h / h
            new_h = target_h
            new_w = max(1, int(w * scale))
        
        # Ensure we don't exceed target dimensions
        if new_w > target_w:
            new_h = int(new_h * (target_w / new_w))
            new_w = target_w
        if new_h > target_h:
            new_w = int(new_w * (target_h / new_h))
            new_h = target_h
        
        img_fit = resize_lanczos_to_box(pil_img, (new_w, new_h))
        w, h = img_fit.size
    else:
        img_fit = pil_img
        w, h = pil_img.size
    
    # Now we have: w <= target_w AND h <= target_h (invariant)
    
    # Default: always pad to preserve full content
    if not allow_crop:
        # Pad to target dimensions
        canvas = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
        x = (target_w - w) // 2
        y = (target_h - h) // 2
        canvas.paste(img_fit, (x, y))
        return canvas
    
    # Optional cropping path (only if explicitly allowed)
    if w >= target_w and h >= target_h:
        # Crop to center
        x0 = (w - target_w) // 2
        y0 = (h - target_h) // 2
        return img_fit.crop((x0, y0, x0 + target_w, y0 + target_h))
    else:
        # If one side is smaller, pad (invariant already guaranteed)
        canvas = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
        x = (target_w - w) // 2
        y = (target_h - h) // 2
        canvas.paste(img_fit, (x, y))
        return canvas
