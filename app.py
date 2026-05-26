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
        "hero": "Turn YouTube videos into clean notes, mindmaps, infographics, quizzes, and flashcards.",
        "cache": "Same video + same language loads instantly from cache.",
        "input": "Paste a YouTube link",
        "generate": "Generate study notes",
        "instant": "Instant loading for repeated videos",
        "empty": "Paste a YouTube link in the sidebar and click Create Note.",
        "cached": "Loaded from cache. OpenAI API was not called.",
        "new_saved": "New summary created and saved.",
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
        "source": "원본 자막",
        "create": "새 노트 만들기",
        "output_language": "결과 언어",
        "youtube_url": "유튜브 링크",
        "create_note": "노트 만들기",
        "hero": "유튜브 영상을 깔끔한 노트, 마인드맵, 인포그래픽, 퀴즈, 플래시카드로 정리합니다.",
        "cache": "같은 영상과 같은 언어는 저장된 결과를 즉시 불러옵니다.",
        "input": "유튜브 링크 입력",
        "generate": "학습 노트 생성",
        "instant": "반복 영상 즉시 로딩",
        "empty": "왼쪽 사이드바에 유튜브 링크를 넣고 노트 만들기를 눌러 주세요.",
        "cached": "저장된 요약을 불러왔습니다. OpenAI API를 다시 호출하지 않았습니다.",
        "new_saved": "새 요약을 만들고 저장했습니다.",
        "getting_transcript": "자막을 가져오는 중...",
        "analyzing": "영상을 정리하는 중...",
        "download": "TXT 다운로드"
    },
    "French": {
        "app_name": "GreenNote AI",
        "menu": "Menu",
        "home": "Accueil",
        "note": "Note",
        "mindmap": "Carte mentale",
        "infographic": "Infographie",
        "quiz": "Quiz",
        "flashcards": "Cartes mémoire",
        "source": "Source",
        "create": "Créer une note",
        "output_language": "Langue de sortie",
        "youtube_url": "Lien YouTube",
        "create_note": "Créer",
        "hero": "Transformez des vidéos YouTube en notes, cartes mentales, infographies, quiz et cartes mémoire.",
        "cache": "La même vidéo dans la même langue se charge instantanément depuis le cache.",
        "input": "Coller un lien YouTube",
        "generate": "Générer des notes",
        "instant": "Chargement instantané",
        "empty": "Collez un lien YouTube dans la barre latérale et cliquez sur Créer.",
        "cached": "Résumé chargé depuis le cache. Aucun appel OpenAI.",
        "new_saved": "Nouveau résumé créé et enregistré.",
        "getting_transcript": "Récupération des sous-titres...",
        "analyzing": "Analyse de la vidéo...",
        "download": "Télécharger TXT"
    },
    "Spanish": {
        "app_name": "GreenNote AI",
        "menu": "Menú",
        "home": "Inicio",
        "note": "Nota",
        "mindmap": "Mapa mental",
        "infographic": "Infografía",
        "quiz": "Quiz",
        "flashcards": "Tarjetas",
        "source": "Fuente",
        "create": "Crear nueva nota",
        "output_language": "Idioma de salida",
        "youtube_url": "Enlace de YouTube",
        "create_note": "Crear nota",
        "hero": "Convierte videos de YouTube en notas, mapas mentales, infografías, quizzes y tarjetas.",
        "cache": "El mismo video y el mismo idioma se cargan al instante desde la caché.",
        "input": "Pega un enlace de YouTube",
        "generate": "Generar notas",
        "instant": "Carga instantánea",
        "empty": "Pega un enlace de YouTube en la barra lateral y haz clic en Crear nota.",
        "cached": "Resumen cargado desde la caché. No se llamó a OpenAI.",
        "new_saved": "Nuevo resumen creado y guardado.",
        "getting_transcript": "Obteniendo subtítulos...",
        "analyzing": "Analizando video...",
        "download": "Descargar TXT"
    },
    "Italian": {
        "app_name": "GreenNote AI",
        "menu": "Menu",
        "home": "Home",
        "note": "Note",
        "mindmap": "Mappa mentale",
        "infographic": "Infografica",
        "quiz": "Quiz",
        "flashcards": "Flashcard",
        "source": "Fonte",
        "create": "Crea nuova nota",
        "output_language": "Lingua di output",
        "youtube_url": "Link YouTube",
        "create_note": "Crea nota",
        "hero": "Trasforma video YouTube in note, mappe mentali, infografiche, quiz e flashcard.",
        "cache": "Lo stesso video nella stessa lingua viene caricato subito dalla cache.",
        "input": "Incolla un link YouTube",
        "generate": "Genera note",
        "instant": "Caricamento immediato",
        "empty": "Incolla un link YouTube nella barra laterale e clicca Crea nota.",
        "cached": "Riassunto caricato dalla cache. Nessuna chiamata OpenAI.",
        "new_saved": "Nuovo riassunto creato e salvato.",
        "getting_transcript": "Recupero sottotitoli...",
        "analyzing": "Analisi del video...",
        "download": "Scarica TXT"
    }
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
    padding-top: 1.5rem;
    max-width: 1120px;
}

