from typing import Optional
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PIDConfig:
    kp: float = 0.4
    ki: float = 0.0
    kd: float = 0.0
    deadzone: float = 2.0
    max_step: int = 12


class PIDController:
    def __init__(self, config: Optional[PIDConfig]= None):
        self.config = config or PIDConfig()
        self._integral_x = 0.0
        self._integral_y = 0.0
        self._prev_error_x = 0.0
        self._prev_error_y = 0.0

    def reset(self) -> None:
        self._integral_x = 0.0
        self._integral_y = 0.0
        self._prev_error_x = 0.0
        self._prev_error_y = 0.0

    def compute(self, error_x: float, error_y: float) -> tuple[int, int, bool]:
        if abs(error_x) <= self.config.deadzone and abs(error_y) <= self.config.deadzone:
            return 0, 0, True

        self._integral_x += error_x
        self._integral_y += error_y
        derivative_x = error_x - self._prev_error_x
        derivative_y = error_y - self._prev_error_y
        self._prev_error_x = error_x
        self._prev_error_y = error_y

        move_x = self._calc_step(error_x, self._integral_x, derivative_x)
        move_y = self._calc_step(error_y, self._integral_y, derivative_y)
        return move_x, move_y, False

    def _calc_step(self, error: float, integral: float, derivative: float) -> int:
        raw = (
            error * self.config.kp
            + integral * self.config.ki
            + derivative * self.config.kd
        )
        step = int(round(raw))
        if step == 0 and abs(error) > self.config.deadzone:
            step = 1 if error > 0 else -1
        if step > self.config.max_step:
            return self.config.max_step
        if step < -self.config.max_step:
            return -self.config.max_step
        return step