import os
import re
import json
import hashlib
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

CACHE_DIR = Path("summary_cache")
CACHE_DIR.mkdir(exist_ok=True)

LANGUAGE_OPTIONS = [
    "English",
    "Korean",
    "French",
    "Spanish",
    "Italian"
]

UI_TEXT = {
    "English": {
        "app_name": "GreenNote AI",
        "menu": "Menu",
        "home": "Home",
        "note": "Note",
        "mindmap": "Mindmap",
        "infographic": "Infographic",
        "quiz": "Quiz",
        "flashcards": "Flashcards",
        "source": "Source",
        "create": "Create New Note",
        "output_language": "Output Language",
        "youtube_url": "YouTube URL",
        "create_note": "Create Note",
        "hero": "Turn YouTube videos into beautiful notes, mindmaps, quizzes and flashcards.",
        "cache": "Previously summarized videos load instantly from cache.",
        "input": "Paste a YouTube link",
        "generate": "Generate study notes",
        "instant": "Instant loading",
        "empty": "Paste a YouTube link to begin.",
        "cached": "Loaded instantly from cache.",
        "new_saved": "New summary created.",
        "getting_transcript": "Fetching transcript...",
        "analyzing": "Analyzing video...",
        "download": "Download TXT"
    },
    "Korean": {
        "app_name": "GreenNote AI",
        "menu": "메뉴",
        "home": "홈",
        "note": "노트",
        "mindmap": "마인드맵",
        "infographic": "인포그래픽",
        "quiz": "퀴즈",
        "flashcards": "플래시카드",
        "source": "원본",
        "create": "새 노트 만들기",
        "output_language": "출력 언어",
        "youtube_url": "유튜브 링크",
        "create_note": "노트 생성",
        "hero": "유튜브 영상을 노트, 마인드맵, 인포그래픽, 퀴즈, 플래시카드로 정리합니다.",
        "cache": "같은 영상은 저장된 결과를 즉시 불러옵니다.",
        "input": "유튜브 링크 입력",
        "generate": "학습 노트 생성",
        "instant": "즉시 로딩",
        "empty": "유튜브 링크를 입력해 주세요.",
        "cached": "캐시된 결과를 즉시 불러왔습니다.",
        "new_saved": "새 요약을 생성했습니다.",
        "getting_transcript": "자막 불러오는 중...",
        "analyzing": "영상 분석 중...",
        "download": "TXT 다운로드"
    }
}

st.set_page_config(
    page_title="GreenNote AI",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)

lang = "English"

if "selected_language" not in st.session_state:
    st.session_state.selected_language = "English"

lang = st.session_state.selected_language
t = UI_TEXT[lang]

st.markdown("""
<style>
html, body, [class*="css"] {
    font-family: Inter, sans-serif;
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #ecfdf5 0%, #ffffff 100%);
}

.block-container {
    max-width: 1200px;
    padding-top: 1rem;
}

.main-title {
    font-size: clamp(40px, 7vw, 72px);
    font-weight: 900;
    color: #064e3b;
    line-height: 1.1;
}

.soft-card {
    background: white;
    border: 1px solid #d1fae5;
    border-radius: 28px;
    padding: clamp(22px, 4vw, 40px);
    box-shadow: 0 14px 40px rgba(6,78,59,0.08);
    margin-bottom: 28px;
}

.green-box {
    background: #ecfdf5;
    border-left: 7px solid #10b981;
    border-radius: 18px;
    padding: 20px;
    color: #065f46;
    font-weight: 700;
    font-size: clamp(17px, 2vw, 24px);
    margin-top: 18px;
}

.keyword {
    display:inline-block;
    background:#d1fae5;
    color:#065f46;
    padding:8px 14px;
    border-radius:999px;
    margin-right:8px;
    margin-top:10px;
    font-weight:700;
}

.note-card {
    background:white;
    border:1px solid #d1fae5;
    border-radius:22px;
    padding:24px;
    margin-bottom:20px;
    box-shadow:0 8px 22px rgba(6,78,59,0.06);
}

.info-card {
    background:linear-gradient(180deg,#ffffff 0%,#f0fdf4 100%);
    border:1px solid #bbf7d0;
    border-radius:22px;
    padding:24px;
    margin-bottom:18px;
}

.center-input {
    margin-top:28px;
    margin-bottom:10px;
}

.stButton > button {
    background:#059669 !important;
    color:white !important;
    border:none !important;
    border-radius:16px !important;
    height:58px !important;
    font-size:18px !important;
    font-weight:800 !important;
    width:100%;
}

.stTextInput input {
    border-radius:16px !important;
    border:2px solid #d1fae5 !important;
    height:58px !important;
    font-size:17px !important;
}

@media (max-width: 768px) {

    .main-title {
        font-size: 44px;
    }

    .soft-card {
        padding:22px;
        border-radius:22px;
    }

    [data-testid="stHorizontalBlock"] {
        flex-direction: column;
    }

    [data-testid="column"] {
        width:100% !important;
        flex:1 1 100% !important;
    }
}
</style>
""", unsafe_allow_html=True)


