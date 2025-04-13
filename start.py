import subprocess
import threading
import time
import socket
import urllib.request
import logging
from typing import Optional

# 配置日志格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ComfyUIService:
    def __init__(self, port: int = 8188):
        self.port = port
        self._stop_event = threading.Event()

    def check_port_ready(self) -> bool:
        """检查端口是否就绪"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            return sock.connect_ex(('127.0.0.1', self.port)) == 0

    def start_localtunnel(self):
        """启动localtunnel暴露服务"""
        try:
            # 获取公网IP
            public_ip = urllib.request.urlopen(
                'https://ipv4.icanhazip.com', 
                timeout=3
            ).read().decode('utf8').strip()
            
            logger.info(f"\n ComfyUI 服务已启动在端口 {self.port}")
            logger.info(f" 公网访问 IP: {public_ip}")
            
            # 启动localtunnel
            process = subprocess.Popen(
                ["lt", "--port", str(self.port)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # 实时输出日志
            while not self._stop_event.is_set():
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    logger.info(output.strip())
            
        except Exception as e:
            logger.error(f"启动localtunnel失败: {e}")

    def monitor_and_expose(self):
        """监控ComfyUI服务并暴露端口"""
        logger.info(f" 开始监控端口 {self.port}...")
        
        while not self._stop_event.is_set():
            if self.check_port_ready():
                self.start_localtunnel()
                break
            time.sleep(0.5)
        
        logger.info("监控线程退出")

    def start_comfyui(self):
        """启动ComfyUI主服务"""
        try:
            logger.info("正在启动 ComfyUI 主服务...")
            subprocess.run(
                ["python", "main.py", "--dont-print-server"],
                check=True
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"ComfyUI 启动失败: {e}")
        finally:
            self._stop_event.set()

    def run(self):
        """主运行方法"""
        # 启动监控线程
        monitor_thread = threading.Thread(
            target=self.monitor_and_expose,
            daemon=True
        )
        monitor_thread.start()
        
        # 启动ComfyUI
        self.start_comfyui()
        
        # 等待线程结束
        monitor_thread.join(timeout=1)

if __name__ == "__main__":
    service = ComfyUIService(port=8188)
    service.run()