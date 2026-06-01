<template>
  <el-container class="app-layout">
    <!-- 左侧导航栏 -->
    <el-aside :width="isCollapse ? '64px' : '200px'" class="nav-aside" style="transition: width 0.3s">
      <div class="logo-box" style="display: flex; align-items: center; justify-content: space-between;">
        <h2 class="logo-text" v-show="!isCollapse">卡丘工坊像素画</h2>
        <span style="cursor: pointer; padding: 4px;" @click="isCollapse = !isCollapse">☰</span>
      </div>
      <el-menu
        :default-active="activeTab"
        class="nav-menu"
        @select="handleSelect"
        :collapse="isCollapse"
        :collapse-transition="false"
      >
        <el-menu-item index="image">
          <el-icon><span style="font-size: 16px;">🖼️</span></el-icon>
          <template #title>蓝图</template>
        </el-menu-item>
        <el-menu-item index="task">
          <el-icon><span style="font-size: 16px;">🚀</span></el-icon>
          <template #title>任务</template>
        </el-menu-item>
        <el-menu-item index="debug">
          <el-icon><span style="font-size: 16px;">🔧</span></el-icon>
          <template #title>调试</template>
        </el-menu-item>
        <el-menu-item index="about">
          <el-icon><span style="font-size: 16px;">ℹ️</span></el-icon>
          <template #title>关于</template>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- 右侧主体内容 -->
    <el-container class="main-container">
      <el-header class="system-monitor" height="40px">
        <div class="monitor-item">
          <span class="monitor-label">前台窗口: </span>
          <el-tag size="small" :type="foregroundWindow?.is_foreground ? 'success' : 'info'">
            {{ foregroundWindow?.title || '未获取' }}
          </el-tag>
        </div>
      </el-header>

      <el-main class="content-main">
        <!-- 图像处理面板（蓝图管理） -->
        <div v-show="activeTab === 'image'" class="panel-content image-panel">
          <el-row :gutter="20">
            <el-col :span="8">
              <el-card shadow="never" class="settings-card">
                <template #header>蓝图设置</template>
                <div class="setting-item compact">
                   <div class="label">尺寸(W×H)</div>
                   <el-input-number v-model="bpWidth" :min="1" :max="512" @change="handleWidthChange" size="small" style="width: 80px" :controls="false" />
                   <span class="mx-2">×</span>
                   <el-input-number v-model="bpHeight" :min="1" :max="512" @change="handleHeightChange" size="small" style="width: 80px" :controls="false" />
                </div>
                <div class="setting-item compact">
                   <el-checkbox v-model="keepRatio" size="small">保持宽高比</el-checkbox>
                </div>
                
                <div class="setting-item compact mt-3" style="display: flex; gap: 10px;">
                  <el-upload
                    action="#"
                    :auto-upload="false"
                    :on-change="handleImageChange"
                    :show-file-list="false"
                    accept=".png,.jpg,.jpeg"
                  >
                    <el-button type="primary" plain size="small">选择图片</el-button>
                  </el-upload>
                  
                  <el-button type="success" size="small" style="flex: 1;" :disabled="!uploadedFile || isGenerating" @click="generateBlueprint" :loading="isGenerating">
                    🚀 生成预览
                  </el-button>
                </div>
                
                <div class="setting-item compact mt-3" style="display: flex; gap: 10px;">
                  <el-button type="warning" plain size="small" style="flex: 1;" :disabled="!currentBlueprint" @click="exportTask">💾 保存任务进度</el-button>
                  <el-upload
                    action="#"
                    :auto-upload="false"
                    :on-change="importTask"
                    :show-file-list="false"
                    accept=".json"
                    style="flex: 1;"
                  >
                    <el-button type="info" plain size="small" style="width: 100%;">📂 导入任务进度</el-button>
                  </el-upload>
                </div>
              </el-card>
            </el-col>
            <el-col :span="16">
              <el-card shadow="never" class="settings-card preview-card simple-preview">
                <template #header>预览</template>
                <div class="canvas-container">
                  <canvas ref="previewCanvasStatic" class="pixel-canvas static-canvas"></canvas>
                </div>
                <div v-if="!currentBlueprint" class="empty-state">待生成</div>
              </el-card>
            </el-col>
          </el-row>
        </div>

        <!-- 任务与执行面板（核心监控） -->
        <div v-show="activeTab === 'task'" class="panel-content task-workflow">
          <div class="workflow-header">
            <div class="status-info">
              <span v-if="currentBlueprint">进度: {{ pipelineProgress }} / {{ pipelineTotal }}</span>
              <el-progress 
                v-if="currentBlueprint"
                type="line" 
                :percentage="pipelinePercentage" 
                style="width: 150px; margin-left: 15px;" 
                :show-text="false"
                :stroke-width="10"
              />
              <el-tag size="small" v-if="busy" type="warning" class="ml-2">执行中</el-tag>
            </div>
            <div class="action-group">
              <el-button-group class="mr-2">
                <el-button size="small" @click="zoomOut">🔍 -</el-button>
                <el-button size="small" @click="zoomIn">🔍 +</el-button>
                <el-button size="small" @click="calculateInitialZoom">适应</el-button>
              </el-button-group>
              <el-button type="primary" :disabled="!currentBlueprint || selectionRects.length === 0" @click="markSelectionStatus('pending')">标记待建造</el-button>
              <el-button type="success" :disabled="!currentBlueprint || selectionRects.length === 0" @click="markSelectionStatus('completed')">标记已完成</el-button>
              <el-button type="warning" plain :disabled="!currentBlueprint || selectionRects.length === 0" @click="markSelectionStatus('ignored')">清除（不建造）</el-button>
              <el-button type="info" :disabled="!currentBlueprint" @click="planCurrentBlueprint">规划</el-button>
              <el-button type="success" :disabled="busy || !currentBlueprint" @click="startAutoBuild">开始搭建</el-button>
              <el-button type="danger" :disabled="!busy" @click="stopAutoBuild">停止</el-button>
              <el-button size="small" type="primary" link @click="resetProgress">重置</el-button>
            </div>
            <div class="action-group" style="margin-top: 10px; gap: 8px; flex-wrap: wrap;">
              <el-tag size="small" type="info">当前选区: {{ selectionRects.length }} 段</el-tag>
              <el-tag size="small" type="success">待建造: {{ pendingRegionCount }}</el-tag>
              <el-tag size="small" type="warning">已完成: {{ completedRegionCount }}</el-tag>
              <el-tag size="small" type="danger">规划状态: {{ planDirty ? '已失效' : '已规划' }}</el-tag>
            </div>
          </div>

          <div class="workspace-area scrollable-workspace" ref="workspaceContainer">
            <div class="main-canvas-wrapper">
              <canvas 
                ref="previewCanvas" 
                class="pixel-canvas interactive task-canvas" 
                :style="getTaskCanvasStyle"
                @wheel.ctrl.prevent="handleZoom"
                @mousedown="handleCanvasMouseDown"
                @mousemove="handleCanvasMouseMove"
                @mouseup="handleCanvasMouseUp"
                @mouseleave="handleCanvasMouseUp"
                @contextmenu.prevent
              ></canvas>
              <div v-if="!currentBlueprint" class="empty-state">先前往“蓝图”页面生成数据</div>
            </div>
          </div>

          <!-- 任务页底部日志 -->
          <div class="log-footer-mini">
            <div class="log-header-mini">
              <span>系统日志</span>
              <el-button size="small" text @click="logs = []">清空</el-button>
            </div>
            <div class="log-content-mini" ref="logContainer">
              <p v-for="(log, i) in reversedLogs" :key="i" class="log-line">{{ log }}</p>
            </div>
          </div>
        </div>
        <!-- 调试面板（包含环境设定） -->
        <div v-show="activeTab === 'debug'" class="panel-content">
          <el-row :gutter="20">
            <!-- 左侧一列：环境设定与调试操作 -->
            <el-col :span="12">
              <el-card shadow="never" class="settings-card mb-3">
                <template #header>环境设定</template>
                <div class="window-panel">
                  <div style="display: flex; gap: 8px; align-items: center;">
                    <el-select v-model="selectedWindowHwnd" placeholder="选择游戏窗口" filterable style="flex: 1">
                      <el-option
                        v-for="window in windowOptions"
                        :key="window.hwnd"
                        :label="formatWindowLabel(window)"
                        :value="window.hwnd"
                      />
                    </el-select>
                    <el-button size="small" @click="refreshWindows" title="刷新窗口列表">🔄</el-button>
                  </div>
                  
                  <div class="mt-4">
                    <el-button class="full-width-btn" type="primary" plain @click="selectCalabiyau">一键选中卡丘</el-button>
                  </div>
                </div>
              </el-card>

              <el-card shadow="never" class="settings-card">
                <template #header>调试操作</template>
                <div class="debug-actions">
                  <el-button :disabled="busy" type="primary" @click="testClick">测试-鼠标左击</el-button>
                  <el-button :disabled="busy" type="success" @click="testMove">测试-角色移动</el-button>
                  <el-button :disabled="busy" type="warning" @click="testVision">测试-方块中心</el-button>
                  <el-button :disabled="busy" type="danger" @click="testGetColor">测试-取色</el-button>
                </div>
                <div class="debug-info mt-4" v-if="foregroundWindow">
                  <div>标题: {{ foregroundWindow.title }}</div>
                  <div>进程: {{ foregroundWindow.exe_name || '未知' }}</div>
                  <div>句柄: {{ foregroundWindow.hwnd }}</div>
                  <div>PID: {{ foregroundWindow.pid }}</div>
                </div>
              </el-card>
            </el-col>

            <!-- 右侧：校准配置 & 等待时间 -->
            <el-col :span="12">
              <el-card shadow="never" class="settings-card">
                <template #header>校准配置 & 时间配置</template>
                <div class="setting-item">
                  <div class="label">调色板 X/Y</div>
                  <el-input-number size="small" v-model="configPaletteX" :min="0" />
                  <el-input-number size="small" v-model="configPaletteY" :min="0" class="ml-2" />
                </div>
                <div class="setting-item mt-2">
                  <div class="label">校验点 X/Y</div>
                  <el-input-number size="small" v-model="configVerifyX" :min="0" />
                  <el-input-number size="small" v-model="configVerifyY" :min="0" class="ml-2" />
                </div>
                <div class="setting-item mt-2">
                  <div class="label">确定按钮 X/Y</div>
                  <el-input-number size="small" v-model="configConfirmX" :min="0" />
                  <el-input-number size="small" v-model="configConfirmY" :min="0" class="ml-2" />
                </div>
                <div class="setting-item mt-2">
                  <div class="label">移动采样率(Hz)</div>
                  <el-input-number size="small" v-model="moveSampleRate" :min="30" :max="100" />
                </div>
                <div class="setting-item mt-2">
                  <div class="label">拟人化等级 (0-3)</div>
                  <el-input-number size="small" v-model="humanizeLevel" :min="0" :max="3" />
                </div>
                <div class="setting-item mt-2">
                  <div class="label">视角阈值 (%)</div>
                  <el-input-number size="small" v-model="viewAdjustThresholdPercent" :min="5" :max="50" />
                </div>
                <div class="setting-item mt-2">
                  <div class="label">染色失败重试次数</div>
                  <el-input-number size="small" v-model="dyeRetryCount" :min="0" :max="10" />
                </div>
                <div class="setting-item mt-2">
                  <el-checkbox v-model="debugMode">DEBUG模式</el-checkbox>
                </div>
                <el-button size="small" type="primary" class="mt-2" plain>保存坐标校准记录 (TODO)</el-button>
                <div class="setting-item mt-2">
                  <div class="label">开始建造快捷键</div>
                  <el-input v-model="startBuildHotkey" size="small" placeholder="例如 F6 / Ctrl+Enter" style="width: 180px" />
                </div>

                <div class="timing-panel mt-4">
                  <div class="setting-item">
                    <div class="label">确定游戏仍在前台的时间</div>
                    <el-input-number size="small" v-model="focusSettleDelay" :min="0" :max="1" :step="0.05" :precision="2" />
                  </div>
                  <div class="setting-item">
                    <div class="label">放置-切换方块</div>
                    <el-input-number size="small" v-model="placeKeyDelay" :min="0" :max="1" :step="0.05" :precision="2" />
                  </div>
                  <div class="setting-item">
                    <div class="label">放置-点击</div>
                    <el-input-number size="small" v-model="placeClickDelay" :min="0" :max="1" :step="0.05" :precision="2" />
                  </div>
                  <div class="setting-item">
                    <div class="label">放置-切回铁板</div>
                    <el-input-number size="small" v-model="dyeReturnDelay" :min="0" :max="1" :step="0.05" :precision="2" />
                  </div>
                  <div class="setting-item">
                    <div class="label">染色-打开面板</div>
                    <el-input-number size="small" v-model="dyeOpenDelay" :min="0" :max="1" :step="0.05" :precision="2" />
                  </div>
                  <div class="setting-item">
                    <div class="label">染色-粘贴后</div>
                    <el-input-number size="small" v-model="dyePasteDelay" :min="0" :max="1" :step="0.05" :precision="2" />
                  </div>
                  <div class="setting-item">
                    <div class="label">染色-确认后</div>
                    <el-input-number size="small" v-model="dyeConfirmDelay" :min="0" :max="1" :step="0.05" :precision="2" />
                  </div>
                  <div class="setting-item">
                    <div class="label">UI-鼠标点击前等待</div>
                    <el-input-number size="small" v-model="uiClickDelay" :min="0" :max="1" :step="0.05" :precision="2" />
                  </div>
                  <div class="setting-item">
                    <div class="label">UI-键盘操作前等待</div>
                    <el-input-number size="small" v-model="uiClipboardDelay" :min="0" :max="1" :step="0.05" :precision="2" />
                  </div>
                  <div class="setting-item">
                    <div class="label">移动</div>
                    <el-input-number size="small" v-model="moveHoldDelay" :min="0" :max="1" :step="0.05" :precision="2" />
                  </div>
                  
                  <el-divider border-style="dashed" />
                  
                  <div class="setting-item">
                    <div class="label" style="width: 140px;">估算单次循环耗时：</div>
                    <span style="color: #666; font-size: 14px">{{ estimatedSingleBlockTime.toFixed(2) }} s</span>
                  </div>
                  <div class="setting-item mt-2">
                    <div class="label" style="width: 140px;">当前蓝图总耗时：</div>
                    <span style="color: #0080ff; font-weight: bold">{{ formatEstimatedTotalTime }}</span>
                  </div>
                </div>
              </el-card>
            </el-col>
          </el-row>
        </div>
        <!-- 关于面板 -->
        <div v-show="activeTab === 'about'" class="panel-content">
          <el-card shadow="never" class="settings-card">
            <h2>Beta <small>v0.3.0</small></h2>
            <p>个人主页：<a href="https://space.bilibili.com/2199618" target="_blank" rel="noopener">https://space.bilibili.com/2199618</a></p>
            <p>项目主页：<a href="https://github.com/FlandreSatori/calabiyau-workshop-pixelart" target="_blank" rel="noopener">https://github.com/FlandreSatori/calabiyau-workshop-pixelart</a></p>
          </el-card>
        </div>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, nextTick, watch } from 'vue';
