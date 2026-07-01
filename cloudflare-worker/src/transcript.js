import { jsonResponse } from './cors.js';

function extractVideoId(url) {
  try {
    const u = new URL(url);
    if (u.hostname === 'youtu.be') return u.pathname.slice(1).split('?')[0];
    const v = u.searchParams.get('v');
    if (v) return v;
    const pathMatch = u.pathname.match(/(?:\/embed\/|\/shorts\/)([a-zA-Z0-9_-]{11})/);
    if (pathMatch) return pathMatch[1];
  } catch {}
  return null;
}

async function getTitle(videoId) {
  try {
    const res = await fetch(`https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v=${videoId}&format=json`);
    if (!res.ok) return '제목 없음';
    const data = await res.json();
    return data.title || '제목 없음';
  } catch { return '제목 없음'; }
}

// YouTube timedtext API 직접 호출 (watch 페이지 불필요)
async function fetchTimedText(videoId, lang, kind = '') {
  const kindParam = kind ? `&kind=${kind}` : '';
  const url = `https://www.youtube.com/api/timedtext?v=${videoId}&lang=${lang}${kindParam}&fmt=srv3`;
  const res = await fetch(url, {
    headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36' },
  });
  if (!res.ok || res.status === 204) return null;
  const text = await res.text();
  if (!text || text.length < 30) return null;
  return text;
}

function parseTimedText(xml) {
  const texts = [];
  const re = /<s[^>]*>([^<]*(?:<[^/][^>]*\/>[^<]*)*)<\/s>|<text[^>]*>([^<]*)<\/text>/g;
  let m;
  while ((m = re.exec(xml)) !== null) {
    const raw = (m[1] || m[2] || '')
      .replace(/<[^>]+>/g, '')
      .replace(/&#39;/g, "'").replace(/&amp;/g, '&')
      .replace(/&quot;/g, '"').replace(/&lt;/g, '<').replace(/&gt;/g, '>')
      .replace(/\n/g, ' ').trim();
    if (raw) texts.push(raw);
  }
  return texts;
}

async function getTranscript(videoId) {
  // 시도 순서: 한국어 수동 → 한국어 자동생성 → 영어 수동 → 영어 자동생성
  const attempts = [
    { lang: 'ko', kind: '' },
    { lang: 'ko', kind: 'asr' },
    { lang: 'en', kind: '' },
    { lang: 'en', kind: 'asr' },
  ];

  let xml = null;
  let usedLang = '';

  for (const { lang, kind } of attempts) {
    xml = await fetchTimedText(videoId, lang, kind);
    if (xml) { usedLang = lang + (kind ? '(자동)' : ''); break; }
  }

  if (!xml) {
    throw new Error('자막을 찾을 수 없습니다. 이 영상에 자막이 없거나 비공개 영상입니다.');
  }

  const texts = parseTimedText(xml);
  if (!texts.length) throw new Error('자막 내용이 비어있습니다.');

  const paragraphs = [];
  for (let i = 0; i < texts.length; i += 8) {
    paragraphs.push(texts.slice(i, i + 8).join(' '));
  }

  const title = await getTitle(videoId);
  return { title, transcript: paragraphs.join('\n\n'), language: usedLang };
}

const SUMMARY_PROMPT = (title) => `다음 5장 형식으로 한국어로 상세 분석을 작성해주세요.
별표(**), 샵(#), 대시(---) 같은 마크다운 기호는 절대 사용하지 마세요.
각 장은 반드시 아래처럼 [숫자장] 형태로 시작하고, 불릿은 - 로 작성해주세요.

[1장] 핵심 요약
영상의 핵심 메시지를 2~3문장으로 요약해주세요.

[2장] 배경 & 맥락
이 주제의 배경, 현재 상황, 중요성을 2~4문장으로 서술해주세요.

[3장] 주요 내용 상세
- 핵심 포인트 1: 구체적 설명
- 핵심 포인트 2: 구체적 설명
- 핵심 포인트 3: 구체적 설명
- 핵심 포인트 4: 구체적 설명
- 핵심 포인트 5: 구체적 설명

[4장] 핵심 인사이트 & 분석
단순 요약을 넘어선 깊이 있는 분석, 숨겨진 의미, 연관 트렌드를 3~5문장으로 서술해주세요.

[5장] 결론 & 시사점
실용적인 takeaway와 투자·비즈니스·개인 관점의 활용 방안을 2~4문장으로 서술해주세요.`;

async function callGemini(apiKey, model, parts, maxOutputTokens = 8192) {
  const res = await fetch(
    `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${apiKey}`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        contents: [{ parts }],
        generationConfig: { maxOutputTokens, temperature: 0.3 },
      }),
    }
  );
  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`Gemini API 오류: ${errText.slice(0, 200)}`);
  }
  let data;
  try { data = await res.json(); } catch { throw new Error('Gemini 응답 파싱 실패'); }
  const text = data.candidates?.[0]?.content?.parts?.[0]?.text;
  if (!text) throw new Error('Gemini 응답이 비어있습니다');
  return text;
}

