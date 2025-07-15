"""
Basic tests for MCP Volume Ranking Server
"""

import pytest
import asyncio
from src.config import get_settings
from src.server import handle_health_check, handle_list_tools, handle_get_volume_ranking
from src.utils.logger import setup_logger

class TestBasicFunctionality:
    """기본 기능 테스트"""
    
    def test_config_loading(self):
        """설정 로딩 테스트"""
        settings = get_settings()
        assert settings.environment == "development"
        assert settings.default_ranking_count == 20
        assert settings.max_ranking_count == 50
    
    def test_logger_setup(self):
        """로거 설정 테스트"""
        logger = setup_logger("test")
        assert logger is not None
        logger.info("Test log message")
    
    @pytest.mark.asyncio
    async def test_list_tools(self):
        """도구 목록 조회 테스트"""
        tools = await handle_list_tools()
        assert len(tools) >= 2
        
        tool_names = [tool.name for tool in tools]
        assert "health_check" in tool_names
        assert "get_volume_ranking" in tool_names
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """헬스체크 테스트"""
        result = await handle_health_check()
        assert len(result) == 1
        assert "healthy" in result[0].text
        assert "MCP Volume Ranking Server" in result[0].text
    
    @pytest.mark.asyncio
    async def test_volume_ranking_mock(self):
        """거래대금 순위 조회 테스트 (모의 데이터)"""
        # 기본 매개변수
        result = await handle_get_volume_ranking({})
        assert len(result) == 1
        assert "Mock" in result[0].text
        
        # 사용자 정의 매개변수
        result = await handle_get_volume_ranking({
            "market": "KOSPI",
            "count": 10,
            "include_details": True
        })
        assert len(result) == 1
        assert "KOSPI" in result[0].text or "Mock" in result[0].text

if __name__ == "__main__":
    # 간단한 테스트 실행
    pytest.main([__file__, "-v"])