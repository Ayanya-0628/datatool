# 更新日志

## 2026-01-30 15:30
- **重构**: 将应用启动方式从 PyQt 内置浏览器改为系统默认浏览器
  - 解决内置 WebEngine 渲染卡顿和掉帧问题
  - 启动器改为轻量级控制面板模式
- **修复**: 解决 PyInstaller 打包缺失依赖问题
  - 修复 `PyQt6` 缺失导致启动器无法运行
  - 修复 `scikit-learn` 和 `matplotlib` 缺失导致 PCA 分析和图表生成失败
  - 更新 `browser_app.spec` 显式收集复杂库的所有资源文件
- **优化**: 修复前端变量选择弹窗无法滚动的问题
  - 更新 `style.css` 优化 `transfer-target-box` 布局

## 2026-01-30 14:15
- **新增**: PCA 主成分分析支持变量正向化配置
  - 前端增加变量配置弹窗 (`Config Modal`)，支持极大型、极小型、区间型设置
  - 变量列表中增加齿轮图标 (⚙️) 用于快速打开配置
  - 后端适配 `target_configs` 参数，在 PCA 分析前自动进行数据标准化预处理

## 2026-01-28 12:55
- **新增**: PCA 主成分分析显著性检验 (PERMANOVA)
  - 实现基于距离矩阵的置换多元方差分析 (Permutational MANOVA)
  - 在双标图中自动标注 $R^2$ 和 $P$ 值
  - 支持智能识别分组变量 (单列自动推断)
- **优化**: 图表导出功能增强
  - 所有分析图表 (PCA/聚类) 增加 "下载高清大图 (600 DPI)" 按钮
  - 优化 3D 双标图的轴线显示和空间感
  - 修复 PERMANOVA 统计文本在 2D 图中的遮挡问题 (z-order 置顶)
- **功能**: 添加网页关闭自动停止服务机制 (`/api/shutdown`)

## 2026-01-27 10:45
- **修复**: 聚类相关性热图可视化问题
  - 修正左侧树状图生长方向 (指向热图)
  - 修复相关系数数值被背景遮挡的问题 (调整 z-order)
- **功能**: PCA 和聚类分析支持指标正向化配置 (target_configs)

## 2026-01-25 00:15
- **发布**: 完成 Windows 安装包制作 ("数据分析2.0")
  - **打包方案**: 使用 PyInstaller 冻结 Python 环境 + Inno Setup 制作安装程序
  - **核心修复**: 修改 `app.py` 中的 `get_app_data_dir()`，将日志和导出文件重定向至 `%LOCALAPPDATA%`，解决安装在 `Program Files` 后的权限报错 (500 Error)
  - **性能优化**: `launcher.py` 启用 ANGLE (DirectX 11) 后端和 DPI 适配，解决 WebEngine 滚动卡顿问题
  - **配置更新**: `setup.iss` 更新应用名称为 "数据分析2.0"，版本号 2.0
  - **清理**: 移除开发过程中的临时测试脚本和构建缓存

## 2026-01-24 23:30
- **修复**: 解决 `/api/analyze` 返回 500 Internal Server Error 的问题
  - **根本原因**: Flask Debug 模式的 Reloader 机制会启动两个进程（主进程+工作进程），当旧进程未正确清理时，多个进程同时监听同一端口，导致请求被分配到没有最新 `data_store` 数据的旧进程
  - **症状**: 浏览器收到 `Unexpected token '<'` 错误（服务器返回 HTML 错误页面而非 JSON）
  - **解决方案**:
    1. 终止所有占用端口的冲突进程
    2. 添加全局错误处理器 `@app.errorhandler(Exception)` 确保所有异常返回 JSON 格式
    3. 添加 `@app.errorhandler(500)` 专门处理 500 错误
    4. 错误日志写入 `error.log` 文件便于排查
- **经验总结**:
  - Flask `debug=True` 时会创建 reloader 子进程，内存中的 `data_store` 不共享
  - 多次启动服务器前应先检查端口占用：`netstat -ano | findstr ":7860"`
  - 强制终止进程：`taskkill /F /PID <pid>`

## 2026-01-24 15:30
- 新增变量拖拽选择功能：支持将变量从列表直接拖入因子/性状/分组框
- 修复拖拽变量时误触发全局文件上传遮罩的问题
- 优化拖拽时的视觉反馈（样式高亮、透明度）

## 2026-01-23 10:35
- 新增 PCA 主成分分析模块 (`pca_analysis.py`)：支持碎石图、2D/3D 双标图、置信椭圆可视化
- 新增聚类分析模块 (`clustering.py`)：支持 K-Means 和层次聚类、肘部法则图、树状图
- `app.py` 新增 `/api/analyze_pca`、`/api/analyze_cluster` 等 API 端点
- 前端新增侧边栏布局仪表盘 (`dashboard.html`)
- 扩展 `app.js` 和 `style.css` 支持 PCA 和聚类功能
- 新增 `CLAUDE.md` 项目指导文档
- `requirements.txt` 添加 scikit-learn 和 matplotlib 依赖
