# 💰 거래대금 순위 MCP 서버 개발 계획서

## 1. 프로젝트 개요

### 1.1 목적
한국 주식시장(코스피/코스닥)의 거래대금 상위 종목을 실시간으로 조회하고 분석할 수 있는 MCP 서버 구축

### 1.2 범위
- 거래대금 상위 종목 순위 (전체/코스피/코스닥)
- 시가총액 상위 종목 순위
- 거래량 상위 종목 순위
- 외국인/기관 순매수 상위 종목
- 프로그램 매매 상위 종목
- 업종별 거래대금 순위

### 1.3 기술 스택
- **언어**: Python 3.11+
- **MCP SDK**: mcp-python
- **API Client**: 한국투자증권 OpenAPI
- **비동기 처리**: asyncio, aiohttp
- **데이터 검증**: pydantic
- **캐싱**: Redis (선택적) + 내장 메모리 캐시

## 2. 서버 아키텍처

```
mcp-volume-ranking/
├── src/
│   ├── server.py              # MCP 서버 메인
│   ├── tools/                 # MCP 도구 정의
│   │   ├── __init__.py
│   │   ├── volume_tools.py    # 거래대금 관련 도구
│   │   ├── ranking_tools.py   # 순위 조회 도구
│   │   └── investor_tools.py # 투자자별 순위 도구
│   ├── api/
│   │   ├── __init__.py
│   │   ├── client.py          # 한국투자증권 API 클라이언트
│   │   ├── models.py          # 데이터 모델
│   │   └── constants.py       # API 상수 정의
│   ├── utils/
│   │   ├── cache.py           # 캐시 관리
│   │   ├── formatter.py       # 데이터 포맷팅
│   │   ├── calculator.py      # 순위 계산 로직
│   │   └── validator.py       # 데이터 검증
│   ├── config.py              # 설정 관리
│   └── exceptions.py          # 예외 정의
├── tests/
│   ├── test_tools.py
│   ├── test_calculator.py
│   └── test_api.py
├── requirements.txt
├── .env.example
└── README.md
```

## 3. 핵심 기능 명세

### 3.1 제공 도구 (Tools)

#### 1) `get_volume_ranking`
```python
@tool
async def get_volume_ranking(
    market: Literal["ALL", "KOSPI", "KOSDAQ"] = "ALL",
    count: int = 20,
    include_details: bool = True
) -> dict:
    """
    거래대금 상위 종목 조회
    
    Parameters:
        market: 시장 구분 (ALL, KOSPI, KOSDAQ)
        count: 조회할 종목 수 (최대 50)
        include_details: 상세 정보 포함 여부
    
    Returns:
        {
            "timestamp": "2024-01-10T10:30:00+09:00",
            "market": "ALL",
            "ranking": [
                {
                    "rank": 1,
                    "stock_code": "005930",
                    "stock_name": "삼성전자",
                    "market_type": "KOSPI",
                    "current_price": 78500,
                    "change": 1200,
                    "change_rate": 1.55,
                    "volume": 15234567,
                    "trading_value": 1196213009500,  # 거래대금 (원)
                    "market_cap": 468923450000000,   # 시가총액 (원)
                    "foreign_ratio": 51.23,          # 외국인 보유비율
                    "per": 12.5,                     # 주가수익비율
                    "turnover_rate": 0.25            # 회전율
                },
                ...
            ],
            "summary": {
                "total_trading_value": 8523456789000,
                "kospi_trading_value": 5234567890000,
                "kosdaq_trading_value": 3288888899000,
                "top5_concentration": 35.6  # 상위 5종목 집중도
            }
        }
    """
```

#### 2) `get_volume_change_ranking`
```python
@tool
async def get_volume_change_ranking(
    market: Literal["ALL", "KOSPI", "KOSDAQ"] = "ALL",
    period: Literal["1D", "5D", "20D"] = "1D",
    count: int = 20
) -> dict:
    """
    거래대금 증가율 상위 종목 조회
    
    Parameters:
        market: 시장 구분
        period: 비교 기간 (1D: 전일대비, 5D: 5일평균대비, 20D: 20일평균대비)
        count: 조회할 종목 수
    
    Returns:
        {
            "timestamp": "2024-01-10T10:30:00+09:00",
            "period": "1D",
            "ranking": [
                {
                    "rank": 1,
                    "stock_code": "123456",
                    "stock_name": "종목명",
                    "current_volume": 234567890000,
                    "previous_volume": 45678900000,
                    "volume_change_rate": 413.5,  # 증가율 %
                    "price_change_rate": 15.3,
                    "news_count": 5,  # 관련 뉴스 수
                    "disclosure_count": 2  # 공시 수
                },
                ...
            ]
        }
    """
```

