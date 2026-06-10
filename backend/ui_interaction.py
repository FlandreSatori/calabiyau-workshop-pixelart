from __future__ import annotations

import time
import random
from ctypes import windll

try:
    import win32clipboard
except ImportError:  # pragma: no cover
    win32clipboard = None

try:
    import win32gui
except ImportError:  # pragma: no cover
    win32gui = None


class UIInteraction:
    def __init__(self, dd, exe_name: str = "Calabiyau-Win64-Shipping.exe", humanize_level: int = 0):
        self.dd = dd
        self.exe_name = exe_name
        self.humanize_level = humanize_level

    def _get_absolute_coords(self, input_x: int, input_y: int) -> tuple[int, int]:
        from backend.window_manager import WindowManager
        rect = WindowManager.get_window_rect(self.exe_name)
        if rect:
            left, top, width, height = rect
            
            # TODO: 用户第一次启用时，需要对染色UI位置进行截图校准
            # 当前硬编码坐标基于 2560x1440 游戏内基准分辨率测量，运行期间按比例自适应缩放到当前窗体
            mapped_x = int(left + width * (input_x / 2560.0))
            mapped_y = int(top + height * (input_y / 1440.0))
            print(f"  [UI适配] 自动修正偏移: {input_x},{input_y} -> {mapped_x},{mapped_y}")
            return mapped_x, mapped_y
            
        return input_x, input_y

    def _sleep(self, base_delay: float) -> None:
        """Sleep with tiny jitter if humanization is enabled."""
        if self.humanize_level > 0:
            jitter = base_delay * 0.15 * self.humanize_level
            actual = base_delay + random.uniform(-jitter, jitter)
            time.sleep(max(0.001, actual))
        else:
            time.sleep(max(0.001, base_delay))

    def _move_cursor_absolute(self, x: int, y: int) -> None:
        """Move the system cursor directly for UI operations.

        If humanize_level is greater than 0, performs a smooth movement
        trajectory instead of instant teleportation to avoid heuristic
        anomaly detection by anti-cheat systems. Total movement duration
        is kept under ~100ms.
        """
        if self.humanize_level == 0:
            try:
                windll.user32.SetCursorPos(int(x), int(y))
            except Exception:
                self.dd.mouse_move(int(x), int(y))
            return

        start_x, start_y = x, y
        if win32gui is not None:
            try:
                start_x, start_y = win32gui.GetCursorPos()
            except Exception:
                pass

        # Add tiny random offset based on level
        end_x = int(x + random.randint(-self.humanize_level, self.humanize_level))
        end_y = int(y + random.randint(-self.humanize_level, self.humanize_level))

        dist = ((end_x - start_x)**2 + (end_y - start_y)**2)**0.5
        if dist < 5:
            try:
                windll.user32.SetCursorPos(end_x, end_y)
            except Exception:
                self.dd.mouse_move(end_x, end_y)
            return

        # Keep the total humanized movement time extremely short to not block the pipeline
        total_time = 0.03 + (0.02 * self.humanize_level)
        steps = int(max(5, min(15, dist / 20)))
        step_time = total_time / steps

        for i in range(1, steps + 1):
            t = i / steps
            # ease-out curve
            t_e = 1 - (1 - t) * (1 - t)
            cx = int(start_x + (end_x - start_x) * t_e)
            cy = int(start_y + (end_y - start_y) * t_e)

            try:
                windll.user32.SetCursorPos(cx, cy)
            except Exception:
                self.dd.mouse_move(cx, cy)
            time.sleep(step_time)

        # Snap to final randomized target
        try:
            windll.user32.SetCursorPos(end_x, end_y)
        except Exception:
            self.dd.mouse_move(end_x, end_y)

    def open_color_panel(self) -> None:
        self.dd.key_press("e")

    def paste_hex_color(self, x: int, y: int, color_hex: str, click_delay: float = 0.2, clipboard_delay: float = 0.2) -> None:
        abs_x, abs_y = self._get_absolute_coords(x, y)
        
        # 1. Clear previous content more aggressively and paste
        self._move_cursor_absolute(abs_x, abs_y)
        self._sleep(click_delay)
        self.dd.mouse_click("left")
        self._sleep(click_delay)
        
        # Select all and delete to ensure a clean slate
        self.dd.key_combination("ctrl", "a")
        self._sleep(click_delay)

        # 2. Set clipboard and paste
        self._set_clipboard_text(color_hex)
        self._sleep(clipboard_delay)
        self.dd.key_combination("ctrl", "v")
        self._sleep(click_delay)

    def click_confirm(self, x: int, y: int, click_delay: float = 0.2) -> None:
        abs_x, abs_y = self._get_absolute_coords(x, y)
        self._move_cursor_absolute(abs_x, abs_y)
        self._sleep(click_delay) 
        self.dd.mouse_click("left")
        self._sleep(click_delay) 

    def close_panel(self) -> None:
        self.dd.key_press("e")

    def _set_clipboard_text(self, text: str) -> None:
        if win32clipboard is None:
            raise RuntimeError("win32clipboard 不可用，请安装 pywin32")

        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(text)
        finally:
            win32clipboard.CloseClipboard()
