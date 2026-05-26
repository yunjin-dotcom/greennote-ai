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

import os
from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

CACHE_DIR = Path("summary_cache")
CACHE_DIR.mkdir(exist_ok=True)

LANGUAGE_OPTIONS = [
    "한국어(Korean)",
    "영어(English)",
    "프랑스어(French)",
    "스페인어(Spanish)",
    "이탈리아어(Italian)"
]

LANGUAGE_MAP = {
    "한국어(Korean)": "Korean",
    "영어(English)": "English",
    "프랑스어(French)": "French",
    "스페인어(Spanish)": "Spanish",
    "이탈리아어(Italian)": "Italian"
}

st.set_page_config(
    page_title="GreenNote AI",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #ecfdf5 0%, #ffffff 100%);
}

.block-container {
    padding-top: 2rem;
    max-width: 1180px;
}

.main-title {
    font-size: 44px;
    font-weight: 900;
    color: #064e3b;
    line-height: 1.25;
}

.soft-card {
    background: #ffffff;
    border: 1px solid #d1fae5;
    border-radius: 24px;
    padding: 28px;
    box-shadow: 0 12px 32px rgba(6, 78, 59, 0.08);
    margin-bottom: 22px;
}

.green-box {
    background: #ecfdf5;
    border-left: 6px solid #10b981;
    border-radius: 18px;
    padding: 18px;
    font-weight: 700;
    color: #065f46;
    margin: 16px 0;
}

.keyword {
    display: inline-block;
    background: #d1fae5;
    color: #065f46;
    border-radius: 999px;
    padding: 8px 14px;
    margin-right: 8px;
    margin-bottom: 8px;
    font-weight: 800;
}

.timeline {
    display: inline-block;
    background: #d1fae5;
    color: #047857 !important;
    border-radius: 999px;
    padding: 6px 11px;
    font-weight: 900;
    text-decoration: none;
    margin-right: 8px;
}

.section-title {
    font-size: 24px;
    font-weight: 900;
    color: #064e3b;
}

.small-muted {
    color: #64748b;
    font-size: 14px;
}

.mind-branch {
    background: #ffffff;
    border: 1px solid #d1fae5;
    border-left: 7px solid #10b981;
    border-radius: 20px;
    padding: 22px;
    margin-bottom: 16px;
    box-shadow: 0 8px 22px rgba(6, 78, 59, 0.06);
}

