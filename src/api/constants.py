"""
Constants and mappings for Korea Investment Securities API
한국투자증권 API 상수 및 매핑 테이블
"""

from typing import Dict, List
from enum import Enum

# API 기본 설정
class APIConstants:
    """API 기본 상수"""
    BASE_URL = "https://openapi.koreainvestment.com:9443"
    TOKEN_ENDPOINT = "/oauth2/tokenP"
    
    # 요청 제한
    MAX_REQUESTS_PER_SECOND = 5
    MAX_RANKING_COUNT = 50
    DEFAULT_TIMEOUT = 30
    
    # 토큰 설정
    TOKEN_EXPIRE_BUFFER = 300  # 5분 여유시간

# 시장 코드 매핑
class MarketCode(Enum):
    """시장 코드"""
    ALL = "J"        # 전체
    KOSPI = "0"      # 코스피
    KOSDAQ = "1"     # 코스닥
    KONEX = "2"      # 코넥스

MARKET_CODE_MAPPING = {
    "ALL": MarketCode.ALL.value,
    "KOSPI": MarketCode.KOSPI.value,
    "KOSDAQ": MarketCode.KOSDAQ.value,
    "KONEX": MarketCode.KONEX.value
}

MARKET_NAME_MAPPING = {
    MarketCode.ALL.value: "전체",
    MarketCode.KOSPI.value: "코스피",
    MarketCode.KOSDAQ.value: "코스닥",
    MarketCode.KONEX.value: "코넥스"
}

# 투자자 유형 코드
class InvestorType(Enum):
    """투자자 유형"""
    FOREIGN = "FOREIGN"        # 외국인
    INSTITUTION = "INSTITUTION" # 기관
    INDIVIDUAL = "INDIVIDUAL"   # 개인
    PROGRAM = "PROGRAM"        # 프로그램

# 거래 유형 코드
class TradeType(Enum):
    """거래 유형"""
    BUY = "BUY"    # 매수
    SELL = "SELL"  # 매도
    NET = "NET"    # 순매수

# 투자자별 화면 코드 매핑
INVESTOR_SCREEN_CODE_MAPPING = {
    (InvestorType.FOREIGN.value, TradeType.BUY.value): "20172",
    (InvestorType.FOREIGN.value, TradeType.SELL.value): "20173",
    (InvestorType.FOREIGN.value, TradeType.NET.value): "20174",
    (InvestorType.INSTITUTION.value, TradeType.BUY.value): "20175",
    (InvestorType.INSTITUTION.value, TradeType.SELL.value): "20176",
    (InvestorType.INSTITUTION.value, TradeType.NET.value): "20177",
    (InvestorType.INDIVIDUAL.value, TradeType.BUY.value): "20178",
    (InvestorType.INDIVIDUAL.value, TradeType.SELL.value): "20179",
    (InvestorType.INDIVIDUAL.value, TradeType.NET.value): "20180",
    (InvestorType.PROGRAM.value, TradeType.BUY.value): "20181",
    (InvestorType.PROGRAM.value, TradeType.SELL.value): "20182",
    (InvestorType.PROGRAM.value, TradeType.NET.value): "20183"
}

# 정렬 기준 코드
class SortType(Enum):
    """정렬 기준"""
    TRADING_VALUE = "0"  # 거래대금순
    TRADING_VOLUME = "1" # 거래량순
    PRICE_CHANGE = "2"   # 등락률순
    MARKET_CAP = "3"     # 시가총액순

# 기간 코드
class PeriodType(Enum):
    """기간 구분"""
    ONE_DAY = "1D"      # 1일
    FIVE_DAYS = "5D"    # 5일
    TWENTY_DAYS = "20D" # 20일
    SIXTY_DAYS = "60D"  # 60일

