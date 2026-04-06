#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
국장 데일리 대시보드 자동 생성기
Usage: python generate.py
"""
import sys
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
}

def fetch_market():
    print("시장 데이터 수집 중...")
    data = {}
    for name, sym in TICKERS.items():
        try:
            t = yf.Ticker(sym)
            hist = t.history(period='5d', auto_adjust=True)
            hist = hist.dropna(subset=['Close'])
            if len(hist) >= 2:
                prev = float(hist['Close'].iloc[-2])
                curr = float(hist['Close'].iloc[-1])
                chg = curr - prev
                pct = chg / prev * 100 if prev != 0 else 0
                data[name] = {'val': curr, 'chg': chg, 'pct': pct, 'ok': True}
            elif len(hist) == 1:
                data[name] = {'val': float(hist['Close'].iloc[-1]), 'chg': 0, 'pct': 0, 'ok': False}
            else:
                data[name] = {'val': None, 'chg': None, 'pct': None, 'ok': False}
        except Exception as e:
            print(f"  [{name}] 오류: {e}")
            data[name] = {'val': None, 'chg': None, 'pct': None, 'ok': False}
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

        resp = requests.post(
            f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}',
            json={'contents': [{'parts': [{'text': prompt}]}],
                  'generationConfig': {'temperature': 0.7, 'maxOutputTokens': 1024, 'thinkingConfig': {'thinkingBudget': 0}}},
            timeout=60
        )
        resp.raise_for_status()
        parts = resp.json()['candidates'][0]['content']['parts']
        text = next((p['text'] for p in parts if 'text' in p), '').strip()
        # JSON 파싱
        import json, re
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

        resp = requests.post(
            f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}',
            json={'contents': [{'parts': [{'text': prompt}]}],
                  'generationConfig': {'temperature': 0.3, 'maxOutputTokens': 1024, 'thinkingConfig': {'thinkingBudget': 0}}},
            timeout=60
        )
        resp.raise_for_status()
        parts = resp.json()['candidates'][0]['content']['parts']
        text = next((p['text'] for p in parts if 'text' in p), '').strip()
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

        resp = requests.post(
            f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}',
            json={'contents': [{'parts': [{'text': prompt}]}],
                  'generationConfig': {'temperature': 0.5, 'maxOutputTokens': 1024, 'thinkingConfig': {'thinkingBudget': 0}}},
            timeout=60
        )
        resp.raise_for_status()
        parts = resp.json()['candidates'][0]['content']['parts']
        text = next((p['text'] for p in parts if 'text' in p), '').strip()
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
        resp = requests.post(
            f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}',
            json={'contents': [{'parts': [{'text': prompt}]}],
                  'generationConfig': {'temperature': 0.3, 'maxOutputTokens': 1024, 'thinkingConfig': {'thinkingBudget': 0}}},
            timeout=60
        )
        resp.raise_for_status()
        parts = resp.json()['candidates'][0]['content']['parts']
        text = next((p['text'] for p in parts if 'text' in p), '').strip()
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if m:
            data = json.loads(m.group(0))
            result = data.get('reports', [])
            # index로 원본 URL 매핑
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
                for entry in f.entries[:10]:
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
        news['international'] = translate_news_to_korean(news['international'])
    return news

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
.update-btn{{display:inline-block;margin-top:5px;padding:4px 10px;font-size:10px;color:var(--blue);border:1px solid var(--blue);border-radius:6px;text-decoration:none;opacity:.8}}
.update-btn:hover{{opacity:1;text-decoration:none}}
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
"""

# ── HTML 생성 ──────────────────────────────────────────────────────────────────

def generate_html(market, news, stocks, ai_brief, dt, usdkrw_week=None, macro_hist=None, research_summary=None, stock_story=None):
    kdate = korean_date(dt)
    gen_time = dt.strftime("%H:%M 생성")

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
  <div class="header-right">{gen_time}<br><a class="update-btn" href="https://github.com/mamibj112-spec/dashboard/actions/workflows/daily.yml" target="_blank">지금 업데이트</a></div>
