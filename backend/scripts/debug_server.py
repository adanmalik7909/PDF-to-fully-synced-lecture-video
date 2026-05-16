import sys
import os
import subprocess
import time
import requests

def test_startup():
    print("--- Diagnostic: Server Startup Test ---")
    
    # Try to import app.main
    try:
        sys.path.append(os.path.join(os.getcwd(), "backend"))
        os.chdir("backend")
        from app.main import app
        print("Import app.main: OK")
    except Exception as e:
        print(f"Import app.main: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return

    # Try to start uvicorn in a subprocess and capture output
    print("Starting uvicorn...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait a few seconds
    time.sleep(10)
    
    # Check if process is still alive
    if proc.poll() is not None:
        print(f"Server DIED immediately. Return code: {proc.poll()}")
        stdout, stderr = proc.communicate()
        print(f"STDOUT: {stdout}")
        print(f"STDERR: {stderr}")
    else:
        print("Server appears to be ALIVE (listening on 127.0.0.1:8000)")
        try:
            r = requests.get("http://127.0.0.1:8000/health", timeout=5)
            print(f"HEALTH CHECK: {r.status_code} - {r.json()}")
        except Exception as e:
            print(f"HEALTH CHECK: FAILED - {e}")
        
        proc.terminate()
        print("Server stopped.")

if __name__ == "__main__":
    test_startup()
