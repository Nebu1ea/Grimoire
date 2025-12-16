# Grimoire_C2/run.py (或 app.py)

from flask import Flask
from config import Config
from server.api_routes import api_bp
from server.core.beacon_service import GrimoireBeaconService
from server.core.task_service import GrimoireTaskService
from server.operator_routes import operator_bp
from server.auth_routes import auth_bp
# 导入核心管理器和数据库管理
from server.persistence.database import init_db, shutdown_session
from server.scheduler import start_scheduler
from shared.CryptoManager import GrimoireCryptoManager


def create_app():
    # 实例化 Flask 应用
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config['CRYPTO_MANAGER'] = GrimoireCryptoManager()
    app.config['BEACON_SERVICE'] = GrimoireBeaconService()
    app.config['TASK_SERVICE'] = GrimoireTaskService()


    # 初始化数据库连接和模型
    try:
        init_db()
        print("Grimoire Server: Database initialized and ready.")
    except Exception as e:
        print("FATAL: Database initialization failed.")
        print(f"Error Details: {e}")
        exit(1)

    # 注册 Teardown 钩子
    # 保证每个请求结束时，线程绑定的数据库会话都被清理
    app.teardown_appcontext(shutdown_session)

    # 注册路由蓝图
    app.register_blueprint(api_bp)
    app.register_blueprint(operator_bp)
    app.register_blueprint(auth_bp)


    start_scheduler(app)

    return app



if __name__ == '__main__':
    app = create_app()

    print("-" * 50)
    print(f"{Config.PROJECT_NAME} Server")
    print(f"Mode: {'DEBUG' if app.debug else 'PRODUCTION'}")
    print(f"Listening on: http://{Config.SERVER_HOST}:{Config.SERVER_PORT}")
    print("-" * 50)

    app.run(
        host=Config.SERVER_HOST,
        port=Config.SERVER_PORT,
        debug=Config.DEBUG
    )