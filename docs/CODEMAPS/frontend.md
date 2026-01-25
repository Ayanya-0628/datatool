# 前端架构 (Frontend)

**最后更新:** 2026-01-25
**入口文件:** `templates/dashboard.html`, `static/app.js`

## 架构概览

```
Frontend
├── templates/
│   └── dashboard.html    # 主界面 HTML 模板
└── static/
    ├── app.js            # 交互逻辑 (2292 行)
    └── style.css         # 样式文件 (Carbon Design 风格)
```

## 全局状态管理

```javascript
let appState = {
    dataId: null,           // 当前数据 UUID
    columns: [],            // 所有列名
    factors: [],            // 选中的因子
    targets: [],            // 选中的性状
    pcaGroups: [],          // PCA 分组变量
    results: null,          // 分析结果
    analysisType: 'anova',  // 'anova' | 'pca' | 'cluster'

    // 聚类参数
    clusterFilter: 'all',
    clusterParams: {
        algorithm: 'kmeans',
        n_clusters: 3,
        linkage_method: 'ward'
    },

    // 多选状态
    selectedItems: [],
    lastSelectedIndex: -1
};
```

## DOM 元素索引

```javascript
const elements = {
    // 文件上传
    uploadZone, fileInput, fileInfo, fileName, fileRows, clearFile,

    // 变量选择
    variableSection, sourceList, factorList, targetList, btnAnalyze,

    // 加载/结果区域
    loadingSection, resultSection, resultTabs, btnExport,

    // 表格容器 (ANOVA)
    threeLineTable, slicedTable, slicedSepTable, mainTable, anovaTable, corrTable,

    // PCA 容器
    pcaLoadingsTable, pcaVarianceTable, pcaWeightsTable, pcaScoresTable,
    pcaScreePlot, pcaBiplot2d, pcaBiplot3d,

    // 聚类容器
    clusterSummary, clusterScatterPlot, clusterDendrogramPlot, clusterDataTable,

    // 控件
    analysisTypeTabs, clusterParamsPanel, dataFilterPanel
};
```

## 功能模块

### 1. 文件上传

```javascript
// 支持的格式
accept=".csv,.xls,.xlsx"

// 上传流程
uploadFile(file)
  -> POST /api/upload
  -> 检查 need_sheet_selection
  -> handleLoadedData() 或 showSheetModal()
```

### 2. 变量选择

**交互方式:**
- 单击: 单选
- Ctrl+点击: 切换选择
- Shift+点击: 范围选择
- 双击: 快速添加为性状
- 拖拽: 拖入因子/性状框

```javascript
// 拖拽功能
initDragAndDrop()
  -> setupDropZone(element, listType, label)
  -> 支持多选拖拽
```

### 3. 分析类型切换

```javascript
// 三种分析模式
'anova'   -> 方差分析 + LSD 多重比较
'pca'     -> 主成分分析
'cluster' -> 聚类分析

// UI 自适应
updateVariableUIForAnalysisType()
  -> 显示/隐藏相关控件
  -> 更新按钮文字
  -> 重置变量选择
```

### 4. 分析执行

```javascript
async function runAnalysis() {
    // 1. 验证输入
    // 2. 显示加载状态
    // 3. 调用对应 API
    //    - ANOVA: /api/analyze
    //    - PCA: /api/analyze_pca
    //    - Cluster: /api/analyze_cluster
    // 4. 渲染结果
    // 5. 切换结果 Tab
}
```

### 5. 结果渲染

```javascript
// ANOVA 结果
renderResults(data)
  -> renderDataTable(slicedSepTable, data.sliced_sep)
  -> renderDataTable(mainTable, data.main)
  -> ...

// PCA 结果
renderPCAResults(data)
  -> renderDataTable() for tables
  -> renderPCAPlot() for charts

// 聚类结果
renderClusterResults(data)
  -> cluster summary HTML
  -> renderClusterPlot()
  -> renderClusterDataTable()
```

### 6. 表格渲染 (性能优化)

```javascript
function renderDataTable(container, data) {
    const MAX_ROWS = 500;  // 性能阈值
    const isTruncated = data.length > MAX_ROWS;
    const displayData = isTruncated ? data.slice(0, MAX_ROWS) : data;

    // 生成 HTML 表格
    // 如果截断，显示提示信息
}
```

### 7. 导出功能

```javascript
// ANOVA 导出
exportANOVAResults()
  -> POST /api/export
  -> 下载 Excel 或保存到本地目录

// PCA 导出
exportPCAResults()
  -> POST /api/export_pca

// 聚类导出
exportClusterData()
  -> POST /api/export_cluster
  -> 下载 CSV
```

## UI 组件

### Tab 切换

```html
<div class="tabs" id="result-tabs">
    <button class="tab-btn active" data-tab="sliced-sep">组内比较</button>
    ...
</div>
<div class="tab-panel active" id="panel-sliced-sep">...</div>
```

```javascript
handleTabClick(clickedBtn, tabContainer)
  -> 更新按钮 active 状态
  -> 显示对应 panel
```

### Toast 提示

```javascript
function showToast(message, type = 'info') {
    // type: 'info' | 'success' | 'warning' | 'error'
    // 3秒后自动消失
}
```

### 密度切换

```javascript
// Carbon Design 规范
data-density="default" | "compact"

// 应用到结果区域
elements.resultSection.setAttribute('data-density', density);
```

## API 调用封装

```javascript
// 通用模式
async function apiCall(url, data) {
    const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    return await response.json();
}
```

## 事件绑定

```javascript
document.addEventListener('DOMContentLoaded', init);

function init() {
    initUpload();           // 文件上传
    initTabs();             // Tab 切换
    initExport();           // 导出按钮
    initModal();            // 模态框
    initMultiSelect();      // 多选功能
    initBrowse();           // 路径浏览
    initAnalysisTypeTabs(); // 分析类型切换
    initClusterControls();  // 聚类控制
    initPcaEllipseControls(); // PCA 椭圆控制
    initDensityToggle();    // 密度切换
    initDragAndDrop();      // 拖拽功能
}
```

## 样式规范

### 颜色变量 (CSS)

```css
:root {
    --primary-color: #2196F3;
    --success-color: #4CAF50;
    --warning-color: #FF9800;
    --error-color: #F44336;
    --text-primary: #1a1a2e;
    --text-secondary: #64748b;
    --border-color: #e2e8f0;
    --bg-primary: #ffffff;
    --bg-secondary: #f8fafc;
}
```

### 响应式布局

```css
/* 三栏布局 */
.main-layout {
    display: grid;
    grid-template-columns: 200px 1fr 1fr;
}

/* 移动端适配 */
@media (max-width: 768px) {
    .main-layout {
        grid-template-columns: 1fr;
    }
}
```

## 外部依赖

```html
<!-- XLSX 库 (Excel 处理) -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js"></script>

<!-- Google Fonts -->
<link href="https://fonts.googleapis.com/css2?family=Fira+Code&family=Fira+Sans&display=swap" rel="stylesheet">
```
