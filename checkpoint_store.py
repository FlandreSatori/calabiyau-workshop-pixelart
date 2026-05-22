from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json


@dataclass
class Checkpoint:
    block_index: int = 0
    row_index: int = 0
    column_index: int = 0
    direction: str = "right"


class CheckpointStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load(self) -> Checkpoint | None:
        if not self.path.exists():
            return None
        data: dict[str, Any] = json.loads(self.path.read_text(encoding="utf-8"))
        return Checkpoint(
            block_index=int(data.get("block_index", 0)),
            row_index=int(data.get("row_index", 0)),
            column_index=int(data.get("column_index", 0)),
            direction=str(data.get("direction", "right")),
        )

    def save(self, checkpoint: Checkpoint) -> None:
        self.path.write_text(
            json.dumps(
                {
                    "block_index": checkpoint.block_index,
                    "row_index": checkpoint.row_index,
                    "column_index": checkpoint.column_index,
                    "direction": checkpoint.direction,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def clear(self) -> None:
        if self.path.exists():
            self.path.unlink()