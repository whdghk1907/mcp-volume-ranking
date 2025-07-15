"""
Cache Decorators
캐시 데코레이터
"""

import functools
import inspect
from typing import Any, Callable, Optional, Dict, Union
from datetime import datetime

from src.utils.logger import setup_logger
from .hierarchical_cache import HierarchicalCache, get_hierarchical_cache
from .key_generator import CacheKeyGenerator, get_key_generator


logger = setup_logger("cache_decorators")


def cache_result(
    ttl: Optional[int] = None,
    key_prefix: Optional[str] = None,
    condition: Optional[Callable[[Any], bool]] = None,
    cache_instance: Optional[HierarchicalCache] = None,
    key_generator: Optional[CacheKeyGenerator] = None
):
    """
    함수 결과를 캐시하는 데코레이터
    
    Args:
        ttl: 캐시 만료 시간 (초)
        key_prefix: 캐시 키 접두사
        condition: 캐시 조건 함수 (결과를 받아서 bool 반환)
        cache_instance: 사용할 캐시 인스턴스
        key_generator: 키 생성기 인스턴스
        
    Returns:
        데코레이터 함수
    """
    def decorator(func: Callable) -> Callable:
        # 캐시 인스턴스 초기화
        cache = cache_instance or get_hierarchical_cache()
        keygen = key_generator or get_key_generator()
        
        # 함수 시그니처 분석
        sig = inspect.signature(func)
        func_name = func.__name__
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                # 바인드된 인수들 가져오기
                bound_args = sig.bind(*args, **kwargs)
                bound_args.apply_defaults()
                
                # 캐시 키 생성
                cache_key = _generate_cache_key(
                    func_name, 
                    bound_args.arguments, 
                    key_prefix, 
                    keygen
                )
                
                # 캐시에서 조회
                cached_result = await cache.get(cache_key)
                if cached_result is not None:
                    logger.debug(f"Cache hit for {func_name}: {cache_key}")
                    return cached_result
                
                # 함수 실행
                logger.debug(f"Cache miss for {func_name}: {cache_key}")
                result = await func(*args, **kwargs)
                
                # 캐시 조건 확인
                if condition is None or condition(result):
                    # 캐시에 저장
                    try:
                        await cache.set(cache_key, result, ttl)
                        logger.debug(f"Cached result for {func_name}: {cache_key}")
                    except Exception as e:
                        logger.warning(f"Failed to cache result for {func_name}: {cache_key}, error: {str(e)}")
                
                return result
                
            except Exception as e:
                logger.error(f"Cache decorator error for {func_name}: {str(e)}")
                # 캐시 오류 시 원본 함수 실행
                return await func(*args, **kwargs)
        
        # 캐시 무효화 메서드 추가
        wrapper.invalidate_cache = lambda *args, **kwargs: invalidate_cache(func_name, *args, **kwargs)
        wrapper.cache_key = lambda *args, **kwargs: _generate_cache_key(
            func_name, 
            sig.bind(*args, **kwargs).arguments, 
            key_prefix, 
            keygen
        )
        
        return wrapper
    
    return decorator


async def invalidate_cache(func_name: str, *args, **kwargs) -> bool:
    """
    특정 함수의 캐시 무효화
    
    Args:
        func_name: 함수 이름
        *args: 함수 인수
        **kwargs: 함수 키워드 인수
        
    Returns:
        무효화 성공 여부
    """
    try:
        cache = get_hierarchical_cache()
        keygen = get_key_generator()
        
        # 캐시 키 생성
        cache_key = _generate_cache_key(func_name, kwargs, None, keygen)
        
        # 캐시 무효화
        result = await cache.invalidate(cache_key)
        
        if result:
            logger.debug(f"Cache invalidated for {func_name}: {cache_key}")
        else:
            logger.debug(f"Cache key not found for {func_name}: {cache_key}")
        
        return result
        
    except Exception as e:
        logger.error(f"Cache invalidation failed for {func_name}: {str(e)}")
        return False


async def invalidate_pattern(pattern: str) -> int:
    """
    패턴에 매칭되는 캐시 무효화
    
    Args:
        pattern: 무효화할 키 패턴
        
    Returns:
        무효화된 키의 개수
    """
    try:
        cache = get_hierarchical_cache()
        return await cache.invalidate_pattern(pattern)
        
    except Exception as e:
        logger.error(f"Cache pattern invalidation failed: {pattern}, error: {str(e)}")
        return 0


