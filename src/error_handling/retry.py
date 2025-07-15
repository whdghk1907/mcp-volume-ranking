"""
Retry Logic - TDD Implementation
재시도 로직 - TDD 구현
"""

import asyncio
import time
import random
from typing import Callable, Awaitable, Any, Optional, Dict, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import math

from src.utils.logger import setup_logger


class RetryStrategy(Enum):
    """재시도 전략"""
    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    FIBONACCI = "fibonacci"
    ADAPTIVE = "adaptive"


class CircuitBreakerState(Enum):
    """회로차단기 상태"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class RetryConfig:
    """재시도 설정"""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    jitter_range: tuple = (0.0, 0.1)


class ExponentialBackoffRetry:
    """지수 백오프 재시도"""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, 
                 max_delay: float = 60.0, exponential_base: float = 2.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.logger = setup_logger("exponential_backoff_retry")
        
        # 통계
        self.total_attempts = 0
        self.successful_attempts = 0
        self.failed_attempts = 0
    
    async def execute(self, operation: Callable[[], Awaitable[Any]]) -> Any:
        """작업 실행"""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            self.total_attempts += 1
            
            try:
                result = await operation()
                self.successful_attempts += 1
                
                if attempt > 0:
                    self.logger.info(f"Operation succeeded on attempt {attempt + 1}")
                
                return result
                
            except Exception as e:
                last_exception = e
                self.failed_attempts += 1
                
                if attempt < self.max_retries:
                    delay = self._calculate_delay(attempt)
                    self.logger.warning(
                        f"Operation failed on attempt {attempt + 1}, "
                        f"retrying in {delay:.2f}s: {str(e)}"
                    )
                    await asyncio.sleep(delay)
                else:
                    self.logger.error(
                        f"Operation failed after {self.max_retries + 1} attempts: {str(e)}"
                    )
        
        raise last_exception
    
    def _calculate_delay(self, attempt: int) -> float:
        """지연 시간 계산"""
        # 지수 백오프: base_delay * (exponential_base ^ attempt)
        delay = self.base_delay * (self.exponential_base ** attempt)
        
        # 최대 지연 시간 제한
        delay = min(delay, self.max_delay)
        
        # 지터 추가 (동시 재시도 충돌 방지)
        jitter = random.uniform(0, delay * 0.1)
        
        return delay + jitter
    
    def get_stats(self) -> Dict[str, Any]:
        """통계 반환"""
        success_rate = (self.successful_attempts / self.total_attempts * 100 
                       if self.total_attempts > 0 else 0)
        
        return {
            "total_attempts": self.total_attempts,
            "successful_attempts": self.successful_attempts,
            "failed_attempts": self.failed_attempts,
            "success_rate": round(success_rate, 2)
        }


class CircuitBreakerRetry:
    """회로차단기 재시도"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0, 
                 half_open_requests: int = 3):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_requests = half_open_requests
        
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.half_open_attempts = 0
        
        self.logger = setup_logger("circuit_breaker_retry")
    
    async def execute(self, operation: Callable[[], Awaitable[Any]]) -> Any:
        """작업 실행"""
        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                self._move_to_half_open()
            else:
                raise Exception("Circuit breaker is open")
        
        try:
            result = await operation()
            self._record_success()
            return result
            
        except Exception as e:
            self._record_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """리셋 시도 여부"""
        if self.last_failure_time is None:
            return False
        
        elapsed = time.time() - self.last_failure_time
        return elapsed >= self.recovery_timeout
    
    def _move_to_half_open(self):
        """HALF_OPEN 상태로 전환"""
        self.state = CircuitBreakerState.HALF_OPEN
        self.half_open_attempts = 0
        self.logger.info("Circuit breaker moved to HALF_OPEN state")
    
    def _record_success(self):
        """성공 기록"""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.half_open_attempts += 1
            if self.half_open_attempts >= self.half_open_requests:
                self._move_to_closed()
        elif self.state == CircuitBreakerState.CLOSED:
            self.failure_count = 0
    
    def _record_failure(self):
        """실패 기록"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            self._move_to_open()
        elif (self.state == CircuitBreakerState.CLOSED and 
              self.failure_count >= self.failure_threshold):
            self._move_to_open()
    
    def _move_to_closed(self):
        """CLOSED 상태로 전환"""
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.half_open_attempts = 0
        self.logger.info("Circuit breaker moved to CLOSED state")
    
    def _move_to_open(self):
        """OPEN 상태로 전환"""
        self.state = CircuitBreakerState.OPEN
        self.half_open_attempts = 0
        self.logger.warning(
            f"Circuit breaker moved to OPEN state after {self.failure_count} failures"
        )
    
    @property
    def state_name(self) -> str:
        """상태 이름 반환"""
        return self.state.value


class AdaptiveRetry:
    """적응형 재시도"""
    
    def __init__(self):
        self.success_history = []
        self.failure_history = []
        self.current_strategy = "moderate"
        self.window_size = 50  # 최근 50개 요청 기준
        
        self.strategies = {
            "aggressive": {"max_retries": 5, "base_delay": 0.5, "exponential_base": 1.5},
            "moderate": {"max_retries": 3, "base_delay": 1.0, "exponential_base": 2.0},
            "conservative": {"max_retries": 2, "base_delay": 2.0, "exponential_base": 2.5}
        }
        
        self.logger = setup_logger("adaptive_retry")
    
    async def execute(self, operation: Callable[[], Awaitable[Any]]) -> Any:
        """작업 실행"""
        strategy_config = self.strategies[self.current_strategy]
        
        retry = ExponentialBackoffRetry(
            max_retries=strategy_config["max_retries"],
            base_delay=strategy_config["base_delay"],
            exponential_base=strategy_config["exponential_base"]
        )
        
        try:
            result = await retry.execute(operation)
            self._record_success()
            return result
        except Exception as e:
            self._record_failure()
            raise
    
    def _record_success(self):
        """성공 기록"""
        self.success_history.append(time.time())
        self._trim_history()
        self._update_strategy()
    
    def _record_failure(self):
        """실패 기록"""
        self.failure_history.append(time.time())
        self._trim_history()
        self._update_strategy()
    
    def _trim_history(self):
        """기록 정리"""
        current_time = time.time()
        window_start = current_time - 300  # 5분 윈도우
        
        self.success_history = [t for t in self.success_history if t > window_start]
        self.failure_history = [t for t in self.failure_history if t > window_start]
    
    def _update_strategy(self):
        """전략 업데이트"""
        total_requests = len(self.success_history) + len(self.failure_history)
        
        if total_requests < 10:
            return
        
        success_rate = len(self.success_history) / total_requests
        
        # 성공률에 따른 전략 조정
        if success_rate > 0.9:
            new_strategy = "aggressive"
        elif success_rate > 0.7:
            new_strategy = "moderate"
        else:
            new_strategy = "conservative"
        
        if new_strategy != self.current_strategy:
            self.logger.info(f"Strategy changed from {self.current_strategy} to {new_strategy}")
            self.current_strategy = new_strategy
    
    def get_current_strategy(self) -> str:
        """현재 전략 반환"""
        return self.current_strategy
    
    def get_success_rate(self) -> float:
        """성공률 반환"""
        total = len(self.success_history) + len(self.failure_history)
        if total == 0:
            return 0.0
        return len(self.success_history) / total


class RetryWithJitter:
    """지터를 포함한 재시도"""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, 
                 jitter_range: tuple = (0.0, 0.1)):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.jitter_range = jitter_range
        self.logger = setup_logger("retry_with_jitter")
    
    async def execute(self, operation: Callable[[], Awaitable[Any]]) -> Any:
        """작업 실행"""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return await operation()
            except Exception as e:
                last_exception = e
                
                if attempt < self.max_retries:
                    delay = self._calculate_jittered_delay(attempt)
                    await asyncio.sleep(delay)
                    
        raise last_exception
    
    def _calculate_jittered_delay(self, attempt: int) -> float:
        """지터가 포함된 지연 시간 계산"""
        # 기본 지연 (선형 증가)
        base = self.base_delay * (attempt + 1)
        
        # 지터 추가
        jitter_min, jitter_max = self.jitter_range
        jitter = random.uniform(jitter_min, jitter_max)
        
        return base + jitter


class FibonacciRetry:
    """피보나치 재시도"""
    
    def __init__(self, max_retries: int = 8, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.fibonacci_sequence = self._generate_fibonacci(max_retries + 1)
        self.logger = setup_logger("fibonacci_retry")
    
    def _generate_fibonacci(self, n: int) -> List[int]:
        """피보나치 수열 생성"""
        if n <= 0:
            return []
        elif n == 1:
            return [1]
        elif n == 2:
            return [1, 1]
        
        fib = [1, 1]
        for i in range(2, n):
            fib.append(fib[i-1] + fib[i-2])
        
        return fib
    
    async def execute(self, operation: Callable[[], Awaitable[Any]]) -> Any:
        """작업 실행"""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return await operation()
            except Exception as e:
                last_exception = e
                
                if attempt < self.max_retries:
                    delay = self._calculate_fibonacci_delay(attempt)
                    self.logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay:.2f}s")
                    await asyncio.sleep(delay)
        
        raise last_exception
    
    def _calculate_fibonacci_delay(self, attempt: int) -> float:
        """피보나치 지연 시간 계산"""
        fib_multiplier = self.fibonacci_sequence[min(attempt, len(self.fibonacci_sequence) - 1)]
        return self.base_delay * fib_multiplier


class RetryPool:
    """재시도 풀"""
    
    def __init__(self, pool_size: int = 10):
        self.pool_size = pool_size
        self.active_retries = {}
        self.retry_stats = {}
        self.logger = setup_logger("retry_pool")
        self._lock = asyncio.Lock()
    
    async def execute_with_retry(self, operation_id: str, operation: Callable[[], Awaitable[Any]], 
                               retry_config: Optional[RetryConfig] = None) -> Any:
        """재시도와 함께 작업 실행"""
        config = retry_config or RetryConfig()
        
        async with self._lock:
            if len(self.active_retries) >= self.pool_size:
                raise Exception("Retry pool is full")
            
            retry = ExponentialBackoffRetry(
                max_retries=config.max_retries,
                base_delay=config.base_delay,
                max_delay=config.max_delay,
                exponential_base=config.exponential_base
            )
            
            self.active_retries[operation_id] = retry
        
        try:
            result = await retry.execute(operation)
            
            # 통계 업데이트
            stats = retry.get_stats()
            self.retry_stats[operation_id] = {
                **stats,
                "completed_at": datetime.now(),
                "result": "success"
            }
            
            return result
            
        except Exception as e:
            # 실패 통계 업데이트
            stats = retry.get_stats()
            self.retry_stats[operation_id] = {
                **stats,
                "completed_at": datetime.now(),
                "result": "failed",
                "error": str(e)
            }
            raise
        finally:
            async with self._lock:
                self.active_retries.pop(operation_id, None)
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """풀 통계 반환"""
        return {
            "pool_size": self.pool_size,
            "active_retries": len(self.active_retries),
            "total_operations": len(self.retry_stats),
            "success_rate": self._calculate_overall_success_rate()
        }
    
    def _calculate_overall_success_rate(self) -> float:
        """전체 성공률 계산"""
        if not self.retry_stats:
            return 0.0
        
        successful = sum(1 for stats in self.retry_stats.values() 
                        if stats["result"] == "success")
        
        return successful / len(self.retry_stats) * 100