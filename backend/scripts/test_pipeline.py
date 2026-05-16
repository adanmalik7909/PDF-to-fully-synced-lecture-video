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

BASE = "http://localhost:8000/api/pipeline"

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
    print("  SmartStudyInstructor — Pipeline Integration Test")
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

    print(f"\n[1] UPLOAD — {os.path.basename(pdf_path)}")
    with open(pdf_path, "rb") as f:
        r = requests.post(f"{BASE}/upload", files={"file": (os.path.basename(pdf_path), f, "application/pdf")})
    if not ok("POST /upload", r):
        sys.exit(1)
    data = r.json()
    doc_id = data["doc_id"]
    print(f"     doc_id = {doc_id}")

    print(f"\n[2] RAG STATUS — polling for completion (max 60s)…")
    start = time.time()
    while time.time() - start < 60:
        r = requests.get(f"{BASE}/rag-status/{doc_id}")
        s = r.json()
        status = s.get("rag_status")
        print(f"     status={status}  pages={s.get('pages',0)}  chunks={s.get('chunks',0)}")
        if status == "completed":
            break
        if status == "failed":
            print("  [FAIL] RAG ingestion failed"); sys.exit(1)
        time.sleep(3)

    print(f"\n[3] GENERATE SCRIPT")
    r = requests.post(f"{BASE}/generate-script/{doc_id}")
    if not ok("POST /generate-script", r):
        # Non-fatal — may be mock
        script = "Test lecture script about machine learning fundamentals."
    else:
        script = r.json()["script"]
        wc = len(script.split())
        print(f"     {wc} words generated")

    print(f"\n[4] GENERATE AUDIO")
    r = requests.post(f"{BASE}/generate-audio",
                      json={"script": script[:500], "doc_id": doc_id},  # shorter for speed
                      headers={"Content-Type": "application/json"})
    if not ok("POST /generate-audio", r):
        print("  ⚠ Audio generation failed (check gTTS connectivity)")
    else:
        print(f"     audio_url = {r.json().get('audio_url')}")

    print(f"\n[5] GENERATE VIDEO")
    r = requests.post(f"{BASE}/generate-video/{doc_id}",
                      json={"script": script},
                      headers={"Content-Type": "application/json"})
    if not ok("POST /generate-video (start)", r):
        sys.exit(1)
    job_id = r.json()["job_id"]
    print(f"     job_id = {job_id}")

    print("     Polling video status…")
    start = time.time()
    while time.time() - start < 300:
        r = requests.get(f"{BASE}/video-status/{job_id}")
        s = r.json()
        print(f"     [{int(time.time()-start)}s] {s['status']}  {s['progress']}%  — {s['message']}")
        if s["status"] == "completed":
            print(f"\n  [OK]  video_url = {s['video_url']}")
            break
        if s["status"] == "failed":
            print(f"\n  [FAIL]  Video failed: {s['message']}")
            break
        time.sleep(5)

    print(f"\n[6] ASK Q&A")
    r = requests.post(f"{BASE}/ask",
                      json={"question": "What is machine learning?", "doc_id": doc_id},
                      headers={"Content-Type": "application/json"})
    if ok("POST /ask", r):
        answer = r.json().get("answer", "")
        print(f"     Answer ({len(answer)} chars): {answer[:150]}…")

    print("\n" + "=" * 60)
    print("  Test Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
