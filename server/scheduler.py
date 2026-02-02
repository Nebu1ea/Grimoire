import os
import shutil

from apscheduler.schedulers.background import BackgroundScheduler
from config import Config
from server.persistence.database import get_db_session  # 调度器需要 db session
import time

def cleanup_job(app):
    """
    实际执行清理 Beacon 的任务。
    """
    print("--- SCHEDULER: Starting stale beacon cleanup job ---")
    try:
        beacon_service = app.config['BEACON_SERVICE']
        # 调度器在后台运行，必须自己获取和管理数据库会话
        with get_db_session() as db:
            # 调用 beacon_service 中实现的清理逻辑
            # cleanup_stale_beacons 会根据 config 中的阈值更新状态
            beacon_service.cleanup_stale_beacons(db)
        print("--- SCHEDULER: Stale beacon cleanup job finished ---")

    except Exception as e:
        # 确保调度器任务失败时，数据库连接能正确释放
        print(f"!!! SCHEDULER ERROR: Failed to run cleanup job: {e}")


def clean_tmp(app):
    """
    执行清理任务：只清理过期的临时构建目录
    """
    try:
        # 找到 tmp 根目录
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        tmp_dir = os.path.join(base_dir, "tmp")

        if not os.path.exists(tmp_dir):
            return

        now = time.time()
        expiration_seconds = 600  # 10分钟前的文件统统删除

        # 遍历 tmp 下的所有子目录
        for item in os.listdir(tmp_dir):
            item_path = os.path.join(tmp_dir, item)

            # 只针对 build_ 开头的文件夹进行逻辑判断
            if os.path.isdir(item_path) and item.startswith("build_"):
                # 获取文件夹的最后修改时间
                mtime = os.path.getmtime(item_path)

                if (now - mtime) > expiration_seconds:
                    shutil.rmtree(item_path, ignore_errors=True)
                    print(f"[CLEANUP] 成功超度了过期的文件夹: {item}")
                else:
                    print(f"[CLEANUP] 文件夹 {item} 还很年轻，留它一条生路。")

    except Exception as e:
        print(f"!!! SCHEDULER ERROR: Cleanup failed: {e}")

def start_scheduler(app):
    """
    初始化并启动后台调度器。
    """
    # 确保只在应用上下文中运行一次
    if not hasattr(app, 'scheduler'):
        scheduler = BackgroundScheduler()

        # 注册任务：定时清理
        scheduler.add_job(
            cleanup_job,
            'interval',
            minutes=Config.CLEANUP_INTERVAL_MINUTES,
            id='cleanup_stale_beacons_job',
            name='Stale Beacon Cleanup',
            max_instances=1,
            args=[app]
        )

        # 注册任务: 删除tmp文件夹
        scheduler.add_job(
            clean_tmp,
            'interval',
            minutes=Config.CLEANUP_INTERVAL_MINUTES,
            id='cleanup_tmp_job',
            name='Tmp Dir Cleanup',
            max_instances=1,
            args=[app]
        )

        scheduler.start()
        app.scheduler = scheduler
        print(f"*** Scheduler started. Cleanup job runs every {Config.CLEANUP_INTERVAL_MINUTES} minutes. ***")

        # 在程序退出时关闭调度器
        import atexit
        atexit.register(lambda: scheduler.shutdown())