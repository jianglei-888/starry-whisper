import sys
import os
import threading

# 确保从项目根目录运行
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import yaml
import uvicorn
import webview
from src.api import app

with open("config/config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)


def start_server():
    uvicorn.run(
        app,
        host=config["api"]["host"],
        port=config["api"]["port"],
        log_level="warning",
    )


if __name__ == "__main__":
    # 后台启动 FastAPI
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    import time
    time.sleep(1)  # 等服务启动

    # 启动桌面窗口
    host = config["api"]["host"]
    port = config["api"]["port"]
    window = webview.create_window(
        title=config["window"]["title"],
        url=f"http://{host}:{port}",
        width=config["window"]["width"],
        height=config["window"]["height"],
        resizable=True,
        min_size=(360, 500),
    )
    webview.start()
