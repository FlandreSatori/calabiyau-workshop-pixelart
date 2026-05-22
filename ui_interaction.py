from __future__ import annotations

import time

try:
    import win32clipboard
except ImportError:  # pragma: no cover
    win32clipboard = None


class UIInteraction:
    def __init__(self, dd, exe_name: str = "Calabiyau-Win64-Shipping.exe"):
        self.dd = dd
        self.exe_name = exe_name

    def _get_absolute_coords(self, input_x: int, input_y: int) -> tuple[int, int]:
        from window_manager import WindowManager
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

    def open_color_panel(self) -> None:
        self.dd.key_press("e")

    def paste_hex_color(self, x: int, y: int, color_hex: str, click_delay: float = 0.2, clipboard_delay: float = 0.2) -> None:
        abs_x, abs_y = self._get_absolute_coords(x, y)
        
        # 1. Clear previous content more aggressively and paste
        self.dd.mouse_move(abs_x, abs_y)
        time.sleep(click_delay)
        self.dd.mouse_click("left")
        time.sleep(click_delay)
        
        # Select all and delete to ensure a clean slate
        self.dd.key_combination("ctrl", "a")
        time.sleep(click_delay)

        # 2. Set clipboard and paste
        self._set_clipboard_text(color_hex)
        time.sleep(clipboard_delay)
        self.dd.key_combination("ctrl", "v")
        time.sleep(click_delay)

    def click_confirm(self, x: int, y: int, click_delay: float = 0.2) -> None:
        abs_x, abs_y = self._get_absolute_coords(x, y)
        self.dd.mouse_move(abs_x, abs_y)
        time.sleep(click_delay) 
        self.dd.mouse_click("left")
        time.sleep(click_delay) 

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