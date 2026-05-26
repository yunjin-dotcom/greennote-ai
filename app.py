import os
import re
import json
import hashlib
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from youtube_transcript_api import YouTubeTranscriptApi

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

CACHE_DIR = Path("summary_cache")
CACHE_DIR.mkdir(exist_ok=True)

LANGUAGES = ["English", "Korean"]

TEXT = {
    "English": {
        "title": "🌿 GreenNote AI",
        "subtitle": "Turn YouTube videos into clear study notes, mindmaps, quizzes and flashcards.",
        "cache": "Previously summarized videos load instantly from cache.",
        "placeholder": "Paste a YouTube link here...",
        "button": "✨ Create Note",
        "loading_transcript": "Fetching transcript...",
        "loading_ai": "Creating notes...",
        "cached": "Loaded from cache.",
        "created": "New note created.",
        "invalid": "Invalid YouTube URL.",
        "no_transcript": "No transcript is available for this video.",
        "menu": "Menu",
        "home": "Home",
        "note": "Note",
        "mindmap": "Mindmap",
        "quiz": "Quiz",
        "flashcards": "Flashcards",
    },
    "Korean": {
        "title": "🌿 GreenNote AI",
        "subtitle": "유튜브 영상을 깔끔한 요약 노트, 마인드맵, 퀴즈, 플래시카드로 정리합니다.",
        "cache": "이전에 요약한 영상은 캐시에서 즉시 불러옵니다.",
        "placeholder": "유튜브 링크를 입력하세요...",
        "button": "✨ 노트 생성하기",
        "loading_transcript": "자막을 가져오는 중...",
        "loading_ai": "AI가 노트를 만드는 중...",
        "cached": "저장된 요약을 불러왔습니다.",
        "created": "새 노트를 생성했습니다.",
        "invalid": "유효하지 않은 유튜브 링크입니다.",
        "no_transcript": "이 영상에서 사용할 수 있는 자막을 찾지 못했습니다.",
        "menu": "메뉴",
        "home": "홈",
        "note": "노트",
        "mindmap": "마인드맵",
        "quiz": "퀴즈",
        "flashcards": "플래시카드",
    },
}

