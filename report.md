# 🌸 屎山代码分析报告 🌸

## 📑 目录

- [糟糕指数](#overall-score)
- [评分指标详情](#metrics-details)
- [最屎代码排行榜](#problem-files)
- [诊断结论](#conclusion)

![Score](https://img.shields.io/badge/Score-88%25-brightgreen)

## 糟糕指数 {#overall-score}

| 指标摘要 | 评分 |
|------|-------|
| **糟糕指数** | **88.31/100** |
| 屎山等级 | 🌸 偶有异味 |

> 清新宜人，初闻像早晨的露珠

### 📊 统计信息

| 指标 | 数值 |
|--------|-------|
| 总文件数 | 33 |
| 已跳过 | 22531 |
| 耗时 | 3148ms |

## 评分指标详情 {#metrics-details}

| 指标摘要 | 评分 | 状态 |
|:-----|------:|:------:|
| 循环复杂度 | 6.78% | ✓✓ |
| 认知复杂度 | 9.43% | ✓✓ |
| 嵌套深度 | 1.82% | ✓✓ |
| 函数长度 | 6.71% | ✓✓ |
| 文件长度 | 0.82% | ✓✓ |
| 参数数量 | 4.90% | ✓✓ |
| 代码重复 | 0.40% | ✓✓ |
| 结构分析 | 2.24% | ✓✓ |
| 错误处理 | 24.49% | ✓ |
| 注释比例 | 44.85% | ○ |
| 命名规范 | 11.33% | ✓✓ |

## 最屎代码排行榜 {#problem-files}

### 1. backend\routers\blueprint.py

**糟糕指数: 32.61**

**问题**: 🔄 复杂度问题: 2, ⚠️ 其他问题: 1, 🏗️ 结构问题: 1, ❌ 错误处理问题: 8, 📝 注释问题: 1

- 🔄 `plan_pipeline()` L62: 复杂度: 27
- 🔄 `plan_pipeline()` L62: 认知复杂度: 33
- 📏 `plan_pipeline()` L62: 124 代码量
- 🏗️ `plan_pipeline()` L62: 中等嵌套: 3
- ❌ L10: 未处理的易出错调用
- 🔍 ...还有 7 个问题实在太屎，列不完了

### 2. backend\movement_controller.py

**糟糕指数: 30.52**

**问题**: 🔄 复杂度问题: 7, ⚠️ 其他问题: 3, 🏗️ 结构问题: 2, 📝 注释问题: 1, 🏷️ 命名问题: 7

- 🔄 `_evaluate_move_jump()` L46: 复杂度: 12
- 🔄 `move_to_next_block()` L105: 复杂度: 20
- 🔄 `_evaluate_move_jump()` L46: 认知复杂度: 14
- 🔄 `move_to_next_block()` L105: 认知复杂度: 30
- 🔄 `move_keep()` L205: 认知复杂度: 20
- 🔍 ...还有 14 个问题实在太屎，列不完了

### 3. run_app.py

**糟糕指数: 14.98**

**问题**: 🔄 复杂度问题: 7, ⚠️ 其他问题: 2, 🏗️ 结构问题: 4, ❌ 错误处理问题: 1, 📝 注释问题: 1

- 🔄 `get_listening_pid_windows()` L150: 复杂度: 11
- 🔄 `get_process_image_name_windows()` L182: 复杂度: 11
- 🔄 `main()` L396: 复杂度: 14
- 🔄 `get_listening_pid_windows()` L150: 认知复杂度: 19
- 🔄 `get_process_image_name_windows()` L182: 认知复杂度: 17
- 🔍 ...还有 8 个问题实在太屎，列不完了

### 4. pydd.py

**糟糕指数: 12.96**

**问题**: 🔄 复杂度问题: 2, ⚠️ 其他问题: 3, 🏗️ 结构问题: 1, 🏷️ 命名问题: 4

- 🔄 `_type_text_by_key()` L468: 认知复杂度: 17
- 🔄 `_type_text_by_key()` L468: 嵌套深度: 4
- 📏 `_get_key_code()` L500: 125 代码量
- 🏗️ `_type_text_by_key()` L468: 中等嵌套: 4
- 🏷️ `__init__()` L203: "__init__" - snake_case
- 🔍 ...还有 3 个问题实在太屎，列不完了

### 5. disabled\test_screenshot_tool.py

**糟糕指数: 12.18**

**问题**: 🔄 复杂度问题: 2, ⚠️ 其他问题: 2, 🏗️ 结构问题: 2, ❌ 错误处理问题: 2, 📝 注释问题: 1, 🏷️ 命名问题: 2

- 🔄 `_show_with_marker()` L52: 认知复杂度: 14
- 🔄 `_show_with_marker()` L52: 嵌套深度: 4
- 📏 `_show_with_marker()` L52: 64 代码量
- 🏗️ `_show_with_marker()` L52: 中等嵌套: 4
- 🏗️ `on_mouse()` L58: 中等嵌套: 3
- 🔍 ...还有 4 个问题实在太屎，列不完了

### 6. backend\routers\vision.py

**糟糕指数: 9.75**

**问题**: ⚠️ 其他问题: 1, 🏗️ 结构问题: 1, ❌ 错误处理问题: 6, 📝 注释问题: 1

- 📏 `calibrate_horizontal_white()` L168: 90 代码量
- 🏗️ `get_pixel_color()` L34: 中等嵌套: 3
- ❌ L33: 未处理的易出错调用
- ❌ L80: 未处理的易出错调用
- ❌ L107: 未处理的易出错调用
- 🔍 ...还有 3 个问题实在太屎，列不完了

### 7. backend\routers\system.py

**糟糕指数: 9.56**

**问题**: 🔄 复杂度问题: 2, 🏗️ 结构问题: 1, ❌ 错误处理问题: 10, 📝 注释问题: 1

- 🔄 `get_app_base_dirs()` L30: 认知复杂度: 13
- 🔄 `get_local_file()` L197: 认知复杂度: 13
- 🏗️ `get_local_file()` L197: 中等嵌套: 3
- ❌ L91: 未处理的易出错调用
- ❌ L96: 未处理的易出错调用
- 🔍 ...还有 8 个问题实在太屎，列不完了

### 8. backend\routers\macro.py

**糟糕指数: 9.47**

**问题**: 🔄 复杂度问题: 1, ⚠️ 其他问题: 1, 🏗️ 结构问题: 1, ❌ 错误处理问题: 5, 📝 注释问题: 1

- 🔄 `ensure_game_active()` L60: 认知复杂度: 13
- 📏 `dye_block()` L81: 55 代码量
- 🏗️ `ensure_game_active()` L60: 中等嵌套: 3
- ❌ L80: 未处理的易出错调用
- ❌ L137: 未处理的易出错调用
- 🔍 ...还有 3 个问题实在太屎，列不完了

### 9. backend\vision_core.py

**糟糕指数: 9.30**

**问题**: 🔄 复杂度问题: 4, ⚠️ 其他问题: 3, 🏗️ 结构问题: 3, 🏷️ 命名问题: 10

- 🔄 `_fit_marker_from_contour()` L200: 复杂度: 12
- 🔄 `_estimate_square_horizontal_error()` L141: 认知复杂度: 13
- 🔄 `_fit_marker_from_contour()` L200: 认知复杂度: 14
- 🔄 `_extract_four_markers()` L357: 认知复杂度: 16
- 📏 `_fit_marker_from_contour()` L200: 53 代码量
- 🔍 ...还有 13 个问题实在太屎，列不完了

### 10. backend\ui_interaction.py

**糟糕指数: 8.97**

**问题**: 🔄 复杂度问题: 1, ⚠️ 其他问题: 2, 🏷️ 命名问题: 5

- 🔄 `_move_cursor_absolute()` L48: 认知复杂度: 14
- 📏 `_move_cursor_absolute()` L48: 57 代码量
- 📏 `paste_hex_color()` L109: 6 参数数量
- 🏷️ `__init__()` L19: "__init__" - snake_case
- 🏷️ `_get_absolute_coords()` L24: "_get_absolute_coords" - snake_case
- 🔍 ...还有 3 个问题实在太屎，列不完了

## 诊断结论 {#conclusion}

🌸 **偶有异味** - 基本没事，但是有伤风化

👍 继续保持，你是编码界的一股清流，代码洁癖者的骄傲

---

*由 [fuck-u-code](https://github.com/Done-0/fuck-u-code) 生成*