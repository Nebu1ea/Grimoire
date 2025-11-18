from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from server.persistence.models import Base
from config import Config

# 连接引擎
ConnectEngine = None
# 会话工厂
DatabaseSessionManager = None


# 初始化
def init_db():
    global ConnectEngine, DatabaseSessionManager

    # 创建 SQLAlchemy 引擎
    ConnectEngine = create_engine(
        Config.DATABASE_URI,
        # echo=True 打印所有执行的 SQL 语句，方便调试
        echo=True
    )

    # 测试连接并创建表
    try:
        # 尝试连接
        ConnectEngine.connect()
    except Exception as e:
        print("ERROR: Could not connect to MySQL database!")
        print(f"Connection URI: {Config.DATABASE_URI}")
        print(f"Details: {e}")
        raise

    # 创建所有表
    Base.metadata.create_all(bind=ConnectEngine)
    print("MySQL tables checked/created successfully.")

    # 创建会话工厂，并把线程隔离，保证多线程也能正常操作
    DatabaseSessionManager = scoped_session(
        sessionmaker(autocommit=False, autoflush=False, bind=ConnectEngine)
    )


def get_db_session():
    """
    提供一个数据库会话供外部模块使用。
    """
    db = DatabaseSessionManager()
    try:
        # 这里不用return是为了防止以后忘记close了
        yield db
    finally:
        db.close()


def shutdown_session(exception=None):
    """
    在 Flask 请求结束后移除和清理会话。
    """
    DatabaseSessionManager.remove()