</div>

<nav class="tab-nav">
  <button class="tab-btn active" onclick="sw('dom',this)">📈 국내</button>
  <button class="tab-btn" onclick="sw('us',this)">🌐 해외</button>
  <button class="tab-btn" onclick="sw('re',this)">🏠 부동산</button>
  <button class="tab-btn" onclick="sw('hot',this)">🔥 핫이슈</button>
  <button class="tab-btn" onclick="sw('cal',this)">📅 일정</button>
</nav>

<!-- ===== 국내 탭 ===== -->
<div id="tab-dom" class="tab-panel active">

  <div class="section">
    <div class="banner {dom_cls}">
      <strong>{dom_ico} 오늘 시황</strong><br>
      코스피 {vdisp(market,'kospi')} {cdisp(market,'kospi')} &nbsp;|&nbsp;
      코스닥 {vdisp(market,'kosdaq')} {cdisp(market,'kosdaq')}<br>
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
  </div>

  <div class="section">
    <div class="section-label">해외 주요 지수</div>
    <div class="index-grid">
      <div class="idx-card">
        <div class="idx-name">S&amp;P 500</div>
        <div class="idx-val">{vdisp(market,'sp500')}</div>
        <div class="idx-chg">{cdisp(market,'sp500')}</div>
      </div>
      <div class="idx-card">
        <div class="idx-name">나스닥 100</div>
        <div class="idx-val">{vdisp(market,'nasdaq')}</div>
        <div class="idx-chg">{cdisp(market,'nasdaq')}</div>
      </div>
      <div class="idx-card">
        <div class="idx-name">다우존스</div>
        <div class="idx-val">{vdisp(market,'dow')}</div>
        <div class="idx-chg">{cdisp(market,'dow')}</div>
      </div>
      <div class="idx-card">
        <div class="idx-name">닛케이 225</div>
        <div class="idx-val">{vdisp(market,'nikkei')}</div>
        <div class="idx-chg">{cdisp(market,'nikkei')}</div>
      </div>
    </div>
  </div>

  <div class="section">
    <div class="section-label">글로벌 매크로</div>
    <div class="macro-grid">
      <div class="macro-card">
        <div class="macro-name">미 10년물</div>
        <div class="macro-val">{vdisp(market,'tnx')}</div>
        <div class="macro-chg">{cdisp(market,'tnx')}</div>
      </div>
      <div class="macro-card">
        <div class="macro-name">달러 인덱스</div>
        <div class="macro-val">{vdisp(market,'dxy')}</div>
        <div class="macro-chg">{cdisp(market,'dxy')}</div>
      </div>
      <div class="macro-card">
        <div class="macro-name">브렌트유</div>
        <div class="macro-val">{vdisp(market,'brent')}</div>
        <div class="macro-chg">{cdisp(market,'brent')}</div>
      </div>
      <div class="macro-card">
        <div class="macro-name">금 선물</div>
        <div class="macro-val">{vdisp(market,'gold')}</div>
        <div class="macro-chg">{cdisp(market,'gold')}</div>
      </div>
      <div class="macro-card">
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
var _tabTitles={{dom:'📈 국내 주식',us:'🌐 해외',re:'🏠 부동산',hot:'🔥 핫이슈',cal:'📅 주요 일정'}};
function sw(id, btn) {{
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('tab-' + id).classList.add('active');
  btn.classList.add('active');
  document.querySelector('.header-title').textContent=_tabTitles[id]||'국장 데일리 대시보드';
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
    ai_brief = fetch_ai_briefing(market, news)

    research_reports = fetch_research_reports()
    research_summary = fetch_research_summary(research_reports)
    stock_story = fetch_stock_story(stocks)

    macro_hist  = fetch_macro_history()
    html = generate_html(market, news, stocks, ai_brief, dt, macro_hist=macro_hist, research_summary=research_summary, stock_story=stock_story)

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
