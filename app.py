"""
CB Communication Closed Loop — Streamlit Demo.
Run: streamlit run app.py
"""

import os

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from personas import PERSONAS
from channels import CHANNELS
from engine import run_closed_loop
from llm import get_call_count, reset_call_count
from sample_releases import SAMPLE_RELEASES, DEFAULT_RELEASE

st.set_page_config(page_title="CB Closed Loop", page_icon="🔄", layout="wide")

st.markdown("# 🔄 CB Communication Closed Loop")
st.markdown("Автоматическая оптимизация пресс-релизов ЦБ через интервью с синтетическими персонами")

tab_loop, tab_channels, tab_compare, tab_log = st.tabs([
    "🔄 Closed Loop", "📡 Каналы", "📊 Сравнение", "📋 Лог"
])

# ─── Tab 1: Closed Loop ───
with tab_loop:
    release_key = st.selectbox("Пресс-релиз", list(SAMPLE_RELEASES.keys()))
    release_text = SAMPLE_RELEASES[release_key]
    st.text_area("Текст", release_text, height=180, disabled=True)

    col1, col2, col3 = st.columns(3)
    max_iter = col1.slider("Макс. итераций", 1, 10, 3)
    persona_keys = col2.multiselect(
        "Персоны",
        list(PERSONAS.keys()),
        default=list(PERSONAS.keys()),
        format_func=lambda k: f"{PERSONAS[k]['name']} ({PERSONAS[k]['age']}, {PERSONAS[k]['city']})",
    )
    adaptive = col3.checkbox("Adaptive интервью (LLM-модератор)", value=False,
                              help="Scripted = фиксированные вопросы (стабильно). Adaptive = LLM генерирует follow-up (ближе к реальной фокус-группе).")

    if st.button("🚀 Запустить Closed Loop", type="primary", use_container_width=True):
        if not persona_keys:
            st.warning("Выберите хотя бы одну персону")
        else:
            reset_call_count()
            selected = {k: PERSONAS[k] for k in persona_keys}
            with st.spinner(f"Итерации closed loop ({max_iter} макс.)..."):
                result = run_closed_loop(
                    release_text, selected,
                    max_iterations=max_iter,
                    adaptive_interview=adaptive,
                )
                st.session_state["loop_result"] = result
                st.session_state["llm_calls"] = get_call_count()

    if "loop_result" in st.session_state:
        result = st.session_state["loop_result"]

        # Metrics row
        mc = st.columns(4)
        mc[0].metric("Итераций", len(result.iterations))
        mc[1].metric("Score (старт)", f"{result.scores[0]:.0f}/100" if result.scores else "—")
        mc[2].metric("Score (финал)", f"{result.scores[-1]:.0f}/100" if result.scores else "—")
        mc[3].metric("LLM-коллов", st.session_state.get("llm_calls", "—"))

        # Score chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=list(range(1, len(result.scores) + 1)),
            y=result.scores,
            mode="lines+markers+text",
            text=[f"{s:.0f}" for s in result.scores],
            textposition="top center",
            line=dict(color="#3B82F6", width=3),
            marker=dict(size=12),
        ))
        fig.update_layout(
            title="Communication Score по итерациям",
            xaxis_title="Итерация", yaxis_title="Score (0-100)",
            yaxis=dict(range=[0, 100]), height=400,
        )
        st.plotly_chart(fig, use_container_width=True)

        # Readability metrics
        if result.original_readability and result.final_readability:
            st.subheader("Объективные метрики читаемости (Flesch-Kincaid)")
            rc = st.columns(4)
            orig_r = result.original_readability
            final_r = result.final_readability
            rc[0].metric("Flesch (0-100)", f"{final_r['flesch_ru']:.0f}",
                         delta=f"{final_r['flesch_ru'] - orig_r['flesch_ru']:+.0f}")
            rc[1].metric("Ср. длина предложения", f"{final_r['avg_sentence_length']:.0f} слов",
                         delta=f"{final_r['avg_sentence_length'] - orig_r['avg_sentence_length']:+.0f}",
                         delta_color="inverse")
            rc[2].metric("Терминов ЦБ", f"{final_r['jargon_count']}",
                         delta=f"{final_r['jargon_count'] - orig_r['jargon_count']:+d}",
                         delta_color="inverse")
            rc[3].metric("Сложных слов", f"{final_r['complex_word_ratio']:.1%}",
                         delta=f"{final_r['complex_word_ratio'] - orig_r['complex_word_ratio']:+.1%}",
                         delta_color="inverse")

        # Before/After
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("### 📝 Оригинал")
            st.text_area("", result.original_text, height=250, disabled=True, key="orig")
        with col_b:
            st.markdown("### ✅ Оптимизированный")
            st.text_area("", result.final_text, height=250, disabled=True, key="final")

        # Iteration details
        for it in result.iterations:
            score = it.analysis.get("communication_score", "?")
            with st.expander(f"Итерация {it.iteration} — Score: {score}"):
                # Problems
                problems = it.analysis.get("problems", [])
                if problems:
                    st.markdown("**Проблемы:**")
                    for p in problems:
                        st.markdown(
                            f"- *\"{p.get('phrase', '')}\"* — {p.get('issue', '')}  \n"
                            f"  → {p.get('suggestion', '')}"
                        )

                # Strengths
                strengths = it.analysis.get("strengths", [])
                if strengths:
                    st.markdown("**Сильные стороны:**")
                    for s in strengths:
                        st.markdown(f"- {s}")

                st.divider()

                # Interview excerpts
                for iv in it.interviews:
                    st.markdown(f"**{iv.persona_name}:**")
                    for turn in iv.turns[:3]:  # first 3 questions
                        st.markdown(f"> **В:** {turn.question}")
                        st.markdown(f"> {turn.answer}")
                    if len(iv.turns) > 3:
                        st.caption(f"... ещё {len(iv.turns) - 3} вопросов")
                    st.divider()

