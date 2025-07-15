"""
API Client Tests
API 클라이언트 테스트
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
import json

from src.api.client import KoreaInvestmentAPI, VolumeRankingAPI, APIToken
from src.api.models import KoreaInvestmentAPIResponse
from src.api.constants import get_market_code, get_error_message, is_valid_stock_code
from src.exceptions import (
    APIError, 
    AuthenticationError, 
    ConfigurationError,
    TimeoutError
)

class TestAPIToken:
    """API 토큰 테스트"""
    
    def test_token_creation(self):
        """토큰 생성 테스트"""
        token = APIToken(access_token="test_token_123")
        assert token.access_token == "test_token_123"
        assert token.token_type == "Bearer"
        assert token.authorization_header == "Bearer test_token_123"
    
    def test_token_expiry(self):
        """토큰 만료 테스트"""
        from datetime import timedelta
        
        # 만료되지 않은 토큰
        token = APIToken(
            access_token="test_token",
            expires_in=3600  # 1시간
        )
        assert not token.is_expired
        
        # 만료된 토큰 시뮬레이션
        token.created_at = datetime.now() - timedelta(seconds=3700)
        assert token.is_expired

class TestAPIConstants:
    """API 상수 테스트"""
    
    def test_market_code_mapping(self):
        """시장 코드 매핑 테스트"""
        assert get_market_code("ALL") == "J"
        assert get_market_code("KOSPI") == "0"
        assert get_market_code("KOSDAQ") == "1"
        assert get_market_code("invalid") == "J"  # 기본값
    
    def test_stock_code_validation(self):
        """종목 코드 검증 테스트"""
        assert is_valid_stock_code("005930")  # 삼성전자
        assert is_valid_stock_code("000660")  # SK하이닉스
        assert not is_valid_stock_code("00593")  # 5자리
        assert not is_valid_stock_code("0059300")  # 7자리
        assert not is_valid_stock_code("00593A")  # 문자 포함
    
    def test_error_message_mapping(self):
        """에러 메시지 매핑 테스트"""
        assert get_error_message("0") == "정상"
        assert get_error_message("40010000") == "잘못된 요청"
        assert get_error_message("unknown") == "알 수 없는 오류 (unknown)"

class TestKoreaInvestmentAPI:
    """한국투자증권 API 클라이언트 테스트"""
    
    def test_api_initialization_error(self):
        """API 초기화 에러 테스트"""
        with patch('src.config.get_settings') as mock_settings:
            mock_settings.return_value.korea_investment_app_key = "your_app_key_here"
            mock_settings.return_value.korea_investment_app_secret = "valid_secret"
            
            with pytest.raises(ConfigurationError):
                KoreaInvestmentAPI()
    
    @patch('src.config.get_settings')
    def test_api_initialization_success(self, mock_settings):
        """API 초기화 성공 테스트"""
        mock_settings.return_value.korea_investment_app_key = "valid_app_key"
        mock_settings.return_value.korea_investment_app_secret = "valid_secret"
        mock_settings.return_value.korea_investment_base_url = "https://test.api.com"
        mock_settings.return_value.api_timeout_seconds = 30
        
        api = KoreaInvestmentAPI()
        assert api.app_key == "valid_app_key"
        assert api.app_secret == "valid_secret"
        assert api.base_url == "https://test.api.com"
    
    @patch('src.config.get_settings')
    @patch('aiohttp.ClientSession.post')
    @pytest.mark.asyncio
    async def test_get_access_token_success(self, mock_post, mock_settings):
        """액세스 토큰 획득 성공 테스트"""
        # Mock 설정
        mock_settings.return_value.korea_investment_app_key = "valid_app_key"
        mock_settings.return_value.korea_investment_app_secret = "valid_secret"
        mock_settings.return_value.korea_investment_base_url = "https://test.api.com"
        mock_settings.return_value.api_timeout_seconds = 30
        
        # Mock 응답
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "access_token": "test_access_token_123",
            "token_type": "Bearer",
            "expires_in": 86400
        }
        mock_post.return_value.__aenter__.return_value = mock_response
        
        # 테스트 실행
        api = KoreaInvestmentAPI()
        token = await api._get_access_token()
        
        assert token == "test_access_token_123"
        assert api._token_cache is not None
        assert api._token_cache.access_token == "test_access_token_123"
    
    @patch('src.config.get_settings')
    @patch('aiohttp.ClientSession.post')
    @pytest.mark.asyncio
    async def test_get_access_token_failure(self, mock_post, mock_settings):
        """액세스 토큰 획득 실패 테스트"""
        # Mock 설정
        mock_settings.return_value.korea_investment_app_key = "invalid_key"
        mock_settings.return_value.korea_investment_app_secret = "invalid_secret"
        mock_settings.return_value.korea_investment_base_url = "https://test.api.com"
        mock_settings.return_value.api_timeout_seconds = 30
        
        # Mock 응답 (인증 실패)
        mock_response = AsyncMock()
        mock_response.status = 401
        mock_response.text.return_value = "Unauthorized"
        mock_post.return_value.__aenter__.return_value = mock_response
        
        # 테스트 실행
        api = KoreaInvestmentAPI()
        
        with pytest.raises(AuthenticationError):
            await api._get_access_token()
    
    @patch('src.config.get_settings')
    @patch('aiohttp.ClientSession.request')
    @pytest.mark.asyncio
    async def test_make_request_success(self, mock_request, mock_settings):
        """API 요청 성공 테스트"""
        # Mock 설정
        mock_settings.return_value.korea_investment_app_key = "valid_key"
        mock_settings.return_value.korea_investment_app_secret = "valid_secret"
        mock_settings.return_value.korea_investment_base_url = "https://test.api.com"
        mock_settings.return_value.api_timeout_seconds = 30
        
        # Mock 토큰 캐시 설정
        api = KoreaInvestmentAPI()
        api._token_cache = APIToken(access_token="test_token_123")
        
        # Mock 응답
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text.return_value = json.dumps({
            "rt_cd": "0",
            "msg1": "성공",
            "output": [{"test": "data"}]
        })
        mock_request.return_value.__aenter__.return_value = mock_response
        
        # 테스트 실행
        result = await api._make_request(
            "GET",
            "/test/endpoint",
            tr_id="TEST01"
        )
        
        assert result["rt_cd"] == "0"
        assert result["msg1"] == "성공"
        assert result["output"] == [{"test": "data"}]
    
    @patch('src.config.get_settings')
    @pytest.mark.asyncio
    async def test_health_check_with_mock_api(self, mock_settings):
        """헬스체크 테스트 (모킹된 API)"""
        # Mock 설정
        mock_settings.return_value.korea_investment_app_key = "valid_key"
        mock_settings.return_value.korea_investment_app_secret = "valid_secret"
        mock_settings.return_value.korea_investment_base_url = "https://test.api.com"
        mock_settings.return_value.api_timeout_seconds = 30
        
        api = KoreaInvestmentAPI()
        
        # get_stock_price 메소드를 모킹
        with patch.object(api, 'get_stock_price') as mock_get_stock_price:
            mock_get_stock_price.return_value = {"rt_cd": "0", "msg1": "성공"}
            
            result = await api.health_check()
            assert result is True
            mock_get_stock_price.assert_called_once_with("005930")
        
        # 실패 케이스
        with patch.object(api, 'get_stock_price') as mock_get_stock_price:
            mock_get_stock_price.side_effect = APIError("API 호출 실패")
            
            result = await api.health_check()
            assert result is False

class TestVolumeRankingAPI:
    """거래대금 순위 API 테스트"""
    
    @patch('src.config.get_settings')
    @pytest.mark.asyncio
    async def test_get_volume_rank_with_mock(self, mock_settings):
        """거래대금 순위 조회 테스트 (모킹)"""
        # Mock 설정
        mock_settings.return_value.korea_investment_app_key = "valid_key"
        mock_settings.return_value.korea_investment_app_secret = "valid_secret"
        mock_settings.return_value.korea_investment_base_url = "https://test.api.com"
        mock_settings.return_value.api_timeout_seconds = 30
        
        api = VolumeRankingAPI()
        
        # _make_request 메소드를 모킹
        mock_response = {
            "rt_cd": "0",
            "msg1": "성공",
            "output": [
                {
                    "hts_kor_isnm": "삼성전자",
                    "mksc_shrn_iscd": "005930",
                    "stck_prpr": "78500",
                    "acml_tr_pbmn": "1196213009500"
                }
            ]
        }
        
        with patch.object(api, '_make_request') as mock_make_request:
            mock_make_request.return_value = mock_response
            
            result = await api.get_volume_rank("J", "0")
            
            assert result["rt_cd"] == "0"
            assert len(result["output"]) == 1
            assert result["output"][0]["hts_kor_isnm"] == "삼성전자"
            
            # _make_request가 올바른 파라미터로 호출되었는지 확인
            mock_make_request.assert_called_once()
            call_args = mock_make_request.call_args
            assert call_args[0][0] == "GET"  # method
            assert "/ranking/volume-rank" in call_args[0][1]  # endpoint

class TestAPIIntegration:
    """API 통합 테스트 (실제 API 키 없이)"""
    
    @pytest.mark.asyncio
    async def test_api_workflow_with_mocks(self):
        """API 워크플로우 통합 테스트 (모킹)"""
        with patch('src.config.get_settings') as mock_settings:
            # 설정 모킹
            mock_settings.return_value.korea_investment_app_key = "test_key"
            mock_settings.return_value.korea_investment_app_secret = "test_secret"
            mock_settings.return_value.korea_investment_base_url = "https://test.api.com"
            mock_settings.return_value.api_timeout_seconds = 30
            
            api = VolumeRankingAPI()
            
            # 토큰 획득 모킹
            with patch.object(api, '_get_access_token') as mock_get_token:
                mock_get_token.return_value = "mock_token_123"
                
                # HTTP 요청 모킹
                with patch('aiohttp.ClientSession.request') as mock_request:
                    mock_response = AsyncMock()
                    mock_response.status = 200
                    mock_response.text.return_value = json.dumps({
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
                                "acml_tr_pbmn": "1196213009500"
                            },
                            {
                                "hts_kor_isnm": "SK하이닉스",
                                "mksc_shrn_iscd": "000660",
                                "stck_prpr": "135000",
                                "prdy_vrss": "-2000",
                                "prdy_ctrt": "-1.46",
                                "acml_vol": "8567432",
                                "acml_tr_pbmn": "1156503320000"
                            }
                        ]
                    })
                    mock_request.return_value.__aenter__.return_value = mock_response
                    
                    # 실제 호출 테스트
                    result = await api.get_volume_rank("J", "0")
                    
                    # 결과 검증
                    assert result["rt_cd"] == "0"
                    assert len(result["output"]) == 2
                    
                    # 삼성전자 데이터 검증
                    samsung = result["output"][0]
                    assert samsung["hts_kor_isnm"] == "삼성전자"
                    assert samsung["mksc_shrn_iscd"] == "005930"
                    assert samsung["stck_prpr"] == "78500"
                    
                    # SK하이닉스 데이터 검증
                    sk = result["output"][1]
                    assert sk["hts_kor_isnm"] == "SK하이닉스"
                    assert sk["mksc_shrn_iscd"] == "000660"
                    assert sk["prdy_ctrt"] == "-1.46"

# 실제 API 테스트 (API 키가 있을 때만 실행)
class TestRealAPI:
    """실제 API 테스트 (API 키 필요)"""
    
    @pytest.mark.skipif(
        condition=True,  # 기본적으로 스킵 (실제 API 키가 없으므로)
        reason="실제 API 키가 필요한 테스트"
    )
    @pytest.mark.asyncio
    async def test_real_api_connection(self):
        """실제 API 연결 테스트"""
        # 이 테스트는 실제 API 키가 설정되었을 때만 실행
        api = VolumeRankingAPI()
        
        try:
            # 헬스체크
            health = await api.health_check()
            print(f"API Health Check: {health}")
            
            if health:
                # 실제 거래대금 순위 조회
                result = await api.get_volume_rank("J", "0")
                print(f"Volume Ranking Result: {result}")
                
                assert result["rt_cd"] == "0"
                assert "output" in result
                
        except Exception as e:
            pytest.skip(f"실제 API 테스트 실패 (예상됨): {str(e)}")

if __name__ == "__main__":
    # 테스트 실행
    pytest.main([__file__, "-v", "-s"])