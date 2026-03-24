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

# ── 수급 데이터 ────────────────────────────────────────────────────────────────

def fetch_supply():
    """Naver Finance 코스피 수급 데이터 (실패 시 None 반환)"""
    try:
        from bs4 import BeautifulSoup
        url = "https://finance.naver.com/sise/sise_index_investor.nhn?code=KOSPI"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "ko-KR,ko;q=0.9",
            "Referer": "https://finance.naver.com/"
        }
        r = requests.get(url, headers=headers, timeout=10)
        r.encoding = 'euc-kr'
        soup = BeautifulSoup(r.text, 'html.parser')

        result = {}
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if len(cells) < 2:
                    continue
                label = cells[0].get_text(strip=True)
                val_str = cells[1].get_text(strip=True).replace(',', '').replace(' ', '')
                try:
                    val = int(val_str)
                except:
                    continue
                if '개인' in label:
                    result['individual'] = val
                elif '외국인' in label and 'institution' not in result:
                    result['foreign'] = val
                elif '기관계' in label or ('기관' in label and 'institution' not in result):
                    result['institution'] = val

        if len(result) >= 2:
            print(f"  수급 데이터 수집 완료: {result}")
            return result
        return None
    except Exception as e:
        print(f"  수급 데이터 오류: {e}")
        return None

def fmt_supply(val):
    if val is None:
        return 'N/A'
    av = abs(val)
    if av >= 10000:
        return f"{val/10000:.1f}조"
    return f"{val:,}억"

def supply_bar(val, label):
    if val is None:
        return f'''<div class="supply-row">
      <div class="supply-label">{label}</div>
      <div class="supply-bar-wrap">
        <div class="supply-center"></div>
        <div style="font-size:10px;color:var(--t3);padding:3px 8px;">실시간 앱 확인 <span class="warn">⚠</span></div>
      </div></div>'''
    is_buy = val >= 0
    pct = min(abs(val) / 20000 * 100, 100)
    amt = fmt_supply(val)
    if is_buy:
        return f'''<div class="supply-row">
      <div class="supply-label">{label}</div>
      <div class="supply-bar-wrap">
        <div class="supply-center"></div>
        <div class="supply-bar buy" style="width:{pct:.0f}%;">
          <span class="supply-amt buy">▲ {amt}</span>
        </div>
      </div></div>'''
    else:
        return f'''<div class="supply-row">
      <div class="supply-label">{label}</div>
      <div class="supply-bar-wrap">
        <div class="supply-center"></div>
        <div class="supply-bar sell" style="width:{pct:.0f}%;">
          <span class="supply-amt sell">▼ {fmt_supply(abs(val))}</span>
        </div>
      </div></div>'''

# ── 뉴스 ──────────────────────────────────────────────────────────────────────

RSS_FEEDS = {
    'domestic': [
        ('연합뉴스', 'https://www.yna.co.kr/rss/economy.xml'),
        ('연합인포맥스', 'https://news.einfomax.co.kr/rss/allList.xml'),
    ],
    'international': [
        ('Reuters', 'https://feeds.reuters.com/reuters/businessNews'),
        ('CNBC', 'https://www.cnbc.com/id/100003114/device/rss/rss.html'),
    ],
    'realestate': [
        ('연합뉴스', 'https://www.yna.co.kr/rss/realestate.xml'),
    ],
    'hot': [
        ('연합뉴스', 'https://www.yna.co.kr/rss/headlines.xml'),
    ],
}

