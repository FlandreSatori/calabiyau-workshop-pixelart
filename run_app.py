import subprocess
import sys
import os
import time
import socket
import ctypes
import json
from typing import Optional


BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 8000

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
def find_existing_path(*candidates: str) -> Optional[str]:
    base_dir = get_app_base_dir()
    for relative_path in candidates:
        absolute_path = os.path.join(base_dir, relative_path)
        if os.path.exists(absolute_path):
            return absolute_path
    return None


def ensure_block_library(base_dir: str) -> None:
    library_path = os.path.join(base_dir, "block_library.json")
    if os.path.exists(library_path):
        return

    default_library = {
        "blocks": [
            {
                "id": "blk-iron",
                "name": "铁板",
                "image": "assets/铁板.png",
                "baseColor": "#FFFFFF",
                "mask": 1.0,
                "dyeable": False,
            }
        ],
        "hotbar_slots": ["blk-iron", None, None, None, None, None, None, None, None],
    }
    try:
        with open(library_path, "w", encoding="utf-8") as f:
            json.dump(default_library, f, ensure_ascii=False, indent=2)
        print(f"Created default block library: {library_path}")
    except Exception as exc:
        print(f"Failed to create default block library: {exc}")
'''

# 兼容兼容低版本Python解释器
def find_existing_path(*candidates: str) -> Optional[str]:
    base_dir = get_app_base_dir()
    for relative_path in candidates:
        absolute_path = os.path.join(base_dir, relative_path)
        if os.path.exists(absolute_path):
            return absolute_path
    return None


def ensure_block_library(base_dir: str) -> None:
    library_path = os.path.join(base_dir, "block_library.json")
    if os.path.exists(library_path):
        return

    default_library = {
        "blocks": [
            {
                "id": "blk-iron",
                "name": "铁板",
                "image": "assets/铁板.png",
                "baseColor": "#FFFFFF",
                "mask": 1.0,
                "dyeable": False,
            }
        ],
        "hotbar_slots": ["blk-iron", None, None, None, None, None, None, None, None],
    }
    try:
        with open(library_path, "w", encoding="utf-8") as f:
            json.dump(default_library, f, ensure_ascii=False, indent=2)
        print(f"Created default block library: {library_path}")
    except Exception as exc:
        print(f"Failed to create default block library: {exc}")


def build_backend_command(base_dir: str) -> list[str]:
    """Build the backend launch command for both dev and frozen modes."""
    host = BACKEND_HOST
    port = str(BACKEND_PORT)

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


def get_listening_pid_windows(port: int, host: str = "127.0.0.1") -> Optional[int]:
    if sys.platform != "win32":
        return None
    try:
        result = subprocess.run(
            ["netstat", "-ano", "-p", "TCP"],
            capture_output=True,
            text=True,
            creationflags=0x08000000,
        )
        lines = (result.stdout or "").splitlines()
        target_local = f"{host}:{port}"
        fallback_local = f":{port}"
        for line in lines:
            s = line.strip()
            if not s:
                continue
            if "LISTENING" not in s.upper():
                continue
            parts = s.split()
            if len(parts) < 5:
                continue
            local_addr = parts[1]
            pid_text = parts[-1]
            if local_addr == target_local or local_addr.endswith(fallback_local):
                if pid_text.isdigit():
                    return int(pid_text)
        return None
    except Exception:
        return None


def get_process_image_name_windows(pid: int) -> str:
    if sys.platform != "win32":
        return ""
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}"],
            capture_output=True,
            text=True,
            creationflags=0x08000000,
        )
        output = (result.stdout or "")
        for line in output.splitlines():
            row = line.strip()
            if not row or row.startswith("=") or row.startswith("映像名称"):
                continue
            parts = row.split()
            if len(parts) >= 2 and parts[1].isdigit() and int(parts[1]) == pid:
                return parts[0]
        return ""
    except Exception:
        return ""


def kill_pid_tree_windows(pid: int) -> None:
    if sys.platform != "win32":
        return
    subprocess.run(
        ["taskkill", "/F", "/T", "/PID", str(pid)],
        creationflags=0x08000000,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def ensure_backend_port_clean(base_dir: str) -> None:
    """Ensure backend port is not occupied by stale processes before launch."""
    pid = get_listening_pid_windows(BACKEND_PORT, BACKEND_HOST)
    if not pid:
        return

    image_name = get_process_image_name_windows(pid).lower()
    allowed = {"python.exe", "pythonw.exe", "backend.exe"}
    if image_name in allowed:
        print(f"Detected stale backend listener on {BACKEND_HOST}:{BACKEND_PORT} ({image_name}, PID={pid}), killing it.")
        kill_pid_tree_windows(pid)
        time.sleep(0.6)
    else:
        print(f"Warning: port {BACKEND_PORT} is occupied by {image_name or 'unknown'} (PID={pid}).")


def cleanup_backend_port_on_exit() -> None:
    """Best-effort cleanup for lingering backend listeners on app exit."""
    if sys.platform != "win32":
        return

    allowed = {"python.exe", "pythonw.exe", "backend.exe"}
    for _ in range(3):
        pid = get_listening_pid_windows(BACKEND_PORT, BACKEND_HOST)
        if not pid:
            return
        image_name = get_process_image_name_windows(pid).lower()
        if image_name not in allowed:
            print(f"Skip exit cleanup: port {BACKEND_PORT} occupied by {image_name or 'unknown'} (PID={pid}).")
            return
        print(f"Exit cleanup: killing {image_name} (PID={pid}) on {BACKEND_HOST}:{BACKEND_PORT}.")
        kill_pid_tree_windows(pid)
        time.sleep(0.3)


def start_backend(base_dir: str) -> subprocess.Popen:
    command = build_backend_command(base_dir)
    if command[0].lower().endswith("backend.exe"):
        print(f"Starting packaged backend: {command[0]}")
    else:
        print("Starting FastAPI backend (development mode)...")

    # --- 0x08000000 代表 CREATE_NO_WINDOW，意思是“不为子进程创建控制台窗口 ---
    creation_flags = 0x08000000 if sys.platform == 'win32' else 0
    child_env = os.environ.copy()
    # Unify runtime resource root (block_library.json, assets/) with launcher directory.
    child_env["PYDD_APP_BASE_DIR"] = base_dir

    return subprocess.Popen(
        command, 
        cwd=base_dir, 
        creationflags=creation_flags,
        env=child_env,
        # stdout=subprocess.DEVNULL,  # 重定向日志输出到 null
        # stderr=subprocess.DEVNULL
    )


def start_frontend(base_dir: str) -> subprocess.Popen:
    packaged_frontend = find_existing_path("frontend.exe")
    if packaged_frontend:
        print(f"Starting packaged frontend: {packaged_frontend}")
        if sys.platform == "win32" and is_admin():
            # Running frontend.exe via explorer uses the current shell token (normally non-admin),
            # which avoids drag-and-drop issues in elevated UI processes.
            subprocess.Popen(["explorer.exe", packaged_frontend], cwd=base_dir)
            return None
        return subprocess.Popen([packaged_frontend], cwd=base_dir)

    if getattr(sys, "frozen", False):
        raise FileNotFoundError("Frozen build requires frontend.exe beside the launcher, but it was not found.")

    frontend_dir = os.path.join(base_dir, "frontend")
    print("Starting Tauri frontend (development mode)...")
    return subprocess.Popen(["npm", "run", "tauri", "dev"], cwd=frontend_dir, shell=True)


def is_process_running_windows(image_name: str) -> bool:
    if sys.platform != "win32":
        return False
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {image_name}"],
            capture_output=True,
            text=True,
            creationflags=0x08000000,
        )
        output = (result.stdout or "") + (result.stderr or "")
        return image_name.lower() in output.lower()
    except Exception:
        return False


def wait_for_packaged_frontend_exit_windows(image_name: str = "frontend.exe") -> None:
    # Wait until process appears (up to ~15s), then wait until it exits.
    appear_deadline = time.time() + 15.0
    while time.time() < appear_deadline:
        if is_process_running_windows(image_name):
            break
        time.sleep(0.3)

    while is_process_running_windows(image_name):
        time.sleep(0.5)

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


def recover_backend_if_needed(base_dir: str, backend_proc: Optional[subprocess.Popen]) -> subprocess.Popen:
    """If launched backend exited early (usually bind conflict), recover by killing stale listener and relaunching."""
    if backend_proc is None:
        return backend_proc
    if backend_proc.poll() is None:
        return backend_proc

    stale_pid = get_listening_pid_windows(BACKEND_PORT, BACKEND_HOST)
    if stale_pid:
        stale_image = get_process_image_name_windows(stale_pid).lower()
        if stale_image in {"python.exe", "pythonw.exe", "backend.exe"}:
            print(f"Launched backend exited; cleaning stale listener {stale_image} (PID={stale_pid}) and retrying.")
            kill_pid_tree_windows(stale_pid)
            time.sleep(0.6)

    relaunched = start_backend(base_dir)
    if not wait_for_port(BACKEND_PORT, host=BACKEND_HOST, timeout=15):
        raise RuntimeError("Backend relaunch failed")
    return relaunched

def main():
    relaunch_as_admin()

    base_dir = get_app_base_dir()
    ensure_block_library(base_dir)
    ensure_backend_port_clean(base_dir)
    backend_proc = start_backend(base_dir)
    frontend_proc: Optional[subprocess.Popen] = None
    frontend_started_unelevated = False
    
    try:
        if wait_for_port(BACKEND_PORT, host=BACKEND_HOST, timeout=15):
            backend_proc = recover_backend_if_needed(base_dir, backend_proc)
            frontend_proc = start_frontend(base_dir)
            if frontend_proc is None and sys.platform == 'win32':
                frontend_started_unelevated = True
                wait_for_packaged_frontend_exit_windows("frontend.exe")
            elif frontend_proc is not None:
                frontend_proc.wait()
        else:
            print("后端启动失败，无法启动前端。")
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        # 定义 Windows 下隐藏窗口的创建标志
        creation_flags = 0x08000000 if sys.platform == 'win32' else 0

        if frontend_started_unelevated and sys.platform == 'win32':
            subprocess.run(
                "taskkill /F /IM frontend.exe",
                creationflags=creation_flags,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        elif frontend_proc:
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

        cleanup_backend_port_on_exit()

if __name__ == "__main__":
    main()