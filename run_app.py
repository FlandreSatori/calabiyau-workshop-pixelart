import subprocess
import sys
import os
import time

def main():
    print("Starting FastAPI backend...")
    # Get python executable to ensure we use the same venv
    python_exe = sys.executable
    
    # Start backend
    backend_proc = subprocess.Popen(
        [python_exe, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000", "--reload"],
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    
    print("Starting Tauri frontend...")
    # Start frontend
    frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")
    
    frontend_proc = None
    try:
        # Give backend a moment to start
        time.sleep(2)
        frontend_proc = subprocess.Popen(
            ["npm", "run", "tauri", "dev"],
            cwd=frontend_dir,
            shell=True
        )
        
        frontend_proc.wait()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        if frontend_proc:
            if sys.platform == 'win32':
                os.system(f"taskkill /F /T /PID {frontend_proc.pid}")
            else:
                frontend_proc.terminate()
        
        if backend_proc:
            if sys.platform == 'win32':
                os.system(f"taskkill /F /T /PID {backend_proc.pid}")
            else:
                backend_proc.terminate()

if __name__ == "__main__":
    main()
