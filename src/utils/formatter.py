"""
Data formatting utilities
데이터 포맷팅 유틸리티
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import re

def format_currency(amount: int, currency: str = "원") -> str:
    """
    통화 포맷팅
    
    Args:
        amount: 금액
        currency: 통화 단위
    
    Returns:
        포맷팅된 통화 문자열
    """
    if amount == 0:
        return f"0{currency}"
    
    # 큰 단위로 변환
    if amount >= 1_000_000_000_000:  # 1조
        return f"{amount / 1_000_000_000_000:.1f}조{currency}"
    elif amount >= 100_000_000:  # 1억
        return f"{amount / 100_000_000:.1f}억{currency}"
    elif amount >= 10_000:  # 1만
        return f"{amount / 10_000:.1f}만{currency}"
    else:
        return f"{amount:,}{currency}"

def format_percentage(value: float, decimal_places: int = 2) -> str:
    """
    퍼센트 포맷팅
    
    Args:
        value: 퍼센트 값
        decimal_places: 소수점 자릿수
    
    Returns:
        포맷팅된 퍼센트 문자열
    """
    if value > 0:
        return f"+{value:.{decimal_places}f}%"
    else:
        return f"{value:.{decimal_places}f}%"

def format_change(change: int, change_rate: float) -> str:
    """
    변화량 포맷팅 (가격 변동)
    
    Args:
        change: 절대 변화량
        change_rate: 변화율
    
    Returns:
        포맷팅된 변화량 문자열
    """
    if change > 0:
        return f"📈 +{change:,}원 ({change_rate:+.2f}%)"
    elif change < 0:
        return f"📉 {change:,}원 ({change_rate:.2f}%)"
    else:
        return f"➡️ 0원 (0.00%)"

def format_volume(volume: int) -> str:
    """
    거래량 포맷팅
    
    Args:
        volume: 거래량
    
    Returns:
        포맷팅된 거래량 문자열
    """
    if volume >= 100_000_000:  # 1억
        return f"{volume / 100_000_000:.1f}억주"
    elif volume >= 10_000:  # 1만
        return f"{volume / 10_000:.1f}만주"
    else:
        return f"{volume:,}주"

def format_market_cap(market_cap: int) -> str:
    """
    시가총액 포맷팅
    
    Args:
        market_cap: 시가총액
    
    Returns:
        포맷팅된 시가총액 문자열
    """
    return format_currency(market_cap)

def format_datetime(dt: datetime, format_type: str = "full") -> str:
    """
    날짜시간 포맷팅
    
    Args:
        dt: 날짜시간 객체
        format_type: 포맷 타입 (full, date, time, short)
    
    Returns:
        포맷팅된 날짜시간 문자열
    """
    if format_type == "full":
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    elif format_type == "date":
        return dt.strftime("%Y-%m-%d")
    elif format_type == "time":
        return dt.strftime("%H:%M:%S")
    elif format_type == "short":
        return dt.strftime("%m/%d %H:%M")
    else:
        return dt.isoformat()

def format_stock_name(stock_name: str, max_length: int = 12) -> str:
    """
    종목명 포맷팅 (길이 제한)
    
    Args:
        stock_name: 종목명
        max_length: 최대 길이
    
    Returns:
        포맷팅된 종목명
    """
    if len(stock_name) <= max_length:
        return stock_name
    else:
        return stock_name[:max_length-1] + "…"

def format_rank_badge(rank: int) -> str:
    """
    순위 뱃지 포맷팅
    
    Args:
        rank: 순위
    
    Returns:
        포맷팅된 순위 뱃지
    """
    if rank == 1:
        return "🥇"
    elif rank == 2:
        return "🥈"
    elif rank == 3:
        return "🥉"
    elif rank <= 10:
        return f"🔟"
    else:
        return f"{rank}"

def format_table_row(
    rank: int,
    stock_name: str,
    current_price: int,
    change: int,
    change_rate: float,
    trading_value: int,
    name_width: int = 12,
    align_right: bool = True
) -> str:
    """
    테이블 행 포맷팅
    
    Args:
        rank: 순위
        stock_name: 종목명
        current_price: 현재가
        change: 변화량
        change_rate: 변화율
        trading_value: 거래대금
        name_width: 종목명 너비
        align_right: 우측 정렬 여부
    
    Returns:
        포맷팅된 테이블 행
    """
    rank_str = f"{rank:2d}"
    name_str = format_stock_name(stock_name, name_width)
    
    if align_right:
        name_str = f"{name_str:>{name_width}}"
    else:
        name_str = f"{name_str:<{name_width}}"
    
    price_str = f"{current_price:>8,}"
    change_str = f"{change:>+7,}" if change != 0 else f"{'0':>7}"
    rate_str = f"{change_rate:>+6.2f}%" if change_rate != 0 else f"{'0.00%':>7}"
    value_str = f"{trading_value:>12,}"
    
    return f"{rank_str} {name_str} {price_str} {change_str} {rate_str} {value_str}"

def format_summary_table(data: List[Dict[str, Any]], title: str = "") -> str:
    """
    요약 테이블 포맷팅
    
    Args:
        data: 테이블 데이터
        title: 테이블 제목
    
    Returns:
        포맷팅된 테이블 문자열
    """
    if not data:
        return "데이터가 없습니다."
    
    lines = []
    
    if title:
        lines.append(f"## {title}")
        lines.append("")
    
    # 헤더
    lines.append("순위 | 종목명 | 현재가 | 변동 | 변동률 | 거래대금")
    lines.append("-" * 60)
    
    # 데이터 행
    for i, item in enumerate(data, 1):
        rank = item.get("rank", i)
        stock_name = item.get("stock_name", "")
        current_price = item.get("current_price", 0)
        change = item.get("change", 0)
        change_rate = item.get("change_rate", 0.0)
        trading_value = item.get("trading_value", 0)
        
        row = format_table_row(
            rank, stock_name, current_price, 
            change, change_rate, trading_value
        )
        lines.append(row)
    
    return "\n".join(lines)

def clean_string(text: str) -> str:
    """
    문자열 정리 (공백, 특수문자 제거)
    
    Args:
        text: 원본 문자열
    
    Returns:
        정리된 문자열
    """
    if not text:
        return ""
    
    # 앞뒤 공백 제거
    text = text.strip()
    
    # 연속된 공백을 하나로 변환
    text = re.sub(r'\s+', ' ', text)
    
    return text

def safe_int(value: Any, default: int = 0) -> int:
    """
    안전한 정수 변환
    
    Args:
        value: 변환할 값
        default: 기본값
    
    Returns:
        정수 값
    """
    if value is None or value == "":
        return default
    
    try:
        if isinstance(value, str):
            # 콤마 제거 후 변환
            value = value.replace(",", "")
        return int(float(value))
    except (ValueError, TypeError):
        return default

def safe_float(value: Any, default: float = 0.0) -> float:
    """
    안전한 실수 변환
    
    Args:
        value: 변환할 값
        default: 기본값
    
    Returns:
        실수 값
    """
    if value is None or value == "":
        return default
    
    try:
        if isinstance(value, str):
            # 콤마 제거 후 변환
            value = value.replace(",", "")
        return float(value)
    except (ValueError, TypeError):
        return default

def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    텍스트 자르기
    
    Args:
        text: 원본 텍스트
        max_length: 최대 길이
        suffix: 접미사
    
    Returns:
        자른 텍스트
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix