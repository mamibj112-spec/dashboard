import { jsonResponse } from './cors.js';

const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36';
const SAMSUNG_SYMBOL = '005930.KS';
const MODULES = 'price,summaryDetail,defaultKeyStatistics,financialData,assetProfile,calendarEvents,earningsTrend,earningsHistory,incomeStatementHistoryQuarterly,majorHoldersBreakdown,netSharePurchaseActivity';

let crumbCache = null; // { cookie, crumb, expiresAt }

async function getCrumb() {
  if (crumbCache && crumbCache.expiresAt > Date.now()) return crumbCache;

  const cookieRes = await fetch('https://fc.yahoo.com', { headers: { 'User-Agent': UA } });
  const cookies = [];
  for (const [key, value] of cookieRes.headers) {
    if (key.toLowerCase() === 'set-cookie') cookies.push(value.split(';')[0]);
  }
  const cookie = cookies.join('; ');

  const crumbRes = await fetch('https://query1.finance.yahoo.com/v1/test/getcrumb', {
    headers: { 'User-Agent': UA, 'Cookie': cookie },
  });
  const crumb = (await crumbRes.text()).trim();

  crumbCache = { cookie, crumb, expiresAt: Date.now() + 1000 * 60 * 30 };
  return crumbCache;
}

async function fetchQuoteSummary(yahooSymbol) {
  const { cookie, crumb } = await getCrumb();
  const url = `https://query2.finance.yahoo.com/v10/finance/quoteSummary/${encodeURIComponent(yahooSymbol)}?modules=${MODULES}&crumb=${encodeURIComponent(crumb)}`;
  const res = await fetch(url, { headers: { 'User-Agent': UA, 'Cookie': cookie } });
  if (!res.ok) return null;
  const data = await res.json();
  return data?.quoteSummary?.result?.[0] || null;
}

// Yahoo 차트 API (인증 불필요) — IPO일(firstTradeDate)과 최근 배당이력 추출용
async function fetchChartMeta(yahooSymbol) {
  const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(yahooSymbol)}?interval=1mo&range=2y&events=div`;
  const res = await fetch(url, { headers: { 'User-Agent': UA } });
  if (!res.ok) return null;
  const data = await res.json();
  return data?.chart?.result?.[0] || null;
}

// Yahoo 차트 API (인증 불필요) — 기술적 지표/기간별 수익률 계산용 일별 시세 히스토리(최대 10년)
async function fetchPriceHistory(yahooSymbol) {
  const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(yahooSymbol)}?interval=1d&range=10y`;
  const res = await fetch(url, { headers: { 'User-Agent': UA } });
  if (!res.ok) return null;
  const data = await res.json();
  const result = data?.chart?.result?.[0];
  if (!result) return null;

  const ts = result.timestamp || [];
  const q = result.indicators?.quote?.[0] || {};
  const closes = [], highs = [], lows = [], dates = [];
  for (let i = 0; i < ts.length; i++) {
    const c = q.close?.[i], h = q.high?.[i], l = q.low?.[i];
    if (c == null || h == null || l == null) continue;
    closes.push(c);
    highs.push(h);
    lows.push(l);
    dates.push(ts[i]);
  }
  return { closes, highs, lows, dates };
}

async function fetchFxRate(pair) {
  const { cookie, crumb } = await getCrumb();
  const url = `https://query2.finance.yahoo.com/v10/finance/quoteSummary/${encodeURIComponent(pair)}?modules=price&crumb=${encodeURIComponent(crumb)}`;
  const res = await fetch(url, { headers: { 'User-Agent': UA, 'Cookie': cookie } });
  if (!res.ok) return null;
  const data = await res.json();
  return num(data?.quoteSummary?.result?.[0]?.price || {}, 'regularMarketPrice');
}

function tvToYahooCandidates(tvSymbol) {
  const parts = tvSymbol.split(':');
  const exchange = parts[0];
  const ticker = parts[1] || parts[0];
  if (exchange === 'KRX') {
    return [`${ticker}.KS`, `${ticker}.KQ`];
  }
  return [ticker];
}

function num(obj, key) {
  const v = obj?.[key];
  return typeof v?.raw === 'number' ? v.raw : null;
}

// earningsTrend.trend 배열에서 특정 기간(period: '+1y' 등)의 성장률 추출
function earningsTrendGrowth(et, period) {
  const trend = et?.trend;
  if (!Array.isArray(trend)) return null;
  const entry = trend.find((t) => t.period === period);
  return entry ? num(entry, 'growth') : null;
}

