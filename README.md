# 卡皮喵 --- 卡丘工坊自动像素画工具

*[ 译者注：Pixel = 皮 ]*

---

项目代码会尽力兼容不同版本的Python解释器

---

#### 从源码构建

打开终端（CMD/PowerShell/ 终端），进入项目文件夹calabiyau-workshop-pixelart。

创建.venv 虚拟环境：

```bash
# Windows用python，mac/linux用python3
python -m venv .venv
```

接着激活虚拟环境：

**Windows**

```bash
# CMD
.venv\Scripts\activate.bat
```

```bash
# PowerShell
.venv\Scripts\Activate.ps1
```

**Mac / Linux**

```bash
# Bash
source .venv/bin/activate
```

若激活成功，终端前面会出现 `(.venv)` 标识。

示例：

```bash
PS D:\develop\calabiyau-workshop-pixelart> python -m venv .venv
PS D:\develop\calabiyau-workshop-pixelart> .venv\Scripts\Activate.ps1
(.venv) PS D:\develop\calabiyau-workshop-pixelart>
```

安装依赖 & 启动程序

```bash
# 安装依赖，使用国内源加速
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
# 启动程序
python .\run_app.py
```

安装前端本地依赖：

在 `frontend` 目录下运行：

```bash
npm install
```

这会安装 `package.json` 中定义的所有依赖（包括 `vue-tsc`、`vite` 等）。

```bash
npm run tauri build
```

---

#### 文档说明

文档参见`calabiyau-workshop-pixelart\docs`

你可以在`calabiyau-workshop-pixelart\docs\guide.md`找到使用说明

---

#### 开发日志与路线计划

参见`calabiyau-workshop-pixelart\devlog`
