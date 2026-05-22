import subprocess
import sys
import os
import time
import ctypes
import threading


def is_admin() -> bool:
    if sys.platform != "win32":
        return True
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def relaunch_as_admin() -> None:
    if sys.platform != "win32" or is_admin():
        return

    script_path = os.path.abspath(__file__)
    if getattr(sys, "frozen", False):
        executable = sys.executable
        params = subprocess.list2cmdline(sys.argv[1:])
    else:
        executable = sys.executable
        params = subprocess.list2cmdline([script_path, *sys.argv[1:]])

    ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, params, None, 1)
    raise SystemExit(0)


def find_existing_path(*candidates: str) -> str | None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    for relative_path in candidates:
        absolute_path = os.path.join(base_dir, relative_path)
        if os.path.exists(absolute_path):
            return absolute_path
    return None


def start_backend(base_dir: str) -> subprocess.Popen:
    packaged_backend = find_existing_path("backend.exe", os.path.join("backend", "backend.exe"), os.path.join("backend", "dist", "backend.exe"))
    if packaged_backend:
        print(f"Starting packaged backend: {packaged_backend}")
        return subprocess.Popen([packaged_backend], cwd=base_dir)

    if getattr(sys, "frozen", False):
        print("Starting embedded backend (packaged launcher mode)...")

        def run_embedded_backend() -> None:
            import uvicorn

            uvicorn.run(
                "backend.main:app",
                host="127.0.0.1",
                port=8000,
                reload=False,
                log_level="info",
            )

        backend_thread = threading.Thread(target=run_embedded_backend, daemon=True)
        backend_thread.start()

        class EmbeddedBackendProcess:
            pid = os.getpid()

            def terminate(self) -> None:
                return None

        return EmbeddedBackendProcess()  # type: ignore[return-value]

    print("Starting FastAPI backend (development mode)...")
    python_exe = sys.executable
    return subprocess.Popen(
        [python_exe, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000", "--reload"],
        cwd=base_dir,
    )


def start_frontend(base_dir: str) -> subprocess.Popen:
    packaged_frontend = find_existing_path(os.path.join("frontend", "target", "release", "frontend.exe"), os.path.join("frontend", "target", "release", "frontend"))
    if packaged_frontend:
        print(f"Starting packaged frontend: {packaged_frontend}")
        return subprocess.Popen([packaged_frontend], cwd=base_dir)

    frontend_dir = os.path.join(base_dir, "frontend")
    print("Starting Tauri frontend (development mode)...")
    return subprocess.Popen(["npm", "run", "tauri", "dev"], cwd=frontend_dir, shell=True)

def main():
    relaunch_as_admin()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    backend_proc = start_backend(base_dir)
    frontend_proc = None
    
    try:
        time.sleep(2)
        frontend_proc = start_frontend(base_dir)
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
