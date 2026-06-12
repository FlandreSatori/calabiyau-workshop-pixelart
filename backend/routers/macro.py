import time
import traceback
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Optional
from backend.dependencies import get_dd, get_vision
from backend.ui_interaction import UIInteraction
from backend.movement_controller import MovementController
from backend.window_manager import WindowManager
from win32 import win32gui

router = APIRouter()

class BaseGameRequest(BaseModel):
    exe_name: str = "Calabiyau-Win64-Shipping.exe"
    window_hwnd: Optional[int]= None
    focus_settle_delay: float = Field(0.05, ge=0.0, le=5.0)
    place_key_delay: float = Field(0.3, ge=0.0, le=5.0)
    place_click_delay: float = Field(0.3, ge=0.0, le=5.0)
    move_hold_delay: float = Field(0.3, ge=0.0, le=5.0)
    dye_open_delay: float = Field(0.1, ge=0.0, le=5.0)
    dye_paste_delay: float = Field(0.2, ge=0.0, le=5.0)
    dye_confirm_delay: float = Field(0.1, ge=0.0, le=5.0)
    dye_return_delay: float = Field(0.3, ge=0.0, le=5.0)
    # Extra fine-grained delays for UI interaction
    ui_click_delay: float = Field(0.3, ge=0.0, le=5.0)
    ui_clipboard_delay: float = Field(0.2, ge=0.0, le=5.0)
    move_sample_rate: float = Field(100.0, ge=1.0, le=1000.0)
    humanize_level: int = Field(0, ge=0, le=3)
    place_slot: int = Field(2, ge=1, le=9)
    dye_slot: int = Field(2, ge=1, le=9)

class DyeRequest(BaseGameRequest):
    hex_color: str
    color_input_x: int = 2157
    color_input_y: int = 930
    confirm_button_x: Optional[int]= None
    confirm_button_y: Optional[int]= None
    repaste_only: bool = False

class DyeConfirmRequest(BaseGameRequest):
    confirm_button_x: int
    confirm_button_y: int

class MoveCharacterRequest(BaseGameRequest):
    direction: str
    timeout: float = 20.0
    dye_recovery: Optional[dict]= None

class MoveKeepRequest(BaseGameRequest):
    direction: str
    timeout: float = 5.0
    baseline_distance: Optional[float]= None
    threshold_ratio: float = Field(0.10, ge=0.0, le=1.0)

class ActionRequest(BaseGameRequest):
    pass

def ensure_game_active(exe_name: str, window_hwnd: Optional[int]= None, settle_delay: float = 0.05):
    # Validate hwnd existence (if provided) and require it to be the current foreground window.
    if window_hwnd is not None:
        try:
            if not win32gui.IsWindow(int(window_hwnd)):
                raise HTTPException(status_code=409, detail=f"window_missing")
        except Exception:
            raise HTTPException(status_code=409, detail=f"window_missing")
        fg = win32gui.GetForegroundWindow()
        if fg != int(window_hwnd):
            raise HTTPException(status_code=409, detail="foreground_not_target")
    else:
        hwnd = WindowManager.get_hwnd(exe_name)
        if hwnd is None:
            raise HTTPException(status_code=404, detail=f"无法找到进程对应的窗口: {exe_name}")
        fg = win32gui.GetForegroundWindow()
        if fg != hwnd:
            raise HTTPException(status_code=409, detail="foreground_not_target")
    time.sleep(settle_delay)

