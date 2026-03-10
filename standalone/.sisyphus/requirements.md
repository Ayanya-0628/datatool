# Requirements


2026-03-05 20:19:00 | Codex | standalone-session | 修复 excel_tidy.py 中文乱码与前端汉化
- 修复后端 API 中 23 处乱码/错误中文文案（含上传、切换工作表、整理、导出、LLM 兜底相关错误提示）。
- 将前端 INDEX_HTML 与 JS 用户可见文案汉化（标题、流程、控制面板、状态、按钮、弹窗、toast/status 文案）。
- 要求文件保持 UTF-8，并执行 python -m py_compile e:\AntiAPP\standalone\excel_tidy.py 验证。

2026-03-05 20:34:44 | Codex | standalone-session | 任务规划：settings持久化+可编辑tidy表+运行目录适配
- 输出结构化执行计划：并行子任务、关键边界条件、最小验证清单。
- 范围限定：单文件 excel_tidy.py，新增 /api/settings、/api/update_cell，前端自动加载/保存与双击编辑。

2026-03-05 20:38:19 | Codex | standalone-session | 新增设置持久化、结果表可编辑、PyInstaller 适配
- 新增需求：程序启动读取运行目录 settings.json，提供 /api/settings GET/POST；前端自动加载并支持“保存设置”。
- 新增需求：整理结果表支持双击编辑（contenteditable），编辑后调用 /api/update_cell 持久更新 tidy_df，并提供编辑高亮与保存成功闪烁反馈。
- 新增需求：使用 sys.argv[0] 计算运行目录，禁止 __file__，并在 frozen 模式关闭 use_reloader。
