import json

from config import Config
from server.persistence.models import Beacon
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Dict, Any, List


class GrimoireBeaconService:
    """
    Beacon 服务层：处理 Beacon 的生命周期管理、数据库注册和状态更新。
    不维护 IP 缓存，依赖 SF 进行会话识别。
    """
    def register_new_beacon(self, db: Session, beacon_id: str, ip_address: str, initial_data: Dict[str, Any]) -> Beacon:
        """
        处理 Beacon 首次签入，将新 Beacon 注册到数据库。
        beacon_id 即为 SF。
        """
        # 检查 Beacon ID 是否已存在，SQLAlchemy重载了等号，所以这里报错就别管了
        existing_beacon = db.query(Beacon).filter(Beacon.id == beacon_id).first()

        if existing_beacon:
            # 如果 ID 存在则更新其状态
            existing_beacon.last_checkin = datetime.utcnow()
            existing_beacon.ip_address = ip_address  # 更新其当前 IP
            existing_beacon.status = 'Active'
            db.add(existing_beacon)
            return existing_beacon

        # 创建新的 Beacon 实例
        new_beacon = Beacon(
            id=beacon_id,
            ip_address=ip_address,
            hostname=initial_data.get('hostname', 'N/A'),
            username=initial_data.get('login_user', 'N/A'),
            os_info=initial_data.get('os', 'N/A'),
            first_seen=datetime.utcnow(),
            last_checkin=datetime.utcnow(),
            status='Active'
        )


        db.add(new_beacon)

        return new_beacon

    def get_beacon_by_id(self, db: Session, beacon_id: str) -> Beacon | None:
        """
        通过 Beacon ID 从数据库获取完整的 Beacon 对象。
        """
        return db.query(Beacon).filter(Beacon.id == beacon_id).first()

    def update_checkin_time(self, db: Session, beacon_id: str):
        """
        更新 Beacon 的最后签入时间，并设置状态为 Active。
        """
        beacon = self.get_beacon_by_id(db, beacon_id)
        if beacon:
            beacon.last_checkin = datetime.utcnow()
            beacon.status = 'Active'
            db.add(beacon)
        else:
            # 这是一个警告：SF 存在但数据库没有对应记录，可能需要重新注册
            print(f"WARNING: SF {beacon_id[:8]} found but no matching database entry.")

    # 定期检查 last_checkin，将超过阈值的 Beacon 状态设为 'Stale'。
    def cleanup_stale_beacons(self, db: Session):
        """
        标记长时间未签入的 Beacon 为 'Stale'。
        通常通过定时任务调用。
        """
        # 不活跃阈值,目前为600s，想改去config.py
        stale_time_limit = datetime.utcnow() - timedelta(seconds=Config.STALE_THRESHOLD_SECONDS)

        # 查询所有当前状态为 'Active' 且最后签入时间早于阈值的 Beacon
        stale_beacons = db.query(Beacon).filter(
            Beacon.status == 'Active',
            Beacon.last_checkin < stale_time_limit
        ).all()

        if stale_beacons:
            print("-" * 50)
            print(f"MAINTENANCE: Found {len(stale_beacons)} stale beacons.")

            for beacon in stale_beacons:
                # 将状态更新为 'Stale'
                beacon.status = 'Stale'
                db.add(beacon)
                print(f"LOSING: Marking {beacon.id[:8]} as Stale.")


    def get_all_beacons(self, db: Session) -> List[Beacon]:
        """
        获取数据库中所有的 Beacon 会话列表，按最后签入时间倒序排列。
        用于 C2 操作员的控制台显示。
        """
        return db.query(Beacon).order_by(Beacon.last_checkin.desc()).all()