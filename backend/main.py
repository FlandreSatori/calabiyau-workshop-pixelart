import asyncio
import argparse
import sys
import ctypes
import os

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.log_manager import manager, install_stdout_bridge, set_broadcast_loop

install_stdout_bridge()

from backend.routers import control, vision, macro, system, blueprint

if sys.platform == "win32":
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass
		
app = FastAPI(title="PYDD Auto Builder API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 业务接口托管
app.include_router(control.router, prefix="/api/control", tags=["Control"])
app.include_router(vision.router, prefix="/api/vision", tags=["Vision"])
app.include_router(macro.router, prefix="/api/macro", tags=["Macro Tools"])
app.include_router(system.router, prefix="/api/system", tags=["System"])
app.include_router(blueprint.router, prefix="/api/blueprint", tags=["Blueprint"])


# # ===============前端静态文件托管================
# # 自动兼容本地开发环境和 PyInstaller 打包环境
# if getattr(sys, "frozen", False):
#     # 打包后环境：期望 dist 文件夹存放在 backend.exe 的同级目录下
#     dist_dir = os.path.join(os.path.dirname(sys.executable), "dist")
# else:
#     # 源码开发环境：寻找项目根目录下的 dist 文件夹
#     current_dir = os.path.dirname(os.path.abspath(__file__))
#     dist_dir = os.path.abspath(os.path.join(current_dir, "..", "dist"))

# if os.path.exists(dist_dir):
#     # html=True 会让访问根目录时自动寻找 index.html
#     app.mount("/", StaticFiles(directory=dist_dir, html=True), name="static")
#     print(f"成功挂载前端静态资源: {dist_dir}")
# else:
#     print(f"⚠️未找到前端静态目录 {dist_dir}")
# # ============================================


@app.on_event("startup")
async def init_log_broadcast_loop():
    set_broadcast_loop(asyncio.get_running_loop())

@app.get("/api/status")
def read_root():
    return {"status": "ok", "message": "Backend is running."}

@app.websocket("/api/ws/logs")
async def websocket_logs(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backend Server")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host")
    parser.add_argument("--port", type=int, default=8000, help="Bind port")
    parser.add_argument("--reload", action="store_true", help="Enable auto reload in development")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    import uvicorn

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=args.reload,
        use_colors=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
