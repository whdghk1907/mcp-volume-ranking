"""
TDD Tests for Investor Ranking Tool
투자자별 거래 순위 도구 TDD 테스트
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from datetime import datetime
from typing import Dict, Any

from src.exceptions import InvalidParameterError, DataValidationError
from src.api.models import InvestorRankingResponse

# 이 테스트들은 현재 실패할 것입니다 (RED phase)

class TestInvestorRankingTool:
    """투자자별 거래 순위 도구 TDD 테스트"""
    
    @pytest.mark.asyncio
    async def test_get_investor_ranking_basic_functionality(self):
        """기본 기능 테스트 - 아직 구현되지 않음 (RED)"""
        from src.tools.investor_tools import InvestorRankingTool
        
        tool = InvestorRankingTool()
        
        # 외국인 순매수 순위 조회
        result = await tool.get_investor_ranking(
            investor_type="FOREIGN",
            trade_type="NET",
            market="ALL",
            count=10
        )
        
        # 응답 구조 검증
        assert isinstance(result, InvestorRankingResponse)
        assert result.investor_type == "FOREIGN"
        assert result.trade_type == "NET"
        assert len(result.ranking) <= 10
        assert result.timestamp is not None
        assert result.summary is not None
    
    @pytest.mark.asyncio
    async def test_investor_ranking_parameter_validation(self):
        """매개변수 검증 테스트 - 아직 구현되지 않음 (RED)"""
        from src.tools.investor_tools import InvestorRankingTool
        
        tool = InvestorRankingTool()
        
        # 유효하지 않은 투자자 유형
        with pytest.raises(InvalidParameterError):
            await tool.get_investor_ranking(
                investor_type="INVALID",
                trade_type="NET",
                market="ALL",
                count=10
            )
        
        # 유효하지 않은 거래 유형
        with pytest.raises(InvalidParameterError):
            await tool.get_investor_ranking(
                investor_type="FOREIGN",
                trade_type="INVALID",
                market="ALL",
                count=10
            )
        
        # 유효하지 않은 시장
        with pytest.raises(InvalidParameterError):
            await tool.get_investor_ranking(
                investor_type="FOREIGN",
                trade_type="NET",
                market="INVALID",
                count=10
            )
    
    @pytest.mark.asyncio
    async def test_investor_types_support(self):
        """모든 투자자 유형 지원 테스트 - 아직 구현되지 않음 (RED)"""
        from src.tools.investor_tools import InvestorRankingTool
        
        tool = InvestorRankingTool()
        
        investor_types = ["FOREIGN", "INSTITUTION", "INDIVIDUAL", "PROGRAM"]
        
        for investor_type in investor_types:
            result = await tool.get_investor_ranking(
                investor_type=investor_type,
                trade_type="NET",
                market="ALL",
                count=5
            )
            
            assert result.investor_type == investor_type
            assert len(result.ranking) <= 5
    
    @pytest.mark.asyncio
    async def test_trade_types_support(self):
        """모든 거래 유형 지원 테스트 - 아직 구현되지 않음 (RED)"""
        from src.tools.investor_tools import InvestorRankingTool
        
        tool = InvestorRankingTool()
        
        trade_types = ["BUY", "SELL", "NET"]
        
        for trade_type in trade_types:
            result = await tool.get_investor_ranking(
                investor_type="FOREIGN",
                trade_type=trade_type,
                market="ALL",
                count=5
            )
            
            assert result.trade_type == trade_type
            assert len(result.ranking) <= 5
    
    @pytest.mark.asyncio
    async def test_net_amount_calculation_accuracy(self):
        """순매수 금액 계산 정확성 테스트 - 아직 구현되지 않음 (RED)"""
        from src.tools.investor_tools import InvestorRankingTool
        
        tool = InvestorRankingTool()
        
        # Mock API 응답
        mock_response = {
            "rt_cd": "0",
            "msg1": "성공",
            "output": [
                {
                    "hts_kor_isnm": "테스트종목",
                    "mksc_shrn_iscd": "123456",
                    "stck_prpr": "10000",
                    "frgn_ntby_qty": "1000",  # 외국인 순매수 수량
                    "frgn_ntby_tr_pbmn": "10000000",  # 외국인 순매수 거래대금
                }
            ]
        }
        
        with patch.object(tool, '_get_api_client') as mock_api:
            mock_client = AsyncMock()
            mock_api.return_value = mock_client
            mock_client.get_investor_trend_rank.return_value = mock_response
            
            result = await tool.get_investor_ranking("FOREIGN", "NET", "ALL", 5)
            
            # 순매수 금액 계산 검증
            assert len(result.ranking) > 0
            ranking_item = result.ranking[0]
            
            # 순매수 = 매수 - 매도
            expected_net = ranking_item.trading_info.buy_amount - ranking_item.trading_info.sell_amount
            assert ranking_item.trading_info.net_amount == expected_net
    
    @pytest.mark.asyncio
    async def test_impact_ratio_calculation(self):
        """영향도 계산 테스트 - 아직 구현되지 않음 (RED)"""
        from src.tools.investor_tools import InvestorRankingTool
        
        tool = InvestorRankingTool()
        
        result = await tool.get_investor_ranking("FOREIGN", "NET", "ALL", 10)
        
        # 영향도 계산 검증
        for item in result.ranking:
            if item.trading_info.impact_ratio is not None:
                # 영향도는 0-100% 범위여야 함
                assert 0 <= item.trading_info.impact_ratio <= 100
        
        # 요약 정보의 시장 영향도 검증
        if result.summary.market_impact is not None:
            assert 0 <= result.summary.market_impact <= 100

class TestInvestorRankingMCPHandler:
    """투자자별 거래 순위 MCP 핸들러 테스트"""
    
    @pytest.mark.asyncio
    async def test_handle_get_investor_ranking_success(self):
        """MCP 핸들러 성공 케이스 - 아직 구현되지 않음 (RED)"""
        from src.tools.investor_tools import handle_get_investor_ranking
        
        arguments = {
            "investor_type": "INSTITUTION",
            "trade_type": "BUY",
            "market": "KOSPI",
            "count": 15
        }
        
        result = await handle_get_investor_ranking(arguments)
        
        # MCP 응답 구조 검증
        assert len(result) == 1
        assert result[0].type == "text"
        assert "투자자별 거래 순위" in result[0].text
        assert "INSTITUTION" in result[0].text or "기관" in result[0].text
        assert "BUY" in result[0].text or "매수" in result[0].text
    
    @pytest.mark.asyncio
    async def test_handle_get_investor_ranking_error(self):
        """MCP 핸들러 에러 케이스 - 아직 구현되지 않음 (RED)"""
        from src.tools.investor_tools import handle_get_investor_ranking
        
        # 잘못된 매개변수
        arguments = {
            "investor_type": "INVALID_TYPE",
            "trade_type": "NET",
            "market": "ALL",
            "count": 10
        }
        
        result = await handle_get_investor_ranking(arguments)
        
        # 에러 메시지 검증
        assert len(result) == 1
        assert result[0].type == "text"
        assert "오류" in result[0].text

class TestInvestorDataCalculations:
    """투자자 데이터 계산 로직 테스트"""
    
    def test_calculate_net_trading_amount(self):
        """순거래 금액 계산 테스트 - 아직 구현되지 않음 (RED)"""
        from src.utils.investor_calculator import calculate_net_trading_amount
        
        buy_amount = 5000000000
        sell_amount = 3000000000
        
        net_amount = calculate_net_trading_amount(buy_amount, sell_amount)
        
        assert net_amount == 2000000000
    
    def test_calculate_average_trading_price(self):
        """평균 거래가 계산 테스트 - 아직 구현되지 않음 (RED)"""
        from src.utils.investor_calculator import calculate_average_trading_price
        
        total_amount = 10000000000
        total_volume = 1000000
        
        avg_price = calculate_average_trading_price(total_amount, total_volume)
        
        assert avg_price == 10000
    
    def test_calculate_market_impact_ratio(self):
        """시장 영향도 계산 테스트 - 아직 구현되지 않음 (RED)"""
        from src.utils.investor_calculator import calculate_market_impact_ratio
        
        investor_amount = 1000000000
        total_market_amount = 10000000000
        
        impact_ratio = calculate_market_impact_ratio(investor_amount, total_market_amount)
        
        assert impact_ratio == 10.0  # 10%

class TestInvestorScreenCodeMapping:
    """투자자 화면 코드 매핑 테스트"""
    
    def test_get_investor_screen_code(self):
        """투자자 화면 코드 획득 테스트 - 아직 구현되지 않음 (RED)"""
        from src.api.constants import get_investor_screen_code
        
        # 외국인 순매수
        code = get_investor_screen_code("FOREIGN", "NET")
        assert code == "20174"
        
        # 기관 매수
        code = get_investor_screen_code("INSTITUTION", "BUY")
        assert code == "20175"
        
        # 개인 매도
        code = get_investor_screen_code("INDIVIDUAL", "SELL")
        assert code == "20179"
        
        # 프로그램 순매수
        code = get_investor_screen_code("PROGRAM", "NET")
        assert code == "20183"
    
    def test_invalid_investor_screen_code(self):
        """잘못된 투자자 코드 처리 테스트 - 아직 구현되지 않음 (RED)"""
        from src.api.constants import get_investor_screen_code
        
        # 잘못된 조합은 기본값 반환
        code = get_investor_screen_code("INVALID", "INVALID")
        assert code == "20174"  # 기본값

class TestInvestorRankingResponseFormatting:
    """투자자별 거래 순위 응답 포맷팅 테스트"""
    
    def test_format_investor_ranking_response_detailed(self):
        """상세 응답 포맷팅 테스트 - 아직 구현되지 않음 (RED)"""
        from src.utils.investor_formatter import format_investor_ranking_response
        
        # Mock 응답 데이터 (실제 모델은 아직 구현되지 않음)
        mock_response = InvestorRankingResponse(
            timestamp=datetime.now(),
            investor_type="FOREIGN",
            trade_type="NET",
            ranking=[],
            summary=None
        )
        
        # 상세 포맷
        detailed = format_investor_ranking_response(mock_response, detailed=True)
        assert "투자자별 거래 순위" in detailed
        assert "외국인" in detailed or "FOREIGN" in detailed
        assert "순매수" in detailed or "NET" in detailed
    
    def test_format_investor_ranking_response_simple(self):
        """간단 응답 포맷팅 테스트 - 아직 구현되지 않음 (RED)"""
        from src.utils.investor_formatter import format_investor_ranking_response
        
        mock_response = InvestorRankingResponse(
            timestamp=datetime.now(),
            investor_type="INSTITUTION",
            trade_type="BUY",
            ranking=[],
            summary=None
        )
        
        # 간단 포맷
        simple = format_investor_ranking_response(mock_response, detailed=False)
        assert len(simple) > 0

# 성능 테스트
class TestInvestorRankingPerformance:
    """투자자별 거래 순위 도구 성능 테스트"""
    
    @pytest.mark.asyncio
    async def test_response_time_under_threshold(self):
        """응답 시간 테스트 - 아직 구현되지 않음 (RED)"""
        from src.tools.investor_tools import InvestorRankingTool
        
        tool = InvestorRankingTool()
        
        start_time = datetime.now()
        
        with patch.object(tool, '_get_api_client') as mock_api:
            mock_client = AsyncMock()
            mock_api.return_value = mock_client
            mock_client.get_investor_trend_rank.return_value = {"rt_cd": "0", "output": []}
            
            await tool.get_investor_ranking("FOREIGN", "NET", "ALL", 20)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # 2초 이내 응답
        assert duration < 2.0

# 에지 케이스 테스트
class TestInvestorRankingEdgeCases:
    """투자자별 거래 순위 도구 에지 케이스 테스트"""
    
    @pytest.mark.asyncio
    async def test_zero_trading_amounts(self):
        """거래금액이 0인 경우 - 아직 구현되지 않음 (RED)"""
        from src.tools.investor_tools import InvestorRankingTool
        
        tool = InvestorRankingTool()
        
        mock_response = {
            "rt_cd": "0",
            "output": [
                {
                    "hts_kor_isnm": "거래없음종목",
                    "mksc_shrn_iscd": "123456",
                    "stck_prpr": "10000",
                    "frgn_ntby_qty": "0",
                    "frgn_ntby_tr_pbmn": "0",
                }
            ]
        }
        
        with patch.object(tool, '_get_api_client') as mock_api:
            mock_client = AsyncMock()
            mock_api.return_value = mock_client
            mock_client.get_investor_trend_rank.return_value = mock_response
            
            result = await tool.get_investor_ranking("FOREIGN", "NET", "ALL", 5)
            
            # 거래금액이 0인 종목도 포함되어야 함
            assert len(result.ranking) > 0
            assert result.ranking[0].trading_info.net_amount == 0

if __name__ == "__main__":
    # 이 테스트들은 현재 모두 실패할 것입니다 (RED phase)
    pytest.main([__file__, "-v"])