#### 3) `get_investor_ranking`
```python
@tool
async def get_investor_ranking(
    investor_type: Literal["FOREIGN", "INSTITUTION", "INDIVIDUAL", "PROGRAM"] = "FOREIGN",
    trade_type: Literal["BUY", "SELL", "NET"] = "NET",
    market: Literal["ALL", "KOSPI", "KOSDAQ"] = "ALL",
    count: int = 20
) -> dict:
    """
    투자자별 거래 상위 종목 조회
    
    Parameters:
        investor_type: 투자자 유형 (외국인/기관/개인/프로그램)
        trade_type: 거래 유형 (매수/매도/순매수)
        market: 시장 구분
        count: 조회할 종목 수
    
    Returns:
        {
            "timestamp": "2024-01-10T10:30:00+09:00",
            "investor_type": "FOREIGN",
            "trade_type": "NET",
            "ranking": [
                {
                    "rank": 1,
                    "stock_code": "005930",
                    "stock_name": "삼성전자",
                    "buy_amount": 523456780000,
                    "sell_amount": 234567890000,
                    "net_amount": 288888890000,
                    "buy_volume": 6678900,
                    "sell_volume": 2987650,
                    "net_volume": 3691250,
                    "average_buy_price": 78350,
                    "average_sell_price": 78520,
                    "impact_ratio": 24.1  # 전체 거래대금 대비 비율
                },
                ...
            ],
            "summary": {
                "total_buy_amount": 2345678900000,
                "total_sell_amount": 1234567890000,
                "total_net_amount": 1111111010000,
                "market_impact": 13.0  # 전체 시장 대비 영향도
            }
        }
    """
```

#### 4) `get_sector_volume_ranking`
```python
@tool
async def get_sector_volume_ranking(
    market: Literal["KOSPI", "KOSDAQ"] = "KOSPI",
    count: int = 20
) -> dict:
    """
    업종별 거래대금 순위 조회
    
    Parameters:
        market: 시장 구분
        count: 조회할 업종 수
    
    Returns:
        {
            "timestamp": "2024-01-10T10:30:00+09:00",
            "market": "KOSPI",
            "ranking": [
                {
                    "rank": 1,
                    "sector_code": "G2510",
                    "sector_name": "반도체",
                    "trading_value": 2345678900000,
                    "trading_volume": 234567890,
                    "stock_count": 45,  # 업종 내 종목 수
                    "average_change_rate": 2.35,
                    "leading_stocks": [
                        {
                            "stock_code": "005930",
                            "stock_name": "삼성전자",
                            "contribution": 45.6  # 업종 내 기여도
                        },
                        ...
                    ],
                    "foreign_net_buy": 345678900000,
                    "institution_net_buy": -123456780000
                },
                ...
            ]
        }
    """
```

#### 5) `get_market_cap_ranking`
```python
@tool
async def get_market_cap_ranking(
    market: Literal["ALL", "KOSPI", "KOSDAQ"] = "ALL",
    count: int = 20,
    filter_by: Optional[Dict] = None
) -> dict:
    """
    시가총액 상위 종목 조회
    
    Parameters:
        market: 시장 구분
        count: 조회할 종목 수
        filter_by: 필터 조건 (예: {"min_trading_value": 10000000000})
    
    Returns:
        {
            "timestamp": "2024-01-10T10:30:00+09:00",
            "market": "ALL",
            "ranking": [
                {
                    "rank": 1,
                    "stock_code": "005930",
                    "stock_name": "삼성전자",
                    "market_cap": 468923450000000,
                    "market_cap_rank_change": 0,  # 전일 대비 순위 변화
                    "current_price": 78500,
                    "trading_value": 1196213009500,
                    "trading_value_rank": 1,
                    "weight_in_index": 31.2,  # 지수 내 비중
                    "foreign_ownership": 51.23,
                    "treasury_stock_ratio": 0.15  # 자사주 비율
                },
                ...
            ],
            "summary": {
                "total_market_cap": 2145678900000000,
                "top10_concentration": 65.4,
                "average_per": 15.6,
                "average_pbr": 1.2
            }
        }
    """
```

