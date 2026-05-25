"""
Pipeline End-to-End Test Script
================================
Run from the backend/ directory WHILE the server is running:

    python scripts/test_pipeline.py

Requires: a small PDF in the same folder (creates one automatically).
"""
import os
import sys
import time
import json
import requests

BASE = "http://localhost:8000/api/blueprint"

# ── Helpers ────────────────────────────────────────────────────────────────────
def ok(label, resp):
    if resp.status_code not in (200, 201):
        print(f"  [FAIL]  {label}  [{resp.status_code}]  {resp.text[:200]}")
        return False
    print(f"  [OK]  {label}  [{resp.status_code}]")
    return True

def create_dummy_pdf(path):
    """Create a minimal single-page PDF for testing."""
    try:
        from reportlab.pdfgen import canvas
        c = canvas.Canvas(path)
        c.setFont("Helvetica", 14)
        c.drawString(72, 720, "Introduction to Machine Learning")
        c.drawString(72, 690, "Machine learning is a subset of artificial intelligence.")
        c.drawString(72, 670, "Key algorithms include linear regression, neural networks,")
        c.drawString(72, 650, "and decision trees. Real-world applications span medicine,")
        c.drawString(72, 630, "finance, and autonomous vehicles.")
        c.save()
        return True
    except Exception as e:
        print(f"  [WARN] Could not create PDF via reportlab: {e}")
        return False


def main():
    print("=" * 60)
    print("  SmartStudyInstructor — V14 Pipeline Integration Test")
    print("=" * 60)

    # ── Step 0: Create test PDF ───────────────────────────────────────────────
    pdf_path = os.path.join(os.path.dirname(__file__), "test_lecture.pdf")
    if not os.path.exists(pdf_path):
        if not create_dummy_pdf(pdf_path):
            # Fallback: use any PDF in static/uploads/pdfs
            uploads = os.path.join(os.path.dirname(__file__), "..", "static", "uploads", "pdfs")
            pdfs = [f for f in os.listdir(uploads) if f.endswith(".pdf")] if os.path.exists(uploads) else []
            if pdfs:
                pdf_path = os.path.join(uploads, pdfs[0])
                print(f"Using existing PDF: {pdf_path}")
            else:
                print("[FAIL] No PDF available for testing. Install reportlab or place a PDF in static/uploads/pdfs/")
                sys.exit(1)

    print(f"\n[1] GENERATE DRAFT — {os.path.basename(pdf_path)}")
    with open(pdf_path, "rb") as f:
        r = requests.post(f"{BASE}/generate-draft", files={"file": (os.path.basename(pdf_path), f, "application/pdf")})
    if not ok("POST /generate-draft", r):
        sys.exit(1)
    
    data = r.json()
    blueprint = data.get("blueprint")
    if not blueprint:
        print("[FAIL] Blueprint not returned.")
        sys.exit(1)
    
    scenes_count = len(blueprint.get("scenes", []))
    print(f"     Blueprint generated with {scenes_count} scenes.")

    print(f"\n[2] ASSEMBLE VIDEO")
    r = requests.post(f"{BASE}/assemble", data={"blueprint_data": json.dumps(blueprint)})
    if not ok("POST /assemble", r):
        sys.exit(1)
        
    job_id = r.json().get("job_id")
    print(f"     job_id = {job_id}")

    print("     Polling video status…")
    start = time.time()
    while time.time() - start < 300:
        r = requests.get(f"{BASE}/status/{job_id}")
        s = r.json()
        status = s.get('status')
        progress = s.get('progress', 0)
        current_step = s.get('current_step', '')
        
        print(f"     [{int(time.time()-start)}s] {status}  {progress}%  — {current_step}")
        if status == "completed":
            print(f"\n  [OK]  video_url = {s.get('video_url')}")
            break
        if status == "failed":
            print(f"\n  [FAIL]  Video failed: {s.get('error')}")
            break
        time.sleep(5)

    print("\n" + "=" * 60)
    print("  Test Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
