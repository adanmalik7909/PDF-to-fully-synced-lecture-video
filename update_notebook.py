import json
import os

notebook_path = r"c:\Users\PMLS\Desktop\Prototype\SmartStudyInstructor\Kaggle_Cloud_Engine.ipynb"

# Exact code for Cell 1
cell_1_code = """# ============================================================
# CELL 1 — SETUP (Run this FIRST, wait for it to finish)
# ============================================================
import os, shutil

print("🔧 Step 1/5: Installing system tools...")
!apt-get install -qq -y ffmpeg 2>/dev/null

print("\\n📦 Step 2/5: Cloning Wav2Lip...")
os.chdir("/kaggle/working")

# If Wav2Lip exists but inference.py is missing, it's corrupted. Delete it.
if os.path.exists("Wav2Lip") and not os.path.exists("Wav2Lip/inference.py"):
    print("  🗑️ Found corrupted Wav2Lip folder. Deleting and re-cloning...")
    shutil.rmtree("Wav2Lip")

if not os.path.exists("Wav2Lip"):
    !git clone https://github.com/Rudrabha/Wav2Lip.git
    print("  ✅ Wav2Lip cloned")
else:
    print("  ✅ Wav2Lip already exists")

# Verify the critical file exists
assert os.path.exists("Wav2Lip/inference.py"), "❌ inference.py NOT FOUND!"
print("  ✅ inference.py verified")

# Create temp directory that Wav2Lip needs
os.makedirs("Wav2Lip/temp", exist_ok=True)
os.makedirs("Wav2Lip/checkpoints", exist_ok=True)

print("\\n📥 Step 3/5: Downloading model weights...")
CKPT = "Wav2Lip/checkpoints/wav2lip_gan.pth"
if not os.path.exists(CKPT) or os.path.getsize(CKPT) < 100_000_000:
    if os.path.exists(CKPT):
        os.remove(CKPT)
    !wget -q 'https://huggingface.co/camenduru/Wav2Lip/resolve/main/checkpoints/wav2lip_gan.pth' -O {CKPT}

if os.path.exists(CKPT) and os.path.getsize(CKPT) > 100_000_000:
    print(f"  ✅ Checkpoint OK: {os.path.getsize(CKPT)/1e6:.1f} MB")
else:
    print("  ❌ Checkpoint download FAILED!")

# s3fd face detection weights
SFD = "Wav2Lip/face_detection/detection/sfd/s3fd.pth"
if not os.path.exists(SFD) or os.path.getsize(SFD) < 1_000_000:
    os.makedirs(os.path.dirname(SFD), exist_ok=True)
    !wget -q 'https://www.adrianbulat.com/downloads/python-fan/s3fd-619a316812.pth' -O {SFD}
    print(f"  ✅ s3fd weights OK")

print("\\n⚙️ Step 4/5: Installing Python packages...")
# Install only flask and pyngrok to avoid downgrading pre-installed numpy/scipy/librosa/torch
!pip install -q flask pyngrok

print("\\n🔧 Step 5/5: Patching Wav2Lip for compatibility...")

# 1. Patch inference.py for PyTorch 2.x
inf_path = "Wav2Lip/inference.py"
if os.path.exists(inf_path):
    with open(inf_path, "r") as f:
        code = f.read()
    patched = False
    if "torch.load(checkpoint_path)" in code:
        code = code.replace(
            "checkpoint = torch.load(checkpoint_path)",
            "checkpoint = torch.load(checkpoint_path, map_location='cpu', weights_only=False)"
        )
        patched = True
    if 'checkpoint = torch.load(checkpoint_path, map_location="cuda")' in code:
        code = code.replace(
            'checkpoint = torch.load(checkpoint_path, map_location="cuda")',
            "checkpoint = torch.load(checkpoint_path, map_location='cpu', weights_only=False)"
        )
        patched = True
    if "checkpoint = torch.load(args.checkpoint_path)" in code:
        code = code.replace(
            "checkpoint = torch.load(args.checkpoint_path)",
            "checkpoint = torch.load(args.checkpoint_path, map_location='cpu', weights_only=False)"
        )
        patched = True
    with open(inf_path, "w") as f:
        f.write(code)
    if patched:
        print("  ✅ Patched torch.load for PyTorch 2.x")

# 2. Patch audio.py for newer librosa using robust regex
audio_path = "Wav2Lip/audio.py"
if os.path.exists(audio_path):
    with open(audio_path, "r") as f:
        acode = f.read()
    patched_audio = False
    
    if "sr=hp.sample_rate" in acode:
        patched_audio = True
        print("  ✅ audio.py already patched for librosa compatibility")
    else:
        import re
        # Match librosa.filters.mel with any spacing/newlines
        pattern = r'librosa\\.filters\\.mel\\(\\s*hp\\.sample_rate\\s*,\\s*hp\\.n_fft\\s*,'
        if re.search(pattern, acode):
            acode = re.sub(pattern, 'librosa.filters.mel(sr=hp.sample_rate, n_fft=hp.n_fft,', acode)
            patched_audio = True
            with open(audio_path, "w") as f:
                f.write(acode)
            print("  ✅ Patched audio.py for librosa compatibility")
        else:
            # Fallback: check if we have librosa.filters.mel with other names or styles
            fallback_pattern = r'librosa\\.filters\\.mel\\([^)]+\\)'
            matches = re.findall(fallback_pattern, acode)
            if matches:
                for match in matches:
                    if "sr=" not in match and "n_fft=" not in match:
                        fixed_match = match.replace("hp.sample_rate", "sr=hp.sample_rate").replace("hp.n_fft", "n_fft=hp.n_fft")
                        acode = acode.replace(match, fixed_match)
                        patched_audio = True
                if patched_audio:
                    with open(audio_path, "w") as f:
                        f.write(acode)
                    print("  ✅ Patched audio.py for librosa compatibility (fallback)")

    if not patched_audio:
        print("  ❌ Could not patch audio.py mel call! Printing file's mel call lines for debug:")
        for line in acode.splitlines():
            if "mel(" in line:
                print("  ", line)

# 3. Patch numpy 2.x deprecated aliases
import glob, re
patched_numpy_count = 0
for filepath in glob.glob("Wav2Lip/**/*.py", recursive=True):
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            file_code = f.read()
        
        modified = False
        if "np.float" in file_code:
            file_code = file_code.replace("np.float", "float")
            modified = True
        if "np.int" in file_code:
            file_code, count = re.subn(r'\\bnp\\.int\\b', 'int', file_code)
            if count > 0:
                modified = True
        if "np.bool" in file_code:
            file_code = file_code.replace("np.bool", "bool")
            modified = True
            
        if modified:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(file_code)
            patched_numpy_count += 1
    except Exception as e:
        print(f"  ❌ Error patching numpy in {filepath}: {e}")

if patched_numpy_count > 0:
    print(f"  ✅ Patched {patched_numpy_count} files for NumPy 2.0 compatibility")

# Quick checkpoint verify
import torch
try:
    ckpt = torch.load(CKPT, map_location='cpu', weights_only=False)
    print(f"  ✅ Checkpoint loads correctly")
    del ckpt
except Exception as e:
    print(f"  ❌ Checkpoint load FAILED: {e}")

print("\\n" + "="*50)
print("✅ SETUP COMPLETE — Now run Cell 2")
print("="*50)"""