import axios from 'axios';
import { ElMessage, UploadFile, ElMessageBox } from 'element-plus';

type WindowInfo = { hwnd: number; pid: number; exe_name: string; title: string; is_foreground: boolean; };

const API_BASE = 'http://127.0.0.1:8000/api';
const isCollapse = ref(false);
const activeTab = ref('image');
const lastDyeAction = ref<(() => Promise<boolean>) | null>(null);
const logs = ref<string[]>([]);
const windowOptions = ref<WindowInfo[]>([]);
const selectedWindowHwnd = ref<number | null>(null);
const foregroundWindow = ref<WindowInfo | null>(null);
const delaySeconds = ref<number>(3);
const autoActivateWindow = ref<boolean>(false);
const busy = ref<boolean>(false);
const shouldStop = ref<boolean>(false);
const debugMode = ref(false);

// Baseline-based view adjust
const baselineGreenDistance = ref<number | null>(null);
const viewAdjustThresholdPercent = ref<number>(15); // percent of baseline distance to trigger (默认 15%)
const viewAdjustNudgeTimeout = ref<number>(0.15); // seconds to hold move for nudge
const humanizeLevel = ref<number>(1); // default level 1

// Configuration Defaults
const configPaletteX = ref(2157);
const configPaletteY = ref(930);
const configConfirmX = ref(2222);
const configConfirmY = ref(1052);
const configVerifyX = ref(2291);
const configVerifyY = ref(933);
const moveSampleRate = ref(60);
const dyeRetryCount = ref(2);
const focusSettleDelay = ref(0.05);
const placeKeyDelay = ref(0.1);
const placeClickDelay = ref(0.1);
const moveHoldDelay = ref(0.1);
const dyeOpenDelay = ref(0.1);
const dyePasteDelay = ref(0.1);
const dyeConfirmDelay = ref(0.2);
const dyeReturnDelay = ref(0.1);
const uiClickDelay = ref(0.05);
const uiClipboardDelay = ref(0.05);

