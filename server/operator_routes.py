# 操作的地方

from flask import Blueprint, jsonify, current_app, request
from flask_jwt_extended import jwt_required

from server.persistence.database import get_db_session

# 蓝图定义，URL 前缀为 /operator
operator_bp = Blueprint('operator_api', __name__, url_prefix='/api/operator')

def get_services():
    """从应用配置中获取所有共享的服务实例"""
    app_config = current_app.config
    return {
        'crypto_mgr': app_config['CRYPTO_MANAGER'],
        'beacon_service': app_config['BEACON_SERVICE'],
        'task_service': app_config['TASK_SERVICE']
    }


# 获取所有 Beacon 列表 (GET /operator/beacons)
@operator_bp.route('/beacons', methods=['GET'])
@jwt_required()
def list_beacons():
    services = get_services()
    beacon_service = services['beacon_service']
    with get_db_session() as db:
        # 获取所有 Beacon，按最后签入时间倒序排列
        beacons = beacon_service.get_all_beacons(db)

        # 格式化输出，用于 Web UI
        beacon_list = [
            {
                'id': b.id,
                'user': b.username,
                'os': b.os_info,
                'ip_address': b.ip_address,
                'last_checkin': b.last_checkin.isoformat(),
                'status': b.status,
                # 'sleep_interval': b.sleep_interval
            }
            for b in beacons
        ]

    return jsonify(beacon_list), 200


# 创建新任务 (POST /operator/task/create)
@operator_bp.route('/task/create', methods=['POST'])
@jwt_required()
def create_new_task():
    services = get_services()
    task_service = services['task_service']

    data = request.get_json()
    beacon_id = data.get('beacon_id')
    command = data.get('command')
    arguments = data.get('arguments')

    if not all([beacon_id, command]):
        return jsonify({'error': 'Missing beacon_id or command type'}), 400

    with get_db_session() as db:
        try:
            # TaskService 负责将任务写入数据库，状态为 PENDING
            task = task_service.create_task(db, beacon_id, command, arguments)

        except ValueError as e:
            # 例如：如果 beacon_id 不存在或无效
            return jsonify({'error': str(e)}), 404

        # 返回任务 ID 给操作员
        return jsonify({'message': 'Task created successfully', 'task_id': task.task_id}), 201


# 查询特定任务结果 (GET /operator/task/output/<task_id>)
@operator_bp.route('/task/output/<int:task_id>', methods=['GET'])
@jwt_required()
def get_task_output(task_id):
    services = get_services()
    task_service = services['task_service']

    with get_db_session() as db:
        task_info = task_service.get_task_output_by_id(db, task_id)

        if not task_info:
            return jsonify({'error': f'Task ID {task_id} not found'}), 404

        # 提取 Task 和 Output 对象
        task = task_info.task
        output = task_info.output  # output 可能是 None，如果任务未执行完

        # 确定内容和格式
        output_content = output.content if output else None

        # 确定内容类型：前端依赖这个字段来决定是直接显示文本还是 Base64 解码
        if task.command in ['screenshot', 'download']:
            content_type = 'base64'
        else:
            content_type = 'text'

        # 格式化输出
        return jsonify({
            'task_id': task.task_id,
            'beacon_id': task.beacon_id,
            'status': task.status,  # PENDING, ASSIGNED, COMPLETED, FAILED
            'command': task.command,
            'arguments': task.arguments,
            'assigned_at': task.assigned_at.isoformat() if task.assigned_at else None,
            'completed_at': task.completed_at.isoformat() if task.completed_at else None,

            # 核心返回内容
            'output_type': content_type,
            'output_content': output_content,  # 可能是 Base64 字符串或纯文本
        })

@operator_bp.route('/task/history/<string:beacon_id>', methods=['GET'])
@jwt_required()
def get_beacon_history(beacon_id):
    """
    根据 Beacon ID (SF) 查询该植入物的所有任务历史记录和输出。
    """
    services = get_services()
    task_service = services['task_service']

    try:
        # 验证 Beacon ID
        if not beacon_id or len(beacon_id) != 64:
            return jsonify({"error": "Invalid Beacon ID format. Must be 64 characters."}), 400

        with get_db_session() as db:
            # 从服务层获取该 Beacon 的所有任务记录
            history_list = task_service.get_tasks_by_beacon_id(db, beacon_id)

            if not history_list:
                return jsonify([]), 200  # 该 Beacon 尚未执行任何任务

            formatted_history = []
            for task_info in history_list:
                # task_info 应该是一个包含 task 和 output 属性的聚合对象 (类似你 get_task_output 中的 task_info)
                task = task_info.task
                output = task_info.output

                # 确定内容和格式
                output_content = output.content if output else None

                if output and task.command in ['screenshot', 'download']:
                    content_type = 'base64'
                else:
                    content_type = 'text'

                # 格式化结果列表
                formatted_history.append({
                    'task_id': task.task_id,
                    'status': task.status,
                    'command': task.command,
                    'arguments': task.arguments,
                    'assigned_at': task.assigned_at.isoformat() if task.assigned_at else None,
                    'completed_at': task.completed_at.isoformat() if task.completed_at else None,

                    'output_type': content_type,
                    # 仅返回输出预览，不返回完整大数据（例如整个 Base64 截图）
                    'output_preview': output_content[:200] + "..." if output_content and len(
                        output_content) > 200 else output_content,
                    'output_received_at': output.received_at.isoformat() if output else None
                })

            return jsonify(formatted_history), 200

    except Exception as e:
        print(f"[ERROR] Failed to retrieve task history for {beacon_id}: {e}")
        return jsonify({"error": "Internal server error"}), 500