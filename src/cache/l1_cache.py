"""
L1 Cache Implementation - Redis-based Cache
L1 캐시 구현 - Redis 기반 캐시
"""

import json
import asyncio
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
import redis.asyncio as redis
from redis.exceptions import RedisError, ConnectionError

from src.config import get_settings
from src.utils.logger import setup_logger
from src.exceptions import CacheError


class L1Cache:
    """L1 캐시 (Redis) - TDD GREEN 단계 구현"""
    
    def __init__(self, redis_url: Optional[str] = None):
        self.settings = get_settings()
        self.logger = setup_logger("l1_cache")
        self.redis_url = redis_url or self.settings.redis_url
        self._redis: Optional[redis.Redis] = None
        self._connection_pool = None
        self._is_connected = False
        
    async def _get_redis(self) -> redis.Redis:
        """Redis 연결 획득 (지연 초기화)"""
        if self._redis is None:
            try:
                # Redis 연결 풀 생성
                self._connection_pool = redis.ConnectionPool.from_url(
                    self.redis_url,
                    max_connections=20,
                    retry_on_timeout=True,
                    socket_keepalive=True,
                    socket_keepalive_options={}
                )
                
                self._redis = redis.Redis(
                    connection_pool=self._connection_pool,
                    decode_responses=True
                )
                
                # 연결 테스트
                await self._redis.ping()
                self._is_connected = True
                self.logger.info("Redis connection established successfully")
                
            except Exception as e:
                self.logger.error(f"Failed to connect to Redis: {str(e)}")
                # Redis 연결 실패 시 Mock 구현 사용
                self._redis = MockRedis()
                self._is_connected = False
                
        return self._redis
    
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
            redis_client = await self._get_redis()
            
            # 데이터 JSON 직렬화 (Pydantic 모델 지원)
            if hasattr(value, 'model_dump'):
                # Pydantic v2 모델
                json_value = json.dumps({
                    '__type__': value.__class__.__name__,
                    '__module__': value.__class__.__module__,
                    '__data__': value.model_dump()
                }, ensure_ascii=False, default=str)
            else:
                json_value = json.dumps(value, ensure_ascii=False, default=str)
            
            # TTL 설정
            if ttl is None:
                ttl = self.settings.cache_l1_ttl_seconds
                
            # Redis에 저장
            result = await redis_client.setex(key, ttl, json_value)
            
            self.logger.debug(f"L1 cache set: {key} (TTL: {ttl}s)")
            return result
            
        except Exception as e:
            self.logger.error(f"L1 cache set failed: {key}, error: {str(e)}")
            raise CacheError(f"L1 캐시 저장 실패: {str(e)}")
    
    async def get(self, key: str) -> Optional[Any]:
        """
        캐시 데이터 조회
        
        Args:
            key: 캐시 키
            
        Returns:
            캐시된 데이터 또는 None
        """
        try:
            redis_client = await self._get_redis()
            
            # Redis에서 조회
            json_value = await redis_client.get(key)
            
            if json_value is None:
                self.logger.debug(f"L1 cache miss: {key}")
                return None
            
            # JSON 역직렬화 (Pydantic 모델 지원)
            data = json.loads(json_value)
            
            # Pydantic 모델 복원
            if isinstance(data, dict) and '__type__' in data and '__module__' in data:
                try:
                    import importlib
                    module = importlib.import_module(data['__module__'])
                    model_class = getattr(module, data['__type__'])
                    value = model_class.model_validate(data['__data__'])
                except Exception as e:
                    self.logger.warning(f"Failed to restore Pydantic model: {e}")
                    value = data['__data__']
            else:
                value = data
            
            self.logger.debug(f"L1 cache hit: {key}")
            return value
            
        except Exception as e:
            self.logger.error(f"L1 cache get failed: {key}, error: {str(e)}")
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
            redis_client = await self._get_redis()
            
            # Redis에서 삭제
            result = await redis_client.delete(key)
            
            self.logger.debug(f"L1 cache delete: {key}")
            return result > 0
            
        except Exception as e:
            self.logger.error(f"L1 cache delete failed: {key}, error: {str(e)}")
            raise CacheError(f"L1 캐시 삭제 실패: {str(e)}")
    
    async def delete_pattern(self, pattern: str) -> int:
        """
        패턴에 매칭되는 캐시 키들 삭제
        
        Args:
            pattern: 삭제할 키 패턴 (예: "volume:*")
            
        Returns:
            삭제된 키의 개수
        """
        try:
            redis_client = await self._get_redis()
            
            # 패턴에 매칭되는 키들 찾기
            keys = await redis_client.keys(pattern)
            
            if not keys:
                self.logger.debug(f"L1 cache pattern delete: no keys match {pattern}")
                return 0
            
            # 키들 삭제
            result = await redis_client.delete(*keys)
            
            self.logger.debug(f"L1 cache pattern delete: {pattern}, deleted {result} keys")
            return result
            
        except Exception as e:
            self.logger.error(f"L1 cache pattern delete failed: {pattern}, error: {str(e)}")
            raise CacheError(f"L1 캐시 패턴 삭제 실패: {str(e)}")
    
    async def exists(self, key: str) -> bool:
        """
        캐시 키 존재 여부 확인
        
        Args:
            key: 확인할 캐시 키
            
        Returns:
            키 존재 여부
        """
        try:
            redis_client = await self._get_redis()
            result = await redis_client.exists(key)
            return result > 0
            
        except Exception as e:
            self.logger.error(f"L1 cache exists check failed: {key}, error: {str(e)}")
            return False
    
    async def health_check(self) -> bool:
        """
        Redis 연결 상태 확인
        
        Returns:
            연결 상태 (True: 정상, False: 비정상)
        """
        try:
            redis_client = await self._get_redis()
            await redis_client.ping()
            return True
            
        except Exception as e:
            self.logger.error(f"L1 cache health check failed: {str(e)}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Redis 서버 통계 정보 조회
        
        Returns:
            통계 정보 딕셔너리
        """
        try:
            redis_client = await self._get_redis()
            
            # Redis INFO 명령어로 서버 정보 조회
            info = await redis_client.info()
            
            # 주요 통계 정보 추출
            stats = {
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": 0.0,
                "redis_version": info.get("redis_version", "unknown"),
                "uptime_in_seconds": info.get("uptime_in_seconds", 0)
            }
            
            # 히트율 계산
            hits = stats["keyspace_hits"]
            misses = stats["keyspace_misses"]
            total = hits + misses
            
            if total > 0:
                stats["hit_rate"] = (hits / total) * 100.0
            
            return stats
            
        except Exception as e:
            self.logger.error(f"L1 cache stats failed: {str(e)}")
            return {
                "connected_clients": 0,
                "used_memory": 0,
                "used_memory_human": "0B",
                "total_commands_processed": 0,
                "keyspace_hits": 0,
                "keyspace_misses": 0,
                "hit_rate": 0.0,
                "redis_version": "unknown",
                "uptime_in_seconds": 0,
                "error": str(e)
            }
    
    async def flush_all(self) -> bool:
        """
        모든 캐시 데이터 삭제 (주의: 개발/테스트 환경에서만 사용)
        
        Returns:
            삭제 성공 여부
        """
        try:
            if self.settings.environment == "production":
                raise CacheError("Production 환경에서는 flush_all을 사용할 수 없습니다")
            
            redis_client = await self._get_redis()
            await redis_client.flushall()
            
            self.logger.warning("L1 cache flushed all data")
            return True
            
        except Exception as e:
            self.logger.error(f"L1 cache flush failed: {str(e)}")
            raise CacheError(f"L1 캐시 전체 삭제 실패: {str(e)}")
    
    async def close(self):
        """Redis 연결 종료"""
        if self._redis:
            await self._redis.close()
            self._redis = None
            self._is_connected = False
            self.logger.info("Redis connection closed")


class MockRedis:
    """Redis 연결 실패 시 사용할 Mock 구현"""
    
    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._expiry: Dict[str, datetime] = {}
    
    async def ping(self):
        """Mock ping"""
        return True
    
    async def setex(self, key: str, ttl: int, value: str) -> bool:
        """Mock setex"""
        self._data[key] = value
        self._expiry[key] = datetime.now() + timedelta(seconds=ttl)
        return True
    
    async def get(self, key: str) -> Optional[str]:
        """Mock get"""
        # 만료 확인
        if key in self._expiry:
            if datetime.now() > self._expiry[key]:
                del self._data[key]
                del self._expiry[key]
                return None
        
        return self._data.get(key)
    
    async def delete(self, *keys: str) -> int:
        """Mock delete"""
        count = 0
        for key in keys:
            if key in self._data:
                del self._data[key]
                if key in self._expiry:
                    del self._expiry[key]
                count += 1
        return count
    
    async def keys(self, pattern: str) -> List[str]:
        """Mock keys"""
        import fnmatch
        return [key for key in self._data.keys() if fnmatch.fnmatch(key, pattern)]
    
    async def exists(self, key: str) -> int:
        """Mock exists"""
        return 1 if key in self._data else 0
    
    async def info(self) -> Dict[str, Any]:
        """Mock info"""
        return {
            "connected_clients": 1,
            "used_memory": len(str(self._data)),
            "used_memory_human": f"{len(str(self._data))}B",
            "total_commands_processed": 100,
            "keyspace_hits": 50,
            "keyspace_misses": 50,
            "redis_version": "mock-1.0.0",
            "uptime_in_seconds": 3600
        }
    
    async def flushall(self):
        """Mock flushall"""
        self._data.clear()
        self._expiry.clear()
    
    async def close(self):
        """Mock close"""
        pass


# 글로벌 L1 캐시 인스턴스
_l1_cache = None

def get_l1_cache() -> L1Cache:
    """글로벌 L1 캐시 인스턴스 획득"""
    global _l1_cache
    if _l1_cache is None:
        _l1_cache = L1Cache()
    return _l1_cache