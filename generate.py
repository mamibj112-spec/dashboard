#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
국장 데일리 대시보드 자동 생성기
Usage: python generate.py
"""
import sys
import json
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

# Windows 콘솔(cp949)에서 이모지 등 출력 시 UnicodeEncodeError로 죽는 것을 방지
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

try:
    import yfinance as yf
    import requests
    import feedparser
    import pytz
except ImportError as e:
    print(f"패키지 없음: {e}")
    print("먼저 실행: pip install -r requirements.txt")
    sys.exit(1)

KST = pytz.timezone('Asia/Seoul')

# ── 날짜 ──────────────────────────────────────────────────────────────────────

def now_kst():
    return datetime.now(KST)

def korean_date(dt):
    days = ['월요일','화요일','수요일','목요일','금요일','토요일','일요일']
    return f"{dt.year}년 {dt.month}월 {dt.day}일 {days[dt.weekday()]}"

# ── 시장 데이터 ────────────────────────────────────────────────────────────────

TICKERS = {
    'kospi':  '^KS11',
    'kosdaq': '^KQ11',
    'sp500':  '^GSPC',
    'dow':    '^DJI',
    'nasdaq': '^NDX',
    'nikkei': '^N225',
    'usdkrw': 'KRW=X',
    'brent':  'BZ=F',
    'wti':    'CL=F',
    'gold':   'GC=F',
    'tnx':    '^TNX',
    'dxy':    'DX-Y.NYB',
    'btc':    'BTC-USD',
    'vix':    '^VIX',
    'rut':    '^RUT',
    'soxx':   'SOXX',
    'xlk':    'XLK',
    'xle':    'XLE',
    'xlv':    'XLV',
    'xlp':    'XLP',
    'xly':    'XLY',
    'xlf':    'XLF',
    'xli':    'XLI',
    'xlb':    'XLB',
    'xlre':   'XLRE',
    'xlu':    'XLU',
    'xlc':    'XLC',
    'tlt':    'TLT',
    'ief':    'IEF',
    'shy':    'SHY',
    'gld':    'GLD',
    'uso':    'USO',
    'slv':    'SLV',
    'unh':    'UNH',
    'avgo':   'AVGO',
    'anet':   'ANET',
    'wmt':    'WMT',
    'arm':    'ARM',
    'pfe':    'PFE',
    'panw':   'PANW',
    'intc':   'INTC',
    'nvda':   'NVDA',
    'aapl':   'AAPL',
    'msft':   'MSFT',
    'meta':   'META',
    'googl':  'GOOGL',
    'amzn':   'AMZN',
    'tsla':   'TSLA',
}

MAG7_MAP = {
    'nvda': '엔비디아', 'aapl': '애플', 'msft': '마이크로소프트', 'googl': '알파벳',
    'amzn': '아마존', 'meta': '메타', 'tsla': '테슬라',
}

US_SECTOR_MAP = {
    'xlk': 'IT/기술', 'xlc': '통신서비스', 'xle': '에너지', 'xlv': '헬스케어', 'xlp': '필수소비재',
    'xly': '경기소비재', 'xlf': '금융', 'xli': '산업재', 'xlb': '소재',
    'xlre': '부동산', 'xlu': '유틸리티'
}
US_BOND_MAP = {
    'tlt': ('TLT', '장기채'), 'ief': ('IEF', '중기채'), 'shy': ('SHY', '단기채'),
}
US_COMMODITY_MAP = {
    'gld': ('GLD', '금'), 'uso': ('USO', '원유'), 'slv': ('SLV', '은'),
}
US_STOCK_MAP = {
    'unh': '유나이티드헬스', 'avgo': '브로드컴', 'anet': '아리스타', 'wmt': '월마트',
    'arm': 'ARM', 'pfe': '화이자', 'panw': '팔로알토', 'intc': '인텔',
    'nvda': '엔비디아', 'aapl': '애플', 'msft': '마이크로소프트', 'meta': '메타'
}

# TradingView 차트 연결용 거래소 매핑 (Mag7 + US_STOCK_MAP 종목)
US_EXCHANGE_MAP = {
    'nvda': 'NASDAQ', 'aapl': 'NASDAQ', 'msft': 'NASDAQ', 'googl': 'NASDAQ',
    'amzn': 'NASDAQ', 'meta': 'NASDAQ', 'tsla': 'NASDAQ', 'avgo': 'NASDAQ',
    'arm': 'NASDAQ', 'panw': 'NASDAQ', 'intc': 'NASDAQ',
    'unh': 'NYSE', 'anet': 'NYSE', 'wmt': 'NYSE', 'pfe': 'NYSE',
}

# 관심 종목 목록 — 티커/이름/시장(US or KR)
WATCHLIST = [
    {'ticker': 'SNDK',    'name': '샌디스크',   'market': 'US'},
]

MAJOR_ETFS = [
    {'name': 'KODEX 200',             'ticker': '069500'},
    {'name': 'KODEX 레버리지',         'ticker': '122630'},
    {'name': 'KODEX 인버스',           'ticker': '114800'},
    {'name': 'KODEX 코스닥150',        'ticker': '229200'},
    {'name': 'TIGER 미국S&P500',       'ticker': '360750'},
]

THEME_ETFS = [
    {'theme': '🔬 반도체',  'etfs': [
        {'name': 'KODEX 반도체',       'ticker': '091160'},
        {'name': 'TIGER 반도체',       'ticker': '091230'},
    ]},
    {'theme': '🔋 2차전지', 'etfs': [
        {'name': 'KODEX 2차전지산업',  'ticker': '305720'},
        {'name': 'TIGER 2차전지테마',  'ticker': '305540'},
    ]},
    {'theme': '🤖 AI·로봇', 'etfs': [
        {'name': 'KODEX AI&로보틱스',  'ticker': '427270'},
        {'name': 'TIGER AI반도체',     'ticker': '483150'},
    ]},
    {'theme': '🇺🇸 미국',   'etfs': [
        {'name': 'TIGER 미국S&P500',       'ticker': '360750'},
        {'name': 'KODEX 미국나스닥100TR',  'ticker': '379800'},
    ]},
]

POPULAR_ETFS = [
    {'name': 'KODEX 200',             'ticker': '069500'},
    {'name': 'KODEX 레버리지',         'ticker': '122630'},
    {'name': 'KODEX 인버스',           'ticker': '114800'},
    {'name': 'TIGER 미국S&P500',       'ticker': '360750'},
    {'name': 'KODEX 2차전지산업',      'ticker': '305720'},
    {'name': 'KODEX 반도체',           'ticker': '091160'},
    {'name': 'KODEX 골드선물(H)',      'ticker': '132030'},
    {'name': 'KODEX 미국나스닥100TR',  'ticker': '379800'},
]

def calculate_rsi(prices, period=14):
    """RSI(상대강도지수) 계산"""
    if len(prices) < period + 1:
        return 50
    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0: return 100
    rs = avg_gain / avg_loss
    return int(100 - (100 / (1 + rs)))

def fetch_market():
    print("시장 데이터 수집 중...")
    data = {}
    for name, sym in TICKERS.items():
        try:
            t = yf.Ticker(sym)
            hist = t.history(period='1mo', auto_adjust=True)
            hist = hist.dropna(subset=['Close'])
            if len(hist) >= 2:
                prices = hist['Close'].tolist()
                prev = float(prices[-2])
                curr = float(prices[-1])
                chg = curr - prev
                pct = chg / prev * 100 if prev != 0 else 0
                rsi = calculate_rsi(prices)
                data[name] = {'val': curr, 'chg': chg, 'pct': pct, 'rsi': rsi, 'ok': True}
            elif len(hist) == 1:
                data[name] = {'val': float(hist['Close'].iloc[-1]), 'chg': 0, 'pct': 0, 'rsi': 50, 'ok': False}
            else:
                data[name] = {'val': None, 'chg': None, 'pct': None, 'rsi': 50, 'ok': False}
        except Exception as e:
            print(f"  [{name}] 오류: {e}")
            data[name] = {'val': None, 'chg': None, 'pct': None, 'rsi': 50, 'ok': False}

    # KIS로 KOSPI/KOSDAQ 현재가 보정 (yfinance보다 정확한 한국 시장 데이터)
    try:
        import kis_api
        token = kis_api.get_token()
        if token:
            for key, code in [('kospi', '0001'), ('kosdaq', '1001')]:
                kis_data = kis_api.get_index_price(token, code)
                if kis_data and kis_data['ok']:
                    existing = data.get(key, {})
                    rsi = existing.get('rsi', 50)
                    # 장 마감/주말엔 KIS chg·pct가 0 → yfinance 값 유지
                    chg = kis_data['chg'] if kis_data['chg'] != 0 else existing.get('chg', 0)
                    pct = kis_data['pct'] if kis_data['pct'] != 0 else existing.get('pct', 0)
                    data[key] = {'val': kis_data['val'], 'chg': chg, 'pct': pct, 'rsi': rsi, 'ok': True}
                    print(f"  [{key}] KIS 보정: {kis_data['val']:.2f} ({pct:+.2f}%)")
    except Exception as e:
        print(f"  KIS 지수 보정 오류: {e}")

    return data


# ── 주도주 & 시장 체감 ─────────────────────────────────────────────────────────

def fetch_market_stocks():
    """주도주/체감 데이터 수집 (KIS 랭킹 우선, FDR fallback)"""
    import FinanceDataReader as fdr
    import pandas as pd

    print("  주도주/체감 데이터 수집 중...")

    # KIS로 거래대금/등락률 상위 종목 조회 (장중에만 유효 데이터 반환)
    kis_top_amt   = []
    kis_top_gain  = []
    kis_top_decline = []
    try:
        import kis_api
        token = kis_api.get_token()
        if token:
            raw_amt     = kis_api.get_volume_ranking(token, top_n=5)
            raw_gain    = kis_api.get_fluctuation_ranking(token, top_n=5)
            raw_decline = kis_api.get_decline_ranking(token, top_n=5)
            # 장 마감 후엔 Amount가 0 — 유효 데이터만 사용
            kis_top_amt     = [x for x in raw_amt     if x.get('Amount', 0) > 0]
            kis_top_gain    = [x for x in raw_gain    if x.get('Amount', 0) > 0]
            kis_top_decline = [x for x in raw_decline if x.get('Amount', 0) > 0]
            if kis_top_amt:
                print(f"  KIS 거래대금 상위 수집 완료: {len(kis_top_amt)}개")
            if kis_top_gain:
                print(f"  KIS 급등주 수집 완료: {len(kis_top_gain)}개")
            if kis_top_decline:
                print(f"  KIS 급락주 수집 완료: {len(kis_top_decline)}개")
    except Exception as e:
        print(f"  KIS 랭킹 오류: {e}")

    # KIS 외국인/기관 순매수, 신고가 수집
    kis_foreign_buy = []
    kis_inst_buy    = []
    kis_high        = []
    try:
        if token:
            raw_foreign = kis_api.get_foreign_net_buy_ranking(token, top_n=5)
            raw_inst    = kis_api.get_institutional_net_buy_ranking(token, top_n=5)
            raw_high    = kis_api.get_52week_high(token, top_n=5)
            kis_foreign_buy = [x for x in raw_foreign if x.get('Amount', 0) > 0]
            kis_inst_buy    = [x for x in raw_inst    if x.get('Amount', 0) > 0]
            kis_high        = [x for x in raw_high    if x.get('Close', 0) > 0]
            if kis_foreign_buy:
                print(f"  KIS 외국인 순매수 수집 완료: {len(kis_foreign_buy)}개")
            if kis_inst_buy:
                print(f"  KIS 기관 순매수 수집 완료: {len(kis_inst_buy)}개")
            if kis_high:
                print(f"  KIS 신고가 수집 완료: {len(kis_high)}개")
    except Exception as e:
        print(f"  KIS 추가 랭킹 오류: {e}")

    # FDR로 시장 체감 온도 (상승/하락 종목 수) 수집
    up = down = flat = 0
    fdr_top_amt     = []
    fdr_top_gain    = []
    fdr_top_decline = []
    fdr_top_rise    = []
    try:
        kospi  = fdr.StockListing('KOSPI')
        kosdaq = fdr.StockListing('KOSDAQ')
        all_s  = pd.concat([kospi, kosdaq], ignore_index=True)
        all_s  = all_s.dropna(subset=['Amount', 'ChagesRatio', 'Close', 'Name'])
        all_s  = all_s[(all_s['Close'] > 0) & (all_s['Amount'] > 0)]

        up   = int((all_s['ChagesRatio'] > 0).sum())
        down = int((all_s['ChagesRatio'] < 0).sum())
        flat = int((all_s['ChagesRatio'] == 0).sum())

        fdr_top_amt     = all_s.nlargest(5, 'Amount')[['Name','Close','ChagesRatio','Amount','Market','Code']].to_dict('records')
        gainers         = all_s[(all_s['ChagesRatio'] > 0) & (all_s['ChagesRatio'] <= 30)]
        fdr_top_gain    = gainers.nlargest(5, 'ChagesRatio')[['Name','Close','ChagesRatio','Amount','Market','Code']].to_dict('records')
        losers          = all_s[(all_s['ChagesRatio'] < 0) & (all_s['ChagesRatio'] >= -30)]
        fdr_top_decline = losers.nsmallest(5, 'ChagesRatio')[['Name','Close','ChagesRatio','Amount','Market','Code']].to_dict('records')
        # 상승률 상위: 상한가 포함 전체 상승 종목
        fdr_top_rise    = all_s[all_s['ChagesRatio'] > 0].nlargest(5, 'ChagesRatio')[['Name','Close','ChagesRatio','Amount','Market','Code']].to_dict('records')
        print(f"  FDR 체감 수집 완료: 상승 {up} / 하락 {down}")
    except Exception as e:
        print(f"  FDR 주도주 오류: {e}")

    top_amt     = kis_top_amt     if kis_top_amt     else fdr_top_amt
    top_gain    = kis_top_gain    if kis_top_gain    else fdr_top_gain
    top_decline = kis_top_decline if kis_top_decline else fdr_top_decline

    if not top_amt and not top_gain:
        return None

    return {
        'breadth':     {'up': up, 'down': down, 'flat': flat},
        'top_amt':     top_amt,
        'top_gain':    top_gain,
        'top_decline': top_decline,
        'foreign_buy': kis_foreign_buy,
        'inst_buy':    kis_inst_buy,
        'high_52w':    kis_high,
        'top_rise':    fdr_top_rise,
    }


def fetch_kr_sectors():
    """KIS API로 KOSPI 주요 업종별 등락률 수집. 장 마감/주말엔 빈 리스트 반환"""
    try:
        import kis_api
        token = kis_api.get_token()
        if not token:
            return []
        sectors = kis_api.get_kr_sector_data(token)
        # 장 마감/주말엔 전부 0 → 의미 없으므로 빈 리스트 반환
        if all(s['pct'] == 0.0 for s in sectors):
            print("  업종 데이터 장 마감 후 (fallback 사용)")
            return []
        print(f"  KIS 업종 {len(sectors)}개 수집 완료")
        return sectors
    except Exception as e:
        print(f"  업종 데이터 오류: {e}")
        return []


def fetch_usdkrw_week():
    """USD/KRW 최근 7일 종가 리스트 반환"""
    try:
        t = yf.Ticker('KRW=X')
        hist = t.history(period='14d', auto_adjust=True)
        hist = hist.dropna(subset=['Close'])
        closes = [round(float(v), 0) for v in hist['Close'].tail(7).tolist()]
        if len(closes) < 2:
            return None
        print(f"  환율 추이 수집 완료: {closes}")
        return closes
    except Exception as e:
        print(f"  환율 추이 오류: {e}")
        return None


def calc_fear_greed(market, stocks):
    """한국 시장 데이터 기반 공포/탐욕 지수 계산 (0~100)"""
    components = []
    # 1. 시장 폭: 상승종목 / (상승+하락) (50%)
    if stocks:
        breadth = stocks.get('breadth', {})
        up   = breadth.get('up', 0)
        down = breadth.get('down', 0)
        total = up + down
        if total > 0:
            components.append((up / total * 100, 0.5))
    # 2. 코스피 모멘텀 (30%): 0% → 50, ±5% → 100/0
    kospi_pct  = d(market, 'kospi').get('pct') or 0
    components.append((min(max(50 + kospi_pct * 10, 0), 100), 0.3))
    # 3. 코스닥 상대강도 (20%): 코스닥-코스피 괴리
    kosdaq_pct = d(market, 'kosdaq').get('pct') or 0
    rel = kosdaq_pct - kospi_pct
    components.append((min(max(50 + rel * 10, 0), 100), 0.2))
    if not components:
        return 50
    total_w = sum(w for _, w in components)
    score   = sum(s * w for s, w in components) / total_w
    return int(round(min(max(score, 0), 100)))


def calc_us_fear_greed(market):
    """미국 시장 데이터 기반 공포/탐욕 지수 계산 (0~100)"""
    components = []
    # 1. VIX (30%): 20 -> 50, 40 -> 0, 10 -> 100
    vix = d(market, 'vix').get('val')
    if vix:
        score = max(0, min(100, 100 - (vix - 12) * (100 / 28)))
        components.append((score, 0.3))
    # 2. S&P 500 RSI (40%): RSI 그대로 사용
    sp500_rsi = d(market, 'sp500').get('rsi')
    if sp500_rsi:
        components.append((sp500_rsi, 0.4))
    # 3. 나스닥 모멘텀 (30%): ±2% -> 100/0, 0% -> 50
    nasdaq_pct = d(market, 'nasdaq').get('pct') or 0
    components.append((min(max(50 + nasdaq_pct * 25, 0), 100), 0.3))

    if not components: return 50
    total_w = sum(w for _, w in components)
    score = sum(s * w for s, w in components) / total_w
    return int(round(score))


def fetch_cnn_fear_greed():
    """CNN Fear & Greed Index 실제 값 조회 (0~100)"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36',
            'Accept': 'application/json',
        }
        r = requests.get('https://production.dataviz.cnn.io/index/fearandgreed/graphdata', headers=headers, timeout=10)
        r.raise_for_status()
        score = r.json()['fear_and_greed']['score']
        return int(round(score))
    except Exception as e:
        print(f"  CNN 공포/탐욕 지수 오류: {e}")
        return None


MACRO_HISTORY_TICKERS = {
    'kospi':  '^KS11',
    'kosdaq': '^KQ11',
    'sp500':  '^GSPC',
    'nasdaq': '^NDX',
    'dow':    '^DJI',
    'vix':    '^VIX',
    'usdkrw': 'KRW=X',
    'brent':  'BZ=F',
    'wti':    'CL=F',
    'tnx':    '^TNX',
    'gold':   'GC=F',
    'dxy':    'DX-Y.NYB',
    'btc':    'BTC-USD',
}

_HIST_DEC = {
    'kospi':2,'kosdaq':2,'sp500':2,'nasdaq':2,'dow':2,'vix':2,
    'usdkrw':0,'brent':1,'wti':1,'tnx':2,'gold':0,'dxy':2,'btc':0
}

def fetch_macro_history():
    """매크로 지표 최근 2주 OHLC 데이터"""
    print("매크로 추이 데이터 수집 중...")
    result = {}
    for key, sym in MACRO_HISTORY_TICKERS.items():
        try:
            t = yf.Ticker(sym)
            hist = t.history(period='30d', auto_adjust=True)
            hist = hist.dropna(subset=['Close'])
            tail = hist.tail(14)
            dec = _HIST_DEC.get(key, 2)
            candles = []
            for idx, row in tail.iterrows():
                candles.append({
                    'time': idx.strftime('%Y-%m-%d'),
                    'open':  round(float(row['Open']),  dec),
                    'high':  round(float(row['High']),  dec),
                    'low':   round(float(row['Low']),   dec),
                    'close': round(float(row['Close']), dec),
                })
            if len(candles) >= 2:
                result[key] = candles
        except Exception as e:
            print(f"  [{key}] 추이 오류: {e}")
    return result


def fear_greed_html(value=62):
    """공포/탐욕 반원 게이지 카드 HTML"""
    import math
    if value <= 25:
        color = '#3b82f6'; label = '극공포'
    elif value <= 45:
        color = '#60a5fa'; label = '공포'
    elif value <= 55:
        color = '#a3a3a3'; label = '중립'
    elif value <= 75:
        color = '#f97316'; label = '탐욕'
    else:
        color = '#ef4444'; label = '극탐욕'
    angle = math.pi * (1 - value / 100)
    nx = round(60 + 50 * math.cos(angle), 1)
    ny = round(60 - 50 * math.sin(angle), 1)
    return f'''<div style="background:var(--card);border-radius:10px;padding:10px 12px;">
      <div style="font-size:10px;color:var(--t3);text-transform:uppercase;letter-spacing:.8px;margin-bottom:4px;">국내 공포/탐욕</div>
      <svg viewBox="0 0 120 65" style="width:100%;display:block;overflow:visible;">
        <path d="M 10 60 A 50 50 0 0 1 24.6 24.6" fill="none" stroke="#3b82f6" stroke-width="10" stroke-linecap="butt"/>
        <path d="M 24.6 24.6 A 50 50 0 0 1 52.2 10.6" fill="none" stroke="#60a5fa" stroke-width="10" stroke-linecap="butt"/>
        <path d="M 52.2 10.6 A 50 50 0 0 1 67.8 10.6" fill="none" stroke="#a3a3a3" stroke-width="10" stroke-linecap="butt"/>
        <path d="M 67.8 10.6 A 50 50 0 0 1 95.4 24.6" fill="none" stroke="#f97316" stroke-width="10" stroke-linecap="butt"/>
        <path d="M 95.4 24.6 A 50 50 0 0 1 110 60" fill="none" stroke="#ef4444" stroke-width="10" stroke-linecap="butt"/>
        <line x1="60" y1="60" x2="{nx}" y2="{ny}" stroke="#fff" stroke-width="2" stroke-linecap="round"/>
        <circle cx="60" cy="60" r="3.5" fill="#fff"/>
      </svg>
      <div style="text-align:center;margin-top:2px;">
        <span style="font-size:18px;font-weight:700;color:{color};">{value}</span>
        <span style="font-size:11px;color:{color};font-weight:600;margin-left:4px;">{label}</span>
      </div>
    </div>'''


def stocks_html(rows):
    if not rows:
        return '<div style="color:var(--t3);font-size:12px;padding:8px 0;">데이터 없음</div>'
    out = ''
    for r in rows:
        name = str(r.get('Name', ''))[:10]
        code = str(r.get('Code', '') or '')
        pct  = float(r.get('ChagesRatio', 0) or 0)
        amt  = r.get('Amount', 0) or 0
        mkt  = str(r.get('Market', ''))
        cls  = 'up-txt' if pct >= 0 else 'dn-txt'
        sign = '▲' if pct >= 0 else '▼'
        amt_str = f"{amt/100000000:.0f}억" if amt >= 100000000 else f"{amt/100000000:.1f}억"
        mkt_badge = '<span style="font-size:9px;color:var(--t3);margin-left:3px;">Q</span>' if 'KOSDAQ' in mkt else ''
        clickable = code.isdigit() and len(code) == 6
        name_attrs = f' onclick="openChart(\'KRX:{code}\')" style="cursor:pointer"' if clickable else ''
        chart_ico = f' <span onclick="openChart(\'KRX:{code}\')" style="cursor:pointer;font-size:9px">📈</span>' if clickable else ''
        out += f'''<div class="stock-row">
  <div class="stock-name"{name_attrs}>{name}{mkt_badge}</div>
  <div class="stock-right">
    {chart_ico}
    <span class="{cls}">{sign}{abs(pct):.1f}%</span>
    <span class="stock-amt">{amt_str}</span>
  </div>
</div>'''
    return out


# ── Gemini 공통 호출 헬퍼 ─────────────────────────────────────────────────────
import threading as _threading, time as _time, collections as _collections

