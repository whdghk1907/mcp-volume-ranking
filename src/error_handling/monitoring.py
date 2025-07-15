"""
Error Monitoring System - TDD Implementation
오류 모니터링 시스템 - TDD 구현
"""

import asyncio
import time
import statistics
from typing import Dict, Any, List, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque, defaultdict
from enum import Enum
import re

from src.utils.logger import setup_logger


class AlertSeverity(Enum):
    """알림 심각도"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ErrorEvent:
    """오류 이벤트"""
    timestamp: datetime
    error_type: str
    endpoint: Optional[str]
    message: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Alert:
    """알림"""
    id: str
    rule: str
    severity: AlertSeverity
    message: str
    triggered_at: datetime
    data: Dict[str, Any] = field(default_factory=dict)


class ErrorRateMonitor:
    """오류율 모니터링"""
    
    def __init__(self, window_size: int = 300):  # 5분 윈도우
        self.window_size = window_size
        self.success_events: Dict[str, deque] = defaultdict(lambda: deque())
        self.error_events: Dict[str, deque] = defaultdict(lambda: deque())
        self.logger = setup_logger("error_rate_monitor")
    
    async def record_success(self, endpoint: str):
        """성공 기록"""
        current_time = time.time()
        self.success_events[endpoint].append(current_time)
        await self._cleanup_old_events(endpoint)
    
    async def record_error(self, endpoint: str, error_type: str):
        """오류 기록"""
        current_time = time.time()
        self.error_events[endpoint].append((current_time, error_type))
        await self._cleanup_old_events(endpoint)
    
    async def _cleanup_old_events(self, endpoint: str):
        """오래된 이벤트 정리"""
        current_time = time.time()
        cutoff_time = current_time - self.window_size
        
        # 성공 이벤트 정리
        while (self.success_events[endpoint] and 
               self.success_events[endpoint][0] < cutoff_time):
            self.success_events[endpoint].popleft()
        
        # 오류 이벤트 정리
        while (self.error_events[endpoint] and 
               self.error_events[endpoint][0][0] < cutoff_time):
            self.error_events[endpoint].popleft()
    
    async def get_error_rate_stats(self, endpoint: str) -> Dict[str, Any]:
        """오류율 통계"""
        await self._cleanup_old_events(endpoint)
        
        success_count = len(self.success_events[endpoint])
        error_count = len(self.error_events[endpoint])
        total_requests = success_count + error_count
        
        error_rate = error_count / total_requests if total_requests > 0 else 0
        
        # 오류 유형별 집계
        error_types = {}
        for _, error_type in self.error_events[endpoint]:
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        return {
            "endpoint": endpoint,
            "window_size_seconds": self.window_size,
            "total_requests": total_requests,
            "success_count": success_count,
            "error_count": error_count,
            "error_rate": round(error_rate, 4),
            "error_types": error_types
        }
    
    async def get_all_endpoints_stats(self) -> Dict[str, Dict[str, Any]]:
        """모든 엔드포인트 통계"""
        all_endpoints = set(self.success_events.keys()) | set(self.error_events.keys())
        
        stats = {}
        for endpoint in all_endpoints:
            stats[endpoint] = await self.get_error_rate_stats(endpoint)
        
        return stats


class ErrorPatternDetector:
    """오류 패턴 감지기"""
    
    def __init__(self, max_events: int = 1000):
        self.max_events = max_events
        self.error_history: List[ErrorEvent] = []
        self.logger = setup_logger("error_pattern_detector")
    
    async def record_error(self, error_type: str, endpoint: Optional[str] = None, 
                          timestamp: Optional[datetime] = None, message: str = "",
                          **metadata):
        """오류 기록"""
        event = ErrorEvent(
            timestamp=timestamp or datetime.now(),
            error_type=error_type,
            endpoint=endpoint,
            message=message,
            metadata=metadata
        )
        
        self.error_history.append(event)
        
        # 최대 이벤트 수 제한
        if len(self.error_history) > self.max_events:
            self.error_history = self.error_history[-self.max_events:]
    
    async def detect_patterns(self) -> List[Dict[str, Any]]:
        """패턴 감지"""
        patterns = []
        
        # 주기적 패턴 감지
        periodic_patterns = await self._detect_periodic_patterns()
        patterns.extend(periodic_patterns)
        
        # 급증 패턴 감지
        spike_patterns = await self._detect_spike_patterns()
        patterns.extend(spike_patterns)
        
        # 연쇄 실패 패턴 감지
        cascade_patterns = await self._detect_cascade_patterns()
        patterns.extend(cascade_patterns)
        
        return patterns
    
    async def _detect_periodic_patterns(self) -> List[Dict[str, Any]]:
        """주기적 패턴 감지"""
        if len(self.error_history) < 10:
            return []
        
        # 시간 간격 분석
        timestamps = [event.timestamp for event in self.error_history[-50:]]  # 최근 50개
        intervals = []
        
        for i in range(1, len(timestamps)):
            interval = (timestamps[i] - timestamps[i-1]).total_seconds() / 60  # 분 단위
            intervals.append(interval)
        
        if not intervals:
            return []
        
        # 주기성 검사 (비슷한 간격이 반복되는지)
        interval_counts = {}
        for interval in intervals:
            # 1분 단위로 반올림
            rounded = round(interval)
            interval_counts[rounded] = interval_counts.get(rounded, 0) + 1
        
        patterns = []
        for interval_min, count in interval_counts.items():
            if count >= 3 and interval_min > 0:  # 최소 3번 반복
                confidence = min(count / len(intervals), 1.0)
                if confidence > 0.3:
                    patterns.append({
                        "type": "periodic",
                        "interval_minutes": interval_min,
                        "occurrences": count,
                        "confidence": round(confidence, 2),
                        "description": f"Errors occurring every {interval_min} minutes"
                    })
        
        return patterns
    
    async def _detect_spike_patterns(self) -> List[Dict[str, Any]]:
        """급증 패턴 감지"""
        if len(self.error_history) < 20:
            return []
        
        # 시간대별 오류 수 계산
        hourly_counts = defaultdict(int)
        
        for event in self.error_history[-100:]:  # 최근 100개
            hour = event.timestamp.replace(minute=0, second=0, microsecond=0)
            hourly_counts[hour] += 1
        
        if len(hourly_counts) < 3:
            return []
        
        counts = list(hourly_counts.values())
        avg_count = statistics.mean(counts)
        
        patterns = []
        for hour, count in hourly_counts.items():
            if count > avg_count * 3:  # 평균의 3배 이상
                patterns.append({
                    "type": "spike",
                    "timestamp": hour.isoformat(),
                    "error_count": count,
                    "average_count": round(avg_count, 1),
                    "spike_ratio": round(count / avg_count, 2),
                    "confidence": min(count / avg_count / 3, 1.0),
                    "description": f"Error spike detected at {hour.strftime('%Y-%m-%d %H:%M')}"
                })
        
        return patterns
    
    async def _detect_cascade_patterns(self) -> List[Dict[str, Any]]:
        """연쇄 실패 패턴 감지"""
        if len(self.error_history) < 5:
            return []
        
        # 짧은 시간 내 여러 엔드포인트 실패
        recent_events = [e for e in self.error_history 
                        if (datetime.now() - e.timestamp).total_seconds() < 300]  # 5분 이내
        
        if len(recent_events) < 5:
            return []
        
        # 엔드포인트별 오류 수
        endpoint_errors = defaultdict(int)
        for event in recent_events:
            if event.endpoint:
                endpoint_errors[event.endpoint] += 1
        
        # 여러 엔드포인트에서 동시에 오류 발생
        affected_endpoints = len([ep for ep, count in endpoint_errors.items() if count >= 2])
        
        patterns = []
        if affected_endpoints >= 3:
            patterns.append({
                "type": "cascade",
                "affected_endpoints": affected_endpoints,
                "total_errors": len(recent_events),
                "time_window_minutes": 5,
                "confidence": min(affected_endpoints / 10, 1.0),
                "endpoint_errors": dict(endpoint_errors),
                "description": f"Cascade failure affecting {affected_endpoints} endpoints"
            })
        
        return patterns


class ErrorAlertManager:
    """오류 알림 관리자"""
    
    def __init__(self):
        self.rules: Dict[str, Dict[str, Any]] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.error_monitor = ErrorRateMonitor()
        self.logger = setup_logger("error_alert_manager")
        self._alert_counter = 0
    
    async def add_rule(self, name: str, condition: Callable[[Dict[str, Any]], bool], 
                      severity: str = "warning", cooldown_minutes: int = 10):
        """알림 규칙 추가"""
        self.rules[name] = {
            "condition": condition,
            "severity": AlertSeverity(severity),
            "cooldown_minutes": cooldown_minutes,
            "last_triggered": None
        }
        
        self.logger.info(f"Added alert rule: {name} (severity: {severity})")
    
    async def record_success(self, endpoint: str):
        """성공 기록"""
        await self.error_monitor.record_success(endpoint)
    
    async def record_error(self, endpoint: str, error_type: str):
        """오류 기록"""
        await self.error_monitor.record_error(endpoint, error_type)
    
    async def check_alerts(self) -> List[Alert]:
        """알림 확인"""
        triggered_alerts = []
        
        # 모든 엔드포인트 통계 가져오기
        all_stats = await self.error_monitor.get_all_endpoints_stats()
        
        for rule_name, rule_config in self.rules.items():
            condition = rule_config["condition"]
            severity = rule_config["severity"]
            cooldown_minutes = rule_config["cooldown_minutes"]
            last_triggered = rule_config["last_triggered"]
            
            # 쿨다운 확인
            if last_triggered:
                elapsed = (datetime.now() - last_triggered).total_seconds() / 60
                if elapsed < cooldown_minutes:
                    continue
            
            # 조건 확인
            for endpoint, stats in all_stats.items():
                if condition(stats):
                    alert = await self._create_alert(rule_name, severity, stats)
                    triggered_alerts.append(alert)
                    
                    # 규칙의 마지막 트리거 시간 업데이트
                    rule_config["last_triggered"] = datetime.now()
                    break
        
        return triggered_alerts
    
    async def _create_alert(self, rule_name: str, severity: AlertSeverity, 
                           stats: Dict[str, Any]) -> Alert:
        """알림 생성"""
        self._alert_counter += 1
        
        alert = Alert(
            id=f"alert_{self._alert_counter}",
            rule=rule_name,
            severity=severity,
            message=f"Alert triggered: {rule_name}",
            triggered_at=datetime.now(),
            data=stats
        )
        
        self.active_alerts[alert.id] = alert
        self.alert_history.append(alert)
        
        self.logger.warning(f"Alert triggered: {rule_name} (severity: {severity.value})")
        
        return alert
    
    async def acknowledge_alert(self, alert_id: str):
        """알림 확인"""
        if alert_id in self.active_alerts:
            del self.active_alerts[alert_id]
            self.logger.info(f"Alert acknowledged: {alert_id}")
    
    async def get_active_alerts(self) -> List[Alert]:
        """활성 알림 목록"""
        return list(self.active_alerts.values())
    
    async def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """알림 히스토리"""
        return self.alert_history[-limit:]


class ErrorDashboard:
    """오류 대시보드"""
    
    def __init__(self):
        self.error_monitor = ErrorRateMonitor()
        self.pattern_detector = ErrorPatternDetector()
        self.alert_manager = ErrorAlertManager()
        self.logger = setup_logger("error_dashboard")
    
    async def record_operation(self, endpoint: str, success: bool = True, 
                              error_type: Optional[str] = None, **metadata):
        """작업 기록"""
        if success:
            await self.error_monitor.record_success(endpoint)
            await self.alert_manager.record_success(endpoint)
        else:
            error_type = error_type or "unknown_error"
            await self.error_monitor.record_error(endpoint, error_type)
            await self.alert_manager.record_error(endpoint, error_type)
            await self.pattern_detector.record_error(
                error_type=error_type,
                endpoint=endpoint,
                **metadata
            )
    
    async def get_dashboard_data(self) -> Dict[str, Any]:
        """대시보드 데이터"""
        # 전체 통계
        all_stats = await self.error_monitor.get_all_endpoints_stats()
        
        # 패턴 분석
        patterns = await self.pattern_detector.detect_patterns()
        
        # 활성 알림
        active_alerts = await self.alert_manager.get_active_alerts()
        
        # 요약 통계
        total_requests = sum(stats["total_requests"] for stats in all_stats.values())
        total_errors = sum(stats["error_count"] for stats in all_stats.values())
        overall_error_rate = total_errors / total_requests if total_requests > 0 else 0
        
        # 가장 문제가 많은 엔드포인트
        problematic_endpoints = sorted(
            all_stats.items(),
            key=lambda x: x[1]["error_rate"],
            reverse=True
        )[:5]
        
        return {
            "summary": {
                "total_requests": total_requests,
                "total_errors": total_errors,
                "overall_error_rate": round(overall_error_rate, 4),
                "active_alerts": len(active_alerts),
                "detected_patterns": len(patterns)
            },
            "endpoint_stats": all_stats,
            "problematic_endpoints": [
                {"endpoint": ep, **stats} 
                for ep, stats in problematic_endpoints
            ],
            "patterns": patterns,
            "active_alerts": [
                {
                    "id": alert.id,
                    "rule": alert.rule,
                    "severity": alert.severity.value,
                    "message": alert.message,
                    "triggered_at": alert.triggered_at.isoformat()
                }
                for alert in active_alerts
            ],
            "generated_at": datetime.now().isoformat()
        }
    
    async def setup_default_alerts(self):
        """기본 알림 설정"""
        # 높은 오류율 알림
        await self.alert_manager.add_rule(
            name="high_error_rate",
            condition=lambda stats: stats["error_rate"] > 0.1,  # 10% 이상
            severity="critical"
        )
        
        # 중간 오류율 알림
        await self.alert_manager.add_rule(
            name="medium_error_rate", 
            condition=lambda stats: stats["error_rate"] > 0.05,  # 5% 이상
            severity="warning"
        )
        
        # 요청 급증 알림
        await self.alert_manager.add_rule(
            name="high_request_volume",
            condition=lambda stats: stats["total_requests"] > 1000,
            severity="info"
        )
        
        self.logger.info("Default alert rules configured")