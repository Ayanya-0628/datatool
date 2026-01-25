import os
import sys
import threading
import webview
from waitress import serve
from app import app
import socket

# Ensure we can find the template/static folders when frozen
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def start_server(port):
    serve(app, host='127.0.0.1', port=port)

def get_free_port():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
    sock.close()
    return port

if __name__ == '__main__':
    # Configuration for frozen environment
    if getattr(sys, 'frozen', False):
        app.template_folder = resource_path('templates')
        app.static_folder = resource_path('static')
        app.root_path = sys._MEIPASS

    port = get_free_port()

    # Start the Flask server in a separate thread
    t = threading.Thread(target=start_server, args=(port,))
    t.daemon = True
    t.start()

    # Create the window
    webview.create_window("Data Analysis Tool", f"http://127.0.0.1:{port}")
    webview.start()
