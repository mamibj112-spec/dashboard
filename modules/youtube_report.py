#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube 딥리포트 생성기 (Gemini 영상 직접 분석)
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
except ImportError as e:
    print(f"패키지 없음: {e}")
    print("먼저 실행: pip install -r requirements.txt")
    sys.exit(1)

KST = pytz.timezone('Asia/Seoul')
REPORTS_PATH = Path(__file__).parent.parent / 'reports.json'
GEMINI_URL = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={}'


def get_video_id(url):
    match = re.search(r'(?:v=|/v/|youtu\.be/|/embed/)([a-zA-Z0-9_-]{11})', url)
    return match.group(1) if match else None


def generate_report_with_gemini(youtube_url):
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        raise Exception("GEMINI_API_KEY 환경변수가 없습니다.")

    prompt = """이 YouTube 영상을 깊이 있게 분석하여 스토리텔링형 리포트를 작성해주세요.

요구사항:
- 단순 요약이 아닌 맥락, 의미, 시사점을 깊이 있게 서술
- 영상의 시각 자료, 발표 내용, 강조점, 흐름까지 모두 반영
- 스토리텔링 형식으로 독자가 몰입할 수 있게 작성
- 섹션은 3~5개, 각 섹션은 소제목 + 2~4문단
- 핵심 인사이트 3~5개 (영상에서 가장 중요한 메시지)

반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트 없이 JSON만:
{
  "title": "임팩트 있는 제목",
  "summary": "핵심 메시지를 담은 한 문장",
  "sections": [
    {"heading": "섹션 소제목", "content": "섹션 내용 (2~4문단, 줄바꿈은 \\n\\n 사용)"}
  ],
  "insights": ["인사이트1", "인사이트2", "인사이트3"]
}"""

    body = {
        "contents": [{
            "parts": [
                {
                    "fileData": {
                        "mimeType": "video/*",
                        "fileUri": youtube_url
                    }
                },
                {"text": prompt}
            ]
        }],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 8192}
    }

    r = requests.post(GEMINI_URL.format(api_key), json=body, timeout=300)
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

    print("Gemini 영상 직접 분석 중...")
    report_data = generate_report_with_gemini(url)

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
