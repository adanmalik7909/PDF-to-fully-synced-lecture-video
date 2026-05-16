import os
import fitz  # PyMuPDF
from PIL import Image
import io
from app.utils.logger import log_info, log_error
from app.config import settings

class DiagramExtractor:
    def __init__(self, output_dir=None):
        self.output_dir = output_dir or os.path.join(settings.STATIC_ASSETS_DIR, "extracted_diagrams")
        os.makedirs(self.output_dir, exist_ok=True)

    def extract_from_pdf(self, pdf_path: str):
        """
        Extract images from PDF and classify them.
        Returns a list of dicts: {page, path, type, bbox, caption}
        """
        results = []
        try:
            doc = fitz.open(pdf_path)
            for page_num in range(len(doc)):
                page = doc[page_num]
                image_list = page.get_images(full=True)
                
                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    
                    # Convert to PIL Image for analysis
                    pil_img = Image.open(io.BytesIO(image_bytes))
                    width, height = pil_img.size
                    
                    # Basic Heuristics for Classification
                    img_type = self._classify_image(pil_img)
                    
                    # Get bounding box (not always easy with xref, but we can try)
                    # For simplicity, we'll use a placeholder or try to find where it's used on page
                    bbox = self._find_image_bbox(page, xref)
                    
                    # Get nearby text as caption
                    caption = self._get_nearby_text(page, bbox) if bbox else ""
                    
                    # Save image
                    filename = f"page_{page_num+1}_img_{img_index}.{image_ext}"
                    filepath = os.path.join(self.output_dir, filename)
                    pil_img.save(filepath)
                    
                    results.append({
                        "page": page_num + 1,
                        "path": filepath,
                        "type": img_type,
                        "bbox": bbox,
                        "caption": caption
                    })
                    
            doc.close()
        except Exception as e:
            log_error(f"Error extracting diagrams: {e}")
            
        return results

    def _classify_image(self, pil_img):
        width, height = pil_img.size
        aspect_ratio = width / height
        
        # Heuristics
        if aspect_ratio > 1.2 and aspect_ratio < 2.5:
            # Broadly generic
            if self._is_low_variance(pil_img):
                return "diagram"
            return "photo"
        elif aspect_ratio >= 2.5:
            return "table" if self._is_low_variance(pil_img) else "banner"
        elif aspect_ratio <= 0.8:
            return "chart" if self._is_low_variance(pil_img) else "photo"
        
        return "diagram"

    def _is_low_variance(self, pil_img):
        # Convert to grayscale and check variance
        gray = pil_img.convert("L")
        import numpy as np
        arr = np.array(gray)
        return np.std(arr) < 50 # Heuristic threshold for "clean" diagrams/tables

    def _find_image_bbox(self, page, xref):
        # PyMuPDF can find where an xref is displayed on a page
        for item in page.get_image_info(xrefs=True):
            if item['xref'] == xref:
                return item['bbox']
        return None

    def _get_nearby_text(self, page, bbox, distance=30):
        if not bbox: return ""
        # Search for text in a slightly larger area than the image
        search_area = (bbox[0], bbox[1] - distance, bbox[2], bbox[3] + distance)
        words = page.get_text("words", clip=search_area)
        # Sort words by position
        words.sort(key=lambda w: (w[3], w[0])) # sort by y1 then x0
        return " ".join([w[4] for w in words])
