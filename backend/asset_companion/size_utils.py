"""Size calculation utilities for asset dimensions."""
from typing import Tuple, Optional


def round_to_power_of_two(value: int) -> int:
    """
    Round value to nearest power of 2.
    
    Args:
        value: Input value
        
    Returns:
        Nearest power of 2
    """
    if value <= 0:
        return 1
    # Find nearest power of 2
    power = 1
    while power < value:
        power <<= 1
    # Choose closer: power or power // 2
    if power - value < value - (power // 2):
        return power
    else:
        return power // 2 if power // 2 > 0 else 1


def round_to_multiple(value: int, multiple: int) -> int:
    """
    Round value to nearest multiple.
    
    Args:
        value: Input value
        multiple: Multiple to round to (e.g., 8)
        
    Returns:
        Nearest multiple
    """
    if value <= 0:
        return multiple
    return round(value / multiple) * multiple


def auto_suggest_size(
    width: int,
    height: int,
    prefer_power_of_two: bool = True
) -> Tuple[int, int]:
    """
    Auto-suggest output size based on input dimensions.
    
    Tries to preserve aspect ratio while rounding to convenient values.
    Prefers power of 2, but falls back to multiple of 8 if aspect ratio
    would be too distorted.
    
    Args:
        width: Input width
        height: Input height
        prefer_power_of_two: If True, prefer power of 2; else prefer multiple of 8
        
    Returns:
        (suggested_width, suggested_height) tuple
    """
    if width <= 0 or height <= 0:
        return (256, 256)
    
    aspect = width / height
    long_side = max(width, height)
    
    if prefer_power_of_two:
        # Try power of 2 for long side
        suggested_long = round_to_power_of_two(long_side)
    else:
        # Use multiple of 8
        suggested_long = round_to_multiple(long_side, 8)
    
    # Calculate other side maintaining aspect ratio
    if width >= height:
        suggested_w = suggested_long
        suggested_h = max(8, round(suggested_w / aspect))
    else:
        suggested_h = suggested_long
        suggested_w = max(8, round(suggested_h * aspect))
    
    # Round both to multiple of 8 for consistency
    suggested_w = round_to_multiple(suggested_w, 8)
    suggested_h = round_to_multiple(suggested_h, 8)
    
    return (suggested_w, suggested_h)


def calculate_target_size(
    width: int,
    height: int,
    mode: str = "auto",
    custom_width: Optional[int] = None,
    custom_height: Optional[int] = None,
    multiple: int = 8
) -> Tuple[int, int]:
    """
    Calculate target size based on mode and input dimensions.
    
    Args:
        width: Input width
        height: Input height
        mode: Size calculation mode:
            - "auto": Auto-suggest based on input (prefers power of 2)
            - "power_of_two": Round to nearest power of 2
            - "multiple": Round to nearest multiple (default: 8)
            - "custom": Use custom_width and custom_height
        custom_width: Custom width (used if mode="custom")
        custom_height: Custom height (used if mode="custom")
        multiple: Multiple for "multiple" mode (default: 8)
        
    Returns:
        (target_width, target_height) tuple
    """
    if mode == "custom":
        if custom_width is None or custom_height is None:
            raise ValueError("custom_width and custom_height required for custom mode")
        return (custom_width, custom_height)
    
    if mode == "power_of_two":
        aspect = width / height if height > 0 else 1.0
        long_side = max(width, height)
        suggested_long = round_to_power_of_two(long_side)
        
        if width >= height:
            target_w = suggested_long
            target_h = max(8, round_to_power_of_two(round(target_w / aspect)))
        else:
            target_h = suggested_long
            target_w = max(8, round_to_power_of_two(round(target_h * aspect)))
        
        return (target_w, target_h)
    
    if mode == "multiple":
        aspect = width / height if height > 0 else 1.0
        long_side = max(width, height)
        suggested_long = round_to_multiple(long_side, multiple)
        
        if width >= height:
            target_w = suggested_long
            target_h = max(multiple, round_to_multiple(round(target_w / aspect), multiple))
        else:
            target_h = suggested_long
            target_w = max(multiple, round_to_multiple(round(target_h * aspect), multiple))
        
        return (target_w, target_h)
    
    # Default: auto mode
    return auto_suggest_size(width, height, prefer_power_of_two=True)

