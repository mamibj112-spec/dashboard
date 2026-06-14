// "핵심 지표 상세" 섹션(캡처2) — 필드 정의(그룹/라벨/포맷) 및 포맷터
// type 종류:
//  price/cap        : fcShared.fmtPrice / fmtCap (통화 인식)
//  shares           : 주식수 약식 표기 (K/M/B)
//  ratio            : 소수 2자리
//  ratioX           : 소수 2자리 + "배"
//  days             : 소수 1자리 + "일"
//  pctFraction      : 0.0X 형태(소수)를 %로 변환, 부호에 따라 상승/하락 색상
//  pctFractionPlain : 0.0X 형태(소수)를 %로 변환, 부호/색상 없음 (지분율·배당성향 등 정적 비율)
//  pctRaw           : 이미 % 단위인 값, 부호에 따라 상승/하락 색상
//  pctRawPlain      : 이미 % 단위인 값, 색상 없음
//  rsi              : RSI(0~100) 전용 배지

var DETAIL_GROUPS = [
  {
    title: '거래 정보',
    fields: [
      { key: 'open', label: '시가', type: 'price' },
      { key: 'dayHigh', label: '일중 고가', type: 'price' },
      { key: 'dayLow', label: '일중 저가', type: 'price' },
      { key: 'regularMarketPreviousClose', label: '전일 종가', type: 'price' },
      { key: 'regularMarketVolume', label: '거래량', type: 'shares' },
      { key: 'averageVolume10days', label: '평균거래량 (10일)', type: 'shares' },
      { key: 'averageVolume', label: '평균거래량 (3개월)', type: 'shares' },
      { key: 'relativeVolume', label: '상대거래량', type: 'ratioX', tip: '최근 거래량이 3개월 평균 대비 몇 배인지' },
      { key: 'fiftyTwoWeekChange', label: '52주 변동률', type: 'pctFraction' }
    ]
  },
  {
    title: '밸류에이션',
    fields: [
      { key: 'priceToSales', label: 'PSR (P/S)', type: 'ratio', tip: '시가총액 ÷ 매출. 낮을수록 매출 대비 저평가' },
      { key: 'enterpriseValue', label: '기업가치 (EV)', type: 'cap' },
      { key: 'enterpriseToRevenue', label: 'EV/Sales', type: 'ratio' },
      { key: 'enterpriseToEbitda', label: 'EV/EBITDA', type: 'ratio' },
      { key: 'pFcf', label: 'P/FCF', type: 'ratio', tip: '시가총액 ÷ 자유현금흐름. 낮을수록 현금창출력 대비 저평가' },
      { key: 'pCash', label: 'P/Cash', type: 'ratio', tip: '시가총액 ÷ 보유 현금' }
    ]
  },
  {
    title: '수익성 · 현금흐름',
    fields: [
      { key: 'totalRevenue', label: '매출 (TTM)', type: 'cap' },
      { key: 'netIncomeToCommon', label: '순이익 (TTM)', type: 'cap' },
      { key: 'grossProfits', label: '매출총이익', type: 'cap' },
      { key: 'operatingCashflow', label: '영업현금흐름', type: 'cap' },
      { key: 'freeCashflow', label: '자유현금흐름 (FCF)', type: 'cap' },
      { key: 'totalCash', label: '보유 현금', type: 'cap' },
      { key: 'totalDebt', label: '총부채', type: 'cap' },
      { key: 'revenuePerShare', label: '주당매출 (SPS)', type: 'price' }
    ]
  },
  {
    title: '성장성',
    fields: [
      { key: 'revenueGrowth', label: '매출성장률 (YoY)', type: 'pctFraction' },
      { key: 'earningsGrowth', label: '순이익성장률 (YoY)', type: 'pctFraction' },
      { key: 'revenueQoQGrowth', label: '매출성장률 (QoQ)', type: 'pctFraction', tip: '직전 분기 대비' },
      { key: 'netIncomeQoQGrowth', label: '순이익성장률 (QoQ)', type: 'pctFraction', tip: '직전 분기 대비' },
      { key: 'epsQoQGrowth', label: 'EPS성장률 (QoQ)', type: 'pctFraction', tip: '직전 분기 대비' }
    ]
  },
  {
    title: '기술적 지표',
    fields: [
      { key: 'rsi14', label: 'RSI (14)', type: 'rsi' },
      { key: 'beta', label: '베타', type: 'ratio', tip: '시장(지수) 대비 변동성. 1보다 크면 시장보다 더 크게 움직임' },
      { key: 'sma20Gap', label: 'SMA20 대비', type: 'pctRaw', tip: '20일 이동평균선 대비 현재가 괴리율' },
      { key: 'sma50Gap', label: 'SMA50 대비', type: 'pctRaw', tip: '50일 이동평균선 대비 현재가 괴리율' },
      { key: 'sma200Gap', label: 'SMA200 대비', type: 'pctRaw', tip: '200일 이동평균선 대비 현재가 괴리율' },
      { key: 'atr14', label: 'ATR (14)', type: 'price', tip: '최근 14일 평균 일중 변동폭' },
      { key: 'volWeekly', label: '변동성 (단기, 연율화)', type: 'pctRawPlain', tip: '최근 약 2개월 일별 변동성을 연율화한 값' },
      { key: 'volMonthly', label: '변동성 (장기, 연율화)', type: 'pctRawPlain', tip: '최근 약 1년 일별 변동성을 연율화한 값' }
    ]
  },
  {
    title: '퍼포먼스',
    fields: [
      { key: 'ret1w', label: '1주 수익률', type: 'pctRaw' },
      { key: 'ret1m', label: '1개월 수익률', type: 'pctRaw' },
      { key: 'ret3m', label: '3개월 수익률', type: 'pctRaw' },
      { key: 'ret6m', label: '6개월 수익률', type: 'pctRaw' },
      { key: 'retYtd', label: 'YTD 수익률', type: 'pctRaw' },
      { key: 'ret1y', label: '1년 수익률', type: 'pctRaw' },
      { key: 'ret3y', label: '3년 수익률', type: 'pctRaw' },
      { key: 'ret5y', label: '5년 수익률', type: 'pctRaw' }
    ]
  },
  {
    title: '수급 · 소유구조',
    fields: [
      { key: 'institutionsPercentHeld', label: '기관 지분율', type: 'pctFractionPlain' },
      { key: 'insidersPercentHeld', label: '내부자 지분율', type: 'pctFractionPlain' },
      { key: 'netInsiderPurchasePercent', label: '내부자 순매수율', type: 'pctFraction', sub: 'netInsiderPurchasePeriod', tip: '최근 일정 기간 내부자 매수-매도 비율 (보유 주식 대비)' },
      { key: 'sharesOutstanding', label: '발행주식수', type: 'shares' },
      { key: 'floatShares', label: '유통주식수', type: 'shares' },
      { key: 'shortPercentOfFloat', label: '숏비율 (유통주식 대비)', type: 'pctFractionPlain' },
      { key: 'shortRatio', label: 'Short Ratio', type: 'days', tip: '평균 거래량 기준, 숏 포지션을 청산하는 데 걸리는 일수' },
      { key: 'shortChange', label: 'Short 변화 (전월대비)', type: 'pctFraction',
        compute: function (d) {
          if (d.sharesShort == null || d.sharesShortPriorMonth == null || !d.sharesShortPriorMonth) return null;
          return (d.sharesShort - d.sharesShortPriorMonth) / d.sharesShortPriorMonth;
        }
      }
    ]
  },
  {
    title: '배당',
    fields: [
      { key: 'trailingAnnualDividendRate', label: '연간 배당금 (주당)', type: 'price' },
      { key: 'payoutRatio', label: '배당성향', type: 'pctFractionPlain' },
      { key: 'fiveYearAvgDividendYield', label: '5년 평균 배당수익률', type: 'pctRawPlain' }
    ]
  }
];

