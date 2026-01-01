"""
Real-ESRGAN (realesrgan-ncnn-vulkan) integration with auto-download support.

Chosen robust approach:
- Download the official portable ZIP from GitHub Releases (fixed filenames for v0.2.5.0).
- Extract into a dedicated cache subfolder (keep the whole bundle: exe + models + dlls).
- Run the binary with cwd=binary.parent so relative resources (models/, dlls) are found.
- Provide clear errors if something is missing.

This avoids the common Windows pitfall:
moving only the .exe breaks models/dll resolution -> runtime failure -> 500 in FastAPI.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple
import urllib.request
import zipfile


# Fixed, known-good release and asset names for portable ncnn-vulkan builds.
REALESRGAN_VERSION = "v0.2.5.0"
REALESRGAN_RELEASES = "https://github.com/xinntao/Real-ESRGAN/releases"


def _asset_name_for_current_os() -> Optional[str]:
    """Return the exact asset ZIP name for the current OS (v0.2.5.0)."""
    system = platform.system().lower()
    if system == "windows":
        return "realesrgan-ncnn-vulkan-20220424-windows.zip"
    if system == "linux":
        return "realesrgan-ncnn-vulkan-20220424-ubuntu.zip"
    if system == "darwin":
        return "realesrgan-ncnn-vulkan-20220424-macos.zip"
    return None


def get_realesrgan_binary_name() -> str:
    """Return binary filename for current OS."""
    return "realesrgan-ncnn-vulkan.exe" if platform.system().lower() == "windows" else "realesrgan-ncnn-vulkan"


def find_realesrgan_in_path() -> Optional[Path]:
    """
    Check if realesrgan-ncnn-vulkan is already available in PATH.
    Note: if it's in PATH, we assume user installed it properly with models available.
    """
    binary = shutil.which(get_realesrgan_binary_name())
    return Path(binary) if binary else None


def get_realesrgan_cache_dir() -> Path:
    """
    Cache directory for downloaded portable builds.

    Windows: %LOCALAPPDATA%/asset-companion/realesrgan
    Linux/macOS: ~/.cache/asset-companion/realesrgan
    """
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path.home() / ".cache"
    return base / "asset-companion" / "realesrgan"


def _extract_dir_for_release(cache_dir: Path) -> Path:
    """
    Where the portable bundle is extracted.
    Keep the whole folder intact (exe + models + dlls).
    """
    # You can include version & asset date to avoid collisions.
    return cache_dir / f"portable-{REALESRGAN_VERSION}-20220424"


def _validate_bundle(binary_path: Path) -> None:
    """
    Validate the extracted bundle structure.

    At minimum we expect:
    - binary exists
    - models/ directory exists somewhere near the binary (usually sibling)
    """
    if not binary_path.exists():
        raise RuntimeError(f"Real-ESRGAN binary not found: {binary_path}")

    # Most portable zips have models/ next to the exe
    models_dir = binary_path.parent / "models"
    if not models_dir.exists() or not models_dir.is_dir():
        # Some zips may have nested structure; still, models should be near exe after rglob find.
        raise RuntimeError(
            "Real-ESRGAN bundle seems incomplete: 'models' directory not found next to the binary. "
            "Do not move only the exe; keep the entire extracted folder."
        )


def download_realesrgan() -> Optional[Path]:
    """
    Download and extract portable realesrgan-ncnn-vulkan for current OS.

    Returns:
        Path to the binary inside the extracted bundle, or None on failure.
    """
    asset = _asset_name_for_current_os()
    if not asset:
        print(f"Unsupported OS: {platform.system()} {platform.machine()}")
        return None

    cache_dir = get_realesrgan_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)

    extract_dir = _extract_dir_for_release(cache_dir)
    binary_name = get_realesrgan_binary_name()

    # If already extracted, locate binary and validate.
    if extract_dir.exists():
        # Find exe in extracted folder (handles nested folders inside zip).
        found = None
        for p in extract_dir.rglob(binary_name):
            found = p
            break
        if found:
            try:
                if sys.platform != "win32":
                    os.chmod(found, 0o755)
                _validate_bundle(found)
                return found
            except Exception:
                # Extraction may be corrupted; re-extract below.
                shutil.rmtree(extract_dir, ignore_errors=True)

    # Download ZIP into cache root.
    download_url = f"{REALESRGAN_RELEASES}/download/{REALESRGAN_VERSION}/{asset}"
    zip_path = cache_dir / asset

    try:
        print(f"Downloading realesrgan-ncnn-vulkan from {download_url}...")
        urllib.request.urlretrieve(download_url, zip_path)

        # Fresh extract
        if extract_dir.exists():
            shutil.rmtree(extract_dir, ignore_errors=True)
        extract_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(extract_dir)

        # Locate binary (zip may contain nested folder)
        found = None
        for p in extract_dir.rglob(binary_name):
            found = p
            break

        if not found:
            print(f"Binary '{binary_name}' not found after extraction.")
            return None

        if sys.platform != "win32":
            os.chmod(found, 0o755)

        # Validate required resources
        _validate_bundle(found)

        # Optionally remove ZIP to save space
        try:
            zip_path.unlink(missing_ok=True)
        except Exception:
            pass

        return found

    except Exception as e:
        print(f"Failed to download/extract realesrgan-ncnn-vulkan: {e}")
        print(f"Manual download: {REALESRGAN_RELEASES}")
        return None


def get_realesrgan_path() -> Optional[Path]:
    """
    Get a working realesrgan-ncnn-vulkan binary.

    Priority:
    1) PATH install
    2) cached extracted portable bundle
    3) download + extract portable bundle
    """
    path_binary = find_realesrgan_in_path()
    if path_binary:
        return path_binary

    cache_dir = get_realesrgan_cache_dir()
    extract_dir = _extract_dir_for_release(cache_dir)
    binary_name = get_realesrgan_binary_name()

    if extract_dir.exists():
        for p in extract_dir.rglob(binary_name):
            try:
                _validate_bundle(p)
                return p
            except Exception:
                break

    return download_realesrgan()


def check_realesrgan_available() -> bool:
    """
    Check if realesrgan-ncnn-vulkan is available and can be executed.
    
    This will attempt to download if not found, but may return False
    if the binary exists but cannot be executed (e.g., missing dependencies).
    """
    binary_path = get_realesrgan_path()
    if not binary_path:
        return False

    try:
        # Use cwd=binary.parent to ensure models/dlls resolve properly.
        result = subprocess.run(
            [str(binary_path), "-h"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(binary_path.parent),
        )
        # Help often returns 1; accept 0/1.
        return result.returncode in (0, 1)
    except Exception:
        return False


def run_realesrgan(
    input_path: Path,
    output_path: Path,
    scale: int = 4,
    model: str = "realesrgan-x4plus",
) -> None:
    """
    Run realesrgan-ncnn-vulkan super-resolution.

    Args:
        input_path: input image path
        output_path: output image path
        scale: upscale factor (2 or 4 typically)
        model: model name (e.g. realesrgan-x4plus)

    Raises:
        RuntimeError if binary is unavailable or execution fails.
    """
    binary_path = get_realesrgan_path()
    if not binary_path:
        raise RuntimeError(
            "realesrgan-ncnn-vulkan not found and auto-download failed. "
            f"See: {REALESRGAN_RELEASES}"
        )

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    # Ensure output folder exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Remove existing output file if it exists (some tools won't overwrite)
    if output_path.exists():
        output_path.unlink()
    
    # Use absolute paths to avoid issues with cwd
    abs_input = input_path.resolve()
    abs_output = output_path.resolve()

    cmd = [
        str(binary_path),
        "-i", str(abs_input),
        "-o", str(abs_output),
        "-s", str(scale),
        "-n", model,
        "-f", "png",
    ]

    try:
        # The critical part: run with cwd=binary.parent
        # so the executable can locate models/ and local dll dependencies.
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(binary_path.parent),
        )

        err = (result.stderr or "").strip()
        out = (result.stdout or "").strip()
        
        if result.returncode != 0:
            raise RuntimeError(
                f"realesrgan failed (code {result.returncode}).\n"
                f"Command: {' '.join(cmd)}\n"
                f"Working directory: {binary_path.parent}\n"
                f"STDERR:\n{err}\n"
                f"STDOUT:\n{out}"
            )

        # Check both absolute and original paths (in case of path resolution issues)
        if not abs_output.exists() and not output_path.exists():
            # List files in output directory for debugging
            output_dir_files = list(output_path.parent.glob("*")) if output_path.parent.exists() else []
            # Also check the working directory in case file was written there
            cwd_files = list(binary_path.parent.glob("*.png")) if binary_path.parent.exists() else []
            raise RuntimeError(
                f"realesrgan did not produce output file: {abs_output}\n"
                f"Command: {' '.join(cmd)}\n"
                f"Working directory: {binary_path.parent}\n"
                f"Return code: {result.returncode}\n"
                f"STDERR: {err}\n"
                f"STDOUT: {out}\n"
                f"Files in output directory: {[str(f) for f in output_dir_files]}\n"
                f"PNG files in working directory: {[str(f) for f in cwd_files]}"
            )

    except subprocess.TimeoutExpired:
        raise RuntimeError("realesrgan-ncnn-vulkan timed out")