#### 6) `get_unusual_volume`
```python
@tool
async def get_unusual_volume(
    market: Literal["ALL", "KOSPI", "KOSDAQ"] = "ALL",
    threshold: float = 200.0,  # 평균 대비 %
    min_price: Optional[int] = None,
    count: int = 20
) -> dict:
    """
    이상 거래량 종목 감지
    
    Parameters:
        market: 시장 구분
        threshold: 이상 거래 감지 임계값 (평균 대비 %)
        min_price: 최소 주가 필터
        count: 조회할 종목 수
    
    Returns:
        {
            "timestamp": "2024-01-10T10:30:00+09:00",
            "detection_criteria": {
                "threshold": 200.0,
                "comparison_period": "20D",
                "min_price": 1000
            },
            "unusual_stocks": [
                {
                    "stock_code": "123456",
                    "stock_name": "종목명",
                    "current_volume": 12345678,
                    "average_volume": 2345678,
                    "volume_ratio": 526.3,  # 평균 대비 비율
                    "price_change_rate": 25.3,
                    "trading_value": 234567890000,
                    "consecutive_days": 2,  # 연속 이상거래일
                    "possible_reasons": [
                        "major_disclosure",
                        "news_coverage",
                        "technical_breakout"
                    ]
                },
                ...
            ]
        }
    """
```

## 4. API 클라이언트 구현

### 4.1 한국투자증권 API 클라이언트 확장

```python
# src/api/client.py
from typing import Dict, List, Optional
import aiohttp
from datetime import datetime

class VolumeRankingAPI(KoreaInvestmentAPI):
    """거래대금 순위 전용 API 클라이언트"""
    
    async def get_volume_rank(
        self, 
        market_code: str,
        rank_sort_cls: str = "0"  # 0: 거래대금순
    ) -> Dict:
        """거래대금 순위 조회"""
        token = await self._get_access_token()
        
        headers = {
            "authorization": f"Bearer {token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "FHPST01710000"
        }
        
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
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/uapi/domestic-stock/v1/ranking/volume-rank",
                headers=headers,
                params=params
            ) as resp:
                return await resp.json()
    
    async def get_investor_trend_rank(
        self,
        market_code: str,
        investor_type: str,
        trade_type: str
    ) -> Dict:
        """투자자별 거래 순위 조회"""
        token = await self._get_access_token()
        
        headers = {
            "authorization": f"Bearer {token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "FHPST01720000"
        }
        
        params = {
            "FID_COND_MRKT_DIV_CODE": market_code,
            "FID_COND_SCR_DIV_CODE": self._get_investor_screen_code(investor_type, trade_type),
            "FID_RANK_SORT_CLS_CODE": "0",
            "FID_INPUT_ISCD": "0000"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/uapi/domestic-stock/v1/ranking/investor-trend",
                headers=headers,
                params=params
            ) as resp:
                return await resp.json()
    
    def _get_investor_screen_code(self, investor_type: str, trade_type: str) -> str:
        """투자자 유형별 화면 코드 매핑"""
        mapping = {
            ("FOREIGN", "BUY"): "20172",
            ("FOREIGN", "SELL"): "20173",
            ("FOREIGN", "NET"): "20174",
            ("INSTITUTION", "BUY"): "20175",
            ("INSTITUTION", "SELL"): "20176",
            ("INSTITUTION", "NET"): "20177",
            ("INDIVIDUAL", "BUY"): "20178",
            ("INDIVIDUAL", "SELL"): "20179",
            ("INDIVIDUAL", "NET"): "20180"
        }
        return mapping.get((investor_type, trade_type), "20174")
```

### 4.2 데이터 모델 정의