def clean_text(text):
    text = str(text or "")
    text = re.sub(r"<[^>]*>", "", text)
    text = text.replace("```", "")
    return text.strip()


def extract_video_id(url):
    patterns = [
        r"(?:v=)([a-zA-Z0-9_-]{11})",
        r"(?:youtu\\.be/)([a-zA-Z0-9_-]{11})",
        r"(?:shorts/)([a-zA-Z0-9_-]{11})"
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    raise ValueError("Invalid YouTube URL")


def seconds_to_mmss(seconds):
    seconds = int(seconds)
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def youtube_link(video_id, seconds):
    return f"https://youtu.be/{video_id}?t={int(seconds)}"


def cache_key(video_id, language):
    raw = f"{video_id}_{language}"
    return hashlib.md5(raw.encode()).hexdigest()


def cache_path(video_id, language):
    return CACHE_DIR / f"{cache_key(video_id, language)}.json"


def load_cache(video_id, language):
    path = cache_path(video_id, language)

    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    return None


def save_cache(video_id, language, report):
    path = cache_path(video_id, language)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)


@st.cache_data(show_spinner=False)
def get_transcript(video_id):

    ytt = YouTubeTranscriptApi()

    transcript = ytt.fetch(video_id)

    items = []

    for item in transcript:
        items.append({
            "time": seconds_to_mmss(item.start),
            "seconds": int(item.start),
            "url": youtube_link(video_id, item.start),
            "text": item.text
        })

    return items


def split_transcript(items, max_chars=14000):

    chunks = []
    current = []
    current_len = 0

    for item in items:

        line = f"[{item['time']}] {item['text']}"

        current.append(line)
        current_len += len(line)

        if current_len >= max_chars:
            chunks.append("\\n".join(current))
            current = []
            current_len = 0

    if current:
        chunks.append("\\n".join(current))

    return chunks


def analyze_chunk(chunk, output_language):

    prompt = f"""
Analyze this YouTube transcript.

Output language: {output_language}

Rules:
- Natural human writing
- No HTML
- No code
- No SVG
- No markdown tables

Transcript:
{chunk}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": "Return clean natural text only."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.2
    )

    return response.choices[0].message.content


def create_report(content, output_language):

    prompt = f"""
Create a clean JSON learning report.

Language: {output_language}

NO HTML.
NO SVG.
NO CODE.

Return valid JSON only.

Schema:

{{
 "title":"",
 "summary":"",
 "keywords":["","",""],
 "sections":[
   {{
      "time":"",
      "url":"",
      "emoji":"",
      "title":"",
      "message":"",
      "points":["","",""]
   }}
 ],
 "mindmap":[
   {{
      "emoji":"",
      "topic":"",
      "children":["","",""]
   }}
 ],
 "quiz":[
   {{
      "question":"",
      "answer":"",
      "explanation":""
   }}
 ]
}}

Source:
{content}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": "Return valid JSON only."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.15
    )

    content = response.choices[0].message.content
    content = content.replace("```json", "").replace("```", "")

    return json.loads(content)


