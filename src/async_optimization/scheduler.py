"""
Background Task Scheduler - TDD Implementation
백그라운드 작업 스케줄러 - TDD 구현
"""

import asyncio
import time
from typing import Dict, Any, List, Optional, Callable, Awaitable, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import re

from src.config import get_settings
from src.utils.logger import setup_logger


class TaskStatus(Enum):
    """작업 상태"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ScheduledTask:
    """스케줄된 작업"""
    task_id: str
    name: str
    coro: Callable[[], Awaitable[Any]]
    interval_seconds: Optional[float] = None
    cron_expression: Optional[str] = None
    depends_on: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    failure_count: int = 0
    result: Any = None
    error: Optional[str] = None


class BackgroundScheduler:
    """백그라운드 스케줄러"""
    
    def __init__(self):
        self.tasks: Dict[str, ScheduledTask] = {}
        self.running = False
        self.scheduler_task = None
        self.logger = setup_logger("background_scheduler")
    
    async def schedule_periodic(self, coro: Callable[[], Awaitable[Any]], interval_seconds: float, name: Optional[str] = None) -> str:
        """주기적 작업 스케줄링"""
        task_id = f"periodic_{len(self.tasks)}_{time.time()}"
        task_name = name or f"periodic_task_{task_id}"
        
        task = ScheduledTask(
            task_id=task_id,
            name=task_name,
            coro=coro,
            interval_seconds=interval_seconds,
            next_run=datetime.now() + timedelta(seconds=interval_seconds)
        )
        
        self.tasks[task_id] = task
        self.logger.info(f"Scheduled periodic task: {task_name} (interval: {interval_seconds}s)")
        
        return task_id
    
    async def start(self):
        """스케줄러 시작"""
        if self.running:
            return
        
        self.running = True
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        self.logger.info("Background scheduler started")
    
    async def stop(self):
        """스케줄러 중지"""
        self.running = False
        
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Background scheduler stopped")
    
    async def cancel_task(self, task_id: str):
        """작업 취소"""
        if task_id in self.tasks:
            self.tasks[task_id].status = TaskStatus.CANCELLED
            self.logger.info(f"Task cancelled: {task_id}")
    
    async def _scheduler_loop(self):
        """스케줄러 메인 루프"""
        while self.running:
            now = datetime.now()
            
            for task_id, task in self.tasks.items():
                if (task.status in [TaskStatus.PENDING, TaskStatus.COMPLETED] and
                    task.next_run and now >= task.next_run):
                    
                    # 작업 실행
                    asyncio.create_task(self._execute_task(task))
            
            await asyncio.sleep(0.1)  # 100ms 간격으로 확인
    
    async def _execute_task(self, task: ScheduledTask):
        """작업 실행"""
        task.status = TaskStatus.RUNNING
        task.last_run = datetime.now()
        
        try:
            result = await task.coro()
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.run_count += 1
            
            # 다음 실행 시간 계산
            if task.interval_seconds:
                task.next_run = datetime.now() + timedelta(seconds=task.interval_seconds)
            
            self.logger.debug(f"Task executed successfully: {task.name}")
            
        except Exception as e:
            task.error = str(e)
            task.status = TaskStatus.FAILED
            task.failure_count += 1
            
            self.logger.error(f"Task execution failed: {task.name}, error: {str(e)}")


class CronScheduler:
    """크론 스케줄러"""
    
    def __init__(self):
        self.tasks: Dict[str, ScheduledTask] = {}
        self.running = False
        self.scheduler_task = None
        self.logger = setup_logger("cron_scheduler")
    
    async def schedule_cron(self, coro: Callable[[], Awaitable[Any]], cron_expression: str, name: Optional[str] = None) -> str:
        """크론 표현식으로 작업 스케줄링"""
        task_id = f"cron_{len(self.tasks)}_{time.time()}"
        task_name = name or f"cron_task_{task_id}"
        
        task = ScheduledTask(
            task_id=task_id,
            name=task_name,
            coro=coro,
            cron_expression=cron_expression,
            next_run=self._calculate_next_cron_run(cron_expression)
        )
        
        self.tasks[task_id] = task
        self.logger.info(f"Scheduled cron task: {task_name} ({cron_expression})")
        
        return task_id
    
    def _calculate_next_cron_run(self, cron_expression: str) -> datetime:
        """크론 표현식으로 다음 실행 시간 계산 (간단한 구현)"""
        # 매초 실행 ("* * * * * *")
        if cron_expression == "* * * * * *":
            return datetime.now() + timedelta(seconds=1)
        
        # 기본적으로 1분 후
        return datetime.now() + timedelta(minutes=1)
    
    async def start(self):
        """스케줄러 시작"""
        if self.running:
            return
        
        self.running = True
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        self.logger.info("Cron scheduler started")
    
    async def stop(self):
        """스케줄러 중지"""
        self.running = False
        
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Cron scheduler stopped")
    
    async def _scheduler_loop(self):
        """스케줄러 메인 루프"""
        while self.running:
            now = datetime.now()
            
            for task_id, task in self.tasks.items():
                if (task.status in [TaskStatus.PENDING, TaskStatus.COMPLETED] and
                    task.next_run and now >= task.next_run):
                    
                    # 작업 실행
                    asyncio.create_task(self._execute_task(task))
            
            await asyncio.sleep(0.1)
    
    async def _execute_task(self, task: ScheduledTask):
        """작업 실행"""
        task.status = TaskStatus.RUNNING
        task.last_run = datetime.now()
        
        try:
            result = await task.coro()
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.run_count += 1
            
            # 다음 실행 시간 계산
            if task.cron_expression:
                task.next_run = self._calculate_next_cron_run(task.cron_expression)
            
            self.logger.debug(f"Cron task executed successfully: {task.name}")
            
        except Exception as e:
            task.error = str(e)
            task.status = TaskStatus.FAILED
            task.failure_count += 1
            
            self.logger.error(f"Cron task execution failed: {task.name}, error: {str(e)}")


class DependencyScheduler:
    """의존성 관리 스케줄러"""
    
    def __init__(self):
        self.tasks: Dict[str, ScheduledTask] = {}
        self.running = False
        self.completed_tasks: Set[str] = set()
        self.scheduler_task = None
        self.logger = setup_logger("dependency_scheduler")
    
    async def add_task(self, name: str, coro: Callable[[], Awaitable[Any]], depends_on: Optional[List[str]] = None) -> str:
        """의존성이 있는 작업 추가"""
        task_id = f"dep_{len(self.tasks)}_{time.time()}"
        
        task = ScheduledTask(
            task_id=task_id,
            name=name,
            coro=coro,
            depends_on=depends_on or []
        )
        
        self.tasks[task_id] = task
        self.logger.info(f"Added task with dependencies: {name} (depends on: {depends_on})")
        
        return task_id
    
    async def start(self):
        """스케줄러 시작"""
        if self.running:
            return
        
        self.running = True
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        self.logger.info("Dependency scheduler started")
    
    async def wait_all(self):
        """모든 작업 완료 대기"""
        while any(task.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED] 
                  for task in self.tasks.values()):
            await asyncio.sleep(0.01)
        
        self.running = False
        if self.scheduler_task:
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
    
    async def _scheduler_loop(self):
        """스케줄러 메인 루프"""
        while self.running:
            ready_tasks = []
            
            for task_id, task in self.tasks.items():
                if (task.status == TaskStatus.PENDING and
                    self._are_dependencies_met(task)):
                    ready_tasks.append(task)
            
            # 준비된 작업들 실행
            for task in ready_tasks:
                asyncio.create_task(self._execute_task(task))
            
            await asyncio.sleep(0.01)
    
    def _are_dependencies_met(self, task: ScheduledTask) -> bool:
        """의존성이 충족되었는지 확인"""
        return all(dep_id in self.completed_tasks for dep_id in task.depends_on)
    
    async def _execute_task(self, task: ScheduledTask):
        """작업 실행"""
        task.status = TaskStatus.RUNNING
        task.last_run = datetime.now()
        
        try:
            result = await task.coro()
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.run_count += 1
            
            # 완료된 작업 목록에 추가
            self.completed_tasks.add(task.task_id)
            
            self.logger.debug(f"Dependency task executed successfully: {task.name}")
            
        except Exception as e:
            task.error = str(e)
            task.status = TaskStatus.FAILED
            task.failure_count += 1
            
            self.logger.error(f"Dependency task execution failed: {task.name}, error: {str(e)}")


class RetryableScheduler:
    """재시도 가능한 스케줄러"""
    
    def __init__(self):
        self.logger = setup_logger("retryable_scheduler")
    
    async def schedule_with_retry(self, coro: Callable[[], Awaitable[Any]], max_retries: int, retry_delay: float) -> Any:
        """재시도가 가능한 작업 스케줄링"""
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                result = await coro()
                if attempt > 0:
                    self.logger.info(f"Task succeeded on attempt {attempt + 1}")
                return result
                
            except Exception as e:
                last_exception = e
                self.logger.warning(f"Task failed on attempt {attempt + 1}: {str(e)}")
                
                if attempt < max_retries:
                    await asyncio.sleep(retry_delay)
                else:
                    self.logger.error(f"Task failed after {max_retries + 1} attempts")
                    raise last_exception


class ResourceAwareScheduler:
    """리소스 인식 스케줄러"""
    
    def __init__(self, max_memory_mb: int, max_cpu_percent: int):
        self.max_memory_mb = max_memory_mb
        self.max_cpu_percent = max_cpu_percent
        self.current_memory_usage = 0
        self.current_cpu_usage = 0
        self.peak_memory_usage = 0
        self.peak_cpu_usage = 0
        self.active_tasks = {}
        self.logger = setup_logger("resource_aware_scheduler")
    
    async def schedule_task(self, coro: Callable[[], Awaitable[Any]], memory_mb: int, cpu_percent: int) -> Any:
        """리소스 요구사항을 고려한 작업 스케줄링"""
        # 리소스 확인
        while (self.current_memory_usage + memory_mb > self.max_memory_mb or
               self.current_cpu_usage + cpu_percent > self.max_cpu_percent):
            await asyncio.sleep(0.01)  # 리소스가 확보될 때까지 대기
        
        # 리소스 할당
        task_id = f"resource_task_{time.time()}"
        self.current_memory_usage += memory_mb
        self.current_cpu_usage += cpu_percent
        
        # 피크 사용량 업데이트
        self.peak_memory_usage = max(self.peak_memory_usage, self.current_memory_usage)
        self.peak_cpu_usage = max(self.peak_cpu_usage, self.current_cpu_usage)
        
        self.active_tasks[task_id] = {
            "memory_mb": memory_mb,
            "cpu_percent": cpu_percent
        }
        
        try:
            result = await coro()
            return result
        finally:
            # 리소스 해제
            self.current_memory_usage -= memory_mb
            self.current_cpu_usage -= cpu_percent
            del self.active_tasks[task_id]
    
    def get_peak_memory_usage(self) -> int:
        """피크 메모리 사용량 반환"""
        return self.peak_memory_usage
    
    def get_peak_cpu_usage(self) -> int:
        """피크 CPU 사용량 반환"""
        return self.peak_cpu_usage


# 전역 인스턴스 관리
_schedulers = {}


def get_scheduler(scheduler_type: str, **kwargs):
    """스케줄러 인스턴스 획득"""
    key = f"{scheduler_type}_{hash(tuple(sorted(kwargs.items())))}"
    
    if key not in _schedulers:
        if scheduler_type == "background":
            _schedulers[key] = BackgroundScheduler()
        elif scheduler_type == "cron":
            _schedulers[key] = CronScheduler()
        elif scheduler_type == "dependency":
            _schedulers[key] = DependencyScheduler()
        elif scheduler_type == "retryable":
            _schedulers[key] = RetryableScheduler()
        elif scheduler_type == "resource_aware":
            _schedulers[key] = ResourceAwareScheduler(**kwargs)
        else:
            raise ValueError(f"Unknown scheduler type: {scheduler_type}")
    
    return _schedulers[key]