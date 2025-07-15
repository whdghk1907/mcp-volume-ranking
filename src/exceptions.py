"""
Custom exceptions for MCP Volume Ranking Server
"""

class VolumeRankingError(Exception):
    """Base exception for volume ranking operations"""
    
    def __init__(self, message: str, error_code: str = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)

class APIError(VolumeRankingError):
    """API 관련 오류"""
    pass

class APILimitError(APIError):
    """API 제한 초과"""
    pass

class AuthenticationError(APIError):
    """인증 실패"""
    pass

class DataValidationError(VolumeRankingError):
    """데이터 검증 실패"""
    pass

class MarketClosedError(VolumeRankingError):
    """장 마감 시간"""
    pass

class CacheError(VolumeRankingError):
    """캐시 관련 오류"""
    pass

class ConfigurationError(VolumeRankingError):
    """설정 오류"""
    pass

class TimeoutError(VolumeRankingError):
    """타임아웃 오류"""
    pass

class InvalidParameterError(VolumeRankingError):
    """잘못된 매개변수"""
    pass

class StockNotFoundError(VolumeRankingError):
    """종목을 찾을 수 없음"""
    pass

class InsufficientDataError(VolumeRankingError):
    """데이터 부족"""
    pass