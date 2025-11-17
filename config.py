"""
Grimoire Global Configuration
"""
from pathlib import Path
import os

class Config:
    # ========= 基础信息 =========
    PROJECT_NAME = "Grimoire"
    VERSION = "0.0.1"
    AUTHOR = "Nebu1ea"

    # ========= 通信相关 =========
    SERVER_HOST = os.getenv("GRIMOIRE_HOST", "0.0.0.0")
    SERVER_PORT = int(os.getenv("GRIMOIRE_PORT", "8080"))
    SERVER_URL = os.getenv("GRIMOIRE_URL", "https://127.0.0.1:8080")  # beacon 回调地址

    # ========= 加密相关 =========
    CURVE_TYPE = "X25519"
    AES_KEY_LENGTH = 32
    HKDF_INFO = b"grimoire-2025-" + VERSION.encode('utf-8')

    # ========= beacon 行为 =========
    DEFAULT_JITTER = (5, 15)             # 心跳随机范围（秒）
    MAX_RETRY = 5

    # ========= 前端相关 =========
    THEME = "cyberpunk"                  # 还没想好,也还没开始写

    # ========= 路径 =========
    BASE_DIR = Path(__file__).parent
    LOG_DIR = BASE_DIR / "logs"
    PAYLOAD_DIR = BASE_DIR / "server" / "static" / "payloads"


config = Config()
SERVER_PUBLIC_URL = config.SERVER_URL