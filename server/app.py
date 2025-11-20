# Grimoire_C2/run.py (或 app.py)

from flask import Flask

from config import Config
# from server.web_routes import web_bp
from server.api_routes import api_bp
# 导入核心管理器和数据库管理
from server.persistence.database import init_db, shutdown_session



def create_app():
    # 实例化 Flask 应用
    app = Flask(__name__)
    app.config.from_object(Config)

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
    # app.register_blueprint(web_bp)

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