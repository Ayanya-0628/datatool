# 📊 SlyLab (SlyLab)

## 项目概述

基于 Flask 的 Web 数据分析应用，专为非编程背景的研究人员设计。提供从数据上传、智能整理、统计分析到结果导出的完整工作流。核心功能覆盖多因子方差分析（ANOVA）、LSD 多重比较（CLD 紧凑字母显示）、PCA 主成分分析、聚类分析（K-Means/层次聚类）、相关性热力图等，支持 Excel 导出和高清图表下载。

**目标用户**: 农学、生物学等领域的非编程背景研究人员
**部署方式**: ModelScope Docker 创空间 (端口 7860)，兼容 Render/Railway/PythonAnywhere

## 技术栈

| 层级 | 技术 |
|------|------|
| **后端框架** | Flask 2.3+, Gunicorn (生产) |
| **数据处理** | Pandas 2.0+, NumPy 1.24+ |
| **统计分析** | Statsmodels 0.14+ (Type II ANOVA), SciPy 1.10+ |
| **机器学习** | scikit-learn 1.0+ (PCA, K-Means, 层次聚类) |
| **可视化** | Matplotlib 3.7+ (碎石图, 双标图, 树状图, 热力图) |
| **Excel 处理** | Openpyxl 3.1+ |
| **前端** | HTML5, Vanilla JS, CSS (Tailwind 风格看板) |
| **桌面端** | PyQt6 + WebEngine (可选), PyInstaller 打包 |
| **认证** | Flask-Login + SQLite (可选, ENABLE_AUTH=1) |
| **LLM 集成** | SiliconFlow API + DeepSeek-V3 (AI 数据整理回退) |

## 项目结构

```
e:\SlyLab\
│
├── app.py                    # 主 Flask 应用 (87KB, 2296行)
│                               所有 API 端点 + 核心统计逻辑 (ANOVA/LSD/CLD)
├── pca_analysis.py           # PCA 分析模块 — PCAAnalyzer 类
│                               碎石图、2D/3D 双标图、置信椭圆、PERMANOVA、权重计算
├── clustering.py             # 聚类分析模块 — ClusterAnalyzer 类
│                               K-Means、层次聚类、肘部法则、树状图、相关性热图
├── smart_tidy.py             # 智能数据整理 — 合并单元格驱动子表检测
│                               多子表交错布局解析、宽表融合
├── llm_tidy.py               # LLM 辅助整理 — DeepSeek API 调用 + 自动重试
├── build_html.py             # 静态 HTML 构建工具
├── auth.py                   # 可选认证模块 (注册/登录/登出)
├── wsgi.py                   # 生产环境 WSGI 入口 (Gunicorn)
├── launcher.py               # 桌面启动器 (系统浏览器模式)
│
├── templates/                # Jinja2 HTML 模板
│   ├── dashboard.html          # 主仪表盘 (核心 UI)
│   ├── index.html              # 首页/欢迎页
│   ├── login.html              # 登录页
│   └── register.html           # 注册页
│
├── static/                   # 前端静态资源
│   ├── app.js                  # 前端逻辑 (77KB)
│   └── style.css               # 样式表 (21KB)
│
├── modules/                  # 功能子模块
│   └── heatmap.py              # 相关性气泡热力图 (Pearson + 显著性)
│
├── scripts/                  # 工具脚本 (批量分析/热力图绘制)
├── standalone/               # 独立工具
│   └── excel_tidy.py           # 单文件版 Excel 智能整理 (内联 smart_tidy + llm_tidy)
│
├── tests/                    # 测试
│   ├── fixtures/               # 测试数据
│   ├── test_heatmap_module.py
│   └── test_smart_tidy_interleaved.py
│
├── docs/                     # 文档
│   ├── CODEMAPS/               # 代码地图 (后端/前端/分析/桌面端)
│   ├── plans/                  # 开发计划
│   ├── DEPLOY.md               # 部署文档
│   └── 迁移使用说明.md
│
├── .sisyphus/                # 跨 Agent 进度共享
│   ├── progress.md             # 任务完成记录
│   └── requirements.md         # 任务需求记录
│
├── Dockerfile                # Docker 部署配置
├── Procfile                  # Gunicorn 启动配置
├── render.yaml               # Render 部署配置
├── requirements.txt          # Python 依赖
├── CHANGELOG.md              # 变更日志
├── CLAUDE.md                 # Claude Code 指导文档
└── AGENTS.md                 # Agent 行为规范
```

