# 操作的地方

from flask import Blueprint, jsonify, current_app, request
from server.persistence.database import get_db_session

# 蓝图定义，URL 前缀为 /operator
operator_bp = Blueprint('operator_api', __name__, url_prefix='/operator')

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
                'ip_address': b.ip_address,
                'status': b.status,
                'last_seen': b.last_seen.isoformat(),
                'sleep_interval': b.sleep_interval,
                'initial_data': b.initial_data
            }
            for b in beacons
        ]

    return jsonify(beacon_list)


# 创建新任务 (POST /operator/task/create)
@operator_bp.route('/task/create', methods=['POST'])
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