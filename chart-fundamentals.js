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

  function fmtPrice(n, currency) {
    if (n === null || n === undefined || isNaN(n)) return '-';
    if (currency === 'KRW') return fmtNum(n, 0) + '원';
    return '$' + fmtNum(n, 2);
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

  function renderHealth(d) {
    var sector = (d.sector && HEALTH_BENCHMARKS[d.sector]) ? d.sector : 'default';
    var bench = HEALTH_BENCHMARKS[sector];
    var sectorLabel = d.sector || '전체';

    var values = {
      operatingMargins: d.operatingMargins,
      profitMargins: d.profitMargins,
      grossMargins: d.grossMargins,
      returnOnEquity: d.returnOnEquity,
      returnOnAssets: d.returnOnAssets,
      roic: d.roic,
      debtToEquity: d.debtToEquity != null ? d.debtToEquity / 100 : null,
      currentRatio: d.currentRatio,
      quickRatio: d.quickRatio
    };

    var profRows = '', healthRows = '';
    var profSum = 0, profCnt = 0, healthSum = 0, healthCnt = 0;

    HEALTH_METRICS.forEach(function (m) {
      var val = values[m.key];
      if (val == null) return;

      var t = healthTier(val, m.thresholds, m.higherIsBetter);
      var labels = m.tierLabels || ['주의', '양호', '우수'];
      var badgeCls = t === 0 ? 'fc-warn' : 'fc-good';
      var badgeIcon = t === 0 ? '⚠️' : '✅';
      var valStr = m.unit === 'pct' ? fmtPct(val) : val.toFixed(2);

      var pos = healthPosition(val, bench[m.key], m.higherIsBetter);
      var medianStr = m.unit === 'pct' ? fmtPct(bench[m.key]) : bench[m.key].toFixed(2);
      var labelPct = pos ? Math.min(92, Math.max(8, pos.pct)) : 0;

      var rowHtml = '<div class="fc-metric">' +
        '<div class="fc-metric-head">' +
          '<div><div class="fc-metric-label">' + m.label + '</div><div class="fc-metric-desc">' + m.desc + '</div></div>' +
          '<div class="fc-metric-val"><span class="fc-value-num">' + valStr + '</span><span class="fc-badge ' + badgeCls + '">' + badgeIcon + ' ' + labels[t] + '</span></div>' +
        '</div>' +
        (pos ?
          '<div class="fc-bar-wrap">' +
            '<div class="fc-bar-marker-label" style="left:' + labelPct + '%">내 위치 ' + pos.label + '</div>' +
            '<div class="fc-bar-track"><div class="fc-bar-marker" style="left:' + pos.pct + '%"></div></div>' +
          '</div>' +
          '<div class="fc-bench-text">' + sectorLabel + ' 중앙값 ' + medianStr + ' · ' + pos.label + '</div>'
          : '') +
        '<div class="fc-tip">💡 ' + m.tip + '</div>' +
        '</div>';

      if (m.group === 'profit') {
        profRows += rowHtml;
        profSum += t; profCnt++;
      } else {
        healthRows += rowHtml;
        healthSum += t; healthCnt++;
      }
    });

    if (!profRows && !healthRows) {
      showEmpty('fc-health', '데이터를 불러올 수 없습니다.');
      return;
    }

    var profRatio = profCnt ? profSum / (profCnt * 2) : null;
    var healthRatio = healthCnt ? healthSum / (healthCnt * 2) : null;
    var verdict = healthVerdict(profRatio, healthRatio);

    var html = '<div class="fc-verdict fc-verdict-' + verdict.cls + '">' +
      '<div class="fc-verdict-title">' + verdict.emoji + ' ' + verdict.title + '</div>' +
      '<div class="fc-verdict-sub">' + verdict.sub + '</div></div>';

    if (profRows) html += '<div class="fc-subhead">수익성 — 얼마나 효율적으로 돈을 버나</div>' + profRows;
    if (healthRows) html += '<div class="fc-subhead">재무 건전성 — 빚·유동성 부담은 괜찮나</div>' + healthRows;

    html += '<div class="fc-footnote">* 평가는 업종 중앙값 대비 상대 위치(근사값) + 절대 기준을 함께 참고한 결과입니다.</div>';

    setSection('fc-health', html);
  }

  function renderOutlook(d) {
    var upside = (d.targetMeanPrice != null && d.price) ? (d.targetMeanPrice / d.price - 1) : null;

    var values = {
      upside: upside,
      forwardPE: d.forwardPE,
      pegRatio: (d.pegRatio != null && d.pegRatio > 0) ? d.pegRatio : null,
      epsGrowthNextYear: d.epsGrowthNextYear,
      epsGrowthNext5Y: d.epsGrowthNext5Y
    };

    if (Object.keys(values).every(function (k) { return values[k] == null; })) {
      showEmpty('fc-outlook', '데이터를 불러올 수 없습니다.');
      return;
    }

    var scoreSum = 0, scoreCnt = 0;
    var cards = '';

    OUTLOOK_METRICS.forEach(function (m) {
      var val = values[m.key];
      if (m.scored) {
        var tier = outlookTier(val, m.thresholds, m.higherIsBetter);
        if (tier != null) { scoreSum += tier; scoreCnt++; }
      }

      var valStr = '-', valCls = '', subHtml = '';

      if (val != null) {
        if (m.key === 'upside') {
          valStr = fmtPrice(d.targetMeanPrice, d.currency);
          subHtml = '<div class="fc-sub ' + (upside >= 0 ? 'fc-up' : 'fc-down') + '">현재가 대비 ' +
            (upside >= 0 ? '+' : '') + (upside * 100).toFixed(1) + '%</div>';
        } else if (m.key === 'forwardPE') {
          valStr = val.toFixed(2) + '배';
        } else if (m.key === 'pegRatio') {
          valStr = val.toFixed(2);
          var t = outlookTier(val, m.thresholds, m.higherIsBetter);
          subHtml = '<div class="fc-sub ' + (t === 2 ? 'fc-up' : t === 0 ? 'fc-down' : '') + '">' + m.tierLabels[t] + '</div>';
        } else {
          valStr = (val >= 0 ? '+' : '') + fmtPct(val);
          valCls = val >= 0 ? 'fc-up' : 'fc-down';
        }
      }

      cards += '<div class="fc-card">' +
        '<div class="fc-label">' + m.label + '</div>' +
        '<div class="fc-value' + (valCls ? ' ' + valCls : '') + '">' + valStr + '</div>' +
        subHtml +
        '<div class="fc-tip">💡 ' + m.tip + '</div>' +
        '</div>';
    });

    var ratio = scoreCnt ? scoreSum / (scoreCnt * 2) : null;
    var verdict = outlookVerdict(ratio);

    var html = '<div class="fc-verdict fc-verdict-' + verdict.cls + '">' +
      '<div class="fc-verdict-title">' + verdict.emoji + ' ' + verdict.title + '</div>' +
      '<div class="fc-verdict-sub">' + verdict.sub + '</div></div>' +
      '<div class="fc-grid">' + cards + '</div>';

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
      extra += '<div class="fc-rec">목표가 범위: <b>' + fmtPrice(d.targetLowPrice, d.currency) + ' ~ ' + fmtPrice(d.targetHighPrice, d.currency) + '</b></div>';
    }
    if (extra) html += extra;

    html += '<div class="fc-footnote">⚠️ 이 데이터는 애널리스트 추정치이며 실제 결과와 다를 수 있습니다. 투자 결정은 추가 검토와 함께 하세요.</div>';

    setSection('fc-outlook', html);
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
