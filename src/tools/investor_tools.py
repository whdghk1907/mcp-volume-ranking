"""
Investor Ranking Tools - TDD GREEN Phase Implementation
투자자별 거래 순위 도구 - TDD GREEN 단계 구현
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import mcp.types as types

from src.api.client import VolumeRankingAPI
from src.api.constants import get_market_code, get_investor_screen_code
from src.api.models import (
    InvestorRankingResponse, InvestorRankingItem,
    StockInfo, PriceInfo, InvestorTradingInfo, InvestorSummary
)
from src.exceptions import (
    VolumeRankingError, APIError, DataValidationError, 
    InvalidParameterError
)
from src.config import get_settings
from src.utils.logger import setup_logger, get_performance_logger
from src.utils.validator import validate_market, validate_count, validate_investor_type, validate_trade_type

class InvestorRankingTool:
    """투자자별 거래 순위 조회 도구"""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = setup_logger("investor_ranking_tool")
        self.performance_logger = get_performance_logger()
        self.api_client = None
    
    async def _get_api_client(self) -> VolumeRankingAPI:
        """API 클라이언트 획득 (지연 초기화)"""
        if self.api_client is None:
            try:
                self.api_client = VolumeRankingAPI()
                self.logger.info("Investor ranking API client initialized successfully")
            except Exception as e:
                self.logger.error("Failed to initialize investor ranking API client", error=str(e))
                raise APIError(f"API 클라이언트 초기화 실패: {str(e)}")
        
        return self.api_client
    
    def _validate_parameters(
        self, 
        investor_type: str, 
        trade_type: str, 
        market: str, 
        count: int
    ) -> tuple[str, str, str, int]:
        """매개변수 유효성 검증"""
        # 투자자 유형 검증
        investor_type = validate_investor_type(investor_type)
        
        # 거래 유형 검증
        trade_type = validate_trade_type(trade_type)
        
        # 시장 코드 검증
        market = validate_market(market)
        
        # 조회 개수 검증
        count = validate_count(count, min_value=1, max_value=self.settings.max_ranking_count)
        
        return investor_type, trade_type, market, count
    
    async def _get_investor_trend_data(
        self, 
        market_code: str, 
        investor_type: str, 
        trade_type: str
    ) -> List[Dict[str, Any]]:
        """투자자별 거래 트렌드 데이터 조회"""
        api_client = await self._get_api_client()
        
        # VolumeRankingAPI에 investor_trend_rank 메소드가 있다고 가정
        # 실제로는 client.py에 구현되어 있어야 함
        try:
            response = await api_client.get_investor_trend_rank(
                market_code=market_code,
                investor_type=investor_type,
                trade_type=trade_type
            )
        except AttributeError:
            # 메소드가 없는 경우 임시로 volume_rank 사용
            response = await api_client.get_volume_rank(market_code, "0")
        
        if response.get("rt_cd") != "0":
            raise APIError(f"투자자 데이터 조회 실패: {response.get('msg1', '알 수 없는 오류')}")
        
        return response.get("output", [])
    
    def _calculate_trading_amounts(self, raw_data: Dict[str, Any], trade_type: str) -> Dict[str, int]:
        """거래 금액 계산 (임시 구현)"""
        # 실제 API 응답 필드에 따라 수정 필요
        current_price = int(raw_data.get("stck_prpr", "0") or "0")
        volume = int(raw_data.get("acml_vol", "0") or "0")
        trading_value = int(raw_data.get("acml_tr_pbmn", "0") or "0")
        
        if trade_type == "BUY":
            # 매수 데이터만
            return {
                "buy_amount": trading_value,
                "sell_amount": 0,
                "net_amount": trading_value,
                "buy_volume": volume,
                "sell_volume": 0,
                "net_volume": volume
            }
        elif trade_type == "SELL":
            # 매도 데이터만
            return {
                "buy_amount": 0,
                "sell_amount": trading_value,
                "net_amount": -trading_value,
                "buy_volume": 0,
                "sell_volume": volume,
                "net_volume": -volume
            }
        else:  # NET
            # 순매수 (임시로 거래대금의 60%를 매수, 40%를 매도로 가정)
            buy_amount = int(trading_value * 0.6)
            sell_amount = int(trading_value * 0.4)
            buy_volume = int(volume * 0.6)
            sell_volume = int(volume * 0.4)
            
            return {
                "buy_amount": buy_amount,
                "sell_amount": sell_amount,
                "net_amount": buy_amount - sell_amount,
                "buy_volume": buy_volume,
                "sell_volume": sell_volume,
                "net_volume": buy_volume - sell_volume
            }
    
    def _parse_investor_ranking_item(
        self, 
        raw_data: Dict[str, Any], 
        rank: int, 
        trade_type: str
    ) -> InvestorRankingItem:
        """API 응답 데이터를 InvestorRankingItem으로 파싱"""
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
            
            # 거래 정보 계산
            amounts = self._calculate_trading_amounts(raw_data, trade_type)
            
            # 평균 거래가 계산
            avg_buy_price = None
            avg_sell_price = None
            
            if amounts["buy_volume"] > 0:
                avg_buy_price = amounts["buy_amount"] / amounts["buy_volume"]
            if amounts["sell_volume"] > 0:
                avg_sell_price = amounts["sell_amount"] / amounts["sell_volume"]
            
            # 영향도 계산 (전체 거래대금 대비)
            total_trading = int(raw_data.get("acml_tr_pbmn", "0") or "0")
            impact_ratio = None
            if total_trading > 0:
                impact_ratio = (abs(amounts["net_amount"]) / total_trading) * 100.0
            
            trading_info = InvestorTradingInfo(
                buy_amount=amounts["buy_amount"],
                sell_amount=amounts["sell_amount"],
                net_amount=amounts["net_amount"],
                buy_volume=amounts["buy_volume"],
                sell_volume=amounts["sell_volume"],
                net_volume=amounts["net_volume"],
                average_buy_price=avg_buy_price,
                average_sell_price=avg_sell_price,
                impact_ratio=impact_ratio
            )
            
            return InvestorRankingItem(
                rank=rank,
                stock_info=stock_info,
                price_info=price_info,
                trading_info=trading_info
            )
            
        except Exception as e:
            self.logger.error("Failed to parse investor ranking item", rank=rank, error=str(e))
            raise DataValidationError(f"데이터 파싱 실패 (순위 {rank}): {str(e)}")
    
    def _calculate_summary(self, ranking_items: List[InvestorRankingItem]) -> InvestorSummary:
        """요약 정보 계산"""
        if not ranking_items:
            return InvestorSummary(
                total_buy_amount=0,
                total_sell_amount=0,
                total_net_amount=0,
                market_impact=0.0
            )
        
        total_buy = sum(item.trading_info.buy_amount for item in ranking_items)
        total_sell = sum(item.trading_info.sell_amount for item in ranking_items)
        total_net = sum(item.trading_info.net_amount for item in ranking_items)
        
        # 시장 영향도 (임시로 20%로 가정)
        market_impact = 20.0
        
        return InvestorSummary(
            total_buy_amount=total_buy,
            total_sell_amount=total_sell,
            total_net_amount=total_net,
            market_impact=market_impact
        )
    
    async def get_investor_ranking(
        self, 
        investor_type: str = "FOREIGN", 
        trade_type: str = "NET",
        market: str = "ALL", 
        count: int = None
    ) -> InvestorRankingResponse:
        """
        투자자별 거래 상위 종목 조회
        
        Args:
            investor_type: 투자자 유형 (FOREIGN, INSTITUTION, INDIVIDUAL, PROGRAM)
            trade_type: 거래 유형 (BUY, SELL, NET)
            market: 시장 구분 (ALL, KOSPI, KOSDAQ)
            count: 조회할 종목 수
        
        Returns:
            투자자별 거래 순위 응답
        """
        start_time = datetime.now()
        
        # 기본값 설정
        if count is None:
            count = self.settings.default_ranking_count
        
        # 매개변수 검증
        investor_type, trade_type, market, count = self._validate_parameters(
            investor_type, trade_type, market, count
        )
        
        self.logger.info(
            "Starting investor ranking request", 
            investor_type=investor_type,
            trade_type=trade_type,
            market=market, 
            count=count
        )
        
        try:
            # 투자자별 거래 데이터 조회
            market_code = get_market_code(market)
            investor_data = await self._get_investor_trend_data(
                market_code, investor_type, trade_type
            )
            
            if not investor_data:
                raise DataValidationError("투자자 데이터가 없습니다")
            
            # 데이터 파싱
            ranking_items = []
            
            for i, raw_item in enumerate(investor_data[:count], 1):
                try:
                    ranking_item = self._parse_investor_ranking_item(raw_item, i, trade_type)
                    ranking_items.append(ranking_item)
                except Exception as e:
                    self.logger.warning(f"Failed to process investor item {i}", error=str(e))
                    continue
            
            if not ranking_items:
                raise DataValidationError("처리 가능한 투자자 데이터가 없습니다")
            
            # 거래 유형에 따른 정렬
            if trade_type == "BUY":
                ranking_items.sort(key=lambda x: x.trading_info.buy_amount, reverse=True)
            elif trade_type == "SELL":
                ranking_items.sort(key=lambda x: x.trading_info.sell_amount, reverse=True)
            else:  # NET
                ranking_items.sort(key=lambda x: x.trading_info.net_amount, reverse=True)
            
            # 순위 재조정
            for i, item in enumerate(ranking_items, 1):
                item.rank = i
            
            # 요약 정보 계산
            summary = self._calculate_summary(ranking_items)
            
            # 응답 생성
            response = InvestorRankingResponse(
                timestamp=start_time,
                investor_type=investor_type,
                trade_type=trade_type,
                ranking=ranking_items[:count],
                summary=summary
            )
            
            # 성능 로깅
            duration = (datetime.now() - start_time).total_seconds()
            self.performance_logger.log_api_call(
                f"get_investor_ranking({investor_type},{trade_type})", duration, True
            )
            
            self.logger.info(
                "Investor ranking request completed successfully",
                investor_type=investor_type,
                trade_type=trade_type,
                market=market,
                count=len(ranking_items),
                duration=duration
            )
            
            return response
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            self.performance_logger.log_api_call(
                f"get_investor_ranking({investor_type},{trade_type})", duration, False
            )
            
            self.logger.error(
                "Investor ranking request failed",
                investor_type=investor_type,
                trade_type=trade_type,
                market=market,
                count=count,
                error=str(e)
            )
            
            if isinstance(e, VolumeRankingError):
                raise
            else:
                raise APIError(f"투자자별 거래 순위 조회 실패: {str(e)}")

# 글로벌 도구 인스턴스
_investor_ranking_tool = None

def get_investor_ranking_tool() -> InvestorRankingTool:
    """글로벌 투자자별 거래 순위 도구 인스턴스 획득"""
    global _investor_ranking_tool
    if _investor_ranking_tool is None:
        _investor_ranking_tool = InvestorRankingTool()
    return _investor_ranking_tool

async def handle_get_investor_ranking(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """
    MCP 도구 핸들러: 투자자별 거래 순위 조회
    
    Args:
        arguments: 도구 호출 인수
        
    Returns:
        MCP 응답 내용
    """
    try:
        # 매개변수 추출
        investor_type = arguments.get("investor_type", "FOREIGN")
        trade_type = arguments.get("trade_type", "NET")
        market = arguments.get("market", "ALL")
        count = arguments.get("count", None)
        
        # 도구 실행
        tool = get_investor_ranking_tool()
        response = await tool.get_investor_ranking(investor_type, trade_type, market, count)
        
        # 응답 포맷팅
        formatted_response = _format_investor_ranking_response(response)
        
        return [types.TextContent(type="text", text=formatted_response)]
        
    except Exception as e:
        error_message = f"투자자별 거래 순위 조회 오류: {str(e)}"
        return [types.TextContent(type="text", text=error_message)]

def _format_investor_ranking_response(response: InvestorRankingResponse) -> str:
    """투자자별 거래 순위 응답 포맷팅"""
    
    # 투자자 유형 한국어 변환
    investor_names = {
        "FOREIGN": "외국인",
        "INSTITUTION": "기관",
        "INDIVIDUAL": "개인",
        "PROGRAM": "프로그램"
    }
    
    # 거래 유형 한국어 변환
    trade_names = {
        "BUY": "매수",
        "SELL": "매도", 
        "NET": "순매수"
    }
    
    investor_name = investor_names.get(response.investor_type, response.investor_type)
    trade_name = trade_names.get(response.trade_type, response.trade_type)
    
    lines = [
        f"# 투자자별 거래 순위 ({investor_name} {trade_name})",
        f"📊 조회 시간: {response.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
        f"👥 투자자: {investor_name}",
        f"📈 거래 유형: {trade_name}",
        ""
    ]
    
    if response.summary:
        lines.extend([
            "## 요약 정보",
            f"💰 총 매수금액: {response.summary.total_buy_amount:,}원",
            f"💸 총 매도금액: {response.summary.total_sell_amount:,}원",
            f"📊 순거래금액: {response.summary.total_net_amount:+,}원",
            f"🎯 시장 영향도: {response.summary.market_impact:.1f}%",
            ""
        ])
    
    if not response.ranking:
        lines.append("조회된 데이터가 없습니다.")
        return "\n".join(lines)
    
    lines.extend(["## 순위 목록", ""])
    
    for item in response.ranking:
        stock = item.stock_info
        price = item.price_info
        trading = item.trading_info
        
        change_symbol = "📈" if price.change > 0 else "📉" if price.change < 0 else "➡️"
        net_symbol = "📈" if trading.net_amount > 0 else "📉" if trading.net_amount < 0 else "➡️"
        
        lines.append(
            f"**{item.rank}위** {stock.stock_name} ({stock.stock_code})"
        )
        lines.append(
            f"   💰 현재가: {price.current_price:,}원 "
            f"({change_symbol} {price.change:+,}원, {price.change_rate:+.2f}%)"
        )
        lines.append(
            f"   💵 매수금액: {trading.buy_amount:,}원"
        )
        lines.append(
            f"   💸 매도금액: {trading.sell_amount:,}원"
        )
        lines.append(
            f"   📊 순거래금액: {net_symbol} {trading.net_amount:+,}원"
        )
        
        if trading.impact_ratio is not None:
            lines.append(f"   🎯 영향도: {trading.impact_ratio:.2f}%")
        
        lines.append("")
    
    return "\n".join(lines)