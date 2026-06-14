// "향후 전망" 섹션 지표 정의 및 판정 기준 (애널리스트 추정치 기반)
var OUTLOOK_METRICS = [
  { key:'upside',            label:'애널리스트 목표가',     unit:'price', scored:true,  higherIsBetter:true,  thresholds:[0, 0.15],
    tip:'12개월 이내 도달할 전망인 애널리스트 컨센서스 평균' },
  { key:'forwardPE',         label:'예상 PER (Forward)',  unit:'x',     scored:false,
    tip:'내년 예상 EPS 기준, 현재 PER과 비교해 이익 성장 반영 정도 확인' },
  { key:'pegRatio',          label:'PEG (성장 반영 밸류)', unit:'ratio', scored:true,  higherIsBetter:false, thresholds:[2, 1], tierLabels:['고평가','적정 평가','저평가'],
    tip:'PEG < 1 — 성장 대비 저렴' },
  { key:'epsGrowthNextYear', label:'내년 EPS 예상 성장률', unit:'pct',   scored:true,  higherIsBetter:true,  thresholds:[0, 0.10],
    tip:'10% 이상이면 견조한 성장, 마이너스는 이익 감소 예상' },
  { key:'epsGrowthNext5Y',   label:'5년 EPS 예상 연평균',  unit:'pct',   scored:true,  higherIsBetter:true,  thresholds:[0.10, 0.15],
    tip:'장기 성장 전망. 15% 이상이면 고성장 기업' }
];

// 절대 기준(thresholds) 대비 0(주의)/1(양호)/2(우수) 단계 판정
function outlookTier(value, thresholds, higherIsBetter) {
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

// 채점된 지표들의 평균 비율(0~1)을 바탕으로 종합 판정 산출
function outlookVerdict(ratio) {
  if (ratio == null) {
    return { emoji:'ℹ️', cls:'neutral', title:'데이터 부족', sub:'애널리스트 추정치가 부족해 종합 판정이 제한적입니다' };
  }
  if (ratio >= 0.7) {
    return { emoji:'🚀', cls:'good', title:'긍정적 전망', sub:'목표가·성장률·밸류에이션이 긍정적입니다' };
  }
  if (ratio >= 0.35) {
    return { emoji:'🔍', cls:'neutral', title:'중립적 전망', sub:'지표가 엇갈려 추가 확인이 필요합니다' };
  }
  return { emoji:'⚠️', cls:'bad', title:'신중한 접근 필요', sub:'목표가·성장률·밸류에이션 지표가 부진합니다' };
}
