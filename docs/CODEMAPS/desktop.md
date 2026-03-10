# 桌面版架构 (Desktop)

**最后更新:** 2026-01-25
**入口文件:** `launcher.py` (175 行)

## 架构概览

```
Desktop Application
├── launcher.py          # PyQt6 主程序
├── app.py               # Flask 后端 (内嵌)
├── app.spec             # PyInstaller 配置
└── setup.iss            # Inno Setup 安装脚本
```

## 技术栈

- **PyQt6** - Qt 6 Python 绑定
- **Qt WebEngine** - Chromium 内核 Web 视图
- **PyInstaller** - 打包为单文件可执行程序
- **Inno Setup** - Windows 安装程序生成

## 核心组件

### 1. 主窗口 (MainWindow)

```python
class MainWindow(QMainWindow):
    def __init__(self, port):
        # 创建 WebEngineView
        self.browser = QWebEngineView()
        self.setCentralWidget(self.browser)

        # 加载本地 Flask 页面
        self.browser.setUrl(QUrl(f"http://127.0.0.1:{port}"))
```

### 2. Flask 线程

```python
def start_flask(port):
    """在后台线程运行 Flask"""
    run_simple('127.0.0.1', port, app,
               use_reloader=False,
               use_debugger=False,
               threaded=True)

# 启动
flask_thread = threading.Thread(target=start_flask, args=(port,))
flask_thread.daemon = True
flask_thread.start()
```

### 3. 端口发现

```python
def find_free_port(start_port=7860):
    """查找可用端口"""
    for port in range(start_port, start_port + 100):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('127.0.0.1', port))
            sock.close()
            return port
        except OSError:
            continue
    return start_port
```

### 4. 线程安全的目录选择

```python
# Flask 线程 -> Qt 主线程通信
class DialogSignal(QObject):
    request_directory = pyqtSignal()

dialog_signal = DialogSignal()
dialog_lock = threading.Event()
dialog_result = {"path": None}

def qt_select_directory_override():
    """替代原生 tkinter 对话框"""
    dialog_lock.clear()
    dialog_signal.request_directory.emit()
    dialog_lock.wait()  # 阻塞等待用户选择
    return jsonify({'success': True, 'directory': dialog_result["path"]})

# 覆盖 Flask 路由
app.view_functions['select_directory'] = qt_select_directory_override
```

### 5. 性能优化

```python
# 高 DPI 支持
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

# 使用 ANGLE (DirectX 11) 后端
os.environ["QT_OPENGL"] = "angle"
os.environ["QT_ANGLE_PLATFORM"] = "d3d11"

# GPU 栅格化
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
    "--enable-gpu-rasterization "
    "--disable-gpu-vsync "
    "--disable-frame-rate-limit "
    "--enable-accelerated-2d-canvas"
)
```

### 6. 无控制台模式兼容

```python
class NullWriter:
    """吞掉 print 输出，防止无控制台时报错"""
    def write(self, text): pass
    def flush(self): pass

if sys.stdout is None:
    sys.stdout = NullWriter()
if sys.stderr is None:
    sys.stderr = NullWriter()
```

## 打包配置

### PyInstaller (app.spec)

```python
# 关键配置
a = Analysis(
    ['launcher.py'],
    datas=[
        ('templates', 'templates'),
        ('static', 'static'),
    ],
    hiddenimports=[
        'sklearn.cluster',
        'sklearn.decomposition',
        'scipy.cluster.hierarchy',
    ],
)

exe = EXE(
    pyz, a.scripts,
    name='SlyLab',
    console=False,  # 无控制台窗口
    icon='static/favicon.ico',
)
```

### Inno Setup (setup.iss)

```ini
[Setup]
AppName=SlyLab
AppVersion=2.0
DefaultDirName={autopf}\SlyLab
OutputBaseFilename=SlyLab_Setup

[Files]
Source: "dist\SlyLab\*"; DestDir: "{app}"; Flags: recursesubdirs

[Icons]
Name: "{commondesktop}\SlyLab"; Filename: "{app}\SlyLab.exe"
```

## 数据存储路径

```python
def get_app_data_dir():
    """获取应用数据目录 (避免权限问题)"""
    home = os.path.expanduser("~")
    if sys.platform == "win32":
        return os.path.join(home, "AppData", "Local", "SlyLab")
    else:
        return os.path.join(home, ".data_analysis_tool")
```

存储内容:
- `exports/` - 导出文件缓存
- `error.log` - 错误日志
- `debug_analyze.log` - 调试日志

## 启动流程

```
1. main()
   ├── 设置工作目录
   ├── 查找可用端口
   ├── 启动 Flask 后台线程
   ├── 创建 QApplication
   ├── 创建 MainWindow
   └── 进入 Qt 事件循环

2. MainWindow.__init__()
   ├── 连接信号槽
   ├── 创建 WebEngineView
   ├── 加载 Flask URL
   └── 设置窗口图标

3. 延迟刷新 (1秒后)
   └── 确保 Flask 已完全启动
```

## 依赖项

```
PyQt6
PyQt6-WebEngine
pyinstaller
```

## 构建命令

```bash
# 打包
pyinstaller app.spec

# 生成安装程序 (需要 Inno Setup)
iscc setup.iss
```

## 输出文件

```
dist/
└── SlyLab/
    ├── SlyLab.exe
    ├── templates/
    ├── static/
    └── [Qt/Python 运行时]

Output/
└── SlyLab_Setup.exe  # 安装程序
```

