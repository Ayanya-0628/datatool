# -*- coding: utf-8 -*-
"""
数据分析工具 - 轻量版启动器
启动本地 Flask 服务并调用系统浏览器
"""

import sys
import os
import socket
import threading
import time
import ctypes
import traceback
import webbrowser

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

# 导入 PyQt6 模块 (仅保留基本组件)
from PyQt6.QtWidgets import (QApplication, QMainWindow, QMessageBox, QFileDialog,
                             QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout)
from PyQt6.QtCore import QUrl, QTimer, QObject, pyqtSignal, Qt
from PyQt6.QtGui import QIcon, QFont

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
        self.url = f"http://127.0.0.1:{self.port}"

        # 连接信号
        dialog_signal.request_directory.connect(self.open_directory_dialog)

        self.initUI()

        # 启动后自动打开浏览器
        QTimer.singleShot(500, lambda: webbrowser.open(self.url))

    def initUI(self):
        self.setWindowTitle('数据分析工具 - 服务控制器')
        self.resize(400, 220)
        self.setFixedSize(400, 220)  # 固定大小

        # 中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)

        # 状态标签
        self.status_label = QLabel(f"服务正在运行\n{self.url}")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(12)
        self.status_label.setFont(font)
        layout.addWidget(self.status_label)

        # 按钮区域
        btn_layout = QHBoxLayout()

        self.btn_open = QPushButton("在浏览器中打开")
        self.btn_open.setMinimumHeight(40)
        self.btn_open.clicked.connect(lambda: webbrowser.open(self.url))

        self.btn_exit = QPushButton("退出程序")
        self.btn_exit.setMinimumHeight(40)
        self.btn_exit.clicked.connect(self.close)

        btn_layout.addWidget(self.btn_open)
        btn_layout.addWidget(self.btn_exit)

        layout.addLayout(btn_layout)

        # 说明文字
        info_label = QLabel("提示: 程序运行期间请勿关闭此窗口")
        info_label.setStyleSheet("color: gray; font-size: 10px;")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info_label)

        central_widget.setLayout(layout)

        if os.path.exists('static/favicon.ico'):
            self.setWindowIcon(QIcon('static/favicon.ico'))

    def open_directory_dialog(self):
        """在主线程打开文件夹选择框"""
        try:
            # 窗口置顶，确保用户能看到
            self.activateWindow()
            # 恢复窗口（如果是最小化）
            if self.isMinimized():
                self.showNormal()

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
    # 使用 threaded=True 确保 Flask 能处理并发请求
    run_simple('127.0.0.1', port, app, use_reloader=False, use_debugger=False, threaded=True)

def main():
    if getattr(sys, 'frozen', False):
        app_dir = os.path.dirname(sys.executable)
    else:
        app_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(app_dir)

    port = find_free_port(7860)
    os.environ['PORT'] = str(port)

    # 启动 Flask 线程
    flask_thread = threading.Thread(target=start_flask, args=(port,))
    flask_thread.daemon = True
    flask_thread.start()

    # 启动 GUI
    qt_app = QApplication(sys.argv)
    qt_app.setApplicationName("数据分析工具")

    window = MainWindow(port)
    window.show()

    sys.exit(qt_app.exec())

if __name__ == '__main__':
    try:
        main()
    except Exception:
        # 如果没有控制台，弹窗显示错误信息
        error_msg = traceback.format_exc()
        ctypes.windll.user32.MessageBoxW(0, error_msg, "Application Error", 0x10)
        sys.exit(1)