```python
# src/api/models.py
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class StockRankingItem(BaseModel):
    """주식 순위 항목"""
    rank: int
    stock_code: str
    stock_name: str
    market_type: str
    current_price: float
    change: float
    change_rate: float
    volume: int
    trading_value: float
    market_cap: Optional[float] = None
    foreign_ratio: Optional[float] = None
    per: Optional[float] = None
    turnover_rate: Optional[float] = None

class InvestorRankingItem(BaseModel):
    """투자자별 순위 항목"""
    rank: int
    stock_code: str
    stock_name: str
    buy_amount: float
    sell_amount: float
    net_amount: float
    buy_volume: int
    sell_volume: int
    net_volume: int
    average_buy_price: Optional[float] = None
    average_sell_price: Optional[float] = None
    impact_ratio: Optional[float] = None

class SectorRankingItem(BaseModel):
    """업종별 순위 항목"""
    rank: int
    sector_code: str
    sector_name: str
    trading_value: float
    trading_volume: int
    stock_count: int
    average_change_rate: float
    leading_stocks: List[Dict]
    foreign_net_buy: Optional[float] = None
    institution_net_buy: Optional[float] = None

class VolumeRankingResponse(BaseModel):
    """거래대금 순위 응답"""
    timestamp: datetime
    market: str
    ranking: List[StockRankingItem]
    summary: Dict
```

## 5. 캐싱 및 성능 최적화

### 5.1 계층적 캐싱 전략

```python
# src/utils/cache.py
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import asyncio
import json
import hashlib

class HierarchicalCache:
    """계층적 캐싱 시스템"""
    
    def __init__(self):
        self.l1_cache = {}  # 메모리 캐시 (1분)
        self.l2_cache = {}  # 메모리 캐시 (5분)
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "l1_hits": 0,
            "l2_hits": 0
        }
    
    def _generate_key(self, tool_name: str, params: Dict) -> str:
        """캐시 키 생성"""
        param_str = json.dumps(params, sort_keys=True)
        return hashlib.md5(f"{tool_name}:{param_str}".encode()).hexdigest()
    
    async def get_or_fetch(
        self,
        tool_name: str,
        params: Dict,
        fetch_func,
        l1_ttl: int = 60,  # L1 캐시 TTL (초)
        l2_ttl: int = 300  # L2 캐시 TTL (초)
    ) -> Any:
        """계층적 캐시 조회"""
        key = self._generate_key(tool_name, params)
        
        # L1 캐시 확인
        if key in self.l1_cache:
            if self.l1_cache[key]["expires"] > datetime.now():
                self.cache_stats["hits"] += 1
                self.cache_stats["l1_hits"] += 1
                return self.l1_cache[key]["data"]
        
        # L2 캐시 확인
        if key in self.l2_cache:
            if self.l2_cache[key]["expires"] > datetime.now():
                self.cache_stats["hits"] += 1
                self.cache_stats["l2_hits"] += 1
                
                # L1 캐시로 승격
                self.l1_cache[key] = {
                    "data": self.l2_cache[key]["data"],
                    "expires": datetime.now() + timedelta(seconds=l1_ttl)
                }
                
                return self.l2_cache[key]["data"]
        
        # 캐시 미스
        self.cache_stats["misses"] += 1
        
        # 데이터 fetch
        data = await fetch_func()
        
        # 양쪽 캐시에 저장
        self.l1_cache[key] = {
            "data": data,
            "expires": datetime.now() + timedelta(seconds=l1_ttl)
        }
        
        self.l2_cache[key] = {
            "data": data,
            "expires": datetime.now() + timedelta(seconds=l2_ttl)
        }
        
        return data
    
    def invalidate_pattern(self, pattern: str):
        """패턴 기반 캐시 무효화"""
        for cache in [self.l1_cache, self.l2_cache]:
            keys_to_delete = [
                k for k in cache.keys() 
                if pattern in k
            ]
            for key in keys_to_delete:
                del cache[key]
```

### 5.2 순위 계산 최적화