class _GeminiRateLimiter:
    """호출 간격을 강제해 429가 구조적으로 발생하지 않도록 함 (10 RPM = 6초 간격)"""
    def __init__(self, rpm=10):
        self._lock = _threading.Lock()
        self._timestamps = _collections.deque()
        self._interval = 60.0 / rpm  # 6초
        self._rpm = rpm

    def acquire(self):
        with self._lock:
            now = _time.time()
            # 1분 이상 된 기록 제거
            while self._timestamps and now - self._timestamps[0] > 60:
                self._timestamps.popleft()
            # 분당 한도 초과 시 대기
            if len(self._timestamps) >= self._rpm:
                sleep = 60 - (now - self._timestamps[0]) + 0.5
                print(f"  Gemini rate limit 예방 대기 {sleep:.0f}초...")
                _time.sleep(sleep)
                now = _time.time()
            # 최소 호출 간격 보장
            if self._timestamps:
                elapsed = now - self._timestamps[-1]
                if elapsed < self._interval:
                    _time.sleep(self._interval - elapsed)
            self._timestamps.append(_time.time())

_GEMINI_LIMITER = _GeminiRateLimiter(rpm=10)

def _gemini_post(api_key, prompt, temperature=0.7, max_tokens=1024):
    """Gemini API 호출 (Rate Limiter로 429 원천 차단)"""
    url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}'
    body = {'contents': [{'parts': [{'text': prompt}]}],
            'generationConfig': {'temperature': temperature, 'maxOutputTokens': max_tokens,
                                 'thinkingConfig': {'thinkingBudget': 0}}}
    _GEMINI_LIMITER.acquire()
    resp = requests.post(url, json=body, timeout=60)
    resp.raise_for_status()
    parts = resp.json()['candidates'][0]['content']['parts']
    return next((p['text'] for p in parts if 'text' in p), '').strip()


# ── AI 브리핑 ──────────────────────────────────────────────────────────────────

def fetch_ai_briefing(market, news):
    """Gemini API로 오늘 장 AI 브리핑 생성"""
    import os
    api_key = os.environ.get('GEMINI_API_KEY', '').strip()
    if not api_key:
        print("  GEMINI_API_KEY 없음, AI 브리핑 스킵")
        return None
    try:
        print("  AI 브리핑 생성 중...")

        def mv(name):
            item = d(market, name)
            v, pct = item.get('val'), item.get('pct') or 0
            if v is None: return 'N/A'
            sign = '▲' if pct >= 0 else '▼'
            return f"{v:,.2f} ({sign}{abs(pct):.2f}%)"

        headlines = []
        for cat in ['domestic', 'hot', 'international']:
            for item in news.get(cat, [])[:4]:
                headlines.append(item['title'])

        prompt = f"""오늘 한국 주식시장 데이터 (장 마감 기준):
- 코스피: {mv('kospi')}
- 코스닥: {mv('kosdaq')}
- 나스닥: {mv('nasdaq')}
- S&P500: {mv('sp500')}
- USD/KRW: {mv('usdkrw')}
- 미 10년물 금리: {mv('tnx')}
- 브렌트유: {mv('brent')}
- WTI: {mv('wti')}
- 금: {mv('gold')}
- 비트코인: {mv('btc')}

오늘 주요 뉴스:
{chr(10).join(f"- {h}" for h in headlines[:12])}

위 데이터를 바탕으로 단순 나열이 아닌, 지표 간 인과관계와 스토리가 있는 시황 분석을 작성하세요.
부동산 내용은 절대 포함하지 마세요. 주식 시장만 분석하세요.
한국어 뉴스레터 형식으로 작성하며, 투자자들이 오늘 무엇에 집중해야 했는지 명확히 설명하세요.
아래 JSON 형식으로만 응답하세요. 다른 텍스트는 절대 포함하지 마세요.
{{
  "keyword": "오늘의 핵심 키워드 한 줄 (이모지 포함, 20자 이내)",
  "hashtags": ["오늘 한국 시장을 한눈에 보여주는 해시태그 5개 (예: #외국인 순매수 형식, # 포함, 각 12자 이내)"],
  "highlights": [
    {{"title": "오늘의 핵심 이슈 제목 (12자 이내)", "desc": "그 이슈에 대한 한 줄 설명 (35자 이내)"}},
    {{"title": "두 번째 핵심 이슈 제목 (12자 이내)", "desc": "그 이슈에 대한 한 줄 설명 (35자 이내)"}},
    {{"title": "세 번째 핵심 이슈 제목 (12자 이내)", "desc": "그 이슈에 대한 한 줄 설명 (35자 이내)"}}
  ],
  "story": "주요 지표 움직임의 원인과 연결고리 설명 (2~3문장, 인과관계 중심)",
  "sector_story": "업종별 등락 스토리 (왜 올랐고 왜 내렸는지 흐름 설명, 2~3문장)",
  "outlook": "내일 이후 주목해야 할 이벤트나 투자 포인트 (2문장)"
}}"""

        import json, re
        text = _gemini_post(api_key, prompt, temperature=0.7, max_tokens=2048)
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if m:
            data = json.loads(m.group(0))
            print(f"  AI 브리핑 완료")
            return data
        print(f"  AI 브리핑 JSON 파싱 실패: {text[:100]}")
        return None
    except Exception as e:
        print(f"  AI 브리핑 오류: {e}")
        return None


def fetch_us_recent_earnings():
    """Finnhub API로 최근 2주 미국 실적 발표 데이터 수집"""
    import os, requests
    from datetime import datetime, timedelta
    key = os.environ.get('FINNHUB_API_KEY', '').strip()
    if not key:
        return []
    try:
        today = datetime.now()
        frm = (today - timedelta(days=14)).strftime('%Y-%m-%d')
        to = today.strftime('%Y-%m-%d')
        r = requests.get('https://finnhub.io/api/v1/calendar/earnings',
                         params={'from': frm, 'to': to, 'token': key}, timeout=10)
        items = r.json().get('earningsCalendar', [])
        # EPS 실제 수치가 있는 기업만 필터
        reported = [it for it in items if it.get('epsActual') is not None]
        # 예상치와 실제치 모두 있는 기업 우선 정렬 (beat/miss 판단 가능)
        reported.sort(key=lambda x: (x.get('epsEstimate') is None, x.get('date', '')), reverse=False)
        result = []
        for it in reported[:15]:
            eps_a = it.get('epsActual')
            eps_e = it.get('epsEstimate')
            rev_a = it.get('revenueActual')
            rev_e = it.get('revenueEstimate')
            beat = None
            if eps_a is not None and eps_e is not None:
                beat = 'beat' if eps_a >= eps_e else 'miss'
            result.append({
                'symbol':  it.get('symbol', ''),
                'date':    it.get('date', ''),
                'year':    it.get('year'),
                'quarter': it.get('quarter'),
                'eps_actual':   eps_a,
                'eps_estimate': eps_e,
                'rev_actual':   rev_a,
                'rev_estimate': rev_e,
                'beat': beat,
            })
        print(f"  최근 실적 발표 수집 완료: {len(result)}건")
        return result
    except Exception as e:
        print(f"  최근 실적 수집 오류: {e}")
        return []


def fetch_us_ai_briefing(market, news, recent_earnings=None):
    """Gemini API로 미국 증시 AI 브리핑 생성"""
    import os
    api_key = os.environ.get('GEMINI_API_KEY', '').strip()
    if not api_key:
        return None
    try:
        print("  해외 AI 브리핑 생성 중...")

        def mv(name):
            item = d(market, name)
            v, pct = item.get('val'), item.get('pct') or 0
            if v is None: return 'N/A'
            sign = '▲' if pct >= 0 else '▼'
            return f"{v:,.2f} ({sign}{abs(pct):.2f}%)"

        sector_data = ""
        for k, name in US_SECTOR_MAP.items():
            sector_data += f"- {name}: {mv(k)}\n"

        stock_data = ""
        for k, name in US_STOCK_MAP.items():
            stock_data += f"- {name}: {mv(k)}\n"

        mag7_data = ""
        for k, name in MAG7_MAP.items():
            mag7_data += f"- {name}({k.upper()}): {mv(k)}\n"

        bond_data = ""
        for k, (ticker, label) in US_BOND_MAP.items():
            bond_data += f"- {ticker}({label}): {mv(k)}\n"

        commodity_data = ""
        for k, (ticker, label) in US_COMMODITY_MAP.items():
            commodity_data += f"- {ticker}({label}): {mv(k)}\n"

        headlines = []
        for item in news.get('international', [])[:6]:
            headlines.append(item['title'])

        from datetime import datetime as _dt
        today_str = _dt.now().strftime('%Y년 %m월 %d일')

        # 실제 실적 발표 데이터 텍스트 구성
        earnings_text = ''
        if recent_earnings:
            lines = []
            for e in recent_earnings:
                sym = e.get('symbol', '')
                dt = e.get('date', '')
                yr = e.get('year', '')
                q = e.get('quarter', '')
                ea = e.get('eps_actual')
                ee = e.get('eps_estimate')
                beat = e.get('beat', '')
                beat_str = f' ({"예상 상회" if beat=="beat" else "예상 하회"})' if beat else ''
                eps_str = f'EPS {ea}' if ea is not None else ''
                est_str = f'(예상 {ee})' if ee is not None else ''
                lines.append(f"- {sym} [{dt}, {yr}년 Q{q}]: {eps_str} {est_str}{beat_str}")
            earnings_text = '\n'.join(lines)
        else:
            earnings_text = '(실적 데이터 없음)'

        prompt = f"""오늘 날짜: {today_str}
오늘 미국 주식시장 데이터 (현지 종가 기준):
주요 지수:
- S&P500: {mv('sp500')}
- 나스닥: {mv('nasdaq')}
- 다우존스: {mv('dow')}
- VIX 공포지수: {mv('vix')}

섹터별 동향:
{sector_data}

채권:
{bond_data}

원자재:
{commodity_data}

주요 종목 동향:
{stock_data}

매그니피센트 7 동향:
{mag7_data}

최근 2주 실제 실적 발표 기업 (Finnhub 데이터):
{earnings_text}

주요 뉴스 헤드라인:
{chr(10).join(f"- {h}" for h in headlines)}

위 데이터를 바탕으로 단순 나열이 아닌, 지표 간 인과관계와 섹터/종목별 흐름이 있는 시황 분석을 작성하세요.
한국어 뉴스레터 형식으로 작성하며, 투자자들이 오늘 무엇에 집중해야 했는지 명확히 설명하세요.
earnings_reviews는 반드시 위의 "최근 2주 실제 실적 발표 기업" 데이터에서만 선정하고, 오늘 날짜({today_str}) 기준으로 작성하세요.
아래 JSON 형식으로만 응답하세요. 다른 텍스트는 절대 포함하지 마세요.
{{
  "keyword": "오늘 미국 시장 핵심 키워드 (이모지 포함, 20자 이내)",
  "hashtags": ["오늘 시장을 한눈에 보여주는 해시태그 5개 (예: #강한 고용지표, #VIX 급등 형식, # 포함, 각 12자 이내)"],
  "highlights": [
    {{"title": "오늘의 핵심 이슈 제목 (12자 이내)", "desc": "그 이슈에 대한 한 줄 설명 (35자 이내)"}},
    {{"title": "두 번째 핵심 이슈 제목 (12자 이내)", "desc": "그 이슈에 대한 한 줄 설명 (35자 이내)"}},
    {{"title": "세 번째 핵심 이슈 제목 (12자 이내)", "desc": "그 이슈에 대한 한 줄 설명 (35자 이내)"}}
  ],
  "story": "전체적인 시장 분위기와 지수 움직임의 원인 (3~4문장)",
  "sector_story": "섹터·채권·원자재 등 자산군 간의 자금 흐름과 순환매, 그 이유 (3~4문장)",
  "outlook": "향후 주목해야 할 이벤트나 투자 포인트 (2문장)",
  "stock_story": "매그니피센트7과 주요 종목의 등락 원인, 어떤 종목이 시장을 주도했는지에 대한 서사 (3~4문장)",
  "tech_insight": "RSI·MACD·VIX 등 기술적 신호를 종합해 현재 시장의 기술적 상태와 투자자가 주목할 점 (2~3문장)",
  "news_insight": "오늘 해외 주요 뉴스 헤드라인들을 종합한 시장 시사점과 투자자 유의사항 (2~3문장)",
  "earnings_reviews": [
    {{"company": "최근 1~2주 내 실적을 발표했을 법한 미국 상장기업명", "ticker": "티커", "period": "OOOO년 O분기 실적 분석 형식의 회계연도·분기 표기", "summary": "매출·EPS·가이던스 등 핵심 실적 포인트를 한 줄로 (40자 이내)"}},
    {{"company": "두 번째 기업명", "ticker": "티커", "period": "회계연도·분기 표기", "summary": "핵심 실적 포인트 한 줄 (40자 이내)"}},
    {{"company": "세 번째 기업명", "ticker": "티커", "period": "회계연도·분기 표기", "summary": "핵심 실적 포인트 한 줄 (40자 이내)"}},
    {{"company": "네 번째 기업명", "ticker": "티커", "period": "회계연도·분기 표기", "summary": "핵심 실적 포인트 한 줄 (40자 이내)"}},
    {{"company": "다섯 번째 기업명", "ticker": "티커", "period": "회계연도·분기 표기", "summary": "핵심 실적 포인트 한 줄 (40자 이내)"}}
  ]
}}"""

        import json, re
        text = _gemini_post(api_key, prompt, temperature=0.7, max_tokens=2048)
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if m:
            data = json.loads(m.group(0))
            print(f"  해외 AI 브리핑 완료")
            return data
        return None
    except Exception as e:
        print(f"  해외 AI 브리핑 오류: {e}")
        return None



def translate_news_to_korean(items):
    """Gemini API로 해외 뉴스 제목을 한국어로 번역"""
    import os, json, re
    api_key = os.environ.get('GEMINI_API_KEY', '').strip()
    if not api_key or not items:
        return items
    try:
        print("  해외 뉴스 번역 중...")
        titles = [item['title'] for item in items]
        prompt = f"""아래 영어 주식/금융 뉴스 제목을 자연스러운 한국어로 번역하세요.
반드시 아래 JSON 형식으로만 응답하고, 다른 텍스트는 포함하지 마세요.
{{"titles": ["번역된 제목1", "번역된 제목2", ...]}}

{json.dumps(titles, ensure_ascii=False)}"""

        text = _gemini_post(api_key, prompt, temperature=0.3)
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if m:
            ko_titles = json.loads(m.group(0)).get('titles', [])
            for i, item in enumerate(items):
                if i < len(ko_titles) and ko_titles[i]:
                    item['title_orig'] = item['title']
                    item['title'] = ko_titles[i]
            print(f"  해외 뉴스 번역 완료 ({len(items)}건)")
    except Exception as e:
        print(f"  해외 뉴스 번역 오류: {e}")
    return items


# ── 종목 개요 (차트 상세페이지 "어떤 회사인가요" 섹션) ───────────────────────────────

def _tracked_overview_symbols():
    """company-overview.json 생성 대상 TV 심볼 목록 (MAG7 + US_STOCK_MAP + 삼성전자, 중복 제거)"""
    symbols = []
    seen = set()
    for k in list(MAG7_MAP.keys()) + list(US_STOCK_MAP.keys()):
        ex = US_EXCHANGE_MAP.get(k, 'NASDAQ')
        sym = f'{ex}:{k.upper()}'
        if sym not in seen:
            seen.add(sym)
            symbols.append(sym)
    symbols.append('KRX:005930')
    return symbols


def fetch_company_overview():
    """추적 종목별 한글 회사소개 + 특징배지를 Gemini로 일괄 생성 → company-overview.json 데이터"""
    import os, re
    from concurrent.futures import ThreadPoolExecutor
    api_key = os.environ.get('GEMINI_API_KEY', '').strip()
    if not api_key:
        print("  GEMINI_API_KEY 없음, 회사 개요 스킵")
        return {}

    symbols = _tracked_overview_symbols()
    worker_base = 'https://dashboard-trigger.mamibj112.workers.dev'

    def fetch_one(sym):
        try:
            r = requests.get(f'{worker_base}/finance', params={'symbol': sym}, timeout=20)
            r.raise_for_status()
            d = r.json()
            return sym, (d if not d.get('error') else None)
        except Exception as e:
            print(f"  [{sym}] 데이터 조회 오류: {e}")
            return sym, None

    print("  종목 데이터 수집 중...")
    with ThreadPoolExecutor(max_workers=4) as ex:
        fetched = dict(ex.map(fetch_one, symbols))

    blocks = []
    valid_symbols = []
    for sym in symbols:
        d = fetched.get(sym)
        if not d:
            continue
        cap = d.get('marketCap')
        cap_str = f"${cap/1e12:.2f}T" if cap else "정보없음"
        rev_g = d.get('revenueGrowth')
        earn_g = d.get('earningsGrowth')
        summary = (d.get('longBusinessSummary') or '')[:400]
        blocks.append(
            f"[{sym}] {d.get('name')}\n"
            f"- 섹터/업종: {d.get('sector') or '-'} / {d.get('industry') or '-'}\n"
            f"- 시가총액: {cap_str}\n"
            f"- 매출 성장률(YoY): {f'{rev_g*100:.1f}%' if rev_g is not None else '정보없음'}\n"
            f"- 순이익 성장률(YoY): {f'{earn_g*100:.1f}%' if earn_g is not None else '정보없음'}\n"
            f"- 사업 설명(영문): {summary}"
        )
        valid_symbols.append(sym)

    if not blocks:
        return {}

    prompt = (
        "다음은 여러 주식 종목에 대한 실제 데이터입니다. 한국 개인투자자를 위한 종목 소개를 작성하세요.\n\n"
        + "\n\n".join(blocks)
        + "\n\n각 종목에 대해 다음 두 가지를 작성하세요.\n"
        "- description: 이 회사가 어떤 사업을 하는지 한국어로 2~3문장 소개 (전문용어 최소화, 일반인이 이해하기 쉽게)\n"
        "- badges: 위 데이터(시가총액, 성장률 등)에 근거한 이 회사의 특징을 나타내는 짧은 키워드 1~2개 "
        "(예: 초고성장주, 글로벌 시총 최상위권, 고배당 우량주, 안정성장주 — 8자 이내)\n\n"
        "아래 JSON 형식으로만 응답하세요. 다른 텍스트나 설명은 절대 포함하지 마세요.\n"
        "{\n"
        + ",\n".join(f'  "{sym}": {{"description": "...", "badges": ["...", "..."]}}' for sym in valid_symbols)
        + "\n}"
    )

    try:
        print(f"  회사 개요 생성 중... ({len(blocks)}개 종목)")
        text = _gemini_post(api_key, prompt, temperature=0.5, max_tokens=4096)
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if not m:
            print(f"  회사 개요 JSON 파싱 실패: {text[:100]}")
            return {}
        data = json.loads(m.group(0))
        print(f"  회사 개요 생성 완료 ({len(data)}개)")
        return data
    except Exception as e:
        print(f"  회사 개요 생성 오류: {e}")
        return {}


# ── 캘린더 ─────────────────────────────────────────────────────────────────────

# FOMC 2026 (발표일 기준)
# BOK 금통위 2026 (발표일 기준)
# 미국 CPI 2026 (발표일 기준, BLS 공식 일정)
CALENDAR_EVENTS = [
    # FOMC
    ('🇺🇸 FOMC 금리결정', '2026-01-29'),
    ('🇺🇸 FOMC 금리결정', '2026-03-19'),
    ('🇺🇸 FOMC 금리결정', '2026-05-07'),
    ('🇺🇸 FOMC 금리결정', '2026-06-18'),
    ('🇺🇸 FOMC 금리결정', '2026-07-30'),
    ('🇺🇸 FOMC 금리결정', '2026-09-17'),
    ('🇺🇸 FOMC 금리결정', '2026-10-29'),
    ('🇺🇸 FOMC 금리결정', '2026-12-10'),
    # 미국 CPI (BLS 공식 발표일)
    ('🇺🇸 미국 CPI 발표', '2026-01-14'),
    ('🇺🇸 미국 CPI 발표', '2026-02-11'),
    ('🇺🇸 미국 CPI 발표', '2026-03-11'),
    ('🇺🇸 미국 CPI 발표', '2026-04-10'),
    ('🇺🇸 미국 CPI 발표', '2026-05-13'),
    ('🇺🇸 미국 CPI 발표', '2026-06-10'),
    ('🇺🇸 미국 CPI 발표', '2026-07-15'),
    ('🇺🇸 미국 CPI 발표', '2026-08-12'),
    ('🇺🇸 미국 CPI 발표', '2026-09-09'),
    ('🇺🇸 미국 CPI 발표', '2026-10-14'),
    ('🇺🇸 미국 CPI 발표', '2026-11-12'),
    ('🇺🇸 미국 CPI 발표', '2026-12-10'),
    # 한국은행 금통위
    ('🇰🇷 한국은행 금통위', '2026-01-16'),
    ('🇰🇷 한국은행 금통위', '2026-02-27'),
    ('🇰🇷 한국은행 금통위', '2026-04-17'),
    ('🇰🇷 한국은행 금통위', '2026-05-29'),
    ('🇰🇷 한국은행 금통위', '2026-07-17'),
    ('🇰🇷 한국은행 금통위', '2026-08-28'),
    ('🇰🇷 한국은행 금통위', '2026-10-16'),
    ('🇰🇷 한국은행 금통위', '2026-11-27'),
    # 미국 고용 (비농업 고용·실업률, BLS 공식)
    ('🇺🇸 미국 고용지표', '2026-01-09'),
    ('🇺🇸 미국 고용지표', '2026-02-06'),
    ('🇺🇸 미국 고용지표', '2026-03-06'),
    ('🇺🇸 미국 고용지표', '2026-04-03'),
    ('🇺🇸 미국 고용지표', '2026-05-08'),
    ('🇺🇸 미국 고용지표', '2026-06-05'),
    ('🇺🇸 미국 고용지표', '2026-07-02'),
    ('🇺🇸 미국 고용지표', '2026-08-07'),
    ('🇺🇸 미국 고용지표', '2026-09-04'),
    ('🇺🇸 미국 고용지표', '2026-10-02'),
    ('🇺🇸 미국 고용지표', '2026-11-06'),
    ('🇺🇸 미국 고용지표', '2026-12-04'),
    # 미국 PCE 물가 (BEA, 월말 전후 발표)
    ('🇺🇸 미국 PCE 물가', '2026-01-30'),
    ('🇺🇸 미국 PCE 물가', '2026-02-27'),
    ('🇺🇸 미국 PCE 물가', '2026-03-27'),
    ('🇺🇸 미국 PCE 물가', '2026-04-30'),
    ('🇺🇸 미국 PCE 물가', '2026-05-29'),
    ('🇺🇸 미국 PCE 물가', '2026-06-26'),
    ('🇺🇸 미국 PCE 물가', '2026-07-31'),
    ('🇺🇸 미국 PCE 물가', '2026-08-28'),
    ('🇺🇸 미국 PCE 물가', '2026-09-25'),
    ('🇺🇸 미국 PCE 물가', '2026-10-30'),
    ('🇺🇸 미국 PCE 물가', '2026-11-25'),
    ('🇺🇸 미국 PCE 물가', '2026-12-23'),
    # 미국 GDP 속보치 (분기별, BEA)
    ('🇺🇸 미국 GDP 속보치', '2026-01-29'),
    ('🇺🇸 미국 GDP 속보치', '2026-04-29'),
    ('🇺🇸 미국 GDP 속보치', '2026-07-30'),
    ('🇺🇸 미국 GDP 속보치', '2026-10-29'),
    # ISM 제조업 PMI (매월 첫 영업일)
    ('🇺🇸 ISM 제조업 PMI', '2026-01-05'),
    ('🇺🇸 ISM 제조업 PMI', '2026-02-03'),
    ('🇺🇸 ISM 제조업 PMI', '2026-03-02'),
    ('🇺🇸 ISM 제조업 PMI', '2026-04-01'),
    ('🇺🇸 ISM 제조업 PMI', '2026-05-01'),
    ('🇺🇸 ISM 제조업 PMI', '2026-06-01'),
    ('🇺🇸 ISM 제조업 PMI', '2026-07-01'),
    ('🇺🇸 ISM 제조업 PMI', '2026-08-03'),
    ('🇺🇸 ISM 제조업 PMI', '2026-09-01'),
    ('🇺🇸 ISM 제조업 PMI', '2026-10-01'),
    ('🇺🇸 ISM 제조업 PMI', '2026-11-02'),
    ('🇺🇸 ISM 제조업 PMI', '2026-12-01'),
    # 한국 GDP (한국은행, 분기별 속보)
    ('🇰🇷 한국 GDP 속보', '2026-01-23'),
    ('🇰🇷 한국 GDP 속보', '2026-04-24'),
    ('🇰🇷 한국 GDP 속보', '2026-07-24'),
    ('🇰🇷 한국 GDP 속보', '2026-10-23'),
]


