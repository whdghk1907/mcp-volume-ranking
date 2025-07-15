"""
Volume ranking tools for MCP server
거래대금 순위 조회 MCP 도구
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import mcp.types as types

from src.api.client import VolumeRankingAPI
from src.api.constants import get_market_code, get_market_name, VOLUME_RANKING_FIELD_MAPPING
from src.api.models import (
    StockInfo, PriceInfo, VolumeInfo, StockRankingItem, 
    VolumeRankingResponse, RankingSummary
)
from src.exceptions import (
    VolumeRankingError, APIError, DataValidationError, 
    InvalidParameterError, MarketClosedError
)
from src.config import get_settings
from src.utils.logger import setup_logger, get_performance_logger
from src.cache.hierarchical_cache import get_hierarchical_cache
from src.cache.key_generator import get_key_generator
from src.monitoring.metrics import get_performance_metrics

class VolumeRankingTool:
    """거래대금 순위 조회 도구"""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = setup_logger("volume_ranking_tool")
        self.performance_logger = get_performance_logger()
        self.api_client = None
        self.key_generator = get_key_generator()
        self.cache = get_hierarchical_cache()
        self.metrics = get_performance_metrics()
    
    async def _get_api_client(self) -> VolumeRankingAPI:
        """API 클라이언트 획득 (지연 초기화)"""
        if self.api_client is None:
            try:
                self.api_client = VolumeRankingAPI()
                self.logger.info("API client initialized successfully")
            except Exception as e:
                self.logger.error("Failed to initialize API client", error=str(e))
                raise APIError(f"API 클라이언트 초기화 실패: {str(e)}")
        
        return self.api_client
    
    def _validate_parameters(self, market: str, count: int) -> tuple[str, int]:
        """매개변수 유효성 검증"""
        # 시장 코드 검증
        if market not in ["ALL", "KOSPI", "KOSDAQ"]:
            raise InvalidParameterError(f"Invalid market: {market}. Must be one of: ALL, KOSPI, KOSDAQ")
        
        # 조회 개수 검증
        if count < 1:
            raise InvalidParameterError(f"Count must be greater than 0, got: {count}")
        
        if count > self.settings.max_ranking_count:
            self.logger.warning(
                f"Count {count} exceeds maximum {self.settings.max_ranking_count}, using maximum"
            )
            count = self.settings.max_ranking_count
        
        return market, count
    
    def _parse_stock_ranking_item(self, raw_data: Dict[str, Any], rank: int) -> StockRankingItem:
        """API 응답 데이터를 StockRankingItem으로 파싱"""
        try:
            # 기본 주식 정보
            stock_info = StockInfo(
                stock_code=raw_data.get("mksc_shrn_iscd", "").strip(),
                stock_name=raw_data.get("hts_kor_isnm", "").strip(),
                market_type="KOSPI" if rank <= 200 else "KOSDAQ"  # 임시 로직
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
            
            # 거래량 정보
            volume = int(raw_data.get("acml_vol", "0") or "0")
            trading_value = int(raw_data.get("acml_tr_pbmn", "0") or "0")
            turnover_rate = float(raw_data.get("vol_tnrt", "0.0") or "0.0") if raw_data.get("vol_tnrt") else None
            
            volume_info = VolumeInfo(
                volume=volume,
                trading_value=trading_value,
                turnover_rate=turnover_rate
            )
            
            return StockRankingItem(
                rank=rank,
                stock_info=stock_info,
                price_info=price_info,
                volume_info=volume_info
            )
            
        except Exception as e:
            self.logger.error("Failed to parse stock ranking item", rank=rank, error=str(e))
            raise DataValidationError(f"데이터 파싱 실패 (순위 {rank}): {str(e)}")
    
    def _calculate_summary(self, ranking_items: List[StockRankingItem], market: str) -> RankingSummary:
        """요약 정보 계산"""
        if not ranking_items:
            return RankingSummary(total_trading_value=0)
        
        total_trading_value = sum(item.volume_info.trading_value for item in ranking_items)
        
        # 상위 5종목 집중도 계산
        top5_value = sum(
            item.volume_info.trading_value 
            for item in ranking_items[:5]
        )
        top5_concentration = (top5_value / total_trading_value * 100) if total_trading_value > 0 else 0
        
        # 상위 10종목 집중도 계산
        top10_value = sum(
            item.volume_info.trading_value 
            for item in ranking_items[:10]
        )
        top10_concentration = (top10_value / total_trading_value * 100) if total_trading_value > 0 else 0
        
        return RankingSummary(
            total_trading_value=total_trading_value,
            top5_concentration=round(top5_concentration, 2),
            top10_concentration=round(top10_concentration, 2)
        )
    
    async def get_volume_ranking(
        self, 
        market: str = "ALL", 
        count: int = None, 
        include_details: bool = True
    ) -> VolumeRankingResponse:
        """
        거래대금 상위 종목 조회
        
        Args:
            market: 시장 구분 (ALL, KOSPI, KOSDAQ)
            count: 조회할 종목 수
            include_details: 상세 정보 포함 여부
        
        Returns:
            거래대금 순위 응답
        """
        start_time = datetime.now()
        
        # 기본값 설정
        if count is None:
            count = self.settings.default_ranking_count
        
        # 매개변수 검증
        market, count = self._validate_parameters(market, count)
        
        # 캐시 키 생성
        cache_key = self.key_generator.generate_volume_ranking_key(market, count)
        
        # 캐시에서 조회
        cached_result = await self.cache.get(cache_key)
        if cached_result is not None:
            self.logger.debug(f"Cache hit for volume ranking: {cache_key}")
            # 캐시 히트 메트릭 기록
            await self.metrics.record_custom_metric("cache_hits", 1)
            return cached_result
        
        # 캐시 미스 메트릭 기록
        await self.metrics.record_custom_metric("cache_misses", 1)
        
        # 요청 메트릭 기록
        await self.metrics.record_request("get_volume_ranking")
        
        self.logger.info(
            "Starting volume ranking request", 
            market=market, 
            count=count,
            include_details=include_details
        )
        
        try:
            # API 클라이언트 획득
            api_client = await self._get_api_client()
            
            # 시장 코드 변환
            market_code = get_market_code(market)
            
            # API 호출
            api_response = await api_client.get_volume_rank(
                market_code=market_code,
                rank_sort_cls="0"  # 거래대금순
            )
            
            # 응답 검증
            if not api_response.get("output"):
                raise DataValidationError("API 응답에 데이터가 없습니다")
            
            # 데이터 파싱
            ranking_items = []
            raw_items = api_response["output"][:count]  # 요청한 개수만큼 자르기
            
            for i, raw_item in enumerate(raw_items, 1):
                try:
                    ranking_item = self._parse_stock_ranking_item(raw_item, i)
                    ranking_items.append(ranking_item)
                except Exception as e:
                    self.logger.warning(f"Failed to parse item {i}", error=str(e))
                    continue
            
            if not ranking_items:
                raise DataValidationError("파싱 가능한 데이터가 없습니다")
            
            # 요약 정보 계산
            summary = self._calculate_summary(ranking_items, market)
            
            # 응답 생성
            response = VolumeRankingResponse(
                timestamp=start_time,
                market=market,
                ranking=ranking_items,
                summary=summary
            )
            
            # 캐시에 저장
            try:
                ttl = self.key_generator.calculate_ttl("volume_ranking")
                await self.cache.set(cache_key, response, ttl)
                self.logger.debug(f"Cached volume ranking result: {cache_key} (TTL: {ttl}s)")
            except Exception as e:
                self.logger.warning(f"Failed to cache volume ranking result: {cache_key}, error: {str(e)}")
            
            # 성능 로깅
            duration = (datetime.now() - start_time).total_seconds()
            self.performance_logger.log_api_call(
                f"get_volume_ranking({market})", duration, True
            )
            
            # 모니터링 메트릭 기록
            await self.metrics.record_response_time("get_volume_ranking", duration)
            await self.metrics.record_success("get_volume_ranking")
            
            self.logger.info(
                "Volume ranking request completed successfully",
                market=market,
                count=len(ranking_items),
                duration=duration
            )
            
            return response
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            self.performance_logger.log_api_call(
                f"get_volume_ranking({market})", duration, False
            )
            
            # 오류 메트릭 기록
            await self.metrics.record_response_time("get_volume_ranking", duration)
            await self.metrics.record_error("get_volume_ranking", type(e).__name__)
            
            self.logger.error(
                "Volume ranking request failed",
                market=market,
                count=count,
                error=str(e)
            )
            
            if isinstance(e, VolumeRankingError):
                raise
            else:
                raise APIError(f"거래대금 순위 조회 실패: {str(e)}")

# 글로벌 도구 인스턴스
_volume_ranking_tool = None

def get_volume_ranking_tool() -> VolumeRankingTool:
    """글로벌 거래대금 순위 도구 인스턴스 획득"""
    global _volume_ranking_tool
    if _volume_ranking_tool is None:
        _volume_ranking_tool = VolumeRankingTool()
    return _volume_ranking_tool

async def handle_get_volume_ranking(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """
    MCP 도구 핸들러: 거래대금 순위 조회
    
    Args:
        arguments: 도구 호출 인수
        
    Returns:
        MCP 응답 내용
    """
    try:
        # 매개변수 추출
        market = arguments.get("market", "ALL")
        count = arguments.get("count", None)
        include_details = arguments.get("include_details", True)
        
        # 도구 실행
        tool = get_volume_ranking_tool()
        response = await tool.get_volume_ranking(market, count, include_details)
        
        # 응답 포맷팅
        if include_details:
            # 상세 정보 포함
            formatted_response = _format_detailed_response(response)
        else:
            # 간단한 정보만
            formatted_response = _format_simple_response(response)
        
        return [types.TextContent(type="text", text=formatted_response)]
        
    except Exception as e:
        error_message = f"거래대금 순위 조회 오류: {str(e)}"
        return [types.TextContent(type="text", text=error_message)]

def _format_detailed_response(response: VolumeRankingResponse) -> str:
    """상세 응답 포맷팅"""
    lines = [
        f"# 거래대금 순위 ({response.market})",
        f"📊 조회 시간: {response.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
        f"🏪 시장: {get_market_name(get_market_code(response.market))}",
        f"📈 총 거래대금: {response.summary.total_trading_value:,}원",
        ""
    ]
    
    if response.summary.top5_concentration:
        lines.append(f"🎯 상위 5종목 집중도: {response.summary.top5_concentration}%")
    
    if response.summary.top10_concentration:
        lines.append(f"🎯 상위 10종목 집중도: {response.summary.top10_concentration}%")
    
    lines.extend(["", "## 순위 목록", ""])
    
    for item in response.ranking:
        stock = item.stock_info
        price = item.price_info
        volume = item.volume_info
        
        change_symbol = "📈" if price.change > 0 else "📉" if price.change < 0 else "➡️"
        
        lines.append(
            f"**{item.rank}위** {stock.stock_name} ({stock.stock_code})"
        )
        lines.append(
            f"   💰 현재가: {price.current_price:,}원 "
            f"({change_symbol} {price.change:+,}원, {price.change_rate:+.2f}%)"
        )
        lines.append(
            f"   📊 거래대금: {volume.trading_value:,}원"
        )
        lines.append(
            f"   📈 거래량: {volume.volume:,}주"
        )
        
        if volume.turnover_rate:
            lines.append(f"   🔄 회전율: {volume.turnover_rate:.2f}%")
        
        lines.append("")
    
    return "\n".join(lines)

def _format_simple_response(response: VolumeRankingResponse) -> str:
    """간단한 응답 포맷팅"""
    lines = [
        f"거래대금 순위 TOP {len(response.ranking)} ({response.market})",
        f"조회시간: {response.timestamp.strftime('%H:%M:%S')}",
        ""
    ]
    
    for item in response.ranking:
        stock = item.stock_info
        volume = item.volume_info
        
        lines.append(
            f"{item.rank:2d}. {stock.stock_name:<12} "
            f"{volume.trading_value:>12,}원"
        )
    
    return "\n".join(lines)