@router.post("/dye")
def dye_block(req: DyeRequest, dd: Any = Depends(get_dd)):
    req_ctx = (
        f"color={req.hex_color} repaste_only={req.repaste_only} "
        f"target=({req.color_input_x},{req.color_input_y}) hwnd={req.window_hwnd}"
    )
    start = time.perf_counter()
    print(f"[macro.dye] start {req_ctx}")
    try:
        ensure_game_active(req.exe_name, req.window_hwnd, req.focus_settle_delay)

        ui = UIInteraction(dd, req.exe_name, humanize_level=req.humanize_level)

        if not req.repaste_only:
            print(f"[macro.dye] switch slot to {req.dye_slot} and open dye panel")
            dd.key_press(str(req.dye_slot))
            time.sleep(req.dye_return_delay)

            ui.open_color_panel()
            time.sleep(req.dye_open_delay)

        print("[macro.dye] paste hex color")
        # Pass down the granular delays
        ui.paste_hex_color(
            req.color_input_x,
            req.color_input_y,
            req.hex_color,
            click_delay=req.ui_click_delay,
            clipboard_delay=req.ui_clipboard_delay,
        )
        time.sleep(req.dye_paste_delay)

        if req.confirm_button_x and req.confirm_button_y:
            print(
                "[macro.dye] optional inline confirm at "
                f"({req.confirm_button_x},{req.confirm_button_y})"
            )
            ui.click_confirm(req.confirm_button_x, req.confirm_button_y, click_delay=req.ui_click_delay)
            time.sleep(req.dye_confirm_delay)
            time.sleep(req.focus_settle_delay)

        elapsed_ms = (time.perf_counter() - start) * 1000.0
        print(f"[macro.dye] success {req_ctx} elapsed={elapsed_ms:.1f}ms")
        return {"status": "success", "color": req.hex_color}
    except HTTPException as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        print(
            f"[macro.dye] http_error status={exc.status_code} detail={exc.detail} "
            f"elapsed={elapsed_ms:.1f}ms {req_ctx}"
        )
        raise
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        print(f"[macro.dye] unexpected_error elapsed={elapsed_ms:.1f}ms {req_ctx}: {exc!r}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"macro_dye_failed: {type(exc).__name__}: {exc}")

@router.post("/dye-confirm")
def dye_confirm(req: DyeConfirmRequest, dd: Any = Depends(get_dd)):
    req_ctx = (
        f"confirm=({req.confirm_button_x},{req.confirm_button_y}) hwnd={req.window_hwnd}"
    )
    print(f"[macro.dye-confirm] start {req_ctx}")
    try:
        ensure_game_active(req.exe_name, req.window_hwnd, req.focus_settle_delay)
        ui = UIInteraction(dd, req.exe_name, humanize_level=req.humanize_level)
        ui.click_confirm(req.confirm_button_x, req.confirm_button_y, click_delay=req.ui_click_delay)
        time.sleep(req.dye_confirm_delay)
        time.sleep(req.focus_settle_delay)
        print(f"[macro.dye-confirm] success {req_ctx}")
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as exc:
        print(f"[macro.dye-confirm] unexpected_error {req_ctx}: {exc!r}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"macro_dye_confirm_failed: {type(exc).__name__}: {exc}")

@router.post("/place")
def place_block(req: ActionRequest, dd: Any = Depends(get_dd)):
    ensure_game_active(req.exe_name, req.window_hwnd, req.focus_settle_delay)
    dd.key_press(str(req.place_slot))
    time.sleep(req.place_key_delay)
    dd.mouse_click("left")
    time.sleep(req.place_click_delay)
    return {"status": "success"}

@router.post("/move-to-next-block")
def move_character(req: MoveCharacterRequest, dd: Any = Depends(get_dd), vision: Any = Depends(get_vision)):
    ensure_game_active(req.exe_name, req.window_hwnd, req.focus_settle_delay)
    
    movement = MovementController(dd, vision)
    target_hwnd = req.window_hwnd if req.window_hwnd is not None else WindowManager.get_hwnd(req.exe_name)
    
    success = movement.move_to_next_block(
        req.direction, 
        req.timeout, 
        target_hwnd, 
        dye_args=req.dye_recovery,
        sample_rate=req.move_sample_rate
    )
    return {"status": "success" if success else "failed_to_find_marker", "moved": success}

@router.post("/move-keep")
def move_character_keep(req: MoveKeepRequest, dd: Any = Depends(get_dd), vision: Any = Depends(get_vision)):
    ensure_game_active(req.exe_name, req.window_hwnd, req.focus_settle_delay)

    movement = MovementController(dd, vision)
    target_hwnd = req.window_hwnd if req.window_hwnd is not None else WindowManager.get_hwnd(req.exe_name)

    success = movement.move_keep(
        req.direction,
        timeout=req.timeout,
        target_hwnd=target_hwnd,
        sample_rate=req.move_sample_rate,
        baseline_distance=req.baseline_distance,
        threshold_ratio=req.threshold_ratio,
    )
    return {"status": "success" if success else "failed_to_find_marker", "moved": success}