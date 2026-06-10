import tempfile
import os
import asyncio
from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from backend.image_to_blueprint import image_to_blueprint
from backend.log_manager import manager

router = APIRouter()

@router.post("/process")
async def process_blueprint(
    file: UploadFile = File(...),
    width: int = Form(32),
    height: int = Form(32)
):
    try:
        await manager.broadcast(f"正在处理上传的图像: {file.filename}，目标尺寸: {width}x{height}")
        
        # Save uploaded file to a temporary file
        fd, temp_input_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        
        fd_out, temp_output_path = tempfile.mkstemp(suffix=".json")
        os.close(fd_out)
        
        with open(temp_input_path, "wb") as buffer:
            buffer.write(await file.read())
        
        # Call the original synchronous function in a thread to unblock
        blueprint = await asyncio.to_thread(
            image_to_blueprint,
            temp_input_path,
            temp_output_path,
            width,
            height
        )
        
        await manager.broadcast(f"蓝图生成成功，共包含 {len(blueprint.blocks)} 个方块。")
        
        # Blueprint is a dataclass-backed model, so serialize via to_dict().
        resp = blueprint.to_dict()
        
        # Cleanup
        os.remove(temp_input_path)
        os.remove(temp_output_path)
        
        return {"status": "success", "blueprint": resp}

    except Exception as e:
        await manager.broadcast(f"蓝图处理失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

from pydantic import BaseModel, Field
from typing import List, Dict, Any

class PlanRequest(BaseModel):
    blueprint: Dict[str, Any]
    pending_blocks: List[str] = Field(default_factory=list)
    completed_blocks: List[str] = Field(default_factory=list)

@router.post("/plan")
def plan_pipeline(req: PlanRequest):
    blocks = req.blueprint.get("blocks", [])
    if not blocks:
        return {"pipeline": [], "is_fallback": False}
    
    blocks_by_coord = {(int(b["x"]), int(b["y"])): b.get("color", "#FFFFFF") for b in blocks}
    
    completed = set()
    for s in req.completed_blocks:
        try:
            x, y = map(int, s.split(","))
            completed.add((x, y))
        except:
            pass

    pending = set()
    for s in req.pending_blocks:
        try:
            x, y = map(int, s.split(","))
            pending.add((x, y))
        except:
            pass

    remaining_blocks = set(blocks_by_coord.keys()) - completed
    if not remaining_blocks:
        return {"pipeline": [], "is_fallback": False}

    target_blocks = remaining_blocks & pending
    is_fallback = False
    
    if not target_blocks:
        target_blocks = remaining_blocks
        is_fallback = True

    if not target_blocks:
        return {"pipeline": [], "is_fallback": False}

    rx0 = min(x for x, _ in target_blocks)
    rx1 = max(x for x, _ in target_blocks)
    ry0 = min(y for _, y in target_blocks)
    ry1 = max(y for _, y in target_blocks)
    
    total_pipeline = []
    placed_so_far = set()

    rows_with_blocks = {}
    for (x, y) in target_blocks:
        rows_with_blocks.setdefault(y, []).append(x)
        
    for y in sorted(rows_with_blocks.keys(), reverse=True):
        rows_with_blocks[y].sort()

    sorted_y = sorted(rows_with_blocks.keys(), reverse=True)
    if not sorted_y:
        return {"pipeline": [], "is_fallback": is_fallback, "skipped_blocks": []}

    for step_idx, step_y in enumerate(sorted_y):
        xs = rows_with_blocks[step_y]
        left_to_right = (step_idx % 2 == 0)
        
        row_min_x = xs[0]
        row_max_x = xs[-1]
        x_range = range(row_min_x, row_max_x + 1) if left_to_right else range(row_max_x, row_min_x - 1, -1)

        last_useful_col = len(x_range) - 1
        for col_idx, x in enumerate(x_range):
            y = step_y
            if (x, y) in target_blocks:
                placed_so_far.add((x, y))
                total_pipeline.append({
                    "type": "place_and_dye",
                    "x": x,
                    "y": y,
                    "color": blocks_by_coord[(x, y)]
                })

            is_last_in_row = (col_idx == last_useful_col)
            if not is_last_in_row:
                direction = "d" if left_to_right else "a"
                total_pipeline.append({
                    "type": "move",
                    "direction": direction,
                    "desc": f"Move to next cell ({direction})"
                })

        # Move up to next populated row
        if step_idx < len(sorted_y) - 1:
            next_y = sorted_y[step_idx + 1]
            for _ in range(step_y - next_y):
                total_pipeline.append({
                    "type": "move",
                    "direction": "space",
                    "desc": "Move up to next row (space)"
                })
            
            # Since we could be at row_max_x (if left_to_right) or row_min_x (if right_to_left),
            # we may need to align with the start of the next row.
            # But the next row's path generation will just start from row_max_x / row_min_x?
            # Wait, no. The character's physical X coordinate is currently at `x_range[-1]`.
            # The next row's `x_range[0]` might be different. Let's add horizontal moves to reach it.
            current_x = x_range[-1]
            next_xs = rows_with_blocks[next_y]
            next_left_to_right = ((step_idx + 1) % 2 == 0)
            next_start_x = next_xs[0] if next_left_to_right else next_xs[-1]
            
            while current_x < next_start_x:
                total_pipeline.append({"type": "move", "direction": "d", "desc": "Align X (d)"})
                current_x += 1
            while current_x > next_start_x:
                total_pipeline.append({"type": "move", "direction": "a", "desc": "Align X (a)"})
                current_x -= 1

    skipped_blocks = []
    for yy in range(ry0, ry1 + 1):
        for xx in range(rx0, rx1 + 1):
            if (xx, yy) not in target_blocks and (xx, yy) in blocks_by_coord:
                skipped_blocks.append({"x": xx, "y": yy})

    return {
        "pipeline": total_pipeline,
        "is_fallback": is_fallback,
        "target_blocks": [{"x": x, "y": y} for x, y in sorted(target_blocks, key=lambda p: (p[1], p[0]))],
        "skipped_blocks": skipped_blocks,
    }
