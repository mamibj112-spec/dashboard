# -*- coding: utf-8 -*-
"""국장 대시보드 테마 - 영어공부 대시보드(D:/Language Dash Board) 톤.
크림 종이 배경 + 주황 포인트 + Jua(제목)/IBM Plex Sans KR(본문).

CSS 변수(--up/--dn 등)뿐 아니라 generate.py가 인라인으로 쓰는 색(차트 선, 신호 배지,
lightweight-charts 설정 등)도 아래 상수를 가져다 쓴다 - 색을 바꿀 땐 여기만 고치면 됨.
"""

BG = "#FFFEF6"        # 종이 배경
CARD = "#FFFBEA"      # 카드
CARD2 = "#F4EEDA"     # 카드 안쪽/탭 바
INK = "#22202A"       # 본문 글자
INK2 = "#3F3A48"      # 보조 글자
MUTED = "#6B6475"     # 흐린 글자
ACCENT = "#D46A00"    # 주황 포인트(탭/버튼/링크)
UP = "#15803D"
DN = "#BE123C"
BLUE = "#1D4ED8"
GOLD = "#B45309"
ORANGE = "#C2410C"
PURPLE = "#7C3AED"
AMBER = "#D97706"
NEUTRAL = "#78716C"
GRID = "rgba(70,80,120,0.12)"   # 차트 격자
AXIS = "rgba(70,80,120,0.22)"   # 차트 축선


def rgb(hex_color):
    """'#15803D' -> '21,128,61' (rgba(...) 조립용)."""
    h = hex_color.lstrip("#")
    return ",".join(str(int(h[i:i + 2], 16)) for i in (0, 2, 4))


def tint(hex_color, alpha):
    return f"rgba({rgb(hex_color)},{alpha})"


FONT_LINKS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Jua'
    '&family=IBM+Plex+Sans+KR:wght@400;500;600;700&display=swap">'
)

