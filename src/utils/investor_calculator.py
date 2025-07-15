"""
Investor calculation utilities - TDD GREEN Phase
투자자 계산 유틸리티 - TDD GREEN 단계
"""

def calculate_net_trading_amount(buy_amount: int, sell_amount: int) -> int:
    """
    순거래 금액 계산
    
    Args:
        buy_amount: 매수 금액
        sell_amount: 매도 금액
    
    Returns:
        순거래 금액 (매수 - 매도)
    """
    return buy_amount - sell_amount

def calculate_average_trading_price(total_amount: int, total_volume: int) -> float:
    """
    평균 거래가 계산
    
    Args:
        total_amount: 총 거래금액
        total_volume: 총 거래량
    
    Returns:
        평균 거래가
    """
    if total_volume <= 0:
        return 0.0
    
    return total_amount / total_volume

def calculate_market_impact_ratio(investor_amount: int, total_market_amount: int) -> float:
    """
    시장 영향도 계산
    
    Args:
        investor_amount: 투자자 거래금액
        total_market_amount: 전체 시장 거래금액
    
    Returns:
        시장 영향도 (%)
    """
    if total_market_amount <= 0:
        return 0.0
    
    return (abs(investor_amount) / total_market_amount) * 100.0

def calculate_trading_concentration(amounts: list[int]) -> float:
    """
    거래 집중도 계산 (상위 5개 종목 집중도)
    
    Args:
        amounts: 거래금액 리스트 (정렬된 상태)
    
    Returns:
        집중도 (%)
    """
    if not amounts:
        return 0.0
    
    total = sum(amounts)
    if total <= 0:
        return 0.0
    
    top5_total = sum(amounts[:5])
    return (top5_total / total) * 100.0

def calculate_volume_weighted_price(prices: list[float], volumes: list[int]) -> float:
    """
    거래량 가중 평균가 계산
    
    Args:
        prices: 가격 리스트
        volumes: 거래량 리스트
    
    Returns:
        거래량 가중 평균가
    """
    if len(prices) != len(volumes) or not prices:
        return 0.0
    
    total_amount = sum(price * volume for price, volume in zip(prices, volumes))
    total_volume = sum(volumes)
    
    if total_volume <= 0:
        return 0.0
    
    return total_amount / total_volume