def fetch_upcoming_earnings(dt):
    """Finnhub API로 향후 7일 이내 주요 기업 실적 발표 예정 수집"""
    import os, requests
    from datetime import timedelta
    key = os.environ.get('FINNHUB_API_KEY', '').strip()
    if not key:
        return []
    try:
        today = dt.date()
        end = today + timedelta(days=7)
        r = requests.get('https://finnhub.io/api/v1/calendar/earnings',
                         params={'from': str(today), 'to': str(end), 'token': key},
                         timeout=10)
        items = r.json().get('earningsCalendar', [])
        # EPS 예상치가 있는 기업 (애널리스트 커버리지 = 비교적 주요 기업)
        notable = sorted(
            [it for it in items if it.get('epsEstimate') is not None],
            key=lambda x: x.get('date', '')
        )
        result = []
        for it in notable[:20]:
            d_str = it.get('date', '')
            try:
                from datetime import datetime as _dt2, date as _date2
                d = _dt2.strptime(d_str, '%Y-%m-%d').date()
                diff = (d - today).days
                if diff == 0:   label, badge = '오늘', 'nb-red'
                elif diff == 1: label, badge = '내일', 'nb-gold'
                else:           label, badge = f'{d.month}/{d.day}({["월","화","수","목","금","토","일"][d.weekday()]})', 'nb-blue'
            except Exception:
                label, badge = d_str, 'nb-blue'
            result.append({
                'symbol':       it.get('symbol', ''),
                'date':         d_str,
                'label':        label,
                'badge':        badge,
                'year':         it.get('year'),
                'quarter':      it.get('quarter'),
                'eps_estimate': it.get('epsEstimate'),
            })
        print(f"  실적 발표 예정 수집 완료: {len(result)}건")
        return result
    except Exception as e:
        print(f"  실적 발표 예정 오류: {e}")
        return []


def get_weekly_calendar(dt):
    from datetime import timedelta, date as date_cls
    today = dt.date()
    week_end = today + timedelta(days=7)
    events = []
    for name, date_str in CALENDAR_EVENTS:
        d = datetime.strptime(date_str, '%Y-%m-%d').date()
        if today <= d <= week_end:
            diff = (d - today).days
            if diff == 0:
                label = '오늘'
                badge_cls = 'nb-red'
            elif diff == 1:
                label = '내일'
                badge_cls = 'nb-gold'
            else:
                label = f'{d.month}/{d.day}({["월","화","수","목","금","토","일"][d.weekday()]})'
                badge_cls = 'nb-blue'
            events.append({'name': name, 'label': label, 'badge': badge_cls, 'date': d})
    return sorted(events, key=lambda x: x['date'])


# ── 뉴스 ──────────────────────────────────────────────────────────────────────

RSS_FEEDS = {
    'domestic': [
        ('한국경제', 'https://www.hankyung.com/feed/finance'),
        ('매일경제', 'https://www.mk.co.kr/rss/30100041/'),
    ],
    'international': [
        ('CNBC Markets', 'https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664'),
        ('CNBC Finance', 'https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=15839069'),
    ],
    'realestate': [
        ('한국경제', 'https://www.hankyung.com/feed/realestate'),
        ('머니투데이', 'https://news.mt.co.kr/mtview/rss/realestate.xml'),
        ('매일경제', 'https://www.mk.co.kr/rss/30000001/'),
    ],
    'hot': [
        ('한국경제', 'https://www.hankyung.com/feed/economy'),
        ('CNBC', 'https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114'),
    ],
}

REALESTATE_KEYWORDS = ['부동산','아파트','전세','청약','분양','재건축','재개발','임대','빌라','오피스텔','주택','토지','상가','부지','공시지가','임차']
STOCK_KEYWORDS = ['주식','증시','코스피','코스닥','주가','상장','IPO','공모','실적','매수','매도','외국인','기관투자','수급','ETF','펀드','공매도','선물','옵션','배당','증권','반도체','2차전지','바이오','상한가','하한가','급등','급락','시총','거래대금','테마주','코스닥','코스피','금투','기업공개','자사주','유상증자','무상증자','상장폐지','감사의견','영업이익','매출','PER','ROE','지수','장세','개미','동학','서학']
INTL_STOCK_KEYWORDS = ['stock','market','nasdaq','s&p','dow','shares','equity','earnings','ipo','etf','fund','trader','wall street','nyse','fed','rate','inflation','gdp','treasury','yield','bitcoin','crypto','rally','selloff','bull','bear','dividend','buyback','merger','acquisition','invest','portfolio','hedge','futures','options','sec','bond','tariff','trade','china','economy','recession','growth','profit','revenue','quarter','fiscal','index','indices','sector','tech','energy','bank','finance','financial']


def fetch_stock_story(stocks):
    """Gemini로 거래대금 상위 + 급등주 기반 시장 스토리 분석"""
    import os, json, re
    api_key = os.environ.get('GEMINI_API_KEY', '').strip()
    if not api_key or not stocks:
        return None
    try:
        print("  주도주 스토리 분석 중...")
        top_amt  = stocks.get('top_amt', [])
        top_gain = stocks.get('top_gain', [])
        breadth  = stocks.get('breadth', {})

        amt_text  = '\n'.join(f"- {s['Name']} ({s['ChagesRatio']:+.1f}%, 거래대금 {int(s['Amount'])//100000000}억)" for s in top_amt)
        gain_text = '\n'.join(f"- {s['Name']} ({s['ChagesRatio']:+.1f}%)" for s in top_gain)
        up, dn    = breadth.get('up', 0), breadth.get('down', 0)

        prompt = f"""오늘 코스피/코스닥 시장 데이터입니다.

전체 상승 {up}개 / 하락 {dn}개

거래대금 상위:
{amt_text}

급등주 상위:
{gain_text}

위 데이터를 바탕으로 아래 3가지를 분석해주세요. 부동산 내용은 절대 포함하지 마세요.
JSON 형식으로만 응답하세요. 다른 텍스트는 절대 포함하지 마세요.
{{
  "theme": "오늘의 주도 테마 한 줄 (어떤 종목들이 함께 올랐는지, 이모지 포함, 30자 이내)",
  "theme_reason": "해당 테마가 오늘 주목받은 이유 (1~2문장, 뉴스/정책/이슈 추론 포함)",
  "money_flow": "거래대금 상위 분석 - 큰 돈이 어디로 쏠렸는지 (1~2문장, 이례적 종목 포착)",
  "market_tone": "오늘 장세 성격 한 줄 (대형주 장세 vs 테마주 장세 등, 25자 이내)"
}}"""

        text = _gemini_post(api_key, prompt, temperature=0.5)
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if m:
            data = json.loads(m.group(0))
            print("  주도주 스토리 분석 완료")
            return data
        return None
    except Exception as e:
        print(f"  주도주 스토리 오류: {e}")
        return None


def fetch_investor_flow_story(stocks):
    """Gemini로 시장 체감 온도 + 수급(외국인·기관) + 52주 신고가 기반 투자자 동향 인사이트 생성"""
    import os, json, re
    api_key = os.environ.get('GEMINI_API_KEY', '').strip()
    if not api_key or not stocks:
        return ''
    try:
        print("  투자자 동향 인사이트 생성 중...")
        breadth = stocks.get('breadth', {})
        up, dn, flat = breadth.get('up', 0), breadth.get('down', 0), breadth.get('flat', 0)

        def fmt(items):
            return '\n'.join(f"- {s['Name']} ({s['ChagesRatio']:+.1f}%)" for s in items) or '- (데이터 없음)'

        prompt = f"""오늘 코스피/코스닥 수급 및 종목 동향 데이터입니다.

시장 체감 온도: 상승 {up}개 / 하락 {dn}개 / 보합 {flat}개

외국인 순매수 상위:
{fmt(stocks.get('foreign_buy', []))}

기관 순매수 상위:
{fmt(stocks.get('inst_buy', []))}

52주 신고가 근접:
{fmt(stocks.get('high_52w', []))}

위 데이터를 바탕으로 오늘 투자자 동향에 대한 인사이트를 작성해주세요. 부동산 내용은 절대 포함하지 마세요.
JSON 형식으로만 응답하세요. 다른 텍스트는 절대 포함하지 마세요.
{{
  "investor_flow": "수급 주체(외국인·기관)의 움직임과 시장 체감 온도, 신고가 종목의 흐름을 종합한 인사이트 (3~4문장, 이모지 1~2개 포함)"
}}"""

        text = _gemini_post(api_key, prompt, temperature=0.5)
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if m:
            data = json.loads(m.group(0))
            print("  투자자 동향 인사이트 생성 완료")
            return data.get('investor_flow', '')
        return ''
    except Exception as e:
        print(f"  투자자 동향 인사이트 오류: {e}")
        return ''


def fetch_etf_data():
    """ETF 데이터 수집 (KIS API)"""
    result = {'major': [], 'themes': [], 'volume': [], 'popular': []}
    try:
        import kis_api
        token = kis_api.get_token()
        if not token:
            return result

        # 모든 ETF 티커 중복 제거 후 일괄 조회
        all_etfs = {e['ticker']: e['name'] for e in MAJOR_ETFS + POPULAR_ETFS}
        for t in THEME_ETFS:
            for e in t['etfs']:
                all_etfs[e['ticker']] = e['name']

        price_map = {}
        for ticker in all_etfs:
            data = kis_api.get_stock_price(token, ticker)
            if data:
                price_map[ticker] = data

        def make(e):
            d = price_map.get(e['ticker'], {})
            return {'name': e['name'], 'val': d.get('val', 0), 'pct': d.get('pct', 0)}

        result['major']   = [make(e) for e in MAJOR_ETFS]
        result['popular'] = [make(e) for e in POPULAR_ETFS]
        result['themes']  = [{'theme': t['theme'], 'etfs': [make(e) for e in t['etfs']]} for t in THEME_ETFS]
        result['volume']  = kis_api.get_etf_volume_ranking(token, top_n=5)
        print(f"  ETF 데이터 수집 완료: {len(price_map)}개")
    except Exception as e:
        print(f"  ETF 데이터 오류: {e}")
    return result


def fetch_research_reports():
    """네이버 증권 리서치 종목분석 리포트 스크래핑"""
    print("증권사 리포트 수집 중...")
    try:
        from bs4 import BeautifulSoup
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        r = requests.get('https://finance.naver.com/research/company_list.naver', headers=headers, timeout=10)
        r.encoding = 'euc-kr'
        soup = BeautifulSoup(r.text, 'html.parser')
        rows = soup.select('table.type_1 tr')
        reports = []
        for row in rows[2:]:
            tds = row.find_all('td')
            if len(tds) < 5:
                continue
            stock   = tds[0].get_text(strip=True)
            title   = tds[1].get_text(strip=True)
            firm    = tds[2].get_text(strip=True)
            date    = tds[4].get_text(strip=True)
            a_tag   = tds[1].find('a')
            href    = a_tag['href'] if a_tag and a_tag.get('href') else ''
            url     = f"https://finance.naver.com/research/{href}" if href else ''
            if stock and title and firm:
                reports.append({'stock': stock, 'title': title, 'firm': firm, 'date': date, 'url': url})
        print(f"  리포트 수집 완료: {len(reports)}건")
        return reports[:15]
    except Exception as e:
        print(f"  리포트 수집 오류: {e}")
        return []


def fetch_research_summary(reports):
    """Gemini로 오늘의 핵심 리포트 5개 선정 및 요약 + 전체 인사이트"""
    import os, json, re
    api_key = os.environ.get('GEMINI_API_KEY', '').strip()
    if not api_key or not reports:
        return None
    try:
        print("  리포트 AI 요약 중...")
        report_text = '\n'.join(
            f"{i+1}. [{r['firm']}] {r['stock']} - {r['title']} ({r['date']})"
            for i, r in enumerate(reports)
        )
        prompt = f"""아래는 오늘 네이버 증권에 올라온 증권사 리포트 목록입니다.

{report_text}

위 리포트 중 오늘 가장 주목할 만한 5개를 선정하고, 각각의 핵심 투자 포인트를 2줄로 요약해주세요.
선정한 리포트의 번호(위 목록의 숫자)를 index 필드에 포함하세요 (1부터 시작).
아울러 오늘 증권사 리포트들의 전체적인 흐름과 시장 시사점을 2~3줄로 종합한 인사이트도 작성해주세요.
아래 JSON 형식으로만 응답하세요. 다른 텍스트는 절대 포함하지 마세요.
{{
  "reports": [
    {{"index": 1, "stock": "종목명", "firm": "증권사", "title": "리포트 제목", "point1": "핵심 포인트 1줄", "point2": "핵심 포인트 2줄"}},
    {{"index": 2, "stock": "종목명", "firm": "증권사", "title": "리포트 제목", "point1": "핵심 포인트 1줄", "point2": "핵심 포인트 2줄"}},
    {{"index": 3, "stock": "종목명", "firm": "증권사", "title": "리포트 제목", "point1": "핵심 포인트 1줄", "point2": "핵심 포인트 2줄"}},
    {{"index": 4, "stock": "종목명", "firm": "증권사", "title": "리포트 제목", "point1": "핵심 포인트 1줄", "point2": "핵심 포인트 2줄"}},
    {{"index": 5, "stock": "종목명", "firm": "증권사", "title": "리포트 제목", "point1": "핵심 포인트 1줄", "point2": "핵심 포인트 2줄"}}
  ],
  "insight": "오늘 증권사 리포트 전반적 흐름과 시장 시사점 2~3줄"
}}"""
        text = _gemini_post(api_key, prompt, temperature=0.3)
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if m:
            data = json.loads(m.group(0))
            result = data.get('reports', [])
            for rp in result:
                idx = rp.get('index', 0)
                if 1 <= idx <= len(reports):
                    rp['url'] = reports[idx - 1].get('url', '')
            print("  리포트 AI 요약 완료")
            return {'reports': result, 'insight': data.get('insight', '')}
        return None
    except Exception as e:
        print(f"  리포트 AI 요약 오류: {e}")
        return None


def fetch_kr_news_insight(news_items):
    """국내 주식 뉴스 AI 인사이트 생성"""
    import os, json, re
    api_key = os.environ.get('GEMINI_API_KEY', '').strip()
    if not api_key or not news_items:
        return ''
    try:
        print("  국내 뉴스 인사이트 생성 중...")
        news_text = '\n'.join(
            f"- {item.get('title', '')}"
            for item in news_items[:10]
        )
        prompt = f"""아래는 오늘 국내 주식 관련 뉴스 헤드라인입니다.

{news_text}

위 뉴스들을 종합해 오늘 국내 증시의 주요 이슈와 투자자가 주목해야 할 시사점을 2~3줄로 작성해주세요.
JSON 형식으로만 응답하세요.
{{"insight": "뉴스 인사이트 2~3줄"}}"""
        text = _gemini_post(api_key, prompt, temperature=0.3)
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if m:
            data = json.loads(m.group(0))
            print("  국내 뉴스 인사이트 완료")
            return data.get('insight', '')
        return ''
    except Exception as e:
        print(f"  국내 뉴스 인사이트 오류: {e}")
        return ''


TRACKED_APTS = [
    {
        'name': '거여4단지', 'lawd_cd': '11710', 'search': '거여4단지',
        'status': '투기지역', 'status_cls': 'status-normal',
        'info': '거여동 · 5호선 거여역 도보 6분 · 546세대 · 1997년',
        'note': '거여역 도보권 · 재건축 인근 단지 · 송파구 저평가',
        'pyeong': [
            {'label': '17평', 'area_label': '49㎡', 'area_min': 47.0, 'area_max': 52.0},
            {'label': '21평', 'area_label': '59㎡', 'area_min': 57.0, 'area_max': 63.0},
            {'label': '26평', 'area_label': '72㎡', 'area_min': 69.0, 'area_max': 76.0},
        ],
    },
    {
        'name': '문정시영', 'lawd_cd': '11710', 'search': '문정시영',
        'status': '리모델링', 'status_cls': 'status-remodel',
        'info': '문정동 · 개롱역~거여역 사이 · 1,316세대 · 1989년',
        'note': '강남3구 소형 최저가 · 더샵 브랜드 예정 · 18평 프리미엄↑',
        'pyeong': [
            {'label': '12평', 'area_label': '25㎡', 'area_min': 23.0, 'area_max': 27.0},
            {'label': '16평', 'area_label': '35㎡', 'area_min': 33.0, 'area_max': 37.5},
            {'label': '18평', 'area_label': '39㎡', 'area_min': 37.5, 'area_max': 42.0},
            {'label': '22평', 'area_label': '46㎡', 'area_min': 44.0, 'area_max': 49.0},
        ],
        'remodel': '포스코이앤씨 · 더샵 골든하임',
        'remodel_steps': [
            ('done',    '조합설립 · 시공사 선정 · 안전진단 · 교통영향평가 · 도시건축위 사전자문 완료'),
            ('current', '건축심의 + 안전성검토 진행 중 (2026년 중반 결론 예상)'),
            ('todo',    '사업계획승인 → 1,316 → 1,440세대 (+124가구)'),
        ],
    },
]


def fetch_tracked_apt_trades():
    """관심 단지 실거래가 자동 수집 (국토부 API)"""
    import os, requests, xml.etree.ElementTree as ET
    from datetime import datetime, timedelta
    api_key = os.environ.get('DATA_GO_KR_API_KEY', '').strip()
    if not api_key:
        return None
    print("  관심 단지 실거래 수집 중...")
    today = datetime.now()
    # 최근 6개월 YYYYMM 리스트 생성
    months = []
    dt = today.replace(day=1)
    for _ in range(6):
        months.append(dt.strftime('%Y%m'))
        dt = (dt - timedelta(days=1)).replace(day=1)

    result = {}
    for apt in TRACKED_APTS:
        all_trades = []
        seen_months = set()
        for ym in months:
            if ym in seen_months:
                continue
            seen_months.add(ym)
            try:
                url = 'https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade'
                r = requests.get(url, params={
                    'serviceKey': api_key, 'LAWD_CD': apt['lawd_cd'],
                    'DEAL_YMD': ym, 'pageNo': 1, 'numOfRows': 1000,
                }, timeout=12)
                root = ET.fromstring(r.text)
                for item in root.findall('.//item'):
                    nm = item.findtext('aptNm', '').strip()
                    if apt['search'] not in nm:
                        continue
                    amt_str = item.findtext('dealAmount', '').replace(',', '').strip()
                    area_str = item.findtext('excluUseAr', '').strip()
                    day_str = item.findtext('dealDay', '').strip().zfill(2)
                    if amt_str.isdigit() and area_str:
                        all_trades.append({
                            'amt': int(amt_str),
                            'area': float(area_str),
                            'ym': ym,
                            'day': day_str,
                        })
            except Exception:
                pass

        pyeong_result = []
        for py in apt['pyeong']:
            matching = [t for t in all_trades
                        if py['area_min'] <= t['area'] <= py['area_max']]
            if matching:
                latest = sorted(matching, key=lambda x: (x['ym'], x['day']), reverse=True)[0]
                amt_disp = f"{latest['amt']//10000}억{latest['amt']%10000:,}만" if latest['amt'] >= 10000 else f"{latest['amt']:,}만"
                date_disp = f"{latest['ym'][:4]}.{latest['ym'][4:]}"
                pyeong_result.append({
                    'label': py['label'], 'area_label': py['area_label'],
                    'amt': amt_disp, 'date': date_disp,
                })
            else:
                pyeong_result.append({
                    'label': py['label'], 'area_label': py['area_label'],
                    'amt': None, 'date': '',
                })
        result[apt['name']] = pyeong_result

    print(f"  관심 단지 수집 완료")
    return result


def fetch_re_rates():
    """한국은행 ECOS API로 기준금리·국고채·주담대 금리 수집"""
    import os, requests
    from datetime import datetime, timedelta
    result = {}
    try:
        key = os.environ.get('ECOS_API_KEY', 'sample').strip() or 'sample'
        today = datetime.now()
        s = (today - timedelta(days=60)).strftime('%Y%m%d')
        e = today.strftime('%Y%m%d')
        sm = (today - timedelta(days=90)).strftime('%Y%m')
        em = today.strftime('%Y%m')
        headers = {'User-Agent': 'Mozilla/5.0'}

        def ecos(stat, item, freq='D', start=s, end=e):
            url = f'https://ecos.bok.or.kr/api/StatisticSearch/{key}/json/kr/1/5/{stat}/{freq}/{start}/{end}/{item}/'
            r = requests.get(url, headers=headers, timeout=10)
            rows = r.json().get('StatisticSearch', {}).get('row', [])
            return rows[-1] if rows else None

        # 기준금리
        row = ecos('722Y001', '0101000')
        if row:
            result['base_rate'] = float(row['DATA_VALUE'])
            result['base_rate_date'] = row['TIME']

        # 국고채 3년
        row2 = ecos('817Y002', '010190000')
        if row2:
            result['bond_3y'] = float(row2['DATA_VALUE'])

        # 국고채 10년
        row3 = ecos('817Y002', '010200000')
        if row3:
            result['bond_10y'] = float(row3['DATA_VALUE'])

        # 주택담보대출 금리 (신규취급액 기준, 월별)
        row4 = ecos('121Y006', 'BECBLA0302', freq='M', start=sm, end=em)
        if row4:
            result['mortgage_rate'] = float(row4['DATA_VALUE'])
            result['mortgage_date'] = row4['TIME']

        # 전세자금대출 금리
        row5 = ecos('121Y006', 'BECBLA03041', freq='M', start=sm, end=em)
        if row5:
            result['jeonse_rate'] = float(row5['DATA_VALUE'])

        print(f"  금리 데이터 수집 완료: 기준금리 {result.get('base_rate','?')}%")
    except Exception as e:
        print(f"  금리 데이터 오류: {e}")
    return result