// RSI(0~100) → 배지 정보 { label, cls }
function rsiTier(v) {
  if (v >= 70) return { label: '과매수', cls: 'fc-down' };
  if (v <= 30) return { label: '과매도', cls: 'fc-up' };
  return { label: '중립', cls: '' };
}

// 주식수 약식 표기 (예: 24,221,000,000 → 24.22B)
function fmtShares(n) {
  if (n == null || isNaN(n)) return '-';
  if (n >= 1e9) return (n / 1e9).toFixed(2) + 'B';
  if (n >= 1e6) return (n / 1e6).toFixed(2) + 'M';
  if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K';
  return String(n);
}

// 필드 정의 + 데이터(d)를 받아 표시용 { text, cls, sub } 산출
function formatDetailField(field, d, sh) {
  var v = field.compute ? field.compute(d) : d[field.key];
  if (v == null || (typeof v === 'number' && isNaN(v))) return { text: '-', cls: '', sub: null };

  switch (field.type) {
    case 'price':
      return { text: sh.fmtPrice(v, d.currency), cls: '' };
    case 'cap':
      return { text: sh.fmtCap(v, d.currency), cls: '' };
    case 'shares':
      return { text: fmtShares(v), cls: '' };
    case 'ratio':
      return { text: v.toFixed(2), cls: '' };
    case 'ratioX':
      return { text: v.toFixed(2) + '배', cls: '' };
    case 'days':
      return { text: v.toFixed(1) + '일', cls: '' };
    case 'pctFraction':
      return { text: (v >= 0 ? '+' : '') + sh.fmtPct(v), cls: v >= 0 ? 'fc-up' : 'fc-down' };
    case 'pctFractionPlain':
      return { text: sh.fmtPct(v), cls: '' };
    case 'pctRaw':
      return { text: (v >= 0 ? '+' : '') + v.toFixed(2) + '%', cls: v >= 0 ? 'fc-up' : 'fc-down' };
    case 'pctRawPlain':
      return { text: v.toFixed(2) + '%', cls: '' };
    case 'rsi':
      var tier = rsiTier(v);
      return { text: v.toFixed(0), cls: tier.cls, badge: tier.label };
    default:
      return { text: String(v), cls: '' };
  }
}
