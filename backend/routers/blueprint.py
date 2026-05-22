import tempfile
import os
import asyncio
from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from image_to_blueprint import image_to_blueprint
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

from pydantic import BaseModel
from typing import List, Dict, Any

class PlanRequest(BaseModel):
    blueprint: Dict[str, Any]

@router.post("/plan")
def plan_pipeline(req: PlanRequest):
    blocks = req.blueprint.get("blocks", [])
    if not blocks:
        return {"pipeline": []}
    # Build a lookup for quick presence checks and colors
    blocks_by_coord = {(int(b["x"]), int(b["y"])): b.get("color", "#FFFFFF") for b in blocks}
    res = req.blueprint.get("resolution", [0, 0])
    width = int(res[0])
    height = int(res[1])

    pipeline: list[dict] = []

    # Traverse from bottom (y=height-1) up to top (y=0)
    # y=height-1 is the 'bottom' row in the image grid
    for step_y in range(height - 1, -1, -1):
        # Determine traversal direction for this row:
        # If we just started at bottom (height-1) or moved up an even number of times
        # Let's use (height - 1 - step_y) to count how many rows we've climbed
        rows_climbed = (height - 1) - step_y
        left_to_right = (rows_climbed % 2 == 0)
        
        x_range = range(0, width) if left_to_right else range(width - 1, -1, -1)

        for col_idx, x in enumerate(x_range):
            y = step_y
            # If there's a colored block here, place and dye, otherwise skip to movement
            if (x, y) in blocks_by_coord:
                pipeline.append({
                    "type": "place_and_dye",
                    "x": x,
                    "y": y,
                    "color": blocks_by_coord[(x, y)]
                })

            # Decide if we should move to next cell in row
            is_last_in_row = (col_idx == (width - 1))
            if not is_last_in_row:
                direction = "d" if left_to_right else "a"
                pipeline.append({
                    "type": "move",
                    "direction": direction,
                    "desc": f"Move to next cell ({direction})"
                })

        # After finishing a row, if not the topmost row (y=0), move up and stay there
        if step_y > 0:
            pipeline.append({
                "type": "move",
                "direction": "space",
                "desc": "Move up to next row (space)"
            })

    return {"pipeline": pipeline}