// 5년 EPS 연평균 성장률 추정치: Yahoo가 earningsTrend에 '+5y'를 더 이상 제공하지 않아,
// PEG = PER(Forward) / 5년 성장률(%) 관계를 역산해 근사
function estimateEpsGrowth5Y(forwardPE, pegRatio) {
  if (forwardPE == null || pegRatio == null || pegRatio <= 0) return null;
  return (forwardPE / pegRatio) / 100;
}

// earningsHistory.history → 최근 4개 분기 EPS 실적/추정치/서프라이즈%
function extractEarningsHistory(eh) {
  const history = eh?.history;
  if (!Array.isArray(history)) return [];
  return history
    .map((h) => ({
      date: h.quarter?.fmt || null,
      epsActual: num(h, 'epsActual'),
      epsEstimate: num(h, 'epsEstimate'),
      surprisePercent: num(h, 'surprisePercent'),
    }))
    .filter((h) => h.date);
}

// incomeStatementHistoryQuarterly.incomeStatementHistory → 최근 분기순 매출/순이익 (최신순)
function extractIncomeHistoryQuarterly(ih) {
  const history = ih?.incomeStatementHistory;
  if (!Array.isArray(history)) return [];
  return history
    .map((h) => ({
      date: h.endDate?.fmt || null,
      endRaw: h.endDate?.raw || 0,
      totalRevenue: num(h, 'totalRevenue'),
      netIncome: num(h, 'netIncome'),
    }))
    .filter((h) => h.date)
    .sort((a, b) => b.endRaw - a.endRaw);
}

// 직전 분기 대비(QoQ) 증감률
function qoqGrowth(history, key) {
  if (!Array.isArray(history) || history.length < 2) return null;
  const latest = history[0][key];
  const prev = history[1][key];
  if (latest == null || prev == null || prev === 0) return null;
  return (latest - prev) / Math.abs(prev);
}

// earningsHistory(오래된→최신순)에서 최근 분기 EPS의 직전 분기 대비(QoQ) 증감률
function epsQoQGrowth(epsHistory) {
  if (!Array.isArray(epsHistory) || epsHistory.length < 2) return null;
  const latest = epsHistory[epsHistory.length - 1].epsActual;
  const prev = epsHistory[epsHistory.length - 2].epsActual;
  if (latest == null || prev == null || prev === 0) return null;
  return (latest - prev) / Math.abs(prev);
}

// ── 기술적 지표 / 기간별 수익률 (generate.py의 calculate_rsi / sma_gap / ret / atr / vol_* 알고리즘 포팅) ──

// RSI(14) — Wilder의 평활 이동평균 방식
function calcRsi(closes, period = 14) {
  if (closes.length < period + 1) return 50;
  const deltas = [];
  for (let i = 1; i < closes.length; i++) deltas.push(closes[i] - closes[i - 1]);
  const gains = deltas.map((x) => (x > 0 ? x : 0));
  const losses = deltas.map((x) => (x < 0 ? -x : 0));

  let avgGain = gains.slice(0, period).reduce((a, b) => a + b, 0) / period;
  let avgLoss = losses.slice(0, period).reduce((a, b) => a + b, 0) / period;

  for (let i = period; i < deltas.length; i++) {
    avgGain = (avgGain * (period - 1) + gains[i]) / period;
    avgLoss = (avgLoss * (period - 1) + losses[i]) / period;
  }

  if (avgLoss === 0) return 100;
  const rs = avgGain / avgLoss;
  return Math.floor(100 - 100 / (1 + rs));
}

// 현재가의 SMA(n) 대비 괴리율(%)
function smaGap(closes, n) {
  if (closes.length < n) return null;
  const slice = closes.slice(-n);
  const avg = slice.reduce((a, b) => a + b, 0) / n;
  if (!avg) return null;
  const curr = closes[closes.length - 1];
  return (curr - avg) / avg * 100;
}

// N거래일 전 종가 대비 수익률(%)
function periodReturn(closes, days) {
  if (closes.length < days + 1) return null;
  const curr = closes[closes.length - 1];
  const old = closes[closes.length - 1 - days];
  if (!old) return null;
  return (curr - old) / old * 100;
}

