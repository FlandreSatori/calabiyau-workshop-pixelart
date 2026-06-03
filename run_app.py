import subprocess
import sys
import os
import time
import socket
import ctypes
from typing import Optional

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

    ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, params, None, 0)
    raise SystemExit(0)


def get_app_base_dir() -> str:
    """Return the directory that should contain bundled exe assets.

    In a PyInstaller onefile build, __file__ points into the temporary
    extraction directory, while bundled sibling executables and DLLs are
    expected next to the launcher exe.
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

'''
# str | None 是 Python3.10+ 新语法（联合类型）
def find_existing_path(*candidates: str) -> str | None:
    base_dir = get_app_base_dir()
    for relative_path in candidates:
        absolute_path = os.path.join(base_dir, relative_path)
        if os.path.exists(absolute_path):
            return absolute_path
    return None
'''

# 兼容兼容低版本Python解释器
def find_existing_path(*candidates: str) -> Optional[str]:
    base_dir = get_app_base_dir()
    for relative_path in candidates:
        absolute_path = os.path.join(base_dir, relative_path)
        if os.path.exists(absolute_path):
            return absolute_path
    return None


def build_backend_command(base_dir: str) -> list[str]:
    """Build the backend launch command for both dev and frozen modes."""
    host = "127.0.0.1"
    port = "8000"

    packaged_backend = find_existing_path("backend.exe")
    if packaged_backend:
        # Give the packaged backend the same explicit bind target as dev mode.
        return [packaged_backend, "--host", host, "--port", port]

    if getattr(sys, "frozen", False):
        raise FileNotFoundError("Frozen build requires backend.exe beside the launcher, but it was not found.")

    python_exe = sys.executable
    return [
        python_exe,
        "-m",
        "uvicorn",
        "backend.main:app",
        "--host",
        host,
        "--port",
        port,
        "--reload",
    ]


def start_backend(base_dir: str) -> subprocess.Popen:
    command = build_backend_command(base_dir)
    if command[0].lower().endswith("backend.exe"):
        print(f"Starting packaged backend: {command[0]}")
    else:
        print("Starting FastAPI backend (development mode)...")

    # --- 0x08000000 代表 CREATE_NO_WINDOW，意思是“不为子进程创建控制台窗口 ---
    creation_flags = 0x08000000 if sys.platform == 'win32' else 0

    return subprocess.Popen(
        command, 
        cwd=base_dir, 
        creationflags=creation_flags,
        stdout=subprocess.DEVNULL,  # 重定向日志输出到 null
        stderr=subprocess.DEVNULL
    )


def start_frontend(base_dir: str) -> subprocess.Popen:
    packaged_frontend = find_existing_path("frontend.exe")
    if packaged_frontend:
        print(f"Starting packaged frontend: {packaged_frontend}")
        return subprocess.Popen([packaged_frontend], cwd=base_dir)

    if getattr(sys, "frozen", False):
        raise FileNotFoundError("Frozen build requires frontend.exe beside the launcher, but it was not found.")

    frontend_dir = os.path.join(base_dir, "frontend")
    print("Starting Tauri frontend (development mode)...")
    return subprocess.Popen(["npm", "run", "tauri", "dev"], cwd=frontend_dir, shell=True)

def wait_for_port(port, host='127.0.0.1', timeout=10):
    """动态检测端口是否开放，每 0.5 秒测一次，最多等 timeout 秒"""
    start_time = time.time()
    while True:
        try:
            # 尝试建立 TCP 连接
            with socket.create_connection((host, port), timeout=1):
                print(f"🎉 检测到端口 {port} 已成功开放！")
                return True
        except (ValueError, OSError):
            if time.time() - start_time > timeout:
                print(f"❌ 错误：等待端口 {port} 超时，后端可能启动失败了。")
                return False
            print(f"⏳ 后端仍在启动中，正在等待端口 {port}...")
            time.sleep(0.5)

def main():
    relaunch_as_admin()

    base_dir = get_app_base_dir()
    backend_proc = start_backend(base_dir)
    frontend_proc = None
    
    try:
        if wait_for_port(8000, timeout=15):
            frontend_proc = start_frontend(base_dir)
            frontend_proc.wait()
        else:
            print("后端启动失败，无法启动前端。")
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        # 定义 Windows 下隐藏窗口的创建标志
        creation_flags = 0x08000000 if sys.platform == 'win32' else 0

        if frontend_proc:
            if sys.platform == 'win32':
                subprocess.run(
                    f"taskkill /F /T /PID {frontend_proc.pid}", 
                    creationflags=creation_flags,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            else:
                frontend_proc.terminate()
        
        if backend_proc:
            if sys.platform == 'win32':
                subprocess.run(
                    f"taskkill /F /T /PID {backend_proc.pid}", 
                    creationflags=creation_flags,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            else:
                backend_proc.terminate()

if __name__ == "__main__":
    main()