```python
# src/utils/calculator.py
import numpy as np
from typing import List, Dict, Tuple
from collections import defaultdict

class RankingCalculator:
    """순위 계산 및 분석 유틸리티"""
    
    @staticmethod
    def calculate_concentration(ranking_data: List[Dict], top_n: int = 5) -> float:
        """상위 N개 종목 집중도 계산"""
        if not ranking_data:
            return 0.0
        
        total_value = sum(item.get("trading_value", 0) for item in ranking_data)
        if total_value == 0:
            return 0.0
        
        top_n_value = sum(
            item.get("trading_value", 0) 
            for item in ranking_data[:top_n]
        )
        
        return (top_n_value / total_value) * 100
    
    @staticmethod
    def detect_unusual_volume(
        current_volume: float,
        historical_volumes: List[float],
        threshold: float = 2.0
    ) -> Tuple[bool, float]:
        """이상 거래량 감지"""
        if not historical_volumes:
            return False, 0.0
        
        avg_volume = np.mean(historical_volumes)
        std_volume = np.std(historical_volumes)
        
        if avg_volume == 0:
            return False, 0.0
        
        # Z-score 계산
        z_score = (current_volume - avg_volume) / (std_volume + 1e-8)
        
        # 비율 계산
        ratio = (current_volume / avg_volume) * 100
        
        is_unusual = abs(z_score) > threshold or ratio > 200
        
        return is_unusual, ratio
    
    @staticmethod
    def calculate_turnover_rate(
        trading_volume: int,
        total_shares: int,
        free_float_ratio: float = 1.0
    ) -> float:
        """회전율 계산"""
        if total_shares == 0:
            return 0.0
        
        free_float_shares = total_shares * free_float_ratio
        return (trading_volume / free_float_shares) * 100
    
    @staticmethod
    def group_by_sector(
        stocks: List[Dict],
        sector_mapping: Dict[str, str]
    ) -> Dict[str, List[Dict]]:
        """업종별 그룹화"""
        grouped = defaultdict(list)
        
        for stock in stocks:
            stock_code = stock.get("stock_code")
            sector = sector_mapping.get(stock_code, "기타")
            grouped[sector].append(stock)
        
        return dict(grouped)
```

## 6. 에러 처리 및 재시도

```python
# src/exceptions.py
class VolumeRankingError(Exception):
    """거래대금 순위 기본 예외"""
    pass

class APILimitError(VolumeRankingError):
    """API 제한 초과"""
    pass

class DataValidationError(VolumeRankingError):
    """데이터 검증 실패"""
    pass

class MarketClosedError(VolumeRankingError):
    """장 마감 시간"""
    pass

# src/utils/retry.py
import asyncio
from functools import wraps
from typing import TypeVar, Callable
import logging
from datetime import datetime, time

logger = logging.getLogger(__name__)

def check_market_hours(func):
    """장 운영 시간 체크 데코레이터"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        now = datetime.now()
        current_time = now.time()
        
        # 주말 체크
        if now.weekday() >= 5:  # 토요일(5), 일요일(6)
            raise MarketClosedError("주말에는 거래가 없습니다.")
        
        # 장 시간 체크 (오전 9시 ~ 오후 3시 30분)
        market_open = time(9, 0)
        market_close = time(15, 30)
        
        if not (market_open <= current_time <= market_close):
            # 장 시간 외에도 캐시된 데이터 반환 가능
            kwargs["use_cache_only"] = True
            logger.info("장 마감 시간입니다. 캐시된 데이터를 반환합니다.")
        
        return await func(*args, **kwargs)
    
    return wrapper
```

## 7. 구현 일정

### Phase 1: 기초 구현 (3일)
- [ ] 프로젝트 구조 설정
- [ ] MCP 서버 기본 설정
- [ ] 한국투자증권 API 클라이언트 구현
- [ ] 기본 거래대금 순위 도구 구현

### Phase 2: 핵심 기능 (5일)
- [ ] 6개 주요 도구 구현
- [ ] 계층적 캐싱 시스템 구현
- [ ] 순위 계산 로직 구현
- [ ] 투자자별 순위 기능 구현

### Phase 3: 고도화 (3일)
- [ ] 이상 거래량 감지 기능
- [ ] 업종별 분석 기능
- [ ] 성능 최적화
- [ ] 단위 테스트 작성

### Phase 4: 통합 및 배포 (2일)
- [ ] 통합 테스트
- [ ] 문서화
- [ ] Docker 이미지 생성
- [ ] 배포 준비

## 8. 테스트 계획

### 8.1 단위 테스트