// Blueprint Gen state
const bpWidth = ref(32);
const bpHeight = ref(32);
const keepRatio = ref(true);
const originalRatio = ref(1);
const extractLineart = ref(false);
const reduceNoise = ref(false);
const uploadedFile = ref<File | null>(null);
const isGenerating = ref(false);
const currentBlueprint = ref<any>(null);
const previewCanvas = ref<HTMLCanvasElement | null>(null);
const previewCanvasStatic = ref<HTMLCanvasElement | null>(null);

// Zoom logic (Pan uses native scrollbars)
const zoom = ref(1);
const minZoom = ref(0.1);
const workspaceContainer = ref<HTMLElement | null>(null);

const getTaskCanvasStyle = computed(() => {
  if (!currentBlueprint.value) return {};
  const CELL_SIZE = 20;
  return {
    width: `${currentBlueprint.value.resolution[0] * CELL_SIZE * zoom.value}px`,
    height: `${currentBlueprint.value.resolution[1] * CELL_SIZE * zoom.value}px`,
    cursor: 'crosshair',
    imageRendering: 'pixelated' as const
  };
});

const calculateInitialZoom = () => {
  if (!currentBlueprint.value || !workspaceContainer.value) return;
  const CELL_SIZE = 20;
  const container = workspaceContainer.value;
  const bw = currentBlueprint.value.resolution[0] * CELL_SIZE;
  const bh = currentBlueprint.value.resolution[1] * CELL_SIZE;
  const scaleX = (container.clientWidth - 40) / bw;
  const scaleY = (container.clientHeight - 40) / bh;
  const fitZoom = Math.min(scaleX, scaleY);
  minZoom.value = fitZoom;
  zoom.value = fitZoom;
};

const handleZoom = (e: WheelEvent) => {
  const delta = e.deltaY > 0 ? 0.85 : 1.15;
  zoom.value = Math.max(0.05, Math.min(20, zoom.value * delta));
};

const zoomIn = () => {
  zoom.value = Math.min(20, zoom.value * 1.15);
};

const zoomOut = () => {
  zoom.value = Math.max(0.05, zoom.value * 0.85);
};
// Pipeline state
const pipelineProgress = ref(0);
const pipelineTotal = ref(0);
const pipelinePercentage = computed(() => pipelineTotal.value === 0 ? 0 : Math.round((pipelineProgress.value / pipelineTotal.value) * 100));
const completedBlocks = ref<Set<string>>(new Set());
const actionBusy = ref(false);

// Time estimation
const estimatedSingleBlockTime = computed(() => {
  return placeKeyDelay.value + placeClickDelay.value + dyeReturnDelay.value + 
         dyeOpenDelay.value + dyePasteDelay.value + dyeConfirmDelay.value + 
         (uiClickDelay.value * 6) + uiClipboardDelay.value + moveHoldDelay.value + 0.2;
});

const formatEstimatedTotalTime = computed(() => {
  if (pipelineTotal.value === 0) return '0s';
  const totalSeconds = estimatedSingleBlockTime.value * pipelineTotal.value;
  if (totalSeconds < 60) return `${Math.round(totalSeconds)} s`;
  if (totalSeconds < 3600) return `${Math.floor(totalSeconds / 60)} m ${Math.round(totalSeconds % 60)} s`;
  return `${Math.floor(totalSeconds / 3600)} h ${Math.floor((totalSeconds % 3600) / 60)} m`;
});

const handleWidthChange = (val: number | undefined) => {
  if (keepRatio.value && val && originalRatio.value) {
    bpHeight.value = Math.round(val / originalRatio.value);
  }
};

const handleHeightChange = (val: number | undefined) => {
  if (keepRatio.value && val && originalRatio.value) {
    bpWidth.value = Math.round(val * originalRatio.value);
  }
};

type Rect = { x0: number; y0: number; x1: number; y1: number };
type RegionStatus = 'pending' | 'completed' | 'ignored';

const selectionRects = ref<Rect[]>([]);
const pendingBlocks = ref<Set<string>>(new Set());
const ignoredBlocks = ref<Set<string>>(new Set());
const planDirty = ref(true);
const skippedPlannedBlocks = ref<{ x: number; y: number }[]>([]);
const startBuildHotkey = ref('F6');
const isDrawingRegion = ref(false);
const regionStartCoords = ref<{x: number, y: number} | null>(null);
const currentDrawCoords = ref<{x: number, y: number} | null>(null);
const drawMode = ref<'add'|'remove'>('add');
let clickStartPos = { x: 0, y: 0 };

const pendingRegionCount = computed(() => pendingBlocks.value.size);
const completedRegionCount = computed(() => completedBlocks.value.size);

const getBlockCoords = (event: MouseEvent): { blockX: number; blockY: number } => {
  if (!previewCanvas.value) return { blockX: 0, blockY: 0 };
  const rect = previewCanvas.value.getBoundingClientRect();
  const scaleX = previewCanvas.value.width / rect.width;
  const scaleY = previewCanvas.value.height / rect.height;
  const x = (event.clientX - rect.left) * scaleX;
  const y = (event.clientY - rect.top) * scaleY;
  const CELL_SIZE = 20;
  return { blockX: Math.floor(x / CELL_SIZE), blockY: Math.floor(y / CELL_SIZE) };
};



const normalizeRect = (rect: Rect): Rect => ({
  x0: Math.min(rect.x0, rect.x1),
  y0: Math.min(rect.y0, rect.y1),
  x1: Math.max(rect.x0, rect.x1),
  y1: Math.max(rect.y0, rect.y1),
});

const rectToCells = (rect: Rect) => {
  const normalized = normalizeRect(rect);
  const cells: { x: number; y: number }[] = [];
  for (let y = normalized.y0; y <= normalized.y1; y++) {
    for (let x = normalized.x0; x <= normalized.x1; x++) {
      cells.push({ x, y });
    }
  }
  return cells;
};

