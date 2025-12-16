from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity

from persistence.database import get_db_session
from persistence.models import Operator

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/register', methods=['POST'])
@jwt_required()
def register():
    # 可以通过 get_jwt_identity() 知道是哪个已登录的操作员在创建新用户
    current_user_id = get_jwt_identity()
    print(f"DEBUG: Operator ID {current_user_id} is attempting to register a new user.")

    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"msg": "Missing username or password"}), 400

    try:
        with get_db_session() as db:
            # 检查新用户名是否已存在
            if db.query(Operator).filter_by(username=username).first():
                return jsonify({"msg": "Operator already exists"}), 409

            # 创建新操作员
            operator = Operator(username=username)
            operator.set_password(password)
            db.add(operator)

        return jsonify({"msg": f"Operator {username} created successfully by user ID {current_user_id}"}), 201
    except Exception as e:
        print(f"Database error during registration: {e}")
        return jsonify({"msg": "Internal server error"}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    operator = None

    # 查找操作员不需要提交事务，但仍需要 db
    with get_db_session() as db:
        # 查找用户
        operator = db.query(Operator).filter_by(username=username).first()

    # 在 db 外或 db 内进行密码验证（避免将耗时操作卡在 db 事务中）
    if operator is None or not operator.check_password(password):
        return jsonify({"msg": "Bad username or password"}), 401

    # 生成 JWT Access Token
    access_token = create_access_token(identity=operator.id)

    return jsonify(access_token=access_token), 200


@auth_bp.route('/change_password', methods=['POST'])
@jwt_required()
def change_password():
    # 获取当前登录的操作员 ID (来自 JWT Payload)
    operator_id = get_jwt_identity()
    data = request.get_json()

    current_password = data.get('current_password')
    new_password = data.get('new_password')

    if not current_password or not new_password:
        return jsonify({"msg": "Missing current_password or new_password"}), 400

    try:
        with get_db_session() as db:
            # 从数据库中查询当前操作员
            operator = db.query(Operator).filter_by(id=operator_id).first()

            # 验证当前密码是否正确
            if operator is None or not operator.check_password(current_password):
                # 理论上 operator 不会是 None，因为 JWT 已经通过了身份验证
                return jsonify({"msg": "Invalid current password"}), 401

                # 设置新密码并保存到数据库 (set_password 会自动进行哈希)
            operator.set_password(new_password)
            # 依赖上下文管理器在退出时自动提交事务

        return jsonify({"msg": "Password updated successfully"}), 200

    except Exception as e:
        print(f"Database error during password change: {e}")
        return jsonify({"msg": "Internal server error"}), 500