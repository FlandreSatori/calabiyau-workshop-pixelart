from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations
from typing import Optional

import cv2
import mss
import numpy as np

from window_manager import WindowManager


@dataclass
class MarkerObservation:
    x: float
    y: float
    radius: float
    arc_ratio: float
    green_ratio: float


@dataclass
class AlignmentResult:
    has_target: bool
    horizontal_error: float
    center_offset_x: float
    center_offset_y: float
    confidence: float
    source: str
    markers: tuple[MarkerObservation, ...] = field(default_factory=tuple)


class VisionCore:
    def __init__(self, roi_size: int = 850, monitor_index: int = 1, exe_name: str = "Calabiyau-Win64-Shipping.exe"):
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
            markers=tuple(),
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

    def _estimate_square_horizontal_error(self, points: list[tuple[float, float]]) -> Optional[float]:
        """Estimate horizontal error from marker edges to avoid diagonal-angle bias."""
        if len(points) < 4:
            return None

        edge_candidates: list[tuple[float, float]] = []
        for i in range(len(points)):
            x1, y1 = points[i]
            for j in range(i + 1, len(points)):
                x2, y2 = points[j]
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

    @staticmethod
    def _marker_score(marker: MarkerObservation) -> float:
        return float(max(0.0, marker.arc_ratio) * max(0.05, marker.green_ratio) * max(2.0, marker.radius))

    def _build_marker_masks(self, frame: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # 绿色圆点: RGB (0,245~255,0~30)
        green_mask = cv2.inRange(
            rgb,
            np.array([0, 245, 0], dtype=np.uint8),
            np.array([30, 255, 30], dtype=np.uint8),
        )
        # 白色虚影遮挡叠加色: RGB (160~175,190~205,160~175)
        ghost_mask = cv2.inRange(
            rgb,
            np.array([160, 190, 160], dtype=np.uint8),
            np.array([175, 205, 175], dtype=np.uint8),
        )

        combined = cv2.bitwise_or(green_mask, ghost_mask)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel, iterations=1)
        combined = cv2.morphologyEx(combined, cv2.MORPH_OPEN, kernel, iterations=1)
        return combined, green_mask, ghost_mask

    def _fit_marker_from_contour(self, contour: np.ndarray, green_mask: np.ndarray) -> Optional[MarkerObservation]:
        area = float(cv2.contourArea(contour))
        if area < 35.0:
            return None

        (cx, cy), radius = cv2.minEnclosingCircle(contour)
        radius = float(radius)
        if radius < 4.0 or radius > float(self.roi_size) * 0.6:
            return None

        circle_area = float(np.pi * radius * radius)
        if circle_area <= 1e-6:
            return None

        # quarter/half/3-quarter/full circle are all allowed
        fill_ratio = area / circle_area
        if fill_ratio < 0.10 or fill_ratio > 1.25:
            return None

        pts = contour.reshape(-1, 2).astype(np.float32)
        if pts.shape[0] < 5:
            return None

        d = np.hypot(pts[:, 0] - float(cx), pts[:, 1] - float(cy))
        spread = float(np.std(d) / max(1e-6, float(np.mean(d))))
        if spread > 0.40:
            return None

        contour_mask = np.zeros(green_mask.shape, dtype=np.uint8)
        cv2.drawContours(contour_mask, [contour], -1, 255, thickness=-1)
        total_pixels = int(cv2.countNonZero(contour_mask))
        if total_pixels <= 0:
            return None

        green_pixels = int(cv2.countNonZero(cv2.bitwise_and(green_mask, contour_mask)))
        green_ratio = float(green_pixels) / float(total_pixels)

        return MarkerObservation(
            x=float(cx),
            y=float(cy),
            radius=radius,
            arc_ratio=float(np.clip(fill_ratio, 0.0, 1.0)),
            green_ratio=green_ratio,
        )

    def _dedupe_markers(self, markers: list[MarkerObservation]) -> list[MarkerObservation]:
        if not markers:
            return []

        sorted_markers = sorted(markers, key=self._marker_score, reverse=True)
        kept: list[MarkerObservation] = []
        for marker in sorted_markers:
            duplicate = False
            for existing in kept:
                distance = float(np.hypot(marker.x - existing.x, marker.y - existing.y))
                merge_dist = max(2.5, min(marker.radius, existing.radius) * 0.7)
                if distance <= merge_dist:
                    duplicate = True
                    break
            if not duplicate:
                kept.append(marker)
        return kept

    def _square_shape_score(self, markers: list[MarkerObservation]) -> float:
        points = [(m.x, m.y) for m in markers]
        dists: list[float] = []
        for i in range(len(points)):
            x1, y1 = points[i]
            for j in range(i + 1, len(points)):
                x2, y2 = points[j]
                dists.append(float(np.hypot(x2 - x1, y2 - y1)))

        if len(dists) != 6:
            return -1e9

        dists.sort()
        edges = np.array(dists[:4], dtype=np.float32)
        diags = np.array(dists[4:], dtype=np.float32)
        edge_mean = float(np.mean(edges))
        diag_mean = float(np.mean(diags))
        if edge_mean <= 1e-6 or diag_mean <= 1e-6:
            return -1e9

        ratio = diag_mean / edge_mean
        if ratio < 1.20 or ratio > 1.80:
            return -1e9

        edge_cv = float(np.std(edges) / edge_mean)
        diag_cv = float(np.std(diags) / diag_mean)
        quality = float(np.mean([m.arc_ratio for m in markers]))
        return quality - (edge_cv * 1.4 + diag_cv * 1.1 + abs(ratio - np.sqrt(2.0)) * 0.8)

    def _select_best_four_markers(self, markers: list[MarkerObservation]) -> list[MarkerObservation]:
        if len(markers) < 4:
            return []
        if len(markers) == 4:
            return markers

        best_score = -1e9
        best_group: Optional[list[MarkerObservation]] = None
        candidates = sorted(markers, key=self._marker_score, reverse=True)[:8]
        for combo in combinations(candidates, 4):
            group = list(combo)
            score = self._square_shape_score(group)
            if score > best_score:
                best_score = score
                best_group = group

        return best_group if best_group is not None else []

    def _extract_four_markers(self, frame: np.ndarray) -> list[MarkerObservation]:
        combined_mask, green_mask, _ = self._build_marker_masks(frame)
        contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        candidates: list[MarkerObservation] = []
        for contour in contours:
            marker = self._fit_marker_from_contour(contour, green_mask)
            if marker is not None:
                candidates.append(marker)

        if len(candidates) < 4:
            return []

        deduped = self._dedupe_markers(candidates)
        if len(deduped) < 4:
            return []

        chosen = self._select_best_four_markers(deduped)
        if len(chosen) != 4:
            return []

        return chosen

    def _analyze_green_markers(self, frame: np.ndarray) -> Optional[AlignmentResult]:
        markers = self._extract_four_markers(frame)
        if len(markers) != 4:
            return None

        xs = np.array([m.x for m in markers], dtype=np.float32)
        ys = np.array([m.y for m in markers], dtype=np.float32)
        center_x = float(np.mean(xs))
        center_y = float(np.mean(ys))

        estimated_error = self._estimate_square_horizontal_error([(m.x, m.y) for m in markers])
        if estimated_error is not None:
            horizontal_error = estimated_error
        else:
            left_index = int(np.argmin(xs))
            right_index = int(np.argmax(xs))
            dx = float(xs[right_index] - xs[left_index])
            dy = float(ys[right_index] - ys[left_index])
            horizontal_error = float(np.degrees(np.arctan2(dy, dx if abs(dx) > 1e-6 else 1e-6)))

        mean_arc = float(np.mean([m.arc_ratio for m in markers]))
        mean_green = float(np.mean([m.green_ratio for m in markers]))
        confidence = float(np.clip(0.55 * mean_arc + 0.45 * mean_green, 0.0, 1.0))

        return AlignmentResult(
            has_target=True,
            horizontal_error=horizontal_error,
            center_offset_x=center_x - self.center,
            center_offset_y=center_y - self.center,
            confidence=confidence,
            source="green_markers_4pts",
            markers=tuple(markers),
        )

    def measure_green_marker_edge_length(self, frame: np.ndarray) -> Optional[float]:
        """Measure representative edge length between green markers."""
        markers = self._extract_four_markers(frame)
        if len(markers) != 4:
            return None

        points = [(m.x, m.y) for m in markers]
        dists: list[float] = []
        for i in range(len(points)):
            x1, y1 = points[i]
            for j in range(i + 1, len(points)):
                x2, y2 = points[j]
                dists.append(float(np.hypot(x2 - x1, y2 - y1)))

        if len(dists) != 6:
            return None

        dists.sort()
        edge_sample = dists[:4]
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