CSS = """
:root{--bg:""" + BG + """;--card:""" + CARD + """;--card2:""" + CARD2 + """;--border:rgba(70,80,120,.18);
--up:""" + UP + """;--dn:""" + DN + """;--blue:""" + BLUE + """;--gold:""" + GOLD + """;--orange:""" + ORANGE + """;
--purple:""" + PURPLE + """;--t1:""" + INK + """;--t2:""" + INK2 + """;--t3:""" + MUTED + """;
--accent:""" + ACCENT + """;--accent-wash:rgba(245,158,11,.16);
--font-display:'Jua',sans-serif;
--font-body:'IBM Plex Sans KR',-apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Malgun Gothic",sans-serif}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--t1);font-family:var(--font-body);
font-size:13px;max-width:480px;margin:0 auto;padding-bottom:32px}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
.header{padding:18px 16px 0;display:flex;justify-content:space-between;align-items:flex-end}
.header-title{font-size:11px;color:var(--accent);letter-spacing:2px;font-weight:600}
.header-date{font-family:var(--font-display);font-size:19px;font-weight:400;color:var(--t1);white-space:nowrap}
.header-day{font-size:11px;color:var(--t3);margin-top:2px}
.header-right{text-align:right;font-size:11px;color:var(--t3)}
.update-btn{display:inline-block;white-space:nowrap;margin-top:5px;padding:5px 9px;font-size:10.5px;font-weight:600;font-family:inherit;color:var(--accent);border:1px solid var(--accent);border-radius:8px;background:var(--card);cursor:pointer}
.update-btn:hover{background:var(--accent-wash)}
.update-btn:disabled{opacity:.4;cursor:not-allowed}
.update-status{font-size:10px;color:var(--t3);display:block;text-align:right;margin-top:2px;min-height:14px}

.tab-nav{display:flex;flex-wrap:wrap;gap:4px;margin:12px 10px 0;
position:sticky;top:0;background:var(--card2);border-radius:10px;z-index:10;padding:4px;
box-shadow:0 2px 6px rgba(70,80,120,.08)}
.tab-btn{flex:1 1 18%;padding:8px 2px;background:none;border:none;border-radius:7px;
color:var(--t3);font-size:11.5px;font-weight:700;font-family:inherit;cursor:pointer;transition:all .2s;white-space:nowrap;text-align:center}
.tab-btn.active{color:#fff;background:var(--accent)}
.tab-panel{display:none;padding:0 12px}.tab-panel.active{display:block}
.section{margin-top:16px}
.section-label{font-size:10px;color:var(--t3);text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;padding-left:2px}
.banner{padding:12px 14px;border-radius:10px;border-left:3px solid;margin-top:12px;line-height:1.5;font-size:12.5px}
.banner.up{background:rgba(21,128,61,.08);border-color:var(--up)}
.banner.dn{background:rgba(190,18,60,.09);border-color:var(--dn)}
.banner.orange{background:rgba(194,65,12,.08);border-color:var(--orange)}
.banner.blue{background:rgba(29,78,216,.08);border-color:var(--blue)}
.banner.hot{background:rgba(190,18,60,.09);border-color:var(--gold)}
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
.nb-red{background:rgba(190,18,60,.15);color:var(--dn)}.nb-blue{background:rgba(29,78,216,.15);color:var(--blue)}
.nb-green{background:rgba(21,128,61,.15);color:var(--up)}.nb-gold{background:rgba(180,83,9,.15);color:var(--gold)}
.nb-orange{background:rgba(194,65,12,.15);color:var(--orange)}.nb-purple{background:rgba(124,58,237,.15);color:var(--purple)}
.news-title{font-size:14px;font-weight:700;line-height:1.45}
.news-title a{color:var(--t1)}.news-title a:hover{color:var(--blue);text-decoration:none}
.news-summary{font-size:11.5px;color:var(--t2);line-height:1.5;margin-top:5px}
.news-meta{font-size:10px;color:var(--t3);margin-top:5px}
.news-orig{font-size:10px;color:var(--t3);margin-top:3px;font-style:italic;opacity:.7}
.apt-card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:14px;margin-bottom:10px}
.apt-header{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px}
.apt-name{font-size:15px;font-weight:700}.apt-info{font-size:10px;color:var(--t3);margin-top:3px}
.apt-status{font-size:9px;padding:3px 7px;border-radius:4px;font-weight:600;flex-shrink:0}
.status-remodel{background:rgba(124,58,237,.15);color:var(--purple)}
.status-normal{background:rgba(29,78,216,.12);color:var(--blue)}
.apt-table{width:100%;border-collapse:collapse}
.apt-table th{font-size:10px;color:var(--t3);font-weight:400;padding:5px 6px;text-align:right;border-bottom:1px solid var(--border)}
.apt-table th:first-child{text-align:left}
.apt-table td{padding:7px 6px;border-bottom:1px solid rgba(70,80,120,.12);font-size:11px}
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
.idea-headline{font-size:15px;font-weight:800;color:var(--t1);text-align:center;padding:14px 0 6px;letter-spacing:-.3px;line-height:1.4}
.idea-card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:14px;margin-bottom:10px}
.idea-card-head{display:flex;align-items:center;gap:8px;margin-bottom:8px}
.idea-sector{font-size:13px;font-weight:700;color:var(--t1)}
.idea-badge{font-size:10px;font-weight:700;padding:2px 8px;border-radius:10px}
.idea-badge.up{background:rgba(21,128,61,.15);color:var(--up)}
.idea-badge.dn{background:rgba(190,18,60,.15);color:var(--dn)}
.idea-badge.warn{background:rgba(180,83,9,.15);color:var(--gold)}
.idea-body{font-size:12px;color:var(--t2);line-height:1.6}
.idea-meta{font-size:10.5px;margin-top:6px;display:flex;flex-direction:column;gap:3px}
.idea-meta span{display:flex;gap:5px}
.idea-meta-label{color:var(--t3);font-weight:600;flex-shrink:0}
.idea-theme{background:linear-gradient(135deg,rgba(124,58,237,.1),rgba(29,78,216,.08));border:1px solid rgba(124,58,237,.25);border-radius:12px;padding:14px;margin-bottom:10px}
.idea-theme-title{font-size:11px;color:var(--purple);font-weight:700;letter-spacing:.5px;margin-bottom:8px}
.risk-row{display:flex;gap:8px;align-items:flex-start;padding:8px 0;border-bottom:1px solid rgba(70,80,120,.12);font-size:12px;color:var(--t2);line-height:1.5}
.risk-row:last-child{border-bottom:none}
.risk-num{color:var(--dn);font-weight:700;flex-shrink:0}
.stock-row{display:flex;justify-content:space-between;align-items:center;padding:5px 8px;background:var(--card);border-radius:6px;margin-bottom:4px}
.stock-name{font-size:11px;font-weight:600;color:var(--t1);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:72px}
.etf-name{font-size:11px;font-weight:600;color:var(--t1);flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;padding-right:6px}
.stock-right{display:flex;align-items:center;gap:5px;font-size:11px;flex-shrink:0}
.stock-amt{color:var(--t3);font-size:9.5px}
.breadth-wrap{background:var(--card);border-radius:10px;padding:12px 14px}
.breadth-bar{height:8px;background:rgba(190,18,60,.3);border-radius:4px;overflow:hidden;margin-bottom:8px}
.breadth-up{height:100%;background:var(--up);border-radius:4px}
.breadth-label{font-size:12px;display:flex;align-items:center}
.wk-cal-table{background:var(--card);border:1px solid var(--border);border-radius:12px;overflow:hidden}
.wk-cal-row{display:flex;gap:12px;padding:12px 14px;border-bottom:1px solid var(--border)}
.wk-cal-row:last-child{border-bottom:none}
.wk-cal-date{flex:0 0 64px;font-size:12.5px;font-weight:700;color:var(--t2)}
.wk-cal-date.today{color:var(--gold)}
.wk-cal-items{flex:1;min-width:0;display:flex;flex-direction:column;gap:5px}
.wk-cal-item{font-size:12px;color:var(--t2);line-height:1.5}
.wk-cal-item.hl{color:var(--t1);font-weight:600;background:rgba(180,83,9,.12);border-radius:6px;padding:2px 6px;margin:-2px -6px}
.wk-cal-item.empty{color:var(--t3)}
.ai-brief-wrap{background:linear-gradient(135deg,rgba(124,58,237,.12),rgba(29,78,216,.08));border:1px solid rgba(124,58,237,.3);border-radius:12px;padding:14px}
.ai-brief-title{font-size:10px;color:var(--purple);font-weight:700;letter-spacing:.5px;margin-bottom:8px}
.ai-lines{margin-bottom:8px}
.ai-line{font-size:12.5px;color:var(--t1);line-height:1.7;font-weight:500}
.ai-tags{margin-bottom:6px}
.ai-tag{display:inline-block;font-size:11px;padding:3px 10px;border-radius:6px;font-weight:600}
.ai-tag.hot{background:rgba(180,83,9,.15);color:var(--gold);border:1px solid rgba(180,83,9,.3)}
.ai-supply{font-size:11px;color:var(--t2);padding-top:6px;border-top:1px solid rgba(70,80,120,.12)}
.macro-card{cursor:pointer;transition:opacity .15s}
.macro-card:active{opacity:.6}
.stock-story-wrap{display:flex;gap:10px;align-items:flex-start}
.stock-list-col{flex:0 0 44%;min-width:0}
.stock-story-col{flex:1;min-width:0}
.ss-sub-label{font-size:9px;color:var(--t3);text-transform:uppercase;letter-spacing:1px;margin-bottom:5px;padding-left:2px}
.ss-wrap{background:linear-gradient(135deg,rgba(180,83,9,.07),rgba(194,65,12,.05));border:1px solid rgba(180,83,9,.2);border-radius:12px;padding:12px;height:100%;box-sizing:border-box}
.ss-tone{font-size:11.5px;font-weight:700;color:var(--gold);margin-bottom:10px;padding-bottom:8px;border-bottom:1px solid var(--border);line-height:1.4}
.ss-block{margin-bottom:9px}.ss-block:last-child{margin-bottom:0}
.ss-label{font-size:9px;color:var(--gold);font-weight:700;letter-spacing:.5px;margin-bottom:4px}
.ss-theme{font-size:11px;font-weight:600;color:var(--t1);margin-bottom:3px}
.ss-text{font-size:10.5px;color:var(--t2);line-height:1.7}
.story-wrap{background:linear-gradient(135deg,rgba(29,78,216,.08),rgba(124,58,237,.06));border:1px solid rgba(29,78,216,.2);border-radius:12px;padding:14px}
.story-block{margin-bottom:10px}
.story-block:last-child{margin-bottom:0}
.story-label{font-size:10px;color:var(--blue);font-weight:700;letter-spacing:.5px;margin-bottom:5px}
.story-text{font-size:12px;color:var(--t2);line-height:1.75}
.mkt-sec-head{display:flex;align-items:center;gap:8px;margin-bottom:12px;padding-bottom:10px;border-bottom:1px solid var(--border)}
.mkt-sec-icon{font-size:15px}
.mkt-sec-title{font-size:14px;font-weight:700;color:var(--t1);flex:1}
.mkt-sec-num{font-size:10px;color:var(--t3);font-weight:700;background:var(--card2);padding:2px 7px;border-radius:6px}
.hashtag-row{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px}
.hashtag-pill{font-size:10.5px;color:var(--blue);background:rgba(29,78,216,.12);border:1px solid rgba(29,78,216,.25);border-radius:20px;padding:4px 10px;font-weight:600}
.highlight-list{margin-bottom:12px}
.highlight-item{display:flex;gap:8px;padding:7px 0;border-bottom:1px solid rgba(70,80,120,.12)}
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
.mover-card.up-side{border-color:rgba(21,128,61,.2)}
.mover-card.dn-side{border-color:rgba(190,18,60,.2)}
.mover-head{font-size:10px;font-weight:700;margin-bottom:7px}
.mover-head.up{color:var(--up)}
.mover-head.dn{color:var(--dn)}
.mover-row{display:flex;align-items:center;gap:7px;padding:4px 0}
.mover-ticker{font-size:11px;font-weight:700;color:var(--t1);flex:1}
.mover-pct{font-size:11px;font-weight:700}
.earn-list{margin-bottom:10px}
.earn-item{display:flex;gap:8px;padding:8px 0;border-bottom:1px solid rgba(70,80,120,.12)}
.earn-item:last-child{border-bottom:none}
.earn-item.is-extra{display:none}
.earn-item.is-extra.show{display:flex}
.earn-body{flex:1;min-width:0}
.earn-head{font-size:11.5px;font-weight:700;color:var(--t1);margin-bottom:2px;line-height:1.5}
.earn-period{color:var(--t3);font-weight:600}
.earn-summary{font-size:10.5px;color:var(--t2);line-height:1.6}
.earn-more-btn{display:block;width:100%;text-align:center;font-size:10.5px;font-weight:700;color:var(--blue);background:rgba(29,78,216,.1);border:1px solid rgba(29,78,216,.2);border-radius:8px;padding:7px;margin-bottom:12px;cursor:pointer}
.report-card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:12px 14px;margin-bottom:8px}
.report-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:4px}
.report-stock{font-size:13px;font-weight:700;color:var(--t1)}
.report-firm{font-size:10px;color:var(--purple);background:rgba(124,58,237,.12);padding:2px 7px;border-radius:10px}
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
.us-pct-box.up{background:rgba(21,128,61,.12);color:var(--up)}
.us-pct-box.dn{background:rgba(190,18,60,.15);color:var(--dn)}
.rsi-wrap{margin-top:8px}
.rsi-head{font-size:9px;color:var(--t3);display:flex;justify-content:space-between;margin-bottom:4px}
.rsi-bg{height:4px;background:rgba(70,80,120,.12);border-radius:2px;overflow:hidden}
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
.tech-row{display:flex;align-items:center;justify-content:space-between;padding:7px 0;border-bottom:1px solid rgba(70,80,120,.12)}
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
.wl-mkt-badge{background:rgba(29,78,216,.15);color:var(--blue);font-size:9px;padding:1px 5px;border-radius:3px;font-weight:700}
.wl-price{font-size:16px;font-weight:700}
.wl-pct{font-size:11px;font-weight:600;text-align:right}
.wl-card-bot{display:flex;gap:12px;font-size:10.5px;color:var(--t3)}
.tech-pick{display:flex;justify-content:space-between;align-items:center;padding:9px 12px;border-radius:10px;cursor:pointer;font-size:12.5px}
.tech-pick:active{background:var(--card)}
.tech-pick.tech-pick-active{background:var(--card);border:1px solid var(--blue)}
.tech-pick-ticker{color:var(--t3);font-size:10.5px}
.tech-chart-box{height:70vh;min-height:420px;background:var(--card2);border-radius:12px;overflow:hidden}
.tech-signal-box{height:450px;background:var(--card2);border-radius:12px;overflow:hidden}
.tech-insight-box{background:var(--card2);border-radius:12px;padding:14px;min-height:20px}
.tech-patterns-box{background:var(--card2);border-radius:12px;padding:14px;min-height:20px}
.tech-candles-box{background:var(--card2);border-radius:12px;padding:14px;min-height:20px}
.tc-item{display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--border);font-size:12px}
.tc-item:last-child{border-bottom:none}
.tc-date{color:var(--t3);font-size:10.5px}
.tc-tag{font-weight:600}
.tp-row{padding:10px 0;border-bottom:1px solid var(--border)}
.tp-row:last-child{border-bottom:none}
.tp-label{font-size:12px;font-weight:600;color:var(--t1);margin-bottom:8px}
.tp-cells{display:flex;gap:8px}
.tp-cell{flex:1;background:var(--card);border-radius:8px;padding:8px;text-align:center}
.tp-h{font-size:9.5px;color:var(--t3);text-transform:uppercase}
.tp-v{font-size:14px;font-weight:700;margin-top:2px}
.tp-n{font-size:9.5px;color:var(--t3);margin-top:2px}
.tradingview-widget-container,.tradingview-widget-container__widget{height:100%;width:100%}
#stockOverlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:300;transition:opacity .2s;opacity:0}
#stockOverlay.open{opacity:1}
#stockModal{position:fixed;bottom:0;left:0;right:0;max-width:480px;margin:0 auto;background:var(--card);border-radius:20px 20px 0 0;padding:20px 16px;z-index:301;max-height:88vh;overflow-y:auto;transform:translateY(100%);transition:transform .25s ease}
#stockModal.open{transform:translateY(0)}
.sk-price{font-size:24px;font-weight:800}
.sk-row{display:flex;justify-content:space-between;align-items:center;padding:7px 0;border-bottom:1px solid rgba(70,80,120,.12);font-size:12px}
.sk-row:last-child{border-bottom:none}
.sk-label{color:var(--t3)}
.sk-val{font-weight:600;color:var(--t1)}
.sk-sec{font-size:10px;color:var(--t3);text-transform:uppercase;letter-spacing:.8px;margin:12px 0 4px;padding-left:2px}
.perf-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:4px;margin-top:4px}
.perf-cell{background:var(--bg);border-radius:7px;padding:6px 4px;text-align:center}
.perf-period{font-size:9px;color:var(--t3);margin-bottom:2px}
.perf-val{font-size:11px;font-weight:700}

/* ── 영어공부 대시보드 톤 공통 덮어쓰기: 둥근 카드 + 옅은 그림자 + 제목 폰트 ── */
.idx-card,.macro-card,.news-item,.apt-card,.idea-card,.breadth-wrap,.wk-cal-table,
.us-card,.fg-card-mini,.wl-card,.report-card,.idea-theme,.ai-brief-wrap,.ss-wrap,.story-wrap{
border-radius:14px;box-shadow:0 1px 2px rgba(0,0,0,.06)}
.news-item{border:1px solid var(--border);border-left:3px solid var(--border)}
.section-label{font-family:var(--font-display);font-size:16px;color:var(--t1);
text-transform:none;letter-spacing:0;margin-bottom:10px}
.idea-headline,.mkt-sec-title,.apt-name{font-family:var(--font-display);font-weight:400}
.idea-headline{font-size:18px}
.mkt-sec-title{font-size:16px}
.wl-search:focus{border-color:var(--accent)}
.wl-card:active,.tech-pick.tech-pick-active{border-color:var(--accent)}
.earn-more-btn{color:var(--accent);background:var(--accent-wash);border-color:rgba(212,106,0,.3)}
#macroModal{box-shadow:0 -4px 24px rgba(70,80,120,.25)}
"""
