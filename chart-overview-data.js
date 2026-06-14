// "어떤 회사인가요?" 섹션 — 글로벌 시총 레퍼런스 테이블 및 정적 정보
// 시총 값은 근사치(조 달러 단위)이며, 주기적으로 갱신이 필요합니다.
var MARKETCAP_REFERENCE = [
  { name: '엔비디아',       tv: 'NASDAQ:NVDA',  cap: 4.97 },
  { name: '애플',          tv: 'NASDAQ:AAPL',  cap: 3.5 },
  { name: '마이크로소프트',  tv: 'NASDAQ:MSFT',  cap: 3.4 },
  { name: '알파벳',         tv: 'NASDAQ:GOOGL', cap: 2.4 },
  { name: '아마존',         tv: 'NASDAQ:AMZN',  cap: 2.3 },
  { name: '사우디 아람코',   tv: null,           cap: 1.8 },
  { name: '메타',           tv: 'NASDAQ:META',  cap: 1.7 },
  { name: '브로드컴',       tv: 'NASDAQ:AVGO',  cap: 1.5 },
  { name: '삼성전자',       tv: 'KRX:005930',   cap: 1.4 },
  { name: 'TSMC',          tv: null,           cap: 1.3 },
  { name: '버크셔 해서웨이', tv: null,           cap: 1.0 },
  { name: '테슬라',         tv: 'NASDAQ:TSLA',  cap: 1.0 }
];

// 추적 종목의 주요 지수 편입 현황 (근사치, 정적 테이블)
var INDEX_MEMBERSHIP = {
  'NASDAQ:NVDA':  ['S&P 500', '나스닥 100', '다우 30'],
  'NASDAQ:AAPL':  ['S&P 500', '나스닥 100', '다우 30'],
  'NASDAQ:MSFT':  ['S&P 500', '나스닥 100', '다우 30'],
  'NASDAQ:GOOGL': ['S&P 500', '나스닥 100'],
  'NASDAQ:AMZN':  ['S&P 500', '나스닥 100', '다우 30'],
  'NASDAQ:META':  ['S&P 500', '나스닥 100'],
  'NASDAQ:TSLA':  ['S&P 500', '나스닥 100'],
  'NYSE:UNH':     ['S&P 500', '다우 30'],
  'NASDAQ:AVGO':  ['S&P 500', '나스닥 100'],
  'NYSE:ANET':    ['S&P 500'],
  'NYSE:WMT':     ['S&P 500', '다우 30'],
  'NASDAQ:ARM':   ['나스닥 100'],
  'NYSE:PFE':     ['S&P 500'],
  'NASDAQ:PANW':  ['S&P 500', '나스닥 100'],
  'NASDAQ:INTC':  ['S&P 500', '나스닥 100'],
  'KRX:005930':   ['KOSPI 200']
};

// 시가총액 규모 분류 (일반적인 대형주/중형주/소형주 기준, 단위: USD)
function marketCapScaleLabel(capUsd) {
  if (capUsd == null) return null;
  if (capUsd >= 2e11) return '초대형주';
  if (capUsd >= 1e10) return '대형주';
  if (capUsd >= 2e9) return '중형주';
  return '소형주';
}

// MARKETCAP_REFERENCE 기준 글로벌 시총 순위 추정 (레퍼런스 최솟값 미만이면 null)
function estimateMarketCapRank(capUsd, selfTv) {
  if (capUsd == null) return null;
  var capT = capUsd / 1e12;
  var smallest = MARKETCAP_REFERENCE[MARKETCAP_REFERENCE.length - 1].cap;
  if (capT < smallest * 0.9) return null;
  var rank = 1;
  MARKETCAP_REFERENCE.forEach(function (r) {
    if (r.tv !== selfTv && r.cap > capT) rank++;
  });
  return rank;
}

// 'YYYY-MM-DD' → 'YYYY년 M월 D일'
function formatDateKo(dateStr) {
  if (!dateStr) return null;
  var p = dateStr.split('-');
  return p[0] + '년 ' + parseInt(p[1], 10) + '월 ' + parseInt(p[2], 10) + '일';
}

// 'YYYY-MM-DD' → 'YYYY.MM.DD' (좁은 카드에서 줄바꿈 방지)
function formatDateCompact(dateStr) {
  if (!dateStr) return null;
  return dateStr.replace(/-/g, '.');
}

// 오늘 날짜(KST) 기준 D-day (목표일 - 오늘, 일 단위)
function daysUntil(dateStr) {
  if (!dateStr) return null;
  var target = new Date(dateStr + 'T00:00:00+09:00');
  var now = new Date();
  var todayKst = new Date(now.getTime() + (9 * 60 + now.getTimezoneOffset()) * 60000);
  todayKst.setHours(0, 0, 0, 0);
  return Math.round((target - todayKst) / 86400000);
}
