# Data Analysis Tool 2.0 - 代码地图索引

**最后更新:** 2026-01-25
**版本:** 2.0 (Windows 桌面版 + Web 版)

## 项目概述

Data Analysis Tool 是一个基于 Flask 的统计分析 Web 应用，专为非编程背景的研究人员设计。支持多因子方差分析、LSD 多重比较、PCA 主成分分析、聚类分析等功能，并可打包为 Windows 桌面应用。

## 架构图

```
+------------------+     +------------------+     +------------------+
|    Frontend      |     |    Backend       |     |   Analysis       |
|  (HTML/JS/CSS)   | <-> |    (Flask)       | <-> |   Modules        |
+------------------+     +------------------+     +------------------+
        |                        |                        |
        v                        v                        v
+------------------+     +------------------+     +------------------+
| dashboard.html   |     |     app.py       |     | pca_analysis.py  |
| app.js           |     |   (API Routes)   |     | clustering.py    |
| style.css        |     |                  |     |                  |
+------------------+     +------------------+     +------------------+
                                 |
                                 v
                         +------------------+
                         |   launcher.py    |
                         | (PyQt6 Desktop)  |
                         +------------------+
```

## 核心模块索引

| 模块 | 文件 | 用途 | 详细文档 |
|------|------|------|----------|
| 后端核心 | `app.py` | Flask 应用、API 路由、统计逻辑 | [backend.md](backend.md) |
| PCA 分析 | `pca_analysis.py` | 主成分分析、可视化 | [analysis.md](analysis.md) |
| 聚类分析 | `clustering.py` | K-Means/层次聚类 | [analysis.md](analysis.md) |
| 桌面启动器 | `launcher.py` | PyQt6 桌面应用封装 | [desktop.md](desktop.md) |
| 前端界面 | `templates/`, `static/` | Web UI | [frontend.md](frontend.md) |

## 技术栈

### 后端
- **Python 3.10+**
- **Flask >= 2.3.0** - Web 框架
- **Pandas >= 2.0.0** - 数据处理
- **NumPy >= 1.24.0** - 数值计算
- **SciPy >= 1.10.0** - 科学计算
- **statsmodels >= 0.14.0** - 统计模型
- **scikit-learn >= 1.0.0** - 机器学习 (PCA/聚类)
- **matplotlib >= 3.7.0** - 图表生成

### 前端
- **HTML5 + CSS3 + Vanilla JS**
- **Carbon Design System** 风格 UI

### 桌面版
- **PyQt6** - Qt WebEngine 封装
- **PyInstaller** - 打包工具
- **Inno Setup** - Windows 安装程序

## 数据流

```
用户上传文件 (CSV/Excel)
       |
       v
/api/upload --> data_store[uuid] --> 内存存储
       |
       v
/api/analyze (ANOVA) 或 /api/analyze_pca 或 /api/analyze_cluster
       |
       v
统计计算 (statsmodels/sklearn)
       |
       v
JSON 响应 --> 前端渲染表格/图表
       |
       v
/api/export --> Excel 文件下载
```

## 目录结构

```
SlyLab/
├── app.py                 # Flask 主应用 (1558 行)
├── pca_analysis.py        # PCA 分析模块 (651 行)
├── clustering.py          # 聚类分析模块 (444 行)
├── launcher.py            # PyQt6 桌面启动器 (175 行)
├── wsgi.py                # WSGI 入口
├── requirements.txt       # Python 依赖
├── templates/
│   ├── dashboard.html     # 主界面模板
│   └── index.html         # 备用入口
├── static/
│   ├── app.js             # 前端逻辑 (2292 行)
│   └── style.css          # 样式文件
├── dist/                  # PyInstaller 输出
├── Output/                # Inno Setup 安装包输出
├── docs/
│   └── CODEMAPS/          # 代码地图文档
├── CLAUDE.md              # 项目指南
├── CHANGELOG.md           # 版本记录
└── README.md              # 项目说明
```

## 快速导航

- [后端架构](backend.md) - Flask 路由、统计算法、数据存储
- [分析模块](analysis.md) - PCA、聚类分析实现细节
- [前端架构](frontend.md) - UI 组件、状态管理、API 调用
- [桌面版](desktop.md) - PyQt6 封装、打包配置

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `SECRET_KEY` | Flask 密钥 | `dev-key-change-in-production` |
| `PORT` | 服务端口 | `7860` |

## 部署方式

1. **本地开发**: `python app.py`
2. **生产部署**: `gunicorn -b 0.0.0.0:7860 app:app`
3. **Docker**: `docker build -t data-analysis-tool . && docker run -p 7860:7860 data-analysis-tool`
4. **Windows 桌面版**: 运行 `Output/` 目录下的安装程序

