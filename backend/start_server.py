import asyncio
import sys
import uvicorn
import os

if __name__ == "__main__":
    # CRITICAL: This must be set before any event loop starts
    if sys.platform == 'win32':
        print("Setting Windows ProactorEventLoopPolicy...")
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    # Ensure we are in the correct directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Run Uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
