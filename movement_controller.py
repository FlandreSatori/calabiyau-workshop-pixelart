import time
from vision_core import VisionCore
import win32gui

class MovementController:
    def __init__(self, dd, vision: VisionCore):
        self.dd = dd
        self.vision = vision

    def move_to_next_block(self, direction: str, timeout: float = 20.0, target_hwnd: int | None = None, dye_args: dict | None = None, sample_rate: float = 100.0) -> bool:
        deadline = time.time() + timeout
        last_x, last_y = None, None
        
        # Initial check for green markers: if not found, try to recover from UI or switch to slot 1
        check_res = self.vision.detect_alignment()
        if not check_res.has_target:
            print("  [视觉追踪] 未检测到绿色标记，尝试切回1号位...")
            self.dd.key_press("1")
            time.sleep(0.5)
            
            check_res = self.vision.detect_alignment()
            if not check_res.has_target:
                print("  [错误] 无法定位绿色标记，怀疑染色失败或界面异常。")
                return False

        # 记录位置用于墙壁碰撞（防卡死）检测
        stuck_timer = time.time()
        stuck_anchor_x, stuck_anchor_y = None, None
        
        # 预判移动轴：A/D/Left/Right 为横向，其他（Space/Alt等）为纵向
        is_horizontal = direction.lower() in ('a', 'd', 'left', 'right')

        self.dd.key_down(direction)
        try:
            while time.time() < deadline:
                # 检查当前前台窗口，若不是目标窗口则暂停，等待用户点击继续
                if target_hwnd is not None:
                    try:
                        fg = win32gui.GetForegroundWindow()
                        if fg != int(target_hwnd):
                            return False
                    except Exception:
                        return False
                result = self.vision.detect_alignment()
                if result.has_target:
                    current_x = result.center_offset_x
                    current_y = result.center_offset_y
                    
                    if last_x is not None and last_y is not None:
                        delta_x = current_x - last_x
                        delta_y = current_y - last_y
                        
                        if is_horizontal:
                            # print(f"  [视觉追踪] 横向移动中... 方块中心X偏移: {current_x:6.1f} | Delta: {delta_x:6.1f}")
                            if direction.lower() in ('d', 'right') and delta_x > 20.0:
                                print(f"  => 向右移动了！({delta_x:.1f})")
                                return True
                            elif direction.lower() in ('a', 'left') and delta_x < -20.0: 
                                print(f"  => 向左移动了！({delta_x:.1f})")
                                return True
                        else:
                            # print(f"  [视觉追踪] 纵向移动中... 方块中心Y偏移: {current_y:6.1f} | Delta: {delta_y:6.1f}")
                            if direction.lower() in ('space', 'up') and delta_y < -20.0:
                                print(f"  => 向上移动了！({delta_y:.1f})")
                                return True
                            elif direction.lower() in ('alt', 'down') and delta_y > 20.0:
                                print(f"  => 向下移动了！({delta_y:.1f})")
                                return True

                    last_x, last_y = current_x, current_y
                    
                    # # 防卡死判定：如果坐标变化极小，说明撞到游戏世界空气墙/屏幕边缘了
                    # if stuck_anchor_x is None:
                    #     stuck_anchor_x, stuck_anchor_y = current_x, current_y
                    # else:
                    #     # 如果偏离锚点超过 5 个像素，说明画面确实还在移动，重置计时器和保护锚点
                    #     if abs(current_x - stuck_anchor_x) > 2.0 or abs(current_y - stuck_anchor_y) > 2.0:
                    #         stuck_timer = time.time()
                    #         stuck_anchor_x, stuck_anchor_y = current_x, current_y
                    #     elif time.time() - stuck_timer > 2.0:
                    #         print("  => ⚠️ 角色已触碰世界边界/撞墙，触发防卡死！")
                    #         return False

                # 提高采样率，避免错过判定点
                time.sleep(1.0 / max(1.0, sample_rate))
            return False
        finally:
            self.dd.key_up(direction)

    def move_keep(self, direction: str, timeout: float = 5.0, target_hwnd: int | None = None, sample_rate: float = 100.0, baseline_distance: float | None = None, threshold_ratio: float = 0.1) -> bool:
        """Move while monitoring green marker pairwise distance, stop when distance deviates
        from baseline by threshold_ratio (e.g. 0.1 for 10%). Returns True when deviation observed.
        If baseline_distance is None, attempt to measure it from current frame.
        """
        deadline = time.time() + timeout

        # attempt to get baseline distance
        if baseline_distance is None:
            baseline = self.vision.measure_green_marker_edge_length(self.vision.capture_roi())
            if baseline is None or baseline <= 1e-6:
                print("  [move_keep] 无法测量基线距离，放弃调整")
                return False
        else:
            baseline = float(baseline_distance)

        threshold = max(1.0, baseline * float(threshold_ratio))

        self.dd.key_down(direction)
        try:
            while time.time() < deadline:
                # Ensure target window still foreground if provided
                if target_hwnd is not None:
                    try:
                        fg = win32gui.GetForegroundWindow()
                        if fg != int(target_hwnd):
                            return False
                    except Exception:
                        return False

                cur = self.vision.measure_green_marker_edge_length(self.vision.capture_roi())
                if cur is not None:
                    delta = cur - baseline
                    # debug print
                    # print(f"  [move_keep] cur={cur:.2f} baseline={baseline:.2f} delta={delta:.2f} thresh={threshold:.2f}")
                    if abs(delta) >= threshold:
                        print(f"  [move_keep] 距离变化触发: {delta:.2f} >= {threshold:.2f}")
                        return True

                time.sleep(1.0 / max(1.0, sample_rate))

            return False
        finally:
            self.dd.key_up(direction)

