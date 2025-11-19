from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from server.persistence.models import Base
from contextlib import contextmanager
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
        ConnectEngine.connect()
        # 创建所有表
        Base.metadata.create_all(bind=ConnectEngine)
        print("MySQL tables checked/created successfully.")
    except Exception as e:
        print("ERROR: Could not connect to database or create tables!")
        print(f"Connection URI: {Config.DATABASE_URI}")
        print(f"Details: {e}")
        raise

    # 创建会话工厂，并把线程隔离，保证多线程也能正常操作
    DatabaseSessionManager = scoped_session(
        sessionmaker(autocommit=False, autoflush=False, bind=ConnectEngine)
    )

# 用这个钻饰使其可以让with调用
@contextmanager
def get_db_session():
    """
    提供一个数据库会话供外部模块使用。
    """
    if DatabaseSessionManager is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    db = DatabaseSessionManager()
    try:
        # 这里不用return是为了防止以后忘记close了
        yield db
        # 正常退出在提交
        db.commit()
    except Exception as e:
        # 发生异常时，回滚事务
        db.rollback()
        raise e
    finally:
        DatabaseSessionManager.remove()


def shutdown_session():
    """
    在 Flask 请求结束后移除和清理会话。
    """
    if DatabaseSessionManager:
        DatabaseSessionManager.remove()