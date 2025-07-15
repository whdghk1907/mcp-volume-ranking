"""
MCP Volume Ranking Server
한국 주식시장 거래대금 순위 조회 MCP 서버
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel
)
import mcp.types as types
from mcp.server.models import InitializationOptions
import mcp.server.stdio

from src.config import get_settings
from src.exceptions import VolumeRankingError
from src.utils.logger import setup_logger
from src.tools.volume_tools import handle_get_volume_ranking
from src.tools.volume_change_tools import handle_get_volume_change_ranking
from src.tools.investor_tools import handle_get_investor_ranking
from src.tools.sector_tools import handle_get_sector_volume_ranking
from src.tools.market_cap_tools import handle_get_market_cap_ranking
from src.tools.unusual_volume_tools import handle_get_unusual_volume

# 설정 및 로거 초기화
settings = get_settings()
logger = setup_logger()

# MCP 서버 인스턴스 생성
server = Server("volume-ranking")

@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """
    사용 가능한 도구 목록 반환
    """
    return [
        Tool(
            name="health_check",
            description="서버 상태 확인",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_volume_ranking",
            description="거래대금 상위 종목 조회",
            inputSchema={
                "type": "object",
                "properties": {
                    "market": {
                        "type": "string",
                        "enum": ["ALL", "KOSPI", "KOSDAQ"],
                        "default": "ALL",
                        "description": "시장 구분"
                    },
                    "count": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 50,
                        "default": 20,
                        "description": "조회할 종목 수"
                    },
                    "include_details": {
                        "type": "boolean",
                        "default": True,
                        "description": "상세 정보 포함 여부"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="get_volume_change_ranking",
            description="거래량 변화율 순위 조회",
            inputSchema={
                "type": "object",
                "properties": {
                    "market": {
                        "type": "string",
                        "enum": ["ALL", "KOSPI", "KOSDAQ"],
                        "default": "ALL",
                        "description": "시장 구분"
                    },
                    "period": {
                        "type": "string",
                        "enum": ["1D", "1W", "1M"],
                        "default": "1D",
                        "description": "비교 기간"
                    },
                    "count": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 50,
                        "default": 20,
                        "description": "조회할 종목 수"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="get_investor_ranking",
            description="투자자별 거래 순위 조회",
            inputSchema={
                "type": "object",
                "properties": {
                    "investor_type": {
                        "type": "string",
                        "enum": ["FOREIGN", "INSTITUTION", "INDIVIDUAL", "PROGRAM"],
                        "default": "FOREIGN",
                        "description": "투자자 유형"
                    },
                    "trade_type": {
                        "type": "string",
                        "enum": ["BUY", "SELL", "NET"],
                        "default": "NET",
                        "description": "거래 유형"
                    },
                    "market": {
                        "type": "string",
                        "enum": ["ALL", "KOSPI", "KOSDAQ"],
                        "default": "ALL",
                        "description": "시장 구분"
                    },
                    "count": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 50,
                        "default": 20,
                        "description": "조회할 종목 수"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="get_sector_volume_ranking",
            description="업종별 거래대금 순위 조회",
            inputSchema={
                "type": "object",
                "properties": {
                    "market": {
                        "type": "string",
                        "enum": ["KOSPI", "KOSDAQ"],
                        "default": "KOSPI",
                        "description": "시장 구분"
                    },
                    "count": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 30,
                        "default": 10,
                        "description": "조회할 업종 수"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="get_market_cap_ranking",
            description="시가총액 순위 조회",
            inputSchema={
                "type": "object",
                "properties": {
                    "market": {
                        "type": "string",
                        "enum": ["ALL", "KOSPI", "KOSDAQ"],
                        "default": "ALL",
                        "description": "시장 구분"
                    },
                    "count": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 50,
                        "default": 20,
                        "description": "조회할 종목 수"
                    },
                    "filter_by": {
                        "type": "object",
                        "description": "필터링 조건",
                        "properties": {
                            "min_trading_value": {
                                "type": "integer",
                                "description": "최소 거래대금"
                            }
                        }
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="get_unusual_volume",
            description="이상 거래량 감지",
            inputSchema={
                "type": "object",
                "properties": {
                    "market": {
                        "type": "string",
                        "enum": ["ALL", "KOSPI", "KOSDAQ"],
                        "default": "ALL",
                        "description": "시장 구분"
                    },
                    "threshold": {
                        "type": "number",
                        "minimum": 100.0,
                        "maximum": 1000.0,
                        "default": 200.0,
                        "description": "거래량 임계값 (평균 대비 %)"
                    },
                    "count": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 50,
                        "default": 20,
                        "description": "조회할 종목 수"
                    },
                    "min_price": {
                        "type": "integer",
                        "minimum": 100,
                        "description": "최소 주가 (원)"
                    }
                },
                "required": []
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: Optional[Dict[str, Any]]) -> List[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    도구 호출 처리
    """
    logger.info(f"Tool called: {name} with arguments: {arguments}")
    
    try:
        if name == "health_check":
            return await handle_health_check()
        elif name == "get_volume_ranking":
            return await handle_get_volume_ranking(arguments or {})
        elif name == "get_volume_change_ranking":
            return await handle_get_volume_change_ranking(arguments or {})
        elif name == "get_investor_ranking":
            return await handle_get_investor_ranking(arguments or {})
        elif name == "get_sector_volume_ranking":
            return await handle_get_sector_volume_ranking(arguments or {})
        elif name == "get_market_cap_ranking":
            return await handle_get_market_cap_ranking(arguments or {})
        elif name == "get_unusual_volume":
            return await handle_get_unusual_volume(arguments or {})
        else:
            raise VolumeRankingError(f"Unknown tool: {name}")
    
    except Exception as e:
        logger.error(f"Error in tool {name}: {str(e)}")
        return [
            types.TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )
        ]

