"""FastAPI application for Asset Companion."""
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from typing import Optional
from fastapi.responses import JSONResponse, FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from asset_companion.pipeline import process_one, SuperRes
from asset_companion.detect import Kind

app = FastAPI(
    title="Asset Companion",
    description="Simple utility tool for asset processing.",
    version="0.1.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Fixed typo: allowe_origins -> allow_origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Directory setup
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

INPUT_DIR = Path("inputs")
INPUT_DIR.mkdir(exist_ok=True)


@app.post("/process")
async def process(
    file: UploadFile = File(...),
    target: int = Form(512),
    size_mode: str = Form("square"),
    size_width: Optional[int] = Form(None),
    size_height: Optional[int] = Form(None),
    size_multiple: str = Form("8"),
    kind: str = Form("auto"),
    superres: str = Form("none"),
) -> JSONResponse:
    """
    Process an uploaded image through the asset companion pipeline.
    
    Args:
        file: Uploaded image file
        target: Target square size in pixels (default: 512, used if size_mode="square")
        size_mode: Size calculation mode:
            - "square": Use target for square output
            - "auto": Auto-suggest size (power of 2 or multiple of 8)
            - "power_of_two": Round to nearest power of 2
            - "multiple": Round to nearest multiple (use size_multiple)
            - "custom": Use size_width and size_height
        size_width: Custom width (used if size_mode="custom")
        size_height: Custom height (used if size_mode="custom")
        size_multiple: Multiple for "multiple" mode (default: "8", can be "2" or "8")
        kind: Image kind - "auto", "pixel_art", or "illustration" (default: "auto")
        superres: Super-resolution method - "none" or "realesrgan" (default: "none")
        
    Returns:
        JSON response with processing metadata
    """
    try:
        # Validate inputs
        if target < 1 or target > 4096:
            raise HTTPException(
                status_code=400,
                detail="Target size must be between 1 and 4096"
            )
        
        if kind not in ("auto", "pixel_art", "illustration"):
            raise HTTPException(
                status_code=400,
                detail="Kind must be 'auto', 'pixel_art', or 'illustration'"
            )
        
        if superres not in ("none", "realesrgan"):
            raise HTTPException(
                status_code=400,
                detail="Superres must be 'none' or 'realesrgan'"
            )
        
        if size_mode not in ("square", "auto", "power_of_two", "multiple", "custom"):
            raise HTTPException(
                status_code=400,
                detail="size_mode must be 'square', 'auto', 'power_of_two', 'multiple', or 'custom'"
            )
        
        # Save uploaded file first to get dimensions
        if not file.filename:
            raise HTTPException(status_code=400, detail="Filename is required")
        src_path = INPUT_DIR / file.filename
        with src_path.open("wb") as f:
            content = await file.read()
            if len(content) == 0:
                raise HTTPException(status_code=400, detail="Empty file")
            f.write(content)
        
        # Load image to get dimensions for size calculation
        from PIL import Image
        from asset_companion.size_utils import calculate_target_size
        
        with Image.open(src_path) as img:
            input_w, input_h = img.size
        
        # Calculate target dimensions based on mode
        if size_mode == "square":
            target_w = None
            target_h = None
        elif size_mode == "custom":
            if size_width is None or size_height is None:
                raise HTTPException(
                    status_code=400,
                    detail="size_width and size_height required for custom mode"
                )
            if size_width < 1 or size_width > 4096 or size_height < 1 or size_height > 4096:
                raise HTTPException(
                    status_code=400,
                    detail="Custom size must be between 1 and 4096"
                )
            target_w = size_width
            target_h = size_height
        else:
            # Calculate using size_utils
            multiple_val = int(size_multiple) if size_multiple.isdigit() else 8
            if multiple_val not in (2, 4, 8, 16):
                multiple_val = 8
            
            target_w, target_h = calculate_target_size(
                input_w, input_h,
                mode=size_mode,
                multiple=multiple_val
            )
        
        # Process
        output_path = OUTPUT_DIR / (src_path.stem + "_ac.png")
        meta = process_one(
            src=src_path,
            dst=output_path,
            target=target,
            target_w=target_w,
            target_h=target_h,
            kind=Kind(kind),
            superres=superres
        )
        
        return JSONResponse({"ok": True, "meta": meta})
        
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            {"ok": False, "error": str(e)},
            status_code=500
        )


@app.get("/download", response_model=None)
async def download(path: str) -> Response:
    """
    Download a processed image file.
    
    Args:
        path: Path to the file to download
        
    Returns:
        File response or error JSON
    """
    p = Path(path)
    
    # Security: prevent path traversal
    if ".." in str(p) or not p.is_absolute():
        # Only allow files in OUTPUT_DIR
        p = OUTPUT_DIR / p.name
    
    if not p.exists() or not p.is_file():
        return JSONResponse(
            {"ok": False, "error": "File not found"},
            status_code=404
        )
    
    return FileResponse(p)