.info-card {
    background: linear-gradient(180deg, #ffffff 0%, #f0fdf4 100%);
    border: 1px solid #bbf7d0;
    border-radius: 22px;
    padding: 24px;
    min-height: 210px;
    box-shadow: 0 10px 26px rgba(6, 78, 59, 0.07);
}

.quiz-card {
    background: #ffffff;
    border: 1px solid #d1fae5;
    border-radius: 18px;
    padding: 18px;
    margin-bottom: 14px;
}

.flash-card {
    background: #ffffff;
    border: 1px solid #d1fae5;
    border-radius: 20px;
    padding: 22px;
    margin-bottom: 16px;
}
</style>
""", unsafe_allow_html=True)


def clean_text(value):
    text = str(value or "")
    text = re.sub(r"<[^>]*>", "", text)
    text = text.replace("```json", "").replace("```", "")
    text = text.replace("&lt;", "").replace("&gt;", "")
    return text.strip()


def extract_video_id(url):
    patterns = [
        r"(?:v=)([a-zA-Z0-9_-]{11})",
        r"(?:youtu\.be/)([a-zA-Z0-9_-]{11})",
        r"(?:shorts/)([a-zA-Z0-9_-]{11})",
        r"(?:embed/)([a-zA-Z0-9_-]{11})"
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    if re.fullmatch(r"[a-zA-Z0-9_-]{11}", url):
        return url

    raise ValueError("유효한 유튜브 링크 또는 영상 ID가 아닙니다.")


def seconds_to_mmss(seconds):
    seconds = int(seconds)
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def youtube_link(video_id, seconds):
    return f"https://youtu.be/{video_id}?t={int(seconds)}"


def cache_key(video_id, output_language):
    raw = f"{video_id}_{output_language}_stable_v1"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def cache_path(video_id, output_language):
    return CACHE_DIR / f"{cache_key(video_id, output_language)}.json"


def load_cache(video_id, output_language):
    path = cache_path(video_id, output_language)
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def save_cache(video_id, output_language, report, transcript_preview):
    path = cache_path(video_id, output_language)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "report": report,
                "transcript_preview": transcript_preview
            },
            f,
            ensure_ascii=False,
            indent=2
        )


@st.cache_data(show_spinner=False)
def get_transcript(video_id):
    ytt_api = YouTubeTranscriptApi()

    preferred_languages = [
        "ko", "en", "es", "fr", "it",
        "ja", "zh-Hans", "zh-Hant",
        "de", "pt", "id", "vi", "th", "hi"
    ]

    transcript = None

    try:
        transcript = ytt_api.fetch(video_id, languages=preferred_languages)
    except Exception:
        pass

    if transcript is None:
        try:
            transcript_list = ytt_api.list(video_id)

            try:
                transcript_obj = transcript_list.find_transcript(preferred_languages)
                transcript = transcript_obj.fetch()
            except Exception:
                try:
                    transcript_obj = transcript_list.find_generated_transcript(preferred_languages)
                    transcript = transcript_obj.fetch()
                except Exception:
                    for transcript_obj in transcript_list:
                        try:
                            transcript = transcript_obj.fetch()
                            break
                        except Exception:
                            continue
        except Exception as e:
            raise RuntimeError("자막을 가져올 수 없습니다. 자막이 없거나 비공개일 수 있습니다.") from e

    if transcript is None:
        raise RuntimeError("사용 가능한 자막을 찾지 못했습니다.")

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
        line = f"[{item['time']} | {item['url']} | {item['seconds']}초] {item['text']}"
        current.append(line)
        current_len += len(line)

        if current_len >= max_chars:
            chunks.append("\n".join(current))
            current = []
            current_len = 0

    if current:
        chunks.append("\n".join(current))

    return chunks


def analyze_chunk(chunk, index, total, output_language):
    prompt = f"""
You are a careful multilingual YouTube content analyst.

Output language: {output_language}

Rules:
- No matter what language the transcript is in, write everything only in {output_language}.
- If output language is Korean, use natural Korean, not translation-like Korean.
- Do NOT write HTML, SVG, XML, markdown tables, code, tags, or CSS.
- Write plain text only.
- Do not invent anything not supported by the transcript.
- Use the timeline data exactly when possible.

Analyze transcript part {index}/{total}.

Extract:
1. Important ideas
2. Natural section titles
3. Timeline points
4. Key examples and explanations
5. Main branches for a mindmap
6. Infographic-worthy ideas
7. Quiz and flashcard candidates

Transcript:
{chunk}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": f"Output only plain natural language in {output_language}. Never output HTML or code."
            },
            {"role": "user", "content": prompt}
        ],
        temperature=0.15
    )

    return response.choices[0].message.content


def create_report(partials, output_language):
    combined = "\n\n".join(partials)

    prompt = f"""
Create a clean GreenNote AI learning report.

Output language: {output_language}

Important:
- Return ONLY valid JSON.
- All text values must be only in {output_language}.
- If Korean, write like a fluent Korean editor. Avoid awkward translated phrases.
- NEVER include HTML, SVG, XML, CSS, markdown tables, code blocks, angle brackets, or tags.
- Use plain human-readable text only.
- Do not invent facts.
- Keep it useful, specific, and easy to read.

JSON schema:
{{
  "video_title": "clear natural title",
  "one_line_summary": "one clear sentence",
  "keywords": ["keyword1", "keyword2", "keyword3"],
  "note_sections": [
    {{
      "timeline_text": "MM:SS",
      "timeline_url": "https://youtu.be/videoID?t=seconds",
      "emoji": "emoji",
      "title": "natural section title",
      "key_message": "one strong takeaway sentence",
      "points": [
        "detailed point",
        "detailed point",
        "detailed point",
        "detailed point"
      ]
    }}
  ],
  "mindmap": [
    {{
      "emoji": "emoji",
      "topic": "main branch title",
      "children": ["sub idea 1", "sub idea 2", "sub idea 3"]
    }}
  ],
  "infographic": [
    {{
      "number": "1",
      "icon": "emoji",
      "title": "short visual title",
      "summary": "short but meaningful explanation"
    }}
  ],
  "quiz": [
    {{
      "question": "question",
      "options": ["A", "B", "C", "D"],
      "answer": "correct option text",
      "explanation": "short explanation"
    }}
  ],
  "flashcards": [
    {{
      "front": "term or question",
      "back": "clear explanation"
    }}
  ]
}}

Quality:
- note_sections: 7 to 10 sections.
- each note section must have 3 to 5 useful points.
- mindmap: 8 to 12 branches.
- infographic: 6 to 8 blocks.
- quiz: 5 questions.
- flashcards: 8 cards.
- Use real timeline_text and timeline_url.
- Make section titles natural, concise, and not robotic.

Source analysis:
{combined}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": f"Return valid JSON only. No HTML. No code. Natural text only in {output_language}."
            },
            {"role": "user", "content": prompt}
        ],
        temperature=0.1
    )

    content = response.choices[0].message.content.strip()
    content = content.replace("```json", "").replace("```", "").strip()

    return json.loads(content)


def render_home():
    st.markdown("""
    <div class="soft-card">
        <div class="main-title">🌿 GreenNote AI</div>
        <div class="green-box">
            유튜브 영상을 자연스러운 요약 노트, 마인드맵, 인포그래픽, 퀴즈, 플래시카드로 정리합니다.
        </div>
        <p class="small-muted">
            같은 영상과 같은 언어는 캐시에 저장되어 다음부터 즉시 불러옵니다.
        </p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)

    with c1:
        st.info("📁 YouTube 링크 입력")
    with c2:
        st.success("🧠 노트 + 마인드맵 생성")
    with c3:
        st.warning("⚡ 같은 영상은 즉시 로딩")