const markPlanDirty = () => {
  planDirty.value = true;
  skippedPlannedBlocks.value = [];
};

const commitSelection = (status: RegionStatus) => {
  if (selectionRects.value.length === 0) return;

  for (const selection of selectionRects.value) {
    for (const cell of rectToCells(selection)) {
      const key = `${cell.x},${cell.y}`;
      pendingBlocks.value.delete(key);
      completedBlocks.value.delete(key);
      ignoredBlocks.value.delete(key);

      if (status === 'pending') {
        pendingBlocks.value.add(key);
      } else if (status === 'completed') {
        completedBlocks.value.add(key);
      } else if (status === 'ignored') {
        ignoredBlocks.value.add(key);
      }
    }
  }

  selectionRects.value = [];
  regionStartCoords.value = null;
  currentDrawCoords.value = null;
  markPlanDirty();
  drawBlueprint(currentBlueprint.value, currentPipeline.value);
};

const markSelectionStatus = (status: RegionStatus) => {
  commitSelection(status);
};

const handleCanvasMouseDown = (e: MouseEvent) => {
  if (!currentBlueprint.value) return;
  const { blockX, blockY } = getBlockCoords(e);
  clickStartPos = { x: e.clientX, y: e.clientY };
  
  if (e.button === 0) { // Left click
    drawMode.value = 'add';
    selectionRects.value = []; // Clear previous selection
  } else {
    return;
  }
  
  isDrawingRegion.value = true;
  regionStartCoords.value = { x: blockX, y: blockY };
  currentDrawCoords.value = { x: blockX, y: blockY };
};

const handleCanvasMouseMove = (e: MouseEvent) => {
  if (isDrawingRegion.value) {
    const { blockX, blockY } = getBlockCoords(e);
    currentDrawCoords.value = { x: blockX, y: blockY };
    drawBlueprint(currentBlueprint.value, currentPipeline.value);
  }
};

const getPendingBlocksList = () => Array.from(pendingBlocks.value);

const getPlanningCompletedBlocks = () => {
  return Array.from(completedBlocks.value);
};

const planCurrentBlueprint = async () => {
  if (!currentBlueprint.value) return null;
  try {
    const planRes = await axios.post(`${API_BASE}/blueprint/plan`, {
      blueprint: currentBlueprint.value,
      pending_blocks: getPendingBlocksList(),
      completed_blocks: getPlanningCompletedBlocks(),
    });
    currentPipeline.value = planRes.data.pipeline || [];
    pipelineProgress.value = 0;
    pipelineTotal.value = currentPipeline.value.length;
    skippedPlannedBlocks.value = planRes.data.skipped_blocks || [];
    planDirty.value = false;
    drawBlueprint(currentBlueprint.value, currentPipeline.value);
    addLog(`规划完成，共 ${pipelineTotal.value} 步`);
    return planRes.data;
  } catch (error: any) {
    const errDetailObj = error?.response?.data?.detail;
    const detail = typeof errDetailObj === 'object' ? (errDetailObj.detail || '规划失败') : (errDetailObj || error?.message || '规划失败');
    const errorBlocks = typeof errDetailObj === 'object' ? errDetailObj.error_blocks : undefined;
    
    if (errorBlocks) {
      skippedPlannedBlocks.value = errorBlocks;
      drawBlueprint(currentBlueprint.value, []);
    }
    ElMessage.error(detail);
    addLog(`[规划失败] ${detail}`);
    return null;
  }
};

const handleCanvasMouseUp = (e: MouseEvent) => {
  if (!isDrawingRegion.value) return;
  isDrawingRegion.value = false;
  
  const dist = Math.hypot(e.clientX - clickStartPos.x, e.clientY - clickStartPos.y);
  
  if (dist < 5 && e.button === 0 && regionStartCoords.value) {
    findAndJumpToStep(regionStartCoords.value.x, regionStartCoords.value.y);
    selectionRects.value = [];
    drawBlueprint(currentBlueprint.value, currentPipeline.value);
  } else if (regionStartCoords.value && currentDrawCoords.value) {
    const x0 = Math.min(regionStartCoords.value.x, currentDrawCoords.value.x);
    const x1 = Math.max(regionStartCoords.value.x, currentDrawCoords.value.x);
    const y0 = Math.min(regionStartCoords.value.y, currentDrawCoords.value.y);
    const y1 = Math.max(regionStartCoords.value.y, currentDrawCoords.value.y);

    const rect = { x0, y0, x1, y1 };
    selectionRects.value = [rect];
    markPlanDirty();
    drawBlueprint(currentBlueprint.value, currentPipeline.value);
  } else {
    regionStartCoords.value = null;
    currentDrawCoords.value = null;
    drawBlueprint(currentBlueprint.value, currentPipeline.value);
  }
  regionStartCoords.value = null;
  currentDrawCoords.value = null;
};

const findAndJumpToStep = async (bx: number, by: number) => {
  if (!currentBlueprint.value) return;
  try {
    if (planDirty.value) {
      await planCurrentBlueprint();
    }
    const pipeline = currentPipeline.value || [];
    currentPipeline.value = pipeline;
    
    const index = pipeline.findIndex((s: any) => s.type === 'place_and_dye' && s.x === bx && s.y === by);
    if (index !== -1) {
      pipelineProgress.value = index;
      drawBlueprint(currentBlueprint.value, pipeline);
      addLog(`已跳转至坐标 (${bx}, ${by})，下一步将从此处开始`);
    } else {
      addLog(`点选的方块 (${bx}, ${by}) 不在区域规划中，建议重新框选或直接点击给定的起始蓝色方块。`);
    }
  } catch(e) {}
};

const resetProgress = () => {
  pipelineProgress.value = 0;
  completedBlocks.value.clear();
  planDirty.value = true;
  skippedPlannedBlocks.value = [];
  drawBlueprint(currentBlueprint.value, currentPipeline.value);
  addLog('已重置任务进度');
};

let foregroundTimer: number | undefined;
let ws: WebSocket | null = null;
const logContainer = ref<HTMLElement | null>(null);

const reversedLogs = computed(() => [...logs.value].reverse());
const backendLogBuffer = ref<string[]>([]);

const selectedWindow = computed(() => windowOptions.value.find((window) => window.hwnd === selectedWindowHwnd.value) ?? null);

const handleSelect = (index: string) => { activeTab.value = index; };

const runExclusiveAction = async <T>(action: () => Promise<T>): Promise<T> => {
  while (actionBusy.value) {
    await new Promise((resolve) => setTimeout(resolve, 10));
  }
  actionBusy.value = true;
  try {
    return await action();
  } finally {
    actionBusy.value = false;
  }
};

const scrollLogsToLatest = () => {
  nextTick(() => {
    if (logContainer.value) logContainer.value.scrollTop = 0;
  });
};

const addLog = (msg: string) => {
  logs.value.push(`[${new Date().toLocaleTimeString()}] ${msg}`);
  if (!debugMode.value && logs.value.length > 200) logs.value.shift();
  scrollLogsToLatest();
};

const addBackendLog = (msg: string) => {
  const line = `[${new Date().toLocaleTimeString()}] [后端] ${msg}`;
  if (debugMode.value) {
    logs.value.push(line);
    scrollLogsToLatest();
    return;
  }
  backendLogBuffer.value.push(line);
  if (backendLogBuffer.value.length > 1000) backendLogBuffer.value.shift();
};

watch(debugMode, (enabled) => {
  if (enabled && backendLogBuffer.value.length > 0) {
    logs.value.push(...backendLogBuffer.value);
    backendLogBuffer.value = [];
    scrollLogsToLatest();
  }
});

