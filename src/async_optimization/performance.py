"""
Performance Optimization System - TDD Implementation
성능 최적화 시스템 - TDD 구현
"""

import asyncio
import time
from typing import Dict, Any, List, Optional, Callable, Awaitable, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import deque
import weakref

from src.config import get_settings
from src.utils.logger import setup_logger


@dataclass
class ConnectionStats:
    """연결 통계"""
    active_connections: int
    max_connections: int
    total_created: int
    total_closed: int
    avg_usage_time: float


class MockConnection:
    """Mock 연결 객체"""
    
    def __init__(self, connection_id: str):
        self.connection_id = connection_id
        self.created_at = time.time()
        self.last_used = time.time()
        self.usage_count = 0
        self.is_active = True
    
    async def execute(self, query: str) -> Any:
        """Mock 쿼리 실행"""
        self.last_used = time.time()
        self.usage_count += 1
        await asyncio.sleep(0.01)  # 시뮬레이션
        return f"result_for_{query}"
    
    async def close(self):
        """연결 종료"""
        self.is_active = False


class ConnectionPool:
    """연결 풀"""
    
    def __init__(self, max_connections: int, min_connections: int):
        self.max_connections = max_connections
        self.min_connections = min_connections
        self.available_connections = asyncio.Queue()
        self.active_connections = set()
        self.total_created = 0
        self.total_closed = 0
        self.connection_usage_times = deque(maxlen=100)
        self.logger = setup_logger("connection_pool")
    
    async def initialize(self):
        """풀 초기화"""
        for i in range(self.min_connections):
            connection = await self._create_connection()
            await self.available_connections.put(connection)
        
        self.logger.info(f"Connection pool initialized with {self.min_connections} connections")
    
    async def _create_connection(self) -> MockConnection:
        """새 연결 생성"""
        connection_id = f"conn_{self.total_created}"
        self.total_created += 1
        return MockConnection(connection_id)
    
    async def acquire(self):
        """연결 획득"""
        return ConnectionContextManager(self)
    
    async def _acquire_connection(self) -> MockConnection:
        """내부 연결 획득"""
        try:
            # 사용 가능한 연결이 있으면 반환
            connection = self.available_connections.get_nowait()
            self.active_connections.add(connection)
            return connection
        except asyncio.QueueEmpty:
            # 새 연결 생성 (최대 개수 내에서)
            if len(self.active_connections) < self.max_connections:
                connection = await self._create_connection()
                self.active_connections.add(connection)
                return connection
            else:
                # 대기
                connection = await self.available_connections.get()
                self.active_connections.add(connection)
                return connection
    
    async def _release_connection(self, connection: MockConnection):
        """연결 반환"""
        if connection in self.active_connections:
            self.active_connections.remove(connection)
            
            # 사용 시간 기록
            usage_time = time.time() - connection.last_used
            self.connection_usage_times.append(usage_time)
            
            await self.available_connections.put(connection)
    
    def get_stats(self) -> Dict[str, Any]:
        """풀 통계 반환"""
        avg_usage_time = (sum(self.connection_usage_times) / len(self.connection_usage_times) 
                         if self.connection_usage_times else 0)
        
        return {
            "active_connections": len(self.active_connections),
            "available_connections": self.available_connections.qsize(),
            "max_connections": self.max_connections,
            "total_created": self.total_created,
            "total_closed": self.total_closed,
            "avg_usage_time": avg_usage_time
        }
    
    async def close(self):
        """풀 종료"""
        # 모든 활성 연결 종료
        for connection in self.active_connections.copy():
            await connection.close()
            self.active_connections.remove(connection)
            self.total_closed += 1
        
        # 대기 중인 연결 종료
        while not self.available_connections.empty():
            connection = await self.available_connections.get()
            await connection.close()
            self.total_closed += 1
        
        self.logger.info("Connection pool closed")


class ConnectionContextManager:
    """연결 컨텍스트 매니저"""
    
    def __init__(self, pool: ConnectionPool):
        self.pool = pool
        self.connection = None
    
    async def __aenter__(self):
        self.connection = await self.pool._acquire_connection()
        return self.connection
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.connection:
            await self.pool._release_connection(self.connection)


class LazyLoader:
    """지연 로딩 시스템"""
    
    def __init__(self, loader_func: Callable[[], Awaitable[Any]]):
        self.loader_func = loader_func
        self.cached_data = None
        self.loaded = False
        self.loading = False
        self.load_lock = asyncio.Lock()
        self.logger = setup_logger("lazy_loader")
    
    async def get(self) -> Any:
        """데이터 획득 (지연 로딩)"""
        if self.loaded:
            return self.cached_data
        
        async with self.load_lock:
            if self.loaded:
                return self.cached_data
            
            if self.loading:
                # 이미 로딩 중이면 대기
                while self.loading:
                    await asyncio.sleep(0.01)
                return self.cached_data
            
            self.loading = True
            try:
                self.cached_data = await self.loader_func()
                self.loaded = True
                self.logger.debug("Data loaded successfully")
                return self.cached_data
            finally:
                self.loading = False
    
    def invalidate(self):
        """캐시 무효화"""
        self.cached_data = None
        self.loaded = False
        self.logger.debug("Cache invalidated")


