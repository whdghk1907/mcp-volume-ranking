"""
Batch Processing System - TDD Implementation
배치 처리 시스템 - TDD 구현
"""

import asyncio
import time
from typing import Dict, Any, List, Optional, Callable, Awaitable, TypeVar, Generic
from datetime import datetime
from dataclasses import dataclass
from collections import deque

from src.config import get_settings
from src.utils.logger import setup_logger

T = TypeVar('T')
R = TypeVar('R')


@dataclass
class BatchItem:
    """배치 아이템"""
    item: Any
    future: asyncio.Future
    added_at: datetime


class BatchProcessor(Generic[T, R]):
    """기본 배치 처리기"""
    
    def __init__(self, batch_size: int, max_wait_time: float, processor_func: Callable[[List[T]], List[R]]):
        self.batch_size = batch_size
        self.max_wait_time = max_wait_time
        self.processor_func = processor_func
        
        self.current_batch = []
        self.batch_timer = None
        self.processing_lock = asyncio.Lock()
        self.running = False
        self.logger = setup_logger("batch_processor")
    
    async def start(self):
        """배치 처리기 시작"""
        self.running = True
        self.logger.info("Batch processor started")
    
    async def stop(self):
        """배치 처리기 중지"""
        self.running = False
        
        # 대기 중인 배치 처리
        if self.current_batch:
            await self._process_current_batch()
        
        # 타이머 취소
        if self.batch_timer:
            self.batch_timer.cancel()
        
        self.logger.info("Batch processor stopped")
    
    async def add_item(self, item: T) -> asyncio.Future[R]:
        """아이템 추가"""
        if not self.running:
            raise RuntimeError("Batch processor is not running")
        
        future = asyncio.Future()
        batch_item = BatchItem(
            item=item,
            future=future,
            added_at=datetime.now()
        )
        
        async with self.processing_lock:
            self.current_batch.append(batch_item)
            
            # 배치 크기에 도달하면 즉시 처리
            if len(self.current_batch) >= self.batch_size:
                await self._process_current_batch()
            # 첫 번째 아이템이면 타이머 시작
            elif len(self.current_batch) == 1:
                self._start_batch_timer()
        
        return future
    
    def _start_batch_timer(self):
        """배치 타이머 시작"""
        if self.batch_timer:
            self.batch_timer.cancel()
        
        self.batch_timer = asyncio.create_task(self._batch_timeout())
    
    async def _batch_timeout(self):
        """배치 타임아웃 처리"""
        await asyncio.sleep(self.max_wait_time)
        
        async with self.processing_lock:
            if self.current_batch:
                await self._process_current_batch()
    
    async def _process_current_batch(self):
        """현재 배치 처리"""
        if not self.current_batch:
            return
        
        batch_to_process = self.current_batch.copy()
        self.current_batch.clear()
        
        if self.batch_timer:
            self.batch_timer.cancel()
            self.batch_timer = None
        
        try:
            # 배치 처리 실행
            items = [batch_item.item for batch_item in batch_to_process]
            
            if asyncio.iscoroutinefunction(self.processor_func):
                results = await self.processor_func(items)
            else:
                results = self.processor_func(items)
            
            # 결과 분배
            for batch_item, result in zip(batch_to_process, results):
                if not batch_item.future.done():
                    batch_item.future.set_result(result)
            
        except Exception as e:
            # 오류 시 모든 퓨처에 예외 설정
            for batch_item in batch_to_process:
                if not batch_item.future.done():
                    batch_item.future.set_exception(e)
        
        self.logger.debug(f"Processed batch of {len(batch_to_process)} items")