```python
# tests/test_tools.py
import pytest
from src.tools.volume_tools import get_volume_ranking
from src.utils.calculator import RankingCalculator

@pytest.mark.asyncio
async def test_get_volume_ranking():
    """거래대금 순위 조회 테스트"""
    result = await get_volume_ranking(market="ALL", count=10)
    
    assert "ranking" in result
    assert len(result["ranking"]) <= 10
    assert result["ranking"][0]["rank"] == 1
    
    # 순위가 거래대금 순으로 정렬되었는지 확인
    for i in range(1, len(result["ranking"])):
        assert result["ranking"][i-1]["trading_value"] >= result["ranking"][i]["trading_value"]

@pytest.mark.asyncio
async def test_unusual_volume_detection():
    """이상 거래량 감지 테스트"""
    calculator = RankingCalculator()
    
    # 정상 거래량
    is_unusual, ratio = calculator.detect_unusual_volume(
        current_volume=1000000,
        historical_volumes=[900000, 950000, 1100000, 1050000, 980000]
    )
    assert not is_unusual
    
    # 이상 거래량
    is_unusual, ratio = calculator.detect_unusual_volume(
        current_volume=5000000,
        historical_volumes=[900000, 950000, 1100000, 1050000, 980000]
    )
    assert is_unusual
    assert ratio > 400

@pytest.mark.asyncio
async def test_cache_performance():
    """캐시 성능 테스트"""
    from src.utils.cache import HierarchicalCache
    
    cache = HierarchicalCache()
    
    call_count = 0
    async def fetch_func():
        nonlocal call_count
        call_count += 1
        return {"data": "test"}
    
    # 첫 번째 호출 - 캐시 미스
    await cache.get_or_fetch("test_tool", {"param": 1}, fetch_func)
    assert call_count == 1
    assert cache.cache_stats["misses"] == 1
    
    # 두 번째 호출 - L1 캐시 히트
    await cache.get_or_fetch("test_tool", {"param": 1}, fetch_func)
    assert call_count == 1
    assert cache.cache_stats["l1_hits"] == 1
```

### 8.2 통합 테스트
- API 연동 테스트
- 전체 순위 조회 플로우 테스트
- 실시간 데이터 업데이트 테스트
- 장시간 운영 안정성 테스트

## 9. 배포 및 운영

### 9.1 환경 설정

```bash
# .env 파일
KOREA_INVESTMENT_APP_KEY=your_app_key
KOREA_INVESTMENT_APP_SECRET=your_app_secret
CACHE_L1_TTL_SECONDS=60
CACHE_L2_TTL_SECONDS=300
LOG_LEVEL=INFO
MAX_RANKING_COUNT=50
UNUSUAL_VOLUME_THRESHOLD=200
```

### 9.2 Docker 설정

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 실행
CMD ["python", "-m", "src.server"]
```

### 9.3 Docker Compose 설정

```yaml
# docker-compose.yml
version: '3.8'

services:
  mcp-volume-ranking:
    build: .
    container_name: mcp-volume-ranking
    environment:
      - KOREA_INVESTMENT_APP_KEY=${KOREA_INVESTMENT_APP_KEY}
      - KOREA_INVESTMENT_APP_SECRET=${KOREA_INVESTMENT_APP_SECRET}
    ports:
      - "8081:8080"
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## 10. 모니터링 및 유지보수

### 10.1 성능 모니터링

```python
# src/utils/monitoring.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List
import json

@dataclass
class PerformanceMetrics:
    """성능 메트릭"""
    tool_name: str
    response_time: float
    cache_hit: bool
    timestamp: datetime = field(default_factory=datetime.now)
    
class PerformanceMonitor:
    """성능 모니터링"""
    
    def __init__(self):
        self.metrics: List[PerformanceMetrics] = []
        self.threshold_alerts = {
            "response_time": 2.0,  # 2초
            "error_rate": 0.05,    # 5%
            "cache_hit_rate": 0.7  # 70%
        }
    
    def record_metric(self, metric: PerformanceMetrics):
        """메트릭 기록"""
        self.metrics.append(metric)
        self._check_thresholds()
    
    def _check_thresholds(self):
        """임계값 체크"""
        if len(self.metrics) < 100:
            return
        
        recent_metrics = self.metrics[-100:]
        
        # 평균 응답 시간
        avg_response_time = sum(m.response_time for m in recent_metrics) / len(recent_metrics)
        if avg_response_time > self.threshold_alerts["response_time"]:
            self._send_alert(f"높은 응답 시간: {avg_response_time:.2f}초")
        
        # 캐시 히트율
        cache_hits = sum(1 for m in recent_metrics if m.cache_hit)
        cache_hit_rate = cache_hits / len(recent_metrics)
        if cache_hit_rate < self.threshold_alerts["cache_hit_rate"]:
            self._send_alert(f"낮은 캐시 히트율: {cache_hit_rate:.1%}")
    
    def get_summary(self) -> Dict:
        """성능 요약"""
        if not self.metrics:
            return {}
        
        total = len(self.metrics)
        cache_hits = sum(1 for m in self.metrics if m.cache_hit)
        avg_response_time = sum(m.response_time for m in self.metrics) / total
        
        tool_stats = {}
        for metric in self.metrics:
            if metric.tool_name not in tool_stats:
                tool_stats[metric.tool_name] = {
                    "count": 0,
                    "total_time": 0,
                    "cache_hits": 0
                }
            
            stats = tool_stats[metric.tool_name]
            stats["count"] += 1
            stats["total_time"] += metric.response_time
            stats["cache_hits"] += 1 if metric.cache_hit else 0
        
        return {
            "total_requests": total,
            "average_response_time": avg_response_time,
            "cache_hit_rate": cache_hits / total * 100,
            "tool_statistics": {
                name: {
                    "count": stats["count"],
                    "average_time": stats["total_time"] / stats["count"],
                    "cache_hit_rate": stats["cache_hits"] / stats["count"] * 100
                }
                for name, stats in tool_stats.items()
            }
        }
```

