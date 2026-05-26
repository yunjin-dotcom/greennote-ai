import streamlit as st
from openai import OpenAI
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs
import hashlib
import json
import os
import textwrap

# =========================
# PAGE CONFIG
# =========================

st.set_page_config(
    page_title="GreenNote AI",
    page_icon="🌿",
    layout="wide"
)

# =========================
# OPENAI
# =========================

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

# =========================
# CACHE
# =========================

CACHE_DIR = "summary_cache"

if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

# =========================
# LANGUAGE DETECTION
# =========================

browser_lang = st.context.headers.get("Accept-Language", "")

if "ko" in browser_lang.lower():
    default_lang = "한국어"
else:
    default_lang = "English"

# =========================
# UI TEXT
# =========================

TEXT = {
    "English": {
        "title": "🌿 GreenNote AI",
        "subtitle": "Turn YouTube videos into beautiful notes, mindmaps, quizzes and flashcards.",
        "cache": "Previously summarized videos load instantly from cache.",
        "placeholder": "Paste a YouTube link here...",
        "button": "✨ Create Note",
        "loading": "Generating AI study notes...",
        "invalid": "Invalid YouTube URL or video ID.",
        "menu": "Menu",
        "home": "Home",
        "note": "Note",
        "mindmap": "Mindmap",
        "quiz": "Quiz",
        "flashcards": "Flashcards",
        "url_card": "📁 Paste a YouTube link",
        "study_card": "🧠 Generate study notes",
        "speed_card": "⚡ Instant loading",
        "summary_title": "AI Study Notes",
        "mindmap_title": "Mindmap"
    },

    "한국어": {
        "title": "🌿 GreenNote AI",
        "subtitle": "유튜브 영상을 보기 좋은 요약 노트, 마인드맵, 퀴즈, 플래시카드로 정리합니다.",
        "cache": "이전에 요약한 영상은 캐시에서 즉시 불러옵니다.",
        "placeholder": "유튜브 링크를 입력하세요...",
        "button": "✨ 노트 생성하기",
        "loading": "AI가 요약 노트를 생성 중입니다...",
        "invalid": "유효하지 않은 유튜브 링크입니다.",
        "menu": "메뉴",
        "home": "홈",
        "note": "노트",
        "mindmap": "마인드맵",
        "quiz": "퀴즈",
        "flashcards": "플래시카드",
        "url_card": "📁 유튜브 링크 입력",
        "study_card": "🧠 AI 요약 노트 생성",
        "speed_card": "⚡ 캐시 기반 즉시 로딩",
        "summary_title": "AI 요약 노트",
        "mindmap_title": "마인드맵"
    }
}

# =========================
# SIDEBAR
# =========================

with st.sidebar:

    st.markdown(
        """
        <h1 style='color:#065f46;'>🌿 GreenNote AI</h1>
        """,
        unsafe_allow_html=True
    )

    language = st.selectbox(
        "Language",
        ["English", "한국어"],
        index=0 if default_lang == "English" else 1
    )

    t = TEXT[language]

    st.markdown("---")

    st.markdown(f"### {t['menu']}")

    st.radio(
        "",
        [
            t["home"],
            t["note"],
            t["mindmap"],
            t["quiz"],
            t["flashcards"]
        ]
    )

# =========================
# CSS
# =========================

st.markdown("""
<style>

html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, sans-serif;
}

.main {
    background-color:#f7faf8;
}

.block-container {
    max-width:1200px;
    padding-top:2rem;
}

.hero-box {
    background:white;
    padding:40px;
    border-radius:28px;
    border:1px solid #d1fae5;
    margin-bottom:40px;
}

.hero-title {
    font-size:72px;
    font-weight:900;
    color:#065f46;
    margin-bottom:24px;
}

.hero-sub {
    background:#dcfce7;
    padding:24px;
    border-radius:22px;
    font-size:22px;
    font-weight:700;
    color:#065f46;
    border-left:8px solid #10b981;
}

.cache-text {
    margin-top:20px;
    font-size:18px;
    color:#64748b;
}

.center-wrap {
    width:100%;
    display:flex;
    justify-content:center;
}

.input-wrap {
    width:100%;
    max-width:1000px;
}

.stTextInput > div > div > input {
    height:68px;
    font-size:22px;
    border-radius:18px;
    border:2px solid #bbf7d0;
}

.stButton > button {
    width:100%;
    height:68px;
    border:none;
    border-radius:18px;
    background:#059669;
    color:white;
    font-size:24px;
    font-weight:800;
}

.card-row {
    display:flex;
    gap:20px;
    margin-top:30px;
    margin-bottom:40px;
    flex-wrap:wrap;
}

.card {
    flex:1;
    min-width:240px;
    padding:24px;
    border-radius:20px;
    font-size:24px;
    font-weight:700;
}

.blue {
    background:#dbeafe;
    color:#1d4ed8;
}

.green {
    background:#dcfce7;
    color:#166534;
}

.yellow {
    background:#fef9c3;
    color:#a16207;
}

.note-box {
    background:white;
    padding:34px;
    border-radius:24px;
    border:1px solid #d1fae5;
    margin-top:40px;
}

.note-title {
    color:#065f46;
    font-size:42px;
    font-weight:900;
    margin-bottom:20px;
}

.note-card {
    background:#f0fdf4;
    border-radius:18px;
    padding:24px;
    margin-bottom:24px;
    border-left:6px solid #10b981;
}

.note-card h3 {
    color:#065f46;
    font-size:28px;
    margin-bottom:12px;
}

.note-card p {
    color:#334155;
    font-size:18px;
    line-height:1.8;
}

.mindmap-wrap {
    margin-top:40px;
    background:white;
    border-radius:28px;
    padding:40px;
    border:1px solid #d1fae5;
    overflow-x:auto;
}

.mindmap-title {
    font-size:42px;
    font-weight:900;
    color:#065f46;
    margin-bottom:30px;
}

.mindmap-center {
    text-align:center;
    font-size:32px;
    font-weight:900;
    color:#065f46;
    margin-bottom:40px;
}

.branch {
    background:#dcfce7;
    color:#065f46;
    padding:18px 24px;
    border-radius:18px;
    margin-bottom:18px;
    font-size:22px;
    font-weight:700;
}

@media (max-width: 768px) {

    .hero-title {
        font-size:44px;
    }

    .hero-sub {
        font-size:18px;
    }

    .stButton > button {
        font-size:20px;
    }

    .card {
        font-size:18px;
    }

    .note-title {
        font-size:32px;
    }

    .branch {
        font-size:18px;
    }
}

</style>
""", unsafe_allow_html=True)

