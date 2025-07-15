"""
Performance Dashboard
성능 대시보드
"""

import asyncio
import json
from typing import Dict, Any, List, Optional, AsyncIterator
from datetime import datetime, timedelta

from src.config import get_settings
from src.utils.logger import setup_logger
from .metrics import get_performance_metrics
from .health import get_health_checker


class PerformanceDashboard:
    """성능 대시보드 - TDD GREEN 단계 구현"""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = setup_logger("performance_dashboard")
        self.metrics = get_performance_metrics()
        self.health_checker = get_health_checker()
        
        # 알림 임계값
        self._alert_thresholds = {
            "response_time": 1.0,
            "error_rate": 5.0,
            "memory_usage": 80.0,
            "disk_usage": 90.0
        }
        
        # 실시간 스트림 구독자들
        self._subscribers = set()
    
    async def get_dashboard_data(self) -> Dict[str, Any]:
        """대시보드 데이터 생성"""
        self.logger.debug("Generating dashboard data")
        
        # 병렬로 데이터 수집
        tasks = [
            self._get_overview_data(),
            self._get_api_performance_data(),
            self._get_cache_performance_data(),
            self._get_system_health_data(),
            self._get_recent_errors_data()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        dashboard_data = {
            "timestamp": datetime.now().isoformat(),
            "overview": results[0] if not isinstance(results[0], Exception) else {},
            "api_performance": results[1] if not isinstance(results[1], Exception) else {},
            "cache_performance": results[2] if not isinstance(results[2], Exception) else {},
            "system_health": results[3] if not isinstance(results[3], Exception) else {},
            "recent_errors": results[4] if not isinstance(results[4], Exception) else []
        }
        
        return dashboard_data
    
    async def _get_overview_data(self) -> Dict[str, Any]:
        """개요 데이터 생성"""
        all_metrics = await self.metrics.get_all_metrics()
        
        # 전체 통계 계산
        total_requests = 0
        total_errors = 0
        response_times = []
        
        for endpoint, endpoint_metrics in all_metrics.get("endpoints", {}).items():
            error_stats = endpoint_metrics.get("error_rate", {})
            rt_stats = endpoint_metrics.get("response_time", {})
            
            total_requests += error_stats.get("total_requests", 0)
            total_errors += error_stats.get("error_count", 0)
            
            if rt_stats.get("count", 0) > 0:
                response_times.append(rt_stats.get("avg", 0))
        
        # 평균 응답시간 계산
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        # 에러율 계산
        error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0
        
        # 업타임 계산
        uptime_seconds = all_metrics.get("uptime_seconds", 0)
        uptime_hours = uptime_seconds / 3600
        
        return {
            "total_requests": total_requests,
            "avg_response_time": round(avg_response_time, 3),
            "error_rate": round(error_rate, 2),
            "uptime": f"{uptime_hours:.1f}h",
            "uptime_seconds": uptime_seconds,
            "active_endpoints": len(all_metrics.get("endpoints", {}))
        }
    
    async def _get_api_performance_data(self) -> Dict[str, Any]:
        """API 성능 데이터 생성"""
        all_metrics = await self.metrics.get_all_metrics()
        
        api_performance = {
            "endpoints": {}
        }
        
        for endpoint, endpoint_metrics in all_metrics.get("endpoints", {}).items():
            rt_stats = endpoint_metrics.get("response_time", {})
            throughput = endpoint_metrics.get("throughput", {})
            error_rate = endpoint_metrics.get("error_rate", {})
            
            api_performance["endpoints"][endpoint] = {
                "avg_response_time": rt_stats.get("avg", 0),
                "p95_response_time": rt_stats.get("p95", 0),
                "p99_response_time": rt_stats.get("p99", 0),
                "requests_per_second": throughput.get("requests_per_second", 0),
                "total_requests": error_rate.get("total_requests", 0),
                "error_rate": error_rate.get("error_rate", 0),
                "success_rate": error_rate.get("success_rate", 0)
            }
        
        return api_performance
    
    async def _get_cache_performance_data(self) -> Dict[str, Any]:
        """캐시 성능 데이터 생성"""
        try:
            from src.cache.hierarchical_cache import get_hierarchical_cache
            cache = get_hierarchical_cache()
            
            cache_stats = await cache.get_performance_stats()
            
            hierarchical_stats = cache_stats.get("hierarchical", {})
            l1_stats = cache_stats.get("l1_cache", {})
            l2_stats = cache_stats.get("l2_cache", {})
            
            return {
                "hierarchical": {
                    "total_hits": hierarchical_stats.get("total_hits", 0),
                    "total_misses": hierarchical_stats.get("total_misses", 0),
                    "total_hit_rate": hierarchical_stats.get("total_hit_rate", 0),
                    "l1_hits": hierarchical_stats.get("l1_hits", 0),
                    "l2_hits": hierarchical_stats.get("l2_hits", 0)
                },
                "l1_cache": {
                    "hit_rate": l1_stats.get("hit_rate", 0),
                    "memory_usage": l1_stats.get("used_memory_human", "0B"),
                    "connected_clients": l1_stats.get("connected_clients", 0)
                },
                "l2_cache": {
                    "hit_rate": l2_stats.get("hit_rate", 0),
                    "current_size": l2_stats.get("current_size", 0),
                    "max_size": l2_stats.get("max_size", 0),
                    "evictions": l2_stats.get("evictions", 0)
                }
            }
        except Exception as e:
            self.logger.error(f"Failed to get cache performance data: {e}")
            return {}
    
    async def _get_system_health_data(self) -> Dict[str, Any]:
        """시스템 헬스 데이터 생성"""
        try:
            current_health = await self.health_checker.get_current_status()
            
            if not current_health or current_health.get("status") == "unknown":
                # 헬스체크가 실행되지 않은 경우 간단한 체크 실행
                current_health = await self.health_checker.check_all()
            
            return {
                "overall_status": current_health.get("overall_status", "unknown"),
                "components": {
                    name: {
                        "status": details.get("status", "unknown"),
                        "response_time": details.get("response_time", 0)
                    }
                    for name, details in current_health.get("checks", {}).items()
                }
            }
        except Exception as e:
            self.logger.error(f"Failed to get system health data: {e}")
            return {"overall_status": "unknown", "components": {}}
    
    async def _get_recent_errors_data(self) -> List[Dict[str, Any]]:
        """최근 오류 데이터 생성"""
        # 임시 구현: 실제로는 오류 로그에서 수집
        return [
            {
                "timestamp": datetime.now().isoformat(),
                "endpoint": "get_volume_ranking",
                "error_type": "API_ERROR",
                "message": "API request timeout",
                "count": 1
            }
        ]
    
    async def get_real_time_metrics(self) -> AsyncIterator[Dict[str, Any]]:
        """실시간 메트릭 스트림"""
        while True:
            try:
                # 현재 메트릭 수집
                all_metrics = await self.metrics.get_all_metrics()
                
                # 실시간 메트릭 포맷
                real_time_data = {
                    "timestamp": datetime.now().isoformat(),
                    "metrics": {
                        "response_times": {},
                        "throughput": {},
                        "error_rates": {}
                    }
                }
                
                for endpoint, endpoint_metrics in all_metrics.get("endpoints", {}).items():
                    rt_stats = endpoint_metrics.get("response_time", {})
                    throughput = endpoint_metrics.get("throughput", {})
                    error_rate = endpoint_metrics.get("error_rate", {})
                    
                    real_time_data["metrics"]["response_times"][endpoint] = rt_stats.get("avg", 0)
                    real_time_data["metrics"]["throughput"][endpoint] = throughput.get("requests_per_second", 0)
                    real_time_data["metrics"]["error_rates"][endpoint] = error_rate.get("error_rate", 0)
                
                yield real_time_data
                
                # 1초 간격으로 업데이트
                await asyncio.sleep(1)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Real-time metrics stream error: {e}")
                await asyncio.sleep(1)
    
    async def get_historical_data(
        self, 
        start_time: datetime, 
        end_time: datetime, 
        metrics: List[str]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """과거 데이터 쿼리"""
        # 임시 구현: 실제로는 시계열 데이터베이스에서 조회
        historical_data = {}
        
        for metric_name in metrics:
            data_points = []
            
            # 시간 범위 내에서 가상 데이터 생성
            current_time = start_time
            while current_time <= end_time:
                # 가상 데이터 생성 (실제로는 저장된 데이터 조회)
                if metric_name == "response_time":
                    value = 0.5 + (hash(str(current_time)) % 100) / 1000
                elif metric_name == "throughput":
                    value = 10 + (hash(str(current_time)) % 50)
                elif metric_name == "error_rate":
                    value = (hash(str(current_time)) % 10) / 10
                else:
                    value = hash(str(current_time)) % 100
                
                data_points.append({
                    "timestamp": current_time.isoformat(),
                    "value": value
                })
                
                current_time += timedelta(minutes=1)
            
            historical_data[metric_name] = data_points
        
        return historical_data
    
    async def set_alert_threshold(self, metric_name: str, threshold: float):
        """알림 임계값 설정"""
        self._alert_thresholds[metric_name] = threshold
        self.logger.info(f"Alert threshold set: {metric_name} = {threshold}")
    
    async def get_alert_thresholds(self) -> Dict[str, float]:
        """알림 임계값 조회"""
        return dict(self._alert_thresholds)
    
    async def check_alert_conditions(self) -> List[Dict[str, Any]]:
        """알림 조건 확인"""
        alerts = []
        
        try:
            # 현재 메트릭 조회
            all_metrics = await self.metrics.get_all_metrics()
            overview_data = await self._get_overview_data()
            
            # 응답시간 임계값 확인
            if overview_data.get("avg_response_time", 0) > self._alert_thresholds.get("response_time", 1.0):
                alerts.append({
                    "type": "response_time",
                    "severity": "warning",
                    "message": f"Average response time ({overview_data['avg_response_time']:.3f}s) exceeds threshold",
                    "value": overview_data["avg_response_time"],
                    "threshold": self._alert_thresholds["response_time"]
                })
            
            # 에러율 임계값 확인
            if overview_data.get("error_rate", 0) > self._alert_thresholds.get("error_rate", 5.0):
                alerts.append({
                    "type": "error_rate",
                    "severity": "critical",
                    "message": f"Error rate ({overview_data['error_rate']:.2f}%) exceeds threshold",
                    "value": overview_data["error_rate"],
                    "threshold": self._alert_thresholds["error_rate"]
                })
            
            # 메모리 사용량 임계값 확인
            memory_stats = all_metrics.get("memory", {})
            if "system" in memory_stats:
                memory_usage = memory_stats["system"].get("used_percent", 0)
                if memory_usage > self._alert_thresholds.get("memory_usage", 80.0):
                    alerts.append({
                        "type": "memory_usage",
                        "severity": "warning",
                        "message": f"Memory usage ({memory_usage:.1f}%) exceeds threshold",
                        "value": memory_usage,
                        "threshold": self._alert_thresholds["memory_usage"]
                    })
            
        except Exception as e:
            self.logger.error(f"Failed to check alert conditions: {e}")
        
        return alerts
    
    async def export_dashboard_data(self, format: str = "json") -> str:
        """대시보드 데이터 내보내기"""
        dashboard_data = await self.get_dashboard_data()
        
        if format == "json":
            return json.dumps(dashboard_data, indent=2, ensure_ascii=False)
        elif format == "csv":
            return await self._export_csv_format(dashboard_data)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    async def _export_csv_format(self, dashboard_data: Dict[str, Any]) -> str:
        """CSV 형식으로 대시보드 데이터 내보내기"""
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 헤더 작성
        writer.writerow(["Timestamp", "Metric", "Value"])
        
        timestamp = dashboard_data["timestamp"]
        
        # 개요 데이터
        overview = dashboard_data.get("overview", {})
        for key, value in overview.items():
            writer.writerow([timestamp, f"overview_{key}", value])
        
        # API 성능 데이터
        api_performance = dashboard_data.get("api_performance", {})
        for endpoint, metrics in api_performance.get("endpoints", {}).items():
            for metric_name, value in metrics.items():
                writer.writerow([timestamp, f"api_{endpoint}_{metric_name}", value])
        
        return output.getvalue()


# 글로벌 대시보드 인스턴스
_dashboard = None

def get_dashboard() -> PerformanceDashboard:
    """글로벌 대시보드 인스턴스 획득"""
    global _dashboard
    if _dashboard is None:
        _dashboard = PerformanceDashboard()
    return _dashboard