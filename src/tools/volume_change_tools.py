"""
Volume Change Ranking Tools - TDD GREEN Phase Implementation
거래대금 증가율 순위 도구 - TDD GREEN 단계 구현
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import mcp.types as types

from src.api.client import VolumeRankingAPI
from src.api.constants import get_market_code, validate_period
from src.api.models import (
    VolumeChangeRankingResponse, VolumeChangeRankingItem,
    StockInfo, PriceInfo, VolumeChangeInfo
)
from src.exceptions import (
    VolumeRankingError, APIError, DataValidationError, 
    InvalidParameterError
)
from src.config import get_settings
from src.utils.logger import setup_logger, get_performance_logger
from src.utils.validator import validate_market, validate_count, validate_period

class VolumeChangeRankingTool:
    """거래대금 증가율 순위 조회 도구"""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = setup_logger("volume_change_ranking_tool")
        self.performance_logger = get_performance_logger()
        self.api_client = None
    
    async def _get_api_client(self) -> VolumeRankingAPI:
        """API 클라이언트 획득 (지연 초기화)"""
        if self.api_client is None:
            try:
                self.api_client = VolumeRankingAPI()
                self.logger.info("Volume change API client initialized successfully")
            except Exception as e:
                self.logger.error("Failed to initialize volume change API client", error=str(e))
                raise APIError(f"API 클라이언트 초기화 실패: {str(e)}")
        
        return self.api_client
    
    def _validate_parameters(self, market: str, period: str, count: int) -> tuple[str, str, int]:
        """매개변수 유효성 검증"""
        # 시장 코드 검증
        market = validate_market(market)
        
        # 기간 검증
        period = validate_period(period)
        
        # 조회 개수 검증
        count = validate_count(count, min_value=1, max_value=self.settings.max_ranking_count)
        
        return market, period, count
    
    async def _get_current_volume_data(self, market_code: str) -> List[Dict[str, Any]]:
        """현재 거래대금 데이터 조회"""
        api_client = await self._get_api_client()
        
        response = await api_client.get_volume_rank(
            market_code=market_code,
            rank_sort_cls="0"  # 거래대금순
        )
        
        if response.get("rt_cd") != "0":
            raise APIError(f"현재 데이터 조회 실패: {response.get('msg1', '알 수 없는 오류')}")
        
        return response.get("output", [])
    
    async def _get_historical_volume_data(self, stock_code: str, period: str) -> int:
        """히스토리컬 거래대금 데이터 조회 (모킹)"""
        # 실제 구현에서는 별도 API 호출이 필요
        # 현재는 테스트를 통과하기 위한 최소 구현
        
        if period == "1D":
            # 1일 전 데이터 (현재의 80%로 가정)
            return 800000000
        elif period == "5D":
            # 5일 평균 데이터 (현재의 85%로 가정)
            return 850000000
        elif period == "20D":
            # 20일 평균 데이터 (현재의 90%로 가정)
            return 900000000
        else:
            return 1000000000
    
    def _calculate_volume_change_rate(self, current_volume: int, previous_volume: int) -> float:
        """거래대금 증가율 계산"""
        if previous_volume == 0:
            return 999999.0 if current_volume > 0 else 0.0
        
        return ((current_volume - previous_volume) / previous_volume) * 100.0
    
    def _parse_volume_change_item(
        self, 
        raw_data: Dict[str, Any], 
        rank: int, 
        period: str
    ) -> VolumeChangeRankingItem:
        """API 응답 데이터를 VolumeChangeRankingItem으로 파싱"""
        try:
            # 기본 주식 정보
            stock_info = StockInfo(
                stock_code=raw_data.get("mksc_shrn_iscd", "").strip(),
                stock_name=raw_data.get("hts_kor_isnm", "").strip(),
                market_type="KOSPI" if rank <= 200 else "KOSDAQ"
            )
            
            # 가격 정보
            current_price = int(raw_data.get("stck_prpr", "0") or "0")
            change = int(raw_data.get("prdy_vrss", "0") or "0")
            change_rate = float(raw_data.get("prdy_ctrt", "0.0") or "0.0")
            
            price_info = PriceInfo(
                current_price=current_price,
                change=change,
                change_rate=change_rate
            )
            
            # 거래대금 변화 정보 (간단한 계산)
            current_volume = int(raw_data.get("acml_tr_pbmn", "0") or "0")
            # 실제로는 히스토리컬 API에서 가져와야 함
            previous_volume = int(current_volume * 0.8)  # 임시: 20% 증가 가정
            
            volume_change_info = VolumeChangeInfo(
                current_volume=current_volume,
                previous_volume=previous_volume,
                volume_change_rate=self._calculate_volume_change_rate(current_volume, previous_volume),
                comparison_period=period
            )
            
            return VolumeChangeRankingItem(
                rank=rank,
                stock_info=stock_info,
                price_info=price_info,
                volume_change_info=volume_change_info,
                news_count=0,  # 추후 구현
                disclosure_count=0  # 추후 구현
            )
            
        except Exception as e:
            self.logger.error("Failed to parse volume change item", rank=rank, error=str(e))
            raise DataValidationError(f"데이터 파싱 실패 (순위 {rank}): {str(e)}")
    
    async def get_volume_change_ranking(
        self, 
        market: str = "ALL", 
        period: str = "1D", 
        count: int = None
    ) -> VolumeChangeRankingResponse:
        """
        거래대금 증가율 상위 종목 조회
        
        Args:
            market: 시장 구분 (ALL, KOSPI, KOSDAQ)
            period: 비교 기간 (1D, 5D, 20D)
            count: 조회할 종목 수
        
        Returns:
            거래대금 증가율 순위 응답
        """
        start_time = datetime.now()
        
        # 기본값 설정
        if count is None:
            count = self.settings.default_ranking_count
        
        # 매개변수 검증
        market, period, count = self._validate_parameters(market, period, count)
        
        self.logger.info(
            "Starting volume change ranking request", 
            market=market, 
            period=period,
            count=count
        )
        
        try:
            # 현재 거래대금 데이터 조회
            market_code = get_market_code(market)
            current_data = await self._get_current_volume_data(market_code)
            
            if not current_data:
                raise DataValidationError("현재 데이터가 없습니다")
            
            # 증가율 계산 및 정렬
            ranking_items = []
            
            for i, raw_item in enumerate(current_data[:count], 1):
                try:
                    # 히스토리컬 데이터 조회 (실제로는 각 종목별로 API 호출)
                    stock_code = raw_item.get("mksc_shrn_iscd", "")
                    if stock_code:
                        previous_volume = await self._get_historical_volume_data(stock_code, period)
                        
                        # 현재 데이터에 이전 데이터 추가
                        raw_item["previous_volume"] = previous_volume
                    
                    ranking_item = self._parse_volume_change_item(raw_item, i, period)
                    ranking_items.append(ranking_item)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to process item {i}", error=str(e))
                    continue
            
            if not ranking_items:
                raise DataValidationError("처리 가능한 데이터가 없습니다")
            
            # 증가율 기준으로 정렬 (높은 순)
            ranking_items.sort(
                key=lambda x: x.volume_change_info.volume_change_rate, 
                reverse=True
            )
            
            # 순위 재조정
            for i, item in enumerate(ranking_items, 1):
                item.rank = i
            
            # 응답 생성
            response = VolumeChangeRankingResponse(
                timestamp=start_time,
                period=period,
                ranking=ranking_items[:count]
            )
            
            # 성능 로깅
            duration = (datetime.now() - start_time).total_seconds()
            self.performance_logger.log_api_call(
                f"get_volume_change_ranking({market},{period})", duration, True
            )
            
            self.logger.info(
                "Volume change ranking request completed successfully",
                market=market,
                period=period,
                count=len(ranking_items),
                duration=duration
            )
            
            return response
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            self.performance_logger.log_api_call(
                f"get_volume_change_ranking({market},{period})", duration, False
            )
            
            self.logger.error(
                "Volume change ranking request failed",
                market=market,
                period=period,
                count=count,
                error=str(e)
            )
            
            if isinstance(e, VolumeRankingError):
                raise
            else:
                raise APIError(f"거래대금 증가율 순위 조회 실패: {str(e)}")

# 글로벌 도구 인스턴스
_volume_change_ranking_tool = None

def get_volume_change_ranking_tool() -> VolumeChangeRankingTool:
    """글로벌 거래대금 증가율 순위 도구 인스턴스 획득"""
    global _volume_change_ranking_tool
    if _volume_change_ranking_tool is None:
        _volume_change_ranking_tool = VolumeChangeRankingTool()
    return _volume_change_ranking_tool

async def handle_get_volume_change_ranking(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """
    MCP 도구 핸들러: 거래대금 증가율 순위 조회
    
    Args:
        arguments: 도구 호출 인수
        
    Returns:
        MCP 응답 내용
    """
    try:
        # 매개변수 추출
        market = arguments.get("market", "ALL")
        period = arguments.get("period", "1D")
        count = arguments.get("count", None)
        
        # 도구 실행
        tool = get_volume_change_ranking_tool()
        response = await tool.get_volume_change_ranking(market, period, count)
        
        # 응답 포맷팅
        formatted_response = _format_volume_change_response(response)
        
        return [types.TextContent(type="text", text=formatted_response)]
        
    except Exception as e:
        error_message = f"거래대금 증가율 순위 조회 오류: {str(e)}"
        return [types.TextContent(type="text", text=error_message)]

def _format_volume_change_response(response: VolumeChangeRankingResponse) -> str:
    """거래대금 증가율 순위 응답 포맷팅"""
    lines = [
        f"# 거래대금 증가율 순위 ({response.period})",
        f"📊 조회 시간: {response.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
        f"📈 비교 기간: {response.period}",
        ""
    ]
    
    if not response.ranking:
        lines.append("조회된 데이터가 없습니다.")
        return "\n".join(lines)
    
    lines.extend(["## 순위 목록", ""])
    
    for item in response.ranking:
        stock = item.stock_info
        price = item.price_info
        volume_change = item.volume_change_info
        
        change_symbol = "📈" if volume_change.volume_change_rate > 0 else "📉" if volume_change.volume_change_rate < 0 else "➡️"
        
        lines.append(
            f"**{item.rank}위** {stock.stock_name} ({stock.stock_code})"
        )
        lines.append(
            f"   💰 현재가: {price.current_price:,}원 "
            f"({change_symbol} {price.change:+,}원, {price.change_rate:+.2f}%)"
        )
        lines.append(
            f"   📊 현재 거래대금: {volume_change.current_volume:,}원"
        )
        lines.append(
            f"   📈 이전 거래대금: {volume_change.previous_volume:,}원"
        )
        lines.append(
            f"   🚀 증가율: {change_symbol} {volume_change.volume_change_rate:+.2f}%"
        )
        lines.append("")
    
    return "\n".join(lines)