async def handle_health_check() -> List[types.TextContent]:
    """
    헬스체크 처리
    """
    health_status = {
        "status": "healthy",
        "server": "MCP Volume Ranking Server",
        "version": "1.0.0",
        "environment": settings.environment,
        "debug": settings.debug,
        "settings": {
            "max_ranking_count": settings.max_ranking_count,
            "default_ranking_count": settings.default_ranking_count,
            "cache_l1_ttl": settings.cache_l1_ttl_seconds,
            "cache_l2_ttl": settings.cache_l2_ttl_seconds
        }
    }
    
    return [
        types.TextContent(
            type="text",
            text=f"Health Check Result:\n{health_status}"
        )
    ]

async def handle_get_volume_ranking_mock(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """
    거래대금 순위 조회 처리 (임시 구현 - 백업용)
    """
    market = arguments.get("market", "ALL")
    count = arguments.get("count", settings.default_ranking_count)
    include_details = arguments.get("include_details", True)
    
    # 임시 응답 (API 연동 실패 시 사용)
    mock_response = {
        "timestamp": "2024-01-10T10:30:00+09:00",
        "market": market,
        "ranking": [
            {
                "rank": 1,
                "stock_code": "005930",
                "stock_name": "삼성전자",
                "market_type": "KOSPI",
                "current_price": 78500,
                "change": 1200,
                "change_rate": 1.55,
                "volume": 15234567,
                "trading_value": 1196213009500
            }
        ] * min(count, 5),  # 최대 5개 임시 데이터
        "summary": {
            "total_trading_value": 8523456789000,
            "kospi_trading_value": 5234567890000,
            "kosdaq_trading_value": 3288888899000
        }
    }
    
    return [
        types.TextContent(
            type="text",
            text=f"Volume Ranking Result (Mock):\n{mock_response}"
        )
    ]

async def main():
    """
    서버 실행
    """
    logger.info("Starting MCP Volume Ranking Server...")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")
    
    # stdio 인터페이스로 서버 실행
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="volume-ranking",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
        )

if __name__ == "__main__":
    # 비동기 이벤트 루프 실행
    asyncio.run(main())