### 10.2 로그 분석

```python
# src/utils/log_analyzer.py
import re
from collections import Counter
from datetime import datetime
from typing import List, Dict

class LogAnalyzer:
    """로그 분석기"""
    
    def __init__(self, log_file_path: str):
        self.log_file_path = log_file_path
        self.patterns = {
            "error": re.compile(r"ERROR.*"),
            "api_call": re.compile(r"API call to (.+) took (\d+\.\d+)s"),
            "cache_hit": re.compile(r"Cache hit for (.+)"),
            "unusual_volume": re.compile(r"Unusual volume detected: (.+)")
        }
    
    def analyze_logs(self, start_time: datetime = None) -> Dict:
        """로그 분석"""
        errors = []
        api_calls = []
        cache_hits = Counter()
        unusual_volumes = []
        
        with open(self.log_file_path, 'r') as f:
            for line in f:
                # 에러 분석
                if self.patterns["error"].search(line):
                    errors.append(line.strip())
                
                # API 호출 분석
                api_match = self.patterns["api_call"].search(line)
                if api_match:
                    api_calls.append({
                        "endpoint": api_match.group(1),
                        "duration": float(api_match.group(2))
                    })
                
                # 캐시 히트 분석
                cache_match = self.patterns["cache_hit"].search(line)
                if cache_match:
                    cache_hits[cache_match.group(1)] += 1
                
                # 이상 거래량 분석
                unusual_match = self.patterns["unusual_volume"].search(line)
                if unusual_match:
                    unusual_volumes.append(unusual_match.group(1))
        
        return {
            "error_count": len(errors),
            "recent_errors": errors[-10:],
            "api_call_stats": self._calculate_api_stats(api_calls),
            "cache_hit_distribution": dict(cache_hits),
            "unusual_volume_count": len(unusual_volumes),
            "recent_unusual_volumes": unusual_volumes[-10:]
        }
    
    def _calculate_api_stats(self, api_calls: List[Dict]) -> Dict:
        """API 호출 통계 계산"""
        if not api_calls:
            return {}
        
        durations = [call["duration"] for call in api_calls]
        return {
            "total_calls": len(api_calls),
            "average_duration": sum(durations) / len(durations),
            "max_duration": max(durations),
            "min_duration": min(durations)
        }
```

### 10.3 알림 시스템

- API 응답 시간 초과
- 캐시 히트율 저하
- 이상 거래량 다수 감지
- 에러율 상승
- 메모리 사용량 초과

## 11. 보안 고려사항

### 11.1 API 보안
- API 키 환경변수 관리
- 요청 rate limiting
- IP 화이트리스트 (프로덕션)

### 11.2 데이터 보안
- 민감 정보 로그 제외
- 캐시 데이터 암호화 (선택적)
- 정기적 보안 감사

### 11.3 접근 제어
- MCP 서버 인증
- 도구별 권한 관리
- 감사 로그 유지

이 계획서를 통해 효율적이고 안정적인 거래대금 순위 MCP 서버를 구축할 수 있습니다.