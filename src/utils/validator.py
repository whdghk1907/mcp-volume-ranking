"""
Data validation utilities
데이터 검증 유틸리티
"""

import re
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, date

from src.exceptions import DataValidationError, InvalidParameterError

def validate_stock_code(stock_code: str) -> str:
    """
    종목 코드 검증
    
    Args:
        stock_code: 종목 코드
    
    Returns:
        검증된 종목 코드
    
    Raises:
        InvalidParameterError: 유효하지 않은 종목 코드
    """
    if not stock_code:
        raise InvalidParameterError("종목 코드가 없습니다")
    
    # 공백 제거
    stock_code = stock_code.strip()
    
    # 6자리 숫자 검증
    if not re.match(r'^\d{6}$', stock_code):
        raise InvalidParameterError(f"종목 코드는 6자리 숫자여야 합니다: {stock_code}")
    
    return stock_code

def validate_market(market: str) -> str:
    """
    시장 구분 검증
    
    Args:
        market: 시장 구분
    
    Returns:
        검증된 시장 구분
    
    Raises:
        InvalidParameterError: 유효하지 않은 시장 구분
    """
    if not market:
        raise InvalidParameterError("시장 구분이 없습니다")
    
    market = market.upper().strip()
    
    valid_markets = ["ALL", "KOSPI", "KOSDAQ", "KONEX"]
    if market not in valid_markets:
        raise InvalidParameterError(
            f"유효하지 않은 시장 구분: {market}. "
            f"가능한 값: {', '.join(valid_markets)}"
        )
    
    return market

def validate_count(count: Any, min_value: int = 1, max_value: int = 50) -> int:
    """
    조회 개수 검증
    
    Args:
        count: 조회 개수
        min_value: 최소값
        max_value: 최대값
    
    Returns:
        검증된 조회 개수
    
    Raises:
        InvalidParameterError: 유효하지 않은 조회 개수
    """
    if count is None:
        raise InvalidParameterError("조회 개수가 없습니다")
    
    try:
        count = int(count)
    except (ValueError, TypeError):
        raise InvalidParameterError(f"조회 개수는 숫자여야 합니다: {count}")
    
    if count < min_value:
        raise InvalidParameterError(
            f"조회 개수는 {min_value} 이상이어야 합니다: {count}"
        )
    
    if count > max_value:
        raise InvalidParameterError(
            f"조회 개수는 {max_value} 이하여야 합니다: {count}"
        )
    
    return count

def validate_price(price: Any, allow_zero: bool = False) -> int:
    """
    가격 검증
    
    Args:
        price: 가격
        allow_zero: 0 허용 여부
    
    Returns:
        검증된 가격
    
    Raises:
        DataValidationError: 유효하지 않은 가격
    """
    if price is None:
        raise DataValidationError("가격이 없습니다")
    
    try:
        if isinstance(price, str):
            price = price.replace(",", "")
        price = int(float(price))
    except (ValueError, TypeError):
        raise DataValidationError(f"가격은 숫자여야 합니다: {price}")
    
    if not allow_zero and price <= 0:
        raise DataValidationError(f"가격은 0보다 커야 합니다: {price}")
    elif allow_zero and price < 0:
        raise DataValidationError(f"가격은 0 이상이어야 합니다: {price}")
    
    return price

def validate_volume(volume: Any) -> int:
    """
    거래량 검증
    
    Args:
        volume: 거래량
    
    Returns:
        검증된 거래량
    
    Raises:
        DataValidationError: 유효하지 않은 거래량
    """
    if volume is None:
        raise DataValidationError("거래량이 없습니다")
    
    try:
        if isinstance(volume, str):
            volume = volume.replace(",", "")
        volume = int(float(volume))
    except (ValueError, TypeError):
        raise DataValidationError(f"거래량은 숫자여야 합니다: {volume}")
    
    if volume < 0:
        raise DataValidationError(f"거래량은 0 이상이어야 합니다: {volume}")
    
    return volume

