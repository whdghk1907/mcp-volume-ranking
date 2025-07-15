"""
Error Recovery System - TDD Implementation
오류 복구 시스템 - TDD 구현
"""

import asyncio
import json
import time
from typing import Dict, Any, List, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import pickle
import uuid
import copy

from src.utils.logger import setup_logger


class TransactionState(Enum):
    """트랜잭션 상태"""
    ACTIVE = "active"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


@dataclass
class Checkpoint:
    """체크포인트"""
    id: str
    state: Dict[str, Any]
    created_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Operation:
    """작업"""
    id: str
    operation_type: str
    data: Dict[str, Any]
    executed_at: Optional[datetime] = None
    rollback_data: Optional[Dict[str, Any]] = None


class StateRecoveryManager:
    """상태 복구 관리자"""
    
    def __init__(self, max_checkpoints: int = 100):
        self.max_checkpoints = max_checkpoints
        self.checkpoints: Dict[str, Checkpoint] = {}
        self.logger = setup_logger("state_recovery_manager")
    
    async def create_checkpoint(self, state: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> str:
        """체크포인트 생성"""
        checkpoint_id = str(uuid.uuid4())
        
        # 깊은 복사로 상태 저장
        checkpoint = Checkpoint(
            id=checkpoint_id,
            state=copy.deepcopy(state),
            created_at=datetime.now(),
            metadata=metadata or {}
        )
        
        self.checkpoints[checkpoint_id] = checkpoint
        
        # 오래된 체크포인트 정리
        await self._cleanup_old_checkpoints()
        
        self.logger.info(f"Created checkpoint: {checkpoint_id}")
        return checkpoint_id
    
    async def recover_from_checkpoint(self, checkpoint_id: str) -> Dict[str, Any]:
        """체크포인트에서 복구"""
        if checkpoint_id not in self.checkpoints:
            raise ValueError(f"Checkpoint not found: {checkpoint_id}")
        
        checkpoint = self.checkpoints[checkpoint_id]
        
        # 깊은 복사로 상태 반환
        recovered_state = copy.deepcopy(checkpoint.state)
        
        self.logger.info(f"Recovered from checkpoint: {checkpoint_id}")
        return recovered_state
    
    async def list_checkpoints(self) -> List[Dict[str, Any]]:
        """체크포인트 목록"""
        return [
            {
                "id": cp.id,
                "created_at": cp.created_at,
                "metadata": cp.metadata,
                "state_keys": list(cp.state.keys())
            }
            for cp in sorted(self.checkpoints.values(), 
                           key=lambda x: x.created_at, reverse=True)
        ]
    
    async def delete_checkpoint(self, checkpoint_id: str):
        """체크포인트 삭제"""
        if checkpoint_id in self.checkpoints:
            del self.checkpoints[checkpoint_id]
            self.logger.info(f"Deleted checkpoint: {checkpoint_id}")
    
    async def _cleanup_old_checkpoints(self):
        """오래된 체크포인트 정리"""
        if len(self.checkpoints) <= self.max_checkpoints:
            return
        
        # 생성 시간 기준으로 정렬
        sorted_checkpoints = sorted(
            self.checkpoints.items(),
            key=lambda x: x[1].created_at
        )
        
        # 오래된 것부터 삭제
        to_delete = len(self.checkpoints) - self.max_checkpoints
        for i in range(to_delete):
            checkpoint_id = sorted_checkpoints[i][0]
            del self.checkpoints[checkpoint_id]
        
        self.logger.debug(f"Cleaned up {to_delete} old checkpoints")


class TransactionManager:
    """트랜잭션 관리자"""
    
    def __init__(self):
        self.logger = setup_logger("transaction_manager")
    
    async def begin_transaction(self) -> 'Transaction':
        """트랜잭션 시작"""
        transaction = Transaction()
        await transaction.begin()
        return transaction


class Transaction:
    """트랜잭션"""
    
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.state = TransactionState.ACTIVE
        self.operations: List[Operation] = []
        self.executed_operations: List[Operation] = []
        self.rollback_stack: List[Callable[[], Awaitable[None]]] = []
        self.created_at = datetime.now()
        self.logger = setup_logger(f"transaction_{self.id[:8]}")
    
    async def begin(self):
        """트랜잭션 시작"""
        self.state = TransactionState.ACTIVE
        self.logger.info(f"Transaction {self.id} started")
    
    async def execute(self, operation_description: str, 
                     operation_func: Optional[Callable[[], Awaitable[Any]]] = None,
                     rollback_func: Optional[Callable[[], Awaitable[None]]] = None):
        """작업 실행"""
        if self.state != TransactionState.ACTIVE:
            raise RuntimeError(f"Transaction is not active: {self.state}")
        
        operation = Operation(
            id=str(uuid.uuid4()),
            operation_type="execute",
            data={"description": operation_description},
            executed_at=datetime.now()
        )
        
        try:
            # 작업 실행
            if operation_func:
                result = await operation_func()
                operation.data["result"] = str(result)
            
            # 실행된 작업 목록에 추가
            self.executed_operations.append(operation)
            
            # 롤백 함수 스택에 추가
            if rollback_func:
                self.rollback_stack.append(rollback_func)
            
            self.logger.debug(f"Executed operation: {operation_description}")
            
        except Exception as e:
            operation.data["error"] = str(e)
            self.logger.error(f"Operation failed: {operation_description} - {str(e)}")
            raise
    
    async def commit(self):
        """트랜잭션 커밋"""
        if self.state != TransactionState.ACTIVE:
            raise RuntimeError(f"Cannot commit transaction in state: {self.state}")
        
        self.state = TransactionState.COMMITTED
        
        # 롤백 스택 정리 (커밋되었으므로 롤백 불필요)
        self.rollback_stack.clear()
        
        self.logger.info(f"Transaction {self.id} committed with {len(self.executed_operations)} operations")
    
    async def rollback(self):
        """트랜잭션 롤백"""
        if self.state == TransactionState.ROLLED_BACK:
            return  # 이미 롤백됨
        
        if self.state == TransactionState.COMMITTED:
            raise RuntimeError("Cannot rollback committed transaction")
        
        # 역순으로 롤백 실행
        for rollback_func in reversed(self.rollback_stack):
            try:
                await rollback_func()
            except Exception as e:
                self.logger.error(f"Rollback operation failed: {str(e)}")
        
        self.state = TransactionState.ROLLED_BACK
        
        # 실행된 작업 목록 정리
        self.executed_operations.clear()
        self.rollback_stack.clear()
        
        self.logger.info(f"Transaction {self.id} rolled back")


class PartialFailureRecovery:
    """부분 실패 복구"""
    
    def __init__(self):
        self.logger = setup_logger("partial_failure_recovery")
    
    async def execute_with_partial_recovery(
        self, 
        tasks: List[Dict[str, Any]], 
        task_executor: Callable[[Dict[str, Any]], Awaitable[Any]]
    ) -> Dict[str, Any]:
        """부분 복구와 함께 작업 실행"""
        successful_tasks = []
        failed_tasks = []
        results = []
        
        # 모든 작업을 병렬로 실행
        task_futures = []
        for i, task in enumerate(tasks):
            future = asyncio.create_task(self._execute_single_task(task, task_executor))
            task_futures.append((i, task, future))
        
        # 결과 수집
        for i, task, future in task_futures:
            try:
                result = await future
                successful_tasks.append(task)
                results.append({"task_id": task.get("id", i), "result": result, "status": "success"})
            except Exception as e:
                failed_tasks.append(task)
                results.append({"task_id": task.get("id", i), "error": str(e), "status": "failed"})
        
        # 실패한 작업에 대한 복구 시도
        recovery_attempted = False
        if failed_tasks:
            recovery_attempted = True
            await self._attempt_recovery(failed_tasks, task_executor)
        
        summary = {
            "total_tasks": len(tasks),
            "successful": len(successful_tasks),
            "failed": len(failed_tasks),
            "success_rate": len(successful_tasks) / len(tasks) * 100 if tasks else 0,
            "successful_tasks": successful_tasks,
            "failed_tasks": failed_tasks,
            "recovery_attempted": recovery_attempted,
            "results": results
        }
        
        self.logger.info(
            f"Partial recovery completed: {len(successful_tasks)}/{len(tasks)} successful, "
            f"recovery_attempted: {recovery_attempted}"
        )
        
        return summary
    
    async def _execute_single_task(self, task: Dict[str, Any], executor: Callable) -> Any:
        """단일 작업 실행"""
        try:
            return await executor(task)
        except Exception as e:
            self.logger.warning(f"Task {task.get('id', 'unknown')} failed: {str(e)}")
            raise
    
    async def _attempt_recovery(self, failed_tasks: List[Dict[str, Any]], 
                               executor: Callable) -> List[Dict[str, Any]]:
        """복구 시도"""
        recovered_tasks = []
        
        for task in failed_tasks:
            try:
                # 간단한 복구 전략: 한 번 더 시도
                await asyncio.sleep(0.1)  # 짧은 지연 후 재시도
                result = await executor(task)
                
                recovered_tasks.append(task)
                self.logger.info(f"Task {task.get('id', 'unknown')} recovered successfully")
                
            except Exception as e:
                self.logger.error(f"Recovery failed for task {task.get('id', 'unknown')}: {str(e)}")
        
        return recovered_tasks


class CircuitBreakerRecovery:
    """회로차단기 복구"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.is_open = False
        self.logger = setup_logger("circuit_breaker_recovery")
    
    async def execute_with_recovery(self, operation: Callable[[], Awaitable[Any]]) -> Any:
        """복구 기능이 있는 실행"""
        if self.is_open:
            if await self._should_attempt_recovery():
                return await self._attempt_recovery(operation)
            else:
                raise Exception("Circuit breaker is open, operation blocked")
        
        try:
            result = await operation()
            await self._record_success()
            return result
        except Exception as e:
            await self._record_failure()
            raise
    
    async def _should_attempt_recovery(self) -> bool:
        """복구 시도 여부 판단"""
        if self.last_failure_time is None:
            return True
        
        elapsed = time.time() - self.last_failure_time
        return elapsed >= self.recovery_timeout
    
    async def _attempt_recovery(self, operation: Callable[[], Awaitable[Any]]) -> Any:
        """복구 시도"""
        self.logger.info("Attempting circuit breaker recovery")
        
        try:
            # 테스트 요청 실행
            result = await operation()
            
            # 성공 시 회로 닫기
            await self._reset_circuit()
            return result
            
        except Exception as e:
            # 실패 시 회로 다시 열기
            await self._record_failure()
            raise
    
    async def _record_success(self):
        """성공 기록"""
        self.failure_count = 0
        self.is_open = False
    
    async def _record_failure(self):
        """실패 기록"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.is_open = True
            self.logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
    
    async def _reset_circuit(self):
        """회로 리셋"""
        self.failure_count = 0
        self.is_open = False
        self.last_failure_time = None
        self.logger.info("Circuit breaker reset successfully")


class HealthCheckRecovery:
    """헬스체크 기반 복구"""
    
    def __init__(self, check_interval: float = 30.0):
        self.check_interval = check_interval
        self.health_checks: Dict[str, Callable[[], Awaitable[bool]]] = {}
        self.health_status: Dict[str, bool] = {}
        self.last_check_time: Dict[str, float] = {}
        self.recovery_actions: Dict[str, Callable[[], Awaitable[None]]] = {}
        self.running = False
        self.logger = setup_logger("health_check_recovery")
    
    def add_health_check(self, name: str, check_func: Callable[[], Awaitable[bool]], 
                        recovery_func: Optional[Callable[[], Awaitable[None]]] = None):
        """헬스체크 추가"""
        self.health_checks[name] = check_func
        self.health_status[name] = True  # 기본값: 건강함
        self.last_check_time[name] = 0
        
        if recovery_func:
            self.recovery_actions[name] = recovery_func
        
        self.logger.info(f"Added health check: {name}")
    
    async def start_monitoring(self):
        """모니터링 시작"""
        self.running = True
        self.logger.info("Health check monitoring started")
        
        while self.running:
            await self._perform_health_checks()
            await asyncio.sleep(self.check_interval)
    
    async def stop_monitoring(self):
        """모니터링 중지"""
        self.running = False
        self.logger.info("Health check monitoring stopped")
    
    async def _perform_health_checks(self):
        """헬스체크 수행"""
        current_time = time.time()
        
        for name, check_func in self.health_checks.items():
            last_check = self.last_check_time.get(name, 0)
            
            if current_time - last_check >= self.check_interval:
                try:
                    is_healthy = await check_func()
                    previous_status = self.health_status.get(name, True)
                    
                    self.health_status[name] = is_healthy
                    self.last_check_time[name] = current_time
                    
                    # 상태 변화 감지
                    if previous_status and not is_healthy:
                        self.logger.warning(f"Health check failed: {name}")
                        await self._trigger_recovery(name)
                    elif not previous_status and is_healthy:
                        self.logger.info(f"Health check recovered: {name}")
                
                except Exception as e:
                    self.logger.error(f"Health check error for {name}: {str(e)}")
                    self.health_status[name] = False
                    await self._trigger_recovery(name)
    
    async def _trigger_recovery(self, name: str):
        """복구 액션 트리거"""
        if name in self.recovery_actions:
            try:
                await self.recovery_actions[name]()
                self.logger.info(f"Recovery action executed for: {name}")
            except Exception as e:
                self.logger.error(f"Recovery action failed for {name}: {str(e)}")
    
    def get_health_status(self) -> Dict[str, Any]:
        """헬스 상태 반환"""
        overall_healthy = all(self.health_status.values()) if self.health_status else True
        
        return {
            "overall_healthy": overall_healthy,
            "services": dict(self.health_status),
            "last_check_times": dict(self.last_check_time),
            "total_services": len(self.health_checks)
        }