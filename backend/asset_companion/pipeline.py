"""Main image processing pipeline."""
import enum
import json
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, Union
from PIL import Image

from asset_companion.io import (
    load_image_rgba,
    save_image_with_icc,
    get_icc_profile
)   
from asset_companion.detect import (
    Kind,
    detect_kind,
    bbox_from_alpha,
    is_alpha_bbox_meaningful,
    crop_to_bbox
)
from asset_companion.alpha_fix import unpremultiply_rgba, defringe_alpha, smooth_alpha_edges
from asset_companion.scale import choose_integer_scale, resize_nearest
from asset_companion.pad_crop import smart_square, fit_to_size
from asset_companion.size_utils import calculate_target_size
from asset_companion.enhance import unsharp_mask
from asset_companion.realesrgan import run_realesrgan


class SuperRes(str, enum.Enum):
    """Super-resolution method enumeration."""
    none = "none"
    realesrgan = "realesrgan"


def process_one(
    src: Path,
    dst: Path,
    target: int = 512,
    target_w: Optional[int] = None,
    target_h: Optional[int] = None,
    kind: Kind = Kind.auto,
    superres: Union[str, SuperRes] = "none",
    outpaint: bool = False,
    log_jsonl: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Process a single image through the complete pipeline.
    
    Pipeline steps:
    1. Load image and extract metadata
    2. Detect image kind (pixel art vs illustration)
    3. Optional alpha-based trimming (only if meaningful padding removal)
    4. Fix alpha channel issues (kind-specific)
    5. Scale using appropriate strategy
    6. Apply super-resolution if requested (illustrations only)
    7. Make square (always pad, never crop by default)
    8. Apply alpha edge smoothing (illustrations only)
    9. Apply enhancement (kind-specific sharpening)
    10. Save with ICC profile preservation
    
    Default behavior: Preserves full asset content by padding to square.
    Never crops unless explicitly requested. Different processing for
    pixel art (hard edges) vs illustrations (smooth edges).
    
    Args:
        src: Source image path
        dst: Destination image path
        target: Target square size in pixels (used if target_w/target_h not provided)
        target_w: Target width (optional, for non-square output)
        target_h: Target height (optional, for non-square output)
        kind: Image kind (auto-detect if Kind.auto)
        superres: Super-resolution method ("none" or "realesrgan")
        outpaint: Whether to use inpainting (not implemented)
        log_jsonl: Optional path to log JSONL file
        
    Returns:
        Dictionary with processing metadata
    """
    try:
        # Load image
        pil = load_image_rgba(src)
        icc = get_icc_profile(pil)
        meta: Dict[str, Any] = {
            "src": str(src),
            "w": pil.width,
            "h": pil.height
        }
        
        # Determine target dimensions
        if target_w is not None and target_h is not None:
            # Non-square target specified
            final_w, final_h = target_w, target_h
            is_square = False
        else:
            # Square target (default)
            final_w = final_h = target
            is_square = True
        
        # Kind detection (before cropping, to inform processing decisions)
        k = detect_kind(pil) if kind == Kind.auto else kind
        meta["kind"] = k.value
        
        # BBox detection and optional trimming
        # Only trim using alpha bbox if it's meaningful (removes significant padding)
        # Never use saliency-based cropping by default (preserves full asset)
        bbox = bbox_from_alpha(pil)
        if bbox and is_alpha_bbox_meaningful(pil, bbox):
            pil = crop_to_bbox(pil, bbox, margin=2)
            meta["bbox"] = bbox
            meta["trimmed"] = True
        else:
            # No meaningful trimming - use full image
            meta["bbox"] = (0, 0, pil.width - 1, pil.height - 1)
            meta["trimmed"] = False
        
        # Alpha fix - different treatment for pixel art vs illustration
        pil = unpremultiply_rgba(pil)
        if k == Kind.pixel_art:
            # Pixel art: preserve hard edges with light defringe
            pil = defringe_alpha(pil, radius=1)
        else:
            # Illustration: skip defringe (avoids hardening edges)
            # Alpha smoothing will be applied later after scaling
            pass
        
        # Scale strategy
        if k == Kind.pixel_art:
            # Pixel art: integer scale with nearest-neighbor
            if is_square:
                sf = choose_integer_scale(pil.size, target)
                pil = resize_nearest(pil, sf)
                # Always pad to square (preserve full pixel art)
                pil = smart_square(pil, target, use_saliency=False, allow_crop=False)
            else:
                # Non-square: use integer scale for long side, then fit
                long_side = max(pil.width, pil.height)
                target_long = max(final_w, final_h)
                sf = choose_integer_scale((long_side, long_side), target_long)
                pil = resize_nearest(pil, sf)
                # Fit to target dimensions (preserve full pixel art)
                pil = fit_to_size(pil, final_w, final_h, allow_crop=False)
        else:
            # Illustration: super-resolution (optional) then fit to target
            # Normalize superres to string for comparison
            superres_str = superres.value if isinstance(superres, SuperRes) else superres
            if superres_str == SuperRes.realesrgan.value:
                # Write temporary file (lossless)
                # Real-ESRGAN will be auto-downloaded if needed via get_realesrgan_path()
                tmp_in = dst.parent / f".__tmp_in_{src.stem}.png"
                tmp_out = dst.parent / f".__tmp_sr_{src.stem}.png"
                save_image_with_icc(pil, tmp_in, icc)
                run_realesrgan(tmp_in, tmp_out, scale=4, model="realesrgan-x4plus")
                pil = load_image_rgba(tmp_out)
                # Cleanup temp files
                try:
                    tmp_in.unlink(missing_ok=True)
                    tmp_out.unlink(missing_ok=True)
                except Exception:
                    pass
            
            # Fit to target dimensions (preserve full asset)
            if is_square:
                pil = smart_square(pil, target, use_saliency=False, allow_crop=False)
            else:
                pil = fit_to_size(pil, final_w, final_h, allow_crop=False)
            
            # Apply alpha edge smoothing for illustrations (reduces jagged edges)
            pil = smooth_alpha_edges(pil, radius=0.5)
        
        # Enhance - different sharpening for pixel art vs illustration
        if k == Kind.pixel_art:
            # Pixel art: full sharpening (including alpha)
            pil = unsharp_mask(pil, radius=1.0, amount=0.2, rgb_only=False)
        else:
            # Illustration: light RGB-only sharpening (preserves smooth alpha edges)
            pil = unsharp_mask(pil, radius=1.0, amount=0.1, rgb_only=True)
        
        # Save
        save_image_with_icc(pil, dst, icc)
        meta.update({
            "dst": str(dst),
            "ok": True,
            "final_w": pil.width,
            "final_h": pil.height
        })
        
        # Log if requested
        if log_jsonl:
            log_jsonl.parent.mkdir(parents=True, exist_ok=True)
            with open(log_jsonl, "a", encoding="utf-8") as f:
                f.write(json.dumps(meta, ensure_ascii=False) + "\n")
        
        return meta
        
    except Exception as e:
        error_msg = f"{src}: {e}"
        error_meta = {
            "src": str(src),
            "error": str(e),
            "ok": False
        }
        
        # Log error if requested
        if log_jsonl:
            try:
                log_jsonl.parent.mkdir(parents=True, exist_ok=True)
                with open(log_jsonl, "a", encoding="utf-8") as f:
                    f.write(json.dumps(error_meta, ensure_ascii=False) + "\n")
            except Exception:
                pass
        
        # Re-raise with context
        raise RuntimeError(error_msg) from e
