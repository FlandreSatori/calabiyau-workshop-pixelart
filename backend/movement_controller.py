import time
from statistics import mean, pstdev

from backend.vision_core import MarkerObservation, VisionCore
import win32gui

from typing import Optional

class MovementController:
    def __init__(self, dd, vision: VisionCore):
        self.dd = dd
        self.vision = vision
        self.move_duration_history: list[float] = []
        self.move_jump_history: list[float] = []

    def _is_target_window_valid(self, target_hwnd: Optional[int]) -> bool:
        if target_hwnd is None:
            return True
        try:
            fg = win32gui.GetForegroundWindow()
            return fg == int(target_hwnd)
        except Exception:
            return False

    def _match_markers(
        self,
        reference: list[MarkerObservation],
        current: list[MarkerObservation],
    ) -> list[tuple[MarkerObservation, MarkerObservation]]:
        if len(reference) != 4 or len(current) != 4:
            return []

        def sort_markers(markers: list[MarkerObservation]) -> list[MarkerObservation]:
            sorted_by_y = sorted(markers, key=lambda m: m.y)
            top = sorted(sorted_by_y[:2], key=lambda m: m.x)
            bottom = sorted(sorted_by_y[2:], key=lambda m: m.x)
            return top + bottom

        ref_sorted = sort_markers(reference)
        cur_sorted = sort_markers(current)
        return list(zip(ref_sorted, cur_sorted))

    def _evaluate_move_jump(
        self,
        reference: list[MarkerObservation],
        current: list[MarkerObservation],
        direction: str,
    ) -> tuple[bool, float]:
        pairs = self._match_markers(reference, current)
        if len(pairs) != 4:
            return False, 0.0

        is_horizontal = direction.lower() in ("a", "d", "left", "right")
        deltas = []
        for ref, cur in pairs:
            axis_delta = float(cur.x - ref.x) if is_horizontal else float(cur.y - ref.y)
            deltas.append(axis_delta)

        deltas.sort()
        mean_delta = sum(deltas) / 4.0

        moved = False
        d = direction.lower()
        jump_threshold = 8.0
        if d in ("d", "right") and mean_delta > jump_threshold:
            moved = True
        elif d in ("a", "left") and mean_delta < -jump_threshold:
            moved = True
        elif d in ("space", "up") and mean_delta < -jump_threshold:
            moved = True
        elif d in ("alt", "down") and mean_delta > jump_threshold:
            moved = True

        return moved, mean_delta

    def _is_duration_guard_active(self) -> bool:
        if len(self.move_duration_history) < 3 or len(self.move_jump_history) < 3:
            return False

        dur_avg = float(mean(self.move_duration_history))
        jump_avg = float(mean(self.move_jump_history))
        if dur_avg <= 1e-6 or jump_avg <= 1e-6:
            return False

        dur_cv = float(pstdev(self.move_duration_history) / dur_avg)
        jump_cv = float(pstdev(self.move_jump_history) / jump_avg)
        # 仅在连续稳定的历史样本下启用时长阈值卫兵
        return dur_cv <= 0.25 and jump_cv <= 0.35

    def _record_move_success(self, press_duration: float, jump_distance: float) -> None:
        self.move_duration_history.append(float(press_duration))
        self.move_jump_history.append(float(jump_distance))
        if len(self.move_duration_history) > 20:
            self.move_duration_history = self.move_duration_history[-20:]
        if len(self.move_jump_history) > 20:
            self.move_jump_history = self.move_jump_history[-20:]

    def _reset_move_stats(self) -> None:
        self.move_duration_history = []
        self.move_jump_history = []

    def move_to_next_block(self, direction: str, timeout: float = 20.0, target_hwnd: Optional[int] = None, dye_args: Optional[dict] = None, sample_rate: float = 100.0) -> bool:
        deadline = time.time() + timeout

        # 必须先拿到4个圆点（绿+灰），否则尝试切回1号位恢复
        check_res = self.vision.detect_alignment()
        if not check_res.has_target or len(check_res.markers) != 4:
            print("  [视觉追踪] 未检测到完整四圆点，尝试切回1号位...")
            self.dd.key_press("1")
            time.sleep(0.5)

            check_res = self.vision.detect_alignment()
            if not check_res.has_target or len(check_res.markers) != 4:
                print("  [错误] 无法定位完整四圆点，怀疑染色失败或界面异常。")
                self._reset_move_stats()
                return False

        prev_markers = list(check_res.markers)
        press_start = time.time()
        warned_slow = False
        guard_active = self._is_duration_guard_active()
        avg_duration = float(mean(self.move_duration_history)) if self.move_duration_history else 0.0

        self.dd.key_down(direction)
        try:
            while time.time() < deadline:
                if not self._is_target_window_valid(target_hwnd):
                    self._reset_move_stats()
                    return False

                elapsed = time.time() - press_start
                if guard_active and avg_duration > 1e-6:
                    if not warned_slow and elapsed > avg_duration * 1.2:
                        print(f"  [警告] 本次移动按键时长 {elapsed:.3f}s 超过历史均值 1.2x ({avg_duration * 1.2:.3f}s)")
                        warned_slow = True
                    if elapsed > avg_duration * 1.5:
                        print(f"  [错误] 本次移动按键时长 {elapsed:.3f}s 超过历史均值 1.5x ({avg_duration * 1.5:.3f}s)，终止任务")
                        self._reset_move_stats()
                        return False

                result = self.vision.detect_alignment()
                if result.has_target and len(result.markers) == 4:
                    current_markers = list(result.markers)
                    moved, jump_amount = self._evaluate_move_jump(prev_markers, current_markers, direction)

                    if moved:
                        press_duration = time.time() - press_start
                        self._record_move_success(press_duration, jump_amount)

                        d = direction.lower()
                        if d in ("d", "right"):
                            print(f"  => 向右移动成功（跳变 {jump_amount:.2f}px, 按键 {press_duration:.3f}s）")
                        elif d in ("a", "left"):
                            print(f"  => 向左移动成功（跳变 {jump_amount:.2f}px, 按键 {press_duration:.3f}s）")
                        elif d in ("space", "up"):
                            print(f"  => 向上移动成功（跳变 {jump_amount:.2f}px, 按键 {press_duration:.3f}s）")
                        else:
                            print(f"  => 向下移动成功（跳变 {jump_amount:.2f}px, 按键 {press_duration:.3f}s）")
                        return True

                    # 始终采用上一帧作为参考帧
                    prev_markers = current_markers

                # 提高采样率，避免错过判定点
                time.sleep(1.0 / max(1.0, sample_rate))
            self._reset_move_stats()
            return False
        finally:
            self.dd.key_up(direction)

    def move_keep(self, direction: str, timeout: float = 5.0, target_hwnd: Optional[int] = None, sample_rate: float = 100.0, baseline_distance: Optional[float] = None, threshold_ratio: float = 0.1) -> bool:
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

