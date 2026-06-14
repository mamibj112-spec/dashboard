(function () {
  var params = new URLSearchParams(location.search);
  var symbol = params.get('symbol') || 'NASDAQ:AAPL';

  var WORKER_BASE = (location.hostname === 'localhost' || location.hostname === '127.0.0.1')
    ? 'http://127.0.0.1:8787'
    : 'https://dashboard-trigger.mamibj112.workers.dev';

  function fmtPct(n, digits) {
    if (n === null || n === undefined || isNaN(n)) return '-';
    return (n * 100).toFixed(digits === undefined ? 1 : digits) + '%';
  }

  function fmtNum(n, digits) {
    if (n === null || n === undefined || isNaN(n)) return '-';
    return Number(n).toLocaleString('ko-KR', { maximumFractionDigits: digits === undefined ? 1 : digits, minimumFractionDigits: 0 });
  }

  function fmtCap(n, currency) {
    if (n === null || n === undefined) return '-';
    if (currency === 'KRW') return (n / 1e12).toFixed(1) + '조원';
    if (n >= 1e12) return '$' + (n / 1e12).toFixed(2) + 'T';
    if (n >= 1e9) return '$' + (n / 1e9).toFixed(2) + 'B';
    return '$' + (n / 1e6).toFixed(1) + 'M';
  }

  function card(label, value, sub, cls) {
    return '<div class="fc-card"><div class="fc-label">' + label + '</div>' +
      '<div class="fc-value' + (cls ? ' ' + cls : '') + '">' + value + '</div>' +
      (sub ? '<div class="fc-sub">' + sub + '</div>' : '') + '</div>';
  }

  function rangeBar(low, high, cur) {
    if (low == null || high == null || cur == null || high <= low) return '';
    var pct = Math.max(0, Math.min(100, (cur - low) / (high - low) * 100));
    return '<div class="fc-range">' +
      '<div class="fc-range-track">' +
        '<div class="fc-range-fill" style="width:' + pct.toFixed(1) + '%"></div>' +
        '<div class="fc-range-dot" style="left:' + pct.toFixed(1) + '%"></div>' +
      '</div>' +
      '<div class="fc-range-labels"><span>' + fmtNum(low, 0) + '</span>' +
      '<span class="fc-range-pct">52주 범위 내 ' + pct.toFixed(0) + '%</span>' +
      '<span>' + fmtNum(high, 0) + '</span></div></div>';
  }

  function setSection(id, html) {
    var el = document.getElementById(id);
    if (el) el.innerHTML = html;
    if (el) el.classList.remove('fc-empty');
  }

  function showEmpty(id, msg) {
    var el = document.getElementById(id);
    if (!el) return;
    el.className = 'fc-empty';
    el.textContent = msg;
  }

  function renderCore(d) {
    var html = '';
    html += card('시가총액', fmtCap(d.marketCap, d.currency),
      d.marketCapVsSamsung ? '삼성전자 시총의 ' + d.marketCapVsSamsung.toFixed(2) + '배' : null);
    html += card('PER (TTM / 선행)',
      (d.trailingPE != null ? d.trailingPE.toFixed(1) : '-') + ' / ' + (d.forwardPE != null ? d.forwardPE.toFixed(1) : '-'));
    html += card('배당수익률', fmtPct(d.dividendYield));

    var upside = (d.targetMeanPrice != null && d.price) ? (d.targetMeanPrice / d.price - 1) : null;
    html += card('애널리스트 목표가', d.targetMeanPrice != null ? fmtNum(d.targetMeanPrice, 2) : '-',
      upside != null ? (upside >= 0 ? '+' : '') + (upside * 100).toFixed(1) + '% 여력' : null,
      upside != null ? (upside >= 0 ? 'fc-up' : 'fc-down') : null);

    setSection('fc-core', '<div class="fc-grid">' + html + '</div>' + rangeBar(d.fiftyTwoWeekLow, d.fiftyTwoWeekHigh, d.price));
  }

  function healthCard(label, value, goodCond) {
    var cls = goodCond === null ? '' : (goodCond ? 'fc-good' : 'fc-warn');
    return card(label, value, null, cls);
  }

  function renderHealth(d) {
    var html = '';
    html += healthCard('영업이익률', fmtPct(d.operatingMargins), d.operatingMargins != null ? d.operatingMargins >= 0.1 : null);
    html += healthCard('순이익률', fmtPct(d.profitMargins), d.profitMargins != null ? d.profitMargins >= 0.08 : null);
    html += healthCard('매출총이익률', fmtPct(d.grossMargins), d.grossMargins != null ? d.grossMargins >= 0.3 : null);
    html += healthCard('ROE', fmtPct(d.returnOnEquity), d.returnOnEquity != null ? d.returnOnEquity >= 0.15 : null);
    html += healthCard('ROA', fmtPct(d.returnOnAssets), d.returnOnAssets != null ? d.returnOnAssets >= 0.05 : null);
    html += healthCard('부채비율(D/E)', d.debtToEquity != null ? (d.debtToEquity / 100).toFixed(2) : '-', d.debtToEquity != null ? d.debtToEquity <= 150 : null);
    html += healthCard('유동비율', d.currentRatio != null ? d.currentRatio.toFixed(2) : '-', d.currentRatio != null ? d.currentRatio >= 1.5 : null);
    html += healthCard('당좌비율', d.quickRatio != null ? d.quickRatio.toFixed(2) : '-', d.quickRatio != null ? d.quickRatio >= 1.0 : null);
    setSection('fc-health', '<div class="fc-grid">' + html + '</div>');
  }

  function renderOutlook(d) {
    var html = '';
    html += card('Forward PER', d.forwardPE != null ? d.forwardPE.toFixed(1) + '배' : '-');
    html += card('PEG', d.pegRatio != null ? d.pegRatio.toFixed(2) : '-',
      d.pegRatio != null ? (d.pegRatio < 1 ? '저평가' : d.pegRatio <= 2 ? '적정 평가' : '고평가') : null);
    html += card('EPS 성장률(연간)', fmtPct(d.earningsGrowth));
    html += card('매출 성장률', fmtPct(d.revenueGrowth));

    var recMap = {
      strong_buy: '적극매수', buy: '매수', hold: '중립',
      underperform: '비중축소', sell: '매도'
    };
    var extra = '';
    if (d.recommendationKey) {
      extra += '<div class="fc-rec">애널리스트 의견: <b>' + (recMap[d.recommendationKey] || d.recommendationKey) + '</b>' +
        (d.numberOfAnalystOpinions ? ' (' + d.numberOfAnalystOpinions + '명 평균)' : '') + '</div>';
    }
    if (d.targetHighPrice != null && d.targetLowPrice != null) {
      extra += '<div class="fc-rec">목표가 범위: <b>' + fmtNum(d.targetLowPrice, 2) + ' ~ ' + fmtNum(d.targetHighPrice, 2) + '</b></div>';
    }
    if (d.earningsDate) {
      extra += '<div class="fc-rec">다음 실적발표: <b>' + d.earningsDate + '</b></div>';
    }

    setSection('fc-outlook', '<div class="fc-grid">' + html + '</div>' + extra);
  }

  fetch(WORKER_BASE + '/finance?symbol=' + encodeURIComponent(symbol))
    .then(function (res) { return res.json(); })
    .then(function (d) {
      if (!d || d.error) {
        showEmpty('fc-core', '데이터를 불러올 수 없습니다.');
        showEmpty('fc-health', '데이터를 불러올 수 없습니다.');
        showEmpty('fc-outlook', '데이터를 불러올 수 없습니다.');
        return;
      }
      renderCore(d);
      renderHealth(d);
      renderOutlook(d);
    })
    .catch(function () {
      showEmpty('fc-core', '데이터를 불러올 수 없습니다.');
      showEmpty('fc-health', '데이터를 불러올 수 없습니다.');
      showEmpty('fc-outlook', '데이터를 불러올 수 없습니다.');
    });
})();
