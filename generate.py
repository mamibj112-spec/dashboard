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
}

US_SECTOR_MAP = {
    'xlk': 'IT/기술', 'xle': '에너지', 'xlv': '헬스케어', 'xlp': '필수소비재', 
    'xly': '경기소비재', 'xlf': '금융', 'xli': '산업재', 'xlb': '소재', 
    'xlre': '부동산', 'xlu': '유틸리티'
}
US_STOCK_MAP = {
    'unh': '유나이티드헬스', 'avgo': '브로드컴', 'anet': '아리스타', 'wmt': '월마트',
    'arm': 'ARM', 'pfe': '화이자', 'panw': '팔로알토', 'intc': '인텔',
    'nvda': '엔비디아', 'aapl': '애플', 'msft': '마이크로소프트', 'meta': '메타'
}

# 관심 종목 목록 — 티커/이름/시장(US or KR)
WATCHLIST = [
    {'ticker': 'SNDK',    'name': '샌디스크',   'market': 'US'},
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
            # RSI 계산을 위해 1개월치 데이터 수집
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
    return data


# ── 주도주 & 시장 체감 ─────────────────────────────────────────────────────────

def fetch_market_stocks():
    """FinanceDataReader로 주도주/체감 데이터 수집"""
    try:
        import FinanceDataReader as fdr
        import pandas as pd

        print("  주도주/체감 데이터 수집 중...")
        kospi  = fdr.StockListing('KOSPI')
        kosdaq = fdr.StockListing('KOSDAQ')
        all_s  = pd.concat([kospi, kosdaq], ignore_index=True)

        # 유효 데이터만
        all_s = all_s.dropna(subset=['Amount', 'ChagesRatio', 'Close', 'Name'])
        all_s = all_s[(all_s['Close'] > 0) & (all_s['Amount'] > 0)]

        # 시장 체감 온도
        up   = int((all_s['ChagesRatio'] > 0).sum())
        down = int((all_s['ChagesRatio'] < 0).sum())
        flat = int((all_s['ChagesRatio'] == 0).sum())

        # 거래대금 상위 5
        top_amt = all_s.nlargest(5, 'Amount')[['Name','Close','ChagesRatio','Amount','Market']].to_dict('records')

        # 상승률 상위 5 (상한가 30% 초과 제외)
        gainers = all_s[(all_s['ChagesRatio'] > 0) & (all_s['ChagesRatio'] <= 30)]
        top_gain = gainers.nlargest(5, 'ChagesRatio')[['Name','Close','ChagesRatio','Amount','Market']].to_dict('records')

        print(f"  주도주 수집 완료: 상승 {up} / 하락 {down}")
        return {'breadth': {'up': up, 'down': down, 'flat': flat},
                'top_amt': top_amt, 'top_gain': top_gain}
    except Exception as e:
        print(f"  주도주 오류: {e}")
        return None


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

def fetch_macro_history():
    """매크로 지표 최근 7일 종가 데이터"""
    print("매크로 추이 데이터 수집 중...")
    result = {}
    for key, sym in MACRO_HISTORY_TICKERS.items():
        try:
            t = yf.Ticker(sym)
            hist = t.history(period='14d', auto_adjust=True)
            hist = hist.dropna(subset=['Close'])
            closes = [round(float(v), 4) for v in hist['Close'].tail(7).tolist()]
            if len(closes) >= 2:
                result[key] = closes
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
        pct  = float(r.get('ChagesRatio', 0) or 0)
        amt  = r.get('Amount', 0) or 0
        mkt  = str(r.get('Market', ''))
        cls  = 'up-txt' if pct >= 0 else 'dn-txt'
        sign = '▲' if pct >= 0 else '▼'
        amt_str = f"{amt/100000000:.0f}억" if amt >= 100000000 else f"{amt/100000000:.1f}억"
        mkt_badge = '<span style="font-size:9px;color:var(--t3);margin-left:3px;">Q</span>' if 'KOSDAQ' in mkt else ''
        out += f'''<div class="stock-row">
  <div class="stock-name">{name}{mkt_badge}</div>
  <div class="stock-right">
    <span class="{cls}">{sign}{abs(pct):.1f}%</span>
    <span class="stock-amt">{amt_str}</span>
  </div>
</div>'''
    return out


# ── Gemini 공통 호출 헬퍼 ─────────────────────────────────────────────────────
def _gemini_post(api_key, prompt, temperature=0.7, max_tokens=1024):
    """Gemini API 호출 + 429 시 최대 3회 재시도 (30초 간격)"""
    import time as _time
    url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}'
    body = {'contents': [{'parts': [{'text': prompt}]}],
            'generationConfig': {'temperature': temperature, 'maxOutputTokens': max_tokens}}
    for attempt in range(3):
        resp = requests.post(url, json=body, timeout=60)
        if resp.status_code == 429:
            wait = 30 * (attempt + 1)
            print(f"  Gemini 429 rate limit, {wait}초 후 재시도 ({attempt+1}/3)...")
            _time.sleep(wait)
            continue
        resp.raise_for_status()
        parts = resp.json()['candidates'][0]['content']['parts']
        return next((p['text'] for p in parts if 'text' in p), '').strip()
    raise Exception('Gemini API 재시도 초과')


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
아래 JSON 형식으로만 응답하세요. 다른 텍스트는 절대 포함하지 마세요.
{{
  "keyword": "오늘의 핵심 키워드 한 줄 (이모지 포함, 20자 이내)",
  "story": "주요 지표 움직임의 원인과 연결고리 설명 (2~3문장, 인과관계 중심)",
  "sector_story": "업종별 등락 스토리 (왜 올랐고 왜 내렸는지 흐름 설명, 2문장)",
  "watch_points": ["투자자 주목 포인트 1", "투자자 주목 포인트 2", "투자자 주목 포인트 3"]
}}"""

        import json, re
        text = _gemini_post(api_key, prompt, temperature=0.7)
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


def fetch_us_ai_briefing(market, news):
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

        headlines = []
        for item in news.get('international', [])[:6]:
            headlines.append(item['title'])

        prompt = f"""오늘 미국 주식시장 데이터 (현지 종가 기준):
주요 지수:
- S&P500: {mv('sp500')}
- 나스닥: {mv('nasdaq')}
- 다우존스: {mv('dow')}
- VIX 공포지수: {mv('vix')}

섹터별 동향:
{sector_data}

주요 종목 동향:
{stock_data}

주요 뉴스 헤드라인:
{chr(10).join(f"- {h}" for h in headlines)}

