from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import cv2
import mss
import numpy as np

from window_manager import WindowManager


@dataclass
class AlignmentResult:
    has_target: bool
    horizontal_error: float
    center_offset_x: float
    center_offset_y: float
    confidence: float
    source: str


class VisionCore:
    def __init__(self, roi_size: int = 200, monitor_index: int = 1, exe_name: str = "Calabiyau-Win64-Shipping.exe"):
        self.roi_size = roi_size
        self.monitor_index = monitor_index
        self.exe_name = exe_name
        self.sct = mss.mss()
        self.center = roi_size / 2.0

    def get_capture_region(self) -> dict[str, int]:
        """动态获取截图区域：优先根据游戏窗口，如果未找到则退回到显示器索引"""
        rect = WindowManager.get_window_rect(self.exe_name)
        if rect:
            left, top, width, height = rect
            cx = int(left + width / 2 - self.roi_size / 2)
            cy = int(top + height / 2 - self.roi_size / 2)
            return {"left": cx, "top": cy, "width": self.roi_size, "height": self.roi_size}
        else:
            # 回退到显示器
            monitor = self.sct.monitors[self.monitor_index]
            cx = int(monitor["left"] + monitor["width"] / 2 - self.roi_size / 2)
            cy = int(monitor["top"] + monitor["height"] / 2 - self.roi_size / 2)
            return {"left": cx, "top": cy, "width": self.roi_size, "height": self.roi_size}

    def capture_roi(self) -> np.ndarray:
        region = self.get_capture_region()
        frame = np.array(self.sct.grab(region), dtype=np.uint8)
        return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

    def analyze_roi(self, frame: np.ndarray) -> AlignmentResult:
        green_result = self._analyze_green_markers(frame)
        if green_result is not None:
            return green_result

        return AlignmentResult(False, 0.0, 0.0, 0.0, 0.0, "none")

    def detect_alignment(self) -> AlignmentResult:
        return self.analyze_roi(self.capture_roi())

    def is_level(self, tolerance_degrees: float = 1.5) -> bool:
        result = self.detect_alignment()
        if not result.has_target:
            return False
        return abs(result.horizontal_error) <= tolerance_degrees

    def analyze_white_ghost_diff(self, frame_with_ghost: np.ndarray, frame_without_ghost: np.ndarray) -> Optional[AlignmentResult]:
        if frame_with_ghost.shape != frame_without_ghost.shape:
            return None
        # 根据用户要求：不要对差分图像做额外的形态学或轮廓处理
        # 直接使用差分图像中的非零像素计算主方向并返回 horizontal_error
        diff = cv2.absdiff(frame_with_ghost, frame_without_ghost)
        gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)

        ys, xs = np.nonzero(gray)
        if xs.size == 0:
            return None

        points = np.column_stack((xs.astype(np.float32), ys.astype(np.float32)))
        if points.shape[0] < 3:
            return None

        center = np.mean(points, axis=0)
        centered = points - center
        cov = np.cov(centered.T)
        eigvals, eigvecs = np.linalg.eigh(cov)
        major_axis = eigvecs[:, int(np.argmax(eigvals))]
        angle = float(np.degrees(np.arctan2(float(major_axis[1]), float(major_axis[0]))))

        horizontal_error = self._normalize_angle_180(angle)
        if horizontal_error > 45.0:
            horizontal_error -= 90.0
        elif horizontal_error < -45.0:
            horizontal_error += 90.0

        major_idx = int(np.argmax(eigvals))
        minor_idx = int(np.argmin(eigvals))
        anisotropy = 1.0
        if float(eigvals[major_idx]) > 1e-6:
            anisotropy = 1.0 - min(1.0, float(eigvals[minor_idx]) / float(eigvals[major_idx]))

        area = float(points.shape[0])
        confidence = min(1.0, (area / float(self.roi_size * self.roi_size)) * 12.0 * max(0.25, anisotropy))

        return AlignmentResult(
            has_target=True,
            horizontal_error=horizontal_error,
            center_offset_x=float(center[0] - self.center),
            center_offset_y=float(center[1] - self.center),
            confidence=confidence,
            source="white_ghost_diff",
        )

    @staticmethod
    def _normalize_angle_180(angle_deg: float) -> float:
        """Normalize angle to [-90, 90)."""
        return float(((angle_deg + 90.0) % 180.0) - 90.0)

    @staticmethod
    def _to_horizontal_equivalent(angle_deg: float) -> float:
        """Fold an edge angle to its horizontal-equivalent angle in [-45, 45]."""
        angle = VisionCore._normalize_angle_180(angle_deg)
        if angle > 45.0:
            angle -= 90.0
        elif angle < -45.0:
            angle += 90.0
        return float(angle)

    def _estimate_square_horizontal_error(self, points: list[tuple[float, float, float]]) -> Optional[float]:
        """Estimate horizontal error from marker edges to avoid diagonal-angle bias."""
        if len(points) < 4:
            return None

        edge_candidates: list[tuple[float, float]] = []
        for i in range(len(points)):
            x1, y1, _ = points[i]
            for j in range(i + 1, len(points)):
                x2, y2, _ = points[j]
                dx = float(x2 - x1)
                dy = float(y2 - y1)
                dist = float(np.hypot(dx, dy))
                if dist <= 1e-6:
                    continue
                angle = float(np.degrees(np.arctan2(dy, dx)))
                edge_candidates.append((dist, self._normalize_angle_180(angle)))

        if len(edge_candidates) < 4:
            return None

        # In a square, 4 shortest pairs are edges and 2 longest are diagonals.
        edge_candidates.sort(key=lambda item: item[0])
        shortest_edges = edge_candidates[:4]
        horizontal_angles = [self._to_horizontal_equivalent(a) for _, a in shortest_edges]

        median_angle = float(np.median(horizontal_angles))
        inliers = [a for a in horizontal_angles if abs(a - median_angle) <= 12.0]
        if not inliers:
            inliers = horizontal_angles

        return float(np.mean(inliers))

    def _analyze_green_markers(self, frame: np.ndarray) -> Optional[AlignmentResult]:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # 严格锁定 #00f700（荧光绿）附近的颜色，排除暗绿和灰绿
        lower_green = np.array([50, 150, 150], dtype=np.uint8)
        upper_green = np.array([70, 255, 255], dtype=np.uint8)
        mask = cv2.inRange(hsv, lower_green, upper_green)
        
        # 闭运算连接断裂的圆弧
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        points: list[tuple[float, float, float]] = []

        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 300:  # 容忍 1/4 圆弧
                continue
                
            pts = contour.reshape(-1, 2).astype(np.float32)
            if len(pts) < 3:
                continue

            try:
                # 代数圆拟合，找回被遮挡圆弧的真实圆心
                x = pts[:, 0]
                y = pts[:, 1]
                z = x**2 + y**2
                A = np.column_stack([x, y, np.ones_like(x)])
                c, _, _, _ = np.linalg.lstsq(A, z, rcond=None)
                
                a = float(c[0] / 2.0)
                b = float(c[1] / 2.0)
                fitted_radius = float(np.sqrt(max(0, c[2] + a**2 + b**2)))
                
                # 过滤异常半径
                if 20.0 < fitted_radius < 200.0:
                    points.append((a, b, float(area)))
            except Exception:
                continue

        # 【修改点】：至少要求 3 个点
        if len(points) < 3:
            return None

        # 按面积取最大的前 4 个点
        points.sort(key=lambda item: item[2], reverse=True)
        points = points[:4]
        
        xs = np.array([p[0] for p in points], dtype=np.float32)
        ys = np.array([p[1] for p in points], dtype=np.float32)
        
        # 【核心几何优化】：精准计算中心
        if len(points) == 4:
            # 4个点齐备，均值即为正中心
            center_x = float(np.mean(xs))
            center_y = float(np.mean(ys))
        else:
            # 只有3个点时，寻找距离最远的两个点（正方形的对角线）
            max_dist = 0
            diag_p1, diag_p2 = (0.0, 0.0), (0.0, 0.0)
            for i in range(3):
                for j in range(i + 1, 3):
                    d = (xs[i] - xs[j])**2 + (ys[i] - ys[j])**2
                    if d > max_dist:
                        max_dist = d
                        diag_p1 = (xs[i], ys[i])
                        diag_p2 = (xs[j], ys[j])
            # 对角线的中点就是绝对的方块正中心，拒绝偏移！
            center_x = float((diag_p1[0] + diag_p2[0]) / 2.0)
            center_y = float((diag_p1[1] + diag_p2[1]) / 2.0)

        # 估算倾斜角
        if len(points) == 4:
            estimated_error = self._estimate_square_horizontal_error(points)
            if estimated_error is not None:
                horizontal_error = estimated_error
            else:
                left_index = int(np.argmin(xs))
                right_index = int(np.argmax(xs))
                dx = float(xs[right_index] - xs[left_index])
                dy = float(ys[right_index] - ys[left_index])
                horizontal_error = float(np.degrees(np.arctan2(dy, dx if abs(dx) > 1e-6 else 1e-6)))
        else:
            # 3个点时，直接找最左和最右的点建立水平基线
            left_index = int(np.argmin(xs))
            right_index = int(np.argmax(xs))
            dx = float(xs[right_index] - xs[left_index])
            dy = float(ys[right_index] - ys[left_index])
            horizontal_error = float(np.degrees(np.arctan2(dy, dx if abs(dx) > 1e-6 else 1e-6)))

        # 置信度计算
        confidence = min(1.0, len(points) / 4.0)

        return AlignmentResult(
            has_target=True,
            horizontal_error=horizontal_error,
            center_offset_x=center_x - self.center,
            center_offset_y=center_y - self.center,
            confidence=confidence,
            source="green_markers",
        )

    def measure_green_marker_edge_length(self, frame: np.ndarray) -> Optional[float]:
        """Measure representative edge length between green markers."""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # 保持一致的纯绿色阈值
        lower_green = np.array([50, 150, 150], dtype=np.uint8)
        upper_green = np.array([70, 255, 255], dtype=np.uint8)
        mask = cv2.inRange(hsv, lower_green, upper_green)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        points: list[tuple[float, float]] = []
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 300:
                continue
                
            pts = contour.reshape(-1, 2).astype(np.float32)
            if len(pts) < 3:
                continue

            try:
                x = pts[:, 0]
                y = pts[:, 1]
                z = x**2 + y**2
                A = np.column_stack([x, y, np.ones_like(x)])
                c, _, _, _ = np.linalg.lstsq(A, z, rcond=None)
                
                a = float(c[0] / 2.0)
                b = float(c[1] / 2.0)
                fitted_radius = float(np.sqrt(max(0, c[2] + a**2 + b**2)))
                
                if 2.0 < fitted_radius < 200.0:
                    points.append((a, b))
            except Exception:
                continue

        if len(points) < 3:
            return None

        dists: list[float] = []
        for i in range(len(points)):
            x1, y1 = points[i]
            for j in range(i + 1, len(points)):
                x2, y2 = points[j]
                dists.append(float(np.hypot(x2 - x1, y2 - y1)))

        if not dists:
            return None

        dists.sort()
        # 对于 3 个点，会产生 3 条距离。前 2 条短的是边长，最长的那条是对角线。
        # 取前两条边长求平均（或直接用最短的边长）
        if len(points) == 3:
            return float(np.mean(dists[:2]))
            
        # 4 个点时，照旧取前4短的距离求中位数
        edge_sample = dists[:4] if len(dists) >= 4 else dists
        return float(np.median(edge_sample))

    # def _analyze_white_preview(self, frame: np.ndarray) -> Optional[AlignmentResult]:
    #     hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    #     lower_white = np.array([0, 0, 170], dtype=np.uint8)
    #     upper_white = np.array([180, 60, 255], dtype=np.uint8)
    #     mask = cv2.inRange(hsv, lower_white, upper_white)
    #     mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    #     mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))

    #     contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    #     if not contours:
    #         return None

    #     contour = max(contours, key=cv2.contourArea)
    #     if cv2.contourArea(contour) < 15:
    #         return None

    #     rect = cv2.minAreaRect(contour)
    #     (center_x, center_y), (_, _), angle = rect
    #     horizontal_error = float(angle)
    #     if horizontal_error < -45.0:
    #         horizontal_error += 90.0

    #     return AlignmentResult(
    #         has_target=True,
    #         horizontal_error=horizontal_error,
    #         center_offset_x=float(center_x - self.center),
    #         center_offset_y=float(center_y - self.center),
    #         confidence=min(1.0, cv2.contourArea(contour) / float(self.roi_size * self.roi_size)),
    #         source="white_preview",
    #     )