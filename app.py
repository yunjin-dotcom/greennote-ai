import os
import re
import json
import hashlib
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from concurrent.futures import ThreadPoolExecutor, as_completed

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from youtube_transcript_api import YouTubeTranscriptApi

try:
    from supabase import create_client
except Exception:
    create_client = None


load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY", "")
SUPABASE_URL = os.getenv("SUPABASE_URL") or st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY", "")

client = OpenAI(api_key=OPENAI_API_KEY)

supabase = None
if create_client and SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception:
        supabase = None


CACHE_DIR = Path("summary_cache")
CACHE_DIR.mkdir(exist_ok=True)

LANGUAGES = ["English", "Korean", "French", "Spanish", "Italian"]

TEXT = {
    "English": {
        "title": "🌿 GreenNote AI",
        "subtitle": "Turn YouTube videos into clear study notes, mindmaps, quizzes and flashcards.",
        "cache": "Previously summarized videos load instantly from cache.",
        "placeholder": "Paste a YouTube link here...",
        "button": "✨ Create Note",
        "loading_transcript": "Fetching transcript...",
        "loading_ai": "Creating notes in parallel...",
        "cached": "Loaded instantly from cache.",
        "created": "New note created and saved.",
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
        "loading_ai": "AI가 병렬로 노트를 만드는 중...",
        "cached": "저장된 요약을 즉시 불러왔습니다.",
        "created": "새 노트를 생성하고 저장했습니다.",
        "invalid": "유효하지 않은 유튜브 링크입니다.",
        "no_transcript": "이 영상에서 사용할 수 있는 자막을 찾지 못했습니다.",
        "menu": "메뉴",
        "home": "홈",
        "note": "노트",
        "mindmap": "마인드맵",
        "quiz": "퀴즈",
        "flashcards": "플래시카드",
    },
    "French": {
        "title": "🌿 GreenNote AI",
        "subtitle": "Transformez des vidéos YouTube en notes, cartes mentales, quiz et cartes mémoire.",
        "cache": "Les vidéos déjà résumées se chargent instantanément depuis le cache.",
        "placeholder": "Collez un lien YouTube ici...",
        "button": "✨ Créer une note",
        "loading_transcript": "Récupération des sous-titres...",
        "loading_ai": "Création des notes en parallèle...",
        "cached": "Chargé instantanément depuis le cache.",
        "created": "Nouvelle note créée et enregistrée.",
        "invalid": "Lien YouTube invalide.",
        "no_transcript": "Aucun sous-titre disponible pour cette vidéo.",
        "menu": "Menu",
        "home": "Accueil",
        "note": "Note",
        "mindmap": "Carte mentale",
        "quiz": "Quiz",
        "flashcards": "Cartes mémoire",
    },
    "Spanish": {
        "title": "🌿 GreenNote AI",
        "subtitle": "Convierte videos de YouTube en notas, mapas mentales, quizzes y tarjetas.",
        "cache": "Los videos ya resumidos se cargan al instante desde la caché.",
        "placeholder": "Pega un enlace de YouTube aquí...",
        "button": "✨ Crear nota",
        "loading_transcript": "Obteniendo subtítulos...",
        "loading_ai": "Creando notas en paralelo...",
        "cached": "Cargado al instante desde la caché.",
        "created": "Nueva nota creada y guardada.",
        "invalid": "Enlace de YouTube inválido.",
        "no_transcript": "No hay subtítulos disponibles para este video.",
        "menu": "Menú",
        "home": "Inicio",
        "note": "Nota",
        "mindmap": "Mapa mental",
        "quiz": "Quiz",
        "flashcards": "Tarjetas",
    },
    "Italian": {
        "title": "🌿 GreenNote AI",
        "subtitle": "Trasforma video YouTube in note, mappe mentali, quiz e flashcard.",
        "cache": "I video già riassunti si caricano subito dalla cache.",
        "placeholder": "Incolla un link YouTube qui...",
        "button": "✨ Crea nota",
        "loading_transcript": "Recupero sottotitoli...",
        "loading_ai": "Creazione note in parallelo...",
        "cached": "Caricato subito dalla cache.",
        "created": "Nuova nota creata e salvata.",
        "invalid": "Link YouTube non valido.",
        "no_transcript": "Nessun sottotitolo disponibile per questo video.",
        "menu": "Menu",
        "home": "Home",
        "note": "Note",
        "mindmap": "Mappa mentale",
        "quiz": "Quiz",
        "flashcards": "Flashcard",
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


def clean_text(value):
    text = str(value or "")
    text = re.sub(r"<[^>]*>", "", text)
    text = text.replace("```json", "").replace("```", "")
    return text.strip()


def extract_video_id(url: str):
    try:
        url = url.strip()
        parsed = urlparse(url)

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

        if re.fullmatch(r"[a-zA-Z0-9_-]{11}", url):
            return url

        return None

    except Exception:
        return None


def seconds_to_mmss(seconds):
    seconds = int(seconds)
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def youtube_time_link(video_id, seconds):
    return f"https://youtu.be/{video_id}?t={int(seconds)}"


def local_cache_path(video_id, language):
    key = hashlib.md5(f"{video_id}_{language}_parallel_supabase_v1".encode()).hexdigest()
    return CACHE_DIR / f"{key}.json"


def load_local_cache(video_id, language):
    path = local_cache_path(video_id, language)
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def save_local_cache(video_id, language, report):
    path = local_cache_path(video_id, language)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)


def load_supabase_cache(video_id, language):
    if not supabase:
        return None
    try:
        res = (
            supabase.table("summaries")
            .select("report")
            .eq("video_id", video_id)
            .eq("language", language)
            .limit(1)
            .execute()
        )
        if res.data:
            return res.data[0]["report"]
    except Exception:
        return None
    return None


def save_supabase_cache(video_id, language, report):
    if not supabase:
        return
    try:
        supabase.table("summaries").upsert(
            {
                "video_id": video_id,
                "language": language,
                "report": report,
            },
            on_conflict="video_id,language",
        ).execute()
    except Exception:
        pass


def load_cache(video_id, language):
    supa = load_supabase_cache(video_id, language)
    if supa:
        return supa

    local = load_local_cache(video_id, language)
    if local:
        return local

    return None


def save_cache(video_id, language, report):
    save_local_cache(video_id, language, report)
    save_supabase_cache(video_id, language, report)


@st.cache_data(show_spinner=False)
def get_transcript(video_id):
    preferred_languages = [
        "ko", "en", "ja", "es", "fr", "it",
        "de", "pt", "zh-Hans", "zh-Hant",
        "id", "vi", "th", "hi", "ar"
    ]

    transcript = None

    try:
        api = YouTubeTranscriptApi()

        try:
            transcript = api.fetch(video_id, languages=preferred_languages)
        except Exception:
            transcript = None

        if transcript is None:
            try:
                transcript_list = api.list(video_id)

                try:
                    transcript_obj = transcript_list.find_transcript(preferred_languages)
                    transcript = transcript_obj.fetch()
                except Exception:
                    transcript = None

                if transcript is None:
                    try:
                        transcript_obj = transcript_list.find_generated_transcript(preferred_languages)
                        transcript = transcript_obj.fetch()
                    except Exception:
                        transcript = None

                if transcript is None:
                    for transcript_obj in transcript_list:
                        try:
                            transcript = transcript_obj.fetch()
                            break
                        except Exception:
                            continue

            except Exception:
                transcript = None

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


def analyze_chunk(chunk, language, chunk_number, total_chunks):
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
- This is chunk {chunk_number} of {total_chunks}.

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


def analyze_chunks_parallel(chunks, language, max_workers=3):
    results = [None] * len(chunks)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(analyze_chunk, chunk, language, i + 1, len(chunks)): i
            for i, chunk in enumerate(chunks)
        }

        progress = st.progress(0)
        completed = 0

        for future in as_completed(future_map):
            idx = future_map[future]
            results[idx] = future.result()
            completed += 1
            progress.progress(completed / len(chunks))

    return results


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

    st.caption("Supabase cache: " + ("ON" if supabase else "OFF"))


st.title(t["title"])
st.info(t["subtitle"])
st.caption(t["cache"])

youtube_url = st.text_input(
    "",
    placeholder=t["placeholder"],
)

create_button = st.button(t["button"], use_container_width=True)

col1, col2, col3 = st.columns(3)

if language == "Korean":
    col1.info("📁 유튜브 링크 입력")
    col2.success("🧠 학습 노트 생성")
    col3.warning("⚡ 캐시 즉시 로딩")
else:
    col1.info("📁 Paste a YouTube link")
    col2.success("🧠 Generate study notes")
    col3.warning("⚡ Instant cache loading")


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
            partials = analyze_chunks_parallel(chunks, language, max_workers=3)
            report = create_report("\n\n".join(partials), language)

        save_cache(video_id, language, report)
        st.session_state.report = report
        st.success(t["created"])


report = st.session_state.report

if report:
    if page == t["home"]:
        st.subheader(clean_text(report.get("title", "")))
        st.write(clean_text(report.get("summary", "")))

        keywords = report.get("keywords", [])
        if keywords:
            st.write(" | ".join([f"#{clean_text(k)}" for k in keywords]))

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
