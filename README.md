# 卡丘工坊自动像素画工具/猫画画

#### 直接启动

前往release下载打包好的软件

#### 从源码构建

打开终端（CMD/PowerShell/ 终端），进入项目文件夹calabiyau-workshop-pixelart

**Windows**
创建.venv 虚拟环境：

```bash
python -m venv .venv
```

接着激活虚拟环境：

```bash
# CMD
.venv\Scripts\activate.bat
```

```bash
# PowerShell
.venv\Scripts\Activate.ps1
```

**Mac / Linux**
```
只有Windows有卡丘喵，散了喵
```

若激活成功，终端前面会出现 `(.venv)` 标识。

示例：

```bash
PS D:\develop\calabiyau-workshop-pixelart> python -m venv .venv
PS D:\develop\calabiyau-workshop-pixelart> .venv\Scripts\Activate.ps1
(.venv) PS D:\develop\calabiyau-workshop-pixelart>
```

安装依赖

```bash
# 使用国内源加速
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

**前端准备**

安装前端本地依赖，在 `frontend` 目录下运行：

```bash
npm install
```

这会安装 `package.json` 中定义的所有依赖（包括 `vue-tsc`、`vite` 等）。

```bash
npm run tauri build
```

| 文件          | 路径                                                                          |
| ----------- | --------------------------------------------------------------------------- |
| **MSI 安装包** | `frontend\src-tauri\target\release\bundle\msi\frontend_0.1.0_x64_en-US.msi` |
| **前端可执行文件** | `frontend\src-tauri\target\release\frontend.exe`                            |

**后端（开发模式）**

```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

**后端（发布模式，打包后端为 exe）**

```bash
pyinstaller --onefile backend/main.py -n backend
copy "dist\backend.exe" "backend.exe"
```

**启动程序**

检查根目录下是否已经放置frontend.exe和backend.exe，如果有则启动：

```bash
python .\run_app.py
```

运行示例：

```bash
PS D:\develop\calabiyau-workshop-pixelart> python run_app.py
Starting packaged backend: D:\develop\calabiyau-workshop-pixelart\backend.exe
⏳ 后端仍在启动中，正在等待端口 8000...
🎉 检测到端口 8000 已成功开放！
Starting packaged frontend: D:\develop\calabiyau-workshop-pixelart\frontend.exe
```

至此，软件已经开始运行！

---

#### 文档说明

文档参见`calabiyau-workshop-pixelart\docs`

你可以在`calabiyau-workshop-pixelart\docs\guide.md`找到使用说明

---

#### 开发日志与路线计划

参见`calabiyau-workshop-pixelart\devlog`
