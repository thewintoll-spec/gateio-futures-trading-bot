# Gate.io 선물 자동매매 봇

Gate.io 거래소의 USDT 선물 자동매매 봇입니다.

## 주요 기능

- ✅ **테스트넷 지원**: 실제 돈 없이 가상 자금으로 테스트 가능
- 📊 **Grid Trading 전략**: 횡보장에 최적화된 그리드 트레이딩
- 🎯 **멀티 심볼 거래**: BTC_USDT, ETH_USDT 동시 거래
- 💰 **스마트 자본 관리**: 0개 포지션 50%, 1개 포지션 95%, 2개 포지션 대기
- 🔄 **자동 TP/SL**: 동적 익절(3%) 및 손절(2%) 관리
- 📈 **실시간 모니터링**: 가격, 포지션, 손익 실시간 표시
- ⚡ **빠른 반응**: 30초 간격 체크 (단타~중단타 전략)

## 설치 방법

### 1. 패키지 설치
```bash
pip install -r requirements.txt
```

### 2. API 키 설정
```bash
# config.py 파일 생성 (config.example.py를 복사)
cp config.example.py config.py
```

`config.py` 파일을 열어서 다음 정보를 입력하세요:
- **API_KEY**: Gate.io API 키
- **API_SECRET**: Gate.io API 시크릿
- **TESTNET**: `True` (테스트넷) 또는 `False` (실거래)
- **SYMBOL**: 거래할 코인 (예: `ETH_USDT`)
- **LEVERAGE**: 레버리지 배수 (예: `10`)

### 3. 봇 실행
```bash
python main_multi.py
```

## 설정 파일 (config.py)

```python
# Gate.io API 설정
API_KEY = "your_api_key_here"
API_SECRET = "your_api_secret_here"

# 환경 설정
TESTNET = True  # 테스트넷 사용
```

## 전략 설명

### Grid Trading 전략
현재 사용 중인 전략으로, 횡보장에서 안정적인 수익을 목표로 합니다.

**전략 파라미터:**
- Grid 개수: 30개
- 가격 범위: ±10%
- Grid당 이익: 0.3%
- 최대 포지션: 10개
- 리밸런싱 임계값: 7%
- Tight SL: 활성화
- Trend Filter: 활성화 (ADX)
- Dynamic SL: 활성화

**진입 조건:**
- 가격이 Grid 레벨에 도달
- 추세 필터 통과 (ADX 확인)
- 최대 포지션 수 미만

**청산 조건:**
- 익절: +3.0% (동적 조정)
- 손절: -2.0% (타이트 손절)
- Grid 리밸런싱: 7% 이상 변동 시

### 자본 관리
스마트 자본 배분으로 리스크를 관리합니다:
- **0개 포지션**: 50% 자본 사용 (첫 진입)
- **1개 포지션**: 95% 가용 자본 사용 (두번째 진입)
- **2개 포지션**: 대기 (포지션 청산 시까지)

## 파일 구조

```
gateio-futures-bot/
├── main_multi.py              # 메인 실행 파일 (멀티 심볼)
├── exchange.py                # Gate.io API 래퍼
├── grid_strategy.py           # Grid Trading 전략
├── adaptive_strategy.py       # Adaptive Multi-Regime 전략
├── trend_following_strategy.py # Trend Following 전략
├── trade_logger.py            # 거래 로그 기록
├── config.py                  # 설정 파일 (직접 생성)
├── config.example.py          # 설정 파일 예시
├── test_live_vs_backtest.py   # 실전 vs 백테스트 비교
├── backtest/                  # 백테스트 엔진
│   ├── backtest.py
│   └── binance_data_loader.py
└── README.md                  # 이 파일
```

## 테스트넷 사용 방법

1. **Gate.io 테스트넷 가입**: https://testnet.gate.io
2. **테스트넷 API 키 발급**:
   - 테스트넷 로그인 → API 관리 → API 키 생성
   - **Futures Trading 권한 활성화** 필수
3. **config.py 설정**:
   ```python
   TESTNET = True
   API_KEY = "테스트넷_API_키"
   API_SECRET = "테스트넷_API_시크릿"
   ```

## 주의사항

⚠️ **중요한 안내사항**

- 이 봇은 **교육 및 테스트 목적**으로 제작되었습니다
- 실제 거래 시 **손실이 발생**할 수 있습니다
- 반드시 **테스트넷에서 충분히 테스트** 후 사용하세요
- 실거래 시 **소액으로 시작**하세요
- API 키는 **절대 공유하지 마세요**
- config.py 파일은 **.gitignore에 포함**되어 있습니다

## 실전 성과 (2025-10-20 ~ 2025-10-22, 44시간)

**전략:** Grid Trading (최적화 버전)

**결과:**
- 총 거래: 5건
- 승률: 60% (3승 2패)
- 총 수익: **+25.52 USDT**
- Profit Factor: 2.42

**심볼별 성과:**
- ETH_USDT: 4건 (+40.59 USDT, 승률 75%)
- BTC_USDT: 1건 (-11.55 USDT, 승률 0%)

**설정:**
- 레버리지: 2배
- 체크 간격: 30초
- 포지션 홀딩 시간: 30분 ~ 3시간 (단타~중단타)

## 로그 예시

```
============================================================
Gate.io Multi-Symbol Futures Trading Bot Started
Strategy: Grid Trading (Optimized)
Symbols: BTC_USDT, ETH_USDT
Environment: TESTNET
============================================================

[Setup] Setting leverage to 2x for all symbols...
[Balance] Available: 1000.0 USDT
[Balance] Total: 1000.0 USDT

[Status] Active positions: 0/2
[Status] Next trade capital: 50% of available USDT

[ETH_USDT] Price: $3842.43
[GRID] Long signal at grid level 15
  TP: 3.0% | SL: 2.0%

[Trade] Executing ETH_USDT...
[ETH_USDT] Opening LONG position...
[ETH_USDT] LONG order executed successfully!

Waiting 30 seconds...
```

## 문제 해결

### API 연결 오류 (401 Unauthorized)
- API 키와 시크릿이 올바른지 확인
- 테스트넷 키를 사용 중이라면 `TESTNET = True` 확인
- API 권한에서 Futures Trading이 활성화되어 있는지 확인

### CONTRACT_NOT_FOUND 오류
- 심볼 형식이 올바른지 확인 (예: `ETH_USDT`)
- 테스트넷에서 해당 심볼이 지원되는지 확인

## 라이선스

이 프로젝트는 교육 목적으로 제작되었습니다. 사용에 따른 모든 책임은 사용자에게 있습니다.
"# gateio-futures-bot"  