# API 엔드포인트
class APIEndpoints:
    """API 엔드포인트"""
    
    # 인증
    TOKEN = "/oauth2/tokenP"
    
    # 현재가 조회
    CURRENT_PRICE = "/uapi/domestic-stock/v1/quotations/inquire-price"
    
    # 순위 조회
    VOLUME_RANKING = "/uapi/domestic-stock/v1/ranking/volume-rank"
    FLUCTUATION_RANKING = "/uapi/domestic-stock/v1/ranking/fluctuation"
    INVESTOR_RANKING = "/uapi/domestic-stock/v1/ranking/investor-trend"
    MARKET_CAP_RANKING = "/uapi/domestic-stock/v1/ranking/market-cap"
    
    # 업종 정보
    SECTOR_INFO = "/uapi/domestic-stock/v1/quotations/inquire-sector"
    SECTOR_RANKING = "/uapi/domestic-stock/v1/ranking/sector-volume"
    
    # 종목 검색
    STOCK_SEARCH = "/uapi/domestic-stock/v1/quotations/search"

# 거래 ID (TR_ID) 매핑
class TransactionID:
    """거래 ID"""
    
    # 현재가 조회
    CURRENT_PRICE = "FHKST01010100"
    
    # 순위 조회
    VOLUME_RANKING = "FHPST01710000"
    FLUCTUATION_RANKING = "FHPST01700000"
    INVESTOR_RANKING = "FHPST01720000"
    MARKET_CAP_RANKING = "FHPST01730000"
    
    # 업종 정보
    SECTOR_INFO = "FHKST03030100"
    SECTOR_RANKING = "FHPST01740000"
    
    # 종목 검색
    STOCK_SEARCH = "CTPF1604R"

# 업종 코드 매핑 (주요 업종만)
SECTOR_CODE_MAPPING = {
    # 코스피 업종
    "G2510": "반도체",
    "G2520": "전자부품",
    "G2530": "컴퓨터",
    "G2540": "통신장비",
    "G2550": "정보기기",
    "G2560": "소프트웨어",
    "G2570": "게임",
    "G2580": "통신서비스",
    "G2590": "인터넷",
    
    "G3010": "철강",
    "G3020": "조선",
    "G3030": "자동차",
    "G3040": "기계",
    "G3050": "항공",
    "G3060": "건설",
    "G3070": "화학",
    "G3080": "석유화학",
    "G3090": "플라스틱",
    
    "G4010": "금융",
    "G4020": "은행",
    "G4030": "증권",
    "G4040": "보험",
    "G4050": "부동산",
    
    "G5010": "의료기기",
    "G5020": "제약",
    "G5030": "바이오",
    "G5040": "화장품",
    "G5050": "식품",
    "G5060": "유통",
    "G5070": "미디어",
    
    # 코스닥 업종 (일부)
    "K001": "IT",
    "K002": "바이오",
    "K003": "중견기업",
    "K004": "벤처기업"
}

# 에러 코드 매핑
ERROR_CODE_MAPPING = {
    "0": "정상",
    "40010000": "잘못된 요청",
    "40020000": "인증 실패",
    "40030000": "권한 없음",
    "40040000": "리소스를 찾을 수 없음",
    "40050000": "메소드 허용되지 않음",
    "42900000": "요청 한도 초과",
    "50000000": "내부 서버 오류",
    "50030000": "서비스 이용 불가",
    "50040000": "게이트웨이 타임아웃"
}

# 필드 매핑 (한국투자증권 API 응답 필드명 -> 내부 필드명)
STOCK_PRICE_FIELD_MAPPING = {
    "stck_shrn_iscd": "stock_code",        # 종목 코드
    "stck_prpr": "current_price",          # 현재가
    "prdy_vrss": "change",                 # 전일대비
    "prdy_vrss_sign": "change_sign",       # 전일대비 부호
    "prdy_ctrt": "change_rate",            # 전일대비율
    "acml_vol": "volume",                  # 누적거래량
    "acml_tr_pbmn": "trading_value",       # 누적거래대금
    "hts_kor_isnm": "stock_name",          # 종목명
    "stck_mxpr": "max_price",              # 상한가
    "stck_llam": "min_price",              # 하한가
    "stck_oprc": "open_price",             # 시가
    "stck_hgpr": "high_price",             # 고가
    "stck_lwpr": "low_price",              # 저가
    "lstn_stcn": "shares_outstanding",     # 상장주수
    "cpfn": "market_cap",                  # 시가총액
    "w52_hgpr": "week52_high",             # 52주 최고가
    "w52_lwpr": "week52_low",              # 52주 최저가
    "per": "per",                          # PER
    "pbr": "pbr",                          # PBR
    "eps": "eps"                           # EPS
}