.main-title {
    font-size: clamp(34px, 6vw, 58px);
    font-weight: 900;
    color: #064e3b;
    line-height: 1.18;
}

.soft-card {
    background: #ffffff;
    border: 1px solid #d1fae5;
    border-radius: 26px;
    padding: clamp(20px, 4vw, 34px);
    box-shadow: 0 12px 34px rgba(6, 78, 59, 0.08);
    margin-bottom: 22px;
}

.green-box {
    background: #ecfdf5;
    border-left: 6px solid #10b981;
    border-radius: 18px;
    padding: 18px;
    font-weight: 750;
    color: #065f46;
    margin: 16px 0;
    font-size: clamp(16px, 2.5vw, 22px);
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

.section-title {
    font-size: clamp(20px, 4vw, 28px);
    font-weight: 900;
    color: #064e3b;
}

.info-card {
    background: linear-gradient(180deg, #ffffff 0%, #f0fdf4 100%);
    border: 1px solid #bbf7d0;
    border-radius: 22px;
    padding: 22px;
    min-height: 180px;
    box-shadow: 0 10px 26px rgba(6, 78, 59, 0.07);
    margin-bottom: 16px;
}

.flash-card {
    background: #ffffff;
    border: 1px solid #d1fae5;
    border-radius: 20px;
    padding: 22px;
    margin-bottom: 16px;
}

@media (max-width: 768px) {
    .block-container {
        padding-left: 1rem;
        padding-right: 1rem;
    }

    .soft-card {
        border-radius: 20px;
        padding: 20px;
    }

    .green-box {
        font-size: 16px;
    }

    [data-testid="stHorizontalBlock"] {
        flex-direction: column;
    }

    [data-testid="column"] {
        width: 100% !important;
        flex: 1 1 100% !important;
        margin-bottom: 0.75rem;
    }

    .main-title {
        font-size: 36px;
    }
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
        r"(?:youtu\\.be/)([a-zA-Z0-9_-]{11})",
        r"(?:shorts/)([a-zA-Z0-9_-]{11})",
        r"(?:embed/)([a-zA-Z0-9_-]{11})"
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    if re.fullmatch(r"[a-zA-Z0-9_-]{11}", url):
        return url

    raise ValueError("Invalid YouTube URL or video ID.")


def seconds_to_mmss(seconds):
    seconds = int(seconds)
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def youtube_link(video_id, seconds):
    return f"https://youtu.be/{video_id}?t={int(seconds)}"


def cache_key(video_id, output_language):
    raw = f"{video_id}_{output_language}_mobile_i18n_v1"
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
            {"report": report, "transcript_preview": transcript_preview},
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
            raise RuntimeError("Transcript could not be fetched.") from e

    if transcript is None:
        raise RuntimeError("No available transcript found.")

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
        line = f"[{item['time']} | {item['url']} | {item['seconds']} seconds] {item['text']}"
        current.append(line)
        current_len += len(line)

        if current_len >= max_chars:
            chunks.append("\\n".join(current))
            current = []
            current_len = 0

    if current:
        chunks.append("\\n".join(current))

    return chunks


def analyze_chunk(chunk, index, total, output_language):
    prompt = f"""
You are a careful multilingual YouTube content analyst.

Output language: {output_language}

Rules:
- Write everything only in {output_language}.
- If output language is Korean, use natural Korean, not translation-like Korean.
- Do NOT write HTML, SVG, XML, markdown tables, code, tags, or CSS.
- Plain text only.
- Do not invent unsupported facts.
- Use timeline data exactly when possible.

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
            {"role": "system", "content": f"Plain text only in {output_language}. Never output HTML or code."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.15
    )

    return response.choices[0].message.content


def create_report(partials, output_language):
    combined = "\\n\\n".join(partials)

    prompt = f"""
Create a clean GreenNote AI learning report.

Output language: {output_language}

Important:
- Return ONLY valid JSON.
- All text values must be only in {output_language}.
- If Korean, write like a fluent Korean editor. Avoid awkward translated phrases.
- NEVER include HTML, SVG, XML, CSS, markdown tables, code blocks, angle brackets, or tags.
- Plain human-readable text only.
- Do not invent facts.

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
      "points": ["point 1", "point 2", "point 3", "point 4"]
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
- each note section: 3 to 5 useful points.
- mindmap: 8 to 12 branches.
- infographic: 6 to 8 blocks.
- quiz: 5 questions.
- flashcards: 8 cards.
- Use real timeline_text and timeline_url.

Source analysis:
{combined}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": f"Return valid JSON only. No HTML. Natural text only in {output_language}."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1
    )

    content = response.choices[0].message.content.strip()
    content = content.replace("```json", "").replace("```", "").strip()
    return json.loads(content)


selected_default_language = "English"
if "selected_language" not in st.session_state:
    st.session_state.selected_language = selected_default_language

with st.sidebar:
    lang = st.selectbox(
        "Language / 언어",
        LANGUAGE_OPTIONS,
        index=LANGUAGE_OPTIONS.index(st.session_state.selected_language)
    )
    st.session_state.selected_language = lang
    t = UI_TEXT[lang]

    st.markdown(f"## 🌿 {t['app_name']}")

    page_labels = [
        t["home"], t["note"], t["mindmap"],
        t["infographic"], t["quiz"], t["flashcards"], t["source"]
    ]

    page = st.radio(t["menu"], page_labels, index=0)

    st.divider()
    st.markdown(f"### ✨ {t['create']}")

    youtube_url = st.text_input(t["youtube_url"])
    create_btn = st.button(t["create_note"], type="primary")

    st.caption(t["cache"])


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
    keyword_html = ""
    for keyword in report.get("keywords", [])[:3]:
        keyword_html += f"<span class='keyword'>#{clean_text(keyword)}</span>"
    st.markdown(keyword_html, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


def render_home():
    st.markdown(f"""
    <div class="soft-card">
        <div class="main-title">🌿 {t['app_name']}</div>
        <div class="green-box">{t['hero']}</div>
        <p style="color:#64748b;font-size:17px;">{t['cache']}</p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.info(f"📁 {t['input']}")
    with c2:
        st.success(f"🧠 {t['generate']}")
    with c3:
        st.warning(f"⚡ {t['instant']}")


def render_note(report):
    render_header(report)
    for section in report.get("note_sections", []):
        with st.container(border=True):
            c1, c2 = st.columns([1, 6])
            with c1:
                st.link_button(
                    clean_text(section.get("timeline_text", "00:00")),
                    section.get("timeline_url", "#")
                )
            with c2:
                st.markdown(f"### {clean_text(section.get('emoji', '📌'))} {clean_text(section.get('title', ''))}")
                st.success(clean_text(section.get("key_message", "")))
            for point in section.get("points", []):
                st.markdown(f"- {clean_text(point)}")


def render_mindmap(report):
    render_header(report)
    st.markdown(f"## 🧠 {t['mindmap']}")
    st.success(clean_text(report.get("one_line_summary", "")))

    branches = report.get("mindmap", [])
    cols = st.columns(2)

    for i, branch in enumerate(branches):
        with cols[i % 2]:
            with st.container(border=True):
                st.markdown(f"### {clean_text(branch.get('emoji', '🌿'))} {clean_text(branch.get('topic', ''))}")
                for child in branch.get("children", []):
                    st.markdown(f"- {clean_text(child)}")


def render_infographic(report):
    render_header(report)
    st.markdown(f"## 🖼️ {t['infographic']}")

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
    st.markdown(f"## 🧩 {t['quiz']}")
    for i, quiz in enumerate(report.get("quiz", []), 1):
        with st.expander(f"Q{i}. {clean_text(quiz.get('question', ''))}"):
            for option in quiz.get("options", []):
                st.markdown(f"- {clean_text(option)}")
            st.success(f"Answer: {clean_text(quiz.get('answer', ''))}")
            st.write(clean_text(quiz.get("explanation", "")))


def render_flashcards(report):
    render_header(report)
    st.markdown(f"## 🃏 {t['flashcards']}")
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
    st.markdown(f"## 📚 {t['source']}")
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
    return "\\n".join(lines)


if "report" not in st.session_state:
    st.session_state.report = None

if "transcript_preview" not in st.session_state:
    st.session_state.transcript_preview = []


if create_btn:
    if not youtube_url.strip():
        st.sidebar.error(t["empty"])
    else:
        try:
            video_id = extract_video_id(youtube_url)
            cached = load_cache(video_id, lang)

            if cached:
                st.session_state.report = cached["report"]
                st.session_state.transcript_preview = cached.get("transcript_preview", [])
                st.success(t["cached"])
            else:
                with st.spinner(t["getting_transcript"]):
                    transcript_items = get_transcript(video_id)
                    st.session_state.transcript_preview = transcript_items[:180]

                with st.spinner(t["analyzing"]):
                    chunks = split_transcript(transcript_items)
                    partials = []
                    progress = st.progress(0)

                    for i, chunk in enumerate(chunks):
                        partial = analyze_chunk(chunk, i + 1, len(chunks), lang)
                        partials.append(partial)
                        progress.progress((i + 1) / len(chunks))

                    report = create_report(partials, lang)
                    st.session_state.report = report

                    save_cache(video_id, lang, report, transcript_items[:180])

                st.success(t["new_saved"])

        except Exception as e:
            st.error(f"Error: {e}")


if page == t["home"]:
    render_home()

elif st.session_state.report is None:
    st.markdown(f"""
    <div class="soft-card">
        <div class="main-title">🌿 {t['app_name']}</div>
        <div class="green-box">{t['empty']}</div>
    </div>
    """, unsafe_allow_html=True)

else:
    report = st.session_state.report

    if page == t["note"]:
        render_note(report)
        st.download_button(
            t["download"],
            data=report_to_text(report),
            file_name="greennote_summary.txt",
            mime="text/plain"
        )
    elif page == t["mindmap"]:
        render_mindmap(report)
    elif page == t["infographic"]:
        render_infographic(report)
    elif page == t["quiz"]:
        render_quiz(report)
    elif page == t["flashcards"]:
        render_flashcards(report)
    elif page == t["source"]:
        render_source()