def validate_percentage(percentage: Any, min_value: float = -100.0, max_value: float = 1000.0) -> float:
    """
    퍼센트 값 검증
    
    Args:
        percentage: 퍼센트 값
        min_value: 최소값
        max_value: 최대값
    
    Returns:
        검증된 퍼센트 값
    
    Raises:
        DataValidationError: 유효하지 않은 퍼센트 값
    """
    if percentage is None:
        raise DataValidationError("퍼센트 값이 없습니다")
    
    try:
        percentage = float(percentage)
    except (ValueError, TypeError):
        raise DataValidationError(f"퍼센트 값은 숫자여야 합니다: {percentage}")
    
    if percentage < min_value or percentage > max_value:
        raise DataValidationError(
            f"퍼센트 값은 {min_value}~{max_value} 범위여야 합니다: {percentage}"
        )
    
    return percentage

def validate_date_string(date_string: str, format_string: str = "%Y%m%d") -> str:
    """
    날짜 문자열 검증
    
    Args:
        date_string: 날짜 문자열
        format_string: 날짜 포맷
    
    Returns:
        검증된 날짜 문자열
    
    Raises:
        InvalidParameterError: 유효하지 않은 날짜
    """
    if not date_string:
        raise InvalidParameterError("날짜가 없습니다")
    
    try:
        datetime.strptime(date_string, format_string)
        return date_string
    except ValueError:
        raise InvalidParameterError(
            f"날짜 형식이 올바르지 않습니다: {date_string} "
            f"(예상 형식: {format_string})"
        )

def validate_investor_type(investor_type: str) -> str:
    """
    투자자 유형 검증
    
    Args:
        investor_type: 투자자 유형
    
    Returns:
        검증된 투자자 유형
    
    Raises:
        InvalidParameterError: 유효하지 않은 투자자 유형
    """
    if not investor_type:
        raise InvalidParameterError("투자자 유형이 없습니다")
    
    investor_type = investor_type.upper().strip()
    
    valid_types = ["FOREIGN", "INSTITUTION", "INDIVIDUAL", "PROGRAM"]
    if investor_type not in valid_types:
        raise InvalidParameterError(
            f"유효하지 않은 투자자 유형: {investor_type}. "
            f"가능한 값: {', '.join(valid_types)}"
        )
    
    return investor_type

def validate_trade_type(trade_type: str) -> str:
    """
    거래 유형 검증
    
    Args:
        trade_type: 거래 유형
    
    Returns:
        검증된 거래 유형
    
    Raises:
        InvalidParameterError: 유효하지 않은 거래 유형
    """
    if not trade_type:
        raise InvalidParameterError("거래 유형이 없습니다")
    
    trade_type = trade_type.upper().strip()
    
    valid_types = ["BUY", "SELL", "NET"]
    if trade_type not in valid_types:
        raise InvalidParameterError(
            f"유효하지 않은 거래 유형: {trade_type}. "
            f"가능한 값: {', '.join(valid_types)}"
        )
    
    return trade_type

def validate_period(period: str) -> str:
    """
    기간 검증
    
    Args:
        period: 기간
    
    Returns:
        검증된 기간
    
    Raises:
        InvalidParameterError: 유효하지 않은 기간
    """
    if not period:
        raise InvalidParameterError("기간이 없습니다")
    
    period = period.upper().strip()
    
    valid_periods = ["1D", "5D", "20D", "60D"]
    if period not in valid_periods:
        raise InvalidParameterError(
            f"유효하지 않은 기간: {period}. "
            f"가능한 값: {', '.join(valid_periods)}"
        )
    
    return period

def validate_api_response(response: Dict[str, Any]) -> Dict[str, Any]:
    """
    API 응답 검증
    
    Args:
        response: API 응답
    
    Returns:
        검증된 API 응답
    
    Raises:
        DataValidationError: 유효하지 않은 API 응답
    """
    if not isinstance(response, dict):
        raise DataValidationError("API 응답이 딕셔너리가 아닙니다")
    
    # 응답 코드 확인
    rt_cd = response.get("rt_cd")
    if rt_cd != "0":
        msg = response.get("msg1", "알 수 없는 오류")
        raise DataValidationError(f"API 오류: {msg} (코드: {rt_cd})")
    
    return response

def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> Dict[str, Any]:
    """
    필수 필드 검증
    
    Args:
        data: 검증할 데이터
        required_fields: 필수 필드 목록
    
    Returns:
        검증된 데이터
    
    Raises:
        DataValidationError: 필수 필드 누락
    """
    missing_fields = []
    
    for field in required_fields:
        if field not in data or data[field] is None:
            missing_fields.append(field)
    
    if missing_fields:
        raise DataValidationError(
            f"필수 필드가 누락되었습니다: {', '.join(missing_fields)}"
        )
    
    return data