// 자막 텍스트 기반 요약
async function summarizeWithText(transcript, title, apiKey, model) {
  return callGemini(apiKey, model, [{
    text: `다음은 YouTube 영상 "${title}"의 자막 전문입니다.\n${SUMMARY_PROMPT(title)}\n\n자막:\n${transcript.slice(0, 30000)}`
  }]);
}

// 자막 없을 때: Gemini가 YouTube 영상 직접 분석 → 요약 + 스크립트 동시 생성
async function analyzeVideoDirectly(videoId, title, apiKey, model) {
  const videoModel = model || 'gemini-2.5-flash';
  const prompt = `YouTube 영상 "${title}"을 시청하고 아래 두 가지를 한국어로 작성해주세요.

===SUMMARY===
${SUMMARY_PROMPT(title)}

===TRANSCRIPT===
영상에서 말한 내용을 최대한 그대로 받아쓰고, 시간 순서대로 자연스러운 문단으로 정리해주세요. 말의 흐름을 살려 읽기 쉽게 구성해주세요.`;

  const raw = await callGemini(apiKey, videoModel, [
    {
      fileData: {
        mimeType: 'video/mp4',
        fileUri: `https://www.youtube.com/watch?v=${videoId}`,
      },
    },
    { text: prompt },
  ], 32768);

  // ===TRANSCRIPT=== 기준으로 분리 (===SUMMARY=== 마커 없이 응답해도 처리)
  const parts = raw.split(/===TRANSCRIPT===/);
  const summaryRaw = parts[0].replace(/===SUMMARY===/g, '').trim();
  const transcriptRaw = parts.length >= 2 ? parts.slice(1).join('').trim() : '';

  return {
    summary: summaryRaw,
    transcript: transcriptRaw,
  };
}

export async function handleTranscript(request, env) {
  const url = new URL(request.url);
  const videoUrl = url.searchParams.get('url');

  if (!videoUrl) return jsonResponse({ error: 'url 파라미터가 필요합니다.' }, 400);

  const videoId = extractVideoId(videoUrl);
  if (!videoId) return jsonResponse({ error: '유효한 YouTube URL이 아닙니다.' }, 400);

  const apiKey = env.GEMINI_API_KEY;
  if (!apiKey) return jsonResponse({ error: 'GEMINI_API_KEY secret이 설정되지 않았습니다.' }, 500);

  const model = url.searchParams.get('model') || 'gemini-2.5-flash';

  try {
    let title = '제목 없음', transcript = '', language = '', summary = '';

    try {
      const result = await getTranscript(videoId);
      title = result.title;
      transcript = result.transcript;
      language = result.language;
      summary = await summarizeWithText(transcript, title, apiKey, model);
    } catch {
      // 자막 없음 → Gemini가 영상 직접 보고 요약 + 스크립트 동시 생성
      title = await getTitle(videoId);
      language = '🤖 Gemini 직접 분석';
      const analyzed = await analyzeVideoDirectly(videoId, title, apiKey, model);
      summary = analyzed.summary;
      transcript = analyzed.transcript;
    }

    return jsonResponse({ title, transcript, summary, language, videoId, model });
  } catch (err) {
    return jsonResponse({ error: err.message || '알 수 없는 오류 발생' }, 500);
  }
}
