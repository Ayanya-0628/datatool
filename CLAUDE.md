# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在本仓库中工作时提供指导。
请始终使用简体中文与我对话，并在回答时保持专业、简洁。

## 项目概述

这是一个基于 Flask 的 Web 数据分析应用，专为非编程背景的研究人员设计。提供多因子方差分析、LSD 多重比较、PCA 主成分分析、聚类分析等功能，支持 Excel 导出。

**技术栈**: Python 3.10, Flask, Pandas, NumPy, SciPy, statsmodels, scikit-learn, matplotlib

## 常用命令

```bash
# 安装依赖
pip install -r requirements.txt

# 启动开发服务器 (默认端口 7860)
python app.py

# 指定端口启动本地开发
python -c "from app import app; app.run(host='0.0.0.0', port=5000)"

# 生产环境部署 (gunicorn)
gunicorn -b 0.0.0.0:7860 app:app

# Docker 构建与运行
docker build -t data-analysis-tool .
docker run -p 7860:7860 data-analysis-tool
```

## 架构说明

### 核心应用结构

- **`app.py`** - 主 Flask 应用，包含所有 API 端点和核心统计逻辑
- **`wsgi.py`** - 生产环境 WSGI 入口文件 (Gunicorn/uWSGI)
- **`pca_analysis.py`** - PCA 分析模块，包含 `PCAAnalyzer` 类，用于主成分分析、可视化（碎石图、双标图）和权重计算
- **`clustering.py`** - 聚类分析模块，包含 `ClusterAnalyzer` 类，支持 K-Means 和层次聚类及树状图

### 前端

- **`templates/dashboard.html`** - 主仪表盘模板
- **`static/app.js`** - 前端 JavaScript
- **`static/style.css`** - 样式文件

### 关键设计模式

1. **数据存储模式**: 上传的数据以 UUID 为键存储在内存中 (`data_store` 字典)，通过后台清理线程在 1 小时后自动过期

2. **行顺序保持**: 所有 `groupby()` 操作使用 `sort=False` 保持原始文件顺序。因子列转换为 `pd.Categorical`，按首次出现顺序排序

3. **列顺序规范**: 结果表格遵循严格排序 - 因子列在前，指标列在后 (Mean | Letter | SD 模式)

4. **可选模块加载**: sklearn、matplotlib 和 tkinter 使用 `HAS_*` 标志条件导入，实现优雅降级

### API 端点

| 端点 | 用途 |
|------|------|
| `/api/upload` | 文件上传 (CSV/Excel)，返回列类型和建议 |
| `/api/load_sheet` | 加载指定 Excel 工作表 (多表文件) |
| `/api/analyze` | 执行方差分析和 LSD 多重比较 |
| `/api/analyze_pca` | 主成分分析 |
| `/api/analyze_cluster` | K-Means 或层次聚类分析 |
| `/api/export` | 导出结果到 Excel |

### 统计方法

- **方差分析 (ANOVA)**: 使用 `statsmodels.formula.api.ols`，采用 Type II 平方和
- **LSD 检验**: 自定义实现于 `pairwise_lsd_test_with_mse()` 函数
- **CLD (紧凑字母显示)**: 使用 Bron-Kerbosch 算法实现于 `solve_clique_cld()` 函数，用于显著性分组
- **PCA**: 使用 sklearn 的 PCA 配合 StandardScaler 标准化，支持置信椭圆可视化

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `SECRET_KEY` | Flask 密钥 | `dev-key-change-in-production` |
| `PORT` | 服务端口 | `7860` |

## 部署说明

- 已适配 ModelScope Docker 创空间 (要求端口 7860)
- 也可部署到 Render、Railway 或 PythonAnywhere
- 最大上传文件: 50MB
- 上传文件 1 小时后自动删除

## 开发调试规范 (Critical)

### 1. 服务重启协议
在修改后端代码 (`app.py`, `pca_analysis.py` 等) 并需要重启服务时，**必须**严格遵循以下步骤：

1.  **清理旧进程**: 必须先强制杀死后台残留进程，防止端口占用和僵尸服务。
    ```bash
    taskkill /F /IM python.exe
    ```
    *(注: 如无法清理，可使用 `wmic process where "name='python.exe'" delete`)*

2.  **启动新服务**: 使用固定端口启动，避免端口漂移导致用户困惑。
    ```bash
    python -c "from app import app; app.run(host='0.0.0.0', port=7860)"
    ```

3.  **状态重置提醒**: 服务重启会导致内存中的数据 (`data_store`) 丢失。**必须**明确告知用户："服务已重启，内存数据已清空，请重新上传文件"。

### 2. 端口管理
- **默认端口**: `7860`
- **备用端口**: 仅在 7860 确实无法释放时才使用 7861+，并告知用户新地址。

## 版本记录规范

### 1. 存档操作
**触发指令**: 当提及 "存档" 或 "提交" 时

- **检查改动**: 运行 `git diff` 检查本次改动内容
- **提交代码**: 执行 `git add .` 和 `git commit`（根据改动内容自动生成 commit message）
- **更新日志**: 在 `CHANGELOG.md` 文件顶部添加记录，格式如下：

```markdown
## YYYY-MM-DD HH:mm
- 改动内容描述...
```

### 2. 回退操作
**触发指令**: 当提及 "回退" 或 "撤销" 时

- **确认目标**: 先提示将回退到哪个版本（显示上一次的提交信息）
- **等待确认**: 等待用户确认后，再执行回退操作
- **记录回退**: 回退完成后，在 `CHANGELOG.md` 文件顶部添加记录，格式如下：

```markdown
## YYYY-MM-DD HH:mm
回退: 撤销了 xxx 改动
```

### 3. 查看历史
**触发指令**: 当提及 "历史" 或 "记录" 时

- **显示记录**: 显示最近 5 次提交的简要信息

## 语言
- 默认使用中文回复与沟通。
- 仅当我明确要求时，切换为英文或其他语言。

## 团队协作触发词
- 当我说“初始化团队”时，启用五角色：
  1) Planner：拆解任务和里程碑
  2) Builder：实现代码
  3) Reviewer：审查改动和风险
  4) Tester：执行验证与回归
  5) Recorder：记录结果与结论

## 固定输出顺序
- 计划 -> 实施 -> 验证 -> 风险 -> 结论
