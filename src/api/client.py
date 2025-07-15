"""
Korea Investment Securities API Client
한국투자증권 OpenAPI 클라이언트
"""

import asyncio
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import aiohttp
import json
import hashlib
from dataclasses import dataclass, field

from src.config import get_settings
from src.exceptions import (
    APIError, 
    APILimitError, 
    AuthenticationError, 
    TimeoutError,
    ConfigurationError
)
from src.utils.logger import setup_logger, get_performance_logger

@dataclass
class APIToken:
    """API 토큰 정보"""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 86400  # 24시간
    created_at: datetime = field(default_factory=datetime.now)
    
    @property
    def is_expired(self) -> bool:
        """토큰 만료 여부 확인"""
        expiry_time = self.created_at + timedelta(seconds=self.expires_in - 300)  # 5분 여유
        return datetime.now() > expiry_time
    
    @property
    def authorization_header(self) -> str:
        """Authorization 헤더 값"""
        return f"{self.token_type} {self.access_token}"

class KoreaInvestmentAPI:
    """한국투자증권 API 베이스 클라이언트"""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = setup_logger("api_client")
        self.performance_logger = get_performance_logger()
        
        # API 설정 검증
        if not self.settings.korea_investment_app_key or self.settings.korea_investment_app_key == "your_app_key_here":
            raise ConfigurationError("Korea Investment API key is not configured")
        
        if not self.settings.korea_investment_app_secret or self.settings.korea_investment_app_secret == "your_app_secret_here":
            raise ConfigurationError("Korea Investment API secret is not configured")
        
        self.app_key = self.settings.korea_investment_app_key
        self.app_secret = self.settings.korea_investment_app_secret
        self.base_url = self.settings.korea_investment_base_url
        
        # 토큰 캐시
        self._token_cache: Optional[APIToken] = None
        self._token_lock = asyncio.Lock()
        
        # 요청 제한 관리
        self._request_times: List[float] = []
        self._max_requests_per_second = 5  # API 제한에 맞게 조정
        
        self.logger.info("API client initialized", base_url=self.base_url)
    
    async def _get_access_token(self) -> str:
        """
        OAuth 2.0 액세스 토큰 획득
        
        Returns:
            액세스 토큰 문자열
        """
        async with self._token_lock:
            # 캐시된 토큰이 유효한 경우 반환
            if self._token_cache and not self._token_cache.is_expired:
                return self._token_cache.access_token
            
            # 새 토큰 요청
            self.logger.info("Requesting new access token")
            
            url = f"{self.base_url}/oauth2/tokenP"
            headers = {
                "content-type": "application/json; charset=utf-8"
            }
            
            data = {
                "grant_type": "client_credentials",
                "appkey": self.app_key,
                "appsecret": self.app_secret
            }
            
            start_time = time.time()
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        url, 
                        headers=headers, 
                        json=data,
                        timeout=aiohttp.ClientTimeout(total=self.settings.api_timeout_seconds)
                    ) as response:
                        duration = time.time() - start_time
                        
                        if response.status == 200:
                            result = await response.json()
                            
                            if "access_token" in result:
                                self._token_cache = APIToken(
                                    access_token=result["access_token"],
                                    token_type=result.get("token_type", "Bearer"),
                                    expires_in=result.get("expires_in", 86400)
                                )
                                
                                self.performance_logger.log_api_call(
                                    "oauth2/tokenP", duration, True
                                )
                                
                                self.logger.info("Access token obtained successfully")
                                return self._token_cache.access_token
                            else:
                                raise AuthenticationError(f"Token response missing access_token: {result}")
                        
                        else:
                            error_text = await response.text()
                            self.performance_logger.log_api_call(
                                "oauth2/tokenP", duration, False
                            )
                            raise AuthenticationError(f"Token request failed: {response.status} - {error_text}")
            
            except asyncio.TimeoutError:
                duration = time.time() - start_time
                self.performance_logger.log_api_call("oauth2/tokenP", duration, False)
                raise TimeoutError("Token request timed out")
            
            except Exception as e:
                duration = time.time() - start_time
                self.performance_logger.log_api_call("oauth2/tokenP", duration, False)
                self.logger.error("Token request failed", error=str(e))
                raise APIError(f"Token request failed: {str(e)}")
    
    async def _rate_limit(self):
        """요청 속도 제한"""
        current_time = time.time()
        
        # 1초 이내의 요청만 유지
        self._request_times = [
            req_time for req_time in self._request_times 
            if current_time - req_time < 1.0
        ]
        
        # 제한 초과 시 대기
        if len(self._request_times) >= self._max_requests_per_second:
            wait_time = 1.0 - (current_time - self._request_times[0])
            if wait_time > 0:
                await asyncio.sleep(wait_time)
        
        self._request_times.append(current_time)
    
    async def _make_request(
        self, 
        method: str,
        endpoint: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        tr_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        API 요청 실행
        
        Args:
            method: HTTP 메소드
            endpoint: API 엔드포인트
            headers: 추가 헤더
            params: 쿼리 매개변수
            data: 요청 데이터
            tr_id: 거래 ID (한국투자증권 API 필수)
        
        Returns:
            API 응답 데이터
        """
        await self._rate_limit()
        
        # 토큰 획득
        token = await self._get_access_token()
        
        # 기본 헤더 설정
        request_headers = {
            "authorization": f"Bearer {token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "content-type": "application/json; charset=utf-8"
        }
        
        if tr_id:
            request_headers["tr_id"] = tr_id
        
        if headers:
            request_headers.update(headers)
        
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                kwargs = {
                    "headers": request_headers,
                    "timeout": aiohttp.ClientTimeout(total=self.settings.api_timeout_seconds)
                }
                
                if params:
                    kwargs["params"] = params
                if data:
                    kwargs["json"] = data
                
                async with session.request(method, url, **kwargs) as response:
                    duration = time.time() - start_time
                    response_text = await response.text()
                    
                    self.logger.debug(
                        "API request completed",
                        method=method,
                        endpoint=endpoint,
                        status=response.status,
                        duration=duration
                    )
                    
                    if response.status == 200:
                        try:
                            result = json.loads(response_text)
                            self.performance_logger.log_api_call(endpoint, duration, True)
                            return result
                        except json.JSONDecodeError as e:
                            self.performance_logger.log_api_call(endpoint, duration, False)
                            raise APIError(f"Invalid JSON response: {str(e)}")
                    
                    elif response.status == 401:
                        # 토큰 만료 시 캐시 무효화
                        self._token_cache = None
                        self.performance_logger.log_api_call(endpoint, duration, False)
                        raise AuthenticationError("Authentication failed - token may be expired")
                    
                    elif response.status == 429:
                        self.performance_logger.log_api_call(endpoint, duration, False)
                        raise APILimitError("API rate limit exceeded")
                    
                    else:
                        self.performance_logger.log_api_call(endpoint, duration, False)
                        raise APIError(f"API request failed: {response.status} - {response_text}")
        
        except asyncio.TimeoutError:
            duration = time.time() - start_time
            self.performance_logger.log_api_call(endpoint, duration, False)
            raise TimeoutError(f"API request timed out: {endpoint}")
        
        except Exception as e:
            duration = time.time() - start_time
            self.performance_logger.log_api_call(endpoint, duration, False)
            self.logger.error("API request failed", endpoint=endpoint, error=str(e))
            raise
    
    async def get_stock_price(self, stock_code: str, market: str = "J") -> Dict[str, Any]:
        """
        주식 현재가 조회 (테스트용)
        
        Args:
            stock_code: 종목 코드
            market: 시장 구분 (J: 주식, ETF)
        
        Returns:
            주식 현재가 정보
        """
        endpoint = "/uapi/domestic-stock/v1/quotations/inquire-price"
        
        params = {
            "FID_COND_MRKT_DIV_CODE": market,
            "FID_INPUT_ISCD": stock_code
        }
        
        headers = {
            "tr_id": "FHKST01010100"
        }
        
        self.logger.info("Requesting stock price", stock_code=stock_code, market=market)
        
        try:
            result = await self._make_request(
                "GET", 
                endpoint, 
                headers=headers, 
                params=params,
                tr_id="FHKST01010100"
            )
            
            return result
        
        except Exception as e:
            self.logger.error("Stock price request failed", stock_code=stock_code, error=str(e))
            raise
    
    async def health_check(self) -> bool:
        """
        API 연결 상태 확인
        
        Returns:
            연결 상태 (True: 정상, False: 비정상)
        """
        try:
            # 삼성전자 주가로 테스트
            await self.get_stock_price("005930")
            return True
        except Exception as e:
            self.logger.warning("API health check failed", error=str(e))
            return False
    
    def clear_token_cache(self):
        """토큰 캐시 초기화"""
        self._token_cache = None
        self.logger.info("Token cache cleared")

class VolumeRankingAPI(KoreaInvestmentAPI):
    """거래대금 순위 전용 API 클라이언트"""
    
    async def get_volume_rank(
        self, 
        market_code: str = "J",
        rank_sort_cls: str = "0"  # 0: 거래대금순
    ) -> Dict[str, Any]:
        """
        거래대금 순위 조회
        
        Args:
            market_code: 시장 코드 (J: 전체, 0: 코스피, 1: 코스닥)
            rank_sort_cls: 정렬 기준 (0: 거래대금순)
        
        Returns:
            거래대금 순위 데이터
        """
        endpoint = "/uapi/domestic-stock/v1/ranking/volume-rank"
        
        params = {
            "FID_COND_MRKT_DIV_CODE": market_code,
            "FID_COND_SCR_DIV_CODE": "20171",  # 거래대금
            "FID_RANK_SORT_CLS_CODE": rank_sort_cls,
            "FID_INPUT_ISCD": "0000",
            "FID_DIV_CLS_CODE": "0",
            "FID_BLNG_CLS_CODE": "0",
            "FID_TRGT_CLS_CODE": "111111111",
            "FID_TRGT_EXLS_CLS_CODE": "000000",
            "FID_INPUT_PRICE_1": "",
            "FID_INPUT_PRICE_2": "",
            "FID_VOL_CNT": "",
            "FID_INPUT_DATE_1": ""
        }
        
        headers = {
            "tr_id": "FHPST01710000"
        }
        
        self.logger.info("Requesting volume ranking", market_code=market_code)
        
        try:
            result = await self._make_request(
                "GET",
                endpoint,
                headers=headers,
                params=params,
                tr_id="FHPST01710000"
            )
            
            return result
        
        except Exception as e:
            self.logger.error("Volume ranking request failed", market_code=market_code, error=str(e))
            raise