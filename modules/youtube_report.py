#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube 딥리포트 생성기
Usage: python modules/youtube_report.py <youtube_url>
"""
import sys
import json
import os
import re
import requests
from datetime import datetime
from pathlib import Path

try:
    import pytz
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError as e:
    print(f"패키지 없음: {e}")
    print("먼저 실행: pip install -r requirements.txt")
    sys.exit(1)

KST = pytz.timezone('Asia/Seoul')
REPORTS_PATH = Path(__file__).parent.parent / 'reports.json'
GEMINI_URL = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={}'


def get_video_id(url):
    match = re.search(r'(?:v=|/v/|youtu\.be/|/embed/)([a-zA-Z0-9_-]{11})', url)
    return match.group(1) if match else None


def get_transcript(video_id):
    # 한국어 → 영어 → 자동생성 순으로 시도
    for langs in [['ko'], ['en'], None]:
        try:
            if langs:
                entries = YouTubeTranscriptApi.get_transcript(video_id, languages=langs)
            else:
                entries = YouTubeTranscriptApi.get_transcript(video_id)
            text = ' '.join(e['text'] for e in entries)
            print(f"  자막 추출 완료 ({len(text)}자)")
            return text
        except Exception:
            continue
    raise Exception("자막을 가져올 수 없습니다. 자막이 없는 영상이거나 접근이 제한된 영상입니다.")


def generate_report_with_gemini(transcript, video_id):
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        raise Exception("GEMINI_API_KEY 환경변수가 없습니다.")

    prompt = f"""다음은 YouTube 영상의 자막입니다. 이 내용을 바탕으로 스토리텔링형 깊이 있는 리포트를 작성해주세요.

요구사항:
- 단순 요약이 아닌 맥락, 의미, 시사점을 깊이 있게 서술
- 스토리텔링 형식으로 독자가 몰입할 수 있게 작성
- 섹션은 3~5개, 각 섹션은 소제목 + 2~4문단
- 인사이트는 핵심적인 것 3~5개

자막 (최대 8000자):
{transcript[:8000]}

반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트 없이 JSON만:
{{
  "title": "임팩트 있는 제목",
  "summary": "핵심 메시지를 담은 한 문장",
  "sections": [
    {{"heading": "섹션 소제목", "content": "섹션 내용 (2~4문단, 줄바꿈은 \\n\\n 사용)"}}
  ],
  "insights": ["인사이트1", "인사이트2", "인사이트3"]
}}"""

    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 4096}
    }

    r = requests.post(GEMINI_URL.format(api_key), json=body, timeout=60)
    r.raise_for_status()

    text = r.json()['candidates'][0]['content']['parts'][0]['text'].strip()

    # JSON 추출
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if not json_match:
        raise Exception("Gemini 응답에서 JSON을 파싱할 수 없습니다.")

    return json.loads(json_match.group())


def load_reports():
    if REPORTS_PATH.exists():
        with open(REPORTS_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_reports(reports):
    with open(REPORTS_PATH, 'w', encoding='utf-8') as f:
        json.dump(reports, f, ensure_ascii=False, indent=2)


def main():
    if len(sys.argv) < 2:
        print("Usage: python modules/youtube_report.py <youtube_url>")
        sys.exit(1)

    url = sys.argv[1].strip()
    print(f"처리 중: {url}")

    video_id = get_video_id(url)
    if not video_id:
        print("❌ 유효하지 않은 YouTube URL입니다.")
        sys.exit(1)

    print("자막 추출 중...")
    transcript = get_transcript(video_id)

    print("Gemini 리포트 생성 중...")
    report_data = generate_report_with_gemini(transcript, video_id)

    now = datetime.now(KST)
    report = {
        "id": f"{video_id}_{now.strftime('%Y%m%d%H%M')}",
        "url": url,
        "video_id": video_id,
        "created_at": now.strftime("%Y년 %m월 %d일 %H:%M"),
        "title": report_data.get("title", "제목 없음"),
        "summary": report_data.get("summary", ""),
        "sections": report_data.get("sections", []),
        "insights": report_data.get("insights", [])
    }

    reports = load_reports()
    reports.insert(0, report)  # 최신순
    save_reports(reports)

    print(f"✅ 저장 완료: {REPORTS_PATH}")
    print(f"   제목: {report['title']}")


if __name__ == '__main__':
    main()
