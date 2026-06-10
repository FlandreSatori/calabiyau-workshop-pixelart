import time
from statistics import mean, pstdev

from vision_core import MarkerObservation, VisionCore
import win32gui

from typing import Optional

class MovementController:
    _forced_by_duration_streak: int = 0

    def __init__(self, dd, vision: VisionCore):
        self.dd = dd
        self.vision = vision
        self.move_duration_history: list[float] = []
        self.move_jump_history: list[float] = []
        self.last_move_reason: str = ""

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

    def move_to_next_block(
        self,
        direction: str,
        timeout: float = 20.0,
        target_hwnd: Optional[int] = None,
        dye_args: Optional[dict] = None,
        sample_rate: float = 100.0,
        manual_baseline_duration: Optional[float] = None,
        missing_brake_frames: int = 5,
    ) -> bool:
        deadline = time.time() + timeout
        missing_streak = 0

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
                self.last_move_reason = "init_marker_missing"
                return False

        prev_markers = list(check_res.markers)
        press_start = time.time()
        manual_baseline = None
        if manual_baseline_duration is not None:
            try:
                v = float(manual_baseline_duration)
                if v > 1e-6:
                    manual_baseline = v
            except Exception:
                manual_baseline = None

        self.dd.key_down(direction)
        try:
            while time.time() < deadline:
                if not self._is_target_window_valid(target_hwnd):
                    self._reset_move_stats()
                    self.last_move_reason = "foreground_lost"
                    return False

                elapsed = time.time() - press_start
                if manual_baseline is not None and elapsed > manual_baseline * 1.05:
                    self._record_move_success(elapsed, 0.0)
                    MovementController._forced_by_duration_streak += 1
                    print(
                        f"  [时长强判] 本次耗时 {elapsed:.3f}s 超过手动基准 5% "
                        f"(基准 {manual_baseline:.3f}s, 阈值 {manual_baseline * 1.05:.3f}s)，强制判定移动成功"
                    )
                    if MovementController._forced_by_duration_streak >= 2:
                        print("  [错误] 连续两次触发时长强判，停止任务")
                        self.last_move_reason = "stopped_by_duration_guard"
                        return False
                    self.last_move_reason = "forced_by_duration"
                    return True

                result = self.vision.detect_alignment()
                if result.has_target and len(result.markers) == 4:
                    missing_streak = 0
                    current_markers = list(result.markers)
                    moved, jump_amount = self._evaluate_move_jump(prev_markers, current_markers, direction)

                    if moved:
                        press_duration = time.time() - press_start
                        self._record_move_success(press_duration, jump_amount)
                        MovementController._forced_by_duration_streak = 0

                        d = direction.lower()
                        if d in ("d", "right"):
                            print(f"  => 向右移动成功（跳变 {jump_amount:.2f}px, 按键 {press_duration:.3f}s）")
                        elif d in ("a", "left"):
                            print(f"  => 向左移动成功（跳变 {jump_amount:.2f}px, 按键 {press_duration:.3f}s）")
                        elif d in ("space", "up"):
                            print(f"  => 向上移动成功（跳变 {jump_amount:.2f}px, 按键 {press_duration:.3f}s）")
                        else:
                            print(f"  => 向下移动成功（跳变 {jump_amount:.2f}px, 按键 {press_duration:.3f}s）")
                        self.last_move_reason = "success"
                        return True

                    # 始终采用上一帧作为参考帧
                    prev_markers = current_markers
                else:
                    missing_streak += 1
                    if missing_streak >= max(1, int(missing_brake_frames)):
                        self.last_move_reason = "missing_brake"
                        return False

                # 提高采样率，避免错过判定点
                time.sleep(1.0 / max(1.0, sample_rate))
            self._reset_move_stats()
            self.last_move_reason = "failed_to_find_marker"
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