st.set_page_config(
    page_title="GreenNote AI",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .block-container {
        max-width: 1100px;
        padding-top: 2rem;
    }
    [data-testid="stSidebar"] {
        background: #ecfdf5;
    }
    div.stButton > button {
        background-color: #059669;
        color: white;
        border-radius: 14px;
        height: 52px;
        font-weight: 700;
        border: none;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def extract_video_id(url: str):
    try:
        parsed = urlparse(url.strip())

        if parsed.hostname in ["youtu.be", "www.youtu.be"]:
            video_id = parsed.path.strip("/")
            return video_id[:11] if len(video_id) >= 11 else None

        if parsed.hostname in ["youtube.com", "www.youtube.com", "m.youtube.com"]:
            if parsed.path == "/watch":
                return parse_qs(parsed.query).get("v", [None])[0]

            if parsed.path.startswith("/shorts/"):
                return parsed.path.split("/")[2]

            if parsed.path.startswith("/embed/"):
                return parsed.path.split("/")[2]

        if re.fullmatch(r"[a-zA-Z0-9_-]{11}", url.strip()):
            return url.strip()

        return None

    except Exception:
        return None


def seconds_to_mmss(seconds):
    seconds = int(seconds)
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def youtube_time_link(video_id, seconds):
    return f"https://youtu.be/{video_id}?t={int(seconds)}"


def get_cache_path(video_id, language):
    key = hashlib.md5(f"{video_id}_{language}_stable_native_v2".encode()).hexdigest()
    return CACHE_DIR / f"{key}.json"


def load_cache(video_id, language):
    path = get_cache_path(video_id, language)
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def save_cache(video_id, language, data):
    path = get_cache_path(video_id, language)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@st.cache_data(show_spinner=False)
def get_transcript(video_id):
    api = YouTubeTranscriptApi()

    preferred_languages = [
        "en", "ko", "ja", "es", "fr", "it",
        "de", "pt", "zh-Hans", "zh-Hant",
        "id", "vi", "th", "hi"
    ]

    transcript = None

    try:
        transcript = api.fetch(video_id, languages=preferred_languages)
    except Exception:
        pass

    if transcript is None:
        try:
            transcript_list = api.list(video_id)

            try:
                transcript_obj = transcript_list.find_transcript(preferred_languages)
                transcript = transcript_obj.fetch()
            except Exception:
                pass

            if transcript is None:
                try:
                    transcript_obj = transcript_list.find_generated_transcript(preferred_languages)
                    transcript = transcript_obj.fetch()
                except Exception:
                    pass

            if transcript is None:
                for transcript_obj in transcript_list:
                    try:
                        transcript = transcript_obj.fetch()
                        break
                    except Exception:
                        continue

        except Exception:
            transcript = None

    if transcript is None:
        return []

    items = []

    for item in transcript:
        try:
            start = item.start
            text = item.text
        except AttributeError:
            start = item.get("start", 0)
            text = item.get("text", "")

        items.append({
            "time": seconds_to_mmss(start),
            "seconds": int(start),
            "url": youtube_time_link(video_id, start),
            "text": text
        })

    return items


def split_transcript(items, max_chars=12000):
    chunks = []
    current = []
    current_len = 0

    for item in items:
        line = f"[{item['time']} | {item['url']}] {item['text']}"
        current.append(line)
        current_len += len(line)

        if current_len >= max_chars:
            chunks.append("\n".join(current))
            current = []
            current_len = 0

    if current:
        chunks.append("\n".join(current))

    return chunks


def analyze_chunk(chunk, language):
    prompt = f"""
You are a careful YouTube content analyst.

Output language: {language}

Rules:
- Write only in {language}.
- If Korean, use natural Korean, not translated Korean.
- Do not output HTML, XML, SVG, CSS, markdown tables, or code.
- Use plain text only.
- Do not invent facts.
- Keep timeline references when available.

Transcript chunk:
{chunk}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": "You summarize YouTube transcripts clearly and naturally."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )

    return response.choices[0].message.content


def create_report(analysis_text, language):
    prompt = f"""
Create a clean learning report from the analysis.

Output language: {language}

Rules:
- Return valid JSON only.
- Do not include HTML, XML, SVG, CSS, markdown tables, or code.
- If Korean, write natural Korean.
- Use concise but useful explanations.

JSON schema:
{{
  "title": "clear title",
  "summary": "one clear summary",
  "keywords": ["keyword1", "keyword2", "keyword3"],
  "sections": [
    {{
      "time": "MM:SS",
      "url": "YouTube timestamp URL",
      "emoji": "emoji",
      "title": "section title",
      "message": "key takeaway",
      "points": ["point 1", "point 2", "point 3"]
    }}
  ],
  "mindmap": [
    {{
      "emoji": "emoji",
      "topic": "main branch",
      "children": ["sub idea 1", "sub idea 2", "sub idea 3"]
    }}
  ],
  "quiz": [
    {{
      "question": "question",
      "answer": "answer",
      "explanation": "explanation"
    }}
  ],
  "flashcards": [
    {{
      "front": "term or question",
      "back": "answer or explanation"
    }}
  ]
}}

Make:
- 6 to 9 sections
- 8 to 12 mindmap branches
- 5 quiz questions
- 8 flashcards

Analysis:
{analysis_text}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": "Return valid JSON only."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.15,
    )

    content = response.choices[0].message.content.strip()
    content = content.replace("```json", "").replace("```", "").strip()

    return json.loads(content)


def clean_text(value):
    text = str(value or "")
    text = re.sub(r"<[^>]*>", "", text)
    text = text.replace("```", "")
    return text.strip()


if "language" not in st.session_state:
    st.session_state.language = "English"

if "report" not in st.session_state:
    st.session_state.report = None


with st.sidebar:
    st.title("🌿 GreenNote AI")

    language = st.selectbox(
        "Language",
        LANGUAGES,
        index=LANGUAGES.index(st.session_state.language),
    )
    st.session_state.language = language
    t = TEXT[language]

    page = st.radio(
        t["menu"],
        [t["home"], t["note"], t["mindmap"], t["quiz"], t["flashcards"]],
    )


st.title(t["title"])
st.info(t["subtitle"])
st.caption(t["cache"])

youtube_url = st.text_input(
    "",
    placeholder=t["placeholder"],
)

create_button = st.button(t["button"], use_container_width=True)

col1, col2, col3 = st.columns(3)
col1.info("📁 " + ("Paste a YouTube link" if language == "English" else "유튜브 링크 입력"))
col2.success("🧠 " + ("Generate study notes" if language == "English" else "학습 노트 생성"))
col3.warning("⚡ " + ("Instant loading" if language == "English" else "즉시 로딩"))


if create_button:
    video_id = extract_video_id(youtube_url)

    if not video_id:
        st.error(t["invalid"])
        st.stop()

    cached = load_cache(video_id, language)

    if cached:
        st.session_state.report = cached
        st.success(t["cached"])

    else:
        with st.spinner(t["loading_transcript"]):
            transcript_items = get_transcript(video_id)

        if not transcript_items:
            st.error(t["no_transcript"])
            st.stop()

        chunks = split_transcript(transcript_items)
        partials = []

        with st.spinner(t["loading_ai"]):
            progress = st.progress(0)

            for i, chunk in enumerate(chunks):
                partials.append(analyze_chunk(chunk, language))
                progress.progress((i + 1) / len(chunks))

            report = create_report("\n\n".join(partials), language)

        save_cache(video_id, language, report)
        st.session_state.report = report
        st.success(t["created"])


report = st.session_state.report

if report:
    if page == t["home"]:
        st.subheader(clean_text(report.get("title", "")))
        st.write(clean_text(report.get("summary", "")))

        for keyword in report.get("keywords", []):
            st.badge(clean_text(keyword))

    elif page == t["note"]:
        st.header(clean_text(report.get("title", "")))
        st.success(clean_text(report.get("summary", "")))

        for section in report.get("sections", []):
            with st.container(border=True):
                if section.get("url"):
                    st.link_button(clean_text(section.get("time", "00:00")), section.get("url"))

                st.subheader(f"{clean_text(section.get('emoji', '📌'))} {clean_text(section.get('title', ''))}")
                st.info(clean_text(section.get("message", "")))

                for point in section.get("points", []):
                    st.markdown(f"- {clean_text(point)}")

    elif page == t["mindmap"]:
        st.header("🧠 " + clean_text(report.get("title", "")))

        cols = st.columns(2)

        for i, branch in enumerate(report.get("mindmap", [])):
            with cols[i % 2]:
                with st.container(border=True):
                    st.subheader(f"{clean_text(branch.get('emoji', '🌿'))} {clean_text(branch.get('topic', ''))}")
                    for child in branch.get("children", []):
                        st.markdown(f"- {clean_text(child)}")

    elif page == t["quiz"]:
        st.header("🧩 Quiz")

        for i, quiz in enumerate(report.get("quiz", []), 1):
            with st.expander(f"Q{i}. {clean_text(quiz.get('question', ''))}"):
                st.success(clean_text(quiz.get("answer", "")))
                st.write(clean_text(quiz.get("explanation", "")))

    elif page == t["flashcards"]:
        st.header("🃏 Flashcards")

        for i, card in enumerate(report.get("flashcards", []), 1):
            with st.expander(f"Card {i}: {clean_text(card.get('front', ''))}"):
                st.write(clean_text(card.get("back", "")))
