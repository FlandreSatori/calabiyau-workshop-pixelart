from fastapi import APIRouter

from window_manager import WindowManager
from backend.task_manager import TaskManager

router = APIRouter()


@router.get("/windows")
def list_windows():
    return {"status": "success", "windows": WindowManager.list_windows()}


@router.get("/foreground")
def get_foreground_window():
    windows = WindowManager.list_windows()
    current = next((window for window in windows if window["is_foreground"]), None)
    return {"status": "success", "window": current}


@router.post("/activate")
def activate_window(payload: dict):
    """Activate a window by hwnd or by exe_name.

    payload: { hwnd?: int, exe_name?: str }
    """
    hwnd = payload.get("hwnd")
    exe_name = payload.get("exe_name")

    if hwnd is not None:
        ok = WindowManager.activate_hwnd(int(hwnd))
        return {"status": "success" if ok else "fail", "by": "hwnd", "hwnd": hwnd}

    if exe_name:
        ok = WindowManager.activate_window(str(exe_name))
        return {"status": "success" if ok else "fail", "by": "exe_name", "exe_name": exe_name}

    return {"status": "fail", "detail": "missing hwnd or exe_name"}


@router.post("/continue")
def continue_tasks():
    """Resume any paused background tasks (user clicked Continue)."""
    TaskManager.resume_all()
    return {"status": "success", "detail": "resumed"}


@router.get("/paused")
def is_paused():
    return {"status": "success", "paused": TaskManager.is_paused()}

@router.post("/abort")
def abort_tasks():
    """Abort any paused background tasks (user clicked Force Stop)."""
    TaskManager.abort_all()
    return {"status": "success", "detail": "aborted"}
