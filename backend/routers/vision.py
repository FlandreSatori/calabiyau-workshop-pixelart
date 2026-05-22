import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Any
from backend.dependencies import get_dd, get_vision
from backend.routers.control import BaseGameRequest, ensure_game_active
from win32 import win32gui

router = APIRouter()

class AnalyzeRequest(BaseModel):
    roi_size: int = 315

class GetColorRequest(BaseModel):
    x: int
    y: int


class WhiteGhostCalibrationRequest(BaseGameRequest):
    roi_size: int = 315
    max_attempts: int = Field(30, ge=1, le=100)
    coarse_switch_threshold: float = Field(1.4, ge=0.0, le=20.0)
    fine_target_threshold: float = Field(0.35, ge=0.0, le=20.0)
    click_settle_delay: float = Field(0.10, ge=0.0, le=5.0)
    move_settle_delay: float = Field(0.09, ge=0.0, le=5.0)
    coarse_gain: float = Field(2.4, ge=0.1, le=20.0)
    fine_gain: float = Field(1.0, ge=0.1, le=20.0)
    coarse_max_step: int = Field(34, ge=1, le=200)
    fine_max_step: int = Field(8, ge=1, le=100)

@router.post("/get-color")
def get_pixel_color(req: GetColorRequest):
    # 1. 获取屏幕桌面的设备上下文 (DC)
    hdc = win32gui.GetDC(0)
    
    # 2. 抓取目标坐标点的 32位 颜色值 (COLORREF)
    pixel = win32gui.GetPixel(hdc, req.x, req.y)
    
    # 3. 及时释放 DC 资源，防止句柄泄露导致系统卡顿
    win32gui.ReleaseDC(0, hdc)
    
    # 4. COLORREF 默认是 BGR 格式，需要转换为前端常用的 RGB 格式
    b = (pixel >> 16) & 0xFF
    g = (pixel >> 8) & 0xFF
    r = pixel & 0xFF
    
    # 5. 格式化为前端要求的 HEX 字符串（如 #FFFFFF）
    hex_color = f"#{r:02X}{g:02X}{b:02X}"
    
    return {"status": "success", "color": hex_color if hex_color else None}

@router.post("/analyze-green")
def analyze_green(req: AnalyzeRequest, vision: Any = Depends(get_vision)):
    # Optionally update ROI size from request
    vision.roi_size = req.roi_size
    vision.center = req.roi_size / 2.0
    
    frame = vision.capture_roi()
    res = vision._analyze_green_markers(frame)
    if res:
        return {
            "status": "success", "has_target": True, 
            "offset_x": res.center_offset_x, "offset_y": res.center_offset_y, 
            "horizontal_error": res.horizontal_error, "confidence": res.confidence
        }
    return {"status": "fail", "has_target": False}

# @router.post("/analyze-white")
# def analyze_white(req: AnalyzeRequest, vision: Any = Depends(get_vision)):
#     vision.roi_size = req.roi_size
#     vision.center = req.roi_size / 2.0
    
#     frame = vision.capture_roi()
#     res = vision._analyze_white_preview(frame)
#     if res:
#         return {
#             "status": "success", "has_target": True,
#             "offset_x": res.center_offset_x, "offset_y": res.center_offset_y, 
#             "horizontal_error": res.horizontal_error, "confidence": res.confidence
#         }
#     return {"status": "fail", "has_target": False}

@router.post("/detect-alignment")
def detect_alignment(req: AnalyzeRequest, vision: Any = Depends(get_vision)):
    vision.roi_size = req.roi_size
    vision.center = req.roi_size / 2.0
    
    res = vision.detect_alignment()
    return {
        "status": "success" if res.has_target else "fail",
        "has_target": res.has_target,
        "offset_x": res.center_offset_x,
        "offset_y": res.center_offset_y,
        "horizontal_error": res.horizontal_error,
        "confidence": res.confidence,
        "source": res.source
    }


@router.post("/green-distance")
def green_distance(req: AnalyzeRequest, vision: Any = Depends(get_vision)):
    vision.roi_size = req.roi_size
    vision.center = req.roi_size / 2.0

    frame = vision.capture_roi()
    dist = vision.measure_green_marker_edge_length(frame)
    if dist is None:
        return {"status": "fail", "distance": None}
    return {"status": "success", "distance": float(dist)}


