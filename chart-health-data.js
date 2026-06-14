// 수익성/재무건전성 평가용 업종 중앙값(근사치) 및 평가 기준 데이터
// 실시간 동종업계 데이터가 아닌, 일반적으로 알려진 업종별 평균 수준의 고정 참고값입니다.
var HEALTH_BENCHMARKS = {
  'Technology':            { operatingMargins:0.12, profitMargins:0.08, grossMargins:0.50, returnOnEquity:0.15, returnOnAssets:0.06, roic:0.10, debtToEquity:0.50, currentRatio:2.0, quickRatio:1.6 },
  'Healthcare':            { operatingMargins:0.10, profitMargins:0.06, grossMargins:0.55, returnOnEquity:0.12, returnOnAssets:0.05, roic:0.08, debtToEquity:0.60, currentRatio:1.8, quickRatio:1.4 },
  'Financial Services':    { operatingMargins:0.30, profitMargins:0.20, grossMargins:0.55, returnOnEquity:0.11, returnOnAssets:0.012, roic:0.07, debtToEquity:1.5, currentRatio:1.1, quickRatio:1.0 },
  'Consumer Cyclical':      { operatingMargins:0.08, profitMargins:0.05, grossMargins:0.32, returnOnEquity:0.15, returnOnAssets:0.05, roic:0.09, debtToEquity:0.80, currentRatio:1.3, quickRatio:0.9 },
  'Consumer Defensive':     { operatingMargins:0.08, profitMargins:0.05, grossMargins:0.30, returnOnEquity:0.18, returnOnAssets:0.06, roic:0.10, debtToEquity:0.90, currentRatio:1.0, quickRatio:0.6 },
  'Communication Services': { operatingMargins:0.15, profitMargins:0.08, grossMargins:0.55, returnOnEquity:0.12, returnOnAssets:0.04, roic:0.07, debtToEquity:1.0, currentRatio:1.0, quickRatio:0.8 },
  'Industrials':            { operatingMargins:0.10, profitMargins:0.06, grossMargins:0.30, returnOnEquity:0.14, returnOnAssets:0.05, roic:0.09, debtToEquity:0.70, currentRatio:1.5, quickRatio:1.0 },
  'Energy':                 { operatingMargins:0.12, profitMargins:0.08, grossMargins:0.35, returnOnEquity:0.10, returnOnAssets:0.05, roic:0.08, debtToEquity:0.40, currentRatio:1.3, quickRatio:0.9 },
  'Utilities':              { operatingMargins:0.18, profitMargins:0.10, grossMargins:0.40, returnOnEquity:0.10, returnOnAssets:0.03, roic:0.05, debtToEquity:1.3, currentRatio:0.9, quickRatio:0.6 },
  'Real Estate':            { operatingMargins:0.30, profitMargins:0.20, grossMargins:0.50, returnOnEquity:0.08, returnOnAssets:0.03, roic:0.04, debtToEquity:1.0, currentRatio:1.0, quickRatio:0.9 },
  'Basic Materials':        { operatingMargins:0.10, profitMargins:0.06, grossMargins:0.25, returnOnEquity:0.10, returnOnAssets:0.05, roic:0.08, debtToEquity:0.60, currentRatio:1.6, quickRatio:1.0 },
  'default':                { operatingMargins:0.10, profitMargins:0.06, grossMargins:0.35, returnOnEquity:0.12, returnOnAssets:0.05, roic:0.08, debtToEquity:0.80, currentRatio:1.5, quickRatio:1.0 }
};

