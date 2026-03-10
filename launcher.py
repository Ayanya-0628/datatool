# -*- coding: utf-8 -*-
"""
SlyLab - 启动器（无窗口）
启动 Flask 后直接打开系统浏览器；仅在点击「选择目录」时弹出文件夹选择框。
关闭浏览器标签页时会尝试自动结束服务。
"""

import sys
import os
import socket
import threading
import ctypes
import traceback
import webbrowser

class NullWriter:
    def write(self, text):
        pass
    def flush(self):
        pass

if sys.stdout is None:
    sys.stdout = NullWriter()
if sys.stderr is None:
    sys.stderr = NullWriter()

from PyQt6.QtWidgets import QApplication, QFileDialog
from PyQt6.QtCore import QTimer, QObject, pyqtSignal, pyqtSlot

from app import app
from flask import jsonify
from werkzeug.serving import run_simple

# === 目录选择：网页点「选择目录」时由 Qt 主线程弹窗（无主窗口）===
class DialogSignal(QObject):
    request_directory = pyqtSignal()

dialog_signal = DialogSignal()
dialog_lock = threading.Event()
dialog_result = {"path": None}


class DialogHelper(QObject):
    @pyqtSlot()
    def show_directory_dialog(self):
        try:
            directory = QFileDialog.getExistingDirectory(None, "选择保存结果的文件夹")
            dialog_result["path"] = directory
        except Exception:
            dialog_result["path"] = None
        finally:
            dialog_lock.set()


def qt_select_directory_override():
    dialog_lock.clear()
    dialog_result["path"] = None
    dialog_signal.request_directory.emit()
    dialog_lock.wait()
    directory = dialog_result["path"]
    if directory:
        return jsonify({'success': True, 'directory': directory})
    return jsonify({'success': False, 'message': '未选择目录'})


app.view_functions['select_directory'] = qt_select_directory_override


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
    url = f"http://127.0.0.1:{port}"

    flask_thread = threading.Thread(target=start_flask, args=(port,))
    flask_thread.daemon = True
    flask_thread.start()

    qt_app = QApplication(sys.argv)
    qt_app.setApplicationName("SlyLab")

    helper = DialogHelper()
    dialog_signal.request_directory.connect(helper.show_directory_dialog)

    QTimer.singleShot(500, lambda: webbrowser.open(url))
    sys.exit(qt_app.exec())


if __name__ == '__main__':
    try:
        main()
    except Exception:
        error_msg = traceback.format_exc()
        ctypes.windll.user32.MessageBoxW(0, error_msg, "Application Error", 0x10)
        sys.exit(1)