@router.post("/calibrate-horizontal-white")
def calibrate_horizontal_white(req: WhiteGhostCalibrationRequest, dd: Any = Depends(get_dd), vision: Any = Depends(get_vision)):
    # 视觉水平校准已被项目改为基于绿色标记距离的动态调整策略，
    # ensure_game_active(req.exe_name, req.window_hwnd, req.focus_settle_delay)

    # vision.roi_size = req.roi_size
    # vision.center = req.roi_size / 2.0

    # # 3D移动态下直接发DD相对移动可能不生效，先用E面板把鼠标输入唤醒，再关闭面板恢复场景。
    # print("[白虚影校准] 预激活鼠标输入：E 打开染色面板 -> 微小鼠标位移 -> E 关闭")
    # dd.key_press("e")
    # time.sleep(0.25)
    # dd.mouse_move_relative(1, 0)
    # time.sleep(0.15)
    # dd.key_press("e")
    # time.sleep(req.focus_settle_delay)

    # steer = 1
    # last_abs_err = float("inf")
    # stage = "coarse"
    # stable_count = 0
    # last_flip_attempt = -999

    # print("[白虚影校准] 开始水平校准：1 键召唤虚影，左键消隐后做差分识别")

    # for attempt in range(req.max_attempts):
    #     print(f"[白虚影校准] 第 {attempt + 1}/{req.max_attempts} 轮：召唤虚影")
    #     dd.key_press("1")
    #     time.sleep(0.5)
    #     frame_with_ghost = vision.capture_roi()

    #     dd.mouse_click("left")
    #     time.sleep(0.5)
    #     frame_without_ghost = vision.capture_roi()

    #     result = vision.analyze_white_ghost_diff(frame_with_ghost, frame_without_ghost)
    #     if result is None:
    #         print("[白虚影校准] 未提取到有效虚影差分，继续重试")
    #         continue

    #     # 忽略接近 ±45° 的模糊/对称结果，这通常表示方向不确定或异常噪声
    #     if abs(float(result.horizontal_error)) >= 44.5:
    #         print(f"[白虚影校准] 检测到模糊角度 {result.horizontal_error:.2f}°，跳过本轮")
    #         continue

    #     # 置信度过低也跳过
    #     if float(result.confidence) < 0.30:
    #         print(f"[白虚影校准] 置信度过低 {result.confidence:.2f}，跳过本轮")
    #         continue

    #     err = float(result.horizontal_error)
    #     abs_err = abs(err)
    #     next_stage = "coarse" if abs_err > req.coarse_switch_threshold else "fine"
    #     if next_stage != stage:
    #         stage = next_stage
    #         print(f"[白虚影校准] 切换到{'粗调' if stage == 'coarse' else '细调'}阶段")

    #     if abs_err <= req.fine_target_threshold:
    #         stable_count += 1
    #         print(f"[白虚影校准][{stage}] 误差 {err:.2f}°，稳定计数 {stable_count}/2，source={result.source}")
    #         if stable_count >= 2:
    #             print(f"[白虚影校准] 完成，当前误差 {err:.2f}°")
    #             return {
    #                 "status": "success",
    #                 "horizontal_error": err,
    #                 "confidence": result.confidence,
    #                 "source": result.source,
    #                 "attempts": attempt + 1,
    #             }
    #     else:
    #         stable_count = 0

    #     worsen_margin = 0.28 if stage == "coarse" else 0.14
    #     if abs_err > last_abs_err + worsen_margin and attempt - last_flip_attempt >= 2:
    #         steer *= -1
    #         last_flip_attempt = attempt
    #         print("[白虚影校准] 误差增大，自动反转调节方向")
    #     last_abs_err = abs_err

    #     gain = req.coarse_gain if stage == "coarse" else req.fine_gain
    #     max_step = req.coarse_max_step if stage == "coarse" else req.fine_max_step
    #     min_step = 2 if stage == "coarse" else 1
    #     dx = int(round(err * gain * steer))
    #     if abs(dx) < min_step:
    #         dx = min_step * (1 if err >= 0 else -1) * steer
    #     dx = max(-max_step, min(max_step, dx))

    #     dd.mouse_move_relative(dx, 0)
    #     print(f"[白虚影校准][{stage}] source={result.source} 误差 {err:.2f}°，dx={dx}，confidence={result.confidence:.2f}")
    #     time.sleep(req.move_settle_delay)
    raise HTTPException(status_code=410, detail="视觉水平校准已禁用，请使用基于距离的视角自动调整")
