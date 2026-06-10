# -*- coding: utf-8 -*-
"""
游戏截图和坐标采集工具
用于辅助采集游戏UI和关键位置的坐标信息
"""

import argparse
import cv2
import mss
import numpy as np
from datetime import datetime
import json
import os

class ScreenshotCollector:
    """屏幕截图采集器"""
    
    def __init__(self, output_dir="./screenshots", capture_monitor_index=1):
        self.output_dir = output_dir
        self.sct = mss.mss()
        os.makedirs(output_dir, exist_ok=True)
        self.coordinate_map = {}
        self.capture_monitor_index = capture_monitor_index

    def list_monitors(self):
        """返回可用显示器信息"""
        return self.sct.monitors
    
    def capture_and_display(self, region=None, name="screenshot"):
        """
        捕获屏幕并显示，支持标记坐标
        
        Args:
            region: (x, y, width, height) 或 None（全屏）
            name: 截图名称
        """
        if region:
            screenshot = np.array(self.sct.grab(region))
        else:
            # 获取指定显示器分辨率
            monitor = self.sct.monitors[self.capture_monitor_index]
            screenshot = np.array(self.sct.grab(monitor))
        
        # BGR格式转RGB
        screenshot_rgb = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2BGR)
        
        # 显示坐标标记窗口
        self._show_with_marker(screenshot_rgb, name)
        
        return screenshot_rgb
    
    def _show_with_marker(self, image, title="Image"):
        """显示图片并支持鼠标点击标记坐标"""
        
        marked_image = image.copy()
        markers = []
        
        def on_mouse(event, x, y, flags, param):
            if event == cv2.EVENT_LBUTTONDOWN:
                # 左键：标记坐标
                markers.append((x, y))
                cv2.circle(marked_image, (x, y), 5, (0, 255, 0), -1)
                cv2.putText(marked_image, f"({x}, {y})", (x + 10, y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                print(f"[标记点 {len(markers)}] 坐标: ({x}, {y})")
            elif event == cv2.EVENT_RBUTTONDOWN:
                # 右键：撤销最后一个标记
                if markers:
                    markers.pop()
                    print(f"撤销标记，剩余 {len(markers)} 个标记")
                    # 重新绘制
                    marked_image[:] = image
                    for mx, my in markers:
                        cv2.circle(marked_image, (mx, my), 5, (0, 255, 0), -1)
                        cv2.putText(marked_image, f"({mx}, {my})", (mx + 10, my), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        cv2.namedWindow(title, cv2.WINDOW_NORMAL)
        cv2.setMouseCallback(title, on_mouse)
        
        print("\n" + "="*60)
        print(f"📸 {title}")
        print("="*60)
        print("操作说明：")
        print("  • 左键点击标记重要坐标")
        print("  • 右键撤销最后一个标记")
        print("  • 按 's' 保存截图和坐标")
        print("  • 按 'ESC' 关闭窗口")
        print("="*60 + "\n")
        
        while True:
            cv2.imshow(title, marked_image)
            key = cv2.waitKey(1) & 0xFF
            
            if key == 27:  # ESC
                break
            elif key == ord('s'):  # 保存
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                # 保存截图
                img_path = os.path.join(self.output_dir, f"{title}_{timestamp}.png")
                cv2.imwrite(img_path, image)
                print(f"✓ 截图已保存: {img_path}")
                
                # 保存坐标
                if markers:
                    coord_path = os.path.join(self.output_dir, f"{title}_coords_{timestamp}.json")
                    with open(coord_path, 'w') as f:
                        json.dump({"markers": markers}, f, indent=2)
                    print(f"✓ 坐标已保存: {coord_path}")
                    print(f"标记的坐标点: {markers}")
                
                self.coordinate_map[title] = markers
        
        cv2.destroyAllWindows()
        return markers
    
    def capture_roi(self, name="roi_capture"):
        """交互式选择ROI区域并截图"""
        monitor = self.sct.monitors[self.capture_monitor_index]
        screenshot = np.array(self.sct.grab(monitor))
        screenshot_rgb = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2BGR)
        
        print(f"\n📍 选择 {name} ROI 区域")
        print("操作：在图像上拖动鼠标选择矩形区域，松开完成")
        
        roi = cv2.selectROI(name, screenshot_rgb, fromCenter=False, showCrosshair=True)
        cv2.destroyAllWindows()
        
        if roi[2] > 0 and roi[3] > 0:
            x, y, w, h = roi
            print(f"✓ ROI 已选择: x={x}, y={y}, 宽={w}, 高={h}")
            return roi
        return None


def main():
    """交互式数据采集主程序"""
    parser = argparse.ArgumentParser(description="游戏截图和坐标采集工具")
    parser.add_argument("--capture-monitor", type=int, default=2, help="要采集的显示器编号，默认1")
    args = parser.parse_args()

    collector = ScreenshotCollector(capture_monitor_index=args.capture_monitor)
    
    print("\n" + "="*60)
    print("🎮 游戏数据采集工具")
    print("="*60)
    print("\n这个工具将帮助你采集游戏截图和UI坐标信息。")
    print("请确保游戏窗口已经打开并处于可见状态。\n")
    print("可用显示器:")
    for index, monitor in enumerate(collector.list_monitors()):
        if index == 0:
            print(f"  {index}: 全虚拟屏幕 {monitor}")
        else:
            print(f"  {index}: {monitor}")
    print(f"\n当前采集目标显示器: {collector.capture_monitor_index}")
    print("提示：CMD 可以留在显示器1交互，脚本会去指定显示器采集。\n")
    
    tasks = [
        ("1. 准心居中 + 四个绿点 + 白色虚影的截图范围", lambda: collector.capture_and_display(name="task1_green_and_preview")),
        ("2. 只有中央四个绿点、没有白色虚影的截图范围", lambda: collector.capture_and_display(name="task2_green_only")),
        ("3. E面板染色界面：输入框范围 + 确认键范围", lambda: collector.capture_and_display(name="task3_e_panel_ui")),
    ]
    
    for idx, (desc, task) in enumerate(tasks, 1):
        print(f"\n[任务 {idx}/{len(tasks)}] {desc}")
        input("按 Enter 开始...")
        try:
            task()
        except Exception as e:
            print(f"❌ 采集失败: {e}")
    
    print("\n" + "="*60)
    print("✓ 数据采集完成！")
    print("="*60)
    print(f"\n采集到的坐标映射:")
    for key, markers in collector.coordinate_map.items():
        print(f"  • {key}: {markers}")
    
    # 保存坐标映射
    map_path = os.path.join(collector.output_dir, "coordinate_map.json")
    with open(map_path, 'w') as f:
        json.dump(collector.coordinate_map, f, indent=2)
    print(f"\n✓ 完整的坐标映射已保存到: {map_path}")


if __name__ == "__main__":
    main()