// 연초(YTD) 첫 거래일 종가 대비 수익률(%)
function ytdReturn(closes, dates) {
  if (!closes.length) return null;
  const curr = closes[closes.length - 1];
  const lastYear = new Date(dates[dates.length - 1] * 1000).getUTCFullYear();
  const yearStart = Date.UTC(lastYear, 0, 1) / 1000;
  for (let i = 0; i < dates.length; i++) {
    if (dates[i] >= yearStart) {
      const base = closes[i];
      return base ? (curr - base) / base * 100 : null;
    }
  }
  return null;
}

// ATR(14) — True Range의 단순 평균
function calcAtr(highs, lows, closes, period = 14) {
  const n = closes.length;
  const maxI = Math.min(period + 1, n);
  if (maxI < 2) return null;
  const trs = [];
  for (let i = 1; i < maxI; i++) {
    const h = highs[n - i], l = lows[n - i], pc = closes[n - i - 1];
    trs.push(Math.max(h - l, Math.abs(h - pc), Math.abs(l - pc)));
  }
  return trs.reduce((a, b) => a + b, 0) / trs.length;
}

// 일별 수익률 표준편차 기반 연율화 변동성(%) — window=52(약 1개월) / 252(약 1년)
function annualizedVol(closes, window) {
  const rets = [];
  for (let i = 1; i < closes.length; i++) {
    if (closes[i - 1]) rets.push((closes[i] - closes[i - 1]) / closes[i - 1]);
  }
  const tail = rets.slice(-window);
  if (tail.length < 2) return null;
  const mean = tail.reduce((a, b) => a + b, 0) / tail.length;
  const variance = tail.reduce((a, b) => a + (b - mean) * (b - mean), 0) / (tail.length - 1);
  return Math.sqrt(variance) * Math.sqrt(window) * 100;
}

// 일별 시세 히스토리 → 기술적 지표 + 기간별 수익률 묶음
function buildTechnicals(hist) {
  if (!hist || hist.closes.length < 30) return {};
  const { closes, highs, lows, dates } = hist;
  return {
    rsi14: calcRsi(closes, 14),
    sma20Gap: smaGap(closes, 20),
    sma50Gap: smaGap(closes, 50),
    sma200Gap: smaGap(closes, 200),
    atr14: calcAtr(highs, lows, closes, 14),
    volWeekly: annualizedVol(closes, 52),
    volMonthly: annualizedVol(closes, 252),
    ret1w: periodReturn(closes, 5),
    ret1m: periodReturn(closes, 21),
    ret3m: periodReturn(closes, 63),
    ret6m: periodReturn(closes, 126),
    retYtd: ytdReturn(closes, dates),
    ret1y: periodReturn(closes, 252),
    ret3y: periodReturn(closes, 756),
    ret5y: periodReturn(closes, 1260),
  };
}

const ROIC_TAX_RATE = 0.21;

// ROIC ≈ 영업이익 × (1 - 세율) / (총부채 + 자기자본 - 현금성자산)
// Yahoo가 ROIC를 직접 제공하지 않아 financialData/defaultKeyStatistics 항목으로 근사 계산
function calcRoic(fd, ks, sd, price) {
  const operatingMargins = num(fd, 'operatingMargins');
  const totalRevenue = num(fd, 'totalRevenue');
  const totalDebt = num(fd, 'totalDebt');
  const totalCash = num(fd, 'totalCash');
  const priceToBook = num(ks, 'priceToBook');
  const marketCap = num(sd, 'marketCap') ?? num(price, 'marketCap');

  if (operatingMargins == null || totalRevenue == null || totalDebt == null ||
      totalCash == null || !marketCap) {
    return null;
  }

  const ebit = totalRevenue * operatingMargins;
  const nopat = ebit * (1 - ROIC_TAX_RATE);
  // priceToBook이 없는 종목(일부 한국 종목)은 시가총액을 자기자본 근사값으로 사용
  const equity = priceToBook ? marketCap / priceToBook : marketCap;
  const investedCapital = totalDebt + equity - totalCash;

  if (investedCapital <= 0) return null;
  return nopat / investedCapital;
}

