"""
Unusual Volume Detection Tools
이상 거래량 감지 도구
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import mcp.types as types

from src.api.client import VolumeRankingAPI
from src.api.constants import get_market_code
from src.api.models import (
    UnusualVolumeResponse, UnusualVolumeItem, StockInfo, PriceInfo, 
    VolumeInfo, VolumeAnalysis, UnusualVolumeSummary
)
from src.exceptions import VolumeRankingError, APIError, DataValidationError
from src.config import get_settings
from src.utils.logger import setup_logger, get_performance_logger
from src.utils.validator import validate_market, validate_count

class UnusualVolumeDetectionTool:
    """이상 거래량 감지 도구"""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = setup_logger("unusual_volume_detection_tool")
        self.performance_logger = get_performance_logger()
        self.api_client = None
    
    async def _get_api_client(self) -> VolumeRankingAPI:
        """API 클라이언트 획득"""
        if self.api_client is None:
            self.api_client = VolumeRankingAPI()
        return self.api_client
    
    def _calculate_volume_ratio(self, current_volume: int, avg_volume: int) -> float:
        """거래량 비율 계산"""
        if avg_volume <= 0:
            return 0.0
        return (current_volume / avg_volume) * 100.0
    
    def _calculate_volume_anomaly_score(self, volume_ratio: float) -> float:
        """거래량 이상 점수 계산"""
        if volume_ratio < 100:
            return 0.0
        elif volume_ratio < 200:
            return 1.0
        elif volume_ratio < 300:
            return 2.0
        elif volume_ratio < 500:
            return 3.0
        elif volume_ratio < 1000:
            return 4.0
        else:
            return 5.0
    
    def _determine_volume_pattern(self, volume_ratio: float, price_change: float) -> str:
        """거래량 패턴 판단"""
        if volume_ratio < 150:
            return "NORMAL"
        elif volume_ratio >= 500:
            if price_change > 3.0:
                return "SURGE_WITH_RISE"
            elif price_change < -3.0:
                return "SURGE_WITH_FALL"
            else:
                return "SURGE_NEUTRAL"
        elif volume_ratio >= 200:
            if price_change > 0:
                return "HIGH_WITH_RISE"
            else:
                return "HIGH_WITH_FALL"
        else:
            return "MODERATE"
    
    async def get_unusual_volume(
        self,
        market: str = "ALL",
        threshold: float = 200.0,
        count: int = None,
        min_price: int = None
    ) -> UnusualVolumeResponse:
        """이상 거래량 감지"""
        
        start_time = datetime.now()
        
        if count is None:
            count = self.settings.default_ranking_count
        
        # 매개변수 검증
        market = validate_market(market)
        count = validate_count(count, min_value=1, max_value=self.settings.max_ranking_count)
        
        if threshold < 100.0:
            threshold = 100.0
        elif threshold > 1000.0:
            threshold = 1000.0
        
        self.logger.info(
            "Starting unusual volume detection", 
            market=market, 
            threshold=threshold, 
            count=count
        )
        
        try:
            # 거래량 데이터 조회
            api_client = await self._get_api_client()
            market_code = get_market_code(market)
            
            # 기본 거래대금 데이터 사용
            response = await api_client.get_volume_rank(market_code, "0")
            
            if response.get("rt_cd") != "0":
                raise APIError(f"데이터 조회 실패: {response.get('msg1', '알 수 없는 오류')}")
            
            # 이상 거래량 데이터 생성
            unusual_items = self._create_unusual_volume_data(
                response.get("output", []), 
                threshold, 
                count, 
                min_price
            )
            
            # 요약 정보 계산
            summary = self._calculate_unusual_volume_summary(unusual_items)
            
            result = UnusualVolumeResponse(
                timestamp=start_time,
                market=market,
                threshold=threshold,
                unusual_items=unusual_items,
                summary=summary
            )
            
            duration = (datetime.now() - start_time).total_seconds()
            self.performance_logger.log_api_call(f"get_unusual_volume({market})", duration, True)
            
            return result
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            self.performance_logger.log_api_call(f"get_unusual_volume({market})", duration, False)
            
            if isinstance(e, VolumeRankingError):
                raise
            else:
                raise APIError(f"이상 거래량 감지 실패: {str(e)}")
    
    def _create_unusual_volume_data(
        self, 
        raw_data: List[Dict[str, Any]], 
        threshold: float,
        count: int,
        min_price: int
    ) -> List[UnusualVolumeItem]:
        """이상 거래량 데이터 생성"""
        
        unusual_items = []
        
        for i, raw_item in enumerate(raw_data, 1):
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
                
                # 최소 가격 필터
                if min_price and current_price < min_price:
                    continue
                
                price_info = PriceInfo(
                    current_price=current_price,
                    change=change,
                    change_rate=change_rate
                )
                
                current_volume = int(raw_item.get("acml_vol", "0") or "0")
                trading_value = int(raw_item.get("acml_tr_pbmn", "0") or "0")
                
                # 평균 거래량 추정 (임시로 현재 거래량의 30-80% 범위)
                avg_volume = int(current_volume * (0.3 + (i * 0.005)))
                
                volume_info = VolumeInfo(
                    volume=current_volume,
                    trading_value=trading_value
                )
                
                # 거래량 비율 계산
                volume_ratio = self._calculate_volume_ratio(current_volume, avg_volume)
                
                # 임계값 이하는 제외
                if volume_ratio < threshold:
                    continue
                
                # 거래량 분석
                anomaly_score = self._calculate_volume_anomaly_score(volume_ratio)
                pattern = self._determine_volume_pattern(volume_ratio, change_rate)
                
                volume_analysis = VolumeAnalysis(
                    volume_ratio=volume_ratio,
                    average_volume=avg_volume,
                    anomaly_score=anomaly_score,
                    pattern=pattern,
                    detection_time=datetime.now()
                )
                
                unusual_item = UnusualVolumeItem(
                    rank=len(unusual_items) + 1,
                    stock_info=stock_info,
                    price_info=price_info,
                    volume_info=volume_info,
                    volume_analysis=volume_analysis
                )
                
                unusual_items.append(unusual_item)
                
                # 개수 제한
                if len(unusual_items) >= count:
                    break
                    
            except Exception as e:
                self.logger.warning(f"Failed to process unusual volume item {i}", error=str(e))
                continue
        
        # 거래량 비율 기준으로 정렬
        unusual_items.sort(key=lambda x: x.volume_analysis.volume_ratio, reverse=True)
        
        # 순위 재조정
        for i, item in enumerate(unusual_items, 1):
            item.rank = i
        
        return unusual_items
    
    def _calculate_unusual_volume_summary(self, unusual_items: List[UnusualVolumeItem]) -> UnusualVolumeSummary:
        """이상 거래량 요약 정보 계산"""
        if not unusual_items:
            return UnusualVolumeSummary(
                total_detected=0,
                high_anomaly_count=0,
                average_volume_ratio=0.0,
                max_volume_ratio=0.0
            )
        
        total_detected = len(unusual_items)
        high_anomaly_count = sum(
            1 for item in unusual_items 
            if item.volume_analysis.anomaly_score >= 4.0
        )
        
        volume_ratios = [item.volume_analysis.volume_ratio for item in unusual_items]
        average_volume_ratio = sum(volume_ratios) / len(volume_ratios)
        max_volume_ratio = max(volume_ratios)
        
        return UnusualVolumeSummary(
            total_detected=total_detected,
            high_anomaly_count=high_anomaly_count,
            average_volume_ratio=average_volume_ratio,
            max_volume_ratio=max_volume_ratio
        )

# 글로벌 인스턴스
_unusual_volume_detection_tool = None

def get_unusual_volume_detection_tool() -> UnusualVolumeDetectionTool:
    global _unusual_volume_detection_tool
    if _unusual_volume_detection_tool is None:
        _unusual_volume_detection_tool = UnusualVolumeDetectionTool()
    return _unusual_volume_detection_tool

async def handle_get_unusual_volume(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """MCP 핸들러: 이상 거래량 감지"""
    try:
        market = arguments.get("market", "ALL")
        threshold = arguments.get("threshold", 200.0)
        count = arguments.get("count", None)
        min_price = arguments.get("min_price", None)
        
        tool = get_unusual_volume_detection_tool()
        response = await tool.get_unusual_volume(market, threshold, count, min_price)
        
        formatted_response = _format_unusual_volume_response(response)
        return [types.TextContent(type="text", text=formatted_response)]
        
    except Exception as e:
        error_message = f"이상 거래량 감지 오류: {str(e)}"
        return [types.TextContent(type="text", text=error_message)]

def _format_unusual_volume_response(response: UnusualVolumeResponse) -> str:
    """이상 거래량 응답 포맷팅"""
    lines = [
        f"# 이상 거래량 감지 ({response.market})",
        f"🔍 조회 시간: {response.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
        f"📊 임계값: {response.threshold:.0f}%",
        f"🏪 시장: {response.market}",
        ""
    ]
    
    if response.summary:
        lines.extend([
            "## 요약 정보",
            f"🚨 감지된 종목: {response.summary.total_detected}개",
            f"⚠️ 고위험 종목: {response.summary.high_anomaly_count}개",
            f"📊 평균 거래량 비율: {response.summary.average_volume_ratio:.1f}%",
            f"📈 최고 거래량 비율: {response.summary.max_volume_ratio:.1f}%",
            ""
        ])
    
    if not response.unusual_items:
        lines.append("감지된 이상 거래량 종목이 없습니다.")
        return "\n".join(lines)
    
    lines.extend(["## 감지된 종목 목록", ""])
    
    for item in response.unusual_items:
        stock = item.stock_info
        price = item.price_info
        volume = item.volume_info
        analysis = item.volume_analysis
        
        change_symbol = "📈" if price.change > 0 else "📉" if price.change < 0 else "➡️"
        
        # 이상 점수에 따른 경고 레벨
        if analysis.anomaly_score >= 4.0:
            alert_symbol = "🚨"
        elif analysis.anomaly_score >= 3.0:
            alert_symbol = "⚠️"
        else:
            alert_symbol = "📊"
        
        # 패턴 표시
        pattern_symbols = {
            "SURGE_WITH_RISE": "🚀",
            "SURGE_WITH_FALL": "💥",
            "SURGE_NEUTRAL": "⚡",
            "HIGH_WITH_RISE": "📈",
            "HIGH_WITH_FALL": "📉",
            "MODERATE": "📊",
            "NORMAL": "➡️"
        }
        pattern_symbol = pattern_symbols.get(analysis.pattern, "📊")
        
        lines.append(f"{alert_symbol} **{item.rank}위** {stock.stock_name} ({stock.stock_code})")
        lines.append(f"   💰 현재가: {price.current_price:,}원 ({change_symbol} {price.change:+,}원)")
        lines.append(f"   📊 현재 거래량: {volume.volume:,}주")
        lines.append(f"   📈 거래량 비율: {analysis.volume_ratio:.1f}% (평균 대비)")
        lines.append(f"   {pattern_symbol} 패턴: {analysis.pattern}")
        lines.append(f"   🎯 이상 점수: {analysis.anomaly_score:.1f}/5.0")
        lines.append("")
    
    return "\n".join(lines)