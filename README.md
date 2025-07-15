# MCP Volume Ranking Server

한국 주식시장의 거래대금 상위 종목을 실시간으로 조회하고 분석할 수 있는 MCP 서버입니다.

## 🚀 주요 기능

- 거래대금 상위 종목 순위 조회 (전체/코스피/코스닥)
- 시가총액 상위 종목 순위
- 거래량 상위 종목 순위
- 외국인/기관 순매수 상위 종목
- 프로그램 매매 상위 종목
- 업종별 거래대금 순위
- 이상 거래량 감지

## 📋 요구사항

- Python 3.11+
- 한국투자증권 OpenAPI 계정 및 API 키

## 🛠️ 설치 및 설정

### 1. 프로젝트 클론 및 환경 설정

```bash
git clone <repository-url>
cd mcp-volume-ranking

# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 또는
venv\Scripts\activate  # Windows

# 의존성 설치
pip install -r requirements.txt
```

### 2. 환경변수 설정

```bash
# .env.example을 .env로 복사
cp .env.example .env

# .env 파일에서 API 키 설정
KOREA_INVESTMENT_APP_KEY=your_actual_app_key
KOREA_INVESTMENT_APP_SECRET=your_actual_app_secret
```

### 3. 서버 실행

```bash
# MCP 서버 실행
python -m src.server
```

## 🔧 개발 상태

### Phase 1: 기초 인프라 구축 ✅
- [x] 프로젝트 구조 설정
- [x] 가상환경 및 의존성 설치
- [x] 기본 MCP 서버 설정
- [x] 로깅 및 설정 시스템

### Phase 2: 핵심 기능 구현 (진행 예정)
- [ ] 한국투자증권 API 클라이언트 구현
- [ ] 6개 주요 MCP 도구 구현
- [ ] 계층적 캐싱 시스템
- [ ] 순위 계산 로직

### Phase 3: 고도화 (진행 예정)
- [ ] 이상 거래량 감지 기능
- [ ] 성능 최적화
- [ ] 테스트 작성

### Phase 4: 배포 준비 (진행 예정)
- [ ] Docker 컨테이너화
- [ ] 모니터링 시스템
- [ ] 문서화 완성

## 📊 사용 가능한 도구

### 현재 구현된 도구

1. **health_check**
   - 서버 상태 확인
   - 설정 정보 조회

2. **get_volume_ranking** (임시 구현)
   - 거래대금 상위 종목 조회
   - 매개변수: market, count, include_details

### 구현 예정인 도구

- `get_volume_change_ranking`: 거래대금 증가율 순위
- `get_investor_ranking`: 투자자별 거래 순위
- `get_sector_volume_ranking`: 업종별 거래대금 순위
- `get_market_cap_ranking`: 시가총액 순위
- `get_unusual_volume`: 이상 거래량 감지

## 🏗️ 프로젝트 구조

```
mcp-volume-ranking/
├── src/
│   ├── __init__.py
│   ├── server.py              # MCP 서버 메인
│   ├── config.py              # 설정 관리
│   ├── exceptions.py          # 예외 정의
│   ├── tools/                 # MCP 도구 정의
│   │   └── __init__.py
│   ├── api/                   # API 클라이언트
│   │   └── __init__.py
│   └── utils/                 # 유틸리티
│       ├── __init__.py
│       └── logger.py          # 로깅 시스템
├── tests/                     # 테스트
├── logs/                      # 로그 파일
├── requirements.txt
├── .env.example
├── .env
└── README.md
```

## 🔍 테스트

### 헬스체크 테스트

서버가 정상적으로 실행되는지 확인:

```bash
# 서버 실행 후
# MCP 클라이언트에서 health_check 도구 호출
```

## 📝 설정 옵션

주요 환경변수:

- `KOREA_INVESTMENT_APP_KEY`: 한국투자증권 API 키
- `KOREA_INVESTMENT_APP_SECRET`: 한국투자증권 API 시크릿
- `LOG_LEVEL`: 로그 레벨 (DEBUG, INFO, WARNING, ERROR)
- `CACHE_L1_TTL_SECONDS`: L1 캐시 TTL (기본: 60초)
- `CACHE_L2_TTL_SECONDS`: L2 캐시 TTL (기본: 300초)
- `MAX_RANKING_COUNT`: 최대 조회 종목 수 (기본: 50)

## 🚨 주의사항

- 이 프로젝트는 현재 개발 중입니다 (Phase 1 완료)
- 실제 API 연동은 Phase 2에서 구현됩니다
- 현재는 모의 데이터를 반환합니다

## 📞 지원

개발 관련 문의나 이슈는 프로젝트 이슈 트래커를 이용해 주세요.

## 📄 라이센스

이 프로젝트는 MIT 라이센스 하에 배포됩니다.