function buildResult(raw, yahooSymbol) {
  const price = raw.price || {};
  const sd = raw.summaryDetail || {};
  const ks = raw.defaultKeyStatistics || {};
  const fd = raw.financialData || {};
  const ap = raw.assetProfile || {};
  const ce = raw.calendarEvents || {};
  const et = raw.earningsTrend || {};
  const eh = raw.earningsHistory || {};
  const mh = raw.majorHoldersBreakdown || {};
  const nsp = raw.netSharePurchaseActivity || {};

  const earningsDate = ce.earnings?.earningsDate?.[0]?.fmt || null;
  const nextEarnings = earningsDate ? {
    date: earningsDate,
    epsEstimate: num(ce.earnings, 'earningsAverage'),
    revenueEstimate: num(ce.earnings, 'revenueAverage'),
  } : null;
  const forwardPE = num(sd, 'forwardPE');
  const pegRatio = num(ks, 'pegRatio');
  const earningsHistory = extractEarningsHistory(eh);
  const incomeHistoryQ = extractIncomeHistoryQuarterly(raw.incomeStatementHistoryQuarterly);

  const marketCap = num(sd, 'marketCap') ?? num(price, 'marketCap');
  const freeCashflow = num(fd, 'freeCashflow');
  const totalCash = num(fd, 'totalCash');
  const regularMarketVolume = num(sd, 'regularMarketVolume');
  const averageVolume = num(sd, 'averageVolume');

  return {
    symbol: yahooSymbol,
    name: price.longName || price.shortName || yahooSymbol,
    currency: price.currency || null,
    price: num(price, 'regularMarketPrice'),
    marketCap: num(sd, 'marketCap') ?? num(price, 'marketCap'),
    trailingPE: num(sd, 'trailingPE'),
    forwardPE,
    dividendYield: num(sd, 'dividendYield'),
    beta: num(sd, 'beta'),
    fiftyTwoWeekHigh: num(sd, 'fiftyTwoWeekHigh'),
    fiftyTwoWeekLow: num(sd, 'fiftyTwoWeekLow'),
    eps: num(ks, 'trailingEps'),
    forwardEps: num(ks, 'forwardEps'),
    pegRatio,
    priceToBook: num(ks, 'priceToBook'),
    targetMeanPrice: num(fd, 'targetMeanPrice'),
    targetHighPrice: num(fd, 'targetHighPrice'),
    targetLowPrice: num(fd, 'targetLowPrice'),
    recommendationKey: fd.recommendationKey || null,
    numberOfAnalystOpinions: num(fd, 'numberOfAnalystOpinions'),
    returnOnEquity: num(fd, 'returnOnEquity'),
    returnOnAssets: num(fd, 'returnOnAssets'),
    debtToEquity: num(fd, 'debtToEquity'),
    currentRatio: num(fd, 'currentRatio'),
    quickRatio: num(fd, 'quickRatio'),
    grossMargins: num(fd, 'grossMargins'),
    operatingMargins: num(fd, 'operatingMargins'),
    profitMargins: num(fd, 'profitMargins'),
    revenueGrowth: num(fd, 'revenueGrowth'),
    earningsGrowth: num(fd, 'earningsGrowth'),
    epsGrowthNextYear: earningsTrendGrowth(et, '+1y'),
    epsGrowthNext5Y: estimateEpsGrowth5Y(forwardPE, pegRatio),
    roic: calcRoic(fd, ks, sd, price),
    sector: ap.sector || null,
    industry: ap.industry || null,
    longBusinessSummary: ap.longBusinessSummary || null,
    fullTimeEmployees: ap.fullTimeEmployees || null,
    country: ap.country || null,
    earningsDate,
    nextEarnings,
    earningsHistory,
    exchange: price.exchange || null,
    exchangeName: price.exchangeName || null,

    // 거래정보
    open: num(sd, 'open'),
    dayHigh: num(sd, 'dayHigh'),
    dayLow: num(sd, 'dayLow'),
    regularMarketPreviousClose: num(sd, 'regularMarketPreviousClose'),
    regularMarketVolume,
    averageVolume,
    averageVolume10days: num(sd, 'averageVolume10days'),
    relativeVolume: (regularMarketVolume != null && averageVolume) ? regularMarketVolume / averageVolume : null,
    fiftyTwoWeekChange: num(ks, '52WeekChange'),

    // 밸류에이션
    priceToSales: num(sd, 'priceToSalesTrailing12Months'),
    enterpriseValue: num(ks, 'enterpriseValue'),
    enterpriseToRevenue: num(ks, 'enterpriseToRevenue'),
    enterpriseToEbitda: num(ks, 'enterpriseToEbitda'),
    pFcf: (marketCap != null && freeCashflow) ? marketCap / freeCashflow : null,
    pCash: (marketCap != null && totalCash) ? marketCap / totalCash : null,

    // 수익성 / 현금흐름
    totalRevenue: num(fd, 'totalRevenue'),
    netIncomeToCommon: num(ks, 'netIncomeToCommon'),
    grossProfits: num(fd, 'grossProfits'),
    operatingCashflow: num(fd, 'operatingCashflow'),
    freeCashflow,
    totalCash,
    totalDebt: num(fd, 'totalDebt'),
    revenuePerShare: num(fd, 'revenuePerShare'),

    // 성장성 (직전 분기 대비)
    revenueQoQGrowth: qoqGrowth(incomeHistoryQ, 'totalRevenue'),
    netIncomeQoQGrowth: qoqGrowth(incomeHistoryQ, 'netIncome'),
    epsQoQGrowth: epsQoQGrowth(earningsHistory),

    // 수급 / 소유구조
    sharesOutstanding: num(ks, 'sharesOutstanding'),
    floatShares: num(ks, 'floatShares'),
    institutionsPercentHeld: num(mh, 'institutionsPercentHeld') ?? num(ks, 'heldPercentInstitutions'),
    insidersPercentHeld: num(mh, 'insidersPercentHeld') ?? num(ks, 'heldPercentInsiders'),
    netInsiderPurchasePercent: num(nsp, 'netPercentInsiderShares'),
    netInsiderPurchasePeriod: nsp.period || null,
    sharesShort: num(ks, 'sharesShort'),
    sharesShortPriorMonth: num(ks, 'sharesShortPriorMonth'),
    shortRatio: num(ks, 'shortRatio'),
    shortPercentOfFloat: num(ks, 'shortPercentOfFloat'),

    // 배당
    payoutRatio: num(sd, 'payoutRatio'),
    trailingAnnualDividendRate: num(sd, 'trailingAnnualDividendRate'),
    fiveYearAvgDividendYield: num(sd, 'fiveYearAvgDividendYield'),
  };
}