def fetch_apt_trade_trend():
    """국토부 아파트 실거래가 API - 서울 주요 구 최근 거래 동향"""
    import os, requests, xml.etree.ElementTree as ET
    from datetime import datetime, timedelta
    api_key = os.environ.get('DATA_GO_KR_API_KEY', '').strip()
    if not api_key:
        return None
    print("  아파트 실거래 동향 수집 중...")
    today = datetime.now()
    ym = today.strftime('%Y%m')
    ym_prev = (today.replace(day=1) - timedelta(days=1)).strftime('%Y%m')
    districts = {'11680':'강남구','11650':'서초구','11710':'송파구',
                 '11440':'마포구','11500':'강서구','11350':'노원구'}
    result = []
    for lawd_cd, name in districts.items():
        for deal_ym in [ym, ym_prev]:
            try:
                url = 'https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade'
                r = requests.get(url, params={
                    'serviceKey': api_key, 'LAWD_CD': lawd_cd,
                    'DEAL_YMD': deal_ym, 'pageNo': 1, 'numOfRows': 100,
                }, timeout=10)
                root = ET.fromstring(r.text)
                items = root.findall('.//item')
                if items:
                    prices = []
                    for item in items:
                        amt = item.findtext('dealAmount','').replace(',','').strip()
                        if amt.isdigit():
                            prices.append(int(amt))
                    if prices:
                        result.append({'name': name, 'count': len(prices),
                                       'avg': sum(prices)//len(prices), 'ym': deal_ym})
                        break
            except:
                pass
    print(f"  실거래 동향 수집 완료: {len(result)}개 구")
    return result or None


def fetch_subscription_schedule():
    """청약홈 APT 분양정보 API - 최근 청약 공고"""
    import os, requests, xml.etree.ElementTree as ET
    from datetime import datetime, timedelta
    api_key = os.environ.get('DATA_GO_KR_API_KEY', '').strip()
    if not api_key:
        return []
    print("  청약 일정 수집 중...")
    today = datetime.now()
    # 이번 달 / 다음 달 청약 공고 조회
    results = []
    for endpoint in [
        'https://apis.data.go.kr/B551528/APTInfoService/getAPTLttotPblancMdlInfo',
        'https://apis.data.go.kr/B551528/APTInfoService/getAPTLttotPblancDetail',
    ]:
        try:
            r = requests.get(endpoint, params={
                'serviceKey': api_key, 'pageNo': 1, 'numOfRows': 5,
            }, timeout=10)
            if r.status_code != 200 or not r.text.strip().startswith('<'):
                continue
            root = ET.fromstring(r.text)
            items = root.findall('.//item')
            for item in items:
                name = item.findtext('houseNm', '') or item.findtext('aptNm', '')
                area = item.findtext('hssplyAdres', '') or item.findtext('sggNm', '')
                rcpt_bgn = item.findtext('rcptBgnde', '') or item.findtext('subscrptRceptBgnde', '')
                rcpt_end = item.findtext('rcptEndde', '') or item.findtext('subscrptRceptEndde', '')
                if name:
                    results.append({'name': name, 'area': area,
                                    'rcpt_bgn': rcpt_bgn, 'rcpt_end': rcpt_end})
            if results:
                break
        except Exception as e:
            continue
    print(f"  청약 일정 수집 완료: {len(results)}건")
    return results


def fetch_re_news_insight(news_items):
    """부동산 뉴스 AI 인사이트 생성"""
    import os, json, re
    api_key = os.environ.get('GEMINI_API_KEY', '').strip()
    if not api_key or not news_items:
        return ''
    try:
        print("  부동산 뉴스 인사이트 생성 중...")
        news_text = '\n'.join(f"- {item.get('title','')}" for item in news_items[:10])
        prompt = f"""아래는 오늘 국내 부동산 관련 뉴스 헤드라인입니다.

{news_text}

위 뉴스들을 종합해 오늘 부동산 시장의 주요 이슈와 실수요자·투자자가 주목해야 할 시사점을 2~3줄로 작성해주세요.
JSON 형식으로만 응답하세요.
{{"insight": "부동산 뉴스 인사이트 2~3줄"}}"""
        text = _gemini_post(api_key, prompt, temperature=0.3)
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if m:
            print("  부동산 뉴스 인사이트 완료")
            return json.loads(m.group(0)).get('insight', '')
        return ''
    except Exception as e:
        print(f"  부동산 뉴스 인사이트 오류: {e}")
        return ''


def fetch_news():
    print("뉴스 수집 중...")
    import re as _re
    news = {}
    for cat, feeds in RSS_FEEDS.items():
        items = []
        for source, url in feeds:
            try:
                f = feedparser.parse(url, request_headers={'User-Agent': 'Mozilla/5.0'})
                for entry in f.entries[:15]:
                    title = entry.get('title', '').strip()
                    link = entry.get('link', '#')
                    published = entry.get('published', '')
                    if not title or len(title) <= 5:
                        continue
                    # 국내 뉴스는 주식 관련 키워드 포함된 것만, 부동산 제외
                    if cat == 'domestic':
                        if any(kw in title for kw in REALESTATE_KEYWORDS):
                            continue
                        if not any(kw in title for kw in STOCK_KEYWORDS):
                            continue
                    # 해외 뉴스는 주식/금융 관련 영어 키워드 포함된 것만
                    if cat == 'international':
                        title_lower = title.lower()
                        if not any(kw in title_lower for kw in INTL_STOCK_KEYWORDS):
                            continue
                    date_str = ''
                    if published:
                        try:
                            from email.utils import parsedate_to_datetime
                            dt = parsedate_to_datetime(published).astimezone(KST)
                            date_str = f"{dt.month}월 {dt.day}일"
                        except:
                            date_str = published[:10]
                    raw_summary = entry.get('summary', '') or entry.get('description', '')
                    summary = _re.sub(r'<[^>]+>', '', raw_summary).strip()
                    summary = summary[:80] + '…' if len(summary) > 80 else summary
                    items.append({'title': title, 'url': link, 'date': date_str, 'source': source, 'summary': summary})
            except Exception as e:
                print(f"  RSS 오류 [{url}]: {e}")
        news[cat] = items[:7]
    # 해외 뉴스 한국어 번역
    if news.get('international'):
        import time as _time; _time.sleep(5)
        news['international'] = translate_news_to_korean(news['international'])
    return news

# ── 관심 종목 ──────────────────────────────────────────────────────────────────

def _fetch_ticker_news(yf_ticker, limit=5):
    """yfinance Ticker 객체에서 최신 뉴스 가져오기"""
    from datetime import datetime as _dt
    try:
        items = []
        for n in (yf_ticker.news or [])[:limit]:
            ts = n.get('providerPublishTime') or n.get('pubDate')
            if ts:
                try:
                    date_str = _dt.fromtimestamp(ts).strftime('%m/%d %H:%M')
                except:
                    date_str = ''
            else:
                date_str = ''
            content = n.get('content') or {}
            title = n.get('title') or content.get('title', '')
            link  = n.get('link')  or (content.get('clickThroughUrl') or {}).get('url', '#')
            publisher = n.get('publisher') or (content.get('provider') or {}).get('displayName', '')
            if title:
                items.append({'title': title, 'link': link, 'publisher': publisher, 'date': date_str})
        return items
    except:
        return []


def fetch_watchlist_data(watchlist):
    """관심 종목 상세 데이터 수집 (yfinance 5년 히스토리)"""
    import pandas as _pd
    from datetime import datetime as _dt2
    results = []
    for item in watchlist:
        ticker = item['ticker']
        name   = item['name']
        market = item['market']
        try:
            t    = yf.Ticker(ticker)
            info = t.info
            hist = t.history(period='5y')
            if hist.empty or len(hist) < 2:
                print(f"  [{ticker}] 히스토리 없음"); continue

            closes = hist['Close'].tolist()
            highs  = hist['High'].tolist()
            lows   = hist['Low'].tolist()
            curr   = closes[-1]
            prev   = closes[-2]
            change     = round(curr - prev, 4)
            change_pct = round(change / prev * 100, 2) if prev else 0
            currency   = info.get('currency', 'USD')

            # ── 헬퍼 ──
            def _r(key, dec=2):
                v = info.get(key)
                return round(v, dec) if v is not None else None
            def _pf(key):
                v = info.get(key)
                return round(v * 100, 2) if v is not None else None
            def _cap(v):
                if v is None: return 'N/A'
                if currency == 'KRW':
                    return f'{v/1e12:.1f}조원' if v >= 1e12 else f'{v/1e8:.0f}억원'
                if v >= 1e12: return f'${v/1e12:.2f}T'
                if v >= 1e9:  return f'${v/1e9:.1f}B'
                return f'${v/1e6:.0f}M'
            def _cash(v):
                if v is None: return 'N/A'
                if currency == 'KRW':
                    return f'{v/1e8:.0f}억원'
                if v >= 1e9: return f'${v/1e9:.1f}B'
                return f'${v/1e6:.0f}M'

            # ── RSI ──
            rsi = round(calculate_rsi(closes), 1)

            # ── SMA 괴리율 ──
            s = _pd.Series(closes)
            def sma_gap(n):
                if len(closes) < n: return None
                v = s.rolling(n).mean().iloc[-1]
                return round((curr - v) / v * 100, 2) if v else None

            # ── 기간별 수익률 ──
            def ret(days):
                if len(closes) < days + 1: return None
                old = closes[-(days + 1)]
                return round((curr - old) / old * 100, 2) if old else None

            # YTD
            try:
                year_start = _dt2(hist.index[-1].year, 1, 1)
                ytd_closes = [c for d2, c in zip(hist.index, closes) if d2.replace(tzinfo=None) >= year_start]
                ret_ytd = round((curr - ytd_closes[0]) / ytd_closes[0] * 100, 2) if ytd_closes else None
            except:
                ret_ytd = None

            ret_3y = round((curr - closes[-(252*3+1)]) / closes[-(252*3+1)] * 100, 2) if len(closes) >= 252*3+1 else None
            ret_5y = round((curr - closes[0]) / closes[0] * 100, 2) if len(closes) >= 252*4 else None

            # ── ATR(14) ──
            try:
                atrs = []
                for i in range(1, min(15, len(closes))):
                    tr = max(highs[-i] - lows[-i],
                             abs(highs[-i] - closes[-i-1]),
                             abs(lows[-i]  - closes[-i-1]))
                    atrs.append(tr)
                atr = round(sum(atrs) / len(atrs), 2) if atrs else None
            except:
                atr = None

            # ── 변동성 (연율화) ──
            try:
                import math as _math
                rets = _pd.Series(closes).pct_change().dropna()
                vol_weekly  = round(float(rets.tail(52).std()  * _math.sqrt(52)  * 100), 2)
                vol_monthly = round(float(rets.tail(252).std() * _math.sqrt(252) * 100), 2)
            except:
                vol_weekly = vol_monthly = None

            # ── 상대 거래량 ──
            vol   = info.get('volume') or info.get('regularMarketVolume')
            avg_v = info.get('averageVolume')
            rel_vol = round(vol / avg_v, 2) if vol and avg_v else None

            # ── IPO 날짜 ──
            try:
                ipo_ts = info.get('firstTradeDateEpochUtc') or info.get('firstTradeDate')
                ipo_date = _dt2.fromtimestamp(ipo_ts).strftime('%Y-%m-%d') if ipo_ts else None
            except:
                ipo_date = None

            results.append({
                # 기본
                'ticker': ticker, 'name': name, 'market': market,
                'price': round(curr, 4), 'change': change, 'change_pct': change_pct,
                'currency': currency,
                # 주요지표
                'market_cap':   _cap(info.get('marketCap')),
                'ev':           _cap(info.get('enterpriseValue')),
                'pe':           _r('trailingPE'),
                'forward_pe':   _r('forwardPE'),
                'pb':           _r('priceToBook'),
                'ps':           _r('priceToSalesTrailing12Months'),
                'peg':          _r('pegRatio'),
                'ev_ebitda':    _r('enterpriseToEbitda'),
                'eps':          _r('trailingEps', 4),
                'shares_out':   _cap(info.get('sharesOutstanding')),
                'float_shares': _cap(info.get('floatShares')),
                # 수익성
                'revenue':      _cash(info.get('totalRevenue')),
                'net_income':   _cash(info.get('netIncomeToCommon')),
                'op_margin':    _pf('operatingMargins'),
                'profit_margin':_pf('profitMargins'),
                'gross_margin': _pf('grossMargins'),
                'roe':          _pf('returnOnEquity'),
                'roa':          _pf('returnOnAssets'),
                'roic':         _pf('returnOnCapital'),
                # 성장성
                'rev_growth':   _pf('revenueGrowth'),
                'earn_growth':  _pf('earningsGrowth'),
                'rev_q_growth': _pf('revenueQuarterlyGrowth'),
                'earn_q_growth':_pf('earningsQuarterlyGrowth'),
                # 재무건전성
                'current_ratio':_r('currentRatio'),
                'quick_ratio':  _r('quickRatio'),
                'debt_equity':  _r('debtToEquity'),
                'total_debt':   _cash(info.get('totalDebt')),
                'total_cash':   _cash(info.get('totalCash')),
                'fcf':          _cash(info.get('freeCashflow')),
                # 배당
                'div_yield':    _pf('dividendYield'),
                'div_rate':     _r('dividendRate', 4),
                'payout_ratio': _pf('payoutRatio'),
                'ex_div_date':  str(info.get('exDividendDate',''))[:10] if info.get('exDividendDate') else None,
                # 주가 성과
                'high52': _r('fiftyTwoWeekHigh', 4), 'low52': _r('fiftyTwoWeekLow', 4),
                'target': _r('targetMeanPrice'),
                'ret_1w': ret(5),  'ret_1m': ret(21), 'ret_3m': ret(63),
                'ret_6m': ret(126),'ret_ytd': ret_ytd,'ret_1y': ret(252),
                'ret_3y': ret_3y,  'ret_5y': ret_5y,
                # 기술적지표
                'rsi': rsi, 'beta': _r('beta'),
                'sma20_gap': sma_gap(20), 'sma50_gap': sma_gap(50), 'sma200_gap': sma_gap(200),
                'atr': atr, 'vol_weekly': vol_weekly, 'vol_monthly': vol_monthly,
                # 거래정보
                'volume': vol, 'avg_volume': avg_v, 'rel_volume': rel_vol,
                'exchange': info.get('exchange',''),
                # 지분구조
                'inst_pct':    _pf('institutionsPercentHeld'),
                'insider_pct': _pf('heldPercentInsiders'),
                'short_float': _pf('shortPercentOfFloat'),
                # 기타
                'sector': info.get('sector',''), 'industry': info.get('industry',''),
                'employees': info.get('fullTimeEmployees'),
                'country':   info.get('country',''),
                'ipo_date':  ipo_date,
                'website':   info.get('website',''),
                'desc':      (info.get('longBusinessSummary') or '')[:250],
                # 뉴스
                'news': translate_news_to_korean(_fetch_ticker_news(t)),
            })
            print(f"  [{ticker}] 수집 완료")
        except Exception as e:
            print(f"  [{ticker}] 오류: {e}")
    return results


# ── 시황 요약 ──────────────────────────────────────────────────────────────────

def build_dom_summary(market):
    """국내 시황 핵심 요약 문장 생성"""
    points = []

    kospi_pct = d(market, 'kospi').get('pct') or 0
    kosdaq_pct = d(market, 'kosdaq').get('pct') or 0
    usdkrw_pct = d(market, 'usdkrw').get('pct') or 0
    usdkrw_val = d(market, 'usdkrw').get('val')

    # 코스피 움직임
    if abs(kospi_pct) >= 2.0:
        word = '급등' if kospi_pct > 0 else '급락'
        points.append(f'코스피 {abs(kospi_pct):.1f}% {word}')
    elif abs(kospi_pct) >= 1.0:
        word = '상승' if kospi_pct > 0 else '하락'
        points.append(f'코스피 {abs(kospi_pct):.1f}% {word}')
    else:
        points.append('코스피 보합권')

    # 코스닥 괴리
    gap = kosdaq_pct - kospi_pct
    if abs(gap) >= 1.0:
        if gap > 0:
            points.append('코스닥 상대 강세')
        else:
            points.append('코스닥 상대 약세')

    # 환율
    if usdkrw_val and usdkrw_pct:
        if usdkrw_val >= 1450:
            points.append(f'원/달러 {usdkrw_val:,.0f}원 고환율 부담')
        elif abs(usdkrw_pct) >= 0.5:
            word = '약세(환율 상승)' if usdkrw_pct > 0 else '강세(환율 하락)'
            points.append(f'원화 {word}')

    # 수급
    # 유가
    brent_pct = d(market, 'brent').get('pct') or 0
    if abs(brent_pct) >= 2.0:
        word = '급등' if brent_pct > 0 else '급락'
        points.append(f'브렌트유 {abs(brent_pct):.1f}% {word}')

    return ' · '.join(points) if points else '시장 데이터 수집 중'


def build_us_summary(market):
    """해외 시황 핵심 요약 문장 생성"""
    points = []

    sp500_pct  = d(market, 'sp500').get('pct') or 0
    nasdaq_pct = d(market, 'nasdaq').get('pct') or 0
    tnx_val    = d(market, 'tnx').get('val')
    tnx_chg    = d(market, 'tnx').get('chg') or 0
    dxy_pct    = d(market, 'dxy').get('pct') or 0
    gold_pct   = d(market, 'gold').get('pct') or 0
    nikkei_pct = d(market, 'nikkei').get('pct') or 0

    # S&P500
    if abs(sp500_pct) >= 2.0:
        word = '급등' if sp500_pct > 0 else '급락'
        points.append(f'S&P500 {abs(sp500_pct):.1f}% {word}')
    elif abs(sp500_pct) >= 1.0:
        word = '상승' if sp500_pct > 0 else '하락'
        points.append(f'S&P500 {abs(sp500_pct):.1f}% {word}')
    else:
        points.append('S&P500 보합')

    # 나스닥 괴리
    gap = nasdaq_pct - sp500_pct
    if abs(gap) >= 1.0:
        word = '강세' if gap > 0 else '약세'
        points.append(f'나스닥 상대 {word} (기술주 {"주도" if gap > 0 else "부진"})')

    # 미 10년물
    if tnx_val and abs(tnx_chg) >= 0.05:
        word = '상승' if tnx_chg > 0 else '하락'
        points.append(f'미 10년물 {tnx_val:.2f}%({word})')
    elif tnx_val and tnx_val >= 4.5:
        points.append(f'미 10년물 {tnx_val:.2f}% 고금리')

    # 달러 인덱스
    if abs(dxy_pct) >= 0.5:
        word = '강세' if dxy_pct > 0 else '약세'
        points.append(f'달러 {word}')

    # 금
    if abs(gold_pct) >= 1.0:
        word = '상승' if gold_pct > 0 else '하락'
        points.append(f'금 {abs(gold_pct):.1f}% {word}')

    # 닛케이
    if abs(nikkei_pct) >= 1.5:
        word = '급등' if nikkei_pct > 0 else '급락'
        points.append(f'닛케이 {abs(nikkei_pct):.1f}% {word}')

    return ' · '.join(points) if points else '시장 데이터 수집 중'


# ── 표시 헬퍼 ─────────────────────────────────────────────────────────────────

def d(market, name):
    return market.get(name, {'val': None, 'chg': None, 'pct': None, 'ok': False})

def vdisp(m, name):
    """값 표시 HTML"""
    item = d(m, name)
    v = item.get('val')
    pct = item.get('pct') or 0
    ok = item.get('ok', False)
    warn = '' if ok else '<span class="warn">⚠</span>'

    if v is None:
        return f'<span class="neu-txt">N/A <span class="warn">⚠</span></span>'

    if name == 'kospi':
        cls = 'up-txt' if pct >= 0 else 'dn-txt'
        return f'<span class="{cls}">{v:,.2f}{warn}</span>'
    if name == 'kosdaq':
        cls = 'up-txt' if pct >= 0 else 'dn-txt'
        return f'<span class="{cls}">{v:,.2f}{warn}</span>'
    if name == 'usdkrw':
        cls = 'dn-txt' if pct > 0 else ('up-txt' if pct < 0 else 'neu-txt')
        return f'<span class="{cls}">{v:,.1f}원{warn}</span>'
    if name in ('brent', 'wti'):
        cls = 'dn-txt' if pct < 0 else 'up-txt'
        return f'<span class="{cls}">${v:.1f}{warn}</span>'
    if name == 'gold':
        cls = 'dn-txt' if pct < 0 else 'up-txt'
        return f'<span class="{cls}">${v:,.0f}{warn}</span>'
    if name == 'tnx':
        cls = 'dn-txt' if pct > 0 else 'up-txt'
        return f'<span class="{cls}">{v:.2f}%{warn}</span>'
    if name == 'dxy':
        cls = 'dn-txt' if pct > 0 else 'up-txt'
        return f'<span class="{cls}">{v:.2f}{warn}</span>'
    if name in ('sp500', 'dow', 'nasdaq', 'nikkei'):
        cls = 'up-txt' if pct >= 0 else 'dn-txt'
        return f'<span class="{cls}">{v:,.2f}{warn}</span>'
    if name == 'btc':
        cls = 'up-txt' if pct >= 0 else 'dn-txt'
        return f'<span class="{cls}">${v:,.0f}{warn}</span>'
    return f'{v:.2f}'

def cdisp(m, name):
    """등락 표시 HTML"""
    item = d(m, name)
    chg = item.get('chg')
    pct = item.get('pct')
    if chg is None or pct is None:
        return ''

    sign = '▲' if chg >= 0 else '▼'
    ac = abs(chg)
    ap = abs(pct)

    if name == 'usdkrw':
        cls = 'dn-txt' if chg > 0 else ('up-txt' if chg < 0 else 'neu-txt')
        return f'<span class="{cls}">{sign} {ac:.1f} ({ap:.2f}%)</span>'
    if name in ('brent', 'wti', 'gold'):
        cls = 'up-txt' if chg >= 0 else 'dn-txt'
        return f'<span class="{cls}">{sign} ${ac:.2f} ({ap:.2f}%)</span>'
    if name == 'tnx':
        cls = 'dn-txt' if chg > 0 else 'up-txt'
        return f'<span class="{cls}">{sign} {ac:.2f}%p</span>'
    if name == 'dxy':
        cls = 'dn-txt' if chg > 0 else 'up-txt'
        return f'<span class="{cls}">{sign} {ac:.2f} ({ap:.2f}%)</span>'

    cls = 'up-txt' if chg >= 0 else 'dn-txt'
    return f'<span class="{cls}">{sign} {ac:.2f} ({ap:.2f}%)</span>'

def news_html(items, badge_cls='nb-blue', badge_txt='뉴스', border=None):
    if not items:
        return '<div style="color:var(--t3);font-size:12px;padding:12px 0;">뉴스를 불러오는 중...</div>'
    style = f' style="border-left-color:{border};"' if border else ''
    out = ''
    for item in items:
        title = item['title']
        if len(title) > 75:
            title = title[:75] + '…'
        url = item.get('url', '#')
        meta = ' · '.join(filter(None, [item.get('source',''), item.get('date','')]))
        summary = item.get('summary', '')
        summary_html = f'<div class="news-summary">{summary}</div>' if summary else ''
        title_orig = item.get('title_orig', '')
        orig_html = f'<div class="news-orig">{title_orig[:80]}{"…" if len(title_orig) > 80 else ""}</div>' if title_orig else ''
        out += f'''<div class="news-item"{style}>
  <span class="news-badge {badge_cls}">{badge_txt}</span>
  <div class="news-title"><a href="{url}" target="_blank">{title}</a></div>
  {orig_html}
  {summary_html}
  <div class="news-meta">{meta}</div>
</div>'''
    return out

# ── CSS ───────────────────────────────────────────────────────────────────────

CSS = """
:root{--bg:#080b10;--card:#0f1318;--card2:#151a22;--border:rgba(255,255,255,.08);
--up:#00e896;--dn:#ff4060;--blue:#4da6ff;--gold:#ffc940;--orange:#ff8c3a;
--purple:#a78bfa;--t1:#f0f4ff;--t2:#b8ccee;--t3:#6a80aa}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--t1);font-family:-apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Malgun Gothic",sans-serif;
font-size:13px;max-width:480px;margin:0 auto;padding-bottom:32px}
a{color:var(--blue);text-decoration:none}a:hover{text-decoration:underline}
.header{padding:16px 16px 0;display:flex;justify-content:space-between;align-items:flex-end}
.header-title{font-size:11px;color:var(--t3);letter-spacing:.5px;text-transform:uppercase}
.header-date{font-size:16px;font-weight:700}
.header-day{font-size:11px;color:var(--t3);margin-top:2px}
.header-right{text-align:right;font-size:11px;color:var(--t3)}
.update-btn{{display:inline-block;margin-top:5px;padding:4px 10px;font-size:10px;color:var(--blue);border:1px solid var(--blue);border-radius:6px;background:none;cursor:pointer;opacity:.8}}
.update-btn:hover{{opacity:1}}
.update-btn:disabled{{opacity:.4;cursor:not-allowed}}
.update-status{{font-size:10px;color:var(--t3);display:block;text-align:right;margin-top:2px;min-height:14px}}

.tab-nav{display:flex;margin:12px 0 0;border-bottom:1px solid var(--border);
position:sticky;top:0;background:var(--bg);z-index:10;padding:0 4px}
.tab-btn{flex:1;padding:10px 4px;background:none;border:none;border-bottom:2px solid transparent;
color:var(--t3);font-size:12px;font-family:inherit;cursor:pointer;transition:all .2s;white-space:nowrap}
.tab-btn.active{color:var(--t1);border-bottom-color:var(--blue);font-weight:600}
.tab-panel{display:none;padding:0 12px}.tab-panel.active{display:block}
.section{margin-top:16px}
.section-label{font-size:10px;color:var(--t3);text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;padding-left:2px}
.banner{padding:12px 14px;border-radius:10px;border-left:3px solid;margin-top:12px;line-height:1.5;font-size:12.5px}
.banner.up{background:rgba(0,232,150,.08);border-color:var(--up)}
.banner.dn{background:rgba(255,64,96,.09);border-color:var(--dn)}
.banner.orange{background:rgba(255,140,58,.08);border-color:var(--orange)}
.banner.blue{background:rgba(77,166,255,.08);border-color:var(--blue)}
.banner.hot{background:rgba(255,64,96,.09);border-color:var(--gold)}
.banner strong{font-weight:700}
.index-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.idx-card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:12px}
.idx-name{font-size:11px;color:var(--t3);margin-bottom:4px}
.idx-val{font-size:20px;font-weight:700}.idx-chg{font-size:12px;margin-top:3px}
.up-txt{color:var(--up)}.dn-txt{color:var(--dn)}.neu-txt{color:var(--t2)}
.macro-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px}
.macro-card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:9px 10px}
.macro-name{font-size:9.5px;color:var(--t3);margin-bottom:2px}
.macro-val{font-size:13px;font-weight:700}.macro-chg{font-size:10px;margin-top:2px}
.news-item{background:var(--card);border-radius:10px;padding:13px 14px;margin-bottom:8px;border-left:3px solid var(--border)}
.news-badge{display:inline-block;font-size:10px;padding:2px 7px;border-radius:3px;margin-bottom:5px;font-weight:600}
.nb-red{background:rgba(255,64,96,.15);color:#ff6080}.nb-blue{background:rgba(77,166,255,.15);color:var(--blue)}
.nb-green{background:rgba(0,232,150,.15);color:var(--up)}.nb-gold{background:rgba(255,201,64,.15);color:var(--gold)}
.nb-orange{background:rgba(255,140,58,.15);color:var(--orange)}.nb-purple{background:rgba(167,139,250,.15);color:var(--purple)}
.news-title{font-size:14px;font-weight:700;line-height:1.45}
.news-title a{color:var(--t1)}.news-title a:hover{color:var(--blue);text-decoration:none}
.news-summary{font-size:11.5px;color:var(--t2);line-height:1.5;margin-top:5px}
.news-meta{font-size:10px;color:var(--t3);margin-top:5px}
.news-orig{font-size:10px;color:var(--t3);margin-top:3px;font-style:italic;opacity:.7}
.apt-card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:14px;margin-bottom:10px}
.apt-header{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px}
.apt-name{font-size:15px;font-weight:700}.apt-info{font-size:10px;color:var(--t3);margin-top:3px}
.apt-status{font-size:9px;padding:3px 7px;border-radius:4px;font-weight:600;flex-shrink:0}
.status-remodel{background:rgba(167,139,250,.15);color:var(--purple)}
.status-normal{background:rgba(77,166,255,.12);color:var(--blue)}
.apt-table{width:100%;border-collapse:collapse}
.apt-table th{font-size:10px;color:var(--t3);font-weight:400;padding:5px 6px;text-align:right;border-bottom:1px solid var(--border)}
.apt-table th:first-child{text-align:left}
.apt-table td{padding:7px 6px;border-bottom:1px solid rgba(255,255,255,.04);font-size:11px}
.apt-table td:not(:first-child){text-align:right}
.apt-table tr:last-child td{border-bottom:none}
.remodel-steps{margin-top:10px;border-top:1px solid var(--border);padding-top:10px}
.remodel-label{font-size:10px;color:var(--t3);margin-bottom:6px}
.step-row{display:flex;align-items:flex-start;gap:6px;margin-bottom:4px}
.step-dot{width:6px;height:6px;border-radius:50%;flex-shrink:0;margin-top:4px}
.step-text{font-size:11px;line-height:1.4}
.step-done .step-dot{background:var(--up)}.step-done .step-text{color:var(--t3)}
.step-current .step-dot{background:var(--gold)}.step-current .step-text{color:var(--gold);font-weight:600}
.step-todo .step-dot{background:var(--border)}.step-todo .step-text{color:var(--t3)}
.invest-point{margin-top:10px;padding:8px 10px;background:var(--card2);border-radius:6px;font-size:11px;color:var(--t2);line-height:1.5}
.warn{color:var(--gold);font-size:10px}
.footer-note{font-size:10px;color:var(--t3);text-align:center;padding:16px 0 4px;line-height:1.6}
.stock-row{display:flex;justify-content:space-between;align-items:center;padding:5px 8px;background:var(--card);border-radius:6px;margin-bottom:4px}
.stock-name{font-size:11px;font-weight:600;color:var(--t1);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:72px}
.stock-right{display:flex;align-items:center;gap:5px;font-size:11px;flex-shrink:0}
.stock-amt{color:var(--t3);font-size:9.5px}
.breadth-wrap{background:var(--card);border-radius:10px;padding:12px 14px}
.breadth-bar{height:8px;background:rgba(255,64,96,.3);border-radius:4px;overflow:hidden;margin-bottom:8px}
.breadth-up{height:100%;background:var(--up);border-radius:4px}
.breadth-label{font-size:12px;display:flex;align-items:center}
.cal-row{display:flex;align-items:center;gap:8px;padding:8px 12px;background:var(--card);border-radius:8px;margin-bottom:5px}
.cal-name{font-size:12.5px;font-weight:600;color:var(--t1)}
.ai-brief-wrap{background:linear-gradient(135deg,rgba(167,139,250,.12),rgba(77,166,255,.08));border:1px solid rgba(167,139,250,.3);border-radius:12px;padding:14px}
.ai-brief-title{font-size:10px;color:var(--purple);font-weight:700;letter-spacing:.5px;margin-bottom:8px}
.ai-lines{margin-bottom:8px}
.ai-line{font-size:12.5px;color:var(--t1);line-height:1.7;font-weight:500}
.ai-tags{margin-bottom:6px}
.ai-tag{display:inline-block;font-size:11px;padding:3px 10px;border-radius:6px;font-weight:600}
.ai-tag.hot{background:rgba(255,201,64,.15);color:var(--gold);border:1px solid rgba(255,201,64,.3)}
.ai-supply{font-size:11px;color:var(--t2);padding-top:6px;border-top:1px solid rgba(255,255,255,.06)}
.macro-card{cursor:pointer;transition:opacity .15s}
.macro-card:active{opacity:.6}
.stock-story-wrap{display:flex;gap:10px;align-items:flex-start}
.stock-list-col{flex:0 0 44%;min-width:0}
.stock-story-col{flex:1;min-width:0}
.ss-sub-label{font-size:9px;color:var(--t3);text-transform:uppercase;letter-spacing:1px;margin-bottom:5px;padding-left:2px}
.ss-wrap{background:linear-gradient(135deg,rgba(255,201,64,.07),rgba(249,115,22,.05));border:1px solid rgba(255,201,64,.2);border-radius:12px;padding:12px;height:100%;box-sizing:border-box}
.ss-tone{font-size:11.5px;font-weight:700;color:var(--gold);margin-bottom:10px;padding-bottom:8px;border-bottom:1px solid var(--border);line-height:1.4}
.ss-block{margin-bottom:9px}.ss-block:last-child{margin-bottom:0}
.ss-label{font-size:9px;color:var(--gold);font-weight:700;letter-spacing:.5px;margin-bottom:4px}
.ss-theme{font-size:11px;font-weight:600;color:var(--t1);margin-bottom:3px}
.ss-text{font-size:10.5px;color:var(--t2);line-height:1.7}
.story-wrap{background:linear-gradient(135deg,rgba(77,166,255,.08),rgba(167,139,250,.06));border:1px solid rgba(77,166,255,.2);border-radius:12px;padding:14px}
.story-block{margin-bottom:10px}
.story-block:last-child{margin-bottom:0}
.story-label{font-size:10px;color:var(--blue);font-weight:700;letter-spacing:.5px;margin-bottom:5px}
.story-text{font-size:12px;color:var(--t2);line-height:1.75}
.mkt-sec-head{display:flex;align-items:center;gap:8px;margin-bottom:12px;padding-bottom:10px;border-bottom:1px solid var(--border)}
.mkt-sec-icon{font-size:15px}
.mkt-sec-title{font-size:14px;font-weight:700;color:var(--t1);flex:1}
.mkt-sec-num{font-size:10px;color:var(--t3);font-weight:700;background:var(--card2);padding:2px 7px;border-radius:6px}
.hashtag-row{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px}
.hashtag-pill{font-size:10.5px;color:var(--blue);background:rgba(77,166,255,.12);border:1px solid rgba(77,166,255,.25);border-radius:20px;padding:4px 10px;font-weight:600}
.highlight-list{margin-bottom:12px}
.highlight-item{display:flex;gap:8px;padding:7px 0;border-bottom:1px solid rgba(255,255,255,.04)}
.highlight-item:last-child{border-bottom:none}
.highlight-dot{color:var(--blue);font-size:13px;line-height:1.6;font-weight:700}
.highlight-title{font-size:12px;font-weight:700;color:var(--t1);margin-bottom:2px}
.highlight-desc{font-size:11px;color:var(--t2);line-height:1.6}
.asset-group-label{font-size:10px;color:var(--t3);font-weight:700;letter-spacing:.5px;margin:12px 0 6px}
.asset-group-label:first-of-type{margin-top:0}
.asset-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:6px}
.asset-grid.cols-3{grid-template-columns:repeat(3,1fr)}
.asset-card{background:var(--card2);border:1px solid var(--border);border-radius:10px;padding:8px 6px;text-align:center}
.asset-ticker{font-size:10.5px;font-weight:700;color:var(--t2)}
.asset-sub{font-size:8.5px;color:var(--t3);margin-top:1px}
.asset-pct{font-size:12px;font-weight:700;margin-top:4px}
.asset-pct.up{color:var(--up)}
.asset-pct.dn{color:var(--dn)}
.ticker-badge{display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;border-radius:50%;font-size:9.5px;font-weight:700;color:#fff;flex-shrink:0;background:linear-gradient(135deg,var(--blue),var(--purple))}
.mover-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px}
.mover-card{background:var(--card2);border:1px solid var(--border);border-radius:10px;padding:10px}
.mover-card.up-side{border-color:rgba(0,232,150,.2)}
.mover-card.dn-side{border-color:rgba(255,64,96,.2)}
.mover-head{font-size:10px;font-weight:700;margin-bottom:7px}
.mover-head.up{color:var(--up)}
.mover-head.dn{color:var(--dn)}
.mover-row{display:flex;align-items:center;gap:7px;padding:4px 0}
.mover-ticker{font-size:11px;font-weight:700;color:var(--t1);flex:1}
.mover-pct{font-size:11px;font-weight:700}
.earn-list{margin-bottom:10px}
.earn-item{display:flex;gap:8px;padding:8px 0;border-bottom:1px solid rgba(255,255,255,.04)}
.earn-item:last-child{border-bottom:none}
.earn-item.is-extra{display:none}
.earn-item.is-extra.show{display:flex}
.earn-body{flex:1;min-width:0}
.earn-head{font-size:11.5px;font-weight:700;color:var(--t1);margin-bottom:2px;line-height:1.5}
.earn-period{color:var(--t3);font-weight:600}
.earn-summary{font-size:10.5px;color:var(--t2);line-height:1.6}
.earn-more-btn{display:block;width:100%;text-align:center;font-size:10.5px;font-weight:700;color:var(--blue);background:rgba(77,166,255,.1);border:1px solid rgba(77,166,255,.2);border-radius:8px;padding:7px;margin-bottom:12px;cursor:pointer}
.report-card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:12px 14px;margin-bottom:8px}
.report-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:4px}
.report-stock{font-size:13px;font-weight:700;color:var(--t1)}
.report-firm{font-size:10px;color:var(--purple);background:rgba(167,139,250,.12);padding:2px 7px;border-radius:10px}
.report-title{font-size:11.5px;color:var(--t2);margin-bottom:7px;line-height:1.5}
.report-points{border-top:1px solid var(--border);padding-top:7px}
.report-point{font-size:11px;color:var(--t2);line-height:1.7}
#macroOverlay{position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:99;display:none;opacity:0;transition:opacity .25s}
#macroOverlay.open{opacity:1}
#macroModal{position:fixed;bottom:20px;left:8px;right:8px;max-width:480px;margin:0 auto;
background:var(--card2);border-radius:16px;padding:16px 16px 24px;z-index:100;
box-shadow:0 -4px 24px rgba(0,0,0,.6);transform:translateY(calc(100% + 28px));
transition:transform .28s cubic-bezier(.4,0,.2,1)}
#macroModal.open{transform:translateY(0)}
.us-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;padding:4px 0 12px}
.us-card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:12px}
.us-card-top{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px}
.us-name-wrap{display:flex;flex-direction:column}
.us-name{font-size:10px;color:var(--t3);font-weight:600}
.us-ticker-badge{font-size:8px;background:var(--card2);padding:1px 4px;border-radius:3px;color:var(--t3);margin-top:2px;align-self:flex-start}
.us-val-row{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}
.us-val{font-size:16px;font-weight:700;color:var(--t1)}
.us-pct-box{font-size:10px;padding:2px 6px;border-radius:4px;font-weight:700}
.us-pct-box.up{background:rgba(0,232,150,.12);color:var(--up)}
.us-pct-box.dn{background:rgba(255,64,96,.15);color:var(--dn)}
.rsi-wrap{margin-top:8px}
.rsi-head{font-size:9px;color:var(--t3);display:flex;justify-content:space-between;margin-bottom:4px}
.rsi-bg{height:4px;background:rgba(255,255,255,.05);border-radius:2px;overflow:hidden}
.rsi-fill{height:100%;background:var(--blue);border-radius:2px}
.fg-card-mini{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:12px;display:flex;align-items:center;gap:12px;margin-bottom:12px}
.fg-emoji{font-size:24px}
.fg-info{display:flex;flex-direction:column}
.fg-label{font-size:10px;color:var(--t3);margin-bottom:2px}
.fg-val-txt{font-size:18px;font-weight:800}
.us-fg-banner{border-radius:12px;padding:14px 16px;margin-top:12px;display:flex;align-items:center;gap:14px}
.us-fg-big{font-size:36px;line-height:1}
.us-fg-right{flex:1}
.us-fg-label{font-size:11px;letter-spacing:.5px;text-transform:uppercase;margin-bottom:2px;font-weight:600}
.us-fg-score{font-size:28px;font-weight:800;line-height:1.1}
.us-fg-desc{font-size:11px;margin-top:4px;opacity:.8}
.tech-row{display:flex;align-items:center;justify-content:space-between;padding:7px 0;border-bottom:1px solid rgba(255,255,255,.04)}
.tech-row:last-child{border-bottom:none}
.tech-name{font-size:11.5px;color:var(--t2)}
.tech-val{font-size:11px;font-weight:600}
.tech-sig{font-size:10px;padding:2px 7px;border-radius:3px;font-weight:700;margin-left:6px}
.wl-search{width:100%;box-sizing:border-box;background:var(--card);border:1px solid var(--border);border-radius:10px;padding:10px 14px;font-size:13px;color:var(--t1);outline:none;margin-bottom:2px}
.wl-search:focus{border-color:var(--blue)}
.wl-grid{display:flex;flex-direction:column;gap:8px}
.wl-card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:12px 14px;cursor:pointer;transition:border-color .15s}
.wl-card:active{border-color:var(--blue)}
.wl-card-top{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px}
.wl-name{font-size:13px;font-weight:700;color:var(--t1)}
.wl-ticker{font-size:10.5px;color:var(--t3);margin-top:2px}
.wl-mkt-badge{background:rgba(77,166,255,.15);color:var(--blue);font-size:9px;padding:1px 5px;border-radius:3px;font-weight:700}
.wl-price{font-size:16px;font-weight:700}
.wl-pct{font-size:11px;font-weight:600;text-align:right}
.wl-card-bot{display:flex;gap:12px;font-size:10.5px;color:var(--t3)}
#stockOverlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:300;transition:opacity .2s;opacity:0}
#stockOverlay.open{opacity:1}
#stockModal{position:fixed;bottom:0;left:0;right:0;max-width:480px;margin:0 auto;background:var(--card);border-radius:20px 20px 0 0;padding:20px 16px;z-index:301;max-height:88vh;overflow-y:auto;transform:translateY(100%);transition:transform .25s ease}
#stockModal.open{transform:translateY(0)}
.sk-price{font-size:24px;font-weight:800}
.sk-row{display:flex;justify-content:space-between;align-items:center;padding:7px 0;border-bottom:1px solid rgba(255,255,255,.05);font-size:12px}
.sk-row:last-child{border-bottom:none}
.sk-label{color:var(--t3)}
.sk-val{font-weight:600;color:var(--t1)}
.sk-sec{font-size:10px;color:var(--t3);text-transform:uppercase;letter-spacing:.8px;margin:12px 0 4px;padding-left:2px}
.perf-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:4px;margin-top:4px}
.perf-cell{background:var(--bg);border-radius:7px;padding:6px 4px;text-align:center}
.perf-period{font-size:9px;color:var(--t3);margin-bottom:2px}
.perf-val{font-size:11px;font-weight:700}
"""

# ── HTML 생성 ──────────────────────────────────────────────────────────────────

def _etf_row(e, show_amt=False):
    name = e.get('name', '')[:14]
    val  = e.get('val', 0)
    pct  = e.get('pct', 0)
    cls  = 'up-txt' if pct >= 0 else 'dn-txt'
    sign = '▲' if pct >= 0 else '▼'
    val_str = f"{val:,.0f}" if val > 0 else '-'
    right = f'<span class="stock-amt">{val_str}</span>'
    if show_amt:
        amt = e.get('amt', 0)
        amt_str = f"{amt/100000000:.0f}억" if amt >= 100000000 else f"{amt/100000000:.1f}억"
        right = f'<span class="stock-amt">{amt_str}</span>'
    return f'<div class="stock-row"><div class="stock-name">{name}</div><div class="stock-right"><span class="{cls}">{sign}{abs(pct):.2f}%</span>{right}</div></div>'


def generate_html(market, news, stocks, ai_brief, dt, usdkrw_week=None, macro_hist=None, research_summary=None, stock_story=None, investor_flow_story=None, us_ai_brief=None, watchlist=None, kr_sectors=None, etf_data=None, cnn_fear_greed=None, kr_news_insight=None, re_rates=None, re_news_insight=None, apt_trade=None, subscription=None, tracked_apt=None, upcoming_earnings=None):
    """최종 HTML 생성"""
    kdate = korean_date(dt)
    gen_time = dt.strftime("%H:%M 생성")

    import json as _json_wl
    watchlist_json = _json_wl.dumps(watchlist or [], ensure_ascii=False)

    # 업종별 등락률 카드 데이터 — KIS 실시간 우선, 없으면 기본값
    _default_sectors = [
        {'name': '전기전자', 'pct': 0.0}, {'name': '자동차', 'pct': 0.0},
        {'name': '금융',    'pct': 0.0}, {'name': '바이오',  'pct': 0.0},
        {'name': '화학',    'pct': 0.0}, {'name': '철강',    'pct': 0.0},
        {'name': '건설',    'pct': 0.0}, {'name': '에너지',  'pct': 0.0},
    ]

    kospi_pct = d(market, 'kospi').get('pct') or 0
    if kospi_pct >= 1.0:
        dom_cls, dom_ico = 'up', '📈'
    elif kospi_pct <= -1.0:
        dom_cls, dom_ico = 'dn', '📉'
    else:
        dom_cls, dom_ico = 'blue', '➖'

    dom_summary = build_dom_summary(market)
    us_summary  = (us_ai_brief or {}).get('story') or build_us_summary(market)

    # 환율 추이 차트
    if usdkrw_week and len(usdkrw_week) >= 2:
        import json as _json
        fx_curr  = usdkrw_week[-1]
        fx_start = usdkrw_week[0]
        fx_diff  = fx_curr - fx_start
        fx_color = '#ef4444' if fx_diff >= 0 else '#3b82f6'
        fx_rgb   = '239,68,68' if fx_diff >= 0 else '59,130,246'
        fx_sign  = '▲' if fx_diff >= 0 else '▼'
        fx_vals_json = _json.dumps(usdkrw_week)
        fx_card = f'''<div style="background:var(--card);border-radius:10px;padding:10px 12px;">
      <div style="font-size:10px;color:var(--t3);text-transform:uppercase;letter-spacing:.8px;margin-bottom:6px;">💱 환율 추이</div>
      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;">
        <div>
          <div style="font-size:18px;font-weight:700;color:{fx_color};">{fx_curr:,.0f}원</div>
          <div style="font-size:10px;color:var(--t3);margin-top:2px;">USD/KRW</div>
        </div>
        <div style="text-align:right;">
          <div style="font-size:12px;font-weight:600;color:{fx_color};">{fx_sign} {abs(fx_diff):.0f}원</div>
          <div style="font-size:9px;color:var(--t3);margin-top:2px;">7일 변동</div>
        </div>
      </div>
      <canvas id="fxChart" height="90"></canvas>
    </div>'''
        fx_script = f'''try{{(function(){{
  var c=document.getElementById('fxChart').getContext('2d');
  var v={fx_vals_json};
  var g=c.createLinearGradient(0,0,0,80);
  g.addColorStop(0,'rgba({fx_rgb},0.25)');
  g.addColorStop(1,'rgba({fx_rgb},0.02)');
  new Chart(c,{{
    type:'line',
    data:{{
      labels:v.map(function(){{return '';}}),
      datasets:[{{data:v,borderColor:'{fx_color}',backgroundColor:g,borderWidth:2,pointRadius:0,fill:true,tension:0.4}}]
    }},
    options:{{
      responsive:true,
      plugins:{{
        legend:{{display:false}},
        tooltip:{{callbacks:{{label:function(x){{return x.raw.toLocaleString()+'원';}}}}}}
      }},
      scales:{{
        x:{{display:false}},
        y:{{
          grid:{{color:'rgba(255,255,255,0.06)'}},
          ticks:{{color:'#6a80aa',font:{{size:9}},callback:function(x){{return x.toLocaleString();}}}},
          border:{{color:'rgba(255,255,255,0.08)'}}
        }}
      }}
    }}
  }});
}})();}}catch(e){{console.warn('fxChart init failed:',e);}}'''
    else:
        fx_card   = ''
        fx_script = ''
    fg_value = calc_fear_greed(market, stocks)
    fg_card  = fear_greed_html(fg_value)

    import json as _json2
    macro_meta = {
        'kospi':  {'name':'코스피',      'color':'#ef4444','rgb':'239,68,68',   'pre':'',  'suf':'', 'dec':2},
        'kosdaq': {'name':'코스닥',      'color':'#3b82f6','rgb':'59,130,246',  'pre':'',  'suf':'', 'dec':2},
        'sp500':  {'name':'S&P 500',    'color':'#00e896','rgb':'0,232,150',   'pre':'',  'suf':'', 'dec':2},
        'nasdaq': {'name':'나스닥 100', 'color':'#4da6ff','rgb':'77,166,255',  'pre':'',  'suf':'', 'dec':2},
        'dow':    {'name':'다우존스',   'color':'#a78bfa','rgb':'167,139,250', 'pre':'',  'suf':'', 'dec':2},
        'vix':    {'name':'VIX',        'color':'#ffc940','rgb':'255,201,64',  'pre':'',  'suf':'', 'dec':2},
        'usdkrw': {'name':'USD/KRW',    'color':'#ef4444','rgb':'239,68,68',   'pre':'',  'suf':'원','dec':0},
        'brent':  {'name':'브렌트유',    'color':'#f97316','rgb':'249,115,22',  'pre':'$', 'suf':'', 'dec':1},
        'wti':    {'name':'WTI',         'color':'#f97316','rgb':'249,115,22',  'pre':'$', 'suf':'', 'dec':1},
        'tnx':    {'name':'미 10년물',   'color':'#4da6ff','rgb':'77,166,255',  'pre':'',  'suf':'%','dec':2},
        'gold':   {'name':'금 선물',     'color':'#ffc940','rgb':'255,201,64',  'pre':'$', 'suf':'', 'dec':0},
        'dxy':    {'name':'달러 인덱스', 'color':'#a78bfa','rgb':'167,139,250', 'pre':'',  'suf':'', 'dec':2},
        'btc':    {'name':'비트코인',    'color':'#f59e0b','rgb':'245,158,11',  'pre':'$', 'suf':'', 'dec':0},
    }
    macro_meta_json = _json2.dumps(macro_meta, ensure_ascii=False)
    macro_hist_json = _json2.dumps(macro_hist or {})

    ai_extra = ''
    ai_html = ''

    # 시황 분석 보조 콘텐츠 (해시태그 / 하이라이트 / 전망 / 업종 서사)
    dom_hashtags_html = ''
    dom_highlights_html = ''
    dom_outlook_html = ''
    sector_story = ''
    if ai_brief:
        for tag in ai_brief.get('hashtags', []):
            dom_hashtags_html += f'<span class="hashtag-pill">{tag}</span>'
        for hl in ai_brief.get('highlights', []):
            dom_highlights_html += f'''<div class="highlight-item">
  <div class="highlight-dot">·</div>
  <div>
    <div class="highlight-title">{hl.get('title','')}</div>
    <div class="highlight-desc">{hl.get('desc','')}</div>
  </div>
</div>'''
        d_out = ai_brief.get('outlook', '')
        if d_out:
            dom_outlook_html = f'''<div class="story-block" style="margin-top:10px">
      <div class="story-label" style="color: var(--blue);">🔭 향후 전망</div>
      <div class="story-text">{d_out}</div>
    </div>'''
        sector_story = ai_brief.get('sector_story', '')

    # 스토리형 시황 분석 섹션
    if ai_brief:
        story = ai_brief.get('story', '')
        story_html = f'''<div class="section">
  <div class="story-wrap">
    <div class="mkt-sec-head">
      <span class="mkt-sec-icon">🇰🇷</span>
      <span class="mkt-sec-title">시장 요약</span>
      <span class="mkt-sec-num">01</span>
    </div>
    <div class="hashtag-row">{dom_hashtags_html}</div>
    <div class="highlight-list">{dom_highlights_html}</div>
    <div class="story-text">{story}</div>
    {dom_outlook_html}
  </div>
</div>'''
    else:
        story_html = ''

    # 주도주 스토리 HTML
    if stock_story:
        stock_story_html = f'''<div class="ss-wrap">
  <div class="ss-tone">{stock_story.get('market_tone','')}</div>
  <div class="ss-block">
    <div class="ss-label">🔥 주도 테마</div>
    <div class="ss-theme">{stock_story.get('theme','')}</div>
    <div class="ss-text">{stock_story.get('theme_reason','')}</div>
  </div>
  <div class="ss-block">
    <div class="ss-label">💰 큰 돈의 흐름</div>
    <div class="ss-text">{stock_story.get('money_flow','')}</div>
  </div>
</div>'''
    else:
        stock_story_html = ''

    # 증권사 리포트 HTML
    if research_summary:
        rp_list = research_summary.get('reports', []) if isinstance(research_summary, dict) else research_summary
        rp_insight = research_summary.get('insight', '') if isinstance(research_summary, dict) else ''
        cards = ''
        for rp in rp_list:
            url = rp.get('url', '')
            link_open  = f'<a href="{url}" target="_blank" style="text-decoration:none;display:block">' if url else '<div>'
            link_close = '</a>' if url else '</div>'
            cards += f'''{link_open}<div class="report-card">
  <div class="report-header">
    <span class="report-stock">{rp.get('stock','')}</span>
    <span class="report-firm">{rp.get('firm','')}</span>
  </div>
  <div class="report-title">{rp.get('title','')}</div>
  <div class="report-points">
    <div class="report-point">· {rp.get('point1','')}</div>
    <div class="report-point">· {rp.get('point2','')}</div>
  </div>
</div>{link_close}'''
        rp_insight_html = f'<div class="story-text" style="margin-top:12px">{rp_insight}</div>' if rp_insight else ''
        research_html = f'''<div class="section"><div class="story-wrap">
  <div class="mkt-sec-head">
    <span class="mkt-sec-icon">📋</span>
    <span class="mkt-sec-title">오늘의 증권사 리포트</span>
    <span class="mkt-sec-num">04</span>
  </div>
  {cards}{rp_insight_html}
</div></div>'''
    else:
        research_html = ''

    dom_news = news_html(news.get('domestic', []), 'nb-blue', '국내')
    int_news = news_html(news.get('international', []), 'nb-blue', '해외')
    re_news  = news_html(news.get('realestate', []),  'nb-orange', '부동산', 'var(--orange)')

    # 금리 카드 HTML
    def _rate_card(label, val, unit='%', sub=''):
        if val is None:
            return f'<div class="macro-card"><div class="macro-name">{label}</div><div class="macro-val" style="color:var(--t3)">-</div><div class="macro-chg" style="font-size:9px;color:var(--t3)">{sub}</div></div>'
        color = 'var(--dn)' if val >= 4.0 else 'var(--up)' if val < 3.0 else 'var(--gold)'
        return f'<div class="macro-card"><div class="macro-name">{label}</div><div class="macro-val" style="color:{color}">{val:.2f}{unit}</div><div class="macro-chg" style="font-size:9px;color:var(--t3)">{sub}</div></div>'

    rr = re_rates or {}
    base_date = rr.get('base_rate_date', '')
    mort_date = rr.get('mortgage_date', '').replace('M', '년 ') + '월' if rr.get('mortgage_date') else ''
    re_rate_html = f'''<div class="macro-grid">
  {_rate_card('한은 기준금리', rr.get('base_rate'), sub=base_date)}
  {_rate_card('국고채 3년', rr.get('bond_3y'), sub='시장금리')}
  {_rate_card('국고채 10년', rr.get('bond_10y'), sub='장기금리')}
  {_rate_card('주담대 금리', rr.get('mortgage_rate'), sub=mort_date+' 신규취급')}
  {_rate_card('전세자금대출', rr.get('jeonse_rate'), sub=mort_date+' 신규취급')}
</div>
<div style="font-size:10px;color:var(--t3);margin-top:8px;">출처: 한국은행 ECOS · <a href="https://ecos.bok.or.kr" target="_blank" style="color:var(--t3)">ecos.bok.or.kr</a></div>'''

    # 실거래 동향 HTML
    if apt_trade:
        ym_str = apt_trade[0]['ym'] if apt_trade else ''
        ym_label = f"{ym_str[:4]}년 {int(ym_str[4:]):}월" if len(ym_str)==6 else ym_str
        rows = ''.join(
            f'<tr><td><strong>{t["name"]}</strong></td>'
            f'<td style="text-align:right">{t["avg"]:,}만원</td>'
            f'<td style="text-align:right;color:var(--t3)">{t["count"]}건</td></tr>'
            for t in apt_trade
        )
        apt_trade_html = f'''<div style="font-size:10px;color:var(--t3);margin-bottom:6px;">서울 주요 구 평균 · {ym_label}</div>
<table class="apt-table">
  <thead><tr><th>구</th><th>평균가</th><th>거래량</th></tr></thead>
  <tbody>{rows}</tbody>
</table>
<div style="font-size:10px;color:var(--t3);margin-top:6px;">출처: 국토교통부 실거래가 · <a href="https://rt.molit.go.kr" target="_blank" style="color:var(--t3)">rt.molit.go.kr</a></div>'''
    else:
        apt_trade_html = '<div style="color:var(--t3);font-size:12px;padding:12px 0;">데이터 수집 중</div>'

    # 청약 일정 HTML
    if subscription:
        def _fmt_date(d):
            return f"{d[:4]}.{d[4:6]}.{d[6:]}" if len(d)==8 else d
        sub_rows = ''.join(
            f'<div class="apt-card" style="margin-bottom:8px;padding:10px 12px">'
            f'<div style="font-size:13px;font-weight:700;color:var(--t1);margin-bottom:4px">{s["name"]}</div>'
            f'<div style="font-size:11px;color:var(--t3);margin-bottom:4px">{s["area"]}</div>'
            f'<div style="font-size:11px;color:var(--gold)">청약: {_fmt_date(s["rcpt_bgn"])} ~ {_fmt_date(s["rcpt_end"])}</div>'
            f'</div>'
            for s in subscription[:4]
        )
        subscription_html = sub_rows or '<div style="color:var(--t3);font-size:12px;padding:8px 0;">일정 없음</div>'
    else:
        subscription_html = '<div style="color:var(--t3);font-size:12px;padding:8px 0;">데이터 수집 중</div>'

    # 관심 단지 HTML 빌더
    def _apt_card(apt_cfg, pyeong_data):
        rows = ''
        latest_date = ''
        for py in (pyeong_data or []):
            amt_cell = py['amt'] if py['amt'] else '<span style="color:var(--t3)">거래없음</span>'
            rows += f'<tr><td><strong>{py["label"]}</strong> {py["area_label"]}</td><td>{amt_cell}</td></tr>'
            if py.get('date'):
                latest_date = py['date']
        header_label = f'실거래 ({latest_date})' if latest_date else '실거래 (정보없음)'
        table = f'''<table class="apt-table">
          <thead><tr><th>평형</th><th>{header_label}</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>'''
        remodel_html = ''
        if apt_cfg.get('remodel_steps'):
            steps = ''.join(
                f'<div class="step-row step-{s}"><div class="step-dot"></div><div class="step-text">{t}</div></div>'
                for s, t in apt_cfg['remodel_steps']
            )
            remodel_html = f'<div class="remodel-steps"><div class="remodel-label">리모델링 진행 — {apt_cfg.get("remodel","")}</div>{steps}</div>'
        return f'''<div class="apt-card">
          <div class="apt-header">
            <div>
              <div class="apt-name">{apt_cfg["name"]}</div>
              <div class="apt-info">{apt_cfg["info"]}</div>
            </div>
            <div class="apt-status {apt_cfg["status_cls"]}">{apt_cfg["status"]}</div>
          </div>
          {table}
          {remodel_html}
          <div class="invest-point">📍 {apt_cfg["note"]}<br>
            <span class="warn">⚠ 최신 실거래가는 호갱노노·KB부동산에서 확인</span>
          </div>
        </div>'''

    tracked_apt_html = ''
    for apt_cfg in TRACKED_APTS:
        pyeong_data = (tracked_apt or {}).get(apt_cfg['name'])
        tracked_apt_html += _apt_card(apt_cfg, pyeong_data)

    hot_news = news_html(news.get('hot', []),          'nb-red',  '이슈')

    # 주도주 & 체감
    if stocks:
        breadth = stocks.get('breadth', {})
        b_up    = breadth.get('up', 0)
        b_dn    = breadth.get('down', 0)
        b_total = b_up + b_dn + breadth.get('flat', 0)
        b_up_pct = f"{b_up/b_total*100:.0f}" if b_total else '–'
        b_up_pct_w = (b_up/b_total*100) if b_total else 0
        breadth_html = f'''<div class="breadth-wrap">
  <div class="breadth-bar">
    <div class="breadth-up" style="width:{b_up_pct_w:.1f}%"></div>
  </div>
  <div class="breadth-label">
    <span class="up-txt">▲ {b_up}개 상승</span>
    <span style="color:var(--t3);margin:0 6px;">|</span>
    <span class="dn-txt">▼ {b_dn}개 하락</span>
    <span style="color:var(--t3);font-size:10px;margin-left:6px;">전체 {b_total}개</span>
  </div>
</div>'''
        top_amt_html     = stocks_html(stocks.get('top_amt', []))
        foreign_buy_html = stocks_html(stocks.get('foreign_buy', []))
        inst_buy_html    = stocks_html(stocks.get('inst_buy', []))
        high_52w_html    = stocks_html(stocks.get('high_52w', []))
    else:
        breadth_html     = '<div style="color:var(--t3);font-size:12px;padding:8px 0;">데이터 없음</div>'
        top_amt_html     = breadth_html
        foreign_buy_html = breadth_html
        inst_buy_html    = breadth_html
        high_52w_html    = breadth_html

    # ETF HTML
    no_data = '<div style="color:var(--t3);font-size:12px;padding:8px 0;">데이터 없음</div>'
    etf = etf_data or {}
    major_etf_html  = ''.join(_etf_row(e) for e in etf.get('major', [])) or no_data
    popular_etf_html = ''.join(_etf_row(e) for e in etf.get('popular', [])) or no_data
    volume_etf_html  = ''.join(_etf_row(e, show_amt=True) for e in etf.get('volume', [])) or no_data
    theme_etf_html = ''
    for t in etf.get('themes', []):
        rows = ''.join(_etf_row(e) for e in t.get('etfs', []))
        theme_etf_html += f'<div class="stock-list-col"><div class="ss-sub-label">{t["theme"]}</div>{rows}</div>'
    if not theme_etf_html:
        theme_etf_html = no_data

    # 캘린더 - 경기 지표
    cal_events = get_weekly_calendar(dt)
    if cal_events:
        cal_html = ''.join(f'''<div class="cal-row">
  <span class="news-badge {e["badge"]}">{e["label"]}</span>
  <span class="cal-name">{e["name"]}</span>
</div>''' for e in cal_events)
    else:
        cal_html = '<div style="color:var(--t3);font-size:12px;padding:8px 0;">이번 주 주요 지표 일정 없음</div>'

    # 캘린더 - 실적 발표 예정
    if upcoming_earnings:
        earn_cal_html = ''.join(f'''<div class="cal-row">
  <span class="news-badge {e["badge"]}">{e["label"]}</span>
  <span class="cal-name" style="font-weight:700">{e["symbol"]}</span>
  <span style="font-size:10px;color:var(--t3);margin-left:4px;">{e["year"]}Q{e["quarter"]} · EPS 예상 {e["eps_estimate"]}</span>
</div>''' for e in upcoming_earnings)
    else:
        earn_cal_html = '<div style="color:var(--t3);font-size:12px;padding:8px 0;">이번 주 주요 실적 발표 없음</div>'


    # 미국 공포/탐욕 지수 (CNN 실제 지수 우선, 실패 시 자체 추정치로 대체)
    us_fg = cnn_fear_greed if cnn_fear_greed is not None else calc_us_fear_greed(market)

    # 테마에 따른 이모지 및 라벨 설정
    if us_fg <= 25: 
        us_fg_emoji, us_fg_label, us_fg_color = '💀', '극도공포', '#3b82f6'
    elif us_fg <= 45:
        us_fg_emoji, us_fg_label, us_fg_color = '😨', '공포', '#60a5fa'
    elif us_fg <= 55:
        us_fg_emoji, us_fg_label, us_fg_color = '😐', '중립', '#a3a3a3'
    elif us_fg <= 75:
        us_fg_emoji, us_fg_label, us_fg_color = '😊', '탐욕', '#f97316'
    else:
        us_fg_emoji, us_fg_label, us_fg_color = '🤑', '극탐욕', '#ef4444'

    # 해외 AI 브리핑 HTML
    # 해외 AI 브리핑 보조 콘텐츠 (해시태그 / 하이라이트 / 전망 / 자산동향 narrative)
    us_hashtags_html = ''
    us_highlights_html = ''
    us_outlook_html = ''
    us_asset_story = ''
    if us_ai_brief:
        for tag in us_ai_brief.get('hashtags', []):
            us_hashtags_html += f'<span class="hashtag-pill">{tag}</span>'
        for hl in us_ai_brief.get('highlights', []):
            us_highlights_html += f'''<div class="highlight-item">
  <div class="highlight-dot">·</div>
  <div>
    <div class="highlight-title">{hl.get('title','')}</div>
    <div class="highlight-desc">{hl.get('desc','')}</div>
  </div>
</div>'''
        u_out = us_ai_brief.get('outlook', '')
        if u_out:
            us_outlook_html = f'''<div class="story-block" style="margin-top:10px">
      <div class="story-label" style="color: var(--blue);">🔭 향후 전망</div>
      <div class="story-text">{u_out}</div>
    </div>'''
        us_asset_story = us_ai_brief.get('sector_story', '')

    # 섹터 & 자산 동향 카드 그리드 HTML
    def _asset_card(ticker, sub, pct, chart_symbol=None):
        cls = 'up' if pct >= 0 else 'dn'
        sign = '+' if pct >= 0 else ''
        sub_html = f'<div class="asset-sub">{sub}</div>' if sub else ''
        card_attrs = f' onclick="openChart(\'{chart_symbol}\')" style="cursor:pointer"' if chart_symbol else ''
        chart_ico = ' 📈' if chart_symbol else ''
        return f'''<div class="asset-card"{card_attrs}>
  <div class="asset-ticker">{ticker}{chart_ico}</div>
  {sub_html}
  <div class="asset-pct {cls}">{sign}{pct:.2f}%</div>
</div>'''

    asset_sectors_html = ''.join(
        _asset_card(k.upper(), name, d(market, k).get('pct', 0) or 0)
        for k, name in US_SECTOR_MAP.items()
    )
    asset_bonds_html = ''.join(
        _asset_card(ticker, label, d(market, k).get('pct', 0) or 0)
        for k, (ticker, label) in US_BOND_MAP.items()
    )
    asset_commodities_html = ''.join(
        _asset_card(ticker, label, d(market, k).get('pct', 0) or 0)
        for k, (ticker, label) in US_COMMODITY_MAP.items()
    )

    # 국내 업종별 등락률 카드 그리드 (KIS 실시간 데이터 우선, 없으면 기본값)
    dom_sectors_html = ''.join(
        _asset_card(s['name'], '', s.get('pct', 0) or 0)
        for s in (kr_sectors if kr_sectors else _default_sectors)
    )

    # ③ 주요 종목 동향 — 매그니피센트 7 카드 그리드
    mag7_html = ''.join(
        _asset_card(k.upper(), name, d(market, k).get('pct', 0) or 0, chart_symbol=f"{US_EXCHANGE_MAP.get(k,'NASDAQ')}:{k.upper()}")
        for k, name in MAG7_MAP.items()
    )

    # 급등/급락 Top 3 (주요 종목 + 매그니피센트7 통합 유니버스에서 산출)
    us_universe = {**US_STOCK_MAP, **MAG7_MAP}
    us_universe_sorted = sorted(
        [(k, d(market, k).get('pct', 0) or 0) for k in us_universe],
        key=lambda x: x[1], reverse=True
    )
    def _mover_row(k, pct):
        cls = 'up' if pct >= 0 else 'dn'
        sign = '+' if pct >= 0 else ''
        ex = US_EXCHANGE_MAP.get(k, 'NASDAQ')
        return f'''<div class="mover-row" onclick="openChart('{ex}:{k.upper()}')" style="cursor:pointer">
  <div class="ticker-badge">{k.upper()[:2]}</div>
  <div class="mover-ticker">{k.upper()} 📈</div>
  <div class="mover-pct {cls}">{sign}{pct:.2f}%</div>
</div>'''

    us_movers_gainers_html = ''.join(_mover_row(k, p) for k, p in us_universe_sorted[:3])
    us_movers_losers_html  = ''.join(_mover_row(k, p) for k, p in us_universe_sorted[-3:][::-1])

    # 최근 실적 리뷰 (AI 생성)
    earnings_reviews_html = ''
    earn_extra_count = 0
    if us_ai_brief:
        reviews = us_ai_brief.get('earnings_reviews', [])
        for i, rv in enumerate(reviews):
            extra_cls = ' is-extra' if i >= 2 else ''
            company = rv.get('company', '')
            ticker = rv.get('ticker', '')
            period = rv.get('period', '')
            summary = rv.get('summary', '')
            earnings_reviews_html += f'''<div class="earn-item{extra_cls}">
  <div class="ticker-badge">{ticker[:2].upper()}</div>
  <div class="earn-body">
    <div class="earn-head">{company}({ticker}) <span class="earn-period">{period}</span></div>
    <div class="earn-summary">{summary}</div>
  </div>
</div>'''
        earn_extra_count = max(0, len(reviews) - 2)
    earn_more_html = ''
    if earn_extra_count > 0:
        earn_more_html = f'''<div class="earn-more-btn" data-more-label="▼ {earn_extra_count}개 더 보기" data-less-label="▲ 접기" onclick="toggleEarnMore(this)">▼ {earn_extra_count}개 더 보기</div>'''

    us_stock_story = (us_ai_brief or {}).get('stock_story', '')

    # 기술적 신호
    def _rsi_signal(rsi):
        if rsi >= 70:   return '과매수', '#ff4060', 'rgba(255,64,96,.15)'
        elif rsi <= 30: return '과매도', '#00e896', 'rgba(0,232,150,.15)'
        elif rsi >= 60: return '강세',   '#00e896', 'rgba(0,232,150,.12)'
        elif rsi <= 40: return '약세',   '#ff8c3a', 'rgba(255,140,58,.15)'
        else:           return '중립',   '#a3a3a3', 'rgba(163,163,163,.12)'

    def _macd_signal(pct):
        if pct > 0.5:    return '골든크로스', '#00e896', 'rgba(0,232,150,.15)'
        elif pct < -0.5: return '데드크로스', '#ff4060', 'rgba(255,64,96,.15)'
        else:            return '수렴',       '#a3a3a3', 'rgba(163,163,163,.12)'

    sp_rsi = d(market,'sp500').get('rsi', 50)
    nd_rsi = d(market,'nasdaq').get('rsi', 50)
    dw_rsi = d(market,'dow').get('rsi', 50)
    sp_pct = d(market,'sp500').get('pct', 0)
    nd_pct = d(market,'nasdaq').get('pct', 0)
    sp_rsi_lbl, sp_rsi_col, sp_rsi_bg = _rsi_signal(sp_rsi)
    nd_rsi_lbl, nd_rsi_col, nd_rsi_bg = _rsi_signal(nd_rsi)
    dw_rsi_lbl, dw_rsi_col, dw_rsi_bg = _rsi_signal(dw_rsi)
    sp_macd_lbl, sp_macd_col, sp_macd_bg = _macd_signal(sp_pct)
    nd_macd_lbl, nd_macd_col, nd_macd_bg = _macd_signal(nd_pct)

    # BB 신호: VIX 기반
    vix_val = d(market,'vix').get('val') or 20
    if vix_val > 30:   bb_lbl, bb_col, bb_bg = '하단밴드 이탈', '#ff4060', 'rgba(255,64,96,.15)'
    elif vix_val < 15: bb_lbl, bb_col, bb_bg = '상단밴드 근접', '#f97316', 'rgba(255,140,58,.15)'
    else:              bb_lbl, bb_col, bb_bg = '밴드 내 정상',  '#a3a3a3', 'rgba(163,163,163,.12)'

    us_tech_html = f'''<div class="tech-row">
  <div class="tech-name">S&amp;P 500 RSI ({sp_rsi})</div>
  <div style="display:flex;align-items:center">
    <div class="rsi-bg" style="width:60px;margin-right:8px"><div class="rsi-fill" style="width:{sp_rsi}%"></div></div>
    <span class="tech-sig" style="background:{sp_rsi_bg};color:{sp_rsi_col}">{sp_rsi_lbl}</span>
  </div>
</div>
<div class="tech-row">
  <div class="tech-name">나스닥 RSI ({nd_rsi})</div>
  <div style="display:flex;align-items:center">
    <div class="rsi-bg" style="width:60px;margin-right:8px"><div class="rsi-fill" style="width:{nd_rsi}%"></div></div>
    <span class="tech-sig" style="background:{nd_rsi_bg};color:{nd_rsi_col}">{nd_rsi_lbl}</span>
  </div>
</div>
<div class="tech-row">
  <div class="tech-name">다우존스 RSI ({dw_rsi})</div>
  <div style="display:flex;align-items:center">
    <div class="rsi-bg" style="width:60px;margin-right:8px"><div class="rsi-fill" style="width:{dw_rsi}%"></div></div>
    <span class="tech-sig" style="background:{dw_rsi_bg};color:{dw_rsi_col}">{dw_rsi_lbl}</span>
  </div>
</div>
<div class="tech-row">
  <div class="tech-name">S&amp;P 500 MACD</div>
  <span class="tech-sig" style="background:{sp_macd_bg};color:{sp_macd_col}">{sp_macd_lbl}</span>
</div>
<div class="tech-row">
  <div class="tech-name">나스닥 MACD</div>
  <span class="tech-sig" style="background:{nd_macd_bg};color:{nd_macd_col}">{nd_macd_lbl}</span>
</div>
<div class="tech-row">
  <div class="tech-name">볼린저밴드 (VIX {vix_val:.1f})</div>
  <span class="tech-sig" style="background:{bb_bg};color:{bb_col}">{bb_lbl}</span>
</div>'''

    # 공포/탐욕 큰 배너 HTML
    if us_fg <= 25:
        fg_bg = 'rgba(59,130,246,.12)'; fg_border = '#3b82f6'; fg_label = '극도 공포'
    elif us_fg <= 45:
        fg_bg = 'rgba(96,165,250,.1)';  fg_border = '#60a5fa'; fg_label = '공포'
    elif us_fg <= 55:
        fg_bg = 'rgba(163,163,163,.1)'; fg_border = '#a3a3a3'; fg_label = '중립'
    elif us_fg <= 75:
        fg_bg = 'rgba(249,115,22,.1)';  fg_border = '#f97316'; fg_label = '탐욕'
    else:
        fg_bg = 'rgba(239,68,68,.12)';  fg_border = '#ef4444'; fg_label = '극도 탐욕'

    us_fg_banner_html = f'''<div class="us-fg-banner" style="background:{fg_bg};border:1px solid {fg_border};">
  <div class="us-fg-big">{us_fg_emoji}</div>
  <div class="us-fg-right">
    <div class="us-fg-label" style="color:{fg_border}">미국 공포/탐욕 지수</div>
    <div class="us-fg-score" style="color:{fg_border}">{us_fg} <span style="font-size:16px">{fg_label}</span></div>
    <div class="us-fg-desc" style="color:{fg_border}">VIX {vix_val:.1f} &nbsp;·&nbsp; S&amp;P RSI {sp_rsi} &nbsp;·&nbsp; 나스닥 모멘텀 {nd_pct:+.2f}%</div>
  </div>
</div>'''

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=1.0">
<meta name="theme-color" content="#080b10">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="국장 대시보드">
<link rel="manifest" href="manifest.json">
<link rel="apple-touch-icon" href="icon-192.png">
<title>국장 대시보드 · {dt.month}월 {dt.day}일</title>
<style>{CSS}</style>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2/dist/chartjs-plugin-datalabels.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/lightweight-charts@4.1.7/dist/lightweight-charts.standalone.production.js"></script>
</head>
<body>

<div class="header">
  <div>
    <div class="header-title">📈 국내 주식</div>
    <div class="header-date">{kdate}</div>
    <div class="header-day">장 마감 기준</div>
  </div>
  <div class="header-right">
    {gen_time}<br>
    <div style="display:flex;gap:4px;margin-top:5px;justify-content:flex-end;">
      <button class="update-btn" id="refreshBtn" onclick="doReload()">↻ 새로고침</button>
      <button class="update-btn" id="updBtn" onclick="triggerUpdate()">지금 업데이트</button>
    </div>
    <span class="update-status" id="updStatus"></span>
  </div>
</div>

<nav class="tab-nav">
  <button class="tab-btn active" onclick="sw('dom',this)">📈 국내</button>
  <button class="tab-btn" onclick="sw('us',this)">🌐 해외</button>
  <button class="tab-btn" onclick="sw('re',this)">🏠 부동산</button>
  <button class="tab-btn" onclick="sw('hot',this)">🔥 핫이슈</button>
  <button class="tab-btn" onclick="sw('cal',this)">📅 일정</button>
  <button class="tab-btn" onclick="sw('watch',this)">📊 종목</button>
  <button class="tab-btn" onclick="sw('etf',this)">📦 ETF</button>
</nav>

<!-- ===== 국내 탭 ===== -->
<div id="tab-dom" class="tab-panel active">

  <div class="section">
    {us_fg_banner_html}
    <div class="banner {dom_cls}">
      <strong>{dom_ico} 오늘 시황</strong><br>
      <span style="display:block;margin-bottom:4px;">코스피 &nbsp;<strong>{vdisp(market,'kospi')}</strong> &nbsp;{cdisp(market,'kospi')}</span>
      <span style="display:block;margin-bottom:6px;">코스닥 &nbsp;<strong>{vdisp(market,'kosdaq')}</strong> &nbsp;{cdisp(market,'kosdaq')}</span>
      <span style="font-size:11.5px;opacity:.9;line-height:1.6">{dom_summary}</span>
    </div>
  </div>

  <div class="section">
    <div class="section-label">00 · 주요 지수 <span style="font-size:9px;color:var(--t3);font-weight:400;">탭하면 추이 차트</span></div>
    <div class="asset-group-label">🇰🇷 국내 지수</div>
    <div class="index-grid">
      <div class="idx-card" onclick="showMacroChart('kospi')" style="cursor:pointer">
        <div class="idx-name">코스피 <span style="font-size:9px;color:var(--t3);">추이 ›</span></div>
        <div class="idx-val">{vdisp(market,'kospi')}</div>
        <div class="idx-chg">{cdisp(market,'kospi')}</div>
      </div>
      <div class="idx-card" onclick="showMacroChart('kosdaq')" style="cursor:pointer">
        <div class="idx-name">코스닥 <span style="font-size:9px;color:var(--t3);">추이 ›</span></div>
        <div class="idx-val">{vdisp(market,'kosdaq')}</div>
        <div class="idx-chg">{cdisp(market,'kosdaq')}</div>
      </div>
    </div>
    <div class="asset-group-label">🇺🇸 미국 주요 지수</div>
    <div class="index-grid">
      <div class="idx-card" onclick="showMacroChart('nasdaq')" style="cursor:pointer">
        <div class="idx-name">나스닥 100</div>
        <div class="idx-val">{vdisp(market,'nasdaq')}</div>
        <div class="idx-chg">{cdisp(market,'nasdaq')}</div>
      </div>
      <div class="idx-card" onclick="showMacroChart('sp500')" style="cursor:pointer">
        <div class="idx-name">S&amp;P 500</div>
        <div class="idx-val">{vdisp(market,'sp500')}</div>
        <div class="idx-chg">{cdisp(market,'sp500')}</div>
      </div>
      <div class="idx-card" onclick="showMacroChart('vix')" style="cursor:pointer">
        <div class="idx-name">VIX <span style="font-size:9px;color:var(--t3);">공포지수</span></div>
        <div class="idx-val">{vdisp(market,'vix')}</div>
        <div class="idx-chg">{cdisp(market,'vix')}</div>
      </div>
      <div class="idx-card" onclick="showMacroChart('dow')" style="cursor:pointer">
        <div class="idx-name">다우존스</div>
        <div class="idx-val">{vdisp(market,'dow')}</div>
        <div class="idx-chg">{cdisp(market,'dow')}</div>
      </div>
    </div>
    <div class="asset-group-label">🌐 글로벌 매크로</div>
    <div class="macro-grid">
      <div class="macro-card" onclick="showMacroChart('usdkrw')">
        <div class="macro-name">USD/KRW</div>
        <div class="macro-val">{vdisp(market,'usdkrw')}</div>
        <div class="macro-chg">{cdisp(market,'usdkrw')}</div>
      </div>
      <div class="macro-card" onclick="showMacroChart('brent')">
        <div class="macro-name">브렌트유</div>
        <div class="macro-val">{vdisp(market,'brent')}</div>
        <div class="macro-chg">{cdisp(market,'brent')}</div>
      </div>
      <div class="macro-card" onclick="showMacroChart('wti')">
        <div class="macro-name">WTI</div>
        <div class="macro-val">{vdisp(market,'wti')}</div>
        <div class="macro-chg">{cdisp(market,'wti')}</div>
      </div>
      <div class="macro-card" onclick="showMacroChart('gold')">
        <div class="macro-name">금 선물</div>
        <div class="macro-val">{vdisp(market,'gold')}</div>
        <div class="macro-chg">{cdisp(market,'gold')}</div>
      </div>
      <div class="macro-card" onclick="showMacroChart('dxy')">
        <div class="macro-name">달러 인덱스</div>
        <div class="macro-val">{vdisp(market,'dxy')}</div>
        <div class="macro-chg">{cdisp(market,'dxy')}</div>
      </div>
      <div class="macro-card" onclick="showMacroChart('btc')">
        <div class="macro-name">🪙 비트코인</div>
        <div class="macro-val">{vdisp(market,'btc')}</div>
        <div class="macro-chg">{cdisp(market,'btc')}</div>
      </div>
    </div>
  </div>

  {story_html}

  <div class="section">
    <div class="story-wrap">
      <div class="mkt-sec-head">
        <span class="mkt-sec-icon">🏭</span>
        <span class="mkt-sec-title">업종 동향</span>
        <span class="mkt-sec-num">02</span>
      </div>
      <div class="asset-group-label">📁 주요 업종</div>
      <div class="asset-grid">{dom_sectors_html}</div>
      <div class="story-text" style="margin-top:12px">{sector_story}</div>
    </div>
  </div>

  <div class="section">
    <div class="story-wrap">
      <div class="mkt-sec-head">
        <span class="mkt-sec-icon">💰</span>
        <span class="mkt-sec-title">투자자 동향</span>
        <span class="mkt-sec-num">03</span>
      </div>
      <div class="asset-group-label">📊 시장 체감 온도</div>
      {breadth_html}
      <div class="stock-story-wrap" style="margin-top:12px">
        <div class="stock-list-col">
          <div class="ss-sub-label">📈 거래대금</div>
          {top_amt_html}
          <div class="ss-sub-label" style="margin-top:10px">👤 외국인 순매수</div>
          {foreign_buy_html}
        </div>
        <div class="stock-story-col">
          <div class="ss-sub-label">🏢 기관 순매수</div>
          {inst_buy_html}
          <div class="ss-sub-label" style="margin-top:10px">🏆 52주 신고가</div>
          {high_52w_html}
        </div>
      </div>
      {f'<div class="story-text" style="margin-top:12px">{investor_flow_story}</div>' if investor_flow_story else ''}
      {f'<div style="margin-top:12px">{stock_story_html}</div>' if stock_story_html else ''}
    </div>
  </div>

  {research_html}

  <div class="section">
    <div class="story-wrap">
      <div class="mkt-sec-head">
        <span class="mkt-sec-icon">📰</span>
        <span class="mkt-sec-title">국내 주식 뉴스</span>
        <span class="mkt-sec-num">05</span>
      </div>
      {dom_news}
      {f'<div class="story-text" style="margin-top:12px">{kr_news_insight}</div>' if kr_news_insight else ''}
    </div>
  </div>

</div>

<!-- ===== 해외 탭 ===== -->
<div id="tab-us" class="tab-panel">

  <div class="section">
    {us_fg_banner_html}
  </div>

  <div class="section">
    <div class="section-label">00 · 주요 지수 &amp; 매크로 <span style="font-size:9px;color:var(--t3);font-weight:400;">탭하면 추이 차트</span></div>
    <div class="us-grid">
      <div class="us-card" onclick="showMacroChart('sp500')">
        <div class="us-card-top">
          <div class="us-name-wrap"><span class="us-name">S&amp;P 500</span><span class="us-ticker-badge">SPX</span></div>
          <span style="font-size:14px">📈</span>
        </div>
        <div class="us-val-row">
          <span class="us-val">{d(market,'sp500').get('val',0):,.2f}</span>
          <span class="us-pct-box {'up' if d(market,'sp500').get('pct',0)>=0 else 'dn'}">{d(market,'sp500').get('pct',0):+.2f}%</span>
        </div>
        <div class="rsi-wrap">
          <div class="rsi-head"><span>RSI</span><span>{d(market,'sp500').get('rsi',50)}</span></div>
          <div class="rsi-bg"><div class="rsi-fill" style="width:{d(market,'sp500').get('rsi',50)}%"></div></div>
        </div>
      </div>
      <div class="us-card" onclick="showMacroChart('nasdaq')">
        <div class="us-card-top">
          <div class="us-name-wrap"><span class="us-name">나스닥 100</span><span class="us-ticker-badge">NDX</span></div>
          <span style="font-size:14px">💻</span>
        </div>
        <div class="us-val-row">
          <span class="us-val">{d(market,'nasdaq').get('val',0):,.2f}</span>
          <span class="us-pct-box {'up' if d(market,'nasdaq').get('pct',0)>=0 else 'dn'}">{d(market,'nasdaq').get('pct',0):+.2f}%</span>
        </div>
        <div class="rsi-wrap">
          <div class="rsi-head"><span>RSI</span><span>{d(market,'nasdaq').get('rsi',50)}</span></div>
          <div class="rsi-bg"><div class="rsi-fill" style="width:{d(market,'nasdaq').get('rsi',50)}%"></div></div>
        </div>
      </div>
      <div class="us-card" onclick="showMacroChart('dow')">
        <div class="us-card-top">
          <div class="us-name-wrap"><span class="us-name">다우존스</span><span class="us-ticker-badge">DJI</span></div>
          <span style="font-size:14px">🏛️</span>
        </div>
        <div class="us-val-row">
          <span class="us-val">{d(market,'dow').get('val',0):,.0f}</span>
          <span class="us-pct-box {'up' if d(market,'dow').get('pct',0)>=0 else 'dn'}">{d(market,'dow').get('pct',0):+.2f}%</span>
        </div>
        <div class="rsi-wrap">
          <div class="rsi-head"><span>RSI</span><span>{d(market,'dow').get('rsi',50)}</span></div>
          <div class="rsi-bg"><div class="rsi-fill" style="width:{d(market,'dow').get('rsi',50)}%"></div></div>
        </div>
      </div>
      <div class="us-card" onclick="showMacroChart('vix')">
        <div class="us-card-top">
          <div class="us-name-wrap"><span class="us-name">공포지수 VIX</span><span class="us-ticker-badge">VIX</span></div>
          <span style="font-size:14px">😰</span>
        </div>
        <div class="us-val-row">
          <span class="us-val">{d(market,'vix').get('val') or 0:.2f}</span>
          <span class="us-pct-box {'dn' if (d(market,'vix').get('pct') or 0)>=0 else 'up'}">{d(market,'vix').get('pct') or 0:+.2f}%</span>
        </div>
        <div class="rsi-wrap">
          <div class="rsi-head"><span>RSI</span><span>{d(market,'vix').get('rsi',50)}</span></div>
          <div class="rsi-bg"><div class="rsi-fill" style="width:{d(market,'vix').get('rsi',50)}%"></div></div>
        </div>
      </div>
    </div>
    <div class="macro-grid" style="margin-top:8px">
      <div class="macro-card" onclick="showMacroChart('tnx')">
        <div class="macro-name">미 10년물</div>
        <div class="macro-val">{vdisp(market,'tnx')}</div>
        <div class="macro-chg">{cdisp(market,'tnx')}</div>
      </div>
      <div class="macro-card" onclick="showMacroChart('dxy')">
        <div class="macro-name">달러 인덱스</div>
        <div class="macro-val">{vdisp(market,'dxy')}</div>
        <div class="macro-chg">{cdisp(market,'dxy')}</div>
      </div>
      <div class="macro-card" onclick="showMacroChart('gold')">
        <div class="macro-name">금 선물</div>
        <div class="macro-val">{vdisp(market,'gold')}</div>
        <div class="macro-chg">{cdisp(market,'gold')}</div>
      </div>
      <div class="macro-card" onclick="showMacroChart('btc')">
        <div class="macro-name">🪙 비트코인</div>
        <div class="macro-val">{vdisp(market,'btc')}</div>
        <div class="macro-chg">{cdisp(market,'btc')}</div>
      </div>
    </div>
  </div>

  <div class="section">
    <div class="story-wrap">
      <div class="mkt-sec-head">
        <span class="mkt-sec-icon">🌐</span>
        <span class="mkt-sec-title">시장 요약</span>
        <span class="mkt-sec-num">01</span>
      </div>
      <div class="hashtag-row">{us_hashtags_html}</div>
      <div class="highlight-list">{us_highlights_html}</div>
      <div class="story-text">{us_summary}</div>
      {us_outlook_html}
    </div>
  </div>

  <div class="section">
    <div class="story-wrap">
      <div class="mkt-sec-head">
        <span class="mkt-sec-icon">📊</span>
        <span class="mkt-sec-title">섹터 & 자산 동향</span>
        <span class="mkt-sec-num">02</span>
      </div>
      <div class="asset-group-label">📁 섹터</div>
      <div class="asset-grid">{asset_sectors_html}</div>
      <div class="asset-group-label">💵 채권</div>
      <div class="asset-grid cols-3">{asset_bonds_html}</div>
      <div class="asset-group-label">🪙 원자재</div>
      <div class="asset-grid cols-3">{asset_commodities_html}</div>
      <div class="story-text" style="margin-top:12px">{us_asset_story}</div>
    </div>
  </div>

  <div class="section">
    <div class="story-wrap">
      <div class="mkt-sec-head">
        <span class="mkt-sec-icon">🔍</span>
        <span class="mkt-sec-title">주요 종목 동향</span>
        <span class="mkt-sec-num">03</span>
      </div>
      <div class="asset-group-label">⭐ 매그니피센트 7</div>
      <div class="asset-grid">{mag7_html}</div>
      <div class="mover-grid">
        <div class="mover-card up-side">
          <div class="mover-head up">🚀 급등 Top 3</div>
          {us_movers_gainers_html}
        </div>
        <div class="mover-card dn-side">
          <div class="mover-head dn">📉 급락 Top 3</div>
          {us_movers_losers_html}
        </div>
      </div>
      <div class="asset-group-label">📋 최근 실적 리뷰</div>
      <div class="earn-list">{earnings_reviews_html}</div>
      {earn_more_html}
      <div class="story-text">{us_stock_story}</div>
    </div>
  </div>

  <div class="section">
    <div class="story-wrap">
      <div class="mkt-sec-head">
        <span class="mkt-sec-icon">📡</span>
        <span class="mkt-sec-title">기술적 신호 리포트</span>
        <span class="mkt-sec-num">04</span>
      </div>
      <div style="background:var(--card);border:1px solid var(--border);border-radius:12px;padding:12px 14px;">
        {us_tech_html}
      </div>
      {f'<div class="story-text" style="margin-top:12px">{(us_ai_brief or {{}}).get("tech_insight","")}</div>' if (us_ai_brief or {{}}).get('tech_insight') else ''}
    </div>
  </div>

  <div class="section">
    <div class="story-wrap">
      <div class="mkt-sec-head">
        <span class="mkt-sec-icon">📰</span>
        <span class="mkt-sec-title">해외 뉴스</span>
        <span class="mkt-sec-num">05</span>
      </div>
      {int_news}
      {f'<div class="story-text" style="margin-top:12px">{(us_ai_brief or {{}}).get("news_insight","")}</div>' if (us_ai_brief or {{}}).get('news_insight') else ''}
    </div>
  </div>

</div>

<!-- ===== 부동산 탭 ===== -->
<div id="tab-re" class="tab-panel">

  <div class="section">
    <div class="story-wrap">
      <div class="mkt-sec-head">
        <span class="mkt-sec-icon">📉</span>
        <span class="mkt-sec-title">금리 &amp; 대출 환경</span>
        <span class="mkt-sec-num">01</span>
      </div>
      {re_rate_html}
    </div>
  </div>

  <div class="section">
    <div class="story-wrap">
      <div class="mkt-sec-head">
        <span class="mkt-sec-icon">📊</span>
        <span class="mkt-sec-title">서울 실거래 동향</span>
        <span class="mkt-sec-num">02</span>
      </div>
      {apt_trade_html}
    </div>
  </div>

  <div class="section">
    <div class="story-wrap">
      <div class="mkt-sec-head">
        <span class="mkt-sec-icon">📋</span>
        <span class="mkt-sec-title">청약 일정</span>
        <span class="mkt-sec-num">03</span>
      </div>
      {subscription_html}
      <div style="font-size:10px;color:var(--t3);margin-top:8px;">출처: 청약홈 · <a href="https://www.applyhome.co.kr" target="_blank" style="color:var(--t3)">applyhome.co.kr</a></div>
    </div>
  </div>

  <div class="section">
    <div class="story-wrap">
      <div class="mkt-sec-head">
        <span class="mkt-sec-icon">📰</span>
        <span class="mkt-sec-title">부동산 뉴스</span>
        <span class="mkt-sec-num">04</span>
      </div>
      {re_news}
      {f'<div class="story-text" style="margin-top:12px">{re_news_insight}</div>' if re_news_insight else ''}
    </div>
  </div>

  <div class="section">
    <div class="story-wrap">
      <div class="mkt-sec-head">
        <span class="mkt-sec-icon">🏠</span>
        <span class="mkt-sec-title">관심 단지</span>
        <span class="mkt-sec-num">05</span>
      </div>
      {tracked_apt_html}
    </div>
  </div>

</div>

<!-- ===== 핫이슈 탭 ===== -->
<div id="tab-hot" class="tab-panel">

  <div class="section">
    <div class="banner hot">
      <strong>🔥 오늘의 핫이슈</strong><br>
      주요 뉴스와 시장 이슈를 확인하세요.
    </div>
  </div>

  <div class="section">
    <div class="section-label">핫이슈 뉴스</div>
    {hot_news}
  </div>

</div>

<!-- ===== 일정 탭 ===== -->
<div id="tab-cal" class="tab-panel">

  <div class="section">
    <div class="banner blue">
      <strong>📅 이번 주 주요 일정</strong><br>
      FOMC · CPI · PCE · GDP · ISM PMI · 고용 · 금통위 · 실적 발표
    </div>
  </div>

  <div class="section">
    <div class="story-wrap">
      <div class="mkt-sec-head">
        <span class="mkt-sec-icon">📊</span>
        <span class="mkt-sec-title">경기 지표 발표</span>
        <span class="mkt-sec-num">01</span>
      </div>
      {cal_html}
      <div style="font-size:10px;color:var(--t3);margin-top:10px;">공모주 일정은 <a href="https://dart.fss.or.kr" target="_blank">DART</a> · <a href="https://ipo.38.co.kr" target="_blank">38커뮤니케이션</a> 확인</div>
    </div>
  </div>

  <div class="section">
    <div class="story-wrap">
      <div class="mkt-sec-head">
        <span class="mkt-sec-icon">📋</span>
        <span class="mkt-sec-title">실적 발표 예정</span>
        <span class="mkt-sec-num">02</span>
      </div>
      {earn_cal_html}
      <div style="font-size:10px;color:var(--t3);margin-top:8px;">출처: Finnhub · EPS 예상치 보유 기업 기준</div>
    </div>
  </div>

</div>


<!-- ===== 종목 탭 ===== -->
<div id="tab-watch" class="tab-panel">
  <div class="section">
    <input type="text" id="watchSearch" class="wl-search" placeholder="종목명 또는 티커 검색..." oninput="renderWatchlist(this.value)">
  </div>
  <div class="section">
    <div id="watchGrid" class="wl-grid"></div>
  </div>
</div>

<!-- ===== ETF 탭 ===== -->
<div id="tab-etf" class="tab-panel">
  <div class="section">
    <div class="section-label">📊 주요 ETF</div>
    {major_etf_html}
  </div>
  <div class="section">
    <div class="section-label">🎯 테마별 ETF</div>
    <div class="stock-story-wrap" style="flex-wrap:wrap;gap:14px;">
      {theme_etf_html}
    </div>
  </div>
  <div class="section">
    <div class="stock-story-wrap">
      <div class="stock-list-col">
        <div class="ss-sub-label">💰 거래대금 상위</div>
        {volume_etf_html}
      </div>
      <div class="stock-story-col">
        <div class="ss-sub-label">⭐ 인기 ETF</div>
        {popular_etf_html}
      </div>
    </div>
  </div>
</div>

<!-- 종목 상세 모달 -->
<div id="stockOverlay" onclick="closeStockModal()"></div>
<div id="stockModal"></div>

<div id="macroOverlay" onclick="closeMacroChart()"></div>
<div id="macroModal">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
    <div id="macroModalTitle" style="font-size:14px;font-weight:700;color:var(--t1);"></div>
    <button onclick="closeMacroChart()" style="background:none;border:none;color:var(--t3);font-size:22px;cursor:pointer;line-height:1;padding:0;">✕</button>
  </div>
  <div id="macroChartContainer" style="width:100%;height:260px;"></div>
</div>

<div class="footer-note">
  {kdate} · {gen_time}<br>
  부동산 시세는 호갱노노·KB부동산에서 직접 확인 권장
</div>

<script>
var MACRO_META={macro_meta_json};
var MACRO_HIST={macro_hist_json};
function showMacroChart(k){{
  var m=MACRO_META[k],vals=MACRO_HIST[k]||[];
  if(!m)return;
  document.getElementById('macroOverlay').style.display='block';
  setTimeout(function(){{
    document.getElementById('macroOverlay').classList.add('open');
    document.getElementById('macroModal').classList.add('open');
  }},10);
  document.getElementById('macroModalTitle').textContent=m.name+' 최근 2주';
  var ct=document.getElementById('macroChartContainer');
  if(ct._lwc){{ct._lwc.remove();ct._lwc=null;}}
  ct.innerHTML='';
  if(!vals.length){{ct.innerHTML='<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--t3);font-size:12px;">다음 업데이트 시 데이터 표시</div>';return;}}
  var data;
  if(typeof vals[0]==='object'&&vals[0].time){{
    data=vals;
  }}else{{
    var base=new Date();base.setHours(0,0,0,0);
    data=vals.map(function(c,i){{
      var d=new Date(base);d.setDate(d.getDate()-(vals.length-1-i));
      return{{time:d.toISOString().slice(0,10),open:c,high:c,low:c,close:c}};
    }});
  }}
  var chart=LightweightCharts.createChart(ct,{{
    width:ct.offsetWidth,height:240,
    layout:{{background:{{type:'solid',color:'transparent'}},textColor:'#6a80aa'}},
    grid:{{vertLines:{{color:'rgba(255,255,255,0.05)'}},horzLines:{{color:'rgba(255,255,255,0.05)'}}}},
    rightPriceScale:{{borderColor:'rgba(255,255,255,0.1)'}},
    timeScale:{{borderColor:'rgba(255,255,255,0.1)',timeVisible:true,minBarSpacing:18,tickMarkFormatter:function(t){{var p=t.split('-');return(p[1]|0)+'/'+(p[2]|0);}}}},
    crosshair:{{mode:1}},
  }});
  var series=chart.addCandlestickSeries({{
    upColor:'#00e896',downColor:'#ff4060',
    borderUpColor:'#00e896',borderDownColor:'#ff4060',
    wickUpColor:'#00e896',wickDownColor:'#ff4060',
  }});
  series.setData(data);
  chart.timeScale().fitContent();
  ct._lwc=chart;
}}
function closeMacroChart(){{
  var ct=document.getElementById('macroChartContainer');
  if(ct._lwc){{ct._lwc.remove();ct._lwc=null;}}
  ct.innerHTML='';
  document.getElementById('macroOverlay').classList.remove('open');
  document.getElementById('macroModal').classList.remove('open');
  setTimeout(function(){{document.getElementById('macroOverlay').style.display='none';}},280);
}}
var _tabTitles={{dom:'📈 국내 주식',us:'🌐 해외',re:'🏠 부동산',hot:'🔥 핫이슈',cal:'📅 주요 일정',watch:'📊 관심 종목',etf:'📦 ETF'}};
var WATCHLIST={watchlist_json};
function _fmt(v,dec,suf){{if(v===null||v===undefined)return'N/A';return(dec!==undefined?v.toFixed(dec):v)+(suf||'');}}
function _pctColor(v){{
  if(v===null||v===undefined)return'<span style="color:var(--t3)">N/A</span>';
  var c=v>=0?'var(--up)':'var(--dn)';
  return'<span style="color:'+c+'">'+(v>=0?'+':'')+v.toFixed(2)+'%</span>';
}}
var TV_EXCHANGE_MAP={{'NMS':'NASDAQ','NGM':'NASDAQ','NCM':'NASDAQ','NYQ':'NYSE','ASE':'AMEX','PCX':'AMEX','BTS':'CBOE','KSC':'KRX','KOE':'KRX'}};
function tvSymbol(s){{
  var ex=TV_EXCHANGE_MAP[s.exchange]||'NASDAQ';
  var t=s.ticker.replace('.KS','').replace('.KQ','');
  return ex+':'+t;
}}
function openChart(symbol){{
  window.open('chart.html?symbol='+encodeURIComponent(symbol),'_blank');
}}
function renderWatchlist(q){{
  var grid=document.getElementById('watchGrid');
  if(!grid)return;
  var list=WATCHLIST.filter(function(s){{
    var t=(q||'').toLowerCase();
    return!t||s.ticker.toLowerCase().includes(t)||s.name.toLowerCase().includes(t);
  }});
  if(!list.length){{grid.innerHTML='<div style="color:var(--t3);font-size:12px;padding:16px 0;text-align:center;">검색 결과 없음</div>';return;}}
  grid.innerHTML=list.map(function(s){{
    var cls=s.change_pct>=0?'up':'dn';
    var sign=s.change_pct>=0?'+':'';
    var cur=s.currency==='KRW'?'₩':'$';
    return'<div class="wl-card" data-ticker="'+s.ticker+'" onclick="showStock(this.dataset.ticker)">'+
      '<div class="wl-card-top">'+
        '<div><div class="wl-name">'+s.name+'</div>'+
        '<div class="wl-ticker"><span class="wl-mkt-badge">'+s.market+'</span> '+s.ticker+
        ' <span onclick="event.stopPropagation();openChart(\\''+tvSymbol(s)+'\\')" style="cursor:pointer" title="차트 보기">📈</span></div></div>'+
        '<div style="text-align:right">'+
          '<div class="wl-price '+cls+'-txt">'+cur+s.price.toLocaleString(undefined,{{maximumFractionDigits:2}})+'</div>'+
          '<div class="wl-pct '+cls+'-txt">'+sign+s.change_pct.toFixed(2)+'%</div>'+
        '</div>'+
      '</div>'+
      '<div class="wl-card-bot">'+
        '<span>시총 '+s.market_cap+'</span>'+
        '<span>P/E '+(s.pe?s.pe:'N/A')+'</span>'+
        '<span>RSI '+s.rsi+'</span>'+
      '</div>'+
    '</div>';
  }}).join('');
}}
function showStock(ticker){{
  var s=WATCHLIST.find(function(x){{return x.ticker===ticker;}});
  if(!s)return;
  var cls=s.change_pct>=0?'up':'dn';
  var sign=s.change_pct>=0?'+':'';
  var cur=s.currency==='KRW'?'₩':'$';
  var p=s.price.toLocaleString(undefined,{{maximumFractionDigits:2}});
  function row(label,val){{return'<div class="sk-row"><span class="sk-label">'+label+'</span><span class="sk-val">'+val+'</span></div>';}}
  function sec(label){{return'<div class="sk-sec">'+label+'</div>';}}
  function v(x,suf){{return x!==null&&x!==undefined?x+(suf||''):'N/A';}}
  function pv(x){{
    if(x===null||x===undefined)return'N/A';
    var c=x>=0?'var(--up)':'var(--dn)';
    return'<span style="color:'+c+'">'+(x>=0?'+':'')+x+'%</span>';
  }}
  var html=
    // ── 헤더 ──
    '<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:14px;">'+
      '<div>'+
        '<div style="font-size:15px;font-weight:700;color:var(--t1);">'+s.name+'</div>'+
        '<div style="font-size:10.5px;color:var(--t3);margin-top:2px;">'+
          '<span class="wl-mkt-badge">'+s.market+'</span> '+s.ticker+
          (s.exchange?' · '+s.exchange:'')+
          (s.sector?' · '+s.sector:'')+
        '</div>'+
      '</div>'+
      '<div style="display:flex;align-items:center;gap:10px;">'+
        '<button onclick="openChart(\\''+tvSymbol(s)+'\\')" style="background:none;border:none;color:var(--t3);font-size:20px;cursor:pointer;padding:0;line-height:1;" title="차트 보기">📈</button>'+
        '<button onclick="closeStockModal()" style="background:none;border:none;color:var(--t3);font-size:22px;cursor:pointer;padding:0;line-height:1;">✕</button>'+
      '</div>'+
    '</div>'+
    // ── 가격 카드 ──
    '<div style="background:var(--bg);border-radius:10px;padding:12px 14px;margin-bottom:4px;">'+
      '<div class="sk-price '+cls+'-txt">'+cur+p+'</div>'+
      '<div style="font-size:12px;color:var(--'+cls+');margin-top:2px;">'+sign+s.change_pct.toFixed(2)+'% ('+sign+cur+Math.abs(s.change).toFixed(2)+')</div>'+
      '<div style="font-size:10px;color:var(--t3);margin-top:6px;">시총 '+s.market_cap+' &nbsp;|&nbsp; EV '+s.ev+'</div>'+
      '<div style="font-size:10px;color:var(--t3);margin-top:3px;">52주 '+cur+(s.low52||'N/A')+' ~ '+cur+(s.high52||'N/A')+'</div>'+
      (s.target?'<div style="font-size:10px;color:var(--t3);margin-top:3px;">목표주가 '+cur+s.target+'</div>':'')+
    '</div>'+
    // ── 1. 주요 지표 ──
    sec('📊 주요 지표')+
    row('시가총액',v(s.market_cap))+
    row('P/E (TTM)',v(s.pe))+row('Forward P/E',v(s.forward_pe))+
    row('PEG',v(s.peg))+row('P/S',v(s.ps))+row('P/B',v(s.pb))+
    row('EV/EBITDA',v(s.ev_ebitda))+
    row('EPS (TTM)',s.eps!==null?cur+s.eps:'N/A')+
    row('유통주식수',v(s.float_shares))+row('발행주식수',v(s.shares_out))+
    // ── 2. 수익성 ──
    sec('💰 수익성')+
    row('EPS (TTM)',s.eps!==null?cur+s.eps:'N/A')+
    row('매출',v(s.revenue))+row('순이익',v(s.net_income))+
    row('매출총이익률',v(s.gross_margin,'%'))+row('영업이익률',v(s.op_margin,'%'))+
    row('순이익률',v(s.profit_margin,'%'))+
    row('ROE',v(s.roe,'%'))+row('ROA',v(s.roa,'%'))+row('ROIC',v(s.roic,'%'))+
    // ── 3. 성장성 ──
    sec('📈 성장성 (YoY)')+
    row('매출 성장률',pv(s.rev_growth))+row('이익 성장률',pv(s.earn_growth))+
    row('분기 매출 성장',pv(s.rev_q_growth))+row('분기 이익 성장',pv(s.earn_q_growth))+
    // ── 4. 재무 건전성 ──
    sec('🏦 재무 건전성')+
    row('유동비율',v(s.current_ratio))+row('당좌비율',v(s.quick_ratio))+
    row('부채비율(D/E)',v(s.debt_equity))+row('총부채',v(s.total_debt))+
    row('현금성 자산',v(s.total_cash))+row('잉여현금흐름',v(s.fcf))+
    // ── 5. 배당 ──
    sec('💵 배당')+
    row('배당수익률',s.div_yield?s.div_yield+'%':'없음')+
    row('주당 배당금',s.div_rate?cur+s.div_rate:'없음')+
    row('배당성향',s.payout_ratio?s.payout_ratio+'%':'N/A')+
    row('배당락일',v(s.ex_div_date))+
    // ── 6. 주가 성과 ──
    sec('📉 주가 성과')+
    '<div class="perf-grid" style="grid-template-columns:repeat(4,1fr);">'+
      ['1W','1M','3M','6M'].map(function(lbl,i){{
        var rv=[s.ret_1w,s.ret_1m,s.ret_3m,s.ret_6m][i];
        var c=rv===null||rv===undefined?'var(--t3)':rv>=0?'var(--up)':'var(--dn)';
        return'<div class="perf-cell"><div class="perf-period">'+lbl+'</div><div class="perf-val" style="color:'+c+'">'+(rv!==null&&rv!==undefined?(rv>=0?'+':'')+rv.toFixed(1)+'%':'N/A')+'</div></div>';
      }}).join('')+
    '</div>'+
    '<div class="perf-grid" style="grid-template-columns:repeat(4,1fr);margin-top:4px;">'+
      ['YTD','1Y','3Y','5Y'].map(function(lbl,i){{
        var rv=[s.ret_ytd,s.ret_1y,s.ret_3y,s.ret_5y][i];
        var c=rv===null||rv===undefined?'var(--t3)':rv>=0?'var(--up)':'var(--dn)';
        return'<div class="perf-cell"><div class="perf-period">'+lbl+'</div><div class="perf-val" style="color:'+c+'">'+(rv!==null&&rv!==undefined?(rv>=0?'+':'')+rv.toFixed(1)+'%':'N/A')+'</div></div>';
      }}).join('')+
    '</div>'+
    // ── 7. 기술적 지표 ──
    sec('🔧 기술적 지표')+
    row('RSI (14)',v(s.rsi))+row('베타',v(s.beta))+
    row('ATR (14)',s.atr!==null?cur+s.atr:'N/A')+
    row('변동성 (주간)',v(s.vol_weekly,'%'))+row('변동성 (월간)',v(s.vol_monthly,'%'))+
    row('SMA20 괴리율',pv(s.sma20_gap))+row('SMA50 괴리율',pv(s.sma50_gap))+row('SMA200 괴리율',pv(s.sma200_gap))+
    // ── 8. 거래 정보 ──
    sec('📋 거래 정보')+
    row('거래량',s.volume?s.volume.toLocaleString():'N/A')+
    row('평균 거래량(3M)',s.avg_volume?s.avg_volume.toLocaleString():'N/A')+
    row('상대 거래량',v(s.rel_volume))+
    row('거래소',v(s.exchange))+
    // ── 9. 지분 구조 ──
    sec('👥 지분 구조')+
    row('기관 보유',v(s.inst_pct,'%'))+row('내부자 보유',v(s.insider_pct,'%'))+row('공매도 비율',v(s.short_float,'%'))+
    // ── 10. 기타 정보 ──
    sec('ℹ️ 기타 정보')+
    row('업종',v(s.sector))+row('세부 업종',v(s.industry))+
    row('국가',v(s.country))+row('임직원 수',s.employees?s.employees.toLocaleString()+'명':'N/A')+
    row('상장일',v(s.ipo_date))+
    (s.website?row('웹사이트','<a href="'+s.website+'" target="_blank" style="color:var(--blue)">'+s.website.replace('https://','')+'</a>'):'')+
    (s.desc?'<div style="font-size:10.5px;color:var(--t3);margin-top:10px;line-height:1.6;padding:8px;background:var(--bg);border-radius:8px;">'+s.desc+'</div>':'')+
    // ── 관련 뉴스 ──
    (s.news&&s.news.length?
      sec('📰 관련 뉴스')+
      s.news.map(function(n){{
        return'<a href="'+n.link+'" target="_blank" style="display:block;text-decoration:none;padding:8px 0;border-bottom:1px solid rgba(255,255,255,.05);">'+
          '<div style="font-size:12px;color:var(--t1);line-height:1.5;margin-bottom:3px;">'+n.title+'</div>'+
          '<div style="font-size:10px;color:var(--t3);">'+n.publisher+(n.date?' · '+n.date:'')+'</div>'+
        '</a>';
      }}).join('')
    :'');
  document.getElementById('stockModal').innerHTML=html;
  document.getElementById('stockOverlay').style.display='block';
  setTimeout(function(){{
    document.getElementById('stockOverlay').classList.add('open');
    document.getElementById('stockModal').classList.add('open');
  }},10);
}}
function closeStockModal(){{
  document.getElementById('stockOverlay').classList.remove('open');
  document.getElementById('stockModal').classList.remove('open');
  setTimeout(function(){{document.getElementById('stockOverlay').style.display='none';}},250);
}}
function toggleEarnMore(btn){{
  var list = btn.previousElementSibling;
  var extras = list.querySelectorAll('.earn-item.is-extra');
  var opened = extras.length && extras[0].classList.contains('show');
  extras.forEach(function(el){{el.classList.toggle('show', !opened);}});
  btn.textContent = opened ? btn.dataset.moreLabel : btn.dataset.lessLabel;
}}
function doReload(){{
  var btn=document.getElementById('refreshBtn');
  btn.disabled=true;btn.textContent='로딩 중...';
  location.reload();
}}
var _updTimer=null;
function triggerUpdate(){{
  var btn=document.getElementById('updBtn');
  btn.disabled=true;btn.textContent='요청 중...';
  document.getElementById('updStatus').textContent='';
  fetch('https://dashboard-trigger.mamibj112.workers.dev',{{method:'POST'}})
  .then(function(r){{return r.json().then(function(d){{return {{code:r.status,data:d}};}});}})
  .then(function(res){{
    if(res.code===200 && res.data.status==='success'){{
      btn.textContent='업데이트 중...';
      document.getElementById('updStatus').textContent='⏳ 1~2분 후 새로고침';
      _updTimer=setTimeout(function(){{location.reload();}},90000);
    }}else if(res.code===409){{
      btn.disabled=false;btn.textContent='지금 업데이트';
      document.getElementById('updStatus').textContent='⏳ 이미 진행 중';
    }}else{{
      btn.disabled=false;btn.textContent='지금 업데이트';
      document.getElementById('updStatus').textContent='❌ 실패';
    }}
  }}).catch(function(){{
    btn.disabled=false;btn.textContent='지금 업데이트';
    document.getElementById('updStatus').textContent='❌ 네트워크 오류';
  }});
}}
function sw(id, btn) {{
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('tab-' + id).classList.add('active');
  btn.classList.add('active');
  document.querySelector('.header-title').textContent=_tabTitles[id]||'국장 데일리 대시보드';
  if(id==='watch') renderWatchlist('');
}}
if ('serviceWorker' in navigator) {{
  navigator.serviceWorker.register('sw.js').catch(() => {{}});
}}
</script>
</body>
</html>"""

# ── 아이콘 생성 ────────────────────────────────────────────────────────────────

def create_icons():
    try:
        from PIL import Image, ImageDraw
        for size in [192, 512]:
            img = Image.new('RGB', (size, size), '#080b10')
            draw = ImageDraw.Draw(img)
            p = size // 7
            bars = [0.45, 0.70, 0.52, 0.88, 0.62, 0.78]
            colors = ['#00e896','#4da6ff','#00e896','#00e896','#4da6ff','#00e896']
            w = (size - p * 2) // len(bars)
            for i, (h, c) in enumerate(zip(bars, colors)):
                x0 = p + i * w + w // 5
                x1 = p + (i + 1) * w - w // 5
                bh = int((size - p * 2) * h * 0.75)
                y0 = size - p - bh
                draw.rounded_rectangle([x0, y0, x1, size - p], radius=max(2, size // 50), fill=c)
            img.save(f'icon-{size}.png')
        print("  아이콘 생성 완료")
    except ImportError:
        print("  Pillow 없음 — 아이콘 생략 (pip install Pillow로 설치 가능)")
    except Exception as e:
        print(f"  아이콘 오류: {e}")

# ── 메인 ──────────────────────────────────────────────────────────────────────

def main():
    from concurrent.futures import ThreadPoolExecutor

    dt = now_kst()
    print(f"대시보드 생성 중: {korean_date(dt)}")

    # 1단계: 데이터 수집 (병렬 — Gemini 호출 없음)
    print("데이터 수집 중 (병렬)...")
    with ThreadPoolExecutor(max_workers=8) as ex:
        f_market          = ex.submit(fetch_market)
        f_news            = ex.submit(fetch_news)
        f_stocks          = ex.submit(fetch_market_stocks)
        f_usdkrw          = ex.submit(fetch_usdkrw_week)
        f_macro           = ex.submit(fetch_macro_history)
        f_research_reports = ex.submit(fetch_research_reports)
        f_kr_sectors      = ex.submit(fetch_kr_sectors)
        f_etf             = ex.submit(fetch_etf_data)
        f_cnn_fg          = ex.submit(fetch_cnn_fear_greed)

    market           = f_market.result()
    news             = f_news.result()
    stocks           = f_stocks.result()
    usdkrw_week      = f_usdkrw.result()
    macro_hist       = f_macro.result()
    research_reports = f_research_reports.result()
    kr_sectors       = f_kr_sectors.result()
    etf_data         = f_etf.result()
    cnn_fear_greed   = f_cnn_fg.result()

    # 2단계: AI 분석 (병렬 — Gemini 호출)
    print("AI 분석 중 (병렬)...")
    recent_earnings = fetch_us_recent_earnings()

    with ThreadPoolExecutor(max_workers=7) as ex:
        f_ai_brief         = ex.submit(fetch_ai_briefing, market, news)
        f_us_ai_brief      = ex.submit(fetch_us_ai_briefing, market, news, recent_earnings)
        f_research_summary = ex.submit(fetch_research_summary, research_reports)
        f_stock_story      = ex.submit(fetch_stock_story, stocks)
        f_investor_flow    = ex.submit(fetch_investor_flow_story, stocks)
        f_watchlist        = ex.submit(fetch_watchlist_data, WATCHLIST)
        f_company_overview = ex.submit(fetch_company_overview)

    ai_brief            = f_ai_brief.result()
    us_ai_brief         = f_us_ai_brief.result()
    research_summary    = f_research_summary.result()
    stock_story         = f_stock_story.result()
    investor_flow_story = f_investor_flow.result()
    watchlist           = f_watchlist.result()
    company_overview    = f_company_overview.result()

    kr_news_insight  = fetch_kr_news_insight(news.get('domestic', []))
    re_rates         = fetch_re_rates()
    apt_trade        = fetch_apt_trade_trend()
    subscription     = fetch_subscription_schedule()
    tracked_apt      = fetch_tracked_apt_trades()
    upcoming_earnings = fetch_upcoming_earnings(dt)
    re_news_insight  = fetch_re_news_insight(news.get('realestate', []))

    html = generate_html(market, news, stocks, ai_brief, dt, usdkrw_week=usdkrw_week, macro_hist=macro_hist, research_summary=research_summary, stock_story=stock_story, investor_flow_story=investor_flow_story, us_ai_brief=us_ai_brief, watchlist=watchlist, kr_sectors=kr_sectors, etf_data=etf_data, cnn_fear_greed=cnn_fear_greed, kr_news_insight=kr_news_insight, re_rates=re_rates, re_news_insight=re_news_insight, apt_trade=apt_trade, subscription=subscription, tracked_apt=tracked_apt, upcoming_earnings=upcoming_earnings)

    out = Path(__file__).parent / 'index.html'
    out.write_text(html, encoding='utf-8')
    print(f"저장 완료: {out}")

    if company_overview:
        overview_out = Path(__file__).parent / 'company-overview.json'
        overview_out.write_text(json.dumps(company_overview, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"저장 완료: {overview_out}")
    else:
        print("  회사 개요 생성 결과 없음 — company-overview.json 유지")

    for icon in ['icon-192.png', 'icon-512.png']:
        if not (Path(__file__).parent / icon).exists():
            print("아이콘 생성 중...")
            create_icons()
            break

    print("완료!")

if __name__ == '__main__':
    main()
