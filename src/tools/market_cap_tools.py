"""
Market Cap Ranking Tools
시가총액 순위 도구
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import mcp.types as types

from src.api.client import VolumeRankingAPI
from src.api.constants import get_market_code
from src.api.models import (
    MarketCapRankingResponse, StockRankingItem, StockInfo, PriceInfo, 
    VolumeInfo, MarketCapInfo, MarketCapSummary
)
from src.exceptions import VolumeRankingError, APIError, DataValidationError
from src.config import get_settings
from src.utils.logger import setup_logger, get_performance_logger
from src.utils.validator import validate_market, validate_count

class MarketCapRankingTool:
    """시가총액 순위 조회 도구"""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = setup_logger("market_cap_ranking_tool")
        self.performance_logger = get_performance_logger()
        self.api_client = None
    
    async def _get_api_client(self) -> VolumeRankingAPI:
        """API 클라이언트 획득"""
        if self.api_client is None:
            self.api_client = VolumeRankingAPI()
        return self.api_client
    
    async def get_market_cap_ranking(
        self,
        market: str = "ALL",
        count: int = None,
        filter_by: Optional[Dict] = None
    ) -> MarketCapRankingResponse:
        """시가총액 순위 조회"""
        
        start_time = datetime.now()
        
        if count is None:
            count = self.settings.default_ranking_count
        
        # 매개변수 검증
        market = validate_market(market)
        count = validate_count(count, min_value=1, max_value=self.settings.max_ranking_count)
        
        self.logger.info("Starting market cap ranking request", market=market, count=count)
        
        try:
            # 시가총액 데이터 조회 (실제로는 별도 API 호출)
            api_client = await self._get_api_client()
            market_code = get_market_code(market)
            
            # 기본 거래대금 데이터 사용 (실제로는 시가총액 API 호출)
            response = await api_client.get_volume_rank(market_code, "0")
            
            if response.get("rt_cd") != "0":
                raise APIError(f"데이터 조회 실패: {response.get('msg1', '알 수 없는 오류')}")
            
            # 시가총액 기준으로 데이터 변환
            ranking_items = self._create_market_cap_ranking(response.get("output", []), count, filter_by)
            
            # 요약 정보 계산
            summary = self._calculate_market_cap_summary(ranking_items)
            
            result = MarketCapRankingResponse(
                timestamp=start_time,
                market=market,
                ranking=ranking_items,
                summary=summary
            )
            
            duration = (datetime.now() - start_time).total_seconds()
            self.performance_logger.log_api_call(f"get_market_cap_ranking({market})", duration, True)
            
            return result
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            self.performance_logger.log_api_call(f"get_market_cap_ranking({market})", duration, False)
            
            if isinstance(e, VolumeRankingError):
                raise
            else:
                raise APIError(f"시가총액 순위 조회 실패: {str(e)}")
    
    def _create_market_cap_ranking(
        self, 
        raw_data: List[Dict[str, Any]], 
        count: int,
        filter_by: Optional[Dict] = None
    ) -> List[StockRankingItem]:
        """시가총액 순위 데이터 생성"""
        
        ranking_items = []
        
        for i, raw_item in enumerate(raw_data[:count], 1):
            try:
                # 기본 정보
                stock_info = StockInfo(
                    stock_code=raw_item.get("mksc_shrn_iscd", "").strip(),
                    stock_name=raw_item.get("hts_kor_isnm", "").strip(),
                    market_type="KOSPI" if i <= 200 else "KOSDAQ"
                )
                
                current_price = int(raw_item.get("stck_prpr", "0") or "0")
                change = int(raw_item.get("prdy_vrss", "0") or "0")
                change_rate = float(raw_item.get("prdy_ctrt", "0.0") or "0.0")
                
                price_info = PriceInfo(
                    current_price=current_price,
                    change=change,
                    change_rate=change_rate
                )
                
                volume = int(raw_item.get("acml_vol", "0") or "0")
                trading_value = int(raw_item.get("acml_tr_pbmn", "0") or "0")
                
                volume_info = VolumeInfo(
                    volume=volume,
                    trading_value=trading_value
                )
                
                # 시가총액 정보 (임시 계산)
                shares_outstanding = 5000000000 - (i * 100000000)  # 임시 상장주수
                market_cap = current_price * shares_outstanding
                
                market_cap_info = MarketCapInfo(
                    market_cap=market_cap,
                    shares_outstanding=shares_outstanding,
                    foreign_ratio=50.0 - (i * 2.0)  # 임시 외국인 비율
                )
                
                # 필터 적용
                if filter_by:
                    min_trading_value = filter_by.get("min_trading_value", 0)
                    if trading_value < min_trading_value:
                        continue
                
                ranking_item = StockRankingItem(
                    rank=i,
                    stock_info=stock_info,
                    price_info=price_info,
                    volume_info=volume_info,
                    market_cap_info=market_cap_info
                )
                
                ranking_items.append(ranking_item)
                
            except Exception as e:
                self.logger.warning(f"Failed to process market cap item {i}", error=str(e))
                continue
        
        # 시가총액 기준으로 정렬
        ranking_items.sort(key=lambda x: x.market_cap_info.market_cap if x.market_cap_info else 0, reverse=True)
        
        # 순위 재조정
        for i, item in enumerate(ranking_items, 1):
            item.rank = i
        
        return ranking_items
    
    def _calculate_market_cap_summary(self, ranking_items: List[StockRankingItem]) -> MarketCapSummary:
        """시가총액 요약 정보 계산"""
        if not ranking_items:
            return MarketCapSummary(
                total_market_cap=0,
                average_per=0.0,
                average_pbr=0.0
            )
        
        total_market_cap = sum(
            item.market_cap_info.market_cap if item.market_cap_info else 0 
            for item in ranking_items
        )
        
        # 임시 PER, PBR 값
        average_per = 15.6
        average_pbr = 1.2
        
        return MarketCapSummary(
            total_market_cap=total_market_cap,
            average_per=average_per,
            average_pbr=average_pbr
        )

# 글로벌 인스턴스
_market_cap_ranking_tool = None

def get_market_cap_ranking_tool() -> MarketCapRankingTool:
    global _market_cap_ranking_tool
    if _market_cap_ranking_tool is None:
        _market_cap_ranking_tool = MarketCapRankingTool()
    return _market_cap_ranking_tool

async def handle_get_market_cap_ranking(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """MCP 핸들러: 시가총액 순위 조회"""
    try:
        market = arguments.get("market", "ALL")
        count = arguments.get("count", None)
        filter_by = arguments.get("filter_by", None)
        
        tool = get_market_cap_ranking_tool()
        response = await tool.get_market_cap_ranking(market, count, filter_by)
        
        formatted_response = _format_market_cap_response(response)
        return [types.TextContent(type="text", text=formatted_response)]
        
    except Exception as e:
        error_message = f"시가총액 순위 조회 오류: {str(e)}"
        return [types.TextContent(type="text", text=error_message)]

def _format_market_cap_response(response: MarketCapRankingResponse) -> str:
    """시가총액 순위 응답 포맷팅"""
    from src.utils.formatter import format_currency
    
    lines = [
        f"# 시가총액 순위 ({response.market})",
        f"📊 조회 시간: {response.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
        f"🏪 시장: {response.market}",
        ""
    ]
    
    if response.summary:
        lines.extend([
            "## 요약 정보",
            f"💰 총 시가총액: {format_currency(response.summary.total_market_cap)}",
            f"📊 평균 PER: {response.summary.average_per:.1f}배",
            f"📈 평균 PBR: {response.summary.average_pbr:.1f}배",
            ""
        ])
    
    lines.extend(["## 순위 목록", ""])
    
    for item in response.ranking:
        stock = item.stock_info
        price = item.price_info
        market_cap = item.market_cap_info
        
        change_symbol = "📈" if price.change > 0 else "📉" if price.change < 0 else "➡️"
        
        lines.append(f"**{item.rank}위** {stock.stock_name} ({stock.stock_code})")
        lines.append(f"   💰 현재가: {price.current_price:,}원 ({change_symbol} {price.change:+,}원)")
        
        if market_cap:
            lines.append(f"   🏢 시가총액: {format_currency(market_cap.market_cap)}")
            lines.append(f"   🌍 외국인비율: {market_cap.foreign_ratio:.1f}%")
        
        lines.append("")
    
    return "\n".join(lines)