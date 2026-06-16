import random
import sqlite3
from pathlib import Path

import streamlit as st

DB_PATH = Path("words.db")


@st.cache_resource
def load_words() -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("""
        SELECT w.id, w.word, w.transcription, g.id, g.name
        FROM words w
        JOIN groups g ON w.group_id = g.id
        ORDER BY w.id
    """).fetchall()
    conn.close()
    return [
        {"id": r[0], "word": r[1], "transcription": r[2], "group_id": r[3], "group": r[4]}
        for r in rows
    ]


def pick_next(
    words: list[dict],
    shown: set,
    last_group: int | None,
    exclude_id: int | None = None,
) -> dict | None:
    available = [w for w in words if w["id"] not in shown]
    if exclude_id is not None:
        trimmed = [w for w in available if w["id"] != exclude_id]
        available = trimmed if trimmed else available
    if not available:
        return None
    preferred = [w for w in available if w["group_id"] != last_group]
    return random.choice(preferred if preferred else available)


def advance(words: list[dict], current: dict, reshuffle: bool) -> None:
    if not reshuffle:
        st.session_state.shown.add(current["id"])
    st.session_state.last_group = current["group_id"]
    st.session_state.current = pick_next(
        words,
        st.session_state.shown,
        st.session_state.last_group,
        exclude_id=current["id"] if reshuffle else None,
    )
    st.session_state.revealed = False
    st.session_state.pop("reshuffle", None)


def reset(words: list[dict]) -> None:
    st.session_state.shown = set()
    st.session_state.last_group = None
    st.session_state.current = pick_next(words, set(), None)
    st.session_state.revealed = False
    st.session_state.pop("reshuffle", None)


def render_reshuffle_checkbox() -> bool:
    return st.checkbox("Reshuffle in deck", key="reshuffle")


def render_hidden(words: list[dict], current: dict) -> None:
    if st.button("Reveal transcription", use_container_width=True):
        st.session_state.revealed = True
        st.rerun()

    st.write("")
    col1, col2 = st.columns([1, 2])
    with col1:
        skip_clicked = st.button("Skip", use_container_width=True)
    with col2:
        reshuffle = render_reshuffle_checkbox()

    if skip_clicked:
        advance(words, current, reshuffle)
        st.rerun()


def render_revealed(words: list[dict], current: dict) -> None:
    st.markdown(
        f"<div style='font-size:1.6rem; letter-spacing:0.05em; padding:0.5rem 0'>"
        f"{current['transcription']}</div>",
        unsafe_allow_html=True,
    )
    st.write("")
    if st.button("Next word →", use_container_width=True, type="primary"):
        advance(words, current, st.session_state.get("reshuffle", False))
        st.rerun()

    render_reshuffle_checkbox()


def main() -> None:
    st.set_page_config(page_title="Phonetic Exam", page_icon="🔤")
    st.title("Phonetic Exam")

    words = load_words()

    if "shown" not in st.session_state:
        reset(words)

    current: dict | None = st.session_state.current

    if current is None:
        st.success("You've gone through all words! Well done.")
        if st.button("Start over"):
            reset(words)
            st.rerun()
        return

    done = len(st.session_state.shown)
    total = len(words)
    st.progress(done / total, text=f"{done} / {total} words")

    st.markdown(f"## {current['word']}")
    st.write("")

    if not st.session_state.revealed:
        render_hidden(words, current)
    else:
        render_revealed(words, current)


if __name__ == "__main__":
    main()
