"""
Health Check System
헬스체크 시스템
"""

import asyncio
import time
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import psutil
import os

from src.config import get_settings
from src.utils.logger import setup_logger
from src.cache.hierarchical_cache import get_hierarchical_cache
from src.api.client import VolumeRankingAPI


class HealthChecker:
    """헬스체크 시스템 - TDD GREEN 단계 구현"""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = setup_logger("health_checker")
        
        # 헬스체크 결과 저장소
        self._health_results = {}
        self._recent_results = []
        
        # 스케줄링 관련
        self._scheduled_task = None
        self._is_running = False
        self._lock = threading.RLock()
        
        # 컴포넌트별 임계값
        self._thresholds = {
            "response_time": 2.0,  # 2초
            "memory_usage": 80.0,  # 80%
            "disk_usage": 90.0,    # 90%
            "cache_hit_rate": 50.0  # 50%
        }
    
    async def check_all(self) -> Dict[str, Any]:
        """전체 헬스체크 실행"""
        start_time = datetime.now()
        
        self.logger.info("Starting comprehensive health check")
        
        health_results = {
            "timestamp": start_time.isoformat(),
            "overall_status": "healthy",
            "checks": {}
        }
        
        # 병렬로 헬스체크 실행
        check_tasks = [
            ("cache", self.check_cache()),
            ("api", self.check_api()),
            ("memory", self.check_memory()),
            ("disk", self.check_disk()),
            ("database", self.check_database())
        ]
        
        results = await asyncio.gather(*[task[1] for task in check_tasks], return_exceptions=True)
        
        # 결과 취합
        degraded_count = 0
        unhealthy_count = 0
        
        for i, (component_name, _) in enumerate(check_tasks):
            result = results[i]
            
            if isinstance(result, Exception):
                health_results["checks"][component_name] = {
                    "status": "unhealthy",
                    "error": str(result),
                    "response_time": None
                }
                unhealthy_count += 1
            else:
                health_results["checks"][component_name] = result
                
                if result["status"] == "degraded":
                    degraded_count += 1
                elif result["status"] == "unhealthy":
                    unhealthy_count += 1
        
        # 전체 상태 결정
        if unhealthy_count > 0:
            health_results["overall_status"] = "unhealthy"
        elif degraded_count > 0:
            health_results["overall_status"] = "degraded"
        else:
            health_results["overall_status"] = "healthy"
        
        # 실행 시간 추가
        execution_time = (datetime.now() - start_time).total_seconds()
        health_results["execution_time"] = execution_time
        
        # 결과 저장
        with self._lock:
            self._health_results = health_results
            self._recent_results.append(health_results)
            
            # 최근 결과 100개만 유지
            if len(self._recent_results) > 100:
                self._recent_results.pop(0)
        
        self.logger.info(f"Health check completed: {health_results['overall_status']} (took {execution_time:.2f}s)")
        
        return health_results
    
    async def check_cache(self) -> Dict[str, Any]:
        """캐시 헬스체크"""
        start_time = time.time()
        
        try:
            cache = get_hierarchical_cache()
            
            # 캐시 상태 확인
            cache_health = await cache.health_check()
            
            # 캐시 성능 통계 확인
            cache_stats = await cache.get_performance_stats()
            
            response_time = time.time() - start_time
            
            # 캐시 히트율 계산
            hierarchical_stats = cache_stats.get("hierarchical", {})
            total_hits = hierarchical_stats.get("total_hits", 0)
            total_misses = hierarchical_stats.get("total_misses", 0)
            total_requests = total_hits + total_misses
            
            hit_rate = (total_hits / total_requests * 100) if total_requests > 0 else 0
            
            # 상태 결정
            status = "healthy"
            if response_time > self._thresholds["response_time"]:
                status = "degraded"
            elif hit_rate < self._thresholds["cache_hit_rate"]:
                status = "degraded"
            elif cache_health["overall_status"] != "healthy":
                status = "unhealthy"
            
            return {
                "status": status,
                "response_time": response_time,
                "hit_rate": hit_rate,
                "l1_status": cache_health["l1_cache"]["status"],
                "l2_status": cache_health["l2_cache"]["status"],
                "details": cache_stats
            }
            
        except Exception as e:
            self.logger.error(f"Cache health check failed: {e}")
            return {
                "status": "unhealthy",
                "response_time": time.time() - start_time,
                "error": str(e)
            }
    
    async def check_api(self) -> Dict[str, Any]:
        """API 헬스체크"""
        start_time = time.time()
        
        try:
            # API 클라이언트 생성 및 테스트
            api_client = VolumeRankingAPI()
            
            # 간단한 API 호출 테스트 (토큰 요청)
            try:
                await api_client._get_access_token()
                api_status = "healthy"
                last_successful_call = datetime.now()
            except Exception as e:
                api_status = "degraded"
                last_successful_call = None
                self.logger.warning(f"API test call failed: {e}")
            
            response_time = time.time() - start_time
            
            # 상태 결정
            status = "healthy"
            if response_time > self._thresholds["response_time"]:
                status = "degraded"
            elif api_status != "healthy":
                status = "degraded"
            
            return {
                "status": status,
                "response_time": response_time,
                "api_status": api_status,
                "last_successful_call": last_successful_call.isoformat() if last_successful_call else None
            }
            
        except Exception as e:
            self.logger.error(f"API health check failed: {e}")
            return {
                "status": "unhealthy",
                "response_time": time.time() - start_time,
                "error": str(e)
            }
    
    async def check_memory(self) -> Dict[str, Any]:
        """메모리 헬스체크"""
        start_time = time.time()
        
        try:
            # 프로세스 메모리 정보
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            
            # 시스템 메모리 정보
            system_memory = psutil.virtual_memory()
            
            # 메모리 사용률 계산
            memory_usage_percent = system_memory.percent
            
            # 상태 결정
            status = "healthy"
            if memory_usage_percent > self._thresholds["memory_usage"]:
                status = "degraded"
            elif memory_usage_percent > 95:
                status = "unhealthy"
            
            response_time = time.time() - start_time
            
            return {
                "status": status,
                "response_time": response_time,
                "system_memory": {
                    "total_gb": round(system_memory.total / (1024**3), 2),
                    "available_gb": round(system_memory.available / (1024**3), 2),
                    "used_percent": memory_usage_percent
                },
                "process_memory": {
                    "rss_mb": round(memory_info.rss / (1024**2), 2),
                    "vms_mb": round(memory_info.vms / (1024**2), 2)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Memory health check failed: {e}")
            return {
                "status": "unhealthy",
                "response_time": time.time() - start_time,
                "error": str(e)
            }
    
    async def check_disk(self) -> Dict[str, Any]:
        """디스크 헬스체크"""
        start_time = time.time()
        
        try:
            # 현재 디렉토리의 디스크 사용량 확인
            disk_usage = psutil.disk_usage('/')
            
            # 사용률 계산
            disk_usage_percent = (disk_usage.used / disk_usage.total) * 100
            
            # 상태 결정
            status = "healthy"
            if disk_usage_percent > self._thresholds["disk_usage"]:
                status = "degraded"
            elif disk_usage_percent > 98:
                status = "unhealthy"
            
            response_time = time.time() - start_time
            
            return {
                "status": status,
                "response_time": response_time,
                "disk_usage": {
                    "total_gb": round(disk_usage.total / (1024**3), 2),
                    "used_gb": round(disk_usage.used / (1024**3), 2),
                    "free_gb": round(disk_usage.free / (1024**3), 2),
                    "used_percent": round(disk_usage_percent, 2)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Disk health check failed: {e}")
            return {
                "status": "unhealthy",
                "response_time": time.time() - start_time,
                "error": str(e)
            }
    
    async def check_database(self) -> Dict[str, Any]:
        """데이터베이스 헬스체크 (현재는 파일 시스템 기반)"""
        start_time = time.time()
        
        try:
            # 로그 파일 디렉토리 확인
            log_dir = self.settings.log_file_path or "/tmp"
            log_dir = os.path.dirname(log_dir) if os.path.isfile(log_dir) else log_dir
            
            # 디렉토리 접근 가능성 확인
            if os.path.exists(log_dir) and os.access(log_dir, os.W_OK):
                status = "healthy"
            else:
                status = "degraded"
            
            response_time = time.time() - start_time
            
            return {
                "status": status,
                "response_time": response_time,
                "log_directory": log_dir,
                "writeable": os.access(log_dir, os.W_OK) if os.path.exists(log_dir) else False
            }
            
        except Exception as e:
            self.logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "response_time": time.time() - start_time,
                "error": str(e)
            }
    
    async def start_scheduled_checks(self, interval_seconds: int = 60):
        """스케줄된 헬스체크 시작"""
        if self._is_running:
            self.logger.warning("Scheduled health checks already running")
            return
        
        self._is_running = True
        self._scheduled_task = asyncio.create_task(self._scheduled_check_loop(interval_seconds))
        
        self.logger.info(f"Started scheduled health checks (interval: {interval_seconds}s)")
    
    async def stop_scheduled_checks(self):
        """스케줄된 헬스체크 중지"""
        if not self._is_running:
            return
        
        self._is_running = False
        
        if self._scheduled_task:
            self._scheduled_task.cancel()
            try:
                await self._scheduled_task
            except asyncio.CancelledError:
                pass
            self._scheduled_task = None
        
        self.logger.info("Stopped scheduled health checks")
    
    def is_scheduled_running(self) -> bool:
        """스케줄된 헬스체크 실행 상태"""
        return self._is_running
    
    async def get_recent_results(self, limit: int = 10) -> List[Dict[str, Any]]:
        """최근 헬스체크 결과 조회"""
        with self._lock:
            return self._recent_results[-limit:] if limit > 0 else self._recent_results[:]
    
    async def get_current_status(self) -> Dict[str, Any]:
        """현재 헬스체크 상태"""
        with self._lock:
            return self._health_results if self._health_results else {"status": "unknown"}
    
    async def _scheduled_check_loop(self, interval_seconds: int):
        """스케줄된 헬스체크 루프"""
        while self._is_running:
            try:
                await self.check_all()
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Scheduled health check failed: {e}")
                await asyncio.sleep(interval_seconds)
    
    def set_threshold(self, component: str, value: float):
        """임계값 설정"""
        if component in self._thresholds:
            self._thresholds[component] = value
            self.logger.info(f"Threshold updated: {component} = {value}")
        else:
            self.logger.warning(f"Unknown threshold component: {component}")
    
    def get_thresholds(self) -> Dict[str, float]:
        """현재 임계값 조회"""
        return dict(self._thresholds)


# 글로벌 헬스체커 인스턴스
_health_checker = None

def get_health_checker() -> HealthChecker:
    """글로벌 헬스체커 인스턴스 획득"""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker