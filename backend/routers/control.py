from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Any
from ..dependencies import get_dd
from window_manager import WindowManager
import time
import win32gui

router = APIRouter()

class BaseGameRequest(BaseModel):
    exe_name: str = "Calabiyau-Win64-Shipping.exe"
    window_hwnd: int | None = None
    focus_settle_delay: float = 0.05

class MoveRequest(BaseGameRequest):
    dx: int
    dy: int

class ClickRequest(BaseGameRequest):
    button: str = "left"

class KeyPressRequest(BaseGameRequest):
    key: str

def ensure_game_active(exe_name: str, window_hwnd: int | None = None, settle_delay: float = 0.05):
    # If a hwnd is provided, verify it exists and is the current foreground window.
    if window_hwnd is not None:
        try:
            if not win32gui.IsWindow(int(window_hwnd)):
                raise HTTPException(status_code=404, detail=f"窗口句柄 {window_hwnd} 不存在")
        except Exception:
            raise HTTPException(status_code=404, detail=f"窗口句柄 {window_hwnd} 不存在")

        fg = win32gui.GetForegroundWindow()
        if fg != int(window_hwnd):
            # Do not force-activate; instruct caller to wait and retry.
            raise HTTPException(status_code=409, detail="foreground_not_target")
    else:
        # If no hwnd provided, try resolve by exe name and verify it's foreground
        hwnd = WindowManager.get_hwnd(exe_name)
        if hwnd is None:
            raise HTTPException(status_code=404, detail=f"无法找到进程对应的窗口: {exe_name}")
        fg = win32gui.GetForegroundWindow()
        if fg != hwnd:
            raise HTTPException(status_code=409, detail="foreground_not_target")
    time.sleep(settle_delay)

@router.post("/move-relative")
def move_relative(req: MoveRequest, dd: Any = Depends(get_dd)):
    ensure_game_active(req.exe_name, req.window_hwnd, req.focus_settle_delay)
    dd.mouse_move_relative(req.dx, req.dy)
    return {"status": "success", "dx": req.dx, "dy": req.dy}

@router.post("/click")
def click(req: ClickRequest, dd: Any = Depends(get_dd)):
    ensure_game_active(req.exe_name, req.window_hwnd, req.focus_settle_delay)
    dd.mouse_click(req.button)
    return {"status": "success", "button": req.button}

@router.post("/keypress")
def keypress(req: KeyPressRequest, dd: Any = Depends(get_dd)):
    ensure_game_active(req.exe_name, req.window_hwnd, req.focus_settle_delay)
    dd.key_press(req.key)
    return {"status": "success", "key": req.key}
