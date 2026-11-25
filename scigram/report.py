"""
Markdown report generator for SciGram manuscript scans.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Any


def render_markdown_report(result: Dict[str, Any], title: str = "Manuscript Scan") -> str:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    bd = result["breakdown_pct"]
    ds = result["document_structure"]
    dims = ds["dimensions"]
    burst = ds["burstiness"]

    lines = [
        f"# SciGram AI & Scientific Structure Report — {title}",
        f"*Generated: {ts} | Words: {result['word_count']} | Passages: {result['passage_count']} | Sentences: {result['sentence_count']}*",
        "",
        "## 1. Executive Verdict",
        f"- **Overall Classification:** **{result['overall_verdict']}** (Composite AI Score: **{result['overall_ai_pct']}%**)",
        f"- **Human-Written:** {bd['human']}%",
        f"- **AI-Assisted / Polished:** {bd['ai_assisted']}%",
        f"- **AI-Generated:** {bd['ai_generated']}%",
        "",
        "## 2. Scientific Structure & Cadence Profile",
        f"- **Sentence Burstiness (CV):** `{burst['cv']:.2f}` *(Human target: >= 0.40; Mean {burst['mean_words']} ± {burst['std_words']} words/sentence)*",
        f"- **Empirical Anchor Density:** `{ds['anchors_per_100w']:.2f}` per 100 words *(Quantitative values, stats, citations, identifiers)*",
        "",
        "| Structural Dimension | Risk Score (0–100) | Interpretation |",
        "| :--- | :---: | :--- |",
        f"| Rhythm Uniformity (Low Burstiness) | {dims['rhythm_uniformity']}% | {'High uniformity' if dims['rhythm_uniformity'] >= 50 else 'Natural variation'} |",
        f"| Participial `-ing` Summary Tails | {dims['participial_tails']}% | {'Frequent trailing clauses' if dims['participial_tails'] >= 30 else 'Clean sentence endings'} |",
        f"| Mechanical Discourse Starters | {dims['formulaic_transitions']}% | {'Overused signposts' if dims['formulaic_transitions'] >= 30 else 'Organic transitions'} |",
        f"| Excess LLM Vocabulary | {dims['excess_llm_vocab']}% | {'High AI diction' if dims['excess_llm_vocab'] >= 30 else 'Direct scientific diction'} |",
        f"| Rhetorical Boilerplate Templates | {dims['rhetorical_boilerplate']}% | {'Stock LLM phrases found' if dims['rhetorical_boilerplate'] >= 25 else 'Minimal boilerplate'} |",
        f"| Parallel Triadic Symmetry | {dims['triadic_symmetry']}% | {'Rule-of-three lists' if dims['triadic_symmetry'] >= 25 else 'Low symmetry'} |",
        f"| Empirical Specificity Deficit | {dims['specificity_deficit']}% | {'Add quantitative anchors' if dims['specificity_deficit'] >= 55 else 'Well-anchored'} |",
        "",
        "## 3. Top Manuscript Revision Priorities",
    ]

    for rec in result.get("recommendations", []):
        lines.append(f"- **[{rec['badge']}] {rec['title']}:** {rec['body']}")

    lines.append("")
    lines.append("## 4. Passage-by-Passage Breakdown")

    badge_map = {
        "human": "HUMAN-WRITTEN",
        "ai_assisted": "AI-ASSISTED",
        "ai_generated": "AI-GENERATED",
    }

    for p in result.get("passages", []):
        sec = f" — {p['section_heading']}" if p.get("section_heading") else ""
        tag = badge_map.get(p["classification"], p["label"])
        lines.append(f"### Passage #{p['index'] + 1}{sec} [{tag} · {p['ai_score_pct']}%]")
        lines.append(f"> {p['text'].replace(chr(10), ' ')}")
        lines.append("")
        ex = p["experts"]
        lines.append(
            f"- **Experts:** TMR-RoBERTa `{round((ex['tmr_roberta'] or 0)*100, 1)}%` | "
            f"E5-LoRA `{round((ex['e5_lora'] or 0)*100, 1)}%` | "
            f"SciStructure `{round(ex['sci_structure']*100, 1)}%` | Confidence: `{p['confidence']}`"
        )
        trigs = p["structure"]["triggers"]
        if trigs:
            trig_summary = ", ".join(f"`{t['matched_text']}` ({t['label']})" for t in trigs[:6])
            lines.append(f"- **Flagged Spans ({len(trigs)}):** {trig_summary}")
        for act in p["coaching"]["actions"]:
            lines.append(f"- **Revision Tip — {act['title']}:** {act['detail']}")
        lines.append("")

    return "\n".join(lines)
