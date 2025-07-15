"""
Configuration management for MCP Volume Ranking Server
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    """Application settings"""
    
    # 한국투자증권 API 설정
    korea_investment_app_key: str = Field(..., env="KOREA_INVESTMENT_APP_KEY")
    korea_investment_app_secret: str = Field(..., env="KOREA_INVESTMENT_APP_SECRET")
    korea_investment_base_url: str = Field(
        default="https://openapi.koreainvestment.com:9443",
        env="KOREA_INVESTMENT_BASE_URL"
    )
    
    # 캐시 설정
    cache_l1_ttl_seconds: int = Field(default=60, env="CACHE_L1_TTL_SECONDS")
    cache_l2_ttl_seconds: int = Field(default=300, env="CACHE_L2_TTL_SECONDS")
    cache_l2_max_size: int = Field(default=1000, env="CACHE_L2_MAX_SIZE")
    cache_max_size: int = Field(default=1000, env="CACHE_MAX_SIZE")  # 하위 호환성
    
    # Redis 설정
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    redis_max_connections: int = Field(default=20, env="REDIS_MAX_CONNECTIONS")
    redis_socket_timeout: int = Field(default=5, env="REDIS_SOCKET_TIMEOUT")
    
    # 캐시 전략 설정
    cache_l1_enabled: bool = Field(default=True, env="CACHE_L1_ENABLED")
    cache_l2_enabled: bool = Field(default=True, env="CACHE_L2_ENABLED")
    cache_write_through: bool = Field(default=True, env="CACHE_WRITE_THROUGH")
    cache_namespace: str = Field(default="volume_ranking", env="CACHE_NAMESPACE")
    
    # 로깅 설정
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    log_file_path: Optional[str] = Field(default=None, env="LOG_FILE_PATH")
    
    # 성능 설정
    max_ranking_count: int = Field(default=50, env="MAX_RANKING_COUNT")
    default_ranking_count: int = Field(default=20, env="DEFAULT_RANKING_COUNT")
    unusual_volume_threshold: float = Field(default=200.0, env="UNUSUAL_VOLUME_THRESHOLD")
    api_timeout_seconds: int = Field(default=30, env="API_TIMEOUT_SECONDS")
    max_concurrent_requests: int = Field(default=10, env="MAX_CONCURRENT_REQUESTS")
    
    # 개발 환경 설정
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    
    # 서버 설정
    server_host: str = Field(default="localhost", env="SERVER_HOST")
    server_port: int = Field(default=8080, env="SERVER_PORT")
    
    # 모니터링 설정
    enable_performance_monitoring: bool = Field(default=True, env="ENABLE_PERFORMANCE_MONITORING")
    monitoring_interval_seconds: int = Field(default=60, env="MONITORING_INTERVAL_SECONDS")
    
    # 알림 설정
    alert_email: Optional[str] = Field(default=None, env="ALERT_EMAIL")
    slack_webhook_url: Optional[str] = Field(default=None, env="SLACK_WEBHOOK_URL")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

# 글로벌 설정 인스턴스
settings = Settings()

def get_settings() -> Settings:
    """Get application settings"""
    return settings