def fetch_news():
    print("뉴스 수집 중...")
    news = {}
    for cat, feeds in RSS_FEEDS.items():
        items = []
        for source, url in feeds:
            try:
                f = feedparser.parse(url, request_headers={'User-Agent': 'Mozilla/5.0'})
                for entry in f.entries[:6]:
                    title = entry.get('title', '').strip()
                    link = entry.get('link', '#')
                    published = entry.get('published', '')
                    if title and len(title) > 5:
                        date_str = ''
                        if published:
                            try:
                                from email.utils import parsedate_to_datetime
                                dt = parsedate_to_datetime(published).astimezone(KST)
                                date_str = f"{dt.month}월 {dt.day}일"
                            except:
                                date_str = published[:10]
                        items.append({'title': title, 'url': link, 'date': date_str, 'source': source})
            except Exception as e:
                print(f"  RSS 오류 [{url}]: {e}")
        news[cat] = items[:7]
    return news

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
        out += f'''<div class="news-item"{style}>
  <span class="news-badge {badge_cls}">{badge_txt}</span>
  <div class="news-title"><a href="{url}" target="_blank">{title}</a></div>
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
.macro-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.macro-card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:11px 12px}
.macro-name{font-size:10px;color:var(--t3);margin-bottom:3px}
.macro-val{font-size:15px;font-weight:700}.macro-chg{font-size:11px;margin-top:2px}
.supply-wrap{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:14px}
.supply-row{display:flex;align-items:center;gap:8px;margin-bottom:10px}
.supply-row:last-child{margin-bottom:0}
.supply-label{font-size:11px;color:var(--t2);width:44px;flex-shrink:0}
.supply-bar-wrap{flex:1;position:relative;height:20px;background:var(--card2);border-radius:4px}
.supply-bar{position:absolute;top:0;bottom:0;border-radius:4px;display:flex;align-items:center}
.supply-bar.buy{left:50%;background:rgba(0,232,150,.25)}
.supply-bar.sell{right:50%;background:rgba(255,64,96,.25);justify-content:flex-end}
.supply-center{position:absolute;left:50%;top:0;bottom:0;width:1px;background:var(--border)}
.supply-amt{font-size:10px;font-weight:600;padding:0 5px;white-space:nowrap}
.supply-amt.buy{color:var(--up)}.supply-amt.sell{color:var(--dn)}
.supply-sub{font-size:10px;color:var(--t3);margin-top:8px;padding-top:8px;border-top:1px solid var(--border)}
.news-item{background:var(--card);border-radius:8px;padding:11px 12px;margin-bottom:6px;border-left:3px solid var(--border)}
.news-badge{display:inline-block;font-size:9px;padding:1px 6px;border-radius:3px;margin-bottom:4px;font-weight:600}
.nb-red{background:rgba(255,64,96,.15);color:#ff6080}.nb-blue{background:rgba(77,166,255,.15);color:var(--blue)}
.nb-green{background:rgba(0,232,150,.15);color:var(--up)}.nb-gold{background:rgba(255,201,64,.15);color:var(--gold)}
.nb-orange{background:rgba(255,140,58,.15);color:var(--orange)}.nb-purple{background:rgba(167,139,250,.15);color:var(--purple)}
.news-title{font-size:12.5px;font-weight:600;line-height:1.4}
.news-title a{color:var(--t1)}.news-title a:hover{color:var(--blue);text-decoration:none}
.news-meta{font-size:10px;color:var(--t3);margin-top:4px}
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
"""

# ── HTML 생성 ──────────────────────────────────────────────────────────────────

def generate_html(market, supply, news, dt):
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

    dom_news = news_html(news.get('domestic', []), 'nb-blue', '국내')
    int_news = news_html(news.get('international', []), 'nb-blue', '해외')
    re_news  = news_html(news.get('realestate', []),  'nb-orange', '부동산', 'var(--orange)')
    hot_news = news_html(news.get('hot', []),          'nb-red',  '이슈')

    if supply:
        sb_foreign = supply_bar(supply.get('foreign'), '외국인')
        sb_inst    = supply_bar(supply.get('institution'), '기관')
        sb_indiv   = supply_bar(supply.get('individual'), '개인')
        supply_note = ''
    else:
        sb_foreign = supply_bar(None, '외국인')
        sb_inst    = supply_bar(None, '기관')
        sb_indiv   = supply_bar(None, '개인')
        supply_note = '<span class="warn">⚠ 자동 조회 실패 — 실시간 앱 확인</span>'

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
</head>
<body>

<div class="header">
  <div>
    <div class="header-title">국장 데일리 대시보드</div>
    <div class="header-date">{kdate}</div>
    <div class="header-day">장 마감 기준</div>
  </div>
  <div class="header-right">{gen_time}<br>자동 업데이트</div>
</div>

<nav class="tab-nav">
  <button class="tab-btn active" onclick="sw('dom',this)">📈 국내</button>
  <button class="tab-btn" onclick="sw('us',this)">🇺🇸 해외</button>
  <button class="tab-btn" onclick="sw('re',this)">🏠 부동산</button>
  <button class="tab-btn" onclick="sw('hot',this)">🔥 핫이슈</button>
</nav>

<!-- ===== 국내 탭 ===== -->
<div id="tab-dom" class="tab-panel active">

  <div class="section">
    <div class="banner {dom_cls}">
      <strong>{dom_ico} 오늘 시황</strong><br>
      코스피 {vdisp(market,'kospi')} {cdisp(market,'kospi')} &nbsp;|&nbsp;
      코스닥 {vdisp(market,'kosdaq')} {cdisp(market,'kosdaq')}
    </div>
  </div>

  <div class="section">
    <div class="section-label">국내 지수</div>
    <div class="index-grid">
      <div class="idx-card">
        <div class="idx-name">코스피</div>
        <div class="idx-val">{vdisp(market,'kospi')}</div>
        <div class="idx-chg">{cdisp(market,'kospi')}</div>
      </div>
      <div class="idx-card">
        <div class="idx-name">코스닥</div>
        <div class="idx-val">{vdisp(market,'kosdaq')}</div>
        <div class="idx-chg">{cdisp(market,'kosdaq')}</div>
      </div>
    </div>
  </div>

  <div class="section">
    <div class="section-label">매크로 지표</div>
    <div class="macro-grid">
      <div class="macro-card">
        <div class="macro-name">USD/KRW</div>
        <div class="macro-val">{vdisp(market,'usdkrw')}</div>
        <div class="macro-chg">{cdisp(market,'usdkrw')}</div>
      </div>
      <div class="macro-card">
        <div class="macro-name">브렌트유</div>
        <div class="macro-val">{vdisp(market,'brent')}</div>
        <div class="macro-chg">{cdisp(market,'brent')}</div>
      </div>
      <div class="macro-card">
        <div class="macro-name">WTI</div>
        <div class="macro-val">{vdisp(market,'wti')}</div>
        <div class="macro-chg">{cdisp(market,'wti')}</div>
      </div>
      <div class="macro-card">
        <div class="macro-name">미 10년물</div>
        <div class="macro-val">{vdisp(market,'tnx')}</div>
        <div class="macro-chg">{cdisp(market,'tnx')}</div>
      </div>
      <div class="macro-card">
        <div class="macro-name">금 선물</div>
        <div class="macro-val">{vdisp(market,'gold')}</div>
        <div class="macro-chg">{cdisp(market,'gold')}</div>
      </div>
      <div class="macro-card">
        <div class="macro-name">달러 인덱스</div>
        <div class="macro-val">{vdisp(market,'dxy')}</div>
        <div class="macro-chg">{cdisp(market,'dxy')}</div>
      </div>
    </div>
  </div>

  <div class="section">
    <div class="section-label">코스피 수급 {supply_note}</div>
    <div class="supply-wrap">
      {sb_foreign}
      {sb_inst}
      {sb_indiv}
      <div class="supply-sub">코스닥 수급 · 선물 포지션은 실시간 앱 확인</div>
    </div>
  </div>

  <div class="section">
    <div class="section-label">국내 뉴스</div>
    {dom_news}
  </div>

</div>

<!-- ===== 해외 탭 ===== -->
<div id="tab-us" class="tab-panel">

  <div class="section">
    <div class="banner {us_cls}">
      <strong>🌐 해외 시황</strong><br>
      S&amp;P500 {vdisp(market,'sp500')} {cdisp(market,'sp500')} &nbsp;|&nbsp;
      나스닥 {vdisp(market,'nasdaq')} {cdisp(market,'nasdaq')}
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

  <div class="section">
    <div class="section-label">부동산 뉴스</div>
    {re_news}
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

<div class="footer-note">
  {kdate} · {gen_time}<br>
  <span class="warn">⚠</span> 수급 데이터 자동 조회 / 부동산 시세는 직접 확인 권장
</div>

<script>
function sw(id, btn) {{
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('tab-' + id).classList.add('active');
  btn.classList.add('active');
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

    market = fetch_market()
    supply = fetch_supply()
    news   = fetch_news()

    html = generate_html(market, supply, news, dt)

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
