// "핵심 지표 상세" 섹션 렌더링 (캡처2)
(function () {
  var PERIOD_LABELS = { '6m': '최근 6개월', '3m': '최근 3개월', '12m': '최근 1년' };

  function badgeClass(cls) {
    if (cls === 'fc-down') return 'fc-warn';
    if (cls === 'fc-up') return 'fc-good';
    return 'fc-neutral';
  }

  function card(field, info) {
    var valueHtml = info.text;
    if (info.badge) {
      valueHtml += ' <span class="fc-badge ' + badgeClass(info.cls) + '">' + info.badge + '</span>';
    }
    return '<div class="fc-card">' +
      '<div class="fc-label">' + field.label + '</div>' +
      '<div class="fc-value' + (info.cls ? ' ' + info.cls : '') + '">' + valueHtml + '</div>' +
      (info.sub ? '<div class="fc-sub">' + info.sub + '</div>' : '') +
      (field.tip ? '<div class="fc-tip">💡 ' + field.tip + '</div>' : '') +
      '</div>';
  }

  function renderDetail(d) {
    var sh = window.fcShared;
    var html = '';

    DETAIL_GROUPS.forEach(function (group) {
      var cards = '';
      group.fields.forEach(function (field) {
        var info = formatDetailField(field, d, sh);
        if (field.sub && d[field.sub] != null && info.text !== '-') {
          info.sub = PERIOD_LABELS[d[field.sub]] || d[field.sub];
        }
        cards += card(field, info);
      });
      html += '<div class="fc-subhead">' + group.title + '</div><div class="fc-grid">' + cards + '</div>';
    });

    html += '<div class="fc-footnote">' +
      '* 지수 편입 현황은 "어떤 회사인가요" 섹션에서 확인할 수 있습니다.<br>' +
      '* 옵션 거래 가능 여부 및 체결건수(Trades)는 데이터 제공 범위 한계로 표시되지 않습니다.<br>' +
      '* 배당성장률(3년/5년)은 배당 이력 데이터가 충분하지 않아 표시되지 않습니다.' +
      '</div>';

    sh.setSection('fc-detail', html);
  }

  window.renderDetail = renderDetail;
})();
