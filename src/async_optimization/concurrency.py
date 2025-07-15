"""
Concurrency Control System - TDD Implementation
동시성 제어 시스템 - TDD 구현
"""

import asyncio
import time
import heapq
from typing import Dict, Any, List, Optional, Callable, Awaitable
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass

from src.config import get_settings
from src.utils.logger import setup_logger


class CircuitBreakerState(Enum):
    """회로차단기 상태"""
    CLOSED = "CLOSED"
    OPEN = "OPEN" 
    HALF_OPEN = "HALF_OPEN"


@dataclass
class TaskItem:
    """우선순위 작업 아이템"""
    priority: int
    task_id: str
    coro: Callable[[], Awaitable[Any]]
    future: asyncio.Future
    created_at: datetime

    def __lt__(self, other):
        # 높은 우선순위가 먼저 실행되도록 (heapq는 최소힙)
        return self.priority > other.priority


class ConcurrencyController:
    """기본 동시성 제어기"""
    
    def __init__(self, max_concurrent: int):
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.logger = setup_logger("concurrency_controller")
    
    def acquire(self):
        """세마포어 획득"""
        return self
    
    async def __aenter__(self):
        await self.semaphore.acquire()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.semaphore.release()


class AdaptiveConcurrencyController:
    """적응형 동시성 제어기"""
    
    def __init__(self, initial_limit: int, min_limit: int, max_limit: int):
        self.initial_limit = initial_limit
        self.min_limit = min_limit
        self.max_limit = max_limit
        self.current_limit = initial_limit
        self.success_count = 0
        self.failure_count = 0
        self.logger = setup_logger("adaptive_concurrency")
        self._lock = asyncio.Lock()
    
    async def record_success(self, response_time: float):
        """성공 기록 및 동시성 조정"""
        async with self._lock:
            self.success_count += 1
            
            # 빠른 응답 시 동시성 증가
            if response_time < 0.2 and self.success_count % 5 == 0:
                if self.current_limit < self.max_limit:
                    self.current_limit += 1
                    self.logger.debug(f"Increased concurrency limit to {self.current_limit}")
    
    async def record_failure(self):
        """실패 기록 및 동시성 조정"""
        async with self._lock:
            self.failure_count += 1
            
            # 실패 시 동시성 감소
            if self.failure_count % 3 == 0:
                if self.current_limit > self.min_limit:
                    self.current_limit -= 1
                    self.logger.debug(f"Decreased concurrency limit to {self.current_limit}")
    
    def get_current_limit(self) -> int:
        """현재 동시성 한계 반환"""
        return self.current_limit


class PriorityTaskScheduler:
    """우선순위 기반 작업 스케줄러"""
    
    def __init__(self, max_concurrent: int):
        self.max_concurrent = max_concurrent
        self.active_tasks = 0
        self.task_queue = []
        self.running_tasks = set()
        self.completed_tasks = set()
        self.logger = setup_logger("priority_scheduler")
        self._queue_lock = asyncio.Lock()
        self._scheduler_task = None
        self._running = False
    
    async def schedule_task(self, coro: Callable[[], Awaitable[Any]], priority: int) -> asyncio.Future:
        """작업 스케줄링"""
        task_id = f"task_{len(self.task_queue)}_{time.time()}"
        future = asyncio.Future()
        
        task_item = TaskItem(
            priority=priority,
            task_id=task_id,
            coro=coro,
            future=future,
            created_at=datetime.now()
        )
        
        async with self._queue_lock:
            heapq.heappush(self.task_queue, task_item)
        
        # 스케줄러 시작
        if not self._running:
            await self._start_scheduler()
        
        return future
    
    async def _start_scheduler(self):
        """스케줄러 시작"""
        if self._scheduler_task is None:
            self._running = True
            self._scheduler_task = asyncio.create_task(self._scheduler_loop())
    
    async def _scheduler_loop(self):
        """스케줄러 메인 루프"""
        while self._running or self.task_queue or self.running_tasks:
            async with self._queue_lock:
                # 실행 가능한 작업이 있고 동시성 한계 내인 경우
                if (self.task_queue and 
                    self.active_tasks < self.max_concurrent):
                    
                    task_item = heapq.heappop(self.task_queue)
                    self.active_tasks += 1
                    self.running_tasks.add(task_item.task_id)
                    
                    # 작업 실행
                    asyncio.create_task(self._execute_task(task_item))
            
            await asyncio.sleep(0.01)  # 작은 지연
    
    async def _execute_task(self, task_item: TaskItem):
        """작업 실행"""
        try:
            result = await task_item.coro()
            task_item.future.set_result(result)
        except Exception as e:
            task_item.future.set_exception(e)
        finally:
            async with self._queue_lock:
                self.active_tasks -= 1
                self.running_tasks.discard(task_item.task_id)
                self.completed_tasks.add(task_item.task_id)
    
    async def wait_all(self):
        """모든 작업 완료 대기"""
        while self.task_queue or self.running_tasks:
            await asyncio.sleep(0.01)
        
        self._running = False
        if self._scheduler_task:
            await self._scheduler_task
            self._scheduler_task = None


class CircuitBreaker:
    """회로차단기 패턴"""
    
    def __init__(self, failure_threshold: int, timeout_seconds: float, recovery_timeout: float):
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.recovery_timeout = recovery_timeout
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED
        self.logger = setup_logger("circuit_breaker")
    
    async def call(self, func: Callable[[], Awaitable[Any]]) -> Any:
        """회로차단기를 통한 함수 호출"""
        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitBreakerState.HALF_OPEN
                self.logger.info("Circuit breaker moved to HALF_OPEN state")
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            # 타임아웃 적용
            result = await asyncio.wait_for(func(), timeout=self.timeout_seconds)
            self._on_success()
            return result
            
        except Exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """리셋 시도 여부 확인"""
        if self.last_failure_time is None:
            return False
        
        return (time.time() - self.last_failure_time) > self.recovery_timeout
    
    def _on_success(self):
        """성공 시 처리"""
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED
    
    def _on_failure(self):
        """실패 시 처리"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            self.logger.warning(f"Circuit breaker opened after {self.failure_count} failures")


# 전역 인스턴스 관리
_concurrency_controllers = {}
_adaptive_controllers = {}
_priority_schedulers = {}
_circuit_breakers = {}


def get_concurrency_controller(name: str, max_concurrent: int) -> ConcurrencyController:
    """동시성 제어기 인스턴스 획득"""
    if name not in _concurrency_controllers:
        _concurrency_controllers[name] = ConcurrencyController(max_concurrent)
    return _concurrency_controllers[name]


def get_adaptive_controller(name: str, initial_limit: int, min_limit: int, max_limit: int) -> AdaptiveConcurrencyController:
    """적응형 동시성 제어기 인스턴스 획득"""
    if name not in _adaptive_controllers:
        _adaptive_controllers[name] = AdaptiveConcurrencyController(initial_limit, min_limit, max_limit)
    return _adaptive_controllers[name]


def get_priority_scheduler(name: str, max_concurrent: int) -> PriorityTaskScheduler:
    """우선순위 스케줄러 인스턴스 획득"""
    if name not in _priority_schedulers:
        _priority_schedulers[name] = PriorityTaskScheduler(max_concurrent)
    return _priority_schedulers[name]


def get_circuit_breaker(name: str, failure_threshold: int, timeout_seconds: float, recovery_timeout: float) -> CircuitBreaker:
    """회로차단기 인스턴스 획득"""
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(failure_threshold, timeout_seconds, recovery_timeout)
    return _circuit_breakers[name]