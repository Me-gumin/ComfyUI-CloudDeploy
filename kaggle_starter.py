import os
import time
import subprocess
import threading
import socket
from comfy.cli_args import args
from app.logger import setup_logger
import logging

# 配置日志格式
setup_logger(log_level=args.verbose, use_stdout=args.log_stdout)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class KaggleNativeForwarding:
    """Kaggle 原生端口转发封装"""
    def __init__(self, port: int):
        self.port = port
        self.is_kaggle = "KAGGLE_KERNEL_RUN_TYPE" in os.environ  # 判断是否 Kaggle 环境

    def setup_native_forwarding(self):
        """打印 Kaggle 原生转发的访问信息"""
        if not self.is_kaggle:
            logging.warning("⚠️ 当前不是 Kaggle 环境，无法使用原生端口转发")
            return None

        # Kaggle 原生端口转发 URL 的格式
        notebook_id = os.environ.get("KAGGLE_KERNEL_ID", "kaggle-notebook")
        url = f"https://{notebook_id}-{self.port}.kaggleusercontent.com/"
        logging.info(f"🌍 Kaggle 原生服务已暴露: {url}")
        return url


class ComfyUIServiceWithKaggleNative:
    def __init__(self, port=8188):
        self.port = port
        self._stop_event = threading.Event()
        self.kaggle_forwarding = KaggleNativeForwarding(port)

    def check_port_ready(self):
        """检查端口是否被进程占用（即服务是否启动成功）"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(("127.0.0.1", self.port)) == 0

    def start_native_exposure(self):
        """启动 Kaggle 原生暴露服务"""
        if not self.kaggle_forwarding.is_kaggle:
            logging.info("🌍 非 Kaggle 环境，使用传统暴露方式（此处可扩展 ngrok/localtunnel）")
            return None

        # 显示原生转发信息
        url = self.kaggle_forwarding.setup_native_forwarding()

        logging.info("⏳ 服务运行中，等待连接...")
        while not self._stop_event.is_set():
            if self.check_port_ready():
                logging.debug("✅ 服务端口正常")
            else:
                logging.warning("⚠️ 服务端口不可用")
            time.sleep(30)

        return url

    def monitor_and_expose_kaggle(self):
        """Kaggle 环境专用的监控和暴露"""
        logging.info(f"🔍 开始监控端口 {self.port}...")

        max_wait_time = 300  # 最大等待5分钟
        start_time = time.time()

        while not self._stop_event.is_set():
            if self.check_port_ready():
                logging.info("🎉 ComfyUI 服务已启动!")
                self.start_native_exposure()
                break

            # 超时检查
            if time.time() - start_time > max_wait_time:
                logging.error("❌ 服务启动超时")
                break

            time.sleep(2)

        logging.info("监控线程退出")


def setup_comfyui_in_kaggle():
    """在 Kaggle 中完整设置 ComfyUI"""
    service = ComfyUIServiceWithKaggleNative(port=8188)

    logging.info("🤖 Kaggle ComfyUI 启动器")
    logging.info("=" * 50)

    # 启动监控线程
    monitor_thread = threading.Thread(
        target=service.monitor_and_expose_kaggle,
        daemon=True
    )
    monitor_thread.start()

    # 启动 ComfyUI 主服务
    try:
        logging.info("🚀 启动 ComfyUI 主进程...")
        subprocess.run([
            "python", "main.py",
            "--dont-print-server",
            "--force-fp16",
            "--listen", "0.0.0.0",  # 必须监听所有接口，才能被 Kaggle 转发
            "--port", str(service.port)
        ], check=True)
    except Exception as e:
        logging.error(f"❌ ComfyUI 启动失败: {e}")
    finally:
        service._stop_event.set()
        monitor_thread.join(timeout=1)


if __name__ == "__main__":
    setup_comfyui_in_kaggle()

