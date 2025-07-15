"""
Data models for Korea Investment Securities API responses
한국투자증권 API 응답 데이터 모델
"""

from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator
from decimal import Decimal

class StockInfo(BaseModel):
    """기본 주식 정보"""
    stock_code: str = Field(..., description="종목 코드")
    stock_name: str = Field(..., description="종목명")
    market_type: str = Field(..., description="시장 구분 (KOSPI/KOSDAQ)")
    
    class Config:
        str_strip_whitespace = True

class PriceInfo(BaseModel):
    """가격 정보"""
    current_price: int = Field(..., description="현재가")
    change: int = Field(..., description="전일 대비 변화")
    change_rate: float = Field(..., description="등락률 (%)")
    
    @field_validator('current_price', 'change')
    @classmethod
    def validate_positive(cls, v):
        if v < 0:
            raise ValueError('Price must be non-negative')
        return v

class VolumeInfo(BaseModel):
    """거래량 정보"""
    volume: int = Field(..., description="거래량")
    trading_value: int = Field(..., description="거래대금")
    turnover_rate: Optional[float] = Field(None, description="회전율 (%)")
    
    @field_validator('volume', 'trading_value')
    @classmethod
    def validate_non_negative(cls, v):
        if v < 0:
            raise ValueError('Volume must be non-negative')
        return v

class MarketCapInfo(BaseModel):
    """시가총액 정보"""
    market_cap: int = Field(..., description="시가총액")
    shares_outstanding: Optional[int] = Field(None, description="상장주식수")
    foreign_ratio: Optional[float] = Field(None, description="외국인 보유비율 (%)")
    
    @field_validator('market_cap')
    @classmethod
    def validate_market_cap(cls, v):
        if v <= 0:
            raise ValueError('Market cap must be positive')
        return v

class FinancialRatios(BaseModel):
    """재무 비율"""
    per: Optional[float] = Field(None, description="주가수익비율")
    pbr: Optional[float] = Field(None, description="주가순자산비율")
    roe: Optional[float] = Field(None, description="자기자본이익률")
    debt_ratio: Optional[float] = Field(None, description="부채비율")

class StockRankingItem(BaseModel):
    """주식 순위 항목"""
    rank: int = Field(..., description="순위")
    stock_info: StockInfo
    price_info: PriceInfo
    volume_info: VolumeInfo
    market_cap_info: Optional[MarketCapInfo] = None
    financial_ratios: Optional[FinancialRatios] = None
    
    @field_validator('rank')
    @classmethod
    def validate_rank(cls, v):
        if v <= 0:
            raise ValueError('Rank must be positive')
        return v

class VolumeChangeInfo(BaseModel):
    """거래대금 변화 정보"""
    current_volume: int = Field(..., description="현재 거래대금")
    previous_volume: int = Field(..., description="비교 기준 거래대금")
    volume_change_rate: float = Field(..., description="거래대금 증가율 (%)")
    comparison_period: str = Field(..., description="비교 기간")
    
class VolumeChangeRankingItem(BaseModel):
    """거래대금 증가율 순위 항목"""
    rank: int = Field(..., description="순위")
    stock_info: StockInfo
    price_info: PriceInfo
    volume_change_info: VolumeChangeInfo
    news_count: Optional[int] = Field(None, description="관련 뉴스 수")
    disclosure_count: Optional[int] = Field(None, description="공시 수")

class InvestorTradingInfo(BaseModel):
    """투자자 거래 정보"""
    buy_amount: int = Field(..., description="매수 금액")
    sell_amount: int = Field(..., description="매도 금액")
    net_amount: int = Field(..., description="순매수 금액")
    buy_volume: int = Field(..., description="매수 거래량")
    sell_volume: int = Field(..., description="매도 거래량")
    net_volume: int = Field(..., description="순매수 거래량")
    average_buy_price: Optional[float] = Field(None, description="평균 매수가")
    average_sell_price: Optional[float] = Field(None, description="평균 매도가")
    impact_ratio: Optional[float] = Field(None, description="전체 거래대금 대비 비율 (%)")
    
    @model_validator(mode='after')
    def validate_net_amounts(self):
        buy_amount = self.buy_amount or 0
        sell_amount = self.sell_amount or 0
        net_amount = self.net_amount or 0
        
        if abs((buy_amount - sell_amount) - net_amount) > 1:  # 반올림 오차 허용
            raise ValueError('Net amount calculation error')
        
        return self

