"""
Logging utilities for MCP Volume Ranking Server
"""

import logging
import sys
from typing import Optional
import structlog
from pathlib import Path

from src.config import get_settings

def setup_logger(name: Optional[str] = None) -> structlog.stdlib.BoundLogger:
    """
    구조화된 로거 설정
    
    Args:
        name: 로거 이름 (None이면 기본값 사용)
    
    Returns:
        구조화된 로거 인스턴스
    """
    settings = get_settings()
    
    # 로그 레벨 설정
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    
    # 로그 파일 경로 설정
    if settings.log_file_path:
        log_file = Path(settings.log_file_path)
        log_file.parent.mkdir(parents=True, exist_ok=True)
    else:
        log_file = None
    
    # 로깅 설정
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        handlers=_get_handlers(log_file, settings.log_format)
    )
    
    # structlog 설정
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="ISO"),
            _get_renderer(settings.log_format),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # 로거 생성
    logger_name = name or "mcp-volume-ranking"
    return structlog.get_logger(logger_name)

def _get_handlers(log_file: Optional[Path], log_format: str) -> list:
    """
    로그 핸들러 생성
    
    Args:
        log_file: 로그 파일 경로
        log_format: 로그 포맷 (json or text)
    
    Returns:
        핸들러 리스트
    """
    handlers = []
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    handlers.append(console_handler)
    
    # 파일 핸들러 (설정된 경우)
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        handlers.append(file_handler)
    
    return handlers

def _get_renderer(log_format: str):
    """
    로그 렌더러 선택
    
    Args:
        log_format: 로그 포맷 (json or text)
    
    Returns:
        적절한 렌더러
    """
    if log_format.lower() == "json":
        return structlog.processors.JSONRenderer()
    else:
        return structlog.dev.ConsoleRenderer(
            colors=True,
            exception_formatter=structlog.dev.plain_traceback
        )

class PerformanceLogger:
    """
    성능 모니터링을 위한 로거
    """
    
    def __init__(self, logger: structlog.stdlib.BoundLogger):
        self.logger = logger
        
    def log_api_call(self, endpoint: str, duration: float, success: bool = True):
        """
        API 호출 로깅
        
        Args:
            endpoint: API 엔드포인트
            duration: 응답 시간 (초)
            success: 성공 여부
        """
        self.logger.info(
            "API call completed",
            endpoint=endpoint,
            duration=duration,
            success=success,
            event_type="api_call"
        )
    
    def log_cache_hit(self, tool_name: str, cache_level: str):
        """
        캐시 히트 로깅
        
        Args:
            tool_name: 도구 이름
            cache_level: 캐시 레벨 (L1, L2)
        """
        self.logger.info(
            "Cache hit",
            tool_name=tool_name,
            cache_level=cache_level,
            event_type="cache_hit"
        )
    
    def log_cache_miss(self, tool_name: str):
        """
        캐시 미스 로깅
        
        Args:
            tool_name: 도구 이름
        """
        self.logger.info(
            "Cache miss",
            tool_name=tool_name,
            event_type="cache_miss"
        )
    
    def log_unusual_volume(self, stock_code: str, stock_name: str, ratio: float):
        """
        이상 거래량 감지 로깅
        
        Args:
            stock_code: 종목 코드
            stock_name: 종목명
            ratio: 평균 대비 비율
        """
        self.logger.warning(
            "Unusual volume detected",
            stock_code=stock_code,
            stock_name=stock_name,
            volume_ratio=ratio,
            event_type="unusual_volume"
        )
    
    def log_error(self, error: Exception, context: dict = None):
        """
        에러 로깅
        
        Args:
            error: 예외 객체
            context: 추가 컨텍스트 정보
        """
        log_data = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "event_type": "error"
        }
        
        if context:
            log_data.update(context)
            
        self.logger.error("Error occurred", **log_data, exc_info=True)

def get_performance_logger() -> PerformanceLogger:
    """
    성능 로거 인스턴스 생성
    
    Returns:
        PerformanceLogger 인스턴스
    """
    base_logger = setup_logger("performance")
    return PerformanceLogger(base_logger)