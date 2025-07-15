"""
Metrics Storage System - Basic Implementation
메트릭 저장소 시스템 - 기본 구현
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from src.config import get_settings
from src.utils.logger import setup_logger


class MetricsStorage:
    """메트릭 저장소 - 기본 구현"""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = setup_logger("metrics_storage")
        
        # 메모리 기반 저장소
        self._metrics_data = {}
        self._retention_policies = {}
    
    async def store_metric(self, metric_name: str, value: float, timestamp: datetime, tags: Optional[Dict[str, str]] = None):
        """메트릭 저장"""
        if metric_name not in self._metrics_data:
            self._metrics_data[metric_name] = []
        
        self._metrics_data[metric_name].append({
            "timestamp": timestamp,
            "value": value,
            "tags": tags or {}
        })
        
        self.logger.debug(f"Metric stored: {metric_name} = {value}")
    
    async def query_metrics(self, metric_name: str, start_time: datetime, end_time: datetime, tags: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """메트릭 쿼리"""
        if metric_name not in self._metrics_data:
            return []
        
        filtered_data = []
        for data_point in self._metrics_data[metric_name]:
            if start_time <= data_point["timestamp"] <= end_time:
                # 태그 필터링
                if tags:
                    if all(data_point["tags"].get(k) == v for k, v in tags.items()):
                        filtered_data.append(data_point)
                else:
                    filtered_data.append(data_point)
        
        return filtered_data
    
    async def aggregate_metrics(self, metric_name: str, start_time: datetime, end_time: datetime, granularity: str, aggregation_function: str) -> List[Dict[str, Any]]:
        """메트릭 집계"""
        data_points = await self.query_metrics(metric_name, start_time, end_time)
        
        if not data_points:
            return []
        
        # 간단한 집계 구현
        values = [dp["value"] for dp in data_points]
        
        if aggregation_function == "avg":
            avg_value = sum(values) / len(values)
        elif aggregation_function == "sum":
            avg_value = sum(values)
        elif aggregation_function == "max":
            avg_value = max(values)
        elif aggregation_function == "min":
            avg_value = min(values)
        else:
            avg_value = sum(values) / len(values)
        
        return [{
            "timestamp": start_time.isoformat(),
            "avg": avg_value,
            "min": min(values),
            "max": max(values),
            "count": len(values)
        }]
    
    async def set_retention_policy(self, metric_name: str, retention_days: int):
        """보존 정책 설정"""
        self._retention_policies[metric_name] = retention_days
        self.logger.info(f"Retention policy set: {metric_name} = {retention_days} days")
    
    async def cleanup_old_metrics(self) -> int:
        """오래된 메트릭 정리"""
        deleted_count = 0
        cutoff_time = datetime.now() - timedelta(days=30)  # 기본 30일
        
        for metric_name, data_points in self._metrics_data.items():
            retention_days = self._retention_policies.get(metric_name, 30)
            metric_cutoff = datetime.now() - timedelta(days=retention_days)
            
            original_count = len(data_points)
            self._metrics_data[metric_name] = [
                dp for dp in data_points if dp["timestamp"] > metric_cutoff
            ]
            deleted_count += original_count - len(self._metrics_data[metric_name])
        
        self.logger.info(f"Cleaned up {deleted_count} old metrics")
        return deleted_count