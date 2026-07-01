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
      studies: ['MACD@tv-basicstudies', 'RSI@tv-basicstudies', 'Stochastic@tv-basicstudies'],
      allow_symbol_change: false,
      support_host: 'https://www.tradingview.com'
    });

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
  }

  window.renderTechList = renderTechList;
  window.selectTechSymbol = selectTechSymbol;
})();
