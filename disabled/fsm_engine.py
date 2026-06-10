from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from collections import defaultdict
from typing import Sequence, Optional

from backend.blueprint_model import Blueprint
from build_config import BuildConfig
from checkpoint_store import Checkpoint, CheckpointStore
from backend.movement_controller import MovementController
from backend.ui_interaction import UIInteraction


class BuildState(Enum):
    INIT = auto()
    PLACE = auto()
    DYE = auto()
    NEXT_BLOCK = auto()
    NEXT_ROW = auto()
    DONE = auto()


@dataclass
class BuildContext:
    blueprint: Blueprint
    color_input_x: int = 0
    color_input_y: int = 0
    confirm_button_x: int = 0
    confirm_button_y: int = 0


@dataclass(frozen=True)
class PlannedBlock:
    x: int
    y: int
    color: str
    row_index: int
    column_index: int
    direction: str


class BuildFSM:
    def __init__(self, dd, vision, context: BuildContext, config: BuildConfig):
        self.dd = dd
        self.vision = vision
        self.context = context
        self.config = config
        self.movement = MovementController(dd, vision)
        self.ui = UIInteraction(dd)
        self.state = BuildState.INIT
        self.current_index = 0
        self.checkpoints = CheckpointStore(config.checkpoint_path)
        self.plan = self._plan_blocks(context.blueprint)
        self.resume_from_checkpoint()

    def run(self) -> None:
        while self.state is not BuildState.DONE:
            if self.state is BuildState.INIT:
                self._step_init()
                print(f"分 {max(block.row_index for block in self.plan) + 1} 行")
            elif self.state is BuildState.PLACE:
                self._step_place()
                print(f"放置第 {self.current_index + 1}/{len(self.plan)} 个方块")
            elif self.state is BuildState.DYE:
                self._step_dye()
                print(f"染色第 {self.current_index + 1}/{len(self.plan)} 个方块")
            elif self.state is BuildState.NEXT_BLOCK:
                self._step_next_block()
                print(f"移动到下一个方块")
            elif self.state is BuildState.NEXT_ROW:
                self._step_next_row()
                print(f"进入下一行")

    def _plan_blocks(self, blueprint: Blueprint) -> list[PlannedBlock]:
        rows: dict[int, list[tuple[int, str]]] = defaultdict(list)
        for block in blueprint.blocks:
            rows[int(block.y)].append((int(block.x), block.color))

        planned: list[PlannedBlock] = []
        # 从图形的最底部（y最大的行）开始往上逆序构建
        for row_index, y in enumerate(sorted(rows.keys(), reverse=True)):
            ordered = sorted(rows[y], key=lambda item: item[0])
            if row_index % 2 == 1:
                ordered = list(reversed(ordered))
                direction = "left"
            else:
                direction = "right"

            for column_index, (x, color) in enumerate(ordered):
                planned.append(
                    PlannedBlock(
                        x=x,
                        y=y,
                        color=color,
                        row_index=row_index,
                        column_index=column_index,
                        direction=direction,
                    )
                )
        return planned

    def resume_from_checkpoint(self) -> None:
        checkpoint = self.checkpoints.load()
        if checkpoint is None:
            return
        self.current_index = min(checkpoint.block_index, len(self.plan))

    def _save_checkpoint(self) -> None:
        current = self._current_planned_block()
        if current is None:
            return
        self.checkpoints.save(
            Checkpoint(
                block_index=self.current_index,
                row_index=current.row_index,
                column_index=current.column_index,
                direction=current.direction,
            )
        )

    def _current_planned_block(self) -> Optional[PlannedBlock]:
        if self.current_index < 0 or self.current_index >= len(self.plan):
            return None
        return self.plan[self.current_index]

    def _next_planned_block(self) -> Optional[PlannedBlock]:
        next_index = self.current_index + 1
        if next_index < 0 or next_index >= len(self.plan):
            return None
        return self.plan[next_index]

    def _step_init(self) -> None:
        self.state = BuildState.PLACE

    def _step_place(self) -> None:
        import time
        current = self._current_planned_block()
        if current is None:
            self.state = BuildState.DONE
            return

        if not self.config.dry_run:
            # 切换到铁板模式用于确认方块
            self.dd.key_press("1")
            time.sleep(0.1)
            
            # 直接切换到要放置的方块，不再改变鼠标视角
            self.dd.key_press("2")
            time.sleep(0.1)
            
        self.dd.mouse_click("left")
        time.sleep(0.1)
        self.state = BuildState.DYE

    def _step_dye(self) -> None:
        import time
        current = self._current_planned_block()
        if current is None:
            self.state = BuildState.DONE
            return

        self.ui.open_color_panel()
        time.sleep(0.1)
        self.ui.paste_hex_color(self.context.color_input_x, self.context.color_input_y, current.color)
        
        if self.context.confirm_button_x and self.context.confirm_button_y:
            print(f"[{current.color}] 移动并点击确认按钮坐标: ({self.context.confirm_button_x}, {self.context.confirm_button_y})")
            self.ui.click_confirm(self.context.confirm_button_x, self.context.confirm_button_y)

        time.sleep(0.1)

        self.state = BuildState.NEXT_BLOCK

    def _step_next_block(self) -> None:
        import time
        current = self._current_planned_block()
        next_block = self._next_planned_block()
        self._save_checkpoint()

        if current is None or next_block is None:
            self.state = BuildState.DONE
            self.checkpoints.clear()
            return

        # 换回铁板模式以便持续获得绿色准心进行横向平移
        if not self.config.dry_run:
            self.dd.key_press("1")
            time.sleep(0.1)

        if next_block.row_index == current.row_index:
            direction = self.config.horizontal_right_key if next_block.direction == "right" else self.config.horizontal_left_key
            self.movement.move_to_next_block(direction)
        else:
            # 图像的 Y 坐标越小，代表越靠近顶部。因此当 next_block.y 小于 current.y 时，是在往上层搭 (对应 Space)
            up_or_down = self.config.vertical_up_key if next_block.y < current.y else self.config.vertical_down_key
            self.movement.move_to_next_block(up_or_down)

        self.current_index += 1
        self.state = BuildState.PLACE

    def _step_next_row(self) -> None:
        self.state = BuildState.PLACE