class DynamicBatchProcessor(Generic[T, R]):
    """동적 배치 처리기"""
    
    def __init__(self, initial_batch_size: int, min_batch_size: int, max_batch_size: int):
        self.initial_batch_size = initial_batch_size
        self.min_batch_size = min_batch_size
        self.max_batch_size = max_batch_size
        self.current_batch_size = initial_batch_size
        
        self.current_batch = []
        self.processing_times = deque(maxlen=10)  # 최근 10개 처리 시간
        self.throughput_history = deque(maxlen=5)  # 최근 5개 처리량
        self.running = False
        self.processing_lock = asyncio.Lock()
        self.batch_timer = None
        self.slow_processing = False
        
        self.logger = setup_logger("dynamic_batch_processor")
    
    async def start(self):
        """처리기 시작"""
        self.running = True
        self.logger.info(f"Dynamic batch processor started with initial batch size: {self.current_batch_size}")
    
    async def stop(self):
        """처리기 중지"""
        self.running = False
        
        if self.current_batch:
            await self._process_current_batch()
        
        if self.batch_timer:
            self.batch_timer.cancel()
        
        self.logger.info("Dynamic batch processor stopped")
    
    async def add_item(self, item: T) -> asyncio.Future[R]:
        """아이템 추가"""
        if not self.running:
            raise RuntimeError("Dynamic batch processor is not running")
        
        future = asyncio.Future()
        batch_item = BatchItem(
            item=item,
            future=future,
            added_at=datetime.now()
        )
        
        async with self.processing_lock:
            self.current_batch.append(batch_item)
            
            # 동적 배치 크기에 도달하면 처리
            if len(self.current_batch) >= self.current_batch_size:
                await self._process_current_batch()
            # 첫 번째 아이템이면 타이머 시작
            elif len(self.current_batch) == 1:
                self._start_batch_timer()
        
        return future
    
    def _start_batch_timer(self):
        """배치 타이머 시작"""
        if self.batch_timer:
            self.batch_timer.cancel()
        
        max_wait_time = 0.05 if self.slow_processing else 0.1
        self.batch_timer = asyncio.create_task(self._batch_timeout(max_wait_time))
    
    async def _batch_timeout(self, wait_time: float):
        """배치 타임아웃"""
        await asyncio.sleep(wait_time)
        
        async with self.processing_lock:
            if self.current_batch:
                await self._process_current_batch()
    
    async def _process_current_batch(self):
        """현재 배치 처리"""
        if not self.current_batch:
            return
        
        batch_to_process = self.current_batch.copy()
        self.current_batch.clear()
        
        if self.batch_timer:
            self.batch_timer.cancel()
            self.batch_timer = None
        
        start_time = time.time()
        
        try:
            # Mock 처리 (실제로는 processor_func 사용)
            await asyncio.sleep(0.01)  # 시뮬레이션
            results = [f"processed_{item.item}" for item in batch_to_process]
            
            # 결과 분배
            for batch_item, result in zip(batch_to_process, results):
                if not batch_item.future.done():
                    batch_item.future.set_result(result)
            
        except Exception as e:
            for batch_item in batch_to_process:
                if not batch_item.future.done():
                    batch_item.future.set_exception(e)
        
        # 성능 메트릭 업데이트
        processing_time = time.time() - start_time
        self.processing_times.append(processing_time)
        throughput = len(batch_to_process) / processing_time if processing_time > 0 else 0
        self.throughput_history.append(throughput)
        
        # 배치 크기 조정
        await self._adjust_batch_size(processing_time, throughput)
        
        self.logger.debug(f"Processed batch of {len(batch_to_process)} items in {processing_time:.3f}s")
    
    async def _adjust_batch_size(self, processing_time: float, throughput: float):
        """배치 크기 동적 조정"""
        if len(self.processing_times) < 3:
            return
        
        avg_processing_time = sum(self.processing_times) / len(self.processing_times)
        
        # 빠른 처리 시 배치 크기 증가
        if avg_processing_time < 0.05 and throughput > 100:
            if self.current_batch_size < self.max_batch_size:
                self.current_batch_size = min(self.current_batch_size + 1, self.max_batch_size)
                self.logger.debug(f"Increased batch size to {self.current_batch_size}")
        
        # 느린 처리 시 배치 크기 감소
        elif avg_processing_time > 0.1 or throughput < 50:
            if self.current_batch_size > self.min_batch_size:
                self.current_batch_size = max(self.current_batch_size - 1, self.min_batch_size)
                self.logger.debug(f"Decreased batch size to {self.current_batch_size}")
    
    def get_current_batch_size(self) -> int:
        """현재 배치 크기 반환"""
        return self.current_batch_size
    
    def simulate_slow_processing(self):
        """느린 처리 시뮬레이션"""
        self.slow_processing = True
        # 배치 크기를 줄여서 반응성 향상
        self.current_batch_size = max(self.current_batch_size - 2, self.min_batch_size)


# 전역 인스턴스 관리
_batch_processors = {}
_dynamic_processors = {}


def get_batch_processor(name: str, batch_size: int, max_wait_time: float, processor_func: Callable) -> BatchProcessor:
    """배치 처리기 인스턴스 획득"""
    if name not in _batch_processors:
        _batch_processors[name] = BatchProcessor(batch_size, max_wait_time, processor_func)
    return _batch_processors[name]


def get_dynamic_batch_processor(name: str, initial_batch_size: int, min_batch_size: int, max_batch_size: int) -> DynamicBatchProcessor:
    """동적 배치 처리기 인스턴스 획득"""
    if name not in _dynamic_processors:
        _dynamic_processors[name] = DynamicBatchProcessor(initial_batch_size, min_batch_size, max_batch_size)
    return _dynamic_processors[name]