const connectWebSocket = () => {
  ws = new WebSocket('ws://127.0.0.1:8000/api/ws/logs');
  ws.onmessage = (event) => addBackendLog(event.data);
  ws.onclose = () => {
    addLog(`WebSocket 已断开，3秒后重连...`);
    setTimeout(connectWebSocket, 3000);
  };
};

const handleImageChange = (file: UploadFile) => {
  if (!file || !file.raw) return;
  const allowed = ['image/png', 'image/jpeg'];
  const f = file.raw as File;
  if (!allowed.includes(f.type)) {
    ElMessage.error('只支持 PNG 或 JPG 格式的图片');
    return;
  }
  uploadedFile.value = f;
  // Fast preview without backend
  const reader = new FileReader();
  reader.onload = (e) => {
    const img = new Image();
    img.onload = () => { 
      originalRatio.value = img.width / img.height;
      if (keepRatio.value) {
        bpHeight.value = Math.round(bpWidth.value / originalRatio.value);
      }
      drawPreviewRaw(img); 
    };
    img.src = e.target?.result as string;
  };
  reader.readAsDataURL(file.raw);
};

const drawPreviewRaw = (img: HTMLImageElement) => {
  const canvas = previewCanvasStatic.value;
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;
  canvas.width = bpWidth.value * 20 || 600;
  canvas.height = bpHeight.value * 20 || 600;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
};

const drawBlueprint = (bp: any, pipeline: any[] = []) => {
  // Update both canvases
  [previewCanvas.value, previewCanvasStatic.value].forEach(canvas => {
    if (!canvas) return;
    const isStatic = canvas === previewCanvasStatic.value;
    const CELL_SIZE = 20;
    canvas.width = bp.resolution[0] * CELL_SIZE;
    canvas.height = bp.resolution[1] * CELL_SIZE;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    let nextStepCoords: string | null = null;
    
    const activePipeline = !planDirty.value ? (pipeline.length > 0 ? pipeline : currentPipeline.value) : [];
    
    if (!isStatic && activePipeline.length > 0) {
      // Find the next step to execute
      for (let i = pipelineProgress.value; i < activePipeline.length; i++) {
        const s = activePipeline[i];
        if (s.type === 'place_and_dye') {
          nextStepCoords = `${s.x},${s.y}`;
          break;
        }
      }
    }
    
    for (const block of bp.blocks) {
      ctx.fillStyle = block.color;
      ctx.fillRect(block.x * CELL_SIZE, block.y * CELL_SIZE, CELL_SIZE, CELL_SIZE);
      
      if (!isStatic) {
        const key = `${block.x},${block.y}`;
        const isCompleted = completedBlocks.value.has(key);
        const isPending = pendingBlocks.value.has(key);

        if (isCompleted) {
          ctx.fillStyle = 'rgba(92, 219, 149, 0.4)';
          ctx.fillRect(block.x * CELL_SIZE, block.y * CELL_SIZE, CELL_SIZE, CELL_SIZE);
        }

        if (isPending) {
          ctx.save();
          ctx.strokeStyle = 'black';
          ctx.lineWidth = 3;
          ctx.lineCap = 'round';
          const bx = block.x * CELL_SIZE;
          const by = block.y * CELL_SIZE;
          
          if (!pendingBlocks.value.has(`${block.x},${block.y - 1}`)) {
            ctx.beginPath(); ctx.moveTo(bx, by); ctx.lineTo(bx + CELL_SIZE, by); ctx.stroke();
          }
          if (!pendingBlocks.value.has(`${block.x + 1},${block.y}`)) {
            ctx.beginPath(); ctx.moveTo(bx + CELL_SIZE, by); ctx.lineTo(bx + CELL_SIZE, by + CELL_SIZE); ctx.stroke();
          }
          if (!pendingBlocks.value.has(`${block.x},${block.y + 1}`)) {
            ctx.beginPath(); ctx.moveTo(bx, by + CELL_SIZE); ctx.lineTo(bx + CELL_SIZE, by + CELL_SIZE); ctx.stroke();
          }
          if (!pendingBlocks.value.has(`${block.x - 1},${block.y}`)) {
            ctx.beginPath(); ctx.moveTo(bx, by); ctx.lineTo(bx, by + CELL_SIZE); ctx.stroke();
          }
          ctx.restore();
        }

        if (key === nextStepCoords) {
          ctx.fillStyle = 'rgba(0, 150, 255, 0.7)';
          ctx.fillRect(block.x * CELL_SIZE, block.y * CELL_SIZE, CELL_SIZE, CELL_SIZE);
        }
      }
    }

    if (!isStatic) {
      for (const rect of selectionRects.value) {
        const width = (rect.x1 - rect.x0 + 1) * CELL_SIZE;
        const height = (rect.y1 - rect.y0 + 1) * CELL_SIZE;
        ctx.save();
        ctx.setLineDash([6, 4]);
        ctx.strokeStyle = 'rgba(120, 190, 255, 0.95)';
        ctx.lineWidth = 2;
        ctx.strokeRect(rect.x0 * CELL_SIZE, rect.y0 * CELL_SIZE, width, height);
        ctx.restore();
      }

      if (activePipeline.length > 0) {
        ctx.beginPath();
        ctx.strokeStyle = 'rgba(255, 140, 0, 0.95)';
        ctx.lineWidth = 3;
        let firstPoint = true;
        for (let i = 0; i < activePipeline.length; i++) {
          const tempStep = activePipeline[i];
          if (tempStep.type === 'place_and_dye') {
            const cx = tempStep.x * CELL_SIZE + CELL_SIZE / 2;
            const cy = tempStep.y * CELL_SIZE + CELL_SIZE / 2;
            if (firstPoint) {
              ctx.moveTo(cx, cy);
              firstPoint = false;
            } else {
              ctx.lineTo(cx, cy);
            }
          }
        }
        ctx.stroke();

        for (const skipped of skippedPlannedBlocks.value) {
          ctx.save();
          ctx.fillStyle = 'rgba(255, 0, 0, 0.6)';
          ctx.fillRect(skipped.x * CELL_SIZE, skipped.y * CELL_SIZE, CELL_SIZE, CELL_SIZE);
          ctx.strokeStyle = '#ff0000';
          ctx.lineWidth = 2;
          ctx.strokeRect(skipped.x * CELL_SIZE, skipped.y * CELL_SIZE, CELL_SIZE, CELL_SIZE);
          ctx.restore();
        }
      }
    }

    // Draw prominent grid
    ctx.strokeStyle = "rgba(0, 0, 0, 0.3)";
    ctx.lineWidth = 1;
    if (bp.resolution[0] <= 512) {
      ctx.beginPath();
      for (let i = 0; i <= bp.resolution[0]; i++) {
        ctx.moveTo(i * CELL_SIZE, 0); 
        ctx.lineTo(i * CELL_SIZE, canvas.height);
      }
      for (let j = 0; j <= bp.resolution[1]; j++) {
        ctx.moveTo(0, j * CELL_SIZE); 
        ctx.lineTo(canvas.width, j * CELL_SIZE);
      }
      ctx.stroke();
    }

    // Draw current drag region
    if (!isStatic && isDrawingRegion.value && regionStartCoords.value && currentDrawCoords.value) {
      const rx0 = Math.min(regionStartCoords.value.x, currentDrawCoords.value.x);
      const rx1 = Math.max(regionStartCoords.value.x, currentDrawCoords.value.x);
      const ry0 = Math.min(regionStartCoords.value.y, currentDrawCoords.value.y);
      const ry1 = Math.max(regionStartCoords.value.y, currentDrawCoords.value.y);
      
      ctx.save();
      ctx.setLineDash([6, 4]);
      ctx.strokeStyle = drawMode.value === 'add' ? 'rgba(120, 190, 255, 0.95)' : 'rgba(255, 120, 120, 0.95)';
      ctx.lineWidth = 2;
      ctx.strokeRect(rx0 * CELL_SIZE, ry0 * CELL_SIZE, (rx1 - rx0 + 1) * CELL_SIZE, (ry1 - ry0 + 1) * CELL_SIZE);
      ctx.restore();
    }
  });
};

