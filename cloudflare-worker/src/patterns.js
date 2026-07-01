import { jsonResponse } from './cors.js';
import { fetchPriceHistory, tvToYahooCandidates } from './financeProxy.js';

const RELIABLE_MIN_N = 10;

function sma(closes, n, i) {
  if (i < n - 1) return null;
  let s = 0;
  for (let k = i - n + 1; k <= i; k++) s += closes[k];
  return s / n;
}

// RSI(14) 시계열 — Wilder 평활 이동평균
function rsiSeries(closes, period = 14) {
  const out = new Array(closes.length).fill(null);
  const gains = [], losses = [];
  for (let i = 1; i < closes.length; i++) {
    const d = closes[i] - closes[i - 1];
    gains.push(d > 0 ? d : 0);
    losses.push(d < 0 ? -d : 0);
  }
  let avgGain = gains.slice(0, period).reduce((a, b) => a + b, 0) / period;
  let avgLoss = losses.slice(0, period).reduce((a, b) => a + b, 0) / period;
  out[period] = rsiFromAvg(avgGain, avgLoss);
  for (let i = period; i < gains.length; i++) {
    avgGain = (avgGain * (period - 1) + gains[i]) / period;
    avgLoss = (avgLoss * (period - 1) + losses[i]) / period;
    out[i + 1] = rsiFromAvg(avgGain, avgLoss);
  }
  return out;
}
function rsiFromAvg(avgGain, avgLoss) {
  if (avgLoss === 0) return 100;
  const rs = avgGain / avgLoss;
  return 100 - 100 / (1 + rs);
}

function forwardReturn(closes, i, days) {
  if (i + days >= closes.length) return null;
  return (closes[i + days] - closes[i]) / closes[i] * 100;
}

function summarizeReturns(closes, indices, daysList) {
  const byHorizon = {};
  daysList.forEach((days) => {
    const rets = indices.map((i) => forwardReturn(closes, i, days)).filter((x) => x != null);
    if (!rets.length) {
      byHorizon[days + 'd'] = { n: 0, avgPct: null, winRatePct: null, reliable: false };
      return;
    }
    const avg = rets.reduce((a, b) => a + b, 0) / rets.length;
    const winRate = rets.filter((x) => x > 0).length / rets.length * 100;
    byHorizon[days + 'd'] = {
      n: rets.length,
      avgPct: Math.round(avg * 100) / 100,
      winRatePct: Math.round(winRate),
      reliable: rets.length >= RELIABLE_MIN_N,
    };
  });
  return byHorizon;
}

// ── 캔들스틱 패턴 (1~3봉) ──
const CANDLE_LOOKBACK = 15;

function candleBody(b) { return Math.abs(b.c - b.o); }
function candleRange(b) { return (b.h - b.l) || 1e-9; }
function upperWick(b) { return b.h - Math.max(b.o, b.c); }
function lowerWick(b) { return Math.min(b.o, b.c) - b.l; }
function isBull(b) { return b.c > b.o; }
function isBear(b) { return b.c < b.o; }

function classifySingle(b, avgRange) {
  const tags = [];
  const bd = candleBody(b), rg = candleRange(b);
  const uw = upperWick(b), lw = lowerWick(b);

  if (bd / rg < 0.1) tags.push('도지 (Doji)');
  if (bd / rg < 0.35 && lw > bd * 2 && uw < bd * 0.5) tags.push(isBull(b) ? '망치형 (Hammer)' : '행잉맨 (Hanging Man)');
  if (bd / rg < 0.35 && uw > bd * 2 && lw < bd * 0.5) tags.push(isBull(b) ? '역망치형 (Inverted Hammer)' : '유성형 (Shooting Star)');
  if (rg > avgRange * 1.5 && bd / rg > 0.6) tags.push(isBull(b) ? '장대양봉' : '장대음봉');
  return tags;
}

function engulfing(prev, curr) {
  if (isBear(prev) && isBull(curr) && curr.o <= prev.c && curr.c >= prev.o) return '상승장악형 (Bullish Engulfing)';
  if (isBull(prev) && isBear(curr) && curr.o >= prev.c && curr.c <= prev.o) return '하락장악형 (Bearish Engulfing)';
  return null;
}

function threeSoldiersOrCrows(b1, b2, b3) {
  if (isBull(b1) && isBull(b2) && isBull(b3) && b2.c > b1.c && b3.c > b2.c && b2.o > b1.o && b3.o > b2.o) return '적삼병 (Three White Soldiers)';
  if (isBear(b1) && isBear(b2) && isBear(b3) && b2.c < b1.c && b3.c < b2.c && b2.o < b1.o && b3.o < b2.o) return '흑삼병 (Three Black Crows)';
  return null;
}

