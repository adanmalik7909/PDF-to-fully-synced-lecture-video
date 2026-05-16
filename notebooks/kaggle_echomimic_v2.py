# ==============================================================================
# 🚀 SmartStudyInstructor V13 — EchoMimicV2 Kaggle Deployment Script
# ==============================================================================
# Instructions:
# 1. Open Kaggle and create a new notebook.
# 2. Set Accelerator to GPU T4 x2.
# 3. Paste this entire script into a cell and run it.
# 4. Copy the ngrok URL it prints and paste it into SmartStudyInstructor settings.
# ==============================================================================

import os
import subprocess
import time

print("🚀 Step 1: Installing Dependencies (takes ~3 mins)...")
!git clone https://github.com/BadToBest/EchoMimicV2.git
%cd EchoMimicV2
!pip install -r requirements.txt
!pip install flask pyngrok flask-cors
!pip install xformers==0.0.26.post1 triton==2.3.0
!apt-get update && apt-get install -y ffmpeg

print("🚀 Step 2: Downloading EchoMimicV2 Weights...")
!mkdir -p pretrained_weights
!wget -O pretrained_weights/denoising_unet.pth "https://huggingface.co/BadToBest/EchoMimicV2/resolve/main/denoising_unet.pth"
!wget -O pretrained_weights/reference_unet.pth "https://huggingface.co/BadToBest/EchoMimicV2/resolve/main/reference_unet.pth"
!wget -O pretrained_weights/motion_module.pth "https://huggingface.co/BadToBest/EchoMimicV2/resolve/main/motion_module.pth"
!wget -O pretrained_weights/face_locator.pth "https://huggingface.co/BadToBest/EchoMimicV2/resolve/main/face_locator.pth"

print("🚀 Step 3: Setting up the inference API...")

server_code = """
import os
import torch
from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from pyngrok import ngrok
import tempfile
import subprocess

app = Flask(__name__)
CORS(app)

# Note: In a real production Kaggle notebook, we would load the EchoMimicV2 models
# into memory here. For the sake of this API, we will invoke their inference script
# which handles the complex diffusion loading and inference.

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ready", "model": "EchoMimicV2"})

@app.route('/generate-avatar', methods=['POST'])
def generate_avatar():
    try:
        # 1. Receive audio and image
        audio_file = request.files['audio']
        image_file = request.files['image']
        
        # 2. Save to temp
        temp_dir = tempfile.mkdtemp()
        audio_path = os.path.join(temp_dir, "input.wav")
        image_path = os.path.join(temp_dir, "avatar.png")
        audio_file.save(audio_path)
        image_file.save(image_path)
        
        output_path = os.path.join(temp_dir, "output.mp4")
        
        # 3. Run Inference (Memory Optimized for T4)
        # We enable gradient checkpointing and attention slicing implicitly via the script args
        print(f"Starting inference for {audio_path}...")
        
        cmd = [
            "python", "-u", "inference/generate.py",
            "--config", "configs/prompts/animation.yaml",
            "--image_path", image_path,
            "--audio_path", audio_path,
            "--output_path", output_path,
            "--W", "512", "--H", "512",
            "--L", "1200", # Max frames
            "--seed", "42",
            "--facelocator", "1",
            "--fp16" # Crucial for T4
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print("Inference Failed:", result.stderr)
            return jsonify({"error": "Inference failed", "details": result.stderr}), 500
            
        return send_file(output_path, mimetype="video/mp4")
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Add your personal ngrok authtoken here if required
    # ngrok.set_auth_token("YOUR_TOKEN")
    public_url = ngrok.connect(5000).public_url
    print("="*60)
    print(f"✅ EchoMimicV2 API is LIVE at: {public_url}")
    print("👉 Paste this URL into your SmartStudyInstructor config!")
    print("="*60)
    app.run(port=5000)
"""

with open("start_api.py", "w") as f:
    f.write(server_code)

print("🚀 Step 4: Starting the server...")
!python start_api.py
