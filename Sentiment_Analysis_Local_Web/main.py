# main.py
import time
import socket
import webbrowser
from pathlib import Path
from threading import Thread

import uvicorn

import config
import runtime
from app import app


def _port_is_free(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False


def pick_free_port(host: str, start_port: int, max_tries: int) -> int:
    for p in range(start_port, start_port + max_tries):
        if _port_is_free(host, p):
            return p
    raise RuntimeError("No free port found in the scan range.")


def wait_until_listening(host: str, port: int, timeout_s: float = 8.0) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.3)
            try:
                s.connect((host, port))
                return True
            except OSError:
                time.sleep(0.15)
    return False


def _find_desktop_dir() -> Path:
    home = Path.home()
    for p in (home / "Desktop", home / "desktop"):
        if p.exists():
            return p

    mnt_users = Path("/mnt/c/Users")
    if mnt_users.exists():
        candidates = []
        for user_dir in mnt_users.iterdir():
            d = user_dir / "Desktop"
            try:
                if d.exists():
                    candidates.append(d)
            except PermissionError:
                continue
        if candidates:
            candidates.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            return candidates[0]

    return Path.cwd()


def write_redirect_html(url: str) -> Path:
    desktop = _find_desktop_dir()
    out_path = desktop / "Sentimet_Analysis_Web.html"

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta http-equiv="refresh" content="0; url={url}">
  <title>Sentiment Analysis</title>
</head>
<body>
  <p>Redirecting to <a href="{url}">{url}</a> ...</p>
</body>
</html>"""

    out_path.write_text(html, encoding="utf-8")
    return out_path


def main():
    runtime.init_runtime()

    port = pick_free_port(config.APP_HOST, config.PREFERRED_PORT, config.PORT_SCAN_MAX)
    url = f"http://{config.APP_HOST}:{port}/"

    html_path = write_redirect_html(url)
    print(f"Desktop HTML written: {html_path}", flush=True)

    uv_conf = uvicorn.Config(app, host=config.APP_HOST, port=port, log_level="info")
    server = uvicorn.Server(uv_conf)

    th = Thread(target=server.run, daemon=False)
    th.start()

    if wait_until_listening(config.APP_HOST, port, timeout_s=8.0):
        webbrowser.open(url)
        print(f"Opened: {url}", flush=True)
    else:
        print(f"Open in browser: {url}", flush=True)

    th.join()


if __name__ == "__main__":
    main()
