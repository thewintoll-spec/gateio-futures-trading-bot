# Gate.io 선물 자동매매 봇

Gate.io 거래소의 USDT 선물 자동매매 봇입니다.

## 주요 기능

- ✅ **테스트넷 지원**: 실제 돈 없이 가상 자금으로 테스트 가능
- 📊 **RSI 전략**: RSI 지표 기반 자동 매매
- 💰 **동적 포지션 사이징**: 계좌 잔액의 80%를 사용하여 자동 계산
- 🔄 **자동 포지션 전환**: Long ↔ Short 자동 전환
- 📈 **실시간 모니터링**: 가격, 포지션, 손익 실시간 표시

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
python main.py
```

## 설정 파일 (config.py)

```python
# Gate.io API 설정
API_KEY = "your_api_key_here"
API_SECRET = "your_api_secret_here"

# 환경 설정
TESTNET = True  # 테스트넷 사용

# 거래 설정
SYMBOL = "ETH_USDT"  # 거래 페어
LEVERAGE = 10        # 레버리지
ORDER_SIZE = 0.01    # 주문 크기 (사용 안 함 - 자동 계산됨)

# RSI 전략 설정
RSI_PERIOD = 14      # RSI 계산 기간
RSI_OVERSOLD = 30    # 과매도 기준 (롱 진입)
RSI_OVERBOUGHT = 70  # 과매수 기준 (숏 진입)
```

## 전략 설명

### RSI 전략
- **RSI < 30 (과매도)**: 롱(매수) 포지션 진입
- **RSI > 70 (과매수)**: 숏(매도) 포지션 진입
- **반대 신호 발생 시**: 기존 포지션 청산 후 새 포지션 진입

### 포지션 사이징
- 계좌 전체 잔액(total balance)의 **80%** 사용
- 레버리지를 고려하여 자동 계산
- 포지션이 있어도 일관된 크기로 거래

## 파일 구조

```
gateio-futures-bot/
├── main.py              # 메인 실행 파일
├── exchange.py          # Gate.io API 래퍼
├── strategy.py          # 매매 전략 (RSI, 이동평균)
├── config.py            # 설정 파일 (직접 생성)
├── config.example.py    # 설정 파일 예시
├── requirements.txt     # 필요한 패키지 목록
└── README.md           # 이 파일
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

## 로그 예시

```
==================================================
Gate.io Futures Trading Bot Started
Environment: TESTNET
==================================================

[Setup] Setting leverage to 10x...
[Balance] Available: 3221.46 USDT
[Setup] Trading pair: ETH_USDT
[Setup] Strategy: RSI (14)

==================================================
[2025-10-17 05:09:39]
[Price] ETH_USDT: $2456.78
[Position] LONG | Size: 98765 | Entry: 2450.00 | PnL: 12.3456 USDT
Current RSI: 45.23
[Signal] No trading signal

Waiting 60 seconds...
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