def validate_stock_ranking_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    주식 순위 항목 검증
    
    Args:
        item: 주식 순위 항목
    
    Returns:
        검증된 항목
    
    Raises:
        DataValidationError: 유효하지 않은 데이터
    """
    if not isinstance(item, dict):
        raise DataValidationError("순위 항목이 딕셔너리가 아닙니다")
    
    # 필수 필드 확인
    required_fields = ["mksc_shrn_iscd", "hts_kor_isnm", "stck_prpr"]
    validate_required_fields(item, required_fields)
    
    # 종목 코드 검증
    stock_code = item.get("mksc_shrn_iscd", "").strip()
    if stock_code:
        validate_stock_code(stock_code)
    
    # 현재가 검증
    current_price = item.get("stck_prpr")
    if current_price is not None:
        validate_price(current_price, allow_zero=True)
    
    # 거래량 검증
    volume = item.get("acml_vol")
    if volume is not None:
        validate_volume(volume)
    
    return item

def validate_ranking_response(response: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    순위 응답 검증
    
    Args:
        response: 순위 응답 리스트
    
    Returns:
        검증된 응답
    
    Raises:
        DataValidationError: 유효하지 않은 응답
    """
    if not isinstance(response, list):
        raise DataValidationError("순위 응답이 리스트가 아닙니다")
    
    if not response:
        raise DataValidationError("순위 데이터가 비어있습니다")
    
    validated_items = []
    for i, item in enumerate(response):
        try:
            validated_item = validate_stock_ranking_item(item)
            validated_items.append(validated_item)
        except DataValidationError as e:
            # 개별 항목 오류는 로그로 기록하고 계속 진행
            continue
    
    if not validated_items:
        raise DataValidationError("유효한 순위 데이터가 없습니다")
    
    return validated_items

def is_market_hours() -> bool:
    """
    장 운영 시간 확인
    
    Returns:
        장 운영 시간 여부
    """
    from datetime import datetime, time
    
    now = datetime.now()
    
    # 주말 확인
    if now.weekday() >= 5:  # 토요일(5), 일요일(6)
        return False
    
    # 장 시간 확인 (오전 9시 ~ 오후 3시 30분)
    market_open = time(9, 0)
    market_close = time(15, 30)
    current_time = now.time()
    
    return market_open <= current_time <= market_close

def validate_threshold(threshold: Any, min_value: float = 0.0, max_value: float = 1000.0) -> float:
    """
    임계값 검증
    
    Args:
        threshold: 임계값
        min_value: 최소값
        max_value: 최대값
    
    Returns:
        검증된 임계값
    
    Raises:
        InvalidParameterError: 유효하지 않은 임계값
    """
    if threshold is None:
        raise InvalidParameterError("임계값이 없습니다")
    
    try:
        threshold = float(threshold)
    except (ValueError, TypeError):
        raise InvalidParameterError(f"임계값은 숫자여야 합니다: {threshold}")
    
    if threshold < min_value or threshold > max_value:
        raise InvalidParameterError(
            f"임계값은 {min_value}~{max_value} 범위여야 합니다: {threshold}"
        )
    
    return threshold

class ValidationResult:
    """검증 결과"""
    
    def __init__(self, is_valid: bool, message: str = "", data: Any = None):
        self.is_valid = is_valid
        self.message = message
        self.data = data
    
    def __bool__(self) -> bool:
        return self.is_valid

def validate_with_result(validator_func, *args, **kwargs) -> ValidationResult:
    """
    검증 함수를 실행하고 결과 반환
    
    Args:
        validator_func: 검증 함수
        *args: 검증 함수 인수
        **kwargs: 검증 함수 키워드 인수
    
    Returns:
        검증 결과
    """
    try:
        result = validator_func(*args, **kwargs)
        return ValidationResult(True, "검증 성공", result)
    except (InvalidParameterError, DataValidationError) as e:
        return ValidationResult(False, str(e), None)
    except Exception as e:
        return ValidationResult(False, f"예상치 못한 오류: {str(e)}", None)