# Exact code for Cell 2
cell_2_code = """# ============================================================
# CELL 2 — LIPSYNC SERVER (Run AFTER Cell 1 finishes)
# ============================================================
import os, sys, base64, subprocess, traceback, threading
from flask import Flask, request, jsonify
from PIL import Image

# ╔══════════════════════════════════════════════════════════╗
# ║  👉 PASTE YOUR NGROK TOKEN BELOW                        ║
# ╚══════════════════════════════════════════════════════════╝
NGROK_TOKEN = "3BZaGFS85TRNgCpNbFcjoTR0V5P_7KPvvJ52uQrtESVeEXAg9"

# ── Configuration ──
JOBS_DIR = "/kaggle/working/lipsync_jobs"
WAV2LIP_DIR = "/kaggle/working/Wav2Lip"
CHECKPOINT = os.path.join(WAV2LIP_DIR, "checkpoints", "wav2lip_gan.pth")

os.makedirs(JOBS_DIR, exist_ok=True)
os.makedirs(os.path.join(WAV2LIP_DIR, "temp"), exist_ok=True)

# Verify setup
assert os.path.exists(os.path.join(WAV2LIP_DIR, "inference.py")), \\
    "❌ Wav2Lip/inference.py NOT FOUND! Run Cell 1 first!"
assert os.path.exists(CHECKPOINT), \\
    "❌ Checkpoint NOT FOUND! Run Cell 1 first!"
print("✅ Wav2Lip verified")

# Only 1 scene at a time (prevents GPU race conditions)
inference_lock = threading.Lock()

app = Flask(__name__)

def prepare_avatar(src, dst, size=720):
    \"\"\"Resize avatar to square for Wav2Lip face detection.\"\"\"
    img = Image.open(src).convert("RGB")
    w, h = img.size
    scale = min(size/w, size/h)
    nw, nh = int(w*scale), int(h*scale)
    img = img.resize((nw, nh), Image.LANCZOS)
    canvas = Image.new("RGB", (size, size), (0,0,0))
    canvas.paste(img, ((size-nw)//2, (size-nh)//2))
    canvas.save(dst, "PNG")
    print(f"  🖼️ Avatar: {w}x{h} → {size}x{size}")

import sys
sys.path.append(WAV2LIP_DIR)

print("\\n🔧 Patching inference.py for persistent VRAM caching...")
inf_path = os.path.join(WAV2LIP_DIR, "inference.py")
if os.path.exists(inf_path):
    with open(inf_path, "r") as f: code = f.read()
    if "_GLOBAL_MODEL = None" not in code:
        code = code.replace("def load_model(path):", "_GLOBAL_MODEL = None\\n_GLOBAL_DETECTOR = None\\ndef load_model(path):\\n\\tglobal _GLOBAL_MODEL\\n\\tif _GLOBAL_MODEL is not None: return _GLOBAL_MODEL")
        code = code.replace("return model.eval()", "_GLOBAL_MODEL = model.eval()\\n\\treturn _GLOBAL_MODEL")
        code = code.replace("face_detector = face_detection.FaceAlignment(face_detection.LandmarksType._2D, ", "global _GLOBAL_DETECTOR\\n\\tif _GLOBAL_DETECTOR is None:\\n\\t\\t_GLOBAL_DETECTOR = face_detection.FaceAlignment(face_detection.LandmarksType._2D, ")
        code = code.replace("device=device)", "device=device)\\n\\tface_detector = _GLOBAL_DETECTOR")
        with open(inf_path, "w") as f: f.write(code)
        print("  ✅ Persistent cache patch applied.")

def run_wav2lip(scene_id, audio_path, avatar_path, output_mp4):
    \"\"\"Run Wav2Lip inference using in-memory model.\"\"\"
    temp_dir = os.path.join(WAV2LIP_DIR, "temp")
    for f in os.listdir(temp_dir):
        try: os.remove(os.path.join(temp_dir, f))
        except: pass
    
    prep = os.path.join(JOBS_DIR, f"{scene_id}_prep.png")
    prepare_avatar(avatar_path, prep)
    
    print(f"  🚀 Running In-Memory Wav2Lip Inference...")
    
    import sys
    # Mock sys.argv so inference.py's top-level parser doesn't crash on initial import
    old_argv = sys.argv
    sys.argv = [
        "inference.py", 
        "--checkpoint_path", os.path.join(WAV2LIP_DIR, "checkpoints", "wav2lip_gan.pth"),
        "--face", prep,
        "--audio", audio_path
    ]
    
    import inference
    import argparse
    
    sys.argv = old_argv
    
    # Fully populated namespace with all required Wav2Lip defaults
    args = argparse.Namespace(
        checkpoint_path=os.path.join(WAV2LIP_DIR, "checkpoints", "wav2lip_gan.pth"),
        face=prep,
        audio=audio_path,
        outfile=output_mp4,
        pads=[0, 10, 0, 0],
        resize_factor=1,
        nosmooth=True,
        fps=25.0,
        box=[-1, -1, -1, -1],
        static=False,
        img_size=96,
        face_det_batch_size=16,
        wav2lip_batch_size=128,
        crop=[0, -1, 0, -1],
        rotate=False
    )
    
    try:
        inference.args = args
        old_cwd = os.getcwd()
        os.chdir(WAV2LIP_DIR)
        inference.main()
        os.chdir(old_cwd)
    except Exception as e:
        print(f"  ❌ Inference Exception: {e}")
        os.chdir(old_cwd)
        return False
    
    if os.path.exists(output_mp4) and os.path.getsize(output_mp4) > 1000:
        print(f"  ✅ Video: {os.path.getsize(output_mp4)} bytes")
        return True
    
    return False


@app.route("/health")
def health():
    import torch
    gpu = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"
    return jsonify({"status": "online", "gpu_name": gpu})

@app.route("/clear_cache")
def clear_cache():
    import torch, gc
    gc.collect()
    if torch.cuda.is_available(): torch.cuda.empty_cache()
    return jsonify({"status": "cleared"})

@app.route("/generate_lipsync", methods=["POST"])
def generate_lipsync():
    try:
        data = request.json
        scene_id = data.get("scene_id", "scene_01")
        
        # Save audio
        audio_path = os.path.join(JOBS_DIR, f"{scene_id}.wav")
        with open(audio_path, "wb") as f:
            f.write(base64.b64decode(data["audio_base64"]))
        print(f"  📁 Audio: {os.path.getsize(audio_path)} bytes")
        
        # Save avatar
        avatar_path = os.path.join(JOBS_DIR, f"{scene_id}_avatar.png")
        with open(avatar_path, "wb") as f:
            f.write(base64.b64decode(data["avatar_image_base64"]))
        print(f"  📁 Avatar: {os.path.getsize(avatar_path)} bytes")
        
        output_mp4 = os.path.join(JOBS_DIR, f"{scene_id}_sync.mp4")
        
        # Serialize GPU access
        print(f"🎬 {scene_id}: waiting for GPU...")
        with inference_lock:
            print(f"  🔓 GPU acquired")
            ok = run_wav2lip(scene_id, audio_path, avatar_path, output_mp4)
        
        if not ok:
            raise Exception(f"Wav2Lip produced no output for {scene_id}")
        
        with open(output_mp4, "rb") as f:
            video_b64 = base64.b64encode(f.read()).decode()
        
        print(f"  ✅ {scene_id} complete!")
        return jsonify({"status": "success", "lipsync_video_base64": video_b64})
        
    except Exception as e:
        print(f"🔥 Error: {traceback.format_exc()}")
        return jsonify({"status": "error", "error_message": str(e)}), 500

# ── Start Server ──
from pyngrok import ngrok

try:
    from kaggle_secrets import UserSecretsClient
    token = UserSecretsClient().get_secret("NGROK_AUTH_TOKEN") or NGROK_TOKEN
except:
    token = NGROK_TOKEN

if not token or "paste_your" in token:
    print("❌ Paste your ngrok token in NGROK_TOKEN variable!")
else:
    ngrok.set_auth_token(token)
    try:
        for t in ngrok.get_tunnels(): ngrok.disconnect(t.public_url)
    except: pass
    tunnel = ngrok.connect(5000)
    url = tunnel.public_url
    # Handle both string and NgrokTunnel object
    if hasattr(tunnel, 'public_url'):
        url = tunnel.public_url
    else:
        url = str(tunnel)
    # Extract clean URL if it contains extra text
    if 'https://' in url:
        import re
        match = re.search(r'(https://[^\\s\\"]+\\.ngrok[^\\s\\"]*)', url)
        if match:
            url = match.group(1)
    print(f"\\n🚀 PUBLIC URL: {url}")
    print(f"\\n📋 Paste in backend/.env:")
    print(f"   CLOUD_RENDER_URL={url}")
    app.run(host="0.0.0.0", port=5000)"""

# Load existing notebook
with open(notebook_path, "r", encoding="utf-8") as f:
    notebook = json.load(f)

# Convert multiline strings to list of lines with trailing \n (except last one)
def to_ipynb_source(code_str):
    lines = code_str.split("\n")
    source_lines = []
    for i, line in enumerate(lines):
        if i == len(lines) - 1:
            source_lines.append(line)
        else:
            source_lines.append(line + "\n")
    return source_lines

# Update cells
notebook["cells"][1]["source"] = to_ipynb_source(cell_1_code)
notebook["cells"][2]["source"] = to_ipynb_source(cell_2_code)

# Save notebook back
with open(notebook_path, "w", encoding="utf-8") as f:
    json.dump(notebook, f, indent=1, ensure_ascii=False)

print("SUCCESS: Kaggle_Cloud_Engine.ipynb has been permanently updated!")
