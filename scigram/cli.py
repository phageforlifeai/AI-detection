"""
Command-Line Interface for SciGram.

Examples:
    python3 -m scigram.cli manuscript.tex --report scan_report.md
    python3 -m scigram.cli draft.docx --json results.json
    python3 -m scigram.cli --sample mixed_manuscript
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .detector import get_detector
from .parsers import extract_document_text
from .report import render_markdown_report
from .samples import PRESET_SAMPLES


CLASS_COLORS = {
    "human": "green",
    "ai_assisted": "yellow",
    "ai_generated": "red",
}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="SciGram — Pangram-style AI Content & Scientific Structure Analyzer"
    )
    parser.add_argument(
        "input_file",
        nargs="?",
        help="Path to manuscript file (.txt, .md, .tex, .docx, .pdf)",
    )
    parser.add_argument(
        "--sample",
        choices=[s["id"] for s in PRESET_SAMPLES],
        help="Run on a built-in scientific sample preset",
    )
    parser.add_argument(
        "--text",
        help="Analyze a direct text string passed on the command line",
    )
    parser.add_argument(
        "--keep-references",
        action="store_true",
        help="Do not strip trailing References/Bibliography section",
    )
    parser.add_argument(
        "--report",
        help="Write a full Markdown diagnostic report to this file path",
    )
    parser.add_argument(
        "--json",
        dest="json_out",
        help="Write raw JSON analysis output to this file path",
    )

    args = parser.parse_args(argv)
    console = Console()

    title = "Direct Input"
    if args.sample:
        preset = next(s for s in PRESET_SAMPLES if s["id"] == args.sample)
        text = preset["text"]
        title = preset["title"]
    elif args.text:
        text = args.text
    elif args.input_file:
        if not os.path.exists(args.input_file):
            console.print(f"[bold red]Error:[/bold red] File not found: {args.input_file}")
            return 1
        with open(args.input_file, "rb") as f:
            raw_bytes = f.read()
        text, meta = extract_document_text(
            args.input_file, raw_bytes, strip_references=not args.keep_references
        )
        title = os.path.basename(args.input_file)
        if meta.get("references_stripped"):
            console.print("[dim]Note: Trailing References section excluded from prose scan.[/dim]")
    else:
        parser.print_help()
        return 0

    detector = get_detector()
    result = detector.analyze(text)
    if "error" in result:
        console.print(f"[bold red]{result['error']}[/bold red]")
        return 1

    v_color = CLASS_COLORS.get(result["overall_classification"], "white")
    bd = result["breakdown_pct"]
    ds = result["document_structure"]
    burst = ds["burstiness"]

    summary = (
        f"[bold {v_color}]{result['overall_verdict']}[/bold {v_color}]  "
        f"(Composite AI Score: [bold]{result['overall_ai_pct']}%[/bold])\n"
        f"[green]Human: {bd['human']}%[/green]  |  "
        f"[yellow]AI-Assisted: {bd['ai_assisted']}%[/yellow]  |  "
        f"[red]AI-Generated: {bd['ai_generated']}%[/red]\n"
        f"[dim]Words: {result['word_count']} · Passages: {result['passage_count']} · "
        f"Burstiness CV: {burst['cv']:.2f} · Empirical Anchors: {ds['anchors_per_100w']:.1f}/100w · "
        f"{result['engine_info']['latency_ms']} ms[/dim]"
    )
    console.print(Panel(summary, title=f"SciGram Scan — {title}", border_style=v_color))

    # Structural table
    dim_table = Table(title="Scientific Structure Diagnostics (0% = Human, 100% = Strong AI Habit)")
    dim_table.add_column("Dimension", style="cyan")
    dim_table.add_column("Risk", justify="right")
    dim_table.add_column("Bar", no_wrap=True)

    dim_labels = [
        ("Rhythm Uniformity (Low Burstiness)", ds["dimensions"]["rhythm_uniformity"]),
        ("Participial '-ing' Summary Tails", ds["dimensions"]["participial_tails"]),
        ("Mechanical Discourse Starters", ds["dimensions"]["formulaic_transitions"]),
        ("Excess LLM Scientific Vocabulary", ds["dimensions"]["excess_llm_vocab"]),
        ("Rhetorical Boilerplate Templates", ds["dimensions"]["rhetorical_boilerplate"]),
        ("Parallel Triadic Symmetry", ds["dimensions"]["triadic_symmetry"]),
        ("Empirical Specificity Deficit", ds["dimensions"]["specificity_deficit"]),
    ]
    for name, val in dim_labels:
        filled = int(round(val / 5.0))
        bar_col = "red" if val >= 55 else ("yellow" if val >= 30 else "green")
        bar_str = f"[{bar_col}]{'█' * filled}[/{bar_col}][dim]{'░' * (20 - filled)}[/dim]"
        dim_table.add_row(name, f"{val:.1f}%", bar_str)
    console.print(dim_table)

    # Passages
    console.print("\n[bold]Passage-by-Passage Highlighting & Coaching:[/bold]")
    for p in result["passages"]:
        c = CLASS_COLORS[p["classification"]]
        sec = f" · {p['section_heading']}" if p.get("section_heading") else ""
        header = f"Passage #{p['index'] + 1}{sec} — [{c}]{p['label']} ({p['ai_score_pct']}%)[/{c}]"

        # Highlight triggers inline
        rich_txt = Text()
        last = 0
        raw_p = p["text"]
        for trig in p["structure"]["triggers"]:
            st, en = trig["start"], trig["end"]
            if st > last:
                rich_txt.append(raw_p[last:st])
            t_style = "bold underline red" if trig["severity"] == "high" else "underline yellow"
            rich_txt.append(raw_p[st:en], style=t_style)
            last = en
        if last < len(raw_p):
            rich_txt.append(raw_p[last:])

        console.print(Panel(rich_txt, title=header, border_style=c))
        for act in p["coaching"]["actions"][:3]:
            console.print(f"  [bold]↳ {act['title']}:[/bold] {act['detail']}")

    if args.report:
        md = render_markdown_report(result, title=title)
        with open(args.report, "w", encoding="utf-8") as f:
            f.write(md)
        console.print(f"\n[green]Saved Markdown report to:[/green] {args.report}")

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        console.print(f"[green]Saved JSON results to:[/green] {args.json_out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
