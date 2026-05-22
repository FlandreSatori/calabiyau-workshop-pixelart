from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json


@dataclass(frozen=True)
class PixelBlock:
    x: int
    y: int
    color: str


@dataclass
class Blueprint:
    version: int = 1
    resolution: tuple[int, int] = (0, 0)
    start_pos: dict[str, int] = field(default_factory=lambda: {"x": 0, "y": 0})
    blocks: list[PixelBlock] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "resolution": list(self.resolution),
            "start_pos": dict(self.start_pos),
            "blocks": [block.__dict__ for block in self.blocks],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Blueprint":
        blocks = [PixelBlock(**item) for item in data.get("blocks", [])]
        resolution = data.get("resolution", [0, 0])
        return cls(
            version=int(data.get("version", 1)),
            resolution=(int(resolution[0]), int(resolution[1])),
            start_pos=dict(data.get("start_pos", {"x": 0, "y": 0})),
            blocks=blocks,
        )

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "Blueprint":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(data)