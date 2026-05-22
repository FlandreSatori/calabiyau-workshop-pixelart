import win32gui
import win32process
import win32con
import psutil

class WindowManager:
    @staticmethod
    def list_windows() -> list[dict[str, object]]:
        windows: list[dict[str, object]] = []

        def callback(hwnd, _):
            if not win32gui.IsWindowVisible(hwnd):
                return True

            title = win32gui.GetWindowText(hwnd).strip()
            if not title:
                return True

            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            exe_name = ""
            try:
                proc = psutil.Process(pid)
                exe_name = (proc.name() or "").strip()
            except Exception:
                exe_name = ""

            left, top = win32gui.ClientToScreen(hwnd, (0, 0))
            _, _, width, height = win32gui.GetClientRect(hwnd)
            windows.append(
                {
                    "hwnd": hwnd,
                    "pid": pid,
                    "exe_name": exe_name,
                    "title": title,
                    "left": left,
                    "top": top,
                    "width": width,
                    "height": height,
                    "is_foreground": hwnd == win32gui.GetForegroundWindow(),
                }
            )
            return True

        win32gui.EnumWindows(callback, None)
        windows.sort(key=lambda item: (not bool(item["is_foreground"]), str(item["title"]).lower()))
        return windows

    @staticmethod
    def get_hwnd(exe_name: str) -> int | None:
        target_pid = None
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'] and proc.info['name'].lower() == exe_name.lower():
                target_pid = proc.info['pid']
                break
                
        if target_pid is None:
            return None
            
        windows = []
        def callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                if pid == target_pid:
                    windows.append(hwnd)
            return True
            
        win32gui.EnumWindows(callback, windows)
        
        if not windows:
            return None
            
        return windows[0]

    @staticmethod
    def activate_window(exe_name: str) -> bool:
        """
        激活并将指定进程的窗口带到前台。
        """
        hwnd = WindowManager.get_hwnd(exe_name)
        if hwnd:
            try:
                # 若最小化则恢复
                if win32gui.IsIconic(hwnd):
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                    
                # 切换到前台
                win32gui.SetForegroundWindow(hwnd)
                import time
                time.sleep(0.2) # 给系统一点时间完成切换
                return True
            except Exception as e:
                print(f"激活窗口失败: {e}")
                return False
        return False

    @staticmethod
    def activate_hwnd(hwnd: int) -> bool:
        try:
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            # 使用 SetForegroundWindow 尝试将窗口置前
            win32gui.SetForegroundWindow(hwnd)
            import time
            time.sleep(0.2)
            return True
        except Exception as e:
            print(f"激活窗口失败: {e}")
            return False

    @staticmethod
    def get_window_rect(exe_name: str) -> tuple[int, int, int, int] | None:
        hwnd = WindowManager.get_hwnd(exe_name)
        if not hwnd:
            return None
            
        # 获取Client区域相对于屏幕的位置
        left, top = win32gui.ClientToScreen(hwnd, (0, 0))
        _, _, width, height = win32gui.GetClientRect(hwnd)
        
        return (left, top, width, height)
