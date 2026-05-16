"""PDF → Slide Images Utility
Renders each page of a PDF as a PNG image suitable for use as video slides.
Uses PyMuPDF (fitz) — already in requirements.txt.
"""
import os
from typing import List
from app.utils.logger import log_info, log_error

# Target slide dimensions (16:9 aspect for video)
SLIDE_WIDTH = 1280
SLIDE_HEIGHT = 720
DPI_SCALE = 2.0  # render at 2× then resize → sharper text


def pdf_to_slide_images(pdf_path: str, output_dir: str) -> List[str]:
    """Render every page of *pdf_path* to a PNG in *output_dir*.

    Returns a list of absolute paths to the generated images in page order.
    Falls back to a generated placeholder slide if fitz is unavailable.
    """
    os.makedirs(output_dir, exist_ok=True)
    image_paths: List[str] = []

    try:
        import fitz  # PyMuPDF

        doc = fitz.open(pdf_path)
        matrix = fitz.Matrix(DPI_SCALE, DPI_SCALE)

        for page_num in range(len(doc)):
            page = doc[page_num]
            pixmap = page.get_pixmap(matrix=matrix, colorspace=fitz.csRGB)

            # Save raw render
            raw_path = os.path.join(output_dir, f"slide_{page_num:03d}_raw.png")
            pixmap.save(raw_path)

            # Resize to target 1280×720
            final_path = os.path.join(output_dir, f"slide_{page_num:03d}.png")
            _resize_image(raw_path, final_path, SLIDE_WIDTH, SLIDE_HEIGHT)
            os.remove(raw_path)

            image_paths.append(final_path)
            log_info(f"[PDF->IMG] Page {page_num + 1}/{len(doc)} -> {final_path}")

        doc.close()
        log_info(f"[PDF->IMG] Done: {len(image_paths)} slides from {pdf_path}")

    except ImportError:
        log_error("[PDF→IMG] fitz (PyMuPDF) not available — generating placeholder slides")
        image_paths = _make_placeholder_slides(output_dir, count=1)

    except Exception as e:
        log_error(f"[PDF→IMG] Error: {e}")
        if not image_paths:
            image_paths = _make_placeholder_slides(output_dir, count=1)

    return image_paths


def _resize_image(src: str, dst: str, width: int, height: int) -> None:
    """Resize image to *width × height* with letterboxing/pillarboxing."""
    try:
        from PIL import Image
        img = Image.open(src).convert("RGB")
        img.thumbnail((width, height), Image.LANCZOS)

        # Paste onto background canvas
        canvas = Image.new("RGB", (width, height), (30, 30, 35))  # dark bg
        x = (width - img.width) // 2
        y = (height - img.height) // 2
        canvas.paste(img, (x, y))
        canvas.save(dst, "PNG", optimize=True)
    except Exception as e:
        log_error(f"[PDF→IMG] resize error: {e} — copying as-is")
        import shutil
        shutil.copy2(src, dst)


def _make_placeholder_slides(output_dir: str, count: int = 1) -> List[str]:
    """Generate simple placeholder slides when PDF rendering is unavailable."""
    paths = []
    try:
        from PIL import Image, ImageDraw, ImageFont
        for i in range(count):
            img = Image.new("RGB", (SLIDE_WIDTH, SLIDE_HEIGHT), (20, 20, 40))
            draw = ImageDraw.Draw(img)
            draw.rectangle([(40, 40), (SLIDE_WIDTH - 40, SLIDE_HEIGHT - 40)],
                           outline=(102, 126, 234), width=3)
            draw.text((SLIDE_WIDTH // 2, SLIDE_HEIGHT // 2),
                      f"Slide {i + 1}",
                      fill=(255, 255, 255), anchor="mm")
            p = os.path.join(output_dir, f"slide_{i:03d}.png")
            img.save(p, "PNG")
            paths.append(p)
    except Exception as e:
        log_error(f"[PDF→IMG] placeholder generation failed: {e}")
    return paths
