# Asset Companion

A production-ready image processing pipeline for game assets and illustrations. Automatically processes images with intelligent cropping, scaling, super-resolution, and enhancement.

## Features

- **Smart Detection**: Automatically detects pixel art vs illustrations
- **Intelligent Cropping**: Uses alpha channel or saliency maps for optimal bounding boxes
- **Adaptive Scaling**:
  - Pixel art: Integer scaling with nearest-neighbor interpolation
  - Illustrations: High-quality Lanczos scaling with optional super-resolution
- **Super-Resolution**: Optional Real-ESRGAN integration (auto-downloads if not found)
- **Alpha Processing**: Unpremultiplies alpha and defringes edges
- **Smart Square**: Intelligently crops or pads images to square format
- **Enhancement**: Applies subtle unsharp mask for final polish
- **ICC Profile Preservation**: Maintains color profiles throughout processing

## Installation

### Requirements

- Python 3.8+
- FastAPI (for web API)
- See `requirements.txt` for full dependencies

### Setup

```bash
cd backend
pip install -r requirements.txt
```

### Real-ESRGAN (Optional)

Real-ESRGAN will be automatically downloaded on first use if not found in PATH. The binary is cached in:

- **Windows**: `%LOCALAPPDATA%\asset-companion\realesrgan\`
- **Linux/Mac**: `~/.cache/asset-companion/realesrgan/`

Alternatively, you can manually install `realesrgan-ncnn-vulkan` and add it to your PATH.

## Usage

### Web API

Start the FastAPI server:

```bash
uvicorn app:app --reload
```

#### Process Image

```bash
POST /process
Content-Type: multipart/form-data

Parameters:
- file: Image file (required)
- target: Target square size in pixels (default: 512)
- kind: "auto", "pixel_art", or "illustration" (default: "auto")
- superres: "none" or "realesrgan" (default: "none")
```

Example with curl:

```bash
curl -X POST "http://localhost:8000/process" \
  -F "file=@image.png" \
  -F "target=512" \
  -F "kind=auto" \
  -F "superres=none"
```

#### Download Processed Image

```bash
GET /download?path=output/image_ac.png
```

### Python API

```python
from pathlib import Path
from asset_companion import process_one, Kind, SuperRes

# Process an image
meta = process_one(
    src=Path("input.png"),
    dst=Path("output.png"),
    target=512,
    kind=Kind.auto,
    superres=SuperRes.none
)

print(meta)  # Processing metadata
```

## Processing Pipeline

1. **Load**: Image loaded and converted to RGBA
2. **BBox Detection**: Finds optimal bounding box using alpha channel or saliency
3. **Crop**: Crops to bounding box with margin
4. **Kind Detection**: Classifies as pixel art or illustration
5. **Alpha Fix**: Unpremultiplies alpha and defringes edges
6. **Scaling**:
   - **Pixel Art**: Integer scale with nearest-neighbor
   - **Illustration**: Lanczos scaling, optional Real-ESRGAN super-resolution
7. **Smart Square**: Intelligently crops or pads to square
8. **Enhancement**: Applies unsharp mask
9. **Save**: Saves with ICC profile preservation

## API Reference

### `process_one()`

Main processing function.

**Parameters:**

- `src` (Path): Source image path
- `dst` (Path): Destination image path
- `target` (int): Target square size (default: 512)
- `kind` (Kind): Image kind - `Kind.auto`, `Kind.pixel_art`, or `Kind.illustration`
- `superres` (str): Super-resolution method - `"none"` or `"realesrgan"`
- `outpaint` (bool): Enable inpainting (not yet implemented)
- `log_jsonl` (Optional[Path]): Optional JSONL log file path

**Returns:**

- `Dict[str, Any]`: Processing metadata including dimensions, bounding box, kind, etc.

### `Kind`

Image type enumeration:

- `Kind.auto`: Auto-detect
- `Kind.pixel_art`: Pixel art image
- `Kind.illustration`: Illustration/image

### `SuperRes`

Super-resolution method:

- `SuperRes.none`: No super-resolution
- `SuperRes.realesrgan`: Real-ESRGAN super-resolution

## Architecture

```
asset_companion/
├── __init__.py          # Package exports
├── pipeline.py          # Main processing pipeline
├── detect.py            # Image kind detection & bbox operations
├── io.py                # Image I/O with ICC preservation
├── scale.py             # Scaling operations
├── pad_crop.py          # Padding, cropping, smart square
├── alpha_fix.py         # Alpha channel processing
├── enhance.py           # Image enhancement
└── realesrgan.py        # Real-ESRGAN integration
```

## Error Handling

The pipeline includes comprehensive error handling:

- Input validation
- File I/O error handling
- Real-ESRGAN availability checks
- Graceful degradation when optional features unavailable