## 核心模块

### 1. 主应用 (`app.py`)

Flask 主应用，包含全部 API 端点和核心统计逻辑。

**数据存储**: UUID 键值内存存储 (`data_store`)，1 小时自动过期，后台清理线程
**统计方法**:
- ANOVA: `statsmodels.formula.api.ols` + Type II 平方和
- LSD 检验: 自定义 `pairwise_lsd_test_with_mse()` 函数
- CLD (紧凑字母显示): Bron-Kerbosch 算法 → `solve_clique_cld()`
- 列顺序规范: [因子列] → [指标|Mean, 指标|Letter, 指标|SD]

**API 端点一览**:

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/upload` | POST | 文件上传 (CSV/Excel)，返回列类型建议 |
| `/api/load_sheet` | POST | 加载指定 Excel 工作表 |
| `/api/analyze` | POST | 方差分析 + LSD 多重比较 |
| `/api/analyze_pca` | POST | PCA 主成分分析 |
| `/api/pca_plot` | POST | PCA 图表生成 (碎石图/双标图) |
| `/api/export_pca` | POST | 导出 PCA 结果到 Excel |
| `/api/analyze_cluster` | POST | 聚类分析 (K-Means/层次) |
| `/api/cluster_elbow` | POST | 肘部法则图 |
| `/api/export_cluster` | POST | 导出聚类结果 |
| `/api/analyze_heatmap` | POST | 相关性热图生成 |
| `/api/export_heatmap_image` | POST | 导出热图图片 |
| `/api/reshape_preview` | POST | 数据整形预览 |
| `/api/reshape` | POST | 执行数据整形 |
| `/api/export_reshape` | POST | 导出整形结果 |
| `/api/smart_tidy_scan` | POST | 智能整理 - 扫描结构 |
| `/api/smart_tidy_execute` | POST | 智能整理 - 执行转换 |
| `/api/llm_tidy` | POST | 双引擎整理 (SmartTidy + LLM 回退) |
| `/api/update_cell` | POST | 单元格编辑 |
| `/api/export` | POST | 导出分析结果到 Excel |
| `/api/shutdown` | POST | 关闭服务 (桌面端) |

### 2. PCA 分析模块 (`pca_analysis.py`)

`PCAAnalyzer` 类封装完整的主成分分析流程：
- 数据预处理: StandardScaler 标准化 + 指标正向化 (极大/极小/区间型)
- 分析输出: 载荷表、方差贡献表、权重计算、综合得分排名
- 可视化: 碎石图、2D/3D 双标图 (支持分组着色 + 置信椭圆)
- 统计检验: 简化版 PERMANOVA (基于欧氏距离，999 次置换)

### 3. 聚类分析模块 (`clustering.py`)

`ClusterAnalyzer` 类支持两种聚类方法：
- K-Means: 自动肘部法则最优 k 选择
- 层次聚类: ward/complete/average/single 连接方法
- 可视化: 肘部法则图、树状图、PCA 投影散点图、聚类热图、相关性热图

### 4. 智能数据整理 (`smart_tidy.py`)

基于合并单元格驱动的复杂 Excel 解析器：
- 自动检测多子表交错布局 (水平 + 垂直)
- 处理合并单元格、多行表头
- 按 [处理, 重复] 外连接融合多子表为宽表
- 过滤平均行/列

### 5. LLM 数据整理 (`llm_tidy.py`)

当 SmartTidy 解析失败时的自动回退方案：
- 调用 SiliconFlow API (DeepSeek-V3 模型)
- 将 Excel 原始结构描述发送给 LLM 生成转换代码
- 自动重试机制 (最多 3 次)

### 6. 相关性热图 (`modules/heatmap.py`)

Pearson 相关气泡热力图：
- 气泡大小映射 |r| 值，颜色映射 r 值方向
- 显著性标记 (*/**/***) 叠加
- 支持中文变量名

## 开发约定

### 关键设计模式

1. **行顺序保持**: 所有 `groupby()` 使用 `sort=False`，因子列转为 `pd.Categorical` 按首次出现顺序
2. **列顺序规范**: 因子列在前 → 指标列在后 (Mean | Letter | SD)
3. **骨架合并策略**: 提取原始唯一因子组合 → left merge 计算结果，保证输入顺序
4. **可选模块加载**: sklearn/matplotlib/tkinter 使用 `HAS_*` 标志条件导入
5. **双引擎整理**: SmartTidy 优先 + LLM 自动回退

### 代码风格

- `df`: 通用 DataFrame
- `sub_df`: 数据子集
- `factors`: 分组键列名列表
- `targets`: 依赖变量列名列表
- 禁止 `set()` 取唯一值 (破坏顺序)，使用 `pd.unique()` 或 `list(dict.fromkeys())`

### 服务重启协议

```bash
# 1. 清理旧进程
taskkill /F /IM python.exe

