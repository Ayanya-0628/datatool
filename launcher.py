# -*- coding: utf-8 -*-
"""
数据分析工具 - 专业桌面版启动器 (PyQt6)
使用 Qt WebEngine 提供原生应用体验
"""

import sys
import os
import socket
import threading
import time
import ctypes
import traceback

# --- 关键修复：防止无控制台模式下 print/stderr 报错 ---
class NullWriter:
    """一个什么都不做的伪装 writer，用于吞掉 print 输出"""
    def write(self, text):
        pass
    def flush(self):
        pass

if sys.stdout is None:
    sys.stdout = NullWriter()
if sys.stderr is None:
    sys.stderr = NullWriter()
# ----------------------------------------------------

# 导入 PyQt6 模块
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox, QFileDialog
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl, QTimer, QObject, pyqtSignal, Qt
from PyQt6.QtGui import QIcon

# --- 性能优化：移除激进参数，改用 DPI 适配 ---
# 1. 移除可能导致负优化的 GPU 强制参数
if "QTWEBENGINE_CHROMIUM_FLAGS" in os.environ:
    del os.environ["QTWEBENGINE_CHROMIUM_FLAGS"]

# 2. 启用高分屏自动缩放 (解决渲染过重导致的卡顿)
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

# 3. 终极性能优化：强制使用 ANGLE (DirectX 11) 后端
# 这通常能解决 Windows 上 Qt WebEngine 滚动卡顿的问题
os.environ["QT_OPENGL"] = "angle"
os.environ["QT_ANGLE_PLATFORM"] = "d3d11"

# 4. 恢复 GPU 栅格化 (在 ANGLE 模式下通常是安全的，且能进一步提升滚动性能)
# 增加 --disable-frame-rate-limit 解除 60fps 限制，提升高刷屏体验
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
    "--enable-gpu-rasterization "
    "--disable-gpu-vsync "
    "--disable-frame-rate-limit "
    "--enable-accelerated-2d-canvas"
)
# --------------------------------

# 导入 Flask 应用
from app import app
from flask import jsonify
from werkzeug.serving import run_simple

# === 线程通信机制 (Flask -> Qt) ===
# 用于在 Flask 线程中安全调用 Qt 主线程的对话框
class DialogSignal(QObject):
    request_directory = pyqtSignal()

# 全局信号对象和同步锁
dialog_signal = DialogSignal()
dialog_lock = threading.Event()
dialog_result = {"path": None}

def qt_select_directory_override():
    """替代 app.py 中的 select_directory，使用 Qt 原生对话框"""
    # 1. 清除事件状态
    dialog_lock.clear()
    dialog_result["path"] = None

    # 2. 发送信号给主线程 (Qt)
    dialog_signal.request_directory.emit()

    # 3. 阻塞等待用户选择完成
    dialog_lock.wait()

    # 4. 获取结果并返回
    directory = dialog_result["path"]
    if directory:
        return jsonify({'success': True, 'directory': directory})
    else:
        return jsonify({'success': False, 'message': '未选择目录'})

# 关键：覆盖 Flask 的原有路由处理函数
app.view_functions['select_directory'] = qt_select_directory_override
# =================================

class MainWindow(QMainWindow):
    def __init__(self, port):
        super().__init__()
        self.port = port

        # 连接信号
        dialog_signal.request_directory.connect(self.open_directory_dialog)

        self.initUI()

    def initUI(self):
        self.setWindowTitle('数据分析工具 - 专业版')
        self.resize(1280, 850)
        self.setMinimumSize(800, 600)

        # 创建浏览器视图
        self.browser = QWebEngineView()
        self.setCentralWidget(self.browser)

        # 加载本地 Flask 页面
        url = f"http://127.0.0.1:{self.port}"
        self.browser.setUrl(QUrl(url))

        if os.path.exists('static/favicon.ico'):
            self.setWindowIcon(QIcon('static/favicon.ico'))

    def open_directory_dialog(self):
        """在主线程打开文件夹选择框"""
        try:
            # 窗口置顶，确保用户能看到
            self.activateWindow()
            directory = QFileDialog.getExistingDirectory(self, "选择保存结果的文件夹")
            dialog_result["path"] = directory
        except Exception as e:
            print(f"Dialog Error: {e}")
            dialog_result["path"] = None
        finally:
            # 无论如何都要释放锁，防止 Flask 线程死锁
            dialog_lock.set()

def find_free_port(start_port=7860):
    for port in range(start_port, start_port + 100):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('127.0.0.1', port))
            sock.close()
            return port
        except OSError:
            continue
    return start_port

def start_flask(port):
    run_simple('127.0.0.1', port, app, use_reloader=False, use_debugger=False, threaded=True)

def main():
    if getattr(sys, 'frozen', False):
        app_dir = os.path.dirname(sys.executable)
    else:
        app_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(app_dir)

    port = find_free_port(7860)
    os.environ['PORT'] = str(port)

    flask_thread = threading.Thread(target=start_flask, args=(port,))
    flask_thread.daemon = True
    flask_thread.start()

    qt_app = QApplication(sys.argv)
    qt_app.setApplicationName("数据分析工具")

    window = MainWindow(port)
    window.show()

    QTimer.singleShot(1000, lambda: window.browser.reload())

    sys.exit(qt_app.exec())

if __name__ == '__main__':
    try:
        main()
    except Exception:
        # 如果没有控制台，弹窗显示错误信息
        error_msg = traceback.format_exc()
        ctypes.windll.user32.MessageBoxW(0, error_msg, "Application Error", 0x10)
        sys.exit(1)