def _generate_cache_key(
    func_name: str, 
    arguments: Dict[str, Any], 
    key_prefix: Optional[str],
    keygen: CacheKeyGenerator
) -> str:
    """
    캐시 키 생성
    
    Args:
        func_name: 함수 이름
        arguments: 함수 인수들
        key_prefix: 키 접두사
        keygen: 키 생성기
        
    Returns:
        생성된 캐시 키
    """
    try:
        # 접두사 설정
        if key_prefix:
            base_key = f"{key_prefix}:{func_name}"
        else:
            base_key = func_name
        
        # self 인수 제거 (클래스 메서드인 경우)
        filtered_args = {k: v for k, v in arguments.items() if k != 'self'}
        
        # 키 생성
        if filtered_args:
            cache_key = keygen.generate_generic_key(base_key, **filtered_args)
        else:
            cache_key = base_key
        
        return cache_key
        
    except Exception as e:
        logger.error(f"Cache key generation failed: {func_name}, error: {str(e)}")
        # 폴백 키 생성
        return f"{func_name}:{hash(str(arguments))}"


def cache_method(
    ttl: Optional[int] = None,
    key_prefix: Optional[str] = None,
    condition: Optional[Callable[[Any], bool]] = None
):
    """
    클래스 메서드를 위한 캐시 데코레이터
    
    Args:
        ttl: 캐시 만료 시간 (초)
        key_prefix: 캐시 키 접두사
        condition: 캐시 조건 함수
        
    Returns:
        데코레이터 함수
    """
    def decorator(method: Callable) -> Callable:
        @functools.wraps(method)
        async def wrapper(self, *args, **kwargs):
            # 클래스 이름을 키 접두사에 추가
            class_name = self.__class__.__name__
            method_name = method.__name__
            
            full_key_prefix = f"{class_name}:{method_name}"
            if key_prefix:
                full_key_prefix = f"{key_prefix}:{full_key_prefix}"
            
            # cache_result 데코레이터 적용
            cached_method = cache_result(
                ttl=ttl,
                key_prefix=full_key_prefix,
                condition=condition
            )(method)
            
            return await cached_method(self, *args, **kwargs)
        
        return wrapper
    
    return decorator


def cache_invalidate_on_update(cache_key_func: Callable):
    """
    업데이트 시 캐시 무효화 데코레이터
    
    Args:
        cache_key_func: 무효화할 캐시 키를 반환하는 함수
        
    Returns:
        데코레이터 함수
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                # 함수 실행
                result = await func(*args, **kwargs)
                
                # 캐시 키 생성
                cache_key = cache_key_func(*args, **kwargs)
                
                # 캐시 무효화
                if cache_key:
                    cache = get_hierarchical_cache()
                    await cache.invalidate(cache_key)
                    logger.debug(f"Cache invalidated after update: {cache_key}")
                
                return result
                
            except Exception as e:
                logger.error(f"Cache invalidation on update failed: {str(e)}")
                return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def cache_warm_on_startup(warm_data_func: Callable):
    """
    시작 시 캐시 워밍 데코레이터
    
    Args:
        warm_data_func: 워밍할 데이터를 반환하는 함수
        
    Returns:
        데코레이터 함수
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                # 캐시 워밍
                warm_data = await warm_data_func(*args, **kwargs)
                if warm_data:
                    cache = get_hierarchical_cache()
                    warmed_count = await cache.warm_cache(warm_data)
                    logger.info(f"Cache warmed {warmed_count} keys on startup")
                
                # 함수 실행
                return await func(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"Cache warming on startup failed: {str(e)}")
                return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator


class CacheStats:
    """캐시 통계 수집 클래스"""
    
    def __init__(self):
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "invalidations": 0,
            "errors": 0
        }
    
    def record_hit(self):
        """캐시 히트 기록"""
        self.stats["hits"] += 1
    
    def record_miss(self):
        """캐시 미스 기록"""
        self.stats["misses"] += 1
    
    def record_set(self):
        """캐시 설정 기록"""
        self.stats["sets"] += 1
    
    def record_invalidation(self):
        """캐시 무효화 기록"""
        self.stats["invalidations"] += 1
    
    def record_error(self):
        """캐시 오류 기록"""
        self.stats["errors"] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """통계 정보 반환"""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = 0.0
        
        if total_requests > 0:
            hit_rate = (self.stats["hits"] / total_requests) * 100.0
        
        return {
            **self.stats,
            "total_requests": total_requests,
            "hit_rate": hit_rate,
            "timestamp": datetime.now().isoformat()
        }
    
    def reset(self):
        """통계 초기화"""
        for key in self.stats:
            self.stats[key] = 0


# 글로벌 캐시 통계 인스턴스
_cache_stats = CacheStats()

def get_cache_stats() -> CacheStats:
    """글로벌 캐시 통계 인스턴스 획득"""
    return _cache_stats