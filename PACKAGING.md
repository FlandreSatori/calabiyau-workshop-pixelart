# Packaging Guide

This project is currently split into:

- a Python FastAPI backend under `backend/`
- a Tauri frontend under `frontend/`
- a launcher script `run_app.py`

The launcher now supports a release-style layout:

- it auto-elevates on Windows
- it prefers packaged binaries when present
- if no standalone backend executable exists, it can run the backend embedded in the launcher process

## Practical release layout

For a portable release folder, ship:

- `run_app.exe` built from `run_app.py`
- `frontend.exe` copied from the Tauri release output

Recommended folder shape:

```text
release/
  run_app.exe
  frontend.exe
  backend/   (optional, only if you package the backend as a separate exe)
```

## Build steps

### 1. Build the frontend

From the workspace root:

```powershell
cd frontend
npm install
npm run tauri build
```

Tauri will generate the release app under `frontend/src-tauri/target/release/` and installer/bundle outputs under `frontend/src-tauri/target/release/bundle/`.

### 2. Build the launcher

Package `run_app.py` with PyInstaller:

```powershell
pyinstaller --onefile --name run_app run_app.py
```

If your environment does not already include the backend dependencies, install them before packaging.

### 3. Publish

Copy the packaged launcher together with the Tauri release executable into the same release directory.

If you want the launcher to start the Tauri app directly, make sure the Tauri executable is named `frontend.exe` or update the path logic in `run_app.py`.

## Notes

- The launcher should be the entry point users double-click.
- The launcher requests administrator privileges on Windows.
- Do not ship development-only folders such as `frontend/node_modules`, `frontend/dist`, or `frontend/src-tauri/target/debug`.