const currentPipeline = ref<any[]>([]);

const exportTask = async () => {
  if (!currentBlueprint.value) return;
  const data = JSON.stringify({
    blueprint: currentBlueprint.value,
    pipelineProgress: pipelineProgress.value,
    completedBlocks: Array.from(completedBlocks.value),
    currentPipeline: currentPipeline.value,
    selectionRects: selectionRects.value,
    pendingBlocks: Array.from(pendingBlocks.value),
    ignoredBlocks: Array.from(ignoredBlocks.value),
    planDirty: planDirty.value,
  }, null, 2);

  try {
    if ('showSaveFilePicker' in window) {
      const handle = await (window as any).showSaveFilePicker({
        suggestedName: `calabiyau-task-${new Date().getTime()}.json`,
        types: [{
          description: 'JSON File',
          accept: { 'application/json': ['.json'] },
        }],
      });
      const writable = await handle.createWritable();
      await writable.write(data);
      await writable.close();
      ElMessage.success('任务进度已成功保存');
    } else {
      // Fallback for browsers that don't support showSaveFilePicker
      const blob = new Blob([data], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `calabiyau-task-${new Date().getTime()}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      ElMessage.success('任务进度已下载到本地');
    }
  } catch (err: any) {
    if (err.name !== 'AbortError') {
      ElMessage.error(`保存失败: ${err.message}`);
    }
  }
};

const importTask = (file: UploadFile) => {
  if (!file || !file.raw) return;
  const reader = new FileReader();
  reader.onload = (e) => {
    try {
      const data = JSON.parse(e.target?.result as string);
      currentBlueprint.value = data.blueprint;
      pipelineProgress.value = data.pipelineProgress || 0;
      completedBlocks.value = new Set(data.completedBlocks || []);
      currentPipeline.value = data.currentPipeline || [];
      selectionRects.value = data.selectionRects || [];
      pendingBlocks.value = new Set(data.pendingBlocks || []);
      ignoredBlocks.value = new Set(data.ignoredBlocks || []);
      planDirty.value = data.planDirty ?? currentPipeline.value.length === 0;
      skippedPlannedBlocks.value = [];
      
      bpWidth.value = data.blueprint.resolution[0];
      bpHeight.value = data.blueprint.resolution[1];
      
      drawBlueprint(currentBlueprint.value, currentPipeline.value);
      nextTick(() => { calculateInitialZoom(); });
      ElMessage.success('任务进度已导入');
      activeTab.value = 'task'; // Switch to task tab automatically
    } catch (err: any) {
      ElMessage.error(`导入失败: ${err.message}`);
    }
  };
  reader.readAsText(file.raw);
};

const generateBlueprint = async () => {
  if (!uploadedFile.value) return;
  isGenerating.value = true;
  const formData = new FormData();
  formData.append('file', uploadedFile.value);
  formData.append('width', bpWidth.value.toString());
  formData.append('height', bpHeight.value.toString());
  formData.append('extract_lineart', extractLineart.value.toString());
  formData.append('reduce_noise', reduceNoise.value.toString());

  try {
    const res = await axios.post(`${API_BASE}/blueprint/process`, formData);
    if (res.data.status === 'success') {
      currentBlueprint.value = res.data.blueprint;
      currentPipeline.value = [];
      planDirty.value = true;
      skippedPlannedBlocks.value = [];
      drawBlueprint(currentBlueprint.value, []);
      nextTick(() => { calculateInitialZoom(); });
      ElMessage.success('蓝图处理完成');
    }
  } catch (err: any) {
    ElMessage.error(`蓝图生成失败: ${err.message}`);
  } finally {
    isGenerating.value = false;
  }
};

// ----------------------
// Task Runner Macros
// ----------------------
const getTargetPayload = () => ({
  exe_name: selectedWindow.value?.exe_name || 'Calabiyau-Win64-Shipping.exe',
  window_hwnd: selectedWindowHwnd.value ?? undefined,
  focus_settle_delay: focusSettleDelay.value,
  place_key_delay: placeKeyDelay.value,
  place_click_delay: placeClickDelay.value,
  move_hold_delay: moveHoldDelay.value,
  dye_open_delay: dyeOpenDelay.value,
  dye_paste_delay: dyePasteDelay.value,
  dye_confirm_delay: dyeConfirmDelay.value,
  dye_return_delay: dyeReturnDelay.value,
  ui_click_delay: uiClickDelay.value,
  ui_clipboard_delay: uiClipboardDelay.value,
  move_sample_rate: moveSampleRate.value,
  humanize_level: humanizeLevel.value,
});

const startAutoBuild = async () => {
  if (!currentBlueprint.value) return;
  busy.value = true;
  shouldStop.value = false;
  
  try {
    if (planDirty.value || currentPipeline.value.length === 0) {
      addLog('正在向服务端请求计划...');
      const planData = await planCurrentBlueprint();
      if (!planData) {
        busy.value = false;
        return;
      }

      if (planData.is_fallback) {
        try {
          await ElMessageBox.confirm(
            '选区为空或已完成，是否搭建剩余未完成的区域？',
            '提示',
            {
              confirmButtonText: '确定',
              cancelButtonText: '取消',
              type: 'info',
            }
          );
        } catch (err) {
          addLog('用户取消自动搭建剩余区域。');
          busy.value = false;
          return;
        }
      }
    }

    const pipeline = currentPipeline.value;
    pipelineProgress.value = 0;
    pipelineTotal.value = pipeline.length;
    
    if (pipeline.length === 0) {
      addLog('没有需要搭建的方块，自动搭建结束。');
      busy.value = false;
      return;
    }
    
    drawBlueprint(currentBlueprint.value, pipeline);
    addLog(`计划就绪，共 ${pipelineTotal.value} 步`);
    await prepareWindowFocus();
    // 记录基线绿色标记距离，用于后续任务中检测视角偏移并用 W/S 微调
    try {
      const dres = await axios.post(`${API_BASE}/vision/green-distance`, { roi_size: 315 });
      if (dres.data?.status === 'success') {
        baselineGreenDistance.value = Number(dres.data.distance);
        addLog(`[视角调整] 已记录基线绿色标记距离: ${baselineGreenDistance.value.toFixed(2)}`);
      } else {
        addLog('[视角调整] 未能记录基线绿色标记距离，视角动态调整将被跳过');
        baselineGreenDistance.value = null;
      }
    } catch (e: any) {
      baselineGreenDistance.value = null;
      addLog('[视角调整] 请求基线距离失败，跳过动态视角调整');
    }

    // 遍历步骤的经典大循环
    for (let i = pipelineProgress.value; i < pipeline.length; i++) {
      if (shouldStop.value) {
        addLog('收到用户停止命令，任务中断。');
        break;
      }
      pipelineProgress.value = i + 1;
      drawBlueprint(currentBlueprint.value, pipeline);
      const step = pipeline[i];
      addLog(`执行步骤 ${i+1}/${pipeline.length}: ${JSON.stringify(step)}`);
      
      // ==========================================
      // 分支一：放置与染色分支（支持并发排他锁、复活 isRecovery）
      // ==========================================
      // 在每一步之前检测绿色标记距离的偏移，超过阈值则用 W/S 微调视角
      try {
        if (baselineGreenDistance.value !== null) {
          // delegate adjustment decision & sampling to backend move-keep endpoint
          const payload = {
            ...getTargetPayload(),
            direction: 'w',
            timeout: viewAdjustNudgeTimeout.value,
            baseline_distance: baselineGreenDistance.value,
            threshold_ratio: viewAdjustThresholdPercent.value / 100.0,
          };

          // if we want to nudge towards canvas (W), use direction 'w'; if away (S), use 's'.
          // Here we probe current distance first to decide which direction to send.
          const cur = await axios.post(`${API_BASE}/vision/green-distance`, { roi_size: 315 });
          if (cur.data?.status === 'success' && cur.data.distance != null) {
            const curDist = Number(cur.data.distance);
            const delta = curDist - baselineGreenDistance.value;
            if (Math.abs(delta) > Math.max(1.0, baselineGreenDistance.value * (viewAdjustThresholdPercent.value / 100.0))) {
              if (delta < 0) {
                addLog(`[视角调整] 距离偏小 ${delta.toFixed(2)}，发送 W 微调`);
                payload.direction = 'w';
              } else {
                addLog(`[视角调整] 距离偏大 ${delta.toFixed(2)}，发送 S 微调`);
                payload.direction = 's';
              }
              await axios.post(`${API_BASE}/macro/move-keep`, payload);
              // 小等待让视角稳定
              await new Promise(r => setTimeout(r, 150));
            }
          }
        }
      } catch (e) {
        // ignore noisy adjust failures
      }
      if (step.type === 'place_and_dye') {
        await runExclusiveAction(async () => {
          let currentBlockRetryCount = 0; // 主流程首次放置染色的异常校验计数

          const executeDye = async (isRecovery = false) => {
            // 放置 (如果是恢复重试，说明面板未关闭且方块已放，不需要重新放置)
            if (!isRecovery) {
              await axios.post(`${API_BASE}/macro/place`, getTargetPayload());
            }

            const dyeWithVerify = async (isRepaste = false) => {
              // 染色核心宏：执行粘贴逻辑
              await axios.post(`${API_BASE}/macro/dye`, {
                ...getTargetPayload(),
                hex_color: step.color,
                color_input_x: configPaletteX.value,
                color_input_y: configPaletteY.value,
                repaste_only: isRepaste
              });

              // 染色后取色校验
              const targetColor = step.color.toUpperCase();
              const verifyRes = await axios.post(`${API_BASE}/vision/get-color`, {
                x: configVerifyX.value,
                y: configVerifyY.value
              });
              const actualColor = verifyRes.data.color.toUpperCase();
              const isValidColor = !(/^#(000000|222222|FFFFFF)$/i.test(actualColor));
              const isSameColor = actualColor === targetColor;
              
              // 异常状态检测（全黑/全白等画面异常，且不是目标颜色）
              if (!isValidColor && !isSameColor) {
                // 如果是从 move 移动失败分支回退进来的，将控制权向上抛给 lastDyeAction 的 while 循环
                if (isRecovery) {
                  addLog(`[Recovery Verify] 检测到染色代码异常(${actualColor})，交由回退外层循环处理`);
                  throw new Error('Verification failed during recovery');
                }

                // 正常主流程的首次重试判定
                if (currentBlockRetryCount < dyeRetryCount.value) {
                  currentBlockRetryCount++;
                  addLog(`[Verify] 检测到染色代码异常(${actualColor})，尝试重新粘贴 (重试 ${currentBlockRetryCount}/${dyeRetryCount.value})...`);
                  await new Promise(r => setTimeout(r, 200));
                  return await dyeWithVerify(true); // 保留面板只重贴
                } else {
                  addLog(`[Verify] 染色框连续异常，重试次数已达上限，强行继续`);
                }
              }
            };
            
            // 执行粘贴与校验
            await dyeWithVerify(isRecovery);
            
            // 统一点击“确认”关闭染色面板
            await axios.post(`${API_BASE}/macro/dye-confirm`, {
              ...getTargetPayload(),
              confirm_button_x: configConfirmX.value,
              confirm_button_y: configConfirmY.value
            });
          };

          // 1. 执行正常的初次染色主流程
          await executeDye();
          
          const key = `${step.x},${step.y}`;
          completedBlocks.value.add(key);
          pendingBlocks.value.delete(key);
          ignoredBlocks.value.delete(key);
          drawBlueprint(currentBlueprint.value, pipeline);

          // 2. 闭包工厂：为当前方块绑定隔离的回退计数器，阻断与下一个方块的相互污染
          const createRecoveryAction = () => {
            let recoveryRetryCount = 0; // 该方块独享的恢复尝试计数器

            return async () => {
              while (recoveryRetryCount < dyeRetryCount.value) {
                recoveryRetryCount++;
                addLog(`[Recovery] 未发现🟢，判定面板未关。开始回退重新粘贴染色 (第 ${recoveryRetryCount}/${dyeRetryCount.value} 次尝试)...`);
                
                try {
                  // 完美联动：传入 true，告知 executeDye 内部跳过放置动作，直达重贴与校验确认
                  await executeDye(true); 
                  addLog('[Recovery] 回退操作成功完成，已成功重新确认颜色');
                  return true; // 挽回成功
                } catch (error) {
                  addLog(`[Recovery] 第 ${recoveryRetryCount} 次回退重贴校验依旧异常`);
                  if (recoveryRetryCount < dyeRetryCount.value) {
                    await new Promise(r => setTimeout(r, 200)); // 必要的防震荡等待
                  }
                }
              }
              addLog(`[Recovery] 达到最大回退重试次数(${dyeRetryCount.value})，放弃本次回退。`);
              return false; // 挽回彻底失败
            };
          };

          // 存储到全局追踪的 Ref 变量中，供下一步使用
          lastDyeAction.value = createRecoveryAction();
        });

      // ==========================================
      // 分支二：移动分支（无缝对接回退机制、独立排他锁）
      // ==========================================
      } else if (step.type === 'move') {
        await runExclusiveAction(async () => {
          try {
            const moveRes = await axios.post(`${API_BASE}/macro/move-to-next-block`, {
              ...getTargetPayload(),
              direction: step.direction,
              timeout: 10.0
            });

            if (moveRes.data.status === 'failed_to_find_marker') {
              addLog('未发现🟢，视为染色面板未正常关闭，尝试触发回退挽回...');
              
              if (lastDyeAction.value) {
                // 执行上面闭包锁定过的回退逻辑（在 move 分支的排他锁内部平滑完成）
                const canRetry = await lastDyeAction.value();
                if (canRetry) {
                  addLog('[Recovery] 上一步颜色挽回成功，正在进行二次移动定位...');
                  // 回退修正完毕，再次尝试移动
                  const retryMoveRes = await axios.post(`${API_BASE}/macro/move-to-next-block`, {
                    ...getTargetPayload(),
                    direction: step.direction,
                    timeout: 10.0
                  });
                  if (retryMoveRes.data.status === 'failed_to_find_marker') {
                    throw new Error('回退重新染色后依然无法定位🟢，任务终止');
                  }
                } else {
                  throw new Error('回退重试次数耗尽，任务终止');
                }
              } else {
                throw new Error('无上一步染色操作记录，无法执行回退，任务终止');
              }
            }
          } catch (err: any) {
            throw err;
          }
        });
      }
    }
  } catch (err: any) {
    handleApiError(err);
  } finally {
    busy.value = false;
  }
};

const stopAutoBuild = async () => {
  shouldStop.value = true;
  busy.value = false;
  try {
    await axios.post(`${API_BASE}/system/abort`);
    addLog('[UI] 已发送强制停止信号并解开前端锁定');
  } catch (err) {
    addLog(`[Error] 强制中止通讯失败`);
  }
};

// ----------------------
// Utils & Helpers
// ----------------------
const formatWindowLabel = (w: WindowInfo) => `${w.title} (${w.exe_name || '未知'})${w.is_foreground ? ' [前台]' : ''}`;

const refreshWindows = async () => {
  try {
    const res = await axios.get(`${API_BASE}/system/windows`);
    windowOptions.value = res.data.windows || [];
    if (!selectedWindowHwnd.value || !windowOptions.value.some((w) => w.hwnd === selectedWindowHwnd.value)) {
      const target = windowOptions.value.find((window) => window.title.includes('卡拉彼丘')) || windowOptions.value[0];
      if (target) {
        selectedWindowHwnd.value = target.hwnd;
      }
    }
  } catch (e: any) {
    ElMessage.error('无法获取窗口列表');
  }
};

const selectCalabiyau = async () => {
  await refreshWindows();
  const target = windowOptions.value.find((window) =>
    (window.exe_name && window.exe_name.toLowerCase().includes('calabiyau')) && window.title.includes('卡拉彼丘')
  );
  if (target) {
    selectedWindowHwnd.value = target.hwnd;
    addLog(`[UI] 已自动选中卡丘窗口: ${target.title}`);
  } else {
    ElMessage.warning('未找到卡拉彼丘进程或窗口');
    addLog('[UI] 未找到卡丘窗口，请确认游戏是否正在运行。');
  }
};

const tryActivateTargetWindow = async () => {
  if (!autoActivateWindow.value || !selectedWindowHwnd.value) return false;
  try {
    const res = await axios.post(`${API_BASE}/system/activate`, {
      hwnd: selectedWindowHwnd.value,
      exe_name: selectedWindow.value?.exe_name,
    });
    return res.data?.status === 'success';
  } catch (e: any) {
    return false;
  }
};

const waitForManualSwitch = async () => {
  for (let i = delaySeconds.value; i > 0; i--) {
    addLog(`请在 ${i} 秒内手动切换到目标窗口...`);
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
};

const prepareWindowFocus = async () => {
  const activated = await tryActivateTargetWindow();
  if (!activated) await waitForManualSwitch();
};

const handleApiError = (e: any) => {
  const status = e.response?.status;
  const detail = e.response?.data?.detail || e.message;
  if (status === 409) {
      addLog(`操作因游戏掉失焦点中断: ${detail}`);
      ElMessage.warning('前台窗口不是目标窗口，任务已终止');
      shouldStop.value = true;
  } else {
      addLog(`操作失败: ${detail}`);
  }
}

const testClick = async () => {
  try {
    busy.value = true;
    await prepareWindowFocus();
    await axios.post(`${API_BASE}/control/click`, { button: 'left', ...getTargetPayload() });
  } catch (e: any) { handleApiError(e); } finally { busy.value = false; }
};
const testMove = async () => {
  try {
    busy.value = true;
    await prepareWindowFocus();
    await axios.post(`${API_BASE}/macro/move-to-next-block`, { direction: 'd', timeout: 5.0, ...getTargetPayload() });
  } catch (e: any) { handleApiError(e); } finally { busy.value = false; }
};
const testVision = async () => {
  try {
    await axios.post(`${API_BASE}/vision/analyze-green`, { roi_size: 315 });
  } catch (e: any) {}
};

const testGetColor = async () => {
  try {
    const res = await axios.post(`${API_BASE}/vision/get-color`, { x: configVerifyX.value, y: configVerifyY.value });
    addLog(`采样颜色: ${res.data.color}`);
  } catch (e: any) {}
};



const refreshForegroundWindow = async () => {
  try {
    const res = await axios.get(`${API_BASE}/system/foreground`);
    foregroundWindow.value = res.data.window || null;
  } catch (e) {}
};

const handleGlobalKeydown = (e: KeyboardEvent) => {
  const hotkey = startBuildHotkey.value?.trim().toLowerCase();
  if (!hotkey) return;

  const parts = hotkey.replace(/ /g, '').split('+');
  const needsCtrl = parts.includes('ctrl');
  const needsAlt = parts.includes('alt');
  const needsShift = parts.includes('shift');
  const key = parts[parts.length - 1];

  const isCtrl = e.ctrlKey || e.metaKey;
  const isAlt = e.altKey;
  const isShift = e.shiftKey;

  if (
    isCtrl === needsCtrl &&
    isAlt === needsAlt &&
    isShift === needsShift &&
    e.key.toLowerCase() === key
  ) {
    e.preventDefault();
    if (busy.value) {
      stopAutoBuild();
    } else if (currentBlueprint.value) {
      startAutoBuild();
    }
  }
};

onMounted(() => {
  refreshWindows();
  refreshForegroundWindow();
  connectWebSocket();
  foregroundTimer = window.setInterval(refreshForegroundWindow, 1000);
  window.addEventListener('keydown', handleGlobalKeydown);
});

onBeforeUnmount(() => {
  if (foregroundTimer) window.clearInterval(foregroundTimer);
  if (ws) ws.close();
  window.removeEventListener('keydown', handleGlobalKeydown);
});
</script>

<style scoped>
/* Layout */
.app-layout { height: 100vh; background: #f8fafc; }
.nav-aside { background: white; border-right: 1px solid #e2e8f0; }
.logo-box { padding: 24px 20px; border-bottom: 1px solid #f1f5f9; }
.logo-text { margin: 0; color: #1e293b; font-size: 18px; }
.nav-menu { border-right: none; }
.main-container { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.system-monitor { display: flex; align-items: center; background: white; border-bottom: 1px solid #e2e8f0; padding: 0 20px; font-size: 13px; z-index: 10; }
.content-main { flex: 1; padding: 20px; overflow-y: auto; }

/* Dashboard/Task Page */
.task-workflow { display: flex; flex-direction: column; height: 100%; gap: 15px; }
.workflow-header { 
  display: flex; justify-content: space-between; align-items: center; 
  padding: 12px 20px; background: white; border-radius: 8px; border: 1px solid #e2e8f0;
}
.status-info { font-weight: 500; font-size: 14px; }
.workspace-area { 
  flex: 1; background: #e2e8f0; border-radius: 8px; position: relative; 
  border: 1px solid #cbd5e1;
}
.scrollable-workspace { overflow: auto; }
.main-canvas-wrapper { min-width: 100%; min-height: 100%; display: grid; place-items: center; padding: 40px; box-sizing: border-box; }
.pixel-canvas.interactive { 
  background: white; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.3); 
  image-rendering: pixelated;
}

/* Local Log in Task page */
.log-footer-mini { height: 180px; background: white; border-radius: 8px; border: 1px solid #e2e8f0; display: flex; flex-direction: column; }
.log-header-mini { padding: 8px 15px; border-bottom: 1px solid #f1f5f9; display: flex; justify-content: space-between; align-items: center; font-size: 13px; color: #64748b; }
.log-content-mini { flex: 1; overflow-y: auto; background: #1a1a1a; color: #d4d4d4; padding: 12px; font-family: 'Consolas', monospace; font-size: 12px; }
.log-line { margin: 2px 0; border-bottom: 1px dashed #333; padding-bottom: 2px; }

/* Image/Blueprint page */
.image-panel .canvas-container { 
  background: #f1f5f9; border-radius: 12px; padding: 20px; 
  display: flex; align-items: center; justify-content: center; height: 500px;
  overflow: hidden;
}
.pixel-canvas { image-rendering: pixelated; border: 1px solid #e2e8f0; background: white; }
.static-canvas { max-width: 100%; max-height: 100%; object-fit: contain; }

/* Common Components */
.settings-card { border-radius: 12px; border: 1px solid #e2e8f0; padding: 5px; }
.setting-item { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.setting-item .label { font-size: 14px; width: 100px; color: #475569; }
.full-width-btn { width: 100%; }
.full-width-select { width: 100%; }
.empty-state { color: #94a3b8; font-size: 14px; }
.ml-2 { margin-left: 8px; } .mt-3 { margin-top: 12px; } .mt-4 { margin-top: 16px; } .mb-3 { margin-bottom: 12px; }
</style>