function buildCandlePatterns(hist, dates) {
  const { opens, highs, lows, closes } = hist;
  if (!opens || opens.length < 20) return { recent: [], multiBar: [] };

  const bars = closes.map((c, i) => ({ date: dates[i], o: opens[i], h: highs[i], l: lows[i], c }));
  const tail = bars.slice(-CANDLE_LOOKBACK);
  const avgRangeBase = bars.slice(-20).reduce((a, b) => a + candleRange(b), 0) / Math.min(20, bars.length);

  const recent = tail.map((b) => ({
    date: b.date,
    dir: isBull(b) ? '양봉' : (isBear(b) ? '음봉' : '보합'),
    tags: classifySingle(b, avgRangeBase),
  })).filter((r) => r.tags.length > 0);

  const multiBar = [];
  const n = bars.length;
  for (let i = Math.max(1, n - CANDLE_LOOKBACK); i < n; i++) {
    const e = engulfing(bars[i - 1], bars[i]);
    if (e) multiBar.push({ from: bars[i - 1].date, to: bars[i].date, label: e });
  }
  for (let i = Math.max(2, n - CANDLE_LOOKBACK); i < n; i++) {
    const t = threeSoldiersOrCrows(bars[i - 2], bars[i - 1], bars[i]);
    if (t) multiBar.push({ from: bars[i - 2].date, to: bars[i].date, label: t });
  }

  return { recent, multiBar };
}

function buildPatterns(hist) {
  const { closes } = hist;
  const dates = hist.dates.map((ts) => new Date(ts * 1000).toISOString().slice(0, 10));
  const rsi = rsiSeries(closes, 14);
  const ma20 = closes.map((_, i) => sma(closes, 20, i));
  const ma60 = closes.map((_, i) => sma(closes, 60, i));

  const rsiOversold = [];
  const rsiOverbought = [];
  for (let i = 1; i < rsi.length; i++) {
    if (rsi[i] == null || rsi[i - 1] == null) continue;
    if (rsi[i] < 30 && rsi[i - 1] >= 30) rsiOversold.push(i);
    if (rsi[i] > 70 && rsi[i - 1] <= 70) rsiOverbought.push(i);
  }

  const goldenCross = [], deadCross = [];
  for (let i = 1; i < closes.length; i++) {
    if (ma20[i] == null || ma60[i] == null || ma20[i - 1] == null || ma60[i - 1] == null) continue;
    if (ma20[i] > ma60[i] && ma20[i - 1] <= ma60[i - 1]) goldenCross.push(i);
    if (ma20[i] < ma60[i] && ma20[i - 1] >= ma60[i - 1]) deadCross.push(i);
  }

  const pullback10 = [];
  for (let i = 1; i < closes.length; i++) {
    if (ma20[i] == null || ma20[i - 1] == null) continue;
    const gap = (closes[i] - ma20[i]) / ma20[i] * 100;
    const prevGap = (closes[i - 1] - ma20[i - 1]) / ma20[i - 1] * 100;
    if (gap < -10 && prevGap >= -10) pullback10.push(i);
  }

  const horizons = [5, 10, 20];
  const last = closes.length - 1;
  const currentRsi = rsi[last];
  const currentGap20 = ma20[last] != null ? (closes[last] - ma20[last]) / ma20[last] * 100 : null;
  const currentMaAlign = (ma20[last] != null && ma60[last] != null) ? (ma20[last] > ma60[last]) : null;

  const patterns = [
    { key: 'rsiOversold', label: 'RSI 과매도(30) 이탈', dates: rsiOversold.map((i) => dates[i]), forward: summarizeReturns(closes, rsiOversold, horizons), current: currentRsi != null && currentRsi < 30 },
    { key: 'rsiOverbought', label: 'RSI 과매수(70) 돌파', dates: rsiOverbought.map((i) => dates[i]), forward: summarizeReturns(closes, rsiOverbought, horizons), current: currentRsi != null && currentRsi > 70 },
    { key: 'goldenCross', label: '골든크로스 (20일선>60일선)', dates: goldenCross.map((i) => dates[i]), forward: summarizeReturns(closes, goldenCross, horizons), current: currentMaAlign === true },
    { key: 'deadCross', label: '데드크로스 (20일선<60일선)', dates: deadCross.map((i) => dates[i]), forward: summarizeReturns(closes, deadCross, horizons), current: currentMaAlign === false },
    { key: 'pullback10', label: '20일선 대비 -10% 눌림목', dates: pullback10.map((i) => dates[i]), forward: summarizeReturns(closes, pullback10, horizons), current: currentGap20 != null && currentGap20 < -10 },
  ];

  const buyHoldPct = closes.length > 1 ? Math.round((closes[closes.length - 1] - closes[0]) / closes[0] * 10000) / 100 : null;
  const candles = buildCandlePatterns(hist, dates);

  return {
    range: { from: dates[0], to: dates[dates.length - 1], bars: closes.length },
    buyHoldPct,
    current: { rsi: currentRsi != null ? Math.round(currentRsi) : null, gap20Pct: currentGap20 != null ? Math.round(currentGap20 * 100) / 100 : null },
    patterns,
    candles,
  };
}

export async function handlePatterns(request) {
  const url = new URL(request.url);
  const tvSymbol = url.searchParams.get('symbol');
  if (!tvSymbol) return jsonResponse({ error: 'symbol 파라미터가 필요합니다.' }, 400);

  const candidates = tvToYahooCandidates(tvSymbol);
  let hist = null;
  for (const sym of candidates) {
    const h = await fetchPriceHistory(sym);
    if (h && h.closes.length >= 60) { hist = h; break; }
  }

  if (!hist) return jsonResponse({ error: '시세 히스토리를 찾을 수 없습니다.' }, 404);

  const result = buildPatterns(hist);
  return jsonResponse({ symbol: tvSymbol, ...result });
}