# 2. 启动新服务
python -c "from app import app; app.run(host='0.0.0.0', port=7860)"

# 3. 提醒：服务重启后 data_store 清空，需重新上传文件
```

### 版本管理触发词

- **"存档"**: git add → git commit → 更新 CHANGELOG.md
- **"回退"**: 确认目标版本 → 执行后记录到 CHANGELOG.md
- **"历史"**: 显示最近 5 次提交信息

## 当前进度

### ✅ 已完成
- 多因子方差分析 (ANOVA) + LSD 多重比较 + CLD 紧凑字母显示
- PCA 主成分分析 (碎石图/2D·3D 双标图/置信椭圆/PERMANOVA/综合得分)
- 聚类分析 (K-Means/层次聚类/肘部法则/树状图/聚类热图)
- 相关性气泡热力图 (Pearson + 显著性标记)
- 数据整形 (宽↔长转换 + 单元格编辑)
- 智能数据整理 (SmartTidy 合并单元格解析 + LLM 回退)
- 独立版 Excel 整理工具 (`standalone/excel_tidy.py`)
- 变量拖拽选择 + 正向化配置
- Excel 导出 + 高清图表下载 (600 DPI)
- Docker 部署 (ModelScope 创空间)
- Windows 安装包 (PyInstaller + Inno Setup)
- 可选认证体系 (注册/登录)
- Tailwind 风格现代看板 UI

### 🔄 进行中
- 前端 UI 持续优化 (数据整形界面对齐独立工具风格)

### 📌 待办
- README.md 完善 (安装步骤、功能截图、使用说明)
- API 文档独立化 (含请求/响应示例)
- 架构可视化图
- CHANGELOG.md 编码修复 (2026-01 月之前的记录存在乱码)

## 已知问题

1. **CHANGELOG 乱码**: `CHANGELOG.md` 中 2026-02-01 之前的记录出现 GBK 乱码 (可能是编辑器编码切换导致)
2. **`.xls` 兼容性**: 旧版 `.xls` 文件在未安装 `xlrd` 时无法读取（SmartTidy 已提供明确提示）
3. **内存存储**: `data_store` 为内存字典，服务重启后数据丢失（设计如此，非 bug）
4. **大文件残留**: `archives/`(460MB)、`Output/`(129MB)、`dist/`(102MB) 含大体积构建产物

