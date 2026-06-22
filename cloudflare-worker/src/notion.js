import { jsonResponse } from './cors.js';

function textToBlocks(text) {
  if (!text) return [];
  const blocks = [];
  const lines = text.split('\n');
  let current = '';

  for (const line of lines) {
    if (current.length + line.length + 1 > 1900) {
      if (current.trim()) {
        blocks.push(paragraphBlock(current.trim()));
      }
      current = line;
    } else {
      current = current ? current + '\n' + line : line;
    }
  }
  if (current.trim()) blocks.push(paragraphBlock(current.trim()));
  return blocks;
}

function paragraphBlock(content) {
  return {
    object: 'block',
    type: 'paragraph',
    paragraph: { rich_text: [{ type: 'text', text: { content } }] },
  };
}

function heading2Block(content) {
  return {
    object: 'block',
    type: 'heading_2',
    heading_2: { rich_text: [{ type: 'text', text: { content } }] },
  };
}

function dividerBlock() {
  return { object: 'block', type: 'divider', divider: {} };
}

export async function handleNotion(request, env) {
  if (request.method !== 'POST') return jsonResponse({ error: 'POST only' }, 405);

  const notionToken = env.NOTION_TOKEN;
  const parentPageId = env.NOTION_PAGE_ID;

  if (!notionToken) return jsonResponse({ error: 'NOTION_TOKEN secret이 설정되지 않았습니다.' }, 500);
  if (!parentPageId) return jsonResponse({ error: 'NOTION_PAGE_ID secret이 설정되지 않았습니다.' }, 500);

  let body;
  try { body = await request.json(); } catch { return jsonResponse({ error: '요청 파싱 실패' }, 400); }

  const { title, summary, transcript, videoUrl, language } = body;

  const children = [];

  if (videoUrl) children.push(paragraphBlock(`🔗 ${videoUrl}`));
  if (language) children.push(paragraphBlock(`📌 분석 방식: ${language}`));
  children.push(dividerBlock());

  children.push(heading2Block('📊 상세 분석 (5장)'));
  children.push(...textToBlocks(summary).slice(0, 50));

  if (transcript) {
    children.push(dividerBlock());
    children.push(heading2Block('📝 스크립트'));
    children.push(...textToBlocks(transcript).slice(0, 40));
  }

  const notionRes = await fetch('https://api.notion.com/v1/pages', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${notionToken}`,
      'Content-Type': 'application/json',
      'Notion-Version': '2022-06-28',
    },
    body: JSON.stringify({
      parent: { type: 'page_id', page_id: parentPageId },
      properties: {
        title: { title: [{ type: 'text', text: { content: title || '영상분석' } }] },
      },
      children: children.slice(0, 100),
    }),
  });

  if (!notionRes.ok) {
    const errText = await notionRes.text();
    return jsonResponse({ error: `Notion API 오류: ${errText.slice(0, 300)}` }, 500);
  }

  const notionData = await notionRes.json();
  return jsonResponse({ url: notionData.url, id: notionData.id });
}
