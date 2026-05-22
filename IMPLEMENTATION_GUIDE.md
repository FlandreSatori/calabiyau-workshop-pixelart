# 🎮 像素画自动搭建系统 - 实现指南

## 第一阶段：数据采集和准备 ✅

### 1️⃣ 安装依赖

```powershell
# 在项目根目录运行
pip install -r requirements_vision.txt
```

### 2️⃣ 运行截图采集工具

```powershell
python screenshot_tool.py
```

**工具会引导你按顺序采集以下数据：**

| 序号 | 采集内容 | 用途 | 采集方法 |
|-----|--------|------|--------|
| 1 | 完整游戏窗口 | 获取屏幕分辨率、确定ROI | 全屏截图，标记准心位置 |
| 2 | 准心对准方块特写 | 校准视觉识别算法 | ROI截图（200x200） |
| 3 | E面板UI | 定位色彩输入框、确认按钮 | **需要标记3个关键坐标** |
| 4 | 已放置的方块 | 验证方块颜色、检测已放置状态 | 单个方块特写 |

### 3️⃣ 采集 E 面板 UI 坐标

打开 E 面板时，**必须标记以下3个坐标点**（左键点击）：

```
Point 1: HEX 颜色输入框的左上角
Point 2: 输入框中心（鼠标点击激活位置）
Point 3: 确认/应用按钮的中心
```

**示例坐标（1920x1080分辨率，仅供参考）：**
- HEX输入框: (1210, 520)
- 确认按钮: (1320, 580)

### 4️⃣ 检查采集结果

采集完成后，检查 `screenshots/` 目录：

```
screenshots/
├── game_window_20240513_120000.png
├── game_window_coords_20240513_120000.json
├── e_panel_ui_20240513_120000.png
├── e_panel_ui_coords_20240513_120000.json
└── coordinate_map.json
```

**打开 `coordinate_map.json`，确认所有坐标已正确采集。**

---

## 第二阶段：核心模块实现 🔧

### Module 1: 视觉识别模块 (vision_core.py)

**功能：**
- 使用 OpenCV 检测四角绿色圆形角标与白色待放置虚影
- 先判断视角是否水平，再进行横向/纵向闭环移动
- 支持本地 ROI 捕捉

**实现要点：**
1. HSV 颜色空间滤波（绿色角标与白色虚影分别设阈值）
2. 形态学处理（erode + dilate）
3. 提取四个角标的圆心或白框上下边缘
4. 计算水平误差：角标中点连线斜率、白框边缘斜率或偏差
5. 输出水平误差与横向偏差，作为状态机输入

### Module 2: 鼠标精密微调模块 (pid_controller.py)

**功能：**
- 基于误差向量的 PID 控制
- 非线性衰减步进
- 死区判定

**参数设置：**
```python
Kp = 0.4  # 比例系数（控制步进大小）
Ki = 0.0  # 积分系数（设为0，避免积分累积误差）
Kd = 0.0  # 微分系数（高频抖动，暂不需要）
deadzone = 2  # 像素死区（±2px 视为精确对准）
```

### Module 3: 闭环移动模块 (movement_controller.py)

**功能：**
- WASD 闭环移动（监测绿框状态）
- Space/Alt 纵向移动
- 移动完成判定

**状态转换：**
```
按下WASD → 循环检测绿框位置
当绿框离开屏幕 → block_passed = True
当新绿框出现在屏幕中央附近 → 释放WASD
进入视觉微调 → 精确对准
```

### Module 4: E面板交互模块 (ui_interaction.py)

**功能：**
- 自动打开 E 面板
- 输入 HEX 颜色代码
- 等待面板关闭

**流程：**
```
按下 E → 等待 300ms（UI动画）
鼠标移动到输入框坐标
左键点击激活输入框
清空输入框（Ctrl+A）
剪贴板写入 HEX 颜色（#RRGGBB）
Ctrl+V 粘贴 → Enter 确认
等待 E 面板消失
```

### Module 5: 状态机核心引擎 (fsm_engine.py)

**主要状态：**
```
State_INIT         → 初始化、校准
  ↓
State_PLACE        → 放置方块
  ↓
State_CALIBRATE    → 精确对准
  ↓
State_DYE          → 执行染色
  ↓
State_NEXT_BLOCK   → 移动到下一列 (或 State_NEXT_ROW)
  ↓
State_NEXT_ROW     → 爬升/下降一行
  ↓
State_PLACE        (循环...)
```

---

## 第三阶段：像素图转换工具

### 实现功能：
1. 读取 PNG/JPG 图片
2. 缩放到目标分辨率（例如 32x32）
3. 提取每个像素的颜色
4. 生成 JSON 蓝图文件

**输出 JSON 格式：**
```json
{
  "version": 1,
  "resolution": [32, 32],
  "start_pos": {"x": 1, "y": 1},
  "blocks": [
    {"x": 0, "y": 0, "color": "#FF5733"},
    {"x": 1, "y": 0, "color": "#33FF57"},
    ...
  ]
}
```

---

## 第四阶段：集成和测试

### 集成流程：
1. ✅ 加载 JSON 蓝图
2. ✅ 初始化 DD 驱动和视觉模块
3. ✅ 执行状态机主循环
4. ✅ 异常捕获和恢复

### 测试清单：
- [ ] 视觉识别能否稳定检测绿框
- [ ] 鼠标微调能否在 2px 内精确对准
- [ ] WASD 闭环能否正确移动到下一个方块
- [ ] E 面板能否正确输入和确认颜色
- [ ] 完整的小型蓝图（3x3）能否正确构建

---

## 🚀 快速开始命令

```powershell
# 1. 安装依赖
pip install -r requirements_vision.txt

# 2. 采集数据（需要游戏打开）
python screenshot_tool.py

# 3. 查看采集结果（可选：手动验证坐标）
# 打开 screenshots/coordinate_map.json

# 4. 创建像素图蓝图（后续实现）
python image_to_blueprint.py --input my_pixel_art.png --output blueprint.json

# 5. 执行自动搭建（后续实现）
python auto_build.py --blueprint blueprint.json
```

---

## ⚠️ 重要提示

1. **游戏配置**
   - 确保游戏在 1920x1080 分辨率下运行
   - 将视角垂直对准建造墙面
   - 玩家位置在墙面左下角 (1, 1)

2. **安全考虑**
   - 系统获得键鼠控制权，运行中不要移动鼠标！
   - 按 F10（待实现）可中断执行，恢复用户控制

3. **调试建议**
   - 首次运行使用最小蓝图（3x3）测试
   - 在 `vision_core.py` 中启用 `DEBUG=True` 查看识别效果
   - 如识别效果不理想，重新采集截图并调整 HSV 阈值

