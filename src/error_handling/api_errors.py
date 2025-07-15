"""
API Error Handling - TDD Implementation
API 오류 처리 - TDD 구현
"""

import asyncio
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from src.utils.logger import setup_logger


class ErrorSeverity(Enum):
    """오류 심각도"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorResponse:
    """오류 응답"""
    handled: bool
    should_retry: bool
    retry_after: float
    severity: ErrorSeverity
    action: str
    details: Dict[str, Any]


class APIErrorHandler:
    """API 오류 처리기"""
    
    def __init__(self):
        self.logger = setup_logger("api_error_handler")
        self.error_stats = {}
        self.rate_limit_info = {}
    
    async def handle_error(self, code: int, message: str, endpoint: Optional[str] = None) -> Dict[str, Any]:
        """API 오류 처리"""
        self.logger.warning(f"API Error: {code} - {message}")
        
        # 오류 통계 업데이트
        await self._update_error_stats(code, endpoint)
        
        # 오류 코드별 처리
        if code == 400:
            return await self._handle_bad_request(message)
        elif code == 401:
            return await self._handle_unauthorized(message)
        elif code == 403:
            return await self._handle_forbidden(message)
        elif code == 404:
            return await self._handle_not_found(message)
        elif code == 429:
            return await self._handle_rate_limit(message, endpoint)
        elif code >= 500:
            return await self._handle_server_error(code, message)
        else:
            return await self._handle_unknown_error(code, message)
    
    async def _handle_bad_request(self, message: str) -> Dict[str, Any]:
        """잘못된 요청 처리"""
        return {
            "handled": True,
            "should_retry": False,  # 클라이언트 오류는 재시도 불필요
            "retry_after": 0,
            "severity": "medium",
            "action": "validate_request",
            "details": {"message": message}
        }
    
    async def _handle_unauthorized(self, message: str) -> Dict[str, Any]:
        """인증 오류 처리"""
        return {
            "handled": True,
            "should_retry": True,   # 토큰 갱신 후 재시도 가능
            "retry_after": 1.0,
            "severity": "high",
            "action": "refresh_token",
            "details": {"message": message}
        }
    
    async def _handle_forbidden(self, message: str) -> Dict[str, Any]:
        """권한 오류 처리"""
        return {
            "handled": True,
            "should_retry": False,  # 권한 문제는 재시도 무의미
            "retry_after": 0,
            "severity": "high",
            "action": "check_permissions",
            "details": {"message": message}
        }
    
    async def _handle_not_found(self, message: str) -> Dict[str, Any]:
        """리소스 없음 처리"""
        return {
            "handled": True,
            "should_retry": False,  # 존재하지 않는 리소스
            "retry_after": 0,
            "severity": "low",
            "action": "check_resource",
            "details": {"message": message}
        }
    
    async def _handle_rate_limit(self, message: str, endpoint: Optional[str] = None) -> Dict[str, Any]:
        """요율 제한 처리"""
        # Retry-After 헤더 파싱 (단순화된 구현)
        retry_after = 60.0  # 기본 1분
        
        if endpoint:
            self.rate_limit_info[endpoint] = {
                "limited_at": time.time(),
                "retry_after": retry_after
            }
        
        return {
            "handled": True,
            "should_retry": True,
            "retry_after": retry_after,
            "severity": "medium",
            "action": "wait_and_retry",
            "details": {
                "message": message,
                "endpoint": endpoint,
                "retry_after_seconds": retry_after
            }
        }
    
    async def _handle_server_error(self, code: int, message: str) -> Dict[str, Any]:
        """서버 오류 처리"""
        # 서버 오류는 재시도 가능
        retry_after = 5.0 if code == 503 else 2.0  # Service Unavailable은 더 길게
        
        return {
            "handled": True,
            "should_retry": True,
            "retry_after": retry_after,
            "severity": "critical" if code >= 503 else "high",
            "action": "retry_with_backoff",
            "details": {
                "message": message,
                "code": code,
                "retry_after_seconds": retry_after
            }
        }
    
    async def _handle_unknown_error(self, code: int, message: str) -> Dict[str, Any]:
        """알 수 없는 오류 처리"""
        return {
            "handled": True,
            "should_retry": True,
            "retry_after": 10.0,  # 보수적인 재시도
            "severity": "medium",
            "action": "investigate",
            "details": {
                "message": message,
                "code": code,
                "note": "Unknown error code"
            }
        }
    
    async def _update_error_stats(self, code: int, endpoint: Optional[str]):
        """오류 통계 업데이트"""
        key = f"{endpoint or 'unknown'}:{code}"
        
        if key not in self.error_stats:
            self.error_stats[key] = {
                "count": 0,
                "first_seen": datetime.now(),
                "last_seen": datetime.now()
            }
        
        self.error_stats[key]["count"] += 1
        self.error_stats[key]["last_seen"] = datetime.now()
    
    def get_error_stats(self) -> Dict[str, Any]:
        """오류 통계 반환"""
        return self.error_stats.copy()
    
    def is_rate_limited(self, endpoint: str) -> bool:
        """요율 제한 상태 확인"""
        if endpoint not in self.rate_limit_info:
            return False
        
        info = self.rate_limit_info[endpoint]
        elapsed = time.time() - info["limited_at"]
        
        return elapsed < info["retry_after"]


class HTTPStatusCodeHandler:
    """HTTP 상태 코드 처리기"""
    
    def __init__(self):
        self.logger = setup_logger("http_status_handler")
    
    def is_retriable_error(self, status_code: int) -> bool:
        """재시도 가능한 오류인지 확인"""
        # 4xx는 일반적으로 클라이언트 오류 (재시도 불가)
        # 5xx는 서버 오류 (재시도 가능)
        # 429는 요율 제한 (재시도 가능)
        return status_code in [408, 429] or status_code >= 500
    
    def get_retry_delay(self, status_code: int, attempt: int = 1) -> float:
        """재시도 지연 시간 계산"""
        base_delays = {
            408: 1.0,   # Request Timeout
            429: 60.0,  # Too Many Requests
            500: 2.0,   # Internal Server Error
            502: 3.0,   # Bad Gateway
            503: 5.0,   # Service Unavailable
            504: 4.0,   # Gateway Timeout
        }
        
        base_delay = base_delays.get(status_code, 2.0)
        
        # 지수 백오프
        return min(base_delay * (2 ** (attempt - 1)), 300.0)  # 최대 5분
    
    def categorize_error(self, status_code: int) -> str:
        """오류 분류"""
        if 400 <= status_code < 500:
            if status_code == 429:
                return "rate_limit"
            elif status_code in [401, 403]:
                return "authentication"
            else:
                return "client_error"
        elif 500 <= status_code < 600:
            return "server_error"
        else:
            return "unknown"


class APIErrorAggregator:
    """API 오류 집계기"""
    
    def __init__(self, window_minutes: int = 5):
        self.window_minutes = window_minutes
        self.error_history = []
        self.logger = setup_logger("api_error_aggregator")
    
    async def record_error(self, endpoint: str, status_code: int, error_type: str):
        """오류 기록"""
        error_record = {
            "endpoint": endpoint,
            "status_code": status_code,
            "error_type": error_type,
            "timestamp": datetime.now()
        }
        
        self.error_history.append(error_record)
        
        # 오래된 기록 정리
        await self._cleanup_old_records()
    
    async def _cleanup_old_records(self):
        """오래된 기록 정리"""
        cutoff_time = datetime.now() - timedelta(minutes=self.window_minutes)
        self.error_history = [
            record for record in self.error_history
            if record["timestamp"] > cutoff_time
        ]
    
    async def get_error_rate(self, endpoint: Optional[str] = None) -> Dict[str, Any]:
        """오류율 계산"""
        await self._cleanup_old_records()
        
        if endpoint:
            errors = [r for r in self.error_history if r["endpoint"] == endpoint]
        else:
            errors = self.error_history
        
        total_errors = len(errors)
        
        if total_errors == 0:
            return {
                "error_rate": 0.0,
                "total_errors": 0,
                "window_minutes": self.window_minutes
            }
        
        # 오류 유형별 집계
        error_types = {}
        status_codes = {}
        
        for error in errors:
            error_type = error["error_type"]
            status_code = error["status_code"]
            
            error_types[error_type] = error_types.get(error_type, 0) + 1
            status_codes[status_code] = status_codes.get(status_code, 0) + 1
        
        return {
            "error_rate": total_errors / max(1, self.window_minutes),  # 분당 오류
            "total_errors": total_errors,
            "window_minutes": self.window_minutes,
            "error_types": error_types,
            "status_codes": status_codes,
            "most_common_error": max(error_types.items(), key=lambda x: x[1])[0] if error_types else None
        }
    
    async def detect_error_spikes(self, threshold_multiplier: float = 3.0) -> List[Dict[str, Any]]:
        """오류 급증 감지"""
        await self._cleanup_old_records()
        
        # 시간대별 오류 수 계산
        hourly_errors = {}
        
        for error in self.error_history:
            hour = error["timestamp"].replace(minute=0, second=0, microsecond=0)
            hourly_errors[hour] = hourly_errors.get(hour, 0) + 1
        
        if len(hourly_errors) < 2:
            return []
        
        # 평균 및 급증 감지
        error_counts = list(hourly_errors.values())
        avg_errors = sum(error_counts) / len(error_counts)
        threshold = avg_errors * threshold_multiplier
        
        spikes = []
        for hour, count in hourly_errors.items():
            if count > threshold:
                spikes.append({
                    "hour": hour,
                    "error_count": count,
                    "threshold": threshold,
                    "spike_ratio": count / avg_errors if avg_errors > 0 else float('inf')
                })
        
        return sorted(spikes, key=lambda x: x["spike_ratio"], reverse=True)