# ─── Tab 2: Channels ───
with tab_channels:
    st.markdown("### Один релиз → разные тексты для разных каналов ЦБ")
    st.markdown("Каждый канал оптимизируется через свой closed loop с персонами целевой аудитории")

    ch_release_key = st.selectbox("Пресс-релиз", list(SAMPLE_RELEASES.keys()), key="ch_rel")
    ch_release_text = SAMPLE_RELEASES[ch_release_key]

    selected_channels = st.multiselect(
        "Каналы",
        list(CHANNELS.keys()),
        default=list(CHANNELS.keys())[:3],
        format_func=lambda k: CHANNELS[k]["name"],
    )

    if st.button("📡 Генерировать для каналов", type="primary", use_container_width=True):
        channel_results = {}
        for ch_key in selected_channels:
            ch = CHANNELS[ch_key]
            personas_subset = {k: PERSONAS[k] for k in ch["audience_persona_keys"]}
            with st.spinner(f"Оптимизируем для: {ch['name']}..."):
                ch_result = run_closed_loop(
                    ch_release_text,
                    personas_subset,
                    max_iterations=3,
                    style_guide=ch["style_guide"],
                )
                channel_results[ch_key] = ch_result
        st.session_state["channel_results"] = channel_results

    if "channel_results" in st.session_state:
        for ch_key, ch_result in st.session_state["channel_results"].items():
            ch = CHANNELS[ch_key]
            final_score = ch_result.scores[-1] if ch_result.scores else 0
            with st.expander(f"📌 {ch['name']} — Score: {final_score:.0f}"):
                st.markdown(f"**Аудитория:** {ch['description']}")
                st.markdown(f"**Стиль:** _{ch['style_guide']}_")
                st.markdown("**Персоны:** " + ", ".join(
                    f"{PERSONAS[k]['name']} ({PERSONAS[k]['age']})"
                    for k in ch["audience_persona_keys"]
                ))
                st.text_area(
                    "Оптимизированный текст", ch_result.final_text,
                    height=200, disabled=True, key=f"ch_{ch_key}",
                )

# ─── Tab 3: Compare ───
with tab_compare:
    if "channel_results" in st.session_state:
        ch_results = st.session_state["channel_results"]

        names = [CHANNELS[k]["name"] for k in ch_results]
        scores = [r.scores[-1] if r.scores else 0 for r in ch_results.values()]

        fig = go.Figure(data=[go.Bar(
            x=names, y=scores,
            marker_color=["#3B82F6", "#10B981", "#F59E0B", "#EC4899"][:len(names)],
            text=[f"{s:.0f}" for s in scores],
            textposition="outside",
        )])
        fig.update_layout(
            title="Communication Score по каналам",
            yaxis=dict(range=[0, 100]), height=400,
        )
        st.plotly_chart(fig, use_container_width=True)

        cols = st.columns(len(ch_results))
        for i, (ch_key, ch_result) in enumerate(ch_results.items()):
            with cols[i]:
                st.markdown(f"**{CHANNELS[ch_key]['name']}**")
                st.text_area("", ch_result.final_text, height=300, disabled=True, key=f"cmp_{ch_key}")
    else:
        st.info("Сначала запустите генерацию по каналам во вкладке «Каналы»")

# ─── Tab 4: Log ───
with tab_log:
    if "loop_result" in st.session_state:
        st.json(st.session_state["loop_result"].to_dict())
    elif "channel_results" in st.session_state:
        for ch_key, ch_result in st.session_state["channel_results"].items():
            with st.expander(f"Лог: {CHANNELS[ch_key]['name']}"):
                st.json(ch_result.to_dict())
    else:
        st.info("Запустите Closed Loop или генерацию по каналам для просмотра лога")
