"""
Performance Metrics Collection System
성능 메트릭 수집 시스템
"""

import asyncio
import time
import threading
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, deque
import statistics
import psutil
import os

from src.config import get_settings
from src.utils.logger import setup_logger


class PerformanceMetrics:
    """성능 메트릭 수집 및 관리 - TDD GREEN 단계 구현"""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = setup_logger("performance_metrics")
        
        # 메트릭 저장소
        self._response_times = defaultdict(lambda: deque(maxlen=1000))
        self._request_counts = defaultdict(int)
        self._error_counts = defaultdict(int)
        self._success_counts = defaultdict(int)
        self._memory_usage = defaultdict(float)
        self._custom_metrics = {}
        
        # 시간 기반 메트릭 (슬라이딩 윈도우)
        self._request_timestamps = defaultdict(lambda: deque(maxlen=1000))
        self._error_timestamps = defaultdict(lambda: deque(maxlen=1000))
        
        # 스레드 안전성
        self._lock = threading.RLock()
        
        # 시작 시간
        self._start_time = datetime.now()
    
    async def record_response_time(self, endpoint: str, duration: float):
        """응답시간 기록"""
        with self._lock:
            self._response_times[endpoint].append({
                "duration": duration,
                "timestamp": datetime.now()
            })
        
        self.logger.debug(f"Response time recorded: {endpoint} = {duration:.3f}s")
    
    async def record_request(self, endpoint: str):
        """요청 기록"""
        with self._lock:
            self._request_counts[endpoint] += 1
            self._request_timestamps[endpoint].append(datetime.now())
        
        self.logger.debug(f"Request recorded: {endpoint}")
    
    async def record_success(self, endpoint: str):
        """성공 기록"""
        with self._lock:
            self._success_counts[endpoint] += 1
        
        self.logger.debug(f"Success recorded: {endpoint}")
    
    async def record_error(self, endpoint: str, error_type: str = "UNKNOWN"):
        """오류 기록"""
        with self._lock:
            self._error_counts[endpoint] += 1
            self._error_timestamps[endpoint].append({
                "timestamp": datetime.now(),
                "error_type": error_type
            })
        
        self.logger.debug(f"Error recorded: {endpoint} - {error_type}")
    
    async def record_memory_usage(self, component: str, bytes_used: float):
        """메모리 사용량 기록"""
        with self._lock:
            self._memory_usage[component] = bytes_used
        
        self.logger.debug(f"Memory usage recorded: {component} = {bytes_used / (1024*1024):.2f}MB")
    
    async def record_custom_metric(self, metric_name: str, value: float):
        """커스텀 메트릭 기록"""
        with self._lock:
            self._custom_metrics[metric_name] = value
        
        self.logger.debug(f"Custom metric recorded: {metric_name} = {value}")
    
    async def get_response_time_stats(self, endpoint: str) -> Dict[str, Any]:
        """응답시간 통계 조회"""
        with self._lock:
            response_times = self._response_times[endpoint]
            
            if not response_times:
                return {
                    "count": 0,
                    "avg": 0.0,
                    "min": 0.0,
                    "max": 0.0,
                    "p50": 0.0,
                    "p95": 0.0,
                    "p99": 0.0
                }
            
            durations = [rt["duration"] for rt in response_times]
            
            return {
                "count": len(durations),
                "avg": statistics.mean(durations),
                "min": min(durations),
                "max": max(durations),
                "p50": statistics.median(durations),
                "p95": self._percentile(durations, 95),
                "p99": self._percentile(durations, 99)
            }
    
    async def get_throughput(self, endpoint: str, window_seconds: int = 60) -> Dict[str, Any]:
        """처리량 조회"""
        with self._lock:
            timestamps = self._request_timestamps[endpoint]
            
            if not timestamps:
                return {
                    "requests_per_second": 0.0,
                    "total_requests": 0,
                    "window_seconds": window_seconds
                }
            
            # 윈도우 내 요청 필터링
            cutoff_time = datetime.now() - timedelta(seconds=window_seconds)
            recent_requests = [ts for ts in timestamps if ts > cutoff_time]
            
            rps = len(recent_requests) / window_seconds if window_seconds > 0 else 0
            
            return {
                "requests_per_second": rps,
                "total_requests": len(timestamps),
                "recent_requests": len(recent_requests),
                "window_seconds": window_seconds
            }
    
    async def get_error_rate(self, endpoint: str) -> Dict[str, Any]:
        """에러율 조회"""
        with self._lock:
            total_requests = self._request_counts[endpoint]
            error_count = self._error_counts[endpoint]
            success_count = self._success_counts[endpoint]
            
            if total_requests == 0:
                return {
                    "total_requests": 0,
                    "error_count": 0,
                    "success_count": 0,
                    "error_rate": 0.0,
                    "success_rate": 0.0
                }
            
            error_rate = (error_count / total_requests) * 100
            success_rate = (success_count / total_requests) * 100
            
            return {
                "total_requests": total_requests,
                "error_count": error_count,
                "success_count": success_count,
                "error_rate": round(error_rate, 2),
                "success_rate": round(success_rate, 2)
            }
    
    async def get_memory_stats(self) -> Dict[str, Any]:
        """메모리 사용량 통계 조회"""
        with self._lock:
            memory_stats = {}
            total_bytes = 0
            
            for component, bytes_used in self._memory_usage.items():
                mb_used = bytes_used / (1024 * 1024)
                memory_stats[component] = {
                    "current_bytes": bytes_used,
                    "current_mb": round(mb_used, 2)
                }
                total_bytes += bytes_used
            
            # 시스템 메모리 정보 추가
            try:
                process = psutil.Process(os.getpid())
                memory_info = process.memory_info()
                
                memory_stats["process"] = {
                    "rss_bytes": memory_info.rss,
                    "rss_mb": round(memory_info.rss / (1024 * 1024), 2),
                    "vms_bytes": memory_info.vms,
                    "vms_mb": round(memory_info.vms / (1024 * 1024), 2)
                }
                
                system_memory = psutil.virtual_memory()
                memory_stats["system"] = {
                    "total_gb": round(system_memory.total / (1024 * 1024 * 1024), 2),
                    "available_gb": round(system_memory.available / (1024 * 1024 * 1024), 2),
                    "used_percent": system_memory.percent
                }
            except Exception as e:
                self.logger.warning(f"Failed to get system memory info: {e}")
            
            memory_stats["total_mb"] = round(total_bytes / (1024 * 1024), 2)
            
            return memory_stats
    
    async def get_custom_metrics(self) -> Dict[str, Any]:
        """커스텀 메트릭 조회"""
        with self._lock:
            return dict(self._custom_metrics)
    
    async def get_all_metrics(self) -> Dict[str, Any]:
        """모든 메트릭 조회"""
        all_metrics = {
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": (datetime.now() - self._start_time).total_seconds(),
            "endpoints": {}
        }
        
        # 모든 엔드포인트 메트릭 수집
        all_endpoints = set()
        with self._lock:
            all_endpoints.update(self._response_times.keys())
            all_endpoints.update(self._request_counts.keys())
            all_endpoints.update(self._error_counts.keys())
        
        for endpoint in all_endpoints:
            all_metrics["endpoints"][endpoint] = {
                "response_time": await self.get_response_time_stats(endpoint),
                "throughput": await self.get_throughput(endpoint),
                "error_rate": await self.get_error_rate(endpoint)
            }
        
        # 시스템 메트릭 추가
        all_metrics["memory"] = await self.get_memory_stats()
        all_metrics["custom"] = await self.get_custom_metrics()
        
        return all_metrics
    
    def _percentile(self, data: List[float], percentile: float) -> float:
        """백분위수 계산"""
        if not data:
            return 0.0
        
        sorted_data = sorted(data)
        index = (percentile / 100) * (len(sorted_data) - 1)
        
        if index.is_integer():
            return sorted_data[int(index)]
        else:
            lower_index = int(index)
            upper_index = lower_index + 1
            weight = index - lower_index
            
            if upper_index < len(sorted_data):
                return sorted_data[lower_index] * (1 - weight) + sorted_data[upper_index] * weight
            else:
                return sorted_data[lower_index]
    
    async def reset_metrics(self):
        """메트릭 초기화"""
        with self._lock:
            self._response_times.clear()
            self._request_counts.clear()
            self._error_counts.clear()
            self._success_counts.clear()
            self._memory_usage.clear()
            self._custom_metrics.clear()
            self._request_timestamps.clear()
            self._error_timestamps.clear()
            self._start_time = datetime.now()
        
        self.logger.info("All metrics reset")
    
    async def export_metrics(self, format: str = "json") -> str:
        """메트릭 내보내기"""
        all_metrics = await self.get_all_metrics()
        
        if format == "json":
            import json
            return json.dumps(all_metrics, indent=2, ensure_ascii=False)
        elif format == "prometheus":
            return await self._export_prometheus_format(all_metrics)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    async def _export_prometheus_format(self, metrics: Dict[str, Any]) -> str:
        """Prometheus 형식으로 메트릭 내보내기"""
        lines = []
        
        # 응답시간 메트릭
        for endpoint, endpoint_metrics in metrics["endpoints"].items():
            rt_stats = endpoint_metrics["response_time"]
            lines.append(f'response_time_seconds_avg{{endpoint="{endpoint}"}} {rt_stats["avg"]}')
            lines.append(f'response_time_seconds_p95{{endpoint="{endpoint}"}} {rt_stats["p95"]}')
            lines.append(f'response_time_seconds_p99{{endpoint="{endpoint}"}} {rt_stats["p99"]}')
            
            # 처리량 메트릭
            throughput = endpoint_metrics["throughput"]
            lines.append(f'requests_per_second{{endpoint="{endpoint}"}} {throughput["requests_per_second"]}')
            
            # 에러율 메트릭
            error_rate = endpoint_metrics["error_rate"]
            lines.append(f'error_rate_percent{{endpoint="{endpoint}"}} {error_rate["error_rate"]}')
        
        # 메모리 메트릭
        if "process" in metrics["memory"]:
            process_mem = metrics["memory"]["process"]
            lines.append(f'memory_rss_bytes {process_mem["rss_bytes"]}')
            lines.append(f'memory_vms_bytes {process_mem["vms_bytes"]}')
        
        # 커스텀 메트릭
        for metric_name, value in metrics["custom"].items():
            lines.append(f'{metric_name} {value}')
        
        return "\n".join(lines)


# 글로벌 성능 메트릭 인스턴스
_performance_metrics = None

def get_performance_metrics() -> PerformanceMetrics:
    """글로벌 성능 메트릭 인스턴스 획득"""
    global _performance_metrics
    if _performance_metrics is None:
        _performance_metrics = PerformanceMetrics()
    return _performance_metrics