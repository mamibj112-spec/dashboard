// "어떤 회사인가요?" 섹션 렌더링 (캡처3)
(function () {
  function card(label, value, sub) {
    return '<div class="fc-card"><div class="fc-label">' + label + '</div>' +
      '<div class="fc-value">' + value + '</div>' +
      (sub ? '<div class="fc-sub">' + sub + '</div>' : '') + '</div>';
  }

  function eventRow(title, dateStr, detail) {
    return '<div class="ov-event">' +
      '<div class="ov-event-date">' + dateStr + '</div>' +
      '<div class="ov-event-body"><div class="ov-event-title">' + title + '</div>' +
      (detail ? '<div class="ov-event-detail">' + detail + '</div>' : '') + '</div></div>';
  }

  function renderCompareChart(d, symbol) {
    var items = [];
    if (d.marketCapUSD != null) items.push({ label: '이 종목', value: d.marketCapUSD });
    if (d.samsungMarketCap != null) items.push({ label: '삼성전자', value: d.samsungMarketCap });

    var top = MARKETCAP_REFERENCE[0];
    if (top.tv !== symbol && d.marketCapUSD != null &&
        Math.abs(d.marketCapUSD - top.cap * 1e12) > top.cap * 1e12 * 0.01) {
      items.push({ label: top.name + ' (세계 1위)', value: top.cap * 1e12 });
    }

    if (items.length < 2) return '';

    var maxVal = Math.max.apply(null, items.map(function (i) { return i.value; }));
    var rows = items.map(function (item) {
      var pct = Math.max(2, (item.value / maxVal) * 100);
      return '<div class="ov-compare-row">' +
        '<div class="ov-compare-label">' + item.label + '</div>' +
        '<div class="ov-compare-track"><div class="ov-compare-fill" style="width:' + pct.toFixed(1) + '%"></div></div>' +
        '<div class="ov-compare-value">$' + (item.value / 1e12).toFixed(2) + 'T</div>' +
        '</div>';
    }).join('');

    return '<div class="ov-compare"><div class="fc-subhead">시가총액 비교</div>' + rows + '</div>';
  }

  function renderEvents(d, sh) {
    var upcoming = '', recent = '';

    if (d.nextEarnings && d.nextEarnings.date) {
      var days = daysUntil(d.nextEarnings.date);
      var dayStr = (days != null && days >= 0) ? ' (D-' + days + ')' : '';
      var parts = [];
      if (d.nextEarnings.epsEstimate != null) parts.push('예상 EPS ' + d.nextEarnings.epsEstimate.toFixed(2));
      if (d.nextEarnings.revenueEstimate != null) parts.push('예상 매출 ' + sh.fmtCap(d.nextEarnings.revenueEstimate, d.currency));
      upcoming += eventRow('실적발표', formatDateKo(d.nextEarnings.date) + dayStr, parts.join(' · '));
    }

    if (Array.isArray(d.recentDividends) && d.recentDividends.length) {
      var nextDiv = d.recentDividends[0];
      var dDays = daysUntil(nextDiv.date);
      if (dDays != null && dDays >= 0) {
        upcoming += eventRow('배당지급(예상)', formatDateKo(nextDiv.date) + ' (D-' + dDays + ')',
          '주당 ' + sh.fmtPrice(nextDiv.amount, d.currency));
      }
    }

    if (Array.isArray(d.earningsHistory) && d.earningsHistory.length) {
      d.earningsHistory.slice().reverse().slice(0, 4).forEach(function (h) {
        var sur = h.surprisePercent != null ? (h.surprisePercent >= 0 ? '+' : '') + h.surprisePercent.toFixed(1) + '%' : '-';
        var surCls = h.surprisePercent != null ? (h.surprisePercent >= 0 ? 'fc-up' : 'fc-down') : '';
        recent += eventRow(formatDateKo(h.date) + ' 실적',
          'EPS ' + (h.epsActual != null ? h.epsActual.toFixed(2) : '-') + ' (예상 ' + (h.epsEstimate != null ? h.epsEstimate.toFixed(2) : '-') + ')',
          '<span class="' + surCls + '">서프라이즈 ' + sur + '</span>');
      });
    }

    if (!upcoming && !recent) return '';

    var html = '<div class="ov-events">';
    if (upcoming) html += '<div class="fc-subhead">다가오는 이벤트</div>' + upcoming;
    if (recent) html += '<div class="fc-subhead">최근 실적 서프라이즈</div>' + recent;
    html += '<div class="fc-footnote">* 매출 서프라이즈%는 데이터 제공 범위 한계로 표시되지 않습니다.</div>';
    html += '</div>';
    return html;
  }

  function loadCompanyOverview(symbol, d) {
    fetch('company-overview.json')
      .then(function (res) { return res.ok ? res.json() : {}; })
      .then(function (data) {
        var info = data && data[symbol];
        var descEl = document.getElementById('ov-highlight');
        var badgesEl = document.getElementById('ov-badges');
        if (info && info.description) {
          if (descEl) descEl.textContent = info.description;
          if (badgesEl && Array.isArray(info.badges)) {
            info.badges.forEach(function (b) {
              badgesEl.insertAdjacentHTML('afterbegin', '<span class="fc-badge fc-good">' + b + '</span>');
            });
          }
          return;
        }
        fallbackDescription(descEl, d);
      })
      .catch(function () {
        fallbackDescription(document.getElementById('ov-highlight'), d);
      });
  }

  function fallbackDescription(descEl, d) {
    if (!descEl) return;
    descEl.textContent = d.longBusinessSummary
      ? d.longBusinessSummary.slice(0, 220) + (d.longBusinessSummary.length > 220 ? '...' : '')
      : '회사 소개 정보가 없습니다.';
  }

  function renderOverview(d) {
    var sh = window.fcShared;
    var symbol = sh.symbol;

    var scaleBadge = marketCapScaleLabel(d.marketCapUSD);
    var badgesHtml = scaleBadge ? '<span class="fc-badge fc-neutral">' + scaleBadge + '</span>' : '';

    var html = '';
    html += '<div class="ov-header">' +
      '<div class="ov-name">' + d.name + ' <span class="ov-ticker">' + symbol + '</span></div>' +
      '<div class="ov-badges" id="ov-badges">' + badgesHtml + '</div>' +
      '</div>';

    html += '<div class="ov-highlight" id="ov-highlight">회사 소개를 불러오는 중...</div>';

    var cards = '';
    var capSub = d.marketCapVsSamsung != null ? '삼성전자 시총의 ' + d.marketCapVsSamsung.toFixed(2) + '배' : null;
    cards += card('시가총액', sh.fmtCap(d.marketCap, d.currency), capSub);

    var rank = estimateMarketCapRank(d.marketCapUSD, symbol);
    var rankVal = rank != null ? '세계 약 ' + rank + '위' : (marketCapScaleLabel(d.marketCapUSD) || '-');
    cards += card('시총 순위', rankVal, '글로벌 대형주 기준 추정');

    cards += card('직원수', d.fullTimeEmployees != null ? sh.fmtNum(d.fullTimeEmployees, 0) + '명' : '-');
    cards += card('상장일', d.firstTradeDate ? formatDateCompact(d.firstTradeDate) : '-');

    var priceSub = d.priceKRW != null ? '약 ' + sh.fmtNum(d.priceKRW, 0) + '원' : null;
    cards += card('현재가', sh.fmtPrice(d.price, d.currency), priceSub);

    html += '<div class="fc-grid">' + cards + '</div>';

    html += renderCompareChart(d, symbol);

    var tags = (INDEX_MEMBERSHIP[symbol] || []).slice();
    if (d.exchangeName) tags.push(d.exchangeName);
    if (d.country) tags.push(d.country);
    if (tags.length) {
      html += '<div class="ov-tags">' + tags.map(function (t) {
        return '<span class="ov-tag">' + t + '</span>';
      }).join('') + '</div>';
    }

    html += renderEvents(d, sh);

    sh.setSection('fc-overview', html);
    loadCompanyOverview(symbol, d);
  }

  window.renderOverview = renderOverview;
})();
