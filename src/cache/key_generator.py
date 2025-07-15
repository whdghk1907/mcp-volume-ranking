"""
Cache Key Generator
캐시 키 생성기
"""

import hashlib
from typing import Dict, Any, Optional
from datetime import datetime, time
from urllib.parse import urlencode

from src.config import get_settings
from src.utils.logger import setup_logger


class CacheKeyGenerator:
    """캐시 키 생성기 - TDD GREEN 단계 구현"""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = setup_logger("cache_key_generator")
        
        # 도구별 기본 TTL 설정
        self.default_ttls = {
            "volume_ranking": 30,      # 거래량 순위
            "investor_ranking": 60,    # 투자자별 거래
            "volume_change": 120,      # 거래량 변화
            "sector_volume": 300,      # 업종별 거래량
            "market_cap": 600,         # 시가총액
            "unusual_volume": 60,      # 이상 거래량
            "health_check": 10         # 헬스체크
        }
    
    def generate_volume_ranking_key(self, market: str, count: int) -> str:
        """거래량 순위 캐시 키 생성"""
        return f"volume_ranking:{market}:{count}"
    
    def generate_investor_ranking_key(
        self, 
        investor_type: str, 
        trade_type: str, 
        market: str, 
        count: int
    ) -> str:
        """투자자별 거래 순위 캐시 키 생성"""
        return f"investor_ranking:{investor_type}:{trade_type}:{market}:{count}"
    
    def generate_volume_change_key(self, market: str, period: str, count: int) -> str:
        """거래량 변화 캐시 키 생성"""
        return f"volume_change:{market}:{period}:{count}"
    
    def generate_sector_volume_key(self, market: str, count: int) -> str:
        """업종별 거래량 캐시 키 생성"""
        return f"sector_volume:{market}:{count}"
    
    def generate_market_cap_key(self, market: str, count: int, filter_hash: Optional[str] = None) -> str:
        """시가총액 캐시 키 생성"""
        base_key = f"market_cap:{market}:{count}"
        if filter_hash:
            base_key += f":{filter_hash}"
        return base_key
    
    def generate_unusual_volume_key(
        self, 
        market: str, 
        threshold: float, 
        count: int, 
        min_price: Optional[int] = None
    ) -> str:
        """이상 거래량 캐시 키 생성"""
        base_key = f"unusual_volume:{market}:{threshold}:{count}"
        if min_price:
            base_key += f":{min_price}"
        return base_key
    
    def generate_health_check_key(self) -> str:
        """헬스체크 캐시 키 생성"""
        return "health_check"
    
    def generate_generic_key(self, tool_name: str, **kwargs) -> str:
        """일반적인 캐시 키 생성"""
        # 매개변수들을 정렬하여 일관된 키 생성
        sorted_params = sorted(kwargs.items())
        param_str = ":".join(f"{k}={v}" for k, v in sorted_params)
        
        if param_str:
            return f"{tool_name}:{param_str}"
        else:
            return tool_name
    
    def generate_pattern(self, tool_name: str, **kwargs) -> str:
        """패턴 매칭을 위한 키 생성"""
        parts = [tool_name]
        
        for key, value in kwargs.items():
            if value is not None:
                parts.append(str(value))
            else:
                parts.append("*")
        
        parts.append("*")
        return ":".join(parts)
    
    def hash_params(self, params: Dict[str, Any]) -> str:
        """매개변수를 해시값으로 변환"""
        # 매개변수를 정렬하여 일관된 해시 생성
        sorted_params = sorted(params.items())
        param_str = urlencode(sorted_params)
        
        # SHA256 해시 생성
        hash_obj = hashlib.sha256(param_str.encode('utf-8'))
        return hash_obj.hexdigest()[:16]  # 처음 16자만 사용
    
    def calculate_ttl(self, tool_name: str, is_trading_time: Optional[bool] = None) -> int:
        """도구별 TTL 계산"""
        base_ttl = self.default_ttls.get(tool_name, 300)  # 기본 5분
        
        # 거래시간 여부에 따른 TTL 조정
        if is_trading_time is None:
            is_trading_time = self._is_trading_time()
        
        if is_trading_time:
            # 거래시간 중에는 TTL을 절반으로 줄임
            return base_ttl // 2
        else:
            # 비거래시간에는 TTL을 두 배로 늘림
            return base_ttl * 2
    
    def _is_trading_time(self) -> bool:
        """현재 거래시간 여부 확인"""
        now = datetime.now()
        
        # 주말 체크
        if now.weekday() >= 5:  # 토요일(5), 일요일(6)
            return False
        
        # 거래시간 체크 (오전 9시 ~ 오후 3시 30분)
        current_time = now.time()
        market_open = time(9, 0)      # 09:00
        market_close = time(15, 30)   # 15:30
        
        return market_open <= current_time <= market_close
    
    def get_cache_namespace(self, tool_name: str) -> str:
        """도구별 캐시 네임스페이스 반환"""
        return f"{self.settings.cache_namespace}:{tool_name}"
    
    def build_full_key(self, tool_name: str, key_suffix: str) -> str:
        """네임스페이스가 포함된 전체 키 생성"""
        namespace = self.get_cache_namespace(tool_name)
        return f"{namespace}:{key_suffix}"
    
    def parse_key(self, full_key: str) -> Dict[str, str]:
        """캐시 키 파싱"""
        try:
            parts = full_key.split(":")
            
            if len(parts) < 2:
                return {"error": "Invalid key format"}
            
            namespace_parts = parts[0].split(":")
            if len(namespace_parts) >= 2:
                namespace = namespace_parts[0]
                tool_name = namespace_parts[1]
            else:
                namespace = "unknown"
                tool_name = parts[0]
            
            return {
                "namespace": namespace,
                "tool_name": tool_name,
                "params": ":".join(parts[1:]) if len(parts) > 1 else "",
                "full_key": full_key
            }
            
        except Exception as e:
            self.logger.error(f"Key parsing failed: {full_key}, error: {str(e)}")
            return {"error": str(e), "full_key": full_key}
    
    def generate_batch_keys(self, tool_name: str, param_sets: list[Dict[str, Any]]) -> list[str]:
        """배치 키 생성"""
        keys = []
        
        for params in param_sets:
            key = self.generate_generic_key(tool_name, **params)
            keys.append(key)
        
        return keys
    
    def validate_key(self, key: str) -> bool:
        """키 형식 유효성 검사"""
        try:
            # 키 길이 제한
            if len(key) > 250:
                return False
            
            # 허용되지 않는 문자 검사
            invalid_chars = [' ', '\n', '\r', '\t']
            for char in invalid_chars:
                if char in key:
                    return False
            
            # 최소 형식 검사
            if ':' not in key:
                return False
            
            return True
            
        except Exception:
            return False


# 글로벌 키 생성기 인스턴스
_key_generator = None

def get_key_generator() -> CacheKeyGenerator:
    """글로벌 키 생성기 인스턴스 획득"""
    global _key_generator
    if _key_generator is None:
        _key_generator = CacheKeyGenerator()
    return _key_generator