"""
L2 Cache Implementation - Memory-based Cache with LRU
L2 캐시 구현 - LRU 기반 메모리 캐시
"""

import asyncio
import time
from typing import Dict, Any, Optional, OrderedDict
from datetime import datetime, timedelta
from collections import OrderedDict as OrderedDictType
import threading
import weakref

from src.config import get_settings
from src.utils.logger import setup_logger
from src.exceptions import CacheError


class CacheItem:
    """캐시 항목 클래스"""
    
    def __init__(self, value: Any, ttl: Optional[int] = None):
        # Pydantic 모델 처리
        if hasattr(value, 'model_dump'):
            self.value = value
            self.is_pydantic = True
        else:
            self.value = value
            self.is_pydantic = False
            
        self.created_at = datetime.now()
        self.expires_at = None
        self.access_count = 0
        self.last_accessed = self.created_at
        
        if ttl is not None:
            self.expires_at = self.created_at + timedelta(seconds=ttl)
    
    def is_expired(self) -> bool:
        """만료 여부 확인"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at
    
    def access(self) -> Any:
        """아이템 접근 시 호출"""
        self.access_count += 1
        self.last_accessed = datetime.now()
        return self.value


class L2Cache:
    """L2 캐시 (메모리) - TDD GREEN 단계 구현"""
    
    def __init__(self, max_size: int = None, default_ttl: int = None):
        self.settings = get_settings()
        self.logger = setup_logger("l2_cache")
        
        # 캐시 설정
        self.max_size = max_size or self.settings.cache_l2_max_size
        self.default_ttl = default_ttl or self.settings.cache_l2_ttl_seconds
        
        # 캐시 저장소 (LRU 구현을 위해 OrderedDict 사용)
        self._cache: OrderedDictType[str, CacheItem] = OrderedDict()
        self._lock = threading.RLock()  # 스레드 안전성을 위한 락
        
        # 통계 정보
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "evictions": 0,
            "expires": 0
        }
        
        # 백그라운드 정리 태스크
        self._cleanup_task = None
        self._start_cleanup_task()
    
    def _start_cleanup_task(self):
        """백그라운드 정리 태스크 시작"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_expired_items())
    
    async def _cleanup_expired_items(self):
        """만료된 항목들 정리 (백그라운드 태스크)"""
        while True:
            try:
                await asyncio.sleep(60)  # 1분마다 정리
                
                with self._lock:
                    expired_keys = []
                    for key, item in self._cache.items():
                        if item.is_expired():
                            expired_keys.append(key)
                    
                    for key in expired_keys:
                        del self._cache[key]
                        self._stats["expires"] += 1
                    
                    if expired_keys:
                        self.logger.debug(f"L2 cache cleaned up {len(expired_keys)} expired items")
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"L2 cache cleanup error: {str(e)}")
    
    def _evict_lru(self):
        """LRU 방출 수행"""
        if not self._cache:
            return
        
        # 가장 오래된 항목 제거
        lru_key = next(iter(self._cache))
        del self._cache[lru_key]
        self._stats["evictions"] += 1
        
        self.logger.debug(f"L2 cache evicted LRU item: {lru_key}")
    
    def _move_to_end(self, key: str):
        """키를 가장 최근 위치로 이동 (LRU 업데이트)"""
        self._cache.move_to_end(key)
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        캐시 데이터 저장
        
        Args:
            key: 캐시 키
            value: 저장할 데이터
            ttl: 만료 시간 (초)
            
        Returns:
            저장 성공 여부
        """
        try:
            with self._lock:
                # TTL 설정
                if ttl is None:
                    ttl = self.default_ttl
                
                # 캐시 항목 생성
                item = CacheItem(value, ttl)
                
                # 기존 키가 있으면 제거 후 추가
                if key in self._cache:
                    del self._cache[key]
                
                # 캐시 크기 제한 확인
                while len(self._cache) >= self.max_size:
                    self._evict_lru()
                
                # 새 항목 추가
                self._cache[key] = item
                self._stats["sets"] += 1
                
                self.logger.debug(f"L2 cache set: {key} (TTL: {ttl}s)")
                return True
                
        except Exception as e:
            self.logger.error(f"L2 cache set failed: {key}, error: {str(e)}")
            raise CacheError(f"L2 캐시 저장 실패: {str(e)}")
    
    async def get(self, key: str) -> Optional[Any]:
        """
        캐시 데이터 조회
        
        Args:
            key: 캐시 키
            
        Returns:
            캐시된 데이터 또는 None
        """
        try:
            with self._lock:
                # 캐시에서 조회
                item = self._cache.get(key)
                
                if item is None:
                    self._stats["misses"] += 1
                    self.logger.debug(f"L2 cache miss: {key}")
                    return None
                
                # 만료 확인
                if item.is_expired():
                    del self._cache[key]
                    self._stats["misses"] += 1
                    self._stats["expires"] += 1
                    self.logger.debug(f"L2 cache expired: {key}")
                    return None
                
                # LRU 업데이트 및 접근 기록
                self._move_to_end(key)
                value = item.access()
                self._stats["hits"] += 1
                
                self.logger.debug(f"L2 cache hit: {key}")
                return value
                
        except Exception as e:
            self.logger.error(f"L2 cache get failed: {key}, error: {str(e)}")
            self._stats["misses"] += 1
            return None
    
    async def delete(self, key: str) -> bool:
        """
        캐시 데이터 삭제
        
        Args:
            key: 삭제할 캐시 키
            
        Returns:
            삭제 성공 여부
        """
        try:
            with self._lock:
                if key in self._cache:
                    del self._cache[key]
                    self._stats["deletes"] += 1
                    self.logger.debug(f"L2 cache delete: {key}")
                    return True
                else:
                    return False
                    
        except Exception as e:
            self.logger.error(f"L2 cache delete failed: {key}, error: {str(e)}")
            raise CacheError(f"L2 캐시 삭제 실패: {str(e)}")
    
    async def exists(self, key: str) -> bool:
        """
        캐시 키 존재 여부 확인
        
        Args:
            key: 확인할 캐시 키
            
        Returns:
            키 존재 여부
        """
        try:
            with self._lock:
                item = self._cache.get(key)
                if item is None:
                    return False
                
                # 만료 확인
                if item.is_expired():
                    del self._cache[key]
                    self._stats["expires"] += 1
                    return False
                
                return True
                
        except Exception as e:
            self.logger.error(f"L2 cache exists check failed: {key}, error: {str(e)}")
            return False
    
    async def clear(self) -> bool:
        """
        모든 캐시 데이터 삭제
        
        Returns:
            삭제 성공 여부
        """
        try:
            with self._lock:
                count = len(self._cache)
                self._cache.clear()
                self._stats["deletes"] += count
                
                self.logger.debug(f"L2 cache cleared {count} items")
                return True
                
        except Exception as e:
            self.logger.error(f"L2 cache clear failed: {str(e)}")
            raise CacheError(f"L2 캐시 전체 삭제 실패: {str(e)}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        캐시 통계 정보 조회
        
        Returns:
            통계 정보 딕셔너리
        """
        try:
            with self._lock:
                total_requests = self._stats["hits"] + self._stats["misses"]
                hit_rate = 0.0
                
                if total_requests > 0:
                    hit_rate = (self._stats["hits"] / total_requests) * 100.0
                
                # 캐시 크기 정보
                current_size = len(self._cache)
                
                # 메모리 사용량 추정
                memory_usage = sum(
                    len(str(key)) + len(str(item.value)) + 200  # 대략적인 오버헤드
                    for key, item in self._cache.items()
                )
                
                return {
                    "hits": self._stats["hits"],
                    "misses": self._stats["misses"],
                    "sets": self._stats["sets"],
                    "deletes": self._stats["deletes"],
                    "evictions": self._stats["evictions"],
                    "expires": self._stats["expires"],
                    "hit_rate": hit_rate,
                    "current_size": current_size,
                    "max_size": self.max_size,
                    "memory_usage_bytes": memory_usage,
                    "memory_usage_mb": memory_usage / (1024 * 1024),
                    "default_ttl": self.default_ttl
                }
                
        except Exception as e:
            self.logger.error(f"L2 cache stats failed: {str(e)}")
            return {
                "hits": 0,
                "misses": 0,
                "sets": 0,
                "deletes": 0,
                "evictions": 0,
                "expires": 0,
                "hit_rate": 0.0,
                "current_size": 0,
                "max_size": self.max_size,
                "memory_usage_bytes": 0,
                "memory_usage_mb": 0.0,
                "default_ttl": self.default_ttl,
                "error": str(e)
            }
    
    async def get_keys(self, pattern: Optional[str] = None) -> list[str]:
        """
        캐시 키 목록 조회
        
        Args:
            pattern: 필터링할 패턴 (없으면 모든 키)
            
        Returns:
            키 목록
        """
        try:
            with self._lock:
                keys = list(self._cache.keys())
                
                if pattern:
                    import fnmatch
                    keys = [key for key in keys if fnmatch.fnmatch(key, pattern)]
                
                return keys
                
        except Exception as e:
            self.logger.error(f"L2 cache get_keys failed: {str(e)}")
            return []
    
    async def health_check(self) -> bool:
        """
        캐시 상태 확인
        
        Returns:
            상태 (항상 True - 메모리 캐시는 항상 사용 가능)
        """
        return True
    
    def close(self):
        """캐시 종료"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            self._cleanup_task = None
        
        with self._lock:
            self._cache.clear()
        
        self.logger.info("L2 cache closed")


# 글로벌 L2 캐시 인스턴스
_l2_cache = None

def get_l2_cache() -> L2Cache:
    """글로벌 L2 캐시 인스턴스 획득"""
    global _l2_cache
    if _l2_cache is None:
        _l2_cache = L2Cache()
    return _l2_cache