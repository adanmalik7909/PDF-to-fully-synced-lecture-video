# -*- coding: utf-8 -*-
"""
SmartStudyInstructor V14 — Camera Utilities
Computes GSAP camera scaling and translation parameters for centering a diagram region.
"""
from typing import Dict

def compute_camera_params(bbox: dict, canvas_w: float = 1920.0, canvas_h: float = 1080.0, margin: float = 0.12) -> dict:
    """
    Takes a region's normalized bounding box (where x_pct, y_pct, w_pct, h_pct are 0.0 - 1.0)
    and computes the target scale and translation values.
    
    Assumes standard canvas dimensions (canvas_w x canvas_h).
    """
    # Map keys from x_pct/y_pct or bbox dict/list formats
    x_pct = bbox.get("x_pct", 0.0)
    y_pct = bbox.get("y_pct", 0.0)
    w_pct = bbox.get("w_pct", 0.2)
    h_pct = bbox.get("h_pct", 0.2)
    
    # Handle alternative bbox dict format {x, y, width, height}
    if "x" in bbox:
        x_pct = bbox["x"]
    if "y" in bbox:
        y_pct = bbox["y"]
    if "width" in bbox:
        w_pct = bbox["width"]
    if "height" in bbox:
        h_pct = bbox["height"]
        
    # Prevent divide-by-zero
    w_pct = max(w_pct, 0.02)
    h_pct = max(h_pct, 0.02)
    
    # Calculate scale to fit the region within the viewport with a margin
    scale_x = (1.0 - 2.0 * margin) / w_pct
    scale_y = (1.0 - 2.0 * margin) / h_pct
    scale = min(scale_x, scale_y)
    
    # Clamp scale between sensible range
    scale = min(max(scale, 1.2), 3.5)
    
    # Compute center point of the region relative to the diagram image (0.0 - 1.0)
    ncx = x_pct + w_pct / 2.0
    ncy = y_pct + h_pct / 2.0
    
    # Target position translates the viewport to align the region center with the screen center (0.5).
    # Since GSAP transforms are relative to center-origin:
    # tx = (viewport_center - region_center) * viewport_size * scale
    tx = (0.5 - ncx) * canvas_w * scale
    ty = (0.5 - ncy) * canvas_h * scale
    
    # Optional bounding: do not pan completely off the diagram edges
    max_tx = (canvas_w * (scale - 1.0)) / 2.0
    max_ty = (canvas_h * (scale - 1.0)) / 2.0
    tx = max(-max_tx, min(max_tx, tx))
    ty = max(-max_ty, min(max_ty, ty))
    
    return {
        "scale": round(scale, 2),
        "x": round(tx, 1),
        "y": round(ty, 1),
        "assumed_width": canvas_w,
        "assumed_height": canvas_h
    }

def compute_connector_pixel_path(path_normalized: list, canvas_w: float = 1920.0, canvas_h: float = 1080.0) -> list:
    """
    Converts a normalized connector path (points in 0.0 - 1.0)
    into absolute pixel coordinates relative to the canvas size.
    """
    pixel_path = []
    if not path_normalized:
        return pixel_path
    for pt in path_normalized:
        if isinstance(pt, dict):
            x = pt.get("x", 0.0)
            y = pt.get("y", 0.0)
        elif isinstance(pt, (list, tuple)) and len(pt) >= 2:
            x, y = pt[0], pt[1]
        else:
            continue
        pixel_path.append({
            "x": round(x * canvas_w, 1),
            "y": round(y * canvas_h, 1)
        })
    return pixel_path

