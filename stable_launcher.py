# -*- coding: utf-8 -*-
"""SlyLab stable launcher.

Start Flask backend, wait for /healthz, then open browser.
Write boot logs to local app-data so startup failures are diagnosable.
"""
from __future__ import annotations

import os
import sys
import socket
import time
import subprocess
import webbrowser
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError

PROJECT_DIR = Path(__file__).resolve().parent
VENV_PY = PROJECT_DIR / '.venv' / 'Scripts' / 'python.exe'
PORT = 7860
BASE_URL = f'http://127.0.0.1:{PORT}'
HEALTH_URL = f'{BASE_URL}/healthz'


def get_appdata_dir() -> Path:
    base = Path.home() / 'AppData' / 'Local' / 'SlyLab'
    base.mkdir(parents=True, exist_ok=True)
    return base


def log(msg: str) -> None:
    log_file = get_appdata_dir() / 'launcher.log'
    with log_file.open('a', encoding='utf-8') as f:
        f.write(time.strftime('[%Y-%m-%d %H:%M:%S] ') + msg + '\n')


def is_port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        return sock.connect_ex(('127.0.0.1', port)) == 0


def kill_existing_listener(port: int) -> None:
    # Best effort only; launcher should still continue if this fails.
    try:
        subprocess.run(
            [
                'powershell', '-WindowStyle', 'Hidden', '-Command',
                (
                    "$p = Get-NetTCPConnection -LocalPort %d -ErrorAction SilentlyContinue | "
                    "Select-Object -ExpandProperty OwningProcess -Unique; "
                    "foreach ($id in $p) { Stop-Process -Id $id -Force -ErrorAction SilentlyContinue }"
                ) % port,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
    except Exception as exc:
        log(f'kill_existing_listener failed: {exc}')


def choose_python() -> str:
    if VENV_PY.exists():
        return str(VENV_PY)
    return sys.executable or 'python'


def start_backend() -> subprocess.Popen:
    py = choose_python()
    log(f'start backend with: {py} app.py')
    out = open(get_appdata_dir() / 'backend.out.log', 'a', encoding='utf-8')
    err = open(get_appdata_dir() / 'backend.err.log', 'a', encoding='utf-8')
    return subprocess.Popen(
        [py, 'app.py'],
        cwd=str(PROJECT_DIR),
        stdout=out,
        stderr=err,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
    )


def wait_for_health(timeout: float = 25.0) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        try:
            req = Request(HEALTH_URL, headers={'Cache-Control': 'no-cache'})
            with urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except URLError:
            pass
        except Exception as exc:
            log(f'health check exception: {exc}')
        time.sleep(1)
    return False


def main() -> int:
    log('launcher start')

    if not PROJECT_DIR.exists():
        log(f'project dir missing: {PROJECT_DIR}')
        return 1

    kill_existing_listener(PORT)
    time.sleep(1)

    # If something else already serves healthy, just open it.
    if is_port_open(PORT) and wait_for_health(timeout=2):
        webbrowser.open(BASE_URL)
        log('existing healthy service detected, browser opened')
        return 0

    proc = start_backend()
    log(f'backend pid={proc.pid}')

    if wait_for_health():
        webbrowser.open(BASE_URL)
        log('backend healthy, browser opened')
        return 0

    log('backend failed to become healthy in time')
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