// 지표 정의: key, 그룹(profit/health), 라벨, 설명, 단위(pct/ratio), higherIsBetter,
// thresholds(주의/양호/우수 경계 - higherIsBetter=false면 [주의경계, 우수경계]는 작을수록 좋음), tierLabels, tip
var HEALTH_METRICS = [
  { key:'operatingMargins', group:'profit', label:'영업이익률', desc:'제품·서비스 팔아 남기는 순수 이익률 (높을수록 잘 벌음)', unit:'pct', higherIsBetter:true, thresholds:[0.10,0.20], tip:'일반적으로 10% 이상이면 양호, 20% 이상이면 우수' },
  { key:'profitMargins',    group:'profit', label:'순이익률',   desc:'세금·이자까지 다 빼고 최종적으로 남는 돈의 비율', unit:'pct', higherIsBetter:true, thresholds:[0.08,0.15], tip:'일반적으로 8% 이상이면 양호, 15% 이상이면 우수' },
  { key:'grossMargins',     group:'profit', label:'매출총이익률', desc:'원재료·생산비를 뺀 이익률 (제품 자체 경쟁력)', unit:'pct', higherIsBetter:true, thresholds:[0.20,0.40], tip:'업종별 편차가 큼 (제조업 30%, IT·소프트웨어는 50% 이상이면 우수)' },
  { key:'returnOnEquity',   group:'profit', label:'ROE',        desc:'주주 돈으로 1년에 얼마나 벌어주는지', unit:'pct', higherIsBetter:true, thresholds:[0.08,0.15], tip:'일반적으로 15% 이상이면 우수 (단, 부채 레버리지 효과 주의)' },
  { key:'returnOnAssets',   group:'profit', label:'ROA',        desc:'회사가 가진 자산 대비 한 해 수익 비율', unit:'pct', higherIsBetter:true, thresholds:[0.05,0.10], tip:'일반적으로 5% 이상이면 양호, 10% 이상이면 우수' },
  { key:'roic',             group:'profit', label:'ROIC',       desc:'사업에 투입한 돈 대비 얼마나 수익 내는지', unit:'pct', higherIsBetter:true, thresholds:[0.08,0.15], tip:'자본비용(보통 8~10%)보다 높으면 가치 창출, 15% 이상이면 우수' },
  { key:'debtToEquity', group:'health', label:'부채비율 D/E', desc:'자본 대비 빚의 비율 (낮을수록 건전)', unit:'ratio', higherIsBetter:false, thresholds:[1.5,0.5], tierLabels:['주의','적정','부채양호'], tip:'일반적으로 1.0 이하면 건전, 1.5까지는 무난 (금융·유틸리티·리츠는 구조적으로 높음)' },
  { key:'currentRatio', group:'health', label:'유동비율', desc:'1년 내 갚을 돈 대비 현금성 자산 여유', unit:'ratio', higherIsBetter:true, thresholds:[1.0,1.5], tip:'1.5~3.0 적정, 1.0 미만이면 단기 유동성 주의' },
  { key:'quickRatio',   group:'health', label:'당좌비율', desc:'재고를 제외한 즉시 현금화 가능 자산 비율', unit:'ratio', higherIsBetter:true, thresholds:[0.5,1.0], tip:'1.0 이상이면 안전, 0.5 미만이면 주의' }
];

// 절대 기준(thresholds) 대비 0(주의)/1(양호)/2(우수) 단계 판정
function healthTier(value, thresholds, higherIsBetter) {
  if (value == null) return null;
  if (higherIsBetter) {
    if (value >= thresholds[1]) return 2;
    if (value >= thresholds[0]) return 1;
    return 0;
  }
  if (value <= thresholds[1]) return 2;
  if (value <= thresholds[0]) return 1;
  return 0;
}

// 업종 중앙값 대비 상대적 위치(대략적인 백분위 근사값) 산출
function healthPosition(value, median, higherIsBetter) {
  if (value == null || median == null || median === 0) return null;
  var ratio = higherIsBetter ? value / median : median / value;
  if (ratio >= 3)    return { pct: 95, label: '최상위권' };
  if (ratio >= 1.5)  return { pct: 85, label: '상위 10%' };
  if (ratio >= 1.2)  return { pct: 70, label: '상위 25%' };
  if (ratio >= 0.8)  return { pct: 50, label: '평균권' };
  if (ratio >= 0.5)  return { pct: 25, label: '평균 이하' };
  return { pct: 8, label: '하위권' };
}

// 수익성/재무건전성 그룹별 점수(0~1)를 바탕으로 종합 판정 산출
function healthVerdict(profRatio, healthRatio) {
  if (profRatio == null || healthRatio == null) {
    return { emoji:'ℹ️', cls:'neutral', title:'데이터 일부 부족', sub:'일부 지표를 확인할 수 없어 종합 판정이 제한적입니다' };
  }
  var profGood = profRatio >= 0.6;
  var healthGood = healthRatio >= 0.6;
  if (profGood && healthGood) {
    return { emoji:'💪', cls:'good', title:'튼튼한 기업 — 수익성·재무 모두 양호', sub:'돈도 잘 벌고 재무 건전성도 우수합니다' };
  }
  if (profGood && !healthGood) {
    return { emoji:'📈', cls:'warn', title:'수익성은 우수, 재무 부담은 주의', sub:'돈은 잘 벌지만 부채·유동성 지표 일부가 기준에 못 미칩니다' };
  }
  if (!profGood && healthGood) {
    return { emoji:'🛡️', cls:'warn', title:'재무는 안정적, 수익성 개선 필요', sub:'재무 건전성은 양호하나 수익성 지표가 다소 낮습니다' };
  }
  return { emoji:'⚠️', cls:'bad', title:'수익성·재무 모두 점검 필요', sub:'수익성과 재무 건전성 지표 전반이 기준에 못 미칩니다' };
}