# =========================
# HERO
# =========================

st.markdown(f"""
<div class="hero-box">
    <div class="hero-title">{t['title']}</div>

    <div class="hero-sub">
        {t['subtitle']}
    </div>

    <div class="cache-text">
        {t['cache']}
    </div>
</div>
""", unsafe_allow_html=True)

# =========================
# CENTER INPUT
# =========================

st.markdown('<div class="center-wrap"><div class="input-wrap">', unsafe_allow_html=True)

youtube_url = st.text_input(
    "",
    placeholder=t["placeholder"]
)

generate = st.button(t["button"])

st.markdown('</div></div>', unsafe_allow_html=True)

# =========================
# CARDS
# =========================

st.markdown(f"""
<div class="card-row">
    <div class="card blue">{t['url_card']}</div>
    <div class="card green">{t['study_card']}</div>
    <div class="card yellow">{t['speed_card']}</div>
</div>
""", unsafe_allow_html=True)

# =========================
# FUNCTIONS
# =========================

def extract_video_id(url):

    try:
        parsed_url = urlparse(url)

        if parsed_url.hostname == "youtu.be":
            return parsed_url.path[1:]

        if parsed_url.hostname in [
            "www.youtube.com",
            "youtube.com",
            "m.youtube.com"
        ]:

            if parsed_url.path == "/watch":
                return parse_qs(parsed_url.query).get("v", [None])[0]

            if parsed_url.path.startswith("/shorts/"):
                return parsed_url.path.split("/")[2]

            if parsed_url.path.startswith("/embed/"):
                return parsed_url.path.split("/")[2]

        return None

    except:
        return None


def get_cache_path(video_id, lang):
    cache_key = hashlib.md5(f"{video_id}_{lang}".encode()).hexdigest()
    return f"{CACHE_DIR}/{cache_key}.json"


def load_cache(video_id, lang):

    cache_path = get_cache_path(video_id, lang)

    if os.path.exists(cache_path):

        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)

    return None


def save_cache(video_id, lang, data):

    cache_path = get_cache_path(video_id, lang)

    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# =========================
# GENERATE
# =========================

if generate and youtube_url:

    video_id = extract_video_id(youtube_url)

    if not video_id:
        st.error(t["invalid"])
        st.stop()

    cached = load_cache(video_id, language)

    if cached:

        result = cached

    else:

        with st.spinner(t["loading"]):

            preferred_languages = [
                "en",
                "ko",
                "ja",
                "es",
                "fr",
                "de"
            ]

            transcript = None

            for lang_code in preferred_languages:

                try:
                    transcript = YouTubeTranscriptApi.get_transcript(
                        video_id,
                        languages=[lang_code]
                    )
                    break

                except:
                    continue

            if not transcript:
                st.error("No transcript available.")
                st.stop()

            full_text = " ".join([x["text"] for x in transcript])

            prompt = f"""
            Create study notes from this transcript.

            Return:
            1. title
            2. summary
            3. 8 note sections
            4. simple mindmap branches

            Transcript:
            {full_text[:12000]}
            """

            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            content = response.choices[0].message.content

            sections = content.split("\n\n")

            result = {
                "title": sections[0] if len(sections) > 0 else "",
                "summary": sections[1] if len(sections) > 1 else "",
                "sections": sections[2:10]
            }

            save_cache(video_id, language, result)

    # =========================
    # NOTES
    # =========================

    st.markdown(f"""
    <div class="note-box">
        <div class="note-title">{t['summary_title']}</div>
    """, unsafe_allow_html=True)

    for idx, section in enumerate(result["sections"]):

        lines = section.split("\n")

        title = lines[0] if len(lines) > 0 else ""
        body = " ".join(lines[1:])

        st.markdown(f"""
        <div class="note-card">
            <h3>{title}</h3>
            <p>{body}</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # =========================
    # MINDMAP
    # =========================

    st.markdown(f"""
    <div class="mindmap-wrap">
        <div class="mindmap-title">{t['mindmap_title']}</div>
        <div class="mindmap-center">
            {result['title']}
        </div>
    """, unsafe_allow_html=True)

    for section in result["sections"][:8]:

        short = textwrap.shorten(section, width=80)

        st.markdown(f"""
        <div class="branch">
            🌿 {short}
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