위 데이터를 바탕으로 단순 나열이 아닌, 지표 간 인과관계와 섹터/종목별 흐름이 있는 시황 분석을 작성하세요.
한국어 뉴스레터 형식으로 작성하며, 투자자들이 오늘 무엇에 집중해야 했는지 명확히 설명하세요.
아래 JSON 형식으로만 응답하세요. 다른 텍스트는 절대 포함하지 마세요.
{{
  "keyword": "오늘 미국 시장 핵심 키워드 (이모지 포함, 20자 이내)",
  "story": "전체적인 시장 분위기와 지수 움직임의 원인 (3~4문장)",
  "sector_story": "섹터 및 주요 종목들의 특징적인 움직임과 이유 (3문장)",
  "outlook": "향후 주목해야 할 이벤트나 투자 포인트 (2문장)"
}}"""

        import json, re
        text = _gemini_post(api_key, prompt, temperature=0.7)
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if m:
            data = json.loads(m.group(0))
            print(f"  해외 AI 브리핑 완료")
            return data
        return None
    except Exception as e:
        print(f"  해외 AI 브리핑 오류: {e}")
        return None


def build_us_story_fallback(market):
    """AI 없을 때 규칙 기반 미국 시황 요약 생성"""
    sp500_pct  = d(market, 'sp500').get('pct') or 0
    nasdaq_pct = d(market, 'nasdaq').get('pct') or 0
    dow_pct    = d(market, 'dow').get('pct') or 0
    vix_val    = d(market, 'vix').get('val') or 20
    sp_rsi     = d(market, 'sp500').get('rsi') or 50
    tnx_val    = d(market, 'tnx').get('val')
    dxy_pct    = d(market, 'dxy').get('pct') or 0
    gold_pct   = d(market, 'gold').get('pct') or 0
    btc_pct    = d(market, 'btc').get('pct') or 0

    # 지수 흐름
    if abs(sp500_pct) >= 2.0:
        idx_desc = f'S&P500이 {abs(sp500_pct):.1f}% {"급등"if sp500_pct>0 else "급락"}하며 큰 변동성을 보였습니다.'
    elif abs(sp500_pct) >= 1.0:
        idx_desc = f'S&P500이 {abs(sp500_pct):.1f}% {"상승"if sp500_pct>0 else "하락"}하였습니다.'
    else:
        idx_desc = f'S&P500이 {sp500_pct:+.2f}%로 보합권에서 마감하였습니다.'

    # 기술주 vs 다우
    gap = nasdaq_pct - dow_pct
    if gap > 1.0:
        tech_desc = f'나스닥이 다우 대비 강세를 보이며 기술주가 시장을 주도했습니다.'
    elif gap < -1.0:
        tech_desc = f'나스닥이 다우 대비 약세로 기술주 부진이 두드러졌습니다.'
    else:
        tech_desc = f'나스닥({nasdaq_pct:+.2f}%)과 다우({dow_pct:+.2f}%)가 비슷한 흐름을 보였습니다.'

    # 공포지수
    if vix_val >= 30:
        vix_desc = f'VIX 공포지수가 {vix_val:.1f}로 고조되어 시장 불안이 큽니다.'
    elif vix_val <= 15:
        vix_desc = f'VIX 공포지수가 {vix_val:.1f}로 낮아 시장이 안정적입니다.'
    else:
        vix_desc = f'VIX 공포지수는 {vix_val:.1f}로 보통 수준입니다.'

    # 매크로
    macro_pts = []
    if tnx_val:
        macro_pts.append(f'미 10년물 금리 {tnx_val:.2f}%')
    if abs(dxy_pct) >= 0.3:
        macro_pts.append(f'달러 인덱스 {"강세" if dxy_pct > 0 else "약세"}({dxy_pct:+.1f}%)')
    if abs(gold_pct) >= 0.5:
        macro_pts.append(f'금 {"상승" if gold_pct > 0 else "하락"}({gold_pct:+.1f}%)')
    if abs(btc_pct) >= 2.0:
        macro_pts.append(f'비트코인 {"급등" if btc_pct > 0 else "급락"}({btc_pct:+.1f}%)')
    macro_desc = ' · '.join(macro_pts) if macro_pts else ''

    # RSI 상태
    if sp_rsi >= 70:
        rsi_desc = f'S&P500 RSI {sp_rsi}로 과매수 구간 진입, 단기 조정 주의가 필요합니다.'
    elif sp_rsi <= 30:
        rsi_desc = f'S&P500 RSI {sp_rsi}로 과매도 구간으로 반등 가능성을 주시하세요.'
    else:
        rsi_desc = f'S&P500 RSI {sp_rsi}로 중립 구간에서 추세를 확인 중입니다.'

    story = f'{idx_desc} {tech_desc}'
    sector = vix_desc
    if macro_desc:
        sector += f' 매크로 지표: {macro_desc}.'
    outlook = rsi_desc

    return {'keyword': '📊 오늘의 미국 증시', 'story': story, 'sector_story': sector, 'outlook': outlook}


def translate_news_to_korean(items):
    """Gemini API로 해외 뉴스 제목/요약을 한국어로 번역"""
    import os, json, re
    api_key = os.environ.get('GEMINI_API_KEY', '').strip()
    if not api_key or not items:
        return items
    try:
        print("  해외 뉴스 번역 중...")
        titles = [item['title'] for item in items]
        summaries = [item.get('summary', '') for item in items]
        prompt = f"""아래 영어 주식/금융 뉴스 제목과 요약을 자연스러운 한국어로 번역하세요.
반드시 아래 JSON 형식으로만 응답하고, 다른 텍스트는 포함하지 마세요.
{{
  "titles": ["번역된 제목1", "번역된 제목2", ...],
  "summaries": ["번역된 요약1", "번역된 요약2", ...]
}}

제목 목록:
{json.dumps(titles, ensure_ascii=False)}

