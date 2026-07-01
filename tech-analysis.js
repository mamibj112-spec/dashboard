// "기술적 분석" 탭: 관심종목 중 하나를 골라 TradingView 캔들차트 + 매수/매도 시그널만 보여줌
(function () {
  var selectedTicker = null;

  function renderTechList(q) {
    var box = document.getElementById('techList');
    if (!box) return;
    var t = (q || '').toLowerCase();
    var list = (window.WATCHLIST || []).filter(function (s) {
      return !t || s.ticker.toLowerCase().includes(t) || s.name.toLowerCase().includes(t);
    });
    if (!list.length) {
      box.innerHTML = '<div style="color:var(--t3);font-size:12px;padding:16px 0;text-align:center;">검색 결과 없음</div>';
      return;
    }
    box.innerHTML = list.map(function (s) {
      var active = selectedTicker === s.ticker ? ' tech-pick-active' : '';
      return '<div class="tech-pick' + active + '" onclick="selectTechSymbol(\'' + s.ticker + '\')">' +
        '<span class="tech-pick-name">' + s.name + '</span>' +
        '<span class="tech-pick-ticker">' + s.market + ' · ' + s.ticker + '</span>' +
      '</div>';
    }).join('');
  }

  function renderTechInsight(s) {
    var box = document.getElementById('techInsight');
    if (!box) return;

    var trendParts = [];
    var trendScore = 0;
    if (s.sma200_gap != null) { trendScore += s.sma200_gap > 0 ? 1 : -1; }
    if (s.sma50_gap != null) { trendScore += s.sma50_gap > 0 ? 1 : -1; }
    if (s.sma20_gap != null) { trendScore += s.sma20_gap > 0 ? 1 : -1; }

    if (s.sma20_gap != null && s.sma50_gap != null && s.sma200_gap != null) {
      if (s.sma20_gap > 0 && s.sma50_gap > 0 && s.sma200_gap > 0) {
        trendParts.push('20·50·200일선이 모두 정배열로, 단기·중기·장기 추세가 전부 상승 방향입니다.');
      } else if (s.sma20_gap < 0 && s.sma50_gap < 0 && s.sma200_gap < 0) {
        trendParts.push('20·50·200일선이 모두 역배열로, 단기·중기·장기 추세가 전부 하락 방향입니다.');
      } else if (s.sma20_gap < 0 && s.sma50_gap > 0) {
        trendParts.push('중장기 상승추세 안에서 단기적으로는 20일선 아래로 눌린 조정 구간입니다.');
      } else {
        trendParts.push('이동평균선들이 방향을 통일하지 못한 혼조 구간입니다.');
      }
    }

    var momentumParts = [];
    if (s.rsi != null) {
      if (s.rsi >= 70) momentumParts.push('RSI ' + s.rsi + '로 과매수 구간이라 단기 되돌림 가능성이 있습니다.');
      else if (s.rsi <= 30) momentumParts.push('RSI ' + s.rsi + '로 과매도 구간이라 단기 반등 가능성이 있습니다.');
      else momentumParts.push('RSI ' + s.rsi + '로 중립 구간입니다.');
    }

    var volParts = [];
    if (s.rel_volume != null) {
      if (s.rel_volume >= 1.5) volParts.push('거래량이 평소 대비 ' + s.rel_volume.toFixed(1) + '배로 관심이 몰리고 있습니다.');
      else if (s.rel_volume <= 0.6) volParts.push('거래량이 평소 대비 ' + s.rel_volume.toFixed(1) + '배로 한산한 편입니다.');
    }

    var rangeParts = [];
    if (s.high52 != null && s.price != null && s.high52 > 0) {
      var gapFromHigh = (s.price - s.high52) / s.high52 * 100;
      if (gapFromHigh > -5) rangeParts.push('52주 신고가 근처(' + gapFromHigh.toFixed(1) + '%)에 있습니다.');
    }
    if (s.low52 != null && s.price != null && s.low52 > 0) {
      var gapFromLow = (s.price - s.low52) / s.low52 * 100;
      if (gapFromLow < 10) rangeParts.push('52주 신저가 근처(+' + gapFromLow.toFixed(1) + '%)에 있습니다.');
    }

    var bias = trendScore > 0 ? '상승 우위' : (trendScore < 0 ? '하락 우위' : '혼조');
    var biasColor = trendScore > 0 ? 'var(--up)' : (trendScore < 0 ? 'var(--dn)' : 'var(--t3)');

    var html = '<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">' +
      '<span style="font-weight:700;color:' + biasColor + '">종합: ' + bias + '</span>' +
      '</div>' +
      '<div style="font-size:12.5px;line-height:1.7;color:var(--t2)">' +
      [trendParts.join(' '), momentumParts.join(' '), volParts.join(' '), rangeParts.join(' ')].filter(Boolean).join(' ') +
      '</div>' +
      '<div style="font-size:10px;color:var(--t3);margin-top:10px">⚠️ 지표를 종합한 현재 상태 설명일 뿐, 매수·매도 타이밍을 예측하거나 보장하지 않습니다.</div>';

    box.innerHTML = html;
  }

  function patternRow(p) {
    var horizons = ['5d', '10d', '20d'];
    var cells = horizons.map(function (h) {
      var f = p.forward[h];
      if (!f || !f.n) return '<div class="tp-cell"><div class="tp-h">' + h + '</div><div class="tp-v" style="color:var(--t3)">표본없음</div></div>';
      var cls = f.avgPct >= 0 ? 'up-txt' : 'dn-txt';
      var warn = f.reliable ? '' : ' ⚠️';
      return '<div class="tp-cell"><div class="tp-h">' + h + '</div>' +
        '<div class="tp-v ' + cls + '">' + (f.avgPct >= 0 ? '+' : '') + f.avgPct + '%</div>' +
        '<div class="tp-n">n=' + f.n + ' · 승률' + f.winRatePct + '%' + warn + '</div></div>';
    }).join('');
    var badge = p.current ? '<span style="background:var(--blue);color:#fff;font-size:9px;font-weight:700;padding:2px 6px;border-radius:4px;margin-left:6px">지금 이 상태</span>' : '';
    var rowStyle = p.current ? ' style="background:rgba(77,166,255,.06);border-radius:8px;padding:10px 8px;margin:2px 0"' : '';
    return '<div class="tp-row"' + rowStyle + '><div class="tp-label">' + p.label + badge + '</div><div class="tp-cells">' + cells + '</div></div>';
  }

  function currentMatchSummary(data) {
    var matched = data.patterns.filter(function (p) { return p.current; });
    if (!matched.length) return '';
    var lines = matched.map(function (p) {
      var f20 = p.forward['20d'];
      if (!f20 || !f20.n) return '지금 <b>' + p.label + '</b> 상태입니다. (과거 이후 20일 데이터 없음)';
      var warn = f20.reliable ? '' : ' — 표본이 적어 참고만';
      return '지금 <b>' + p.label + '</b> 상태입니다. 과거 이 상태 ' + f20.n + '번 중 이후 20일 평균 ' + (f20.avgPct >= 0 ? '+' : '') + f20.avgPct + '%, 승률 ' + f20.winRatePct + '%였습니다' + warn + '.';
    });
    return '<div style="border-top:1px solid var(--border);margin-top:10px;padding-top:10px;font-size:12.5px;line-height:1.7;color:var(--t2)">' +
      '<div style="font-weight:700;color:var(--t1);margin-bottom:6px">🔵 지금 상태와 일치하는 과거 패턴</div>' +
      lines.join('<br>') +
      '<div style="font-size:10px;color:var(--t3);margin-top:8px">⚠️ 이건 과거 기록이지 미래 예측이 아닙니다. "매수/매도하라"는 신호가 아니라 참고 정보입니다.</div>' +
      '</div>';
  }

  function loadTechPatterns(symbol) {
    var box = document.getElementById('techPatterns');
    if (!box) return;
    box.innerHTML = '<div style="color:var(--t3);font-size:12px;padding:12px 0;text-align:center;">⏳ 과거 패턴 분석 중...</div>';

    fetch(window._WORKER + '/patterns?symbol=' + encodeURIComponent(symbol))
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.error) { box.innerHTML = '<div style="color:var(--t3);font-size:12px;padding:12px 0;">❌ ' + data.error + '</div>'; return; }
        var rows = data.patterns.map(patternRow).join('');
        box.innerHTML =
          '<div style="font-size:10.5px;color:var(--t3);margin-bottom:10px">' +
            data.range.from + ' ~ ' + data.range.to + ' (' + data.range.bars + '거래일) · 단순보유 ' + (data.buyHoldPct >= 0 ? '+' : '') + data.buyHoldPct + '%' +
          '</div>' +
          rows +
          '<div style="font-size:10px;color:var(--t3);margin-top:10px">⚠️ n(표본 수)이 ' + RELIABLE_MIN_N_LABEL + '보다 적은 패턴은 통계적으로 신뢰하기 어렵습니다. 과거 패턴이 미래에 반복된다는 보장은 없습니다.</div>';

        var insightBox = document.getElementById('techInsight');
        if (insightBox) insightBox.innerHTML += currentMatchSummary(data);
      })
      .catch(function () {
        box.innerHTML = '<div style="color:var(--t3);font-size:12px;padding:12px 0;">❌ 네트워크 오류</div>';
      });
  }
  var RELIABLE_MIN_N_LABEL = '10회';

  function loadWidget(hostId, src, cfg) {
    var host = document.getElementById(hostId);
    if (!host) return;
    host.innerHTML = '<div class="tradingview-widget-container" style="height:100%"><div class="tradingview-widget-container__widget"></div></div>';
    var s = document.createElement('script');
    s.type = 'text/javascript';
    s.src = src;
    s.async = true;
    s.text = JSON.stringify(cfg);
    host.querySelector('.tradingview-widget-container').appendChild(s);
  }

  function selectTechSymbol(ticker) {
    var s = (window.WATCHLIST || []).find(function (x) { return x.ticker === ticker; });
    if (!s) return;
    selectedTicker = ticker;
    renderTechList(document.getElementById('techSearch').value);

    var symbol = window.tvSymbol(s);
    document.getElementById('techView').style.display = 'block';
    document.getElementById('techSymbolLabel').textContent = s.name + ' (' + s.ticker + ')';

    if (symbol.indexOf('KRX:') === 0) {
      var naverUrl = 'https://finance.naver.com/item/main.naver?code=' + symbol.replace('KRX:', '');
      document.getElementById('tech-chart').innerHTML =
        '<div style="height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px;color:var(--t3);font-size:12.5px;text-align:center;padding:0 20px">' +
          '<div>국내 종목은 TradingView 무료 차트가 지원되지 않아요.</div>' +
          '<button onclick="window.open(\'' + naverUrl + '\',\'_blank\')" style="background:var(--blue);border:none;border-radius:8px;padding:10px 16px;color:#fff;font-size:12px;font-weight:600;cursor:pointer;font-family:inherit">네이버 금융에서 차트 보기</button>' +
        '</div>';
    } else {
      loadWidget('tech-chart', 'https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js', {
        autosize: true,
        symbol: symbol,
        interval: 'D',
        timezone: 'Asia/Seoul',
        theme: 'dark',
        style: '1',
        locale: 'kr',
        backgroundColor: 'rgba(15, 19, 24, 1)',
        gridColor: 'rgba(255, 255, 255, 0.06)',
        studies: [
          { id: 'MASimple@tv-basicstudies', inputs: { length: 5 } },
          { id: 'MASimple@tv-basicstudies', inputs: { length: 10 } },
          { id: 'MASimple@tv-basicstudies', inputs: { length: 20 } },
          { id: 'MASimple@tv-basicstudies', inputs: { length: 60 } },
          { id: 'MASimple@tv-basicstudies', inputs: { length: 120 } },
          { id: 'MASimple@tv-basicstudies', inputs: { length: 240 } },
          { id: 'BB@tv-basicstudies' },
          'IchimokuCloud@tv-basicstudies',
          'MACD@tv-basicstudies',
          'RSI@tv-basicstudies',
          'Stochastic@tv-basicstudies'
        ],
        allow_symbol_change: false,
        support_host: 'https://www.tradingview.com'
      });
    }

    loadWidget('tech-signal', 'https://s3.tradingview.com/external-embedding/embed-widget-technical-analysis.js', {
      symbol: symbol,
      width: '100%',
      height: '100%',
      locale: 'kr',
      colorTheme: 'dark',
      isTransparent: true,
      interval: '1D',
      showIntervalTabs: true
    });

    renderTechInsight(s);
    loadTechPatterns(symbol);
  }

  window.renderTechList = renderTechList;
  window.selectTechSymbol = selectTechSymbol;
})();
