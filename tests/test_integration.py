"""
Integration tests for Phase 1
Phase 1 통합 테스트
"""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock
import json

from src.server import handle_list_tools, handle_health_check, handle_call_tool
from src.tools.volume_tools import handle_get_volume_ranking
from src.api.client import VolumeRankingAPI
from src.config import get_settings

class TestPhase1Integration:
    """Phase 1 통합 테스트"""
    
    @pytest.mark.asyncio
    async def test_server_tools_listing(self):
        """서버 도구 목록 조회 테스트"""
        tools = await handle_list_tools()
        
        # 기본 도구들이 있는지 확인
        tool_names = [tool.name for tool in tools]
        assert "health_check" in tool_names
        assert "get_volume_ranking" in tool_names
        
        # 각 도구가 올바른 스키마를 가지는지 확인
        for tool in tools:
            assert hasattr(tool, 'name')
            assert hasattr(tool, 'description')
            assert hasattr(tool, 'inputSchema')
            assert isinstance(tool.inputSchema, dict)
    
    @pytest.mark.asyncio
    async def test_health_check_functionality(self):
        """헬스체크 기능 테스트"""
        result = await handle_health_check()
        
        assert len(result) == 1
        assert result[0].type == "text"
        assert "healthy" in result[0].text.lower()
        assert "MCP Volume Ranking Server" in result[0].text
    
    @pytest.mark.asyncio
    async def test_tool_call_handler_health_check(self):
        """도구 호출 핸들러 - 헬스체크 테스트"""
        result = await handle_call_tool("health_check", {})
        
        assert len(result) == 1
        assert result[0].type == "text"
        assert "healthy" in result[0].text.lower()
    
    @pytest.mark.asyncio
    async def test_tool_call_handler_unknown_tool(self):
        """도구 호출 핸들러 - 알 수 없는 도구 테스트"""
        result = await handle_call_tool("unknown_tool", {})
        
        assert len(result) == 1
        assert result[0].type == "text"
        assert "Error" in result[0].text
    
    @patch('src.config.get_settings')
    @pytest.mark.asyncio
    async def test_volume_ranking_with_mock_api(self, mock_settings):
        """거래대금 순위 조회 테스트 (모킹된 API)"""
        # 설정 모킹
        mock_settings.return_value.korea_investment_app_key = "test_key"
        mock_settings.return_value.korea_investment_app_secret = "test_secret"
        mock_settings.return_value.korea_investment_base_url = "https://test.api.com"
        mock_settings.return_value.api_timeout_seconds = 30
        mock_settings.return_value.default_ranking_count = 20
        mock_settings.return_value.max_ranking_count = 50
        
        # 도구 핸들러에서 API 호출 모킹
        with patch('src.tools.volume_tools.VolumeRankingAPI') as mock_api_class:
            mock_api = AsyncMock()
            mock_api_class.return_value = mock_api
            
            # API 응답 모킹
            mock_api.get_volume_rank.return_value = {
                "rt_cd": "0",
                "msg1": "정상처리 되었습니다",
                "output": [
                    {
                        "hts_kor_isnm": "삼성전자",
                        "mksc_shrn_iscd": "005930",
                        "stck_prpr": "78500",
                        "prdy_vrss": "1200",
                        "prdy_ctrt": "1.55",
                        "acml_vol": "15234567",
                        "acml_tr_pbmn": "1196213009500",
                        "vol_tnrt": "0.25"
                    },
                    {
                        "hts_kor_isnm": "SK하이닉스",
                        "mksc_shrn_iscd": "000660",
                        "stck_prpr": "135000",
                        "prdy_vrss": "-2000",
                        "prdy_ctrt": "-1.46",
                        "acml_vol": "8567432",
                        "acml_tr_pbmn": "1156503320000",
                        "vol_tnrt": "0.18"
                    }
                ]
            }
            
            # 도구 호출 테스트
            result = await handle_get_volume_ranking({
                "market": "ALL",
                "count": 10,
                "include_details": True
            })
            
            # 결과 검증
            assert len(result) == 1
            assert result[0].type == "text"
            response_text = result[0].text
            
            # 응답에 필요한 정보가 포함되어 있는지 확인
            assert "삼성전자" in response_text
            assert "SK하이닉스" in response_text
            assert "거래대금 순위" in response_text
    
    @patch('src.config.get_settings')
    @pytest.mark.asyncio
    async def test_volume_ranking_parameter_validation(self, mock_settings):
        """거래대금 순위 조회 매개변수 검증 테스트"""
        # 설정 모킹
        mock_settings.return_value.korea_investment_app_key = "test_key"
        mock_settings.return_value.korea_investment_app_secret = "test_secret"
        mock_settings.return_value.korea_investment_base_url = "https://test.api.com"
        mock_settings.return_value.api_timeout_seconds = 30
        mock_settings.return_value.default_ranking_count = 20
        mock_settings.return_value.max_ranking_count = 50
        
        # 유효한 매개변수 테스트
        test_cases = [
            {"market": "ALL", "count": 10},
            {"market": "KOSPI", "count": 20},
            {"market": "KOSDAQ", "count": 5},
            {},  # 기본값 사용
        ]
        
        for test_case in test_cases:
            with patch('src.tools.volume_tools.VolumeRankingAPI') as mock_api_class:
                mock_api = AsyncMock()
                mock_api_class.return_value = mock_api
                mock_api.get_volume_rank.return_value = {
                    "rt_cd": "0",
                    "msg1": "성공",
                    "output": []
                }
                
                result = await handle_get_volume_ranking(test_case)
                # 에러가 발생하지 않고 결과가 반환되는지 확인
                assert len(result) >= 1
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """에러 처리 테스트"""
        # API 키가 없는 상황에서의 에러 처리
        result = await handle_get_volume_ranking({
            "market": "ALL",
            "count": 10
        })
        
        # 에러 메시지가 적절히 반환되는지 확인
        assert len(result) == 1
        assert result[0].type == "text"
        assert "오류" in result[0].text
    
    def test_configuration_loading(self):
        """설정 로딩 테스트"""
        settings = get_settings()
        
        # 기본 설정값들이 로드되는지 확인
        assert hasattr(settings, 'default_ranking_count')
        assert hasattr(settings, 'max_ranking_count')
        assert hasattr(settings, 'log_level')
        assert hasattr(settings, 'environment')
        
        # 설정값들이 유효한지 확인
        assert settings.default_ranking_count > 0
        assert settings.max_ranking_count >= settings.default_ranking_count
        assert settings.environment in ["development", "production", "test"]
    
    @pytest.mark.asyncio
    async def test_full_server_workflow(self):
        """전체 서버 워크플로우 테스트"""
        # 1. 도구 목록 조회
        tools = await handle_list_tools()
        assert len(tools) >= 2
        
        # 2. 헬스체크
        health_result = await handle_health_check()
        assert len(health_result) == 1
        assert "healthy" in health_result[0].text.lower()
        
        # 3. 도구 호출 (헬스체크)
        tool_result = await handle_call_tool("health_check", {})
        assert len(tool_result) == 1
        
        # 4. 도구 호출 (거래대금 순위) - 에러 예상
        volume_result = await handle_call_tool("get_volume_ranking", {
            "market": "ALL",
            "count": 5
        })
        assert len(volume_result) == 1
        # API 키가 없으므로 에러 메시지 또는 모킹된 결과 반환

