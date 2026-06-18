# Progress

## Current State

- 项目类型：SlyLab Python Web 版，Flask + Pandas/Statsmodels/Scipy/Scikit-learn + Matplotlib。
- 主入口：`app.py`
- WSGI 入口：`wsgi.py`
- 服务器依赖：`requirements-server.txt`
- 部署建议：服务器使用 `gunicorn app:app`，并设置 `MPLBACKEND=Agg`、`SECRET_KEY`。
- 历史记录：旧进度仍保留在 `.sisyphus/progress.md`，新记录写入本文件。

## 2026-05-20

- 在 `E:\SlyLab` 找到原版 SlyLab 源码，确认其与旧 Obsidian 部署记录一致。
- 已补装本地测试依赖：`pytest`。
- 已修复聚类分析接口未返回 `circular_heatmap_plot` 的问题，并在前端热图面板渲染环形聚类热图。
- 已保护 `/api/shutdown`：默认返回 403，只有 `ALLOW_SHUTDOWN=1` 时才允许关闭服务。
- 已通过验证：
  - `python -m py_compile app.py auth.py clustering.py modules\heatmap.py modules\barchart.py modules\jointplot.py`
  - `python -m pytest -q`：6 passed
  - Flask test client：`GET /` 返回 200；`POST /api/shutdown` 默认返回 403
- 已部署到腾讯云：
  - 代码目录：`/opt/slylab`
  - systemd 服务：`slylab.service`
  - Gunicorn 本机端口：`127.0.0.1:7861`
  - 公网入口：`http://122.51.86.28/slylab-app/`
  - Caddy 已加 Basic Auth；凭据保存在服务器 `/root/.slylab_credentials`
  - 备份目录：`/root/backups/slylab-src/`
- 服务器验证：
  - `systemctl is-active slylab`：active
  - `http://127.0.0.1:7861/`：200
  - `http://127.0.0.1/slylab-app/` 带认证：200
  - `http://127.0.0.1/slylab-app/` 未认证：401
  - 外网 `http://122.51.86.28/slylab-app/` 带认证：200，未认证：401
- 已加入 Nature 风格 Python 绘图能力：
  - 后端模块：`modules/nature_plot.py`
  - API 入口：`POST /api/nature_plot`
  - 支持图型：`grouped_bar`、`trend`、`heatmap`、`forest`
  - 支持导出：`png`、`svg`、`pdf`、`tiff`、`jpeg`；SVG 保留可编辑文字
  - 前端入口：左侧方法列表新增 `Nature 论文图`，可在界面选择图型、变量、格式、配色并预览/下载
  - 已修复 Nature 面板列选择为空的问题：新增 `POST /api/data_columns`，前端在 `state.columns` 为空时按 `data_id` 自动恢复列名和列类型
  - 已将 `static/app.js` 引用版本从 `v=44` 提升到 `v=45`，避免浏览器继续使用旧 Nature 前端缓存
  - 已对首页和 `app.js` 添加 no-cache 响应头，降低前端部署后旧脚本缓存风险
  - 本地验证：`python -m pytest -q`：10 passed
  - 已部署到 `/opt/slylab` 并重启 `slylab.service`
  - 服务器验证：`/api/nature_plot` 返回 `200 True png`；远端模板与 JS 已包含 Nature 前端入口

## 2026-06-18

- 服务器运维：SlyLab 公网入口 Basic Auth 账号由 `slylab` 改为 `yan`（明文凭据见服务器 `/root/.slylab_credentials`；公网入口 `http://122.51.86.28/slylab-app/`）。弱密码，建议后续加强。
- 修复服务器中文绘图豆腐块：
  - 根因：OpenCloudOS 9.4 未装任何中文字体（`fc-list :lang=zh` = 0），matplotlib 回退无中文字形的 DejaVu Sans。
  - 处置：`dnf install google-noto-sans-cjk-sc-fonts google-noto-serif-cjk-sc-fonts`；清 matplotlib 字体缓存（`/root` 与 `/var/lib/slylab` 两处）并重启 `slylab`。
  - 代码：`modules/heatmap.py`、`modules/nature_plot.py` 字体名单补入 Noto CJK；`nature_plot` 增加 `axes.unicode_minus=False`。
  - 验证：服务端渲染中文，实际选用 `NotoSansCJKsc`，缺字形警告 0。
- 接入 NVIDIA integrate LLM（AI 万能整理兜底引擎）：
  - 模型 `deepseek-ai/deepseek-v4-flash`，base `https://integrate.api.nvidia.com/v1`。
  - `app.py` `/api/llm_tidy` 的 api_key/api_base/model 支持回退环境变量 `LLM_API_KEY`/`LLM_API_BASE`/`LLM_MODEL`。
  - 服务器 `/etc/slylab.env` 写入上述三项（权限 600）；生产 venv 补装 `requests`（此前缺失，LLM 兜底实际不可用，已记入 requirements）。
  - 验证：`HAS_REQUESTS` True，`call_llm` 实测返回成功。
- 备份：`/root/backups/slylab-fonts-20260618/`（含改动前 heatmap.py、nature_plot.py、app.py、slylab.env）。

## Deployment Notes

- 不要提交或上传 `.venv/`、`.git/`、`__pycache__/`、`.pytest_cache/`、历史打包产物和本地日志。
- 生产环境不要使用默认 `SECRET_KEY`。
- 若公网开放，优先使用 Caddy Basic Auth 或应用认证，避免数据分析上传入口裸露。