요약 목록:
{json.dumps(summaries, ensure_ascii=False)}"""

        text = _gemini_post(api_key, prompt, temperature=0.3)
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if m:
            data = json.loads(m.group(0))
            ko_titles = data.get('titles', [])
            ko_summaries = data.get('summaries', [])
            for i, item in enumerate(items):
                if i < len(ko_titles) and ko_titles[i]:
                    item['title_orig'] = item['title']
                    item['title'] = ko_titles[i]
                if i < len(ko_summaries) and ko_summaries[i]:
                    item['summary'] = ko_summaries[i]
            print(f"  해외 뉴스 번역 완료 ({len(items)}건)")
    except Exception as e:
        print(f"  해외 뉴스 번역 오류: {e}")
    return items


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
]


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
    """Gemini로 오늘의 핵심 리포트 3개 선정 및 요약"""
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

위 리포트 중 오늘 가장 주목할 만한 3개를 선정하고, 각각의 핵심 투자 포인트를 2줄로 요약해주세요.
선정한 리포트의 번호(위 목록의 숫자)를 index 필드에 포함하세요 (1부터 시작).
아래 JSON 형식으로만 응답하세요. 다른 텍스트는 절대 포함하지 마세요.
{{
  "reports": [
    {{"index": 1, "stock": "종목명", "firm": "증권사", "title": "리포트 제목", "point1": "핵심 포인트 1줄", "point2": "핵심 포인트 2줄"}},
    {{"index": 2, "stock": "종목명", "firm": "증권사", "title": "리포트 제목", "point1": "핵심 포인트 1줄", "point2": "핵심 포인트 2줄"}},
    {{"index": 3, "stock": "종목명", "firm": "증권사", "title": "리포트 제목", "point1": "핵심 포인트 1줄", "point2": "핵심 포인트 2줄"}}
  ]
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
            return result
        return None
    except Exception as e:
        print(f"  리포트 AI 요약 오류: {e}")
        return None


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
    """관심 종목 상세 데이터 수집 (yfinance)"""
    import pandas as _pd
    results = []
    for item in watchlist:
        ticker = item['ticker']
        name   = item['name']
        market = item['market']
        try:
            t    = yf.Ticker(ticker)
            info = t.info
            hist = t.history(period='1y')
            if hist.empty or len(hist) < 2:
                print(f"  [{ticker}] 히스토리 없음")
                continue
            closes = hist['Close'].tolist()
            curr   = closes[-1]
            prev   = closes[-2]
            change     = round(curr - prev, 4)
            change_pct = round(change / prev * 100, 2) if prev else 0

            # RSI
            rsi = round(calculate_rsi(closes), 1)

            # SMA vs 현재가 괴리율
            s = _pd.Series(closes)
            def sma_gap(n):
                if len(closes) < n: return None
                v = s.rolling(n).mean().iloc[-1]
                return round((curr - v) / v * 100, 2) if v else None

            # 기간별 수익률
            def ret(days):
                if len(closes) < days + 1: return None
                old = closes[-(days + 1)]
                return round((curr - old) / old * 100, 2) if old else None

            currency = info.get('currency', 'USD')
            mc = info.get('marketCap')
            def fmt_cap(v):
                if v is None: return 'N/A'
                if currency == 'KRW':
                    return f'{v/1e12:.1f}조원' if v >= 1e12 else f'{v/1e8:.0f}억원'
                if v >= 1e12: return f'${v/1e12:.2f}T'
                if v >= 1e9:  return f'${v/1e9:.1f}B'
                return f'${v/1e6:.0f}M'

            def pct_fmt(v):
                return round(v * 100, 2) if v is not None else None

            results.append({
                'ticker':       ticker,
                'name':         name,
                'market':       market,
                'price':        round(curr, 4),
                'change':       change,
                'change_pct':   change_pct,
                'currency':     currency,
                'market_cap':   fmt_cap(mc),
                'pe':           round(info.get('trailingPE'), 2)    if info.get('trailingPE')  else None,
                'forward_pe':   round(info.get('forwardPE'), 2)     if info.get('forwardPE')   else None,
                'pb':           round(info.get('priceToBook'), 2)   if info.get('priceToBook') else None,
                'peg':          round(info.get('pegRatio'), 2)      if info.get('pegRatio')    else None,
                'eps':          round(info.get('trailingEps'), 4)   if info.get('trailingEps') else None,
                'target':       round(info.get('targetMeanPrice'),2) if info.get('targetMeanPrice') else None,
                'high52':       round(info.get('fiftyTwoWeekHigh'), 4) if info.get('fiftyTwoWeekHigh') else None,
                'low52':        round(info.get('fiftyTwoWeekLow'), 4)  if info.get('fiftyTwoWeekLow')  else None,
                'beta':         round(info.get('beta'), 2)           if info.get('beta')        else None,
                'volume':       info.get('volume'),
                'avg_volume':   info.get('averageVolume'),
                'div_yield':    pct_fmt(info.get('dividendYield')),
                'op_margin':    pct_fmt(info.get('operatingMargins')),
                'profit_margin':pct_fmt(info.get('profitMargins')),
                'gross_margin': pct_fmt(info.get('grossMargins')),
                'roe':          pct_fmt(info.get('returnOnEquity')),
                'roa':          pct_fmt(info.get('returnOnAssets')),
                'current_ratio':round(info.get('currentRatio'), 2)  if info.get('currentRatio') else None,
                'debt_equity':  round(info.get('debtToEquity'), 2)  if info.get('debtToEquity') else None,
                'sector':       info.get('sector', ''),
                'industry':     info.get('industry', ''),
                'desc':         (info.get('longBusinessSummary') or '')[:180],
                'rsi':          rsi,
                'sma20_gap':    sma_gap(20),
                'sma50_gap':    sma_gap(50),
                'sma200_gap':   sma_gap(200),
                'ret_1w':       ret(5),
                'ret_1m':       ret(21),
                'ret_3m':       ret(63),
                'ret_6m':       ret(126),
                'ret_1y':       round((curr - closes[0]) / closes[0] * 100, 2) if closes[0] else None,
                'news':         _fetch_ticker_news(t),
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
.update-btn{{display:inline-block;margin-top:5px;padding:4px 10px;font-size:10px;color:var(--blue);border:1px solid var(--blue);border-radius:6px;text-decoration:none;opacity:.8;background:none;cursor:pointer}}
.update-btn:hover{{opacity:1;text-decoration:none}}
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
.story-keyword{font-size:14px;font-weight:700;color:var(--t1);margin-bottom:12px;padding-bottom:10px;border-bottom:1px solid var(--border)}
.story-block{margin-bottom:10px}
.story-block:last-child{margin-bottom:0}
.story-label{font-size:10px;color:var(--blue);font-weight:700;letter-spacing:.5px;margin-bottom:5px}
.story-text{font-size:12px;color:var(--t2);line-height:1.75}
.story-watch{font-size:12px;color:var(--t1);line-height:1.9;font-weight:500}
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
.sector-bar-row{display:flex;align-items:center;gap:8px;padding:5px 0;border-bottom:1px solid rgba(255,255,255,.04)}
.sector-bar-row:last-child{border-bottom:none}
.sector-bar-name{font-size:11px;color:var(--t2);width:72px;flex-shrink:0}
.sector-bar-wrap{flex:1;height:12px;background:rgba(255,255,255,.05);border-radius:3px;overflow:hidden}
.sector-bar-fill{height:100%;border-radius:3px}
.sector-bar-pct{font-size:10.5px;font-weight:700;width:48px;text-align:right;flex-shrink:0}
.top3-row{display:flex;align-items:center;gap:8px;padding:7px 0;border-bottom:1px solid rgba(255,255,255,.04)}
.top3-row:last-child{border-bottom:none}
.top3-rank{font-size:11px;color:var(--t3);width:16px;flex-shrink:0;text-align:center}
.top3-name{flex:1;font-size:12px;font-weight:600}
.top3-ticker{font-size:10px;color:var(--t3);margin-top:1px}
.top3-pct{font-size:13px;font-weight:700;flex-shrink:0}
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

def generate_html(market, news, stocks, ai_brief, dt, usdkrw_week=None, macro_hist=None, research_summary=None, stock_story=None, us_ai_brief=None, watchlist=None):
    """최종 HTML 생성"""
    kdate = korean_date(dt)
    gen_time = dt.strftime("%H:%M 생성")

    import json as _json_wl
    watchlist_json = _json_wl.dumps(watchlist or [], ensure_ascii=False)

    kospi_pct = d(market, 'kospi').get('pct') or 0
    if kospi_pct >= 1.0:
        dom_cls, dom_ico = 'up', '📈'
    elif kospi_pct <= -1.0:
        dom_cls, dom_ico = 'dn', '📉'
    else:
        dom_cls, dom_ico = 'blue', '➖'

    sp500_pct = d(market, 'sp500').get('pct') or 0
    us_cls = 'up' if sp500_pct >= 0 else 'dn'

    dom_summary = build_dom_summary(market)
    us_summary  = build_us_summary(market)

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
        fx_script = f'''(function(){{
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
}})();'''
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

    # 스토리형 시황 분석 섹션
    if ai_brief:
        keyword      = ai_brief.get('keyword', '')
        story        = ai_brief.get('story', '')
        sector_story = ai_brief.get('sector_story', '')
        watch_points = ai_brief.get('watch_points', [])
        wp_html = ''.join(f'<div class="story-watch">· {wp}</div>' for wp in watch_points)
        story_html = f'''<div class="section">
  <div class="story-wrap">
    <div class="story-keyword">{keyword}</div>
    <div class="story-block">
      <div class="story-label">📊 시황 흐름</div>
      <div class="story-text">{story}</div>
    </div>
    <div class="story-block">
      <div class="story-label">🏭 업종 스토리</div>
      <div class="story-text">{sector_story}</div>
    </div>
    {f'<div class="story-block"><div class="story-label">👀 오늘의 주목 포인트</div>{wp_html}</div>' if wp_html else ''}
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
        cards = ''
        for rp in research_summary:
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
        research_html = f'<div class="section"><div class="section-label">📋 오늘의 증권사 리포트</div>{cards}</div>'
    else:
        research_html = ''

    dom_news = news_html(news.get('domestic', []), 'nb-blue', '국내')
    int_news = news_html(news.get('international', []), 'nb-blue', '해외')
    re_news  = news_html(news.get('realestate', []),  'nb-orange', '부동산', 'var(--orange)')
    hot_news = news_html(news.get('hot', []),          'nb-red',  '이슈')

    # 주도주 & 체감
    if stocks:
        breadth = stocks.get('breadth', {})
        b_up    = breadth.get('up', 0)
        b_dn    = breadth.get('down', 0)
        b_total = b_up + b_dn + breadth.get('flat', 0)
        b_up_pct = f"{b_up/b_total*100:.0f}" if b_total else '–'
        breadth_html = f'''<div class="breadth-wrap">
  <div class="breadth-bar">
    <div class="breadth-up" style="width:{b_up/b_total*100:.1f}%"></div>
  </div>
  <div class="breadth-label">
    <span class="up-txt">▲ {b_up}개 상승</span>
    <span style="color:var(--t3);margin:0 6px;">|</span>
    <span class="dn-txt">▼ {b_dn}개 하락</span>
    <span style="color:var(--t3);font-size:10px;margin-left:6px;">전체 {b_total}개</span>
  </div>
</div>'''
        top_amt_html  = stocks_html(stocks.get('top_amt', []))
        top_gain_html = stocks_html(stocks.get('top_gain', []))
    else:
        breadth_html  = '<div style="color:var(--t3);font-size:12px;padding:8px 0;">데이터 없음</div>'
        top_amt_html  = breadth_html
        top_gain_html = breadth_html

    # 캘린더
    cal_events = get_weekly_calendar(dt)
    if cal_events:
        cal_html = ''.join(f'''<div class="cal-row">
  <span class="news-badge {e["badge"]}">{e["label"]}</span>
  <span class="cal-name">{e["name"]}</span>
</div>''' for e in cal_events)
    else:
        cal_html = '<div style="color:var(--t3);font-size:12px;padding:8px 0;">이번 주 주요 일정 없음</div>'


    # 미국 공포/탐욕 지수
    us_fg = calc_us_fear_greed(market)
    
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
    if us_ai_brief:
        u_kw   = us_ai_brief.get('keyword', '')
        u_st   = us_ai_brief.get('story', '')
        u_sec  = us_ai_brief.get('sector_story', '')
        u_out  = us_ai_brief.get('outlook', '')
        us_story_html = f'''<div class="section">
  <div class="story-wrap" style="background: linear-gradient(135deg, rgba(77, 166, 255, 0.1), rgba(167, 139, 250, 0.05)); border-color: rgba(77, 166, 255, 0.3);">
    <div class="story-keyword" style="color: var(--blue); border-bottom-color: rgba(77, 166, 255, 0.2);">{u_kw}</div>
    <div class="story-block">
      <div class="story-label" style="color: var(--blue);">🌍 시장 서사</div>
      <div class="story-text">{u_st}</div>
    </div>
    <div class="story-block">
      <div class="story-label" style="color: var(--blue);">📈 섹터/종목 흐름</div>
      <div class="story-text">{u_sec}</div>
    </div>
    <div class="story-block">
      <div class="story-label" style="color: var(--blue);">🔭 향후 전망</div>
      <div class="story-text">{u_out}</div>
    </div>
  </div>
</div>'''
    else:
        # AI 없을 때 규칙 기반 폴백
        fb = build_us_story_fallback(market)
        u_kw  = fb.get('keyword', '')
        u_st  = fb.get('story', '')
        u_sec = fb.get('sector_story', '')
        u_out = fb.get('outlook', '')
        us_story_html = f'''<div class="section">
  <div class="story-wrap" style="background: linear-gradient(135deg, rgba(77, 166, 255, 0.1), rgba(167, 139, 250, 0.05)); border-color: rgba(77, 166, 255, 0.3);">
    <div class="story-keyword" style="color: var(--blue); border-bottom-color: rgba(77, 166, 255, 0.2);">{u_kw}</div>
    <div class="story-block">
      <div class="story-label" style="color: var(--blue);">🌍 시장 서사</div>
      <div class="story-text">{u_st}</div>
    </div>
    <div class="story-block">
      <div class="story-label" style="color: var(--blue);">📈 매크로 / 변동성</div>
      <div class="story-text">{u_sec}</div>
    </div>
    <div class="story-block">
      <div class="story-label" style="color: var(--blue);">🔭 기술적 포인트</div>
      <div class="story-text">{u_out}</div>
    </div>
  </div>
</div>'''

    # 해외 섹터 HTML (색상 막대 바)
    sector_pct_list = [abs(d(market, k).get('pct', 0)) for k in US_SECTOR_MAP]
    max_sector_pct = max(sector_pct_list) if sector_pct_list else 5
    us_sectors_html = ''
    for k, name in US_SECTOR_MAP.items():
        item = d(market, k)
        pct = item.get('pct', 0)
        cls = 'up-txt' if pct >= 0 else 'dn-txt'
        bar_color = 'var(--up)' if pct >= 0 else 'var(--dn)'
        bar_width = min(abs(pct) / max(max_sector_pct, 0.01) * 100, 100)
        sign = '+' if pct >= 0 else ''
        us_sectors_html += f'''<div class="sector-bar-row">
  <div class="sector-bar-name">{name}</div>
  <div class="sector-bar-wrap"><div class="sector-bar-fill" style="width:{bar_width:.1f}%;background:{bar_color}"></div></div>
  <div class="sector-bar-pct {cls}">{sign}{pct:.2f}%</div>
</div>'''

    # 해외 주요 종목 HTML
    us_stocks_html = ''
    for k, name in US_STOCK_MAP.items():
        item = d(market, k)
        pct = item.get('pct', 0)
        cls = 'up-txt' if pct >= 0 else 'dn-txt'
        sign = '+' if pct >= 0 else ''
        us_stocks_html += f'''<div class="stock-row" style="padding: 6px 10px;">
      <div class="stock-name" style="font-size:10.5px; max-width: 85px;">{name}</div>
      <div class="stock-right">
        <span class="{cls}" style="font-size:10.5px; font-weight:700;">{sign}{pct:.2f}%</span>
      </div>
    </div>'''

    # 급등/급락 Top 3
    us_stock_sorted = sorted(
        [(k, name, d(market, k).get('pct', 0)) for k, name in US_STOCK_MAP.items()],
        key=lambda x: x[2], reverse=True
    )
    def _top3_row(rank, k, name, pct):
        cls = 'up-txt' if pct >= 0 else 'dn-txt'
        sign = '+' if pct >= 0 else ''
        return f'''<div class="top3-row">
  <div class="top3-rank">{rank}</div>
  <div><div class="top3-name">{name}</div><div class="top3-ticker">{k.upper()}</div></div>
  <div class="top3-pct {cls}">{sign}{pct:.2f}%</div>
</div>'''

    us_gainers_html = ''.join(_top3_row(i+1, k, n, p) for i, (k, n, p) in enumerate(us_stock_sorted[:3]))
    us_losers_html  = ''.join(_top3_row(i+1, k, n, p) for i, (k, n, p) in enumerate(us_stock_sorted[-3:][::-1]))

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
</head>
<body>

<div class="header">
  <div>
    <div class="header-title">📈 국내 주식</div>
    <div class="header-date">{kdate}</div>
    <div class="header-day">장 마감 기준</div>
  </div>
  <div class="header-right">{gen_time}<br><button class="update-btn" id="dashUpdateBtn" onclick="dashUpdate()">지금 업데이트</button><span class="update-status" id="dashUpdateStatus"></span></div>
</div>

<nav class="tab-nav">
  <button class="tab-btn active" onclick="sw('dom',this)">📈 국내</button>
  <button class="tab-btn" onclick="sw('us',this)">🌐 해외</button>
  <button class="tab-btn" onclick="sw('re',this)">🏠 부동산</button>
  <button class="tab-btn" onclick="sw('hot',this)">🔥 핫이슈</button>
  <button class="tab-btn" onclick="sw('cal',this)">📅 일정</button>
  <button class="tab-btn" onclick="sw('watch',this)">📊 종목</button>
</nav>

<!-- ===== 국내 탭 ===== -->
<div id="tab-dom" class="tab-panel active">

  <div class="section">
    <div class="banner {dom_cls}">
      <strong>{dom_ico} 오늘 시황</strong><br>
      <span style="display:block;margin-bottom:4px;">코스피 &nbsp;<strong>{vdisp(market,'kospi')}</strong> &nbsp;{cdisp(market,'kospi')}</span>
      <span style="display:block;margin-bottom:6px;">코스닥 &nbsp;<strong>{vdisp(market,'kosdaq')}</strong> &nbsp;{cdisp(market,'kosdaq')}</span>
      <span style="font-size:11.5px;opacity:.9;line-height:1.6">{dom_summary}</span>
    </div>
  </div>

  {story_html}

  <div class="section">
    <div class="section-label">국내 지수</div>
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
  </div>

  <div class="section">
    <div class="section-label">미국 주요 지수 <span style="font-size:9px;color:var(--t3);font-weight:400;">탭하면 추이 차트</span></div>
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
  </div>

  <div class="section">
    <div class="section-label">매크로 지표 <span style="font-size:9px;color:var(--t3);font-weight:400;">탭하면 추이 차트</span></div>
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

  <div class="section">
    <div class="section-label">📊 업종별 등락률</div>
    <div style="background:var(--card);border-radius:10px;padding:12px 14px;">
      <canvas id="sectorChart" height="200"></canvas>
    </div>
  </div>

  <div class="section">
    <div class="section-label">📊 시장 체감 온도</div>
    {breadth_html}
  </div>

  <div class="section">
    <div class="stock-story-wrap">
      <div class="stock-list-col">
        <div class="ss-sub-label">📈 거래대금</div>
        {top_amt_html}
        <div class="ss-sub-label" style="margin-top:10px">🚀 급등주</div>
        {top_gain_html}
      </div>
      <div class="stock-story-col">
        {stock_story_html}
      </div>
    </div>
  </div>

  {research_html}

  <div class="section">
    <div class="section-label">국내 주식 뉴스</div>
    {dom_news}
  </div>

</div>

<!-- ===== 해외 탭 ===== -->
<div id="tab-us" class="tab-panel">

  <div class="section">
    <div class="banner {us_cls}">
      <strong>🌐 해외 시황</strong><br>
      S&amp;P500 {vdisp(market,'sp500')} {cdisp(market,'sp500')} &nbsp;|&nbsp;
      나스닥 {vdisp(market,'nasdaq')} {cdisp(market,'nasdaq')}<br>
      <span style="font-size:11.5px;opacity:.9;line-height:1.6">{us_summary}</span>
    </div>
    {us_fg_banner_html}
  </div>

  <div class="section">
    <div class="section-label">주요 지수 <span style="font-size:9px;color:var(--t3);font-weight:400;">탭하면 추이 차트</span></div>
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
  </div>

  <div class="section">
    <div class="section-label">섹터별 성적표</div>
    <div style="background:var(--card);border:1px solid var(--border);border-radius:12px;padding:12px 14px;">
      {us_sectors_html}
    </div>
  </div>

  <div class="section">
    <div class="section-label">급등 / 급락 Top 3</div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
      <div style="background:var(--card);border:1px solid rgba(0,232,150,.2);border-radius:12px;padding:10px 12px;">
        <div style="font-size:10px;color:var(--up);font-weight:700;margin-bottom:6px;">🚀 급등</div>
        {us_gainers_html}
      </div>
      <div style="background:var(--card);border:1px solid rgba(255,64,96,.2);border-radius:12px;padding:10px 12px;">
        <div style="font-size:10px;color:var(--dn);font-weight:700;margin-bottom:6px;">📉 급락</div>
        {us_losers_html}
      </div>
    </div>
  </div>

  {us_story_html}

  <div class="section">
    <div class="section-label">주요 종목 동향</div>
    <div style="display:grid;grid-template-columns: 1fr 1fr; gap: 6px;">
      {us_stocks_html}
    </div>
  </div>

  <div class="section">
    <div class="section-label">기술적 신호 리포트</div>
    <div style="background:var(--card);border:1px solid var(--border);border-radius:12px;padding:12px 14px;">
      {us_tech_html}
    </div>
  </div>

  <div class="section">
    <div class="section-label">데이터 및 매크로</div>
    <div class="macro-grid">
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
    <div class="section-label">해외 뉴스</div>
    {int_news}
  </div>

</div>

<!-- ===== 부동산 탭 ===== -->
<div id="tab-re" class="tab-panel">

  <div class="section">
    <div class="banner orange">
      <strong>🏠 송파구 단지 시세 트래커</strong><br>
      거여4단지 · 문정시영 최신 시세 및 리모델링 현황
    </div>
  </div>

  <div class="section">
    <div class="section-label">거여4단지</div>
    <div class="apt-card">
      <div class="apt-header">
        <div>
          <div class="apt-name">거여4단지</div>
          <div class="apt-info">거여동 · 5호선 거여역 도보 6분 · 546세대 · 1997년</div>
        </div>
        <div class="apt-status status-normal">투기지역</div>
      </div>
      <table class="apt-table">
        <thead><tr><th>평형</th><th>실거래 (2025.11)</th><th>KB시세</th></tr></thead>
        <tbody>
          <tr><td><strong>17평</strong> 49㎡</td><td>8억4,790만</td><td style="color:var(--t3)">하위 8억5천</td></tr>
          <tr><td><strong>21평</strong> 59㎡</td><td>10억4,000만</td><td style="color:var(--t3)">상위 9억2천</td></tr>
          <tr><td><strong>26평</strong> 72㎡</td><td>8억9,000만</td><td style="color:var(--t3)">평균 8억9천</td></tr>
        </tbody>
      </table>
      <div class="invest-point">
        📍 1년 상승률 +3.81% · 거여역 도보권 · 재건축 인근 단지<br>
        송파구 평균 대비 저평가 (평당 3,992만 vs 구 평균 6,909만)<br>
        <span class="warn">⚠ 최신 실거래가는 호갱노노·KB부동산에서 확인</span>
      </div>
    </div>
  </div>

  <div class="section">
    <div class="section-label">문정시영</div>
    <div class="apt-card">
      <div class="apt-header">
        <div>
          <div class="apt-name">문정시영</div>
          <div class="apt-info">문정동 · 개롱역~거여역 사이 · 1,316세대 · 1989년</div>
        </div>
        <div class="apt-status status-remodel">리모델링</div>
      </div>
      <table class="apt-table">
        <thead><tr><th>평형</th><th>실거래 (2025 하반기)</th><th>현재 호가</th></tr></thead>
        <tbody>
          <tr><td><strong>12평</strong> 25㎡</td><td>4억7,270만</td><td style="color:var(--orange)">6억</td></tr>
          <tr><td><strong>16평</strong> 35㎡</td><td>5억8,100만</td><td style="color:var(--orange)">7억 중반</td></tr>
          <tr><td><strong>18평</strong> 39㎡</td><td>7억5,705만</td><td style="color:var(--orange)">9억 초반</td></tr>
          <tr><td><strong>22평</strong> 46㎡</td><td>9억5,850만</td><td style="color:var(--orange)">10억 초반</td></tr>
        </tbody>
      </table>
      <div class="remodel-steps">
        <div class="remodel-label">리모델링 진행 — 포스코이앤씨 · 더샵 골든하임</div>
        <div class="step-row step-done"><div class="step-dot"></div>
          <div class="step-text">조합설립 · 시공사 선정 · 안전진단 · 교통영향평가 · 도시건축위 사전자문 완료</div></div>
        <div class="step-row step-current"><div class="step-dot"></div>
          <div class="step-text">건축심의 + 안전성검토 진행 중 (2026년 중반 결론 예상)</div></div>
        <div class="step-row step-todo"><div class="step-dot"></div>
          <div class="step-text">사업계획승인 → 1,316 → 1,440세대 (+124가구)</div></div>
      </div>
      <div class="invest-point">
        📍 강남3구 소형 최저가 · 더샵 브랜드 예정 · 18평 프리미엄↑<br>
        16·18평 시세 격차 1.5억 확대 · 문정동 전체 개발 기대감<br>
        <span class="warn">⚠ 최신 실거래가는 호갱노노·직방에서 확인</span>
      </div>
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
      FOMC · CPI · 한국은행 금통위 · 고용지표
    </div>
  </div>

  <div class="section">
    <div class="section-label">D-7 이내 일정</div>
    {cal_html}
    <div style="font-size:10px;color:var(--t3);margin-top:10px;">공모주 일정은 <a href="https://dart.fss.or.kr" target="_blank">DART</a> · <a href="https://ipo.38.co.kr" target="_blank">38커뮤니케이션</a> 확인</div>
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

<!-- 종목 상세 모달 -->
<div id="stockOverlay" onclick="closeStockModal()"></div>
<div id="stockModal"></div>

<div id="macroOverlay" onclick="closeMacroChart()"></div>
<div id="macroModal">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
    <div id="macroModalTitle" style="font-size:14px;font-weight:700;color:var(--t1);"></div>
    <button onclick="closeMacroChart()" style="background:none;border:none;color:var(--t3);font-size:22px;cursor:pointer;line-height:1;padding:0;">✕</button>
  </div>
  <canvas id="macroChartCanvas" height="110"></canvas>
  <div id="macroNoData" style="display:none;color:var(--t3);font-size:12px;text-align:center;padding:36px 0;">다음 업데이트 시 데이터 표시</div>
</div>

<div class="footer-note">
  {kdate} · {gen_time}<br>
  부동산 시세는 호갱노노·KB부동산에서 직접 확인 권장
</div>

<script>
var MACRO_META={macro_meta_json};
var MACRO_HIST={macro_hist_json};
var _mc=null;
function showMacroChart(k){{
  var m=MACRO_META[k],vals=MACRO_HIST[k]||[];
  if(!m)return;
  document.getElementById('macroOverlay').style.display='block';
  setTimeout(function(){{
    document.getElementById('macroOverlay').classList.add('open');
    document.getElementById('macroModal').classList.add('open');
  }},10);
  document.getElementById('macroModalTitle').textContent=m.name+' 최근 7일';
  var cv=document.getElementById('macroChartCanvas'),nd=document.getElementById('macroNoData');
  if(_mc){{_mc.destroy();_mc=null;}}
  if(!vals.length){{nd.style.display='block';cv.style.display='none';return;}}
  nd.style.display='none';cv.style.display='block';
  var ctx=cv.getContext('2d');
  var g=ctx.createLinearGradient(0,0,0,130);
  g.addColorStop(0,'rgba('+m.rgb+',0.25)');g.addColorStop(1,'rgba('+m.rgb+',0.02)');
  function fmt(v){{return m.pre+(m.dec===0?Math.round(v).toLocaleString():v.toFixed(m.dec))+m.suf;}}
  _mc=new Chart(ctx,{{type:'line',data:{{labels:vals.map(function(){{return '';}}),datasets:[{{data:vals,borderColor:m.color,backgroundColor:g,borderWidth:2,pointRadius:4,pointBackgroundColor:m.color,fill:true,tension:0.4,clip:false}}]}},options:{{layout:{{padding:{{top:24,bottom:4,left:16,right:16}}}},clip:false,responsive:true,plugins:{{legend:{{display:false}},tooltip:{{callbacks:{{label:function(c){{return fmt(c.raw);}}}}}},datalabels:{{color:m.color,font:{{size:9,weight:'600'}},formatter:function(v){{return fmt(v);}},anchor:'end',align:'top',offset:2,clamp:true}}}},scales:{{x:{{display:false}},y:{{display:false}}}}}},plugins:[ChartDataLabels]}});
}}
function closeMacroChart(){{
  document.getElementById('macroOverlay').classList.remove('open');
  document.getElementById('macroModal').classList.remove('open');
  setTimeout(function(){{document.getElementById('macroOverlay').style.display='none';}},280);
}}
(function(){{
  var ctx=document.getElementById('sectorChart').getContext('2d');
  var vals=[3.2,2.1,1.4,0.8,-0.5,-1.1,-1.8,-2.3];
  var lbls=['반도체','2차전지','자동차','금융','바이오','화학','철강','에너지'];
  var cols=vals.map(function(v){{return v>=0?'#ef4444':'#3b82f6';}});
  new Chart(ctx,{{
    type:'bar',
    data:{{labels:lbls,datasets:[{{data:vals,backgroundColor:cols,borderRadius:4,barThickness:14}}]}},
    options:{{
      indexAxis:'y',responsive:true,
      plugins:{{
        legend:{{display:false}},
        tooltip:{{callbacks:{{label:function(c){{return(c.raw>0?'+':'')+c.raw+'%';}}}}}},
        datalabels:{{
          color:function(ctx){{return ctx.dataset.data[ctx.dataIndex]>=0?'#ef4444':'#3b82f6';}},
          font:{{size:10,weight:'600'}},
          formatter:function(v){{return(v>0?'+':'')+v+'%';}},
          anchor:'end',align:'end',offset:2,clamp:true
        }}
      }},
      scales:{{
        x:{{display:false}},
        y:{{
          grid:{{display:false}},
          ticks:{{color:'#b8ccee',font:{{size:11}}}},
          border:{{color:'rgba(255,255,255,0.08)'}}
        }}
      }}
    }},
    plugins:[ChartDataLabels]
  }});
}})();
var _tabTitles={{dom:'📈 국내 주식',us:'🌐 해외',re:'🏠 부동산',hot:'🔥 핫이슈',cal:'📅 주요 일정',watch:'📊 관심 종목'}};
var WATCHLIST={watchlist_json};
function _fmt(v,dec,suf){{if(v===null||v===undefined)return'N/A';return(dec!==undefined?v.toFixed(dec):v)+(suf||'');}}
function _pctColor(v){{
  if(v===null||v===undefined)return'<span style="color:var(--t3)">N/A</span>';
  var c=v>=0?'var(--up)':'var(--dn)';
  return'<span style="color:'+c+'">'+(v>=0?'+':'')+v.toFixed(2)+'%</span>';
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
    return'<div class="wl-card" onclick="showStock(\''+s.ticker+'\')">'+
      '<div class="wl-card-top">'+
        '<div><div class="wl-name">'+s.name+'</div>'+
        '<div class="wl-ticker"><span class="wl-mkt-badge">'+s.market+'</span> '+s.ticker+'</div></div>'+
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
  var html=
    '<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:14px;">'+
      '<div>'+
        '<div style="font-size:15px;font-weight:700;color:var(--t1);">'+s.name+'</div>'+
        '<div style="font-size:10.5px;color:var(--t3);margin-top:2px;"><span class="wl-mkt-badge">'+s.market+'</span> '+s.ticker+(s.sector?' · '+s.sector:'')+'</div>'+
      '</div>'+
      '<button onclick="closeStockModal()" style="background:none;border:none;color:var(--t3);font-size:22px;cursor:pointer;padding:0;line-height:1;">✕</button>'+
    '</div>'+
    '<div style="background:var(--bg);border-radius:10px;padding:12px 14px;margin-bottom:12px;">'+
      '<div class="sk-price '+cls+'-txt">'+cur+p+'</div>'+
      '<div style="font-size:12px;color:var(--'+cls+');margin-top:2px;">'+sign+s.change_pct.toFixed(2)+'% ('+sign+cur+Math.abs(s.change).toFixed(2)+')</div>'+
      '<div style="font-size:10px;color:var(--t3);margin-top:6px;">시총 '+s.market_cap+' &nbsp;|&nbsp; 52주 '+cur+(s.low52||'N/A')+' ~ '+cur+(s.high52||'N/A')+'</div>'+
      (s.target?'<div style="font-size:10px;color:var(--t3);margin-top:2px;">목표주가 '+cur+s.target+' &nbsp;|&nbsp; 베타 '+(s.beta||'N/A')+'</div>':'')+
    '</div>'+
    sec('수익률')+
    '<div class="perf-grid">'+
      ['1W','1M','3M','6M','1Y'].map(function(p,i){{
        var v=[s.ret_1w,s.ret_1m,s.ret_3m,s.ret_6m,s.ret_1y][i];
        var c=v===null||v===undefined?'var(--t3)':v>=0?'var(--up)':'var(--dn)';
        var tx=v===null||v===undefined?'N/A':(v>=0?'+':'')+v.toFixed(1)+'%';
        return'<div class="perf-cell"><div class="perf-period">'+p+'</div><div class="perf-val" style="color:'+c+'">'+tx+'</div></div>';
      }}).join('')+
    '</div>'+
    sec('기술적 분석')+
    row('RSI (14)',s.rsi)+
    row('SMA 20 괴리율',s.sma20_gap!==null&&s.sma20_gap!==undefined?(s.sma20_gap>=0?'+':'')+s.sma20_gap+'%':'N/A')+
    row('SMA 50 괴리율',s.sma50_gap!==null&&s.sma50_gap!==undefined?(s.sma50_gap>=0?'+':'')+s.sma50_gap+'%':'N/A')+
    row('SMA 200 괴리율',s.sma200_gap!==null&&s.sma200_gap!==undefined?(s.sma200_gap>=0?'+':'')+s.sma200_gap+'%':'N/A')+
    sec('밸류에이션')+
    row('P/E (TTM)',_fmt(s.pe))+
    row('Forward P/E',_fmt(s.forward_pe))+
    row('P/B',_fmt(s.pb))+
    row('PEG',_fmt(s.peg))+
    row('EPS (TTM)',s.eps!==null&&s.eps!==undefined?cur+s.eps:'N/A')+
    sec('수익성')+
    row('영업이익률',s.op_margin!==null?s.op_margin+'%':'N/A')+
    row('순이익률',s.profit_margin!==null?s.profit_margin+'%':'N/A')+
    row('매출총이익률',s.gross_margin!==null?s.gross_margin+'%':'N/A')+
    row('ROE',s.roe!==null?s.roe+'%':'N/A')+
    row('ROA',s.roa!==null?s.roa+'%':'N/A')+
    sec('재무 건전성')+
    row('유동비율',_fmt(s.current_ratio))+
    row('부채비율',_fmt(s.debt_equity))+
    row('배당수익률',s.div_yield!==null&&s.div_yield!==0?s.div_yield+'%':'없음')+
    (s.desc?'<div style="font-size:10.5px;color:var(--t3);margin-top:12px;line-height:1.6;">'+s.desc+'</div>':'')+
    (s.news&&s.news.length?
      sec('관련 뉴스')+
      s.news.map(function(n){{
        return'<a href="'+n.link+'" target="_blank" style="display:block;text-decoration:none;padding:8px 0;border-bottom:1px solid rgba(255,255,255,.05);">'+
          '<div style="font-size:12px;color:var(--t1);line-height:1.5;margin-bottom:3px;">'+n.title+'</div>'+
          '<div style="font-size:10px;color:var(--t3);">'+n.publisher+(n.date?' · '+n.date:'')+'</div>'+
        '</a>';
      }}).join('')
    : '');
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
var _dashRunId=null,_dashPollTimer=null;
function _dashSetBusy(busy){{
  var btn=document.getElementById('dashUpdateBtn');
  btn.disabled=busy;
  btn.textContent=busy?'업데이트 중...':'지금 업데이트';
}}
function _dashStatus(msg){{document.getElementById('dashUpdateStatus').innerHTML=msg;}}
function _dashPoll(pat){{
  if(!_dashRunId)return;
  var p=pat||localStorage.getItem('dash_gh_pat');
  fetch('https://api.github.com/repos/mamibj112-spec/dashboard/actions/runs/'+_dashRunId,{{
    headers:{{'Authorization':'token '+p,'Accept':'application/vnd.github.v3+json'}}
  }}).then(function(r){{return r.json();}}).then(function(d){{
    var s=d.status,c=d.conclusion;
    if(s==='queued'){{_dashStatus('⏳ 대기 중...');}}
    else if(s==='in_progress'){{_dashStatus('⚙️ 업데이트 중...');}}
    else if(s==='completed'){{
      _dashSetBusy(false);
      clearInterval(_dashPollTimer);_dashPollTimer=null;_dashRunId=null;
      if(c==='success'){{_dashStatus('✅ 완료! <a href="javascript:location.reload()" style="color:#60a5fa;">새로고침</a>');}}
      else{{_dashStatus('❌ 실패 ('+c+')');}}
    }}
  }}).catch(function(){{_dashStatus('⚠️ 상태 확인 오류');}});
}}
function dashUpdate(){{
  var pat=localStorage.getItem('dash_gh_pat');
  if(!pat){{pat=prompt('GitHub PAT를 입력하세요 (repo workflow 권한 필요):');if(!pat)return;localStorage.setItem('dash_gh_pat',pat);}}
  _dashSetBusy(true);
  _dashStatus('요청 중...');
  var triggerTime=new Date().toISOString();
  fetch('https://api.github.com/repos/mamibj112-spec/dashboard/actions/workflows/daily.yml/dispatches',{{
    method:'POST',
    headers:{{'Authorization':'token '+pat,'Accept':'application/vnd.github.v3+json','Content-Type':'application/json'}},
    body:JSON.stringify({{ref:'main'}})
  }}).then(function(r){{
    if(r.status===204){{
      _dashStatus('⏳ 시작 중...');
      setTimeout(function(){{
        fetch('https://api.github.com/repos/mamibj112-spec/dashboard/actions/workflows/daily.yml/runs?per_page=5',{{
          headers:{{'Authorization':'token '+pat,'Accept':'application/vnd.github.v3+json'}}
        }}).then(function(r){{return r.json();}}).then(function(d){{
          var run=(d.workflow_runs||[])[0];
          if(run){{
            _dashRunId=run.id;
            _dashPollTimer=setInterval(function(){{_dashPoll(pat);}},5000);
            _dashPoll(pat);
          }}else{{_dashStatus('⚠️ 실행 중 — 1~2분 후 새로고침하세요');}}
        }}).catch(function(){{_dashStatus('⚠️ 실행 중 — 1~2분 후 새로고침하세요');}});
      }},5000);
    }}else{{
      _dashSetBusy(false);
      r.json().then(function(d){{_dashStatus('❌ 실패: '+(d.message||r.status));}}).catch(function(){{_dashStatus('❌ 실패 (PAT 권한 확인 필요)');}});
    }}
  }}).catch(function(){{_dashSetBusy(false);_dashStatus('❌ 네트워크 오류');}});
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
    dt = now_kst()
    print(f"대시보드 생성 중: {korean_date(dt)}")

    market   = fetch_market()
    news     = fetch_news()
    stocks   = fetch_market_stocks()
    ai_brief     = fetch_ai_briefing(market, news)
    us_ai_brief  = fetch_us_ai_briefing(market, news)

    research_reports = fetch_research_reports()
    research_summary = fetch_research_summary(research_reports)
    stock_story      = fetch_stock_story(stocks)

    usdkrw_week  = fetch_usdkrw_week()
    macro_hist   = fetch_macro_history()

    print("관심 종목 수집 중...")
    watchlist = fetch_watchlist_data(WATCHLIST)

    html = generate_html(market, news, stocks, ai_brief, dt, usdkrw_week=usdkrw_week, macro_hist=macro_hist, research_summary=research_summary, stock_story=stock_story, us_ai_brief=us_ai_brief, watchlist=watchlist)

    out = Path(__file__).parent / 'index.html'
    out.write_text(html, encoding='utf-8')
    print(f"저장 완료: {out}")

    for icon in ['icon-192.png', 'icon-512.png']:
        if not (Path(__file__).parent / icon).exists():
            print("아이콘 생성 중...")
            create_icons()
            break

    print("완료!")

if __name__ == '__main__':
    main()