class InvestorRankingItem(BaseModel):
    """투자자별 순위 항목"""
    rank: int = Field(..., description="순위")
    stock_info: StockInfo
    price_info: PriceInfo
    trading_info: InvestorTradingInfo

class LeadingStock(BaseModel):
    """업종 대표 종목"""
    stock_code: str = Field(..., description="종목 코드")
    stock_name: str = Field(..., description="종목명")
    contribution: float = Field(..., description="업종 내 기여도 (%)")

class SectorInfo(BaseModel):
    """업종 정보"""
    sector_code: str = Field(..., description="업종 코드")
    sector_name: str = Field(..., description="업종명")
    stock_count: int = Field(..., description="업종 내 종목 수")

class SectorRankingItem(BaseModel):
    """업종별 순위 항목"""
    rank: int = Field(..., description="순위")
    sector_info: SectorInfo
    trading_value: int = Field(..., description="거래대금")
    trading_volume: int = Field(..., description="거래량")
    average_change_rate: float = Field(..., description="평균 등락률 (%)")
    leading_stocks: List[LeadingStock] = Field(..., description="대표 종목들")
    foreign_net_buy: Optional[int] = Field(None, description="외국인 순매수")
    institution_net_buy: Optional[int] = Field(None, description="기관 순매수")

class UnusualVolumeInfo(BaseModel):
    """이상 거래량 정보"""
    current_volume: int = Field(..., description="현재 거래량")
    average_volume: int = Field(..., description="평균 거래량")
    volume_ratio: float = Field(..., description="평균 대비 비율")
    consecutive_days: int = Field(..., description="연속 이상거래일")
    possible_reasons: List[str] = Field(..., description="가능한 원인들")

class UnusualVolumeItem(BaseModel):
    """이상 거래량 종목"""
    stock_info: StockInfo
    price_info: PriceInfo
    volume_info: VolumeInfo
    unusual_info: UnusualVolumeInfo

class RankingSummary(BaseModel):
    """순위 요약 정보"""
    total_trading_value: int = Field(..., description="전체 거래대금")
    kospi_trading_value: Optional[int] = Field(None, description="코스피 거래대금")
    kosdaq_trading_value: Optional[int] = Field(None, description="코스닥 거래대금")
    top5_concentration: Optional[float] = Field(None, description="상위 5종목 집중도 (%)")
    top10_concentration: Optional[float] = Field(None, description="상위 10종목 집중도 (%)")

class InvestorSummary(BaseModel):
    """투자자별 요약"""
    total_buy_amount: int = Field(..., description="전체 매수 금액")
    total_sell_amount: int = Field(..., description="전체 매도 금액")
    total_net_amount: int = Field(..., description="전체 순매수 금액")
    market_impact: float = Field(..., description="전체 시장 대비 영향도 (%)")

class MarketCapSummary(BaseModel):
    """시가총액 요약"""
    total_market_cap: int = Field(..., description="전체 시가총액")
    average_per: Optional[float] = Field(None, description="평균 PER")
    average_pbr: Optional[float] = Field(None, description="평균 PBR")

class VolumeRankingResponse(BaseModel):
    """거래대금 순위 응답"""
    timestamp: datetime = Field(..., description="조회 시간")
    market: str = Field(..., description="시장 구분")
    ranking: List[StockRankingItem] = Field(..., description="순위 목록")
    summary: RankingSummary = Field(..., description="요약 정보")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class VolumeChangeRankingResponse(BaseModel):
    """거래대금 증가율 순위 응답"""
    timestamp: datetime = Field(..., description="조회 시간")
    period: str = Field(..., description="비교 기간")
    ranking: List[VolumeChangeRankingItem] = Field(..., description="순위 목록")

class InvestorRankingResponse(BaseModel):
    """투자자별 거래 순위 응답"""
    timestamp: datetime = Field(..., description="조회 시간")
    investor_type: str = Field(..., description="투자자 유형")
    trade_type: str = Field(..., description="거래 유형")
    ranking: List[InvestorRankingItem] = Field(..., description="순위 목록")
    summary: InvestorSummary = Field(..., description="요약 정보")