with st.sidebar:

    st.markdown("## 🌿 GreenNote AI")

    lang = st.selectbox(
        "Language",
        LANGUAGE_OPTIONS,
        index=0
    )

    st.session_state.selected_language = lang
    t = UI_TEXT.get(lang, UI_TEXT["English"])

    page = st.radio(
        t["menu"],
        [
            t["home"],
            t["note"],
            t["mindmap"],
            t["quiz"]
        ]
    )

    st.divider()

    st.markdown(f"### ✨ {t['create']}")

st.markdown(f"""
<div class="soft-card">

<div class="main-title">
🌿 GreenNote AI
</div>

<div class="green-box">
{t['hero']}
</div>

<p style="font-size:18px;color:#64748b;margin-top:16px;">
{t['cache']}
</p>

</div>
""", unsafe_allow_html=True)

st.markdown('<div class="center-input">', unsafe_allow_html=True)

youtube_url = st.text_input(
    "",
    placeholder="https://www.youtube.com/watch?v=..."
)

create_btn = st.button(
    f"✨ {t['create_note']}",
    use_container_width=True
)

st.markdown('</div>', unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)

with c1:
    st.info(f"📁 {t['input']}")

with c2:
    st.success(f"🧠 {t['generate']}")

with c3:
    st.warning(f"⚡ {t['instant']}")

if "report" not in st.session_state:
    st.session_state.report = None

if create_btn:

    try:

        video_id = extract_video_id(youtube_url)

        cached = load_cache(video_id, lang)

        if cached:

            st.session_state.report = cached

            st.success(t["cached"])

        else:

            with st.spinner(t["getting_transcript"]):

                transcript_items = get_transcript(video_id)

            chunks = split_transcript(transcript_items)

            combined = []

            with st.spinner(t["analyzing"]):

                for chunk in chunks:
                    combined.append(analyze_chunk(chunk, lang))

            report = create_report(
                "\\n\\n".join(combined),
                lang
            )

            save_cache(video_id, lang, report)

            st.session_state.report = report

            st.success(t["new_saved"])

    except Exception as e:
        st.error(str(e))

report = st.session_state.report

if report and page == t["note"]:

    st.markdown(
        f"<div class='main-title' style='font-size:48px'>{clean_text(report['title'])}</div>",
        unsafe_allow_html=True
    )

    st.markdown(
        f"<div class='green-box'>{clean_text(report['summary'])}</div>",
        unsafe_allow_html=True
    )

    for keyword in report.get("keywords", []):
        st.markdown(
            f"<span class='keyword'>#{clean_text(keyword)}</span>",
            unsafe_allow_html=True
        )

    st.markdown("<br><br>", unsafe_allow_html=True)

    for section in report.get("sections", []):

        with st.container():

            st.markdown('<div class="note-card">', unsafe_allow_html=True)

            st.link_button(
                section["time"],
                section["url"]
            )

            st.markdown(
                f"## {clean_text(section['emoji'])} {clean_text(section['title'])}"
            )

            st.success(clean_text(section["message"]))

            for point in section.get("points", []):
                st.markdown(f"- {clean_text(point)}")

            st.markdown('</div>', unsafe_allow_html=True)

if report and page == t["mindmap"]:

    st.markdown(
        f"<div class='main-title' style='font-size:48px'>{clean_text(report['title'])}</div>",
        unsafe_allow_html=True
    )

    st.markdown("<br>", unsafe_allow_html=True)

    cols = st.columns(2)

    for i, branch in enumerate(report.get("mindmap", [])):

        with cols[i % 2]:

            st.markdown(
                f"""
                <div class="info-card">
                    <h2>{clean_text(branch['emoji'])} {clean_text(branch['topic'])}</h2>
                """,
                unsafe_allow_html=True
            )

            for child in branch.get("children", []):
                st.markdown(f"- {clean_text(child)}")

            st.markdown("</div>", unsafe_allow_html=True)

if report and page == t["quiz"]:

    st.markdown(
        f"<div class='main-title' style='font-size:48px'>{clean_text(report['title'])}</div>",
        unsafe_allow_html=True
    )

    for i, quiz in enumerate(report.get("quiz", []), 1):

        with st.expander(f"Q{i}. {clean_text(quiz['question'])}"):

            st.success(clean_text(quiz["answer"]))

            st.write(clean_text(quiz["explanation"]))
