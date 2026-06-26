from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class BuildConfig:
    blueprint_path: str
    dd_dll_path: str = "./dd63330.dll"
    monitor_index: int = 2
    roi_size: int = 315
    color_input_x: int = 2157
    color_input_y: int = 930
    confirm_button_x: int = 2222
    confirm_button_y: int = 1052
    horizontal_left_key: str = "a"
    horizontal_right_key: str = "d"
    vertical_up_key: str = "space"
    vertical_down_key: str = "alt"
    checkpoint_path: str = ".temp_checkpoint.json"
    dry_run: bool = False

    def resolved_checkpoint_path(self) -> Path:
        return Path(self.checkpoint_path)