VOLUME_RANKING_FIELD_MAPPING = {
    "hts_kor_isnm": "stock_name",          # 종목명
    "mksc_shrn_iscd": "stock_code",        # 종목코드
    "stck_prpr": "current_price",          # 현재가
    "prdy_vrss": "change",                 # 전일대비
    "prdy_vrss_sign": "change_sign",       # 전일대비부호
    "prdy_ctrt": "change_rate",            # 전일대비율
    "acml_vol": "volume",                  # 누적거래량
    "acml_tr_pbmn": "trading_value",       # 누적거래대금
    "lstn_stcn": "shares_outstanding",     # 상장주수
    "stck_mxpr": "max_price",              # 상한가
    "stck_llam": "min_price",              # 하한가
    "cpfn": "market_cap",                  # 시가총액
    "vol_tnrt": "turnover_rate",           # 회전율
    "avls": "available_shares"             # 유통주식수
}

# 기본 설정값
DEFAULT_VALUES = {
    "ranking_count": 20,
    "max_ranking_count": 50,
    "unusual_volume_threshold": 200.0,
    "cache_ttl_seconds": 60,
    "timeout_seconds": 30
}

# 정규식 패턴
PATTERNS = {
    "stock_code": r"^\d{6}$",              # 6자리 숫자
    "date": r"^\d{8}$",                    # YYYYMMDD
    "time": r"^\d{6}$"                     # HHMMSS
}

# 데이터 검증 규칙
VALIDATION_RULES = {
    "stock_code": {
        "pattern": PATTERNS["stock_code"],
        "required": True
    },
    "current_price": {
        "min": 0,
        "required": True
    },
    "volume": {
        "min": 0,
        "required": True
    },
    "trading_value": {
        "min": 0,
        "required": True
    },
    "rank": {
        "min": 1,
        "max": DEFAULT_VALUES["max_ranking_count"],
        "required": True
    }
}

def get_market_code(market: str) -> str:
    """시장명을 시장코드로 변환"""
    return MARKET_CODE_MAPPING.get(market.upper(), MarketCode.ALL.value)

def get_market_name(market_code: str) -> str:
    """시장코드를 시장명으로 변환"""
    return MARKET_NAME_MAPPING.get(market_code, "전체")

def get_investor_screen_code(investor_type: str, trade_type: str) -> str:
    """투자자 유형과 거래 유형으로 화면 코드 획득"""
    return INVESTOR_SCREEN_CODE_MAPPING.get(
        (investor_type.upper(), trade_type.upper()),
        "20174"  # 기본값: 외국인 순매수
    )

def get_sector_name(sector_code: str) -> str:
    """업종 코드를 업종명으로 변환"""
    return SECTOR_CODE_MAPPING.get(sector_code, "기타")

def get_error_message(error_code: str) -> str:
    """에러 코드를 에러 메시지로 변환"""
    return ERROR_CODE_MAPPING.get(error_code, f"알 수 없는 오류 ({error_code})")

def validate_period(period: str) -> str:
    """기간 유효성 검증"""
    from src.exceptions import InvalidParameterError
    
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

def is_valid_stock_code(stock_code: str) -> bool:
    """유효한 종목 코드인지 확인"""
    import re
    return bool(re.match(PATTERNS["stock_code"], stock_code))

def is_market_open() -> bool:
    """장 운영 시간인지 확인"""
    from datetime import datetime, time
    
    now = datetime.now()
    
    # 주말 체크
    if now.weekday() >= 5:  # 토요일(5), 일요일(6)
        return False
    
    # 장 시간 체크 (오전 9시 ~ 오후 3시 30분)
    market_open = time(9, 0)
    market_close = time(15, 30)
    current_time = now.time()
    
    return market_open <= current_time <= market_close