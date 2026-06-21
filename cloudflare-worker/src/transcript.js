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

// HTML에서 captionTracks 배열만 추출 (전체 JSON 파싱보다 훨씬 가볍고 빠름)
function extractCaptionTracks(html) {
  const marker = '"captionTracks":';
  const idx = html.indexOf(marker);
  if (idx === -1) return null;

  const str = html.slice(idx + marker.length);
  if (!str.startsWith('[')) return null;

  let depth = 0, i = 0;
  for (i = 0; i < str.length; i++) {
    const c = str[i];
    if (c === '[' || c === '{') depth++;
    else if (c === ']' || c === '}') { depth--; if (depth === 0) { i++; break; } }
  }

  try { return JSON.parse(str.slice(0, i)); } catch { return null; }
}

async function getTranscript(videoId) {
  const res = await fetch(`https://www.youtube.com/watch?v=${videoId}`, {
    headers: {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36',
      'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8',
      'Cookie': 'CONSENT=YES+cb; PREF=hl=ko',
    },
  });

  if (!res.ok) throw new Error(`YouTube 페이지 로드 실패 (${res.status})`);
  const html = await res.text();

  // 제목 추출
  const titleMatch = html.match(/<title>([^<]+)<\/title>/);
  const title = (titleMatch?.[1] || '제목 없음').replace(/ - YouTube$/, '');

  const captionTracks = extractCaptionTracks(html);
  if (!captionTracks?.length) {
    throw new Error('이 영상에는 자막이 없습니다. (자동 생성 자막 포함)');
  }

  // 한국어 > 영어 > 첫 번째 트랙
  const track = captionTracks.find(t => t.languageCode === 'ko')
    || captionTracks.find(t => t.languageCode === 'en')
    || captionTracks[0];

  const language = track.name?.simpleText || track.languageCode || '알 수 없음';

  // baseUrl이 HTML 인코딩된 경우 디코딩
  const baseUrl = track.baseUrl.replace(/\\u0026/g, '&');

  const captionRes = await fetch(`${baseUrl}&fmt=json3`, {
    headers: { 'User-Agent': 'Mozilla/5.0' },
  });
  if (!captionRes.ok) throw new Error(`자막 파일 다운로드 실패 (${captionRes.status})`);

  let captionData;
  try { captionData = await captionRes.json(); }
  catch { throw new Error('자막 파일 파싱 실패'); }

  const texts = [];
  for (const event of (captionData.events || [])) {
    if (!event.segs) continue;
    const line = event.segs.map(s => (s.utf8 || '').replace(/\n/g, ' ')).join('').trim();
    if (line) texts.push(line);
  }

  if (!texts.length) throw new Error('자막 내용이 비어있습니다.');

  const paragraphs = [];
  for (let i = 0; i < texts.length; i += 8) {
    paragraphs.push(texts.slice(i, i + 8).join(' '));
  }

  return { title, transcript: paragraphs.join('\n\n'), language };
}

async function summarizeWithGemini(transcript, title, apiKey, model = 'gemini-2.0-flash') {
  const prompt = `다음은 YouTube 영상 "${title}"의 자막 전문입니다.
아래 형식으로 한국어로 정리해주세요:

**📌 한 줄 요약**
(핵심 메시지를 한 문장으로)

**🔑 주요 내용**
• (포인트 1)
• (포인트 2)
• (포인트 3~5개)

**💡 결론 / 시사점**
(실용적인 takeaway)

자막:
${transcript.slice(0, 10000)}`;

  const res = await fetch(
    `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${apiKey}`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        contents: [{ parts: [{ text: prompt }] }],
        generationConfig: { maxOutputTokens: 1024, temperature: 0.3 },
      }),
    }
  );

  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`Gemini API 오류: ${errText.slice(0, 200)}`);
  }

  let data;
  try { data = await res.json(); }
  catch { throw new Error('Gemini 응답 파싱 실패'); }

  const text = data.candidates?.[0]?.content?.parts?.[0]?.text;
  if (!text) throw new Error('Gemini 응답이 비어있습니다');
  return text;
}

export async function handleTranscript(request, env) {
  const url = new URL(request.url);
  const videoUrl = url.searchParams.get('url');

  if (!videoUrl) return jsonResponse({ error: 'url 파라미터가 필요합니다.' }, 400);

  const videoId = extractVideoId(videoUrl);
  if (!videoId) return jsonResponse({ error: '유효한 YouTube URL이 아닙니다.' }, 400);

  const apiKey = env.GEMINI_API_KEY;
  if (!apiKey) return jsonResponse({ error: 'GEMINI_API_KEY secret이 설정되지 않았습니다.' }, 500);

  const model = url.searchParams.get('model') || 'gemini-2.0-flash';

  try {
    const { title, transcript, language } = await getTranscript(videoId);
    const summary = await summarizeWithGemini(transcript, title, apiKey, model);
    return jsonResponse({ title, transcript, summary, language, videoId, model });
  } catch (err) {
    return jsonResponse({ error: err.message || '알 수 없는 오류 발생' }, 500);
  }
}
