"""
Volume calculation utilities - TDD GREEN Phase
거래대금 계산 유틸리티 - TDD GREEN 단계
"""

from typing import List, Optional
import statistics

def calculate_volume_change_rate(current_volume: int, previous_volume: int) -> float:
    """
    거래대금 증가율 계산
    
    Args:
        current_volume: 현재 거래대금
        previous_volume: 이전 거래대금
    
    Returns:
        증가율 (퍼센트)
    """
    if previous_volume == 0:
        if current_volume > 0:
            return 999999.0  # 무한대 대신 매우 큰 값
        else:
            return 0.0
    
    return ((current_volume - previous_volume) / previous_volume) * 100.0

def calculate_average_volume(volumes: List[int]) -> float:
    """
    평균 거래대금 계산
    
    Args:
        volumes: 거래대금 리스트
    
    Returns:
        평균 거래대금
    """
    if not volumes:
        return 0.0
    
    return statistics.mean(volumes)

def calculate_volume_volatility(volumes: List[int]) -> float:
    """
    거래대금 변동성 계산 (표준편차)
    
    Args:
        volumes: 거래대금 리스트
    
    Returns:
        변동성 (표준편차)
    """
    if len(volumes) < 2:
        return 0.0
    
    return statistics.stdev(volumes)

def calculate_volume_trend(volumes: List[int]) -> str:
    """
    거래대금 트렌드 계산
    
    Args:
        volumes: 시계열 거래대금 리스트 (오래된 것부터)
    
    Returns:
        트렌드 ("increasing", "decreasing", "stable")
    """
    if len(volumes) < 2:
        return "stable"
    
    # 선형 회귀를 간단히 구현
    n = len(volumes)
    x_sum = sum(range(n))
    y_sum = sum(volumes)
    xy_sum = sum(i * volumes[i] for i in range(n))
    x2_sum = sum(i * i for i in range(n))
    
    if n * x2_sum - x_sum * x_sum == 0:
        return "stable"
    
    slope = (n * xy_sum - x_sum * y_sum) / (n * x2_sum - x_sum * x_sum)
    
    if slope > volumes[-1] * 0.05:  # 5% 이상 증가 경향
        return "increasing"
    elif slope < -volumes[-1] * 0.05:  # 5% 이상 감소 경향
        return "decreasing"
    else:
        return "stable"

def normalize_volume_by_market_cap(volume: int, market_cap: int) -> float:
    """
    시가총액 대비 거래대금 비율 계산
    
    Args:
        volume: 거래대금
        market_cap: 시가총액
    
    Returns:
        시가총액 대비 거래대금 비율 (%)
    """
    if market_cap <= 0:
        return 0.0
    
    return (volume / market_cap) * 100.0