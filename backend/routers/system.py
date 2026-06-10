import json
import os
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.window_manager import WindowManager
from backend.task_manager import TaskManager

router = APIRouter()


class BlockLibraryPayload(BaseModel):
    blocks: list[dict] = Field(default_factory=list)
    hotbar_slots: list = Field(default_factory=list)


def get_app_base_dir() -> Path:
    env_base = os.getenv("PYDD_APP_BASE_DIR")
    if env_base:
        return Path(env_base).resolve()
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def get_app_base_dirs() -> list[Path]:
    dirs: list[Path] = []

    env_base = os.getenv("PYDD_APP_BASE_DIR")
    if env_base:
        dirs.append(Path(env_base).resolve())

    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        dirs.append(exe_dir)
        dirs.append(exe_dir.parent)

    cwd = Path.cwd().resolve()

    # If launched from source but dist exists beside cwd, prefer dist first.
    cwd_dist = cwd / "dist"
    if cwd_dist.exists() and cwd_dist.is_dir():
        dirs.append(cwd_dist)

    dirs.append(cwd)
    dirs.append(cwd.parent)

    # Source workspace fallback (dev mode)
    src_root = Path(__file__).resolve().parents[2]
    src_dist = src_root / "dist"
    if src_dist.exists() and src_dist.is_dir():
        dirs.append(src_dist)
    dirs.append(src_root)

    unique: list[Path] = []
    seen = set()
    for d in dirs:
        key = str(d)
        if key in seen:
            continue
        seen.add(key)
        unique.append(d)
    return unique


def resolve_local_path(rel_path: str) -> Path:
    base_dir = get_app_base_dir().resolve()
    normalized = rel_path.replace("\\", "/").strip().lstrip("/")
    if not normalized:
        raise HTTPException(status_code=400, detail="path_is_empty")
    candidate = (base_dir / normalized).resolve()
    if base_dir not in candidate.parents and candidate != base_dir:
        raise HTTPException(status_code=400, detail="path_outside_base_dir")
    return candidate


def resolve_local_path_with_base(rel_path: str, base_dir: Path) -> Path:
    normalized = rel_path.replace("\\", "/").strip().lstrip("/")
    if not normalized:
        raise HTTPException(status_code=400, detail="path_is_empty")
    candidate = (base_dir / normalized).resolve()
    if base_dir not in candidate.parents and candidate != base_dir:
        raise HTTPException(status_code=400, detail="path_outside_base_dir")
    return candidate


@router.get("/windows")
def list_windows():
    return {"status": "success", "windows": WindowManager.list_windows()}


@router.get("/foreground")
def get_foreground_window():
    windows = WindowManager.list_windows()
    current = next((window for window in windows if window["is_foreground"]), None)
    return {"status": "success", "window": current}


@router.post("/activate")
def activate_window(payload: dict):
    """Activate a window by hwnd or by exe_name.

    payload: { hwnd?: int, exe_name?: str }
    """
    hwnd = payload.get("hwnd")
    exe_name = payload.get("exe_name")

    if hwnd is not None:
        ok = WindowManager.activate_hwnd(int(hwnd))
        return {"status": "success" if ok else "fail", "by": "hwnd", "hwnd": hwnd}

    if exe_name:
        ok = WindowManager.activate_window(str(exe_name))
        return {"status": "success" if ok else "fail", "by": "exe_name", "exe_name": exe_name}

    return {"status": "fail", "detail": "missing hwnd or exe_name"}


@router.post("/continue")
def continue_tasks():
    """Resume any paused background tasks (user clicked Continue)."""
    TaskManager.resume_all()
    return {"status": "success", "detail": "resumed"}


@router.get("/paused")
def is_paused():
    return {"status": "success", "paused": TaskManager.is_paused()}

@router.post("/abort")
def abort_tasks():
    """Abort any paused background tasks (user clicked Force Stop)."""
    TaskManager.abort_all()
    return {"status": "success", "detail": "aborted"}


@router.get("/block-library")
def get_block_library():
    library_path = None
    for base_dir in get_app_base_dirs():
        p = base_dir / "block_library.json"
        if p.exists() and p.is_file():
            library_path = p
            break
    if library_path is None:
        return {
            "status": "not_found",
            "blocks": [],
            "hotbar_slots": [],
            "searched_dirs": [str(d) for d in get_app_base_dirs()],
        }
    try:
        data = json.loads(library_path.read_text(encoding="utf-8"))
        blocks = data.get("blocks", [])
        hotbar_slots = data.get("hotbar_slots", [])
        return {
            "status": "success",
            "source": str(library_path),
            "blocks": blocks,
            "hotbar_slots": hotbar_slots,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"failed_to_read_block_library: {exc}")


@router.post("/block-library")
def save_block_library(payload: BlockLibraryPayload):
    base_dir = get_app_base_dir()
    library_path = base_dir / "block_library.json"
    data = {
        "blocks": payload.blocks,
        "hotbar_slots": payload.hotbar_slots,
    }
    try:
        library_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"status": "success", "path": str(library_path)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"failed_to_save_block_library: {exc}")


@router.get("/runtime-paths")
def runtime_paths():
    return {
        "status": "success",
        "env_base": os.getenv("PYDD_APP_BASE_DIR"),
        "cwd": str(Path.cwd().resolve()),
        "exe": sys.executable,
        "searched_dirs": [str(d) for d in get_app_base_dirs()],
    }


@router.get("/local-file")
def get_local_file(path: str = Query(..., min_length=1), fallback: str = Query("")):
    candidates = [path]
    if fallback:
        candidates.extend([p for p in fallback.split("|") if p])

    tried: list[str] = []
    for rel in candidates:
        for base in get_app_base_dirs():
            try:
                resolved = resolve_local_path_with_base(rel, base)
            except HTTPException:
                continue
            tried.append(str(resolved))
            if resolved.exists() and resolved.is_file():
                return FileResponse(path=str(resolved), filename=resolved.name)

    raise HTTPException(status_code=404, detail={"message": "file_not_found", "tried": tried})