export async function handleFinance(request) {
  const url = new URL(request.url);
  const tvSymbol = url.searchParams.get('symbol');
  if (!tvSymbol) {
    return jsonResponse({ error: 'symbol parameter required' }, 400);
  }

  const candidates = tvToYahooCandidates(tvSymbol);
  let result = null;
  let usedSymbol = null;
  for (const sym of candidates) {
    const r = await fetchQuoteSummary(sym);
    if (r && num(r.summaryDetail || {}, 'previousClose') !== null) {
      result = r;
      usedSymbol = sym;
      break;
    }
  }

  if (!result) {
    return jsonResponse({ error: 'No data found for symbol' }, 404);
  }

  const data = buildResult(result, usedSymbol);

  // KRW per 1 USD 환율 — KRW 환산 표시 및 통화가 다른 종목 간 시가총액 비교에 사용
  const fxRate = await fetchFxRate('KRW=X');
  if (fxRate) {
    if (data.currency !== 'KRW' && data.price != null) data.priceKRW = data.price * fxRate;
    if (data.marketCap != null) {
      data.marketCapUSD = data.currency === 'KRW' ? data.marketCap / fxRate : data.marketCap;
    }
  }

  // 삼성전자 시가총액 비교 (대상 종목이 삼성전자 자신이면 생략)
  if (!/^005930\.(KS|KQ)$/i.test(usedSymbol)) {
    const samsung = await fetchQuoteSummary(SAMSUNG_SYMBOL);
    let samsungCap = samsung ? num(samsung.summaryDetail || {}, 'marketCap') : null;
    if (samsungCap !== null && fxRate) {
      samsungCap = samsungCap / fxRate; // KRW → USD
      data.samsungMarketCap = samsungCap;
      if (data.marketCapUSD != null) data.marketCapVsSamsung = data.marketCapUSD / samsungCap;
    }
  }

  // IPO일 / 최근 배당이력 (Yahoo 차트 API, 인증 불필요)
  const chartMeta = await fetchChartMeta(usedSymbol);
  if (chartMeta?.meta?.firstTradeDate) {
    data.firstTradeDate = new Date(chartMeta.meta.firstTradeDate * 1000).toISOString().slice(0, 10);
  }
  if (chartMeta?.events?.dividends) {
    data.recentDividends = Object.values(chartMeta.events.dividends)
      .sort((a, b) => b.date - a.date)
      .slice(0, 2)
      .map((dv) => ({ date: new Date(dv.date * 1000).toISOString().slice(0, 10), amount: dv.amount }));
  }

  // 일별 시세 히스토리 기반 기술적 지표 / 기간별 수익률 (RSI, SMA 괴리율, ATR, 변동성, 1주~5년 수익률)
  const hist = await fetchPriceHistory(usedSymbol);
  Object.assign(data, buildTechnicals(hist));

  return jsonResponse(data);
}
