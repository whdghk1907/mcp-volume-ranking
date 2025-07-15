"""
Hierarchical Cache System
계층적 캐시 시스템 (L1: Redis, L2: Memory)
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime

from src.config import get_settings
from src.utils.logger import setup_logger
from src.exceptions import CacheError
from .l1_cache import L1Cache, get_l1_cache
from .l2_cache import L2Cache, get_l2_cache
from .key_generator import CacheKeyGenerator, get_key_generator


class HierarchicalCache:
    """계층적 캐시 시스템 - TDD GREEN 단계 구현"""
    
    def __init__(self, l1_cache: Optional[L1Cache] = None, l2_cache: Optional[L2Cache] = None):
        self.settings = get_settings()
        self.logger = setup_logger("hierarchical_cache")
        
        # 캐시 인스턴스 초기화
        self.l1_cache = l1_cache or get_l1_cache()
        self.l2_cache = l2_cache or get_l2_cache()
        self.key_generator = get_key_generator()
        
        # 통계 정보
        self._stats = {
            "l1_hits": 0,
            "l1_misses": 0,
            "l2_hits": 0,
            "l2_misses": 0,
            "sets": 0,
            "deletes": 0,
            "invalidations": 0
        }
        
        # 캐시 전략 설정
        self.write_through = self.settings.cache_write_through
        self.l1_enabled = self.settings.cache_l1_enabled
        self.l2_enabled = self.settings.cache_l2_enabled
    
    async def get(self, key: str) -> Optional[Any]:
        """
        계층적 캐시에서 데이터 조회
        
        Args:
            key: 캐시 키
            
        Returns:
            캐시된 데이터 또는 None
        """
        try:
            # L1 캐시에서 먼저 조회
            if self.l1_enabled:
                l1_result = await self.l1_cache.get(key)
                if l1_result is not None:
                    self._stats["l1_hits"] += 1
                    self.logger.debug(f"Hierarchical cache L1 hit: {key}")
                    return l1_result
                else:
                    self._stats["l1_misses"] += 1
            
            # L2 캐시에서 조회
            if self.l2_enabled:
                l2_result = await self.l2_cache.get(key)
                if l2_result is not None:
                    self._stats["l2_hits"] += 1
                    self.logger.debug(f"Hierarchical cache L2 hit: {key}")
                    
                    # L2에서 찾은 데이터를 L1에 저장 (캐시 프로모션)
                    if self.l1_enabled:
                        try:
                            # 짧은 TTL로 L1에 저장
                            await self.l1_cache.set(key, l2_result, ttl=300)
                        except Exception as e:
                            self.logger.warning(f"Failed to promote to L1: {key}, error: {str(e)}")
                    
                    return l2_result
                else:
                    self._stats["l2_misses"] += 1
            
            self.logger.debug(f"Hierarchical cache miss: {key}")
            return None
            
        except Exception as e:
            self.logger.error(f"Hierarchical cache get failed: {key}, error: {str(e)}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        계층적 캐시에 데이터 저장
        
        Args:
            key: 캐시 키
            value: 저장할 데이터
            ttl: 만료 시간 (초)
            
        Returns:
            저장 성공 여부
        """
        try:
            success = True
            
            # L1 캐시에 저장
            if self.l1_enabled:
                try:
                    l1_ttl = ttl or self.settings.cache_l1_ttl_seconds
                    l1_success = await self.l1_cache.set(key, value, l1_ttl)
                    if not l1_success:
                        success = False
                        self.logger.warning(f"L1 cache set failed: {key}")
                except Exception as e:
                    success = False
                    self.logger.warning(f"L1 cache set error: {key}, error: {str(e)}")
            
            # L2 캐시에 저장
            if self.l2_enabled:
                try:
                    l2_ttl = ttl or self.settings.cache_l2_ttl_seconds
                    l2_success = await self.l2_cache.set(key, value, l2_ttl)
                    if not l2_success:
                        success = False
                        self.logger.warning(f"L2 cache set failed: {key}")
                except Exception as e:
                    success = False
                    self.logger.warning(f"L2 cache set error: {key}, error: {str(e)}")
            
            if success:
                self._stats["sets"] += 1
                self.logger.debug(f"Hierarchical cache set: {key}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Hierarchical cache set failed: {key}, error: {str(e)}")
            raise CacheError(f"계층적 캐시 저장 실패: {str(e)}")
    
    async def delete(self, key: str) -> bool:
        """
        계층적 캐시에서 데이터 삭제
        
        Args:
            key: 삭제할 캐시 키
            
        Returns:
            삭제 성공 여부
        """
        try:
            success = True
            
            # L1 캐시에서 삭제
            if self.l1_enabled:
                try:
                    l1_success = await self.l1_cache.delete(key)
                    if not l1_success:
                        success = False
                except Exception as e:
                    success = False
                    self.logger.warning(f"L1 cache delete error: {key}, error: {str(e)}")
            
            # L2 캐시에서 삭제
            if self.l2_enabled:
                try:
                    l2_success = await self.l2_cache.delete(key)
                    if not l2_success:
                        success = False
                except Exception as e:
                    success = False
                    self.logger.warning(f"L2 cache delete error: {key}, error: {str(e)}")
            
            if success:
                self._stats["deletes"] += 1
                self.logger.debug(f"Hierarchical cache delete: {key}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Hierarchical cache delete failed: {key}, error: {str(e)}")
            raise CacheError(f"계층적 캐시 삭제 실패: {str(e)}")
    
    async def invalidate(self, key: str) -> bool:
        """
        캐시 무효화 (삭제와 동일하지만 통계 구분)
        
        Args:
            key: 무효화할 캐시 키
            
        Returns:
            무효화 성공 여부
        """
        try:
            result = await self.delete(key)
            if result:
                self._stats["invalidations"] += 1
                self.logger.debug(f"Hierarchical cache invalidated: {key}")
            return result
            
        except Exception as e:
            self.logger.error(f"Hierarchical cache invalidation failed: {key}, error: {str(e)}")
            raise CacheError(f"캐시 무효화 실패: {str(e)}")
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """
        패턴에 매칭되는 캐시 키들 무효화
        
        Args:
            pattern: 무효화할 키 패턴
            
        Returns:
            무효화된 키의 개수
        """
        try:
            total_invalidated = 0
            
            # L1 캐시 패턴 삭제
            if self.l1_enabled:
                try:
                    l1_count = await self.l1_cache.delete_pattern(pattern)
                    total_invalidated += l1_count
                except Exception as e:
                    self.logger.warning(f"L1 cache pattern delete error: {pattern}, error: {str(e)}")
            
            # L2 캐시 패턴 삭제 (수동 구현)
            if self.l2_enabled:
                try:
                    l2_keys = await self.l2_cache.get_keys(pattern)
                    for key in l2_keys:
                        if await self.l2_cache.delete(key):
                            total_invalidated += 1
                except Exception as e:
                    self.logger.warning(f"L2 cache pattern delete error: {pattern}, error: {str(e)}")
            
            self._stats["invalidations"] += total_invalidated
            self.logger.debug(f"Hierarchical cache pattern invalidated: {pattern}, count: {total_invalidated}")
            
            return total_invalidated
            
        except Exception as e:
            self.logger.error(f"Hierarchical cache pattern invalidation failed: {pattern}, error: {str(e)}")
            raise CacheError(f"패턴 캐시 무효화 실패: {str(e)}")
    
    async def exists(self, key: str) -> bool:
        """
        캐시 키 존재 여부 확인
        
        Args:
            key: 확인할 캐시 키
            
        Returns:
            키 존재 여부
        """
        try:
            # L1 캐시에서 확인
            if self.l1_enabled:
                if await self.l1_cache.exists(key):
                    return True
            
            # L2 캐시에서 확인
            if self.l2_enabled:
                if await self.l2_cache.exists(key):
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Hierarchical cache exists check failed: {key}, error: {str(e)}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """
        캐시 시스템 상태 확인
        
        Returns:
            상태 정보
        """
        try:
            health_info = {
                "overall_status": "healthy",
                "l1_cache": {"status": "unknown", "enabled": self.l1_enabled},
                "l2_cache": {"status": "unknown", "enabled": self.l2_enabled},
                "timestamp": datetime.now().isoformat()
            }
            
            # L1 캐시 상태 확인
            if self.l1_enabled:
                l1_healthy = await self.l1_cache.health_check()
                health_info["l1_cache"]["status"] = "healthy" if l1_healthy else "unhealthy"
                if not l1_healthy:
                    health_info["overall_status"] = "degraded"
            
            # L2 캐시 상태 확인
            if self.l2_enabled:
                l2_healthy = await self.l2_cache.health_check()
                health_info["l2_cache"]["status"] = "healthy" if l2_healthy else "unhealthy"
                if not l2_healthy:
                    health_info["overall_status"] = "degraded"
            
            return health_info
            
        except Exception as e:
            self.logger.error(f"Hierarchical cache health check failed: {str(e)}")
            return {
                "overall_status": "unhealthy",
                "l1_cache": {"status": "error", "enabled": self.l1_enabled},
                "l2_cache": {"status": "error", "enabled": self.l2_enabled},
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def get_performance_stats(self) -> Dict[str, Any]:
        """
        캐시 성능 통계 조회
        
        Returns:
            성능 통계 정보
        """
        try:
            # 계층적 캐시 통계
            total_hits = self._stats["l1_hits"] + self._stats["l2_hits"]
            total_misses = self._stats["l1_misses"] + self._stats["l2_misses"]
            total_requests = total_hits + total_misses
            
            total_hit_rate = 0.0
            if total_requests > 0:
                total_hit_rate = (total_hits / total_requests) * 100.0
            
            hierarchical_stats = {
                "l1_hits": self._stats["l1_hits"],
                "l1_misses": self._stats["l1_misses"],
                "l2_hits": self._stats["l2_hits"],
                "l2_misses": self._stats["l2_misses"],
                "total_hits": total_hits,
                "total_misses": total_misses,
                "total_hit_rate": total_hit_rate,
                "sets": self._stats["sets"],
                "deletes": self._stats["deletes"],
                "invalidations": self._stats["invalidations"]
            }
            
            # L1 캐시 통계
            l1_stats = {}
            if self.l1_enabled:
                try:
                    l1_stats = await self.l1_cache.get_stats()
                except Exception as e:
                    l1_stats = {"error": str(e)}
            
            # L2 캐시 통계
            l2_stats = {}
            if self.l2_enabled:
                try:
                    l2_stats = await self.l2_cache.get_stats()
                except Exception as e:
                    l2_stats = {"error": str(e)}
            
            return {
                "hierarchical": hierarchical_stats,
                "l1_cache": l1_stats,
                "l2_cache": l2_stats,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Hierarchical cache performance stats failed: {str(e)}")
            return {
                "hierarchical": {},
                "l1_cache": {"error": str(e)},
                "l2_cache": {"error": str(e)},
                "timestamp": datetime.now().isoformat()
            }
    
    async def warm_cache(self, warm_data: Dict[str, Any]) -> int:
        """
        캐시 워밍
        
        Args:
            warm_data: 워밍할 데이터 {key: value}
            
        Returns:
            워밍된 키의 개수
        """
        try:
            warmed_count = 0
            
            for key, value in warm_data.items():
                try:
                    # 기존 데이터가 없는 경우만 워밍
                    if not await self.exists(key):
                        if await self.set(key, value):
                            warmed_count += 1
                except Exception as e:
                    self.logger.warning(f"Cache warming failed for key: {key}, error: {str(e)}")
            
            self.logger.info(f"Cache warmed {warmed_count} keys out of {len(warm_data)}")
            return warmed_count
            
        except Exception as e:
            self.logger.error(f"Cache warming failed: {str(e)}")
            return 0
    
    async def close(self):
        """캐시 시스템 종료"""
        try:
            if self.l1_enabled:
                await self.l1_cache.close()
            
            if self.l2_enabled:
                self.l2_cache.close()
            
            self.logger.info("Hierarchical cache system closed")
            
        except Exception as e:
            self.logger.error(f"Hierarchical cache close failed: {str(e)}")


# 글로벌 계층적 캐시 인스턴스
_hierarchical_cache = None

def get_hierarchical_cache() -> HierarchicalCache:
    """글로벌 계층적 캐시 인스턴스 획득"""
    global _hierarchical_cache
    if _hierarchical_cache is None:
        _hierarchical_cache = HierarchicalCache()
    return _hierarchical_cache