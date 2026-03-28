"""
Генерирует графики из результатов прогонов.
Запуск: python build_charts.py (после run_results.json готов)
"""
import json
import plotly.graph_objects as go
from plotly.subplots import make_subplots

with open("run_results.json") as f:
    results = json.load(f)

# Фильтруем успешные
ok = [r for r in results if r.get("scores")]

# ─── График 1: Score по итерациям для всех прогонов ───
fig1 = go.Figure()
colors = ["#2563EB", "#059669", "#DC2626", "#F59E0B", "#7C3AED", "#EC4899"]
for i, r in enumerate(ok):
    fig1.add_trace(go.Scatter(
        x=list(range(1, len(r["scores"]) + 1)),
        y=r["scores"],
        mode="lines+markers+text",
        text=[str(s) for s in r["scores"]],
        textposition="top center",
        name=r["name"],
        line=dict(color=colors[i % len(colors)], width=3),
        marker=dict(size=10),
    ))
fig1.update_layout(
    title="Communication Score по итерациям (все прогоны)",
    xaxis_title="Итерация", yaxis_title="Score (0-100)",
    yaxis=dict(range=[0, 100]), height=500, template="plotly_white",
)
fig1.write_html("chart_scores.html")
print("chart_scores.html saved")

# ─── График 2: Flesch before/after ───
fig2 = go.Figure()
names = [r["name"] for r in ok]
fig2.add_trace(go.Bar(name="До", x=names, y=[r["flesch_before"] for r in ok],
                       marker_color="#FCA5A5", text=[f'{r["flesch_before"]:.0f}' for r in ok], textposition="outside"))
fig2.add_trace(go.Bar(name="После", x=names, y=[r["flesch_after"] for r in ok],
                       marker_color="#6EE7B7", text=[f'{r["flesch_after"]:.0f}' for r in ok], textposition="outside"))
fig2.update_layout(
    title="Flesch Reading Ease: до и после closed loop",
    barmode="group", height=450, template="plotly_white",
    yaxis=dict(range=[0, 60]),
)
fig2.write_html("chart_flesch.html")
print("chart_flesch.html saved")

# ─── График 3: Сводная таблица ───
fig3 = go.Figure(data=[go.Table(
    header=dict(
        values=["Прогон", "Score (start→end)", "Flesch Δ", "Jargon Δ", "Sentiment Δ", "LLM коллов"],
        fill_color="#1E3A5F", font=dict(color="white", size=12), align="left",
    ),
    cells=dict(
        values=[
            [r["name"] for r in ok],
            [f'{r["scores"][0]}→{r["scores"][-1]}' if r["scores"] else "—" for r in ok],
            [f'{r["flesch_before"]:.0f}→{r["flesch_after"]:.0f} (+{r["flesch_after"]-r["flesch_before"]:.0f})' for r in ok],
            [f'{r["jargon_before"]}→{r["jargon_after"]} ({r["jargon_after"]-r["jargon_before"]:+d})' for r in ok],
            [f'{r["sentiment_before"]:.1f}→{r["sentiment_after"]:.1f}' for r in ok],
            [r["calls"] for r in ok],
        ],
        fill_color="#F8FAFC", font=dict(size=11), align="left", height=30,
    ),
)])
fig3.update_layout(title="Сводка всех прогонов", height=350)
fig3.write_html("chart_summary.html")
print("chart_summary.html saved")

print(f"\nВсего успешных прогонов: {len(ok)}")
for r in ok:
    s = r["scores"]
    print(f"  {r['name']}: {s[0]}→{s[-1]} ({s[-1]-s[0]:+d}), Flesch {r['flesch_before']:.0f}→{r['flesch_after']:.0f}, Calls: {r['calls']}")
