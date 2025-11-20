from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship


# 基类
Base = declarative_base()


class Beacon(Base):
    """
    会话模型
    存储所有beacon的植息。
    """
    __tablename__ = 'beacons'

    # Beacon ID 是唯一标识符，SHA256 的 Hex 字符串长度是 64 个字符
    id = Column(String(64), primary_key=True)

    # 核心信息
    ip_address = Column(String(45), nullable=False)
    hostname = Column(String(255))
    username = Column(String(255))
    os_info = Column(String(255))
    is_admin = Column(Boolean, default=False)

    # 状态和时间
    status = Column(String(50), default='Active', nullable=False)  # Active, Stale, Lost三种状态
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_checkin = Column(DateTime, default=datetime.utcnow)


    tasks = relationship("Task", back_populates="beacon")

    # 输出调试的模样
    def __repr__(self):
        return f"<Beacon(id='{self.id}', ip='{self.ip_address}', user='{self.username}')>"


class Task(Base):
    """
    任务模型
    存储操作员创建的待执行命令。
    """
    __tablename__ = 'tasks'

    task_id = Column(Integer, primary_key=True)

    # 任务分配
    beacon_id = Column(String(36), ForeignKey('beacons.id'), nullable=False)

    # 任务内容
    command = Column(String(255), nullable=False)
    arguments = Column(Text)  # 命令参数

    # 状态
    status = Column(String(50), default='PENDING', nullable=False)  # PENDING, ASSIGNED, COMPLETED, FAILED4种状态

    # 时间和关系
    created_at = Column(DateTime, default=datetime.utcnow)
    assigned_at = Column(DateTime)

    # 关系
    beacon = relationship("Beacon", back_populates="tasks")
    output = relationship("TaskOutput", back_populates="task", uselist=False)  # 任务和输出是一对一关系

    # 依旧是调试消息
    def __repr__(self):
        return f"<Task(id={self.task_id}, status='{self.status}', cmd='{self.command[:20]}')>"


class TaskOutput(Base):
    """
    任务回显模型
    存储 Beacon 执行任务后返回的结果。
    """
    __tablename__ = 'task_outputs'

    # 关联的任务
    task_id = Column(Integer, ForeignKey('tasks.task_id'), primary_key=True, nullable=False)

    # 结果内容
    output_data = Column(Text, nullable=False)  # 原始回显数据

    # 时间戳
    received_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    task = relationship("Task", back_populates="output")

    # 依旧是调试消息
    def __repr__(self):
        return f"<TaskOutput(task_id={self.task_id}, len={len(self.output_data)})>"