def render_header(report):
    st.markdown('<div class="soft-card">', unsafe_allow_html=True)

    st.markdown(
        f"<div class='main-title'>{clean_text(report.get('video_title', 'Untitled'))}</div>",
        unsafe_allow_html=True
    )

    st.markdown(
        f"<div class='green-box'>💡 {clean_text(report.get('one_line_summary', ''))}</div>",
        unsafe_allow_html=True
    )

    keywords = report.get("keywords", [])
    keyword_html = ""
    for keyword in keywords[:3]:
        keyword_html += f"<span class='keyword'>#{clean_text(keyword)}</span>"

    st.markdown(keyword_html, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


def render_note(report):
    render_header(report)

    for section in report.get("note_sections", []):
        st.markdown('<div class="soft-card">', unsafe_allow_html=True)

        col1, col2 = st.columns([1, 8])
        with col1:
            st.link_button(
                clean_text(section.get("timeline_text", "00:00")),
                section.get("timeline_url", "#")
            )

        with col2:
            st.markdown(
                f"### {clean_text(section.get('emoji', '📌'))} {clean_text(section.get('title', ''))}"
            )
            st.success(clean_text(section.get("key_message", "")))

        for point in section.get("points", []):
            st.markdown(f"- {clean_text(point)}")

        st.markdown('</div>', unsafe_allow_html=True)


def render_mindmap(report):
    render_header(report)

    st.markdown("## 🧠 Mindmap")

    branches = report.get("mindmap", [])

    center = clean_text(report.get("one_line_summary", "핵심 주제"))

    st.markdown(
        f"""
        <div style="
            background:#ecfdf5;
            border:2px solid #10b981;
            border-radius:24px;
            padding:24px;
            text-align:center;
            font-size:22px;
            font-weight:900;
            color:#064e3b;
            margin-bottom:24px;">
            중심 주제: {center}
        </div>
        """,
        unsafe_allow_html=True
    )

    cols = st.columns(2)

    for i, branch in enumerate(branches):
        with cols[i % 2]:
            with st.container(border=True):
                st.markdown(
                    f"### {clean_text(branch.get('emoji', '🌿'))} {clean_text(branch.get('topic', ''))}"
                )
                for child in branch.get("children", []):
                    st.markdown(f"- {clean_text(child)}")


def render_infographic(report):
    render_header(report)

    st.markdown("## 🖼️ Infographic Summary")

    items = report.get("infographic", [])

    cols = st.columns(2)

    for i, item in enumerate(items):
        with cols[i % 2]:
            st.markdown(
                f"""
                <div class="info-card">
                    <h2>{clean_text(item.get('icon', '🌿'))} {clean_text(item.get('number', ''))}. {clean_text(item.get('title', ''))}</h2>
                    <p style="font-size:16px;line-height:1.7;color:#374151;">
                        {clean_text(item.get('summary', ''))}
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )


def render_quiz(report):
    render_header(report)

    st.markdown("## 🧩 Quiz")

    for i, quiz in enumerate(report.get("quiz", []), 1):
        with st.expander(f"Q{i}. {clean_text(quiz.get('question', ''))}"):
            for option in quiz.get("options", []):
                st.markdown(f"- {clean_text(option)}")
            st.success(f"정답: {clean_text(quiz.get('answer', ''))}")
            st.write(clean_text(quiz.get("explanation", "")))


def render_flashcards(report):
    render_header(report)

    st.markdown("## 🃏 Flashcards")

    for i, card in enumerate(report.get("flashcards", []), 1):
        with st.expander(f"Card {i}: {clean_text(card.get('front', ''))}"):
            st.markdown(
                f"""
                <div class="flash-card">
                    <h3>{clean_text(card.get('front', ''))}</h3>
                    <p>{clean_text(card.get('back', ''))}</p>
                </div>
                """,
                unsafe_allow_html=True
            )


def render_source():
    st.markdown("## 📚 Source Transcript")

    for item in st.session_state.get("transcript_preview", []):
        st.markdown(f"**[{item['time']}]** {clean_text(item['text'])}")


def report_to_text(report):
    lines = []
    lines.append(clean_text(report.get("video_title", "")))
    lines.append("")
    lines.append(clean_text(report.get("one_line_summary", "")))
    lines.append("")
    lines.append("Keywords: " + ", ".join([clean_text(k) for k in report.get("keywords", [])]))
    lines.append("")

    for section in report.get("note_sections", []):
        lines.append("")
        lines.append(f"{section.get('timeline_text', '')} {clean_text(section.get('title', ''))}")
        lines.append(section.get("timeline_url", ""))
        for point in section.get("points", []):
            lines.append(f"- {clean_text(point)}")

    return "\n".join(lines)


with st.sidebar:
    st.markdown("## 🌿 GreenNote AI")

    page = st.radio(
        "Menu",
        ["Home", "Note", "Mindmap", "Infographic", "Quiz", "Flashcards", "Source"],
        index=0
    )

    st.divider()

    st.markdown("### ✨ Create New Note")

    selected_language_label = st.selectbox(
        "Output Language",
        LANGUAGE_OPTIONS,
        index=0
    )

    output_language = LANGUAGE_MAP[selected_language_label]

    youtube_url = st.text_input("YouTube URL")

    create_btn = st.button("Create Note", type="primary")

    st.caption("같은 영상 + 같은 언어는 캐시에서 즉시 불러옵니다.")


if "report" not in st.session_state:
    st.session_state.report = None

if "transcript_preview" not in st.session_state:
    st.session_state.transcript_preview = []


if create_btn:
    if not youtube_url.strip():
        st.sidebar.error("유튜브 링크를 입력해 주세요.")
    else:
        try:
            video_id = extract_video_id(youtube_url)

            cached = load_cache(video_id, output_language)

            if cached:
                st.session_state.report = cached["report"]
                st.session_state.transcript_preview = cached.get("transcript_preview", [])
                st.success("⚡ 저장된 요약을 불러왔습니다. OpenAI API를 다시 호출하지 않았습니다.")

            else:
                with st.spinner("자막을 가져오는 중..."):
                    transcript_items = get_transcript(video_id)
                    st.session_state.transcript_preview = transcript_items[:180]

                with st.spinner("처음 보는 영상입니다. AI가 내용을 정리하는 중..."):
                    chunks = split_transcript(transcript_items)

                    partials = []
                    progress = st.progress(0)

                    for i, chunk in enumerate(chunks):
                        partial = analyze_chunk(
                            chunk=chunk,
                            index=i + 1,
                            total=len(chunks),
                            output_language=output_language
                        )
                        partials.append(partial)
                        progress.progress((i + 1) / len(chunks))

                    report = create_report(partials, output_language)

                    st.session_state.report = report

                    save_cache(
                        video_id=video_id,
                        output_language=output_language,
                        report=report,
                        transcript_preview=transcript_items[:180]
                    )

                st.success("✅ 새 요약을 만들고 저장했습니다.")

        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")


if page == "Home":
    render_home()

elif st.session_state.report is None:
    st.markdown("""
    <div class="soft-card">
        <div class="main-title">Create a new GreenNote 🌿</div>
        <div class="green-box">
            왼쪽 사이드바에 유튜브 링크를 넣고 Create Note를 눌러 주세요.
        </div>
    </div>
    """, unsafe_allow_html=True)

else:
    report = st.session_state.report

    if page == "Note":
        render_note(report)
        st.download_button(
            "📄 Download TXT",
            data=report_to_text(report),
            file_name="greennote_summary.txt",
            mime="text/plain"
        )

    elif page == "Mindmap":
        render_mindmap(report)

    elif page == "Infographic":
        render_infographic(report)

    elif page == "Quiz":
        render_quiz(report)

    elif page == "Flashcards":
        render_flashcards(report)

    elif page == "Source":
        render_source()