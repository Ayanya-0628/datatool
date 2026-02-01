# 技能：将 Web 应用打包为单文件 EXE (Python/Flask)

## 简介
此技能用于将基于 Python Flask 的 Web 应用程序打包成一个独立的 Windows 可执行文件 (.exe)。该可执行文件启动后会自动运行本地 Web 服务器，并调用系统默认浏览器打开应用界面，无需用户安装 Python 环境或配置浏览器。

## 适用场景
- 打包 Web 应用
- 打包为免安装应用
- 打包为单独文件即可运行的应用
- 部署轻量级桌面工具

## 核心步骤

### 1. 准备启动器脚本 (launcher.py)
创建一个 `launcher.py` 作为程序的入口点，它负责：
1.  启动 Flask 服务（在独立线程中）。
2.  启动一个轻量级 GUI（如 PyQt6 或 Tkinter）作为控制台，防止程序后台静默运行。
3.  自动打开系统默认浏览器访问 `http://127.0.0.1:{port}`。
4.  (可选) 覆盖 Flask 的某些功能（如文件选择对话框），使其调用原生系统对话框。

**关键代码片段 (launcher.py):**
```python
import sys
import threading
import webbrowser
from PyQt6.QtWidgets import QApplication, QMainWindow
from app import app # 导入你的 Flask app 对象

def start_flask(port):
    app.run(port=port, use_reloader=False)

def main():
    port = 7860
    # 启动 Flask 线程
    t = threading.Thread(target=start_flask, args=(port,))
    t.daemon = True
    t.start()

    # 启动 GUI (PyQt6 示例)
    qt_app = QApplication(sys.argv)
    window = QMainWindow()
    window.setWindowTitle("服务正在运行")
    window.show()

    # 延迟打开浏览器
    QTimer.singleShot(500, lambda: webbrowser.open(f"http://127.0.0.1:{port}"))

    sys.exit(qt_app.exec())

if __name__ == '__main__':
    main()
```

### 2. 创建 PyInstaller 配置文件 (.spec)
使用 `pyinstaller` 生成 `.spec` 文件并进行配置。

**命令:** `pyi-makespec launcher.py --name MyApp_Browser --onefile --noconsole`

**配置重点 (browser_app.spec):**
1.  **Hidden Imports**: 手动添加 Flask, Pandas, Numpy, Scikit-learn 等隐式依赖。
2.  **Datas**: 包含 `templates` 和 `static` 目录。
3.  **Excludes**: 排除不必要的重型库（如 `tkinter` 如果用 PyQt，或 `pythonnet`）。
4.  **Collect All**: 对于 `sklearn`, `scipy` 等复杂库，使用 `collect_all` 钩子收集所有子模块和动态库。

```python
from PyInstaller.utils.hooks import collect_all

datas = [('templates', 'templates'), ('static', 'static')]
binaries = []
hiddenimports = ['flask', 'engineio.async_drivers.threading']

# 收集科学计算库的所有资源
packages = ['sklearn', 'scipy', 'statsmodels']
for package in packages:
    p_datas, p_binaries, p_hiddenimports = collect_all(package)
    datas.extend(p_datas)
    binaries.extend(p_binaries)
    hiddenimports.extend(p_hiddenimports)

a = Analysis(
    ['launcher.py'],
    datas=datas,
    hiddenimports=hiddenimports,
    ...
)
```

### 3. 执行打包
运行 PyInstaller 命令进行构建。建议加上 `--clean` 清除缓存。

```bash
pyinstaller browser_app.spec --clean --noconfirm
```

### 4. 验证与发布
1.  在 `dist/` 目录下找到生成的 `.exe` 文件。
2.  双击运行，检查是否成功启动服务器并打开浏览器。
3.  验证静态资源（CSS/JS）是否加载正常。
4.  (可选) 使用 Inno Setup 进一步制作安装包 (`setup.exe`)。

## 常见问题处理
1.  **缺少模块**: 在 `.spec` 文件的 `hiddenimports` 中添加报错的模块名。
2.  **静态文件丢失**: 确保在 `.spec` 的 `datas` 中正确映射了文件夹路径。
3.  **无限重启/多进程错误**: 在 `launcher.py` 顶部添加 `multiprocessing.freeze_support()`。
4.  **控制台闪烁**: 确保 `.spec` 中设置了 `console=False`。
