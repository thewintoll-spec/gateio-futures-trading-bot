"""
Binance Historical Data Loader (API 키 불필요)
"""
import requests
import pandas as pd
from datetime import datetime, timedelta
import time


class BinanceDataLoader:
    """
    Binance에서 과거 데이터 로드 (API 키 불필요)

    공개 API를 사용하므로 무료로 과거 데이터 다운로드 가능
    """

    def __init__(self, symbol='ETHUSDT'):
        """
        Args:
            symbol: Binance 심볼 (예: 'ETHUSDT', 'BTCUSDT')
        """
        self.symbol = symbol
        self.base_url = 'https://fapi.binance.com'  # Futures API

    def fetch_historical_data(self, interval='5m', days=30):
        """
        Binance에서 과거 데이터 가져오기

        Args:
            interval: '1m', '5m', '15m', '1h', '4h', '1d' 등
            days: 가져올 일수

        Returns:
            pandas DataFrame
        """
        print(f"Binance에서 {days}일치 {interval} 데이터 로드 중...")

        # 시간 범위 계산
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)

        all_candles = []

        # Binance API는 최대 1500개씩 반환
        limit = 1500
        current_start = int(start_time.timestamp() * 1000)  # milliseconds
        end_timestamp = int(end_time.timestamp() * 1000)

        request_count = 0
        max_requests = 20  # 안전을 위해 최대 20번 요청

        while current_start < end_timestamp and request_count < max_requests:
            try:
                # Binance Futures Klines API (공개, API 키 불필요)
                url = f"{self.base_url}/fapi/v1/klines"
                params = {
                    'symbol': self.symbol,
                    'interval': interval,
                    'startTime': current_start,
                    'endTime': end_timestamp,
                    'limit': limit
                }

                response = requests.get(url, params=params)
                response.raise_for_status()

                data = response.json()

                if not data:
                    print(f"더 이상 데이터 없음 (요청 {request_count}회)")
                    break

                # 데이터 파싱
                for candle in data:
                    all_candles.append({
                        'timestamp': candle[0] // 1000,  # ms to seconds
                        'open': float(candle[1]),
                        'high': float(candle[2]),
                        'low': float(candle[3]),
                        'close': float(candle[4]),
                        'volume': float(candle[5])
                    })

                request_count += 1
                print(f"요청 {request_count}: {len(data)}개 캔들 로드 (총 {len(all_candles)}개)")

                # 다음 요청 준비
                current_start = data[-1][0] + 1  # 마지막 캔들 시간 + 1ms

                # Rate limit 준수
                time.sleep(0.1)

            except Exception as e:
                print(f"에러 발생: {e}")
                break

        if not all_candles:
            print("데이터를 가져오지 못했습니다!")
            return None

        # DataFrame 변환
        df = pd.DataFrame(all_candles)
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
        df = df.sort_values('datetime')
        df = df.drop_duplicates(subset=['datetime'])
        df = df.reset_index(drop=True)

        print(f"\n총 {len(df)}개 캔들 로드 완료")
        print(f"기간: {df['datetime'].min()} ~ {df['datetime'].max()}")

        market_change = (df.iloc[-1]['close'] - df.iloc[0]['close']) / df.iloc[0]['close'] * 100
        print(f"시장 변동: {market_change:+.2f}%")

        return df

    def save_to_csv(self, df, filename=None):
        """DataFrame을 CSV로 저장"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"data/binance_{self.symbol}_{timestamp}.csv"

        import os
        os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else '.', exist_ok=True)
        df.to_csv(filename, index=False)
        print(f"데이터 저장: {filename}")
        return filename


if __name__ == "__main__":
    # 테스트
    loader = BinanceDataLoader(symbol='ETHUSDT')

    # 30일 데이터 가져오기
    df = loader.fetch_historical_data(interval='5m', days=30)

    if df is not None:
        print("\n처음 5개:")
        print(df.head())
        print("\n마지막 5개:")
        print(df.tail())

        # CSV로 저장
        loader.save_to_csv(df)