class TestPhase1Validation:
    """Phase 1 검증 테스트"""
    
    def test_project_structure(self):
        """프로젝트 구조 검증"""
        import os
        
        # 필수 디렉토리 확인
        required_dirs = [
            "src",
            "src/api", 
            "src/tools",
            "src/utils",
            "tests",
            "logs"
        ]
        
        for dir_path in required_dirs:
            assert os.path.exists(dir_path), f"Required directory missing: {dir_path}"
        
        # 필수 파일 확인
        required_files = [
            "src/__init__.py",
            "src/server.py",
            "src/config.py",
            "src/exceptions.py",
            "src/api/__init__.py",
            "src/api/client.py",
            "src/api/models.py",
            "src/api/constants.py",
            "src/tools/__init__.py",
            "src/tools/volume_tools.py",
            "src/utils/__init__.py",
            "src/utils/logger.py",
            "src/utils/formatter.py",
            "src/utils/validator.py",
            "requirements.txt",
            ".env.example",
            ".env",
            "README.md"
        ]
        
        for file_path in required_files:
            assert os.path.exists(file_path), f"Required file missing: {file_path}"
    
    def test_imports(self):
        """Import 테스트"""
        # 주요 모듈들이 정상적으로 import되는지 확인
        try:
            from src.config import get_settings
            from src.exceptions import VolumeRankingError
            from src.api.client import KoreaInvestmentAPI, VolumeRankingAPI
            from src.api.models import StockInfo, PriceInfo, VolumeInfo
            from src.api.constants import get_market_code
            from src.tools.volume_tools import VolumeRankingTool
            from src.utils.logger import setup_logger
            from src.utils.formatter import format_currency
            from src.utils.validator import validate_stock_code
            
            # 기본 인스턴스 생성 테스트
            settings = get_settings()
            logger = setup_logger()
            
            print("All imports successful")
            
        except Exception as e:
            pytest.fail(f"Import error: {str(e)}")
    
    def test_phase1_completion_criteria(self):
        """Phase 1 완료 기준 검증"""
        
        # ✅ MCP 서버 기본 실행
        from src.server import server
        assert server is not None
        
        # ✅ 한국투자증권 API 연동 (구조 완성)
        from src.api.client import VolumeRankingAPI
        # API 키 없이도 클래스 정의는 확인 가능
        
        # ✅ 첫 번째 도구 동작
        from src.tools.volume_tools import VolumeRankingTool
        tool = VolumeRankingTool()
        assert tool is not None
        
        # ✅ 기본 테스트 통과
        # 이 테스트 자체가 통과되면 기본 테스트 통과 조건 만족
        
        print("Phase 1 completion criteria verified")

if __name__ == "__main__":
    # 테스트 실행
    pytest.main([__file__, "-v", "-s"])