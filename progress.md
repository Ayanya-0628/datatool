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
- 备份：`/root/backups/slylab-fonts-20260618/`（含改动前 heatmap.py、nature_plot.py、app.py、slylab.env、dashboard.html）。
- Git 凭据泄露处置：发现 `templates/dashboard.html` 硬编码 SiliconFlow key（`sk-vqvj…`，由历史提交 `f536fd5` 引入）；GitHub API 核实 `datatool` 仓库实为 **public**（private=false），key 已公开泄露。处置：`filter-branch` 改写 `f536fd5..HEAD` 抹除 key（input value 清空）→ `--force-with-lease` push 覆盖远程 main（`889bc4f` → `b42e90f`）→ 清本地 `refs/original`/备份分支 + `gc` → 服务器 `/opt/slylab` 同步干净 dashboard.html 并重启。本地 `.git` 全量备份在 `E:\SlyLab_git_backup_20260618`。已提示用户去 SiliconFlow 吊销 key（用户表示无所谓）。
- 网络/远程修复：本机 SSH 走 fake-ip（198.18.x）22 端口不通；git 全局 `http(s).proxy` 由 `7890` 改为实际监听端口 `7897`；`origin` 由 SSH 改为 HTTPS（`https://github.com/Ayanya-0628/datatool.git`），走 7897 代理可正常 push/fetch。
- 域名根路径绑定：`rice2026.online` / `www.rice2026.online` 根路径由 "Coming Soon" 占位改为直接反代 SlyLab 应用（Caddy `handle{}` + Basic Auth `yan` → `127.0.0.1:7861`）；保留 `/slylab/` 静态图表工具（无认证）；旧 `/slylab-app/*` 改为 301 跳转到根，兼容老链接。Caddyfile 备份 `/root/backups/slylab-fonts-20260618/Caddyfile.bak.root-bind`。验证：根路径 401/200、首页 title「数据分析工具 Pro」、`/static` 与 `/api` 均通、`/slylab/` 仍可用。三域名 Let's Encrypt 证书有效（到 2026-06-28，Caddy 自动续）。
- 入口改公开：按用户要求去掉**全部** Caddy Basic Auth（`rice2026.online` 根路径、`:80` IP 直连 `/slylab-app/`、`:7860` 端口三处），Caddyfile 全文 `basicauth` 残留 0，打开即用、无登录（应用内置登录 `ENABLE_AUTH` 仍为 0 未启用）。备份 `Caddyfile.bak.no-auth` / `Caddyfile.bak.no-auth-all`，验证三入口均无认证 200。**注意：数据分析/上传口现对公网完全开放，无任何访问控制。**
- 导出落对象存储：按用户要求把导出结果存到腾讯云 COS（cosfs 挂载于 `/mnt/cos`，可写）。`app.py` 的 `EXPORT_DIR` 改为支持环境变量 `SLYLAB_EXPORT_DIR`（默认仍为本地 `APP_DATA_DIR/exports`，本地开发不受影响）；服务器 `/etc/slylab.env` 设 `SLYLAB_EXPORT_DIR=/mnt/cos/slylab/exports`，web 导出 Excel 即写入桶留档（文件名带 uuid、`send_file` 后不删除，会自然累积）。验证：cosfs 写 xlsx 4867B 读回正常、应用 `EXPORT_DIR` 实际指向 `/mnt/cos/slylab/exports`。备份 `app.py.bak.cos` / `slylab.env.bak.cos`。仅落盘的导出文件走桶；内存型数据（上传/分析中间态）仍是 1 小时过期、不入桶。
- 首屏方法画廊（参考 OmicStudio）：按用户要求把"先上传才显示方法"改为"先选方法再上传"。`dashboard.html` 新增 `#method-gallery` 全屏首屏（7 张方法卡片：方差分析/PCA/聚类/热力图/分组柱状图/Nature论文图/数据整形，Material Symbols 图标，三色分类——统计蓝/可视化绿/数据处理琥珀）；侧栏配置面板顶部加「← 返回方法」。`app.js` 新增 `initMethodGallery/enterWorkspace/backToGallery`（点卡片→隐藏画廊+选中对应方法；返回按钮回画廊重选）。**侧栏不再显示方法列表**（用户反馈：方法切换按钮过多、挤占参数设置区），方法切换统一走「返回方法」画廊——`enterWorkspace`/`loadDataSuccess`/`clearData` 三处均保持 `method-section` 隐藏。缓存版本 app.js v45→v47。本地验证：DOM 7 卡片、交互逻辑全过（进工作区 method-section 隐藏、上传面板可见、返回重现、方法正确选中）、Chrome 截图视觉正常；已部署服务器重启，线上画廊卡片数 7、app.js v47。备份 `dashboard.html.bak.gallery(2)` / `app.js.bak.gallery(2)`。后续修留白：去掉 `#variable-section` 的 `mt-auto`（原把参数区顶到侧栏最底、中段空一大片），改为紧跟数据源上传框，备份 `dashboard.html.bak.layout`。另确认分组柱状图默认自动算显著性（`bc-show-letters` 复选框默认 checked → barchart.py `_auto_compute_letters` 做 LSD）。
- 变量参数内联：anova/cluster/pca 的变量选择从"配置变量"弹窗改为**侧栏内联 checkbox 直接勾选**（anova=因子/性状、cluster=标签/特征、pca=分组/分析变量），`app.js` 新增 `renderInlineVars()`（挂在 `updateUIForMethod` 末尾 + 弹窗 `confirmVariableChanges` 后同步），穿梭框弹窗保留作高级入口。缓存 app.js v47→v48。本地 Chrome 验证：anova 2 组 8 候选、pca 分组2/变量3、勾选联动 `summary` 正确。备份 `dashboard.html.bak.inline` / `app.js.bak.inline`。
- 变量配置移主界面（用户反馈：性状多时侧栏挤）：把 anova/cluster/pca 的变量选择从侧栏移到**主界面顶部横向配置区** `#main-var-config`（因子/性状各一卡片、checkbox `grid-cols-2/3` 多列铺开、每组带"全选/清空"、面板自带"分析数据"按钮 `btn-analyze-main`→`runAnalysis`），侧栏重复的 `action-section` 对这三个方法隐藏；`renderInlineVars` 改渲染到 main。缓存 app.js v48→v49。本地 Chrome 验证：8 数值列横向铺开、全选→`summary` 8、侧栏按钮隐藏、主分析按钮就位。备份 `dashboard.html.bak.mainvar` / `app.js.bak.mainvar`。
- **修多 worker 数据丢失 bug**（用户上传多 sheet xlsx 报"加载成功但 undefined 行/无法读取"）：根因 gunicorn `--workers 2` 双进程，内存 `data_store`/`temp_file_store`/`raw_file_store` 等是模块级 dict、**不跨进程共享**——`upload`（存 temp 到 worker A）与 `load_sheet`（请求落 worker B）落不同进程时数据丢失，后端返回"文件已过期"，而前端 `showSheetModal` 选表后**未检查 `data.error`**、直接当成功加载 → `data.rows` undefined。双修复：① service `ExecStart` `--workers 2`→`--workers 1`（内存存储应用必须单 worker，否则 upload→analyze→export 全链路都可能跨 worker 丢数据），daemon-reload 重启；② 前端选表后补 `!res.ok || data.error` 检查并 toast 报错。app.js v49→v50，备份 `slylab.service.bak`。端到端验证：连续 3 次 upload→load_sheet 均 `rows=4 cols=3 error=None`。

## Deployment Notes

- 不要提交或上传 `.venv/`、`.git/`、`__pycache__/`、`.pytest_cache/`、历史打包产物和本地日志。
- 生产环境不要使用默认 `SECRET_KEY`。
- 若公网开放，优先使用 Caddy Basic Auth 或应用认证，避免数据分析上传入口裸露。