class SectorVolumeRankingResponse(BaseModel):
    """업종별 거래대금 순위 응답"""
    timestamp: datetime = Field(..., description="조회 시간")
    market: str = Field(..., description="시장 구분")
    ranking: List[SectorRankingItem] = Field(..., description="순위 목록")

class MarketCapRankingResponse(BaseModel):
    """시가총액 순위 응답"""
    timestamp: datetime = Field(..., description="조회 시간")
    market: str = Field(..., description="시장 구분")
    ranking: List[StockRankingItem] = Field(..., description="순위 목록")
    summary: MarketCapSummary = Field(..., description="요약 정보")

class UnusualVolumeResponse(BaseModel):
    """이상 거래량 응답"""
    timestamp: datetime = Field(..., description="조회 시간")
    detection_criteria: Dict[str, Any] = Field(..., description="감지 기준")
    unusual_stocks: List[UnusualVolumeItem] = Field(..., description="이상 거래량 종목들")

# API 원시 응답 모델 (한국투자증권 API 직접 응답)
class KoreaInvestmentAPIResponse(BaseModel):
    """한국투자증권 API 원시 응답"""
    rt_cd: str = Field(..., description="응답 코드")
    msg_cd: str = Field(..., description="메시지 코드")
    msg1: str = Field(..., description="메시지")
    output: Optional[List[Dict[str, Any]]] = Field(None, description="출력 데이터")
    output1: Optional[List[Dict[str, Any]]] = Field(None, description="출력 데이터1")
    output2: Optional[Dict[str, Any]] = Field(None, description="출력 데이터2")
    
    @property
    def is_success(self) -> bool:
        """성공 여부"""
        return self.rt_cd == "0"
    
    @property
    def error_message(self) -> str:
        """에러 메시지"""
        if self.is_success:
            return ""
        return f"Error {self.msg_cd}: {self.msg1}"

# 이상 거래량 관련 모델들

class VolumeAnalysis(BaseModel):
    """거래량 분석 정보"""
    volume_ratio: float = Field(..., description="거래량 비율 (평균 대비 %)")
    average_volume: int = Field(..., description="평균 거래량")
    anomaly_score: float = Field(..., description="이상 점수 (0-5)")
    pattern: str = Field(..., description="거래량 패턴")
    detection_time: datetime = Field(..., description="감지 시간")
    
    @field_validator('volume_ratio')
    @classmethod
    def validate_volume_ratio(cls, v):
        if v < 0:
            raise ValueError('Volume ratio must be non-negative')
        return v
    
    @field_validator('anomaly_score')
    @classmethod
    def validate_anomaly_score(cls, v):
        if not 0 <= v <= 5:
            raise ValueError('Anomaly score must be between 0 and 5')
        return v

class UnusualVolumeItem(BaseModel):
    """이상 거래량 항목"""
    rank: int = Field(..., description="순위")
    stock_info: StockInfo = Field(..., description="종목 정보")
    price_info: PriceInfo = Field(..., description="가격 정보")
    volume_info: VolumeInfo = Field(..., description="거래량 정보")
    volume_analysis: VolumeAnalysis = Field(..., description="거래량 분석")

class UnusualVolumeSummary(BaseModel):
    """이상 거래량 요약"""
    total_detected: int = Field(..., description="감지된 총 종목 수")
    high_anomaly_count: int = Field(..., description="고위험 이상 거래량 종목 수")
    average_volume_ratio: float = Field(..., description="평균 거래량 비율")
    max_volume_ratio: float = Field(..., description="최고 거래량 비율")

class UnusualVolumeResponse(BaseModel):
    """이상 거래량 응답"""
    timestamp: datetime = Field(..., description="조회 시간")
    market: str = Field(..., description="시장 구분")
    threshold: float = Field(..., description="임계값")
    unusual_items: List[UnusualVolumeItem] = Field(default_factory=list, description="이상 거래량 항목들")
    summary: Optional[UnusualVolumeSummary] = Field(None, description="요약 정보")