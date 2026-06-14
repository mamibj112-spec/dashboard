import { jsonResponse } from './cors.js';

const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36';
const SAMSUNG_SYMBOL = '005930.KS';
const MODULES = 'price,summaryDetail,defaultKeyStatistics,financialData,assetProfile,calendarEvents,earningsTrend';

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

  const earningsDate = ce.earnings?.earningsDate?.[0]?.fmt || null;
  const forwardPE = num(sd, 'forwardPE');
  const pegRatio = num(ks, 'pegRatio');

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

  // 삼성전자 시가총액 비교 (대상 종목이 삼성전자 자신이면 생략)
  if (!/^005930\.(KS|KQ)$/i.test(usedSymbol)) {
    const samsung = await fetchQuoteSummary(SAMSUNG_SYMBOL);
    let samsungCap = samsung ? num(samsung.summaryDetail || {}, 'marketCap') : null;
    if (samsungCap !== null && data.marketCap !== null) {
      if (data.currency && data.currency !== 'KRW') {
        const fxRate = await fetchFxRate('KRW=X'); // KRW per 1 USD
        if (fxRate) samsungCap = samsungCap / fxRate;
      }
      data.samsungMarketCap = samsungCap;
      data.marketCapVsSamsung = data.marketCap / samsungCap;
    }
  }

  return jsonResponse(data);
}
