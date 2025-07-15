"""
Sector Volume Ranking Tools
업종별 거래대금 순위 도구
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import mcp.types as types

from src.api.client import VolumeRankingAPI
from src.api.constants import get_market_code, get_sector_name
from src.api.models import (
    SectorVolumeRankingResponse, SectorRankingItem, SectorInfo, LeadingStock
)
from src.exceptions import VolumeRankingError, APIError, DataValidationError, InvalidParameterError
from src.config import get_settings
from src.utils.logger import setup_logger, get_performance_logger
from src.utils.validator import validate_market, validate_count

class SectorVolumeRankingTool:
    """업종별 거래대금 순위 조회 도구"""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = setup_logger("sector_volume_ranking_tool")
        self.performance_logger = get_performance_logger()
        self.api_client = None
    
    async def _get_api_client(self) -> VolumeRankingAPI:
        """API 클라이언트 획득"""
        if self.api_client is None:
            self.api_client = VolumeRankingAPI()
        return self.api_client
    
    async def get_sector_volume_ranking(
        self,
        market: str = "KOSPI",
        count: int = None
    ) -> SectorVolumeRankingResponse:
        """업종별 거래대금 순위 조회"""
        
        start_time = datetime.now()
        
        if count is None:
            count = self.settings.default_ranking_count
        
        # 매개변수 검증
        market = validate_market(market)
        count = validate_count(count, min_value=1, max_value=30)  # 업종은 최대 30개
        
        self.logger.info("Starting sector volume ranking request", market=market, count=count)
        
        try:
            # 임시 구현: 실제로는 업종별 API 호출
            api_client = await self._get_api_client()
            market_code = get_market_code(market)
            
            # 기본 거래대금 데이터를 가져와서 업종별로 그룹화
            response = await api_client.get_volume_rank(market_code, "0")
            
            if response.get("rt_cd") != "0":
                raise APIError(f"데이터 조회 실패: {response.get('msg1', '알 수 없는 오류')}")
            
            # 임시 업종 데이터 생성
            ranking_items = self._create_mock_sector_ranking(count)
            
            result = SectorVolumeRankingResponse(
                timestamp=start_time,
                market=market,
                ranking=ranking_items
            )
            
            duration = (datetime.now() - start_time).total_seconds()
            self.performance_logger.log_api_call(f"get_sector_volume_ranking({market})", duration, True)
            
            return result
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            self.performance_logger.log_api_call(f"get_sector_volume_ranking({market})", duration, False)
            
            if isinstance(e, VolumeRankingError):
                raise
            else:
                raise APIError(f"업종별 거래대금 순위 조회 실패: {str(e)}")
    
    def _create_mock_sector_ranking(self, count: int) -> List[SectorRankingItem]:
        """임시 업종 순위 데이터 생성"""
        mock_sectors = [
            ("G2510", "반도체", 5),
            ("G3030", "자동차", 3),
            ("G4020", "은행", 4),
            ("G2530", "컴퓨터", 2),
            ("G5020", "제약", 3)
        ]
        
        ranking_items = []
        
        for i, (sector_code, sector_name, stock_count) in enumerate(mock_sectors[:count], 1):
            sector_info = SectorInfo(
                sector_code=sector_code,
                sector_name=sector_name,
                stock_count=stock_count
            )
            
            # 대표 종목 생성
            leading_stocks = [
                LeadingStock(
                    stock_code="005930",
                    stock_name="삼성전자",
                    contribution=45.6
                )
            ]
            
            ranking_item = SectorRankingItem(
                rank=i,
                sector_info=sector_info,
                trading_value=1000000000000 - (i * 100000000000),
                trading_volume=50000000 - (i * 5000000),
                average_change_rate=2.5 - (i * 0.3),
                leading_stocks=leading_stocks,
                foreign_net_buy=100000000000 - (i * 10000000000),
                institution_net_buy=-50000000000 + (i * 5000000000)
            )
            
            ranking_items.append(ranking_item)
        
        return ranking_items

# 글로벌 인스턴스
_sector_volume_ranking_tool = None

def get_sector_volume_ranking_tool() -> SectorVolumeRankingTool:
    global _sector_volume_ranking_tool
    if _sector_volume_ranking_tool is None:
        _sector_volume_ranking_tool = SectorVolumeRankingTool()
    return _sector_volume_ranking_tool

async def handle_get_sector_volume_ranking(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """MCP 핸들러: 업종별 거래대금 순위 조회"""
    try:
        market = arguments.get("market", "KOSPI")
        count = arguments.get("count", None)
        
        tool = get_sector_volume_ranking_tool()
        response = await tool.get_sector_volume_ranking(market, count)
        
        formatted_response = _format_sector_volume_response(response)
        return [types.TextContent(type="text", text=formatted_response)]
        
    except Exception as e:
        error_message = f"업종별 거래대금 순위 조회 오류: {str(e)}"
        return [types.TextContent(type="text", text=error_message)]

def _format_sector_volume_response(response: SectorVolumeRankingResponse) -> str:
    """업종별 거래대금 순위 응답 포맷팅"""
    lines = [
        f"# 업종별 거래대금 순위 ({response.market})",
        f"📊 조회 시간: {response.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
        f"🏪 시장: {response.market}",
        "",
        "## 순위 목록",
        ""
    ]
    
    for item in response.ranking:
        sector = item.sector_info
        
        lines.append(f"**{item.rank}위** {sector.sector_name} ({sector.sector_code})")
        lines.append(f"   📊 거래대금: {item.trading_value:,}원")
        lines.append(f"   📈 거래량: {item.trading_volume:,}주")
        lines.append(f"   📉 평균등락률: {item.average_change_rate:+.2f}%")
        lines.append(f"   🏢 종목수: {sector.stock_count}개")
        
        if item.leading_stocks:
            leading = item.leading_stocks[0]
            lines.append(f"   ⭐ 대표종목: {leading.stock_name} (기여도 {leading.contribution:.1f}%)")
        
        lines.append("")
    
    return "\n".join(lines)