class AsyncCacheWarmer:
    """비동기 캐시 워밍"""
    
    def __init__(self):
        self.warmed_keys = set()
        self.logger = setup_logger("cache_warmer")
    
    async def warm_cache(self, warming_tasks: Dict[str, Callable[[], Awaitable[Any]]]) -> List[str]:
        """병렬 캐시 워밍"""
        warmed_keys = []
        
        # 모든 워밍 작업을 병렬로 실행
        tasks = []
        for key, task_func in warming_tasks.items():
            tasks.append(self._warm_single_key(key, task_func))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            key = list(warming_tasks.keys())[i]
            if not isinstance(result, Exception):
                warmed_keys.append(key)
                self.warmed_keys.add(key)
            else:
                self.logger.warning(f"Failed to warm cache for key {key}: {result}")
        
        self.logger.info(f"Cache warming completed: {len(warmed_keys)}/{len(warming_tasks)} keys warmed")
        return warmed_keys
    
    async def _warm_single_key(self, key: str, task_func: Callable[[], Awaitable[Any]]):
        """단일 키 워밍"""
        await task_func()
        return key


class AdaptiveTimeoutManager:
    """적응형 타임아웃 관리"""
    
    def __init__(self, initial_timeout: float, min_timeout: float, max_timeout: float):
        self.initial_timeout = initial_timeout
        self.min_timeout = min_timeout
        self.max_timeout = max_timeout
        self.current_timeout = initial_timeout
        
        self.response_times = deque(maxlen=20)  # 최근 20개 응답 시간
        self.success_count = 0
        self.timeout_count = 0
        
        self.logger = setup_logger("adaptive_timeout")
    
    async def record_response_time(self, response_time: float):
        """응답 시간 기록 및 타임아웃 조정"""
        self.response_times.append(response_time)
        
        if response_time < self.current_timeout:
            self.success_count += 1
        else:
            self.timeout_count += 1
        
        # 충분한 데이터가 모이면 타임아웃 조정
        if len(self.response_times) >= 10:
            await self._adjust_timeout()
    
    async def _adjust_timeout(self):
        """타임아웃 조정"""
        if not self.response_times:
            return
        
        avg_response_time = sum(self.response_times) / len(self.response_times)
        p95_response_time = sorted(self.response_times)[int(len(self.response_times) * 0.95)]
        
        # 빠른 응답이 많으면 타임아웃 감소
        if avg_response_time < self.current_timeout * 0.5:
            new_timeout = max(avg_response_time * 2, self.min_timeout)
            if new_timeout < self.current_timeout:
                self.current_timeout = new_timeout
                self.logger.debug(f"Decreased timeout to {self.current_timeout:.2f}s")
        
        # 느린 응답이 많으면 타임아웃 증가
        elif p95_response_time > self.current_timeout * 0.8:
            new_timeout = min(p95_response_time * 1.5, self.max_timeout)
            if new_timeout > self.current_timeout:
                self.current_timeout = new_timeout
                self.logger.debug(f"Increased timeout to {self.current_timeout:.2f}s")
    
    def get_current_timeout(self) -> float:
        """현재 타임아웃 반환"""
        return self.current_timeout


# 전역 인스턴스 관리
_connection_pools = {}
_lazy_loaders = {}
_cache_warmers = {}
_timeout_managers = {}


def get_connection_pool(name: str, max_connections: int, min_connections: int) -> ConnectionPool:
    """연결 풀 인스턴스 획득"""
    if name not in _connection_pools:
        _connection_pools[name] = ConnectionPool(max_connections, min_connections)
    return _connection_pools[name]


def get_lazy_loader(name: str, loader_func: Callable[[], Awaitable[Any]]) -> LazyLoader:
    """지연 로더 인스턴스 획득"""
    if name not in _lazy_loaders:
        _lazy_loaders[name] = LazyLoader(loader_func)
    return _lazy_loaders[name]


def get_cache_warmer(name: str) -> AsyncCacheWarmer:
    """캐시 워머 인스턴스 획득"""
    if name not in _cache_warmers:
        _cache_warmers[name] = AsyncCacheWarmer()
    return _cache_warmers[name]


def get_timeout_manager(name: str, initial_timeout: float, min_timeout: float, max_timeout: float) -> AdaptiveTimeoutManager:
    """타임아웃 매니저 인스턴스 획득"""
    if name not in _timeout_managers:
        _timeout_managers[name] = AdaptiveTimeoutManager(initial_timeout, min_timeout, max_timeout)
    return _timeout_managers[name]