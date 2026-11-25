"""
Scientific Structure Revision Coach.
Generates concrete, manuscript-safe guidance and surgical phrase-level edits
to eliminate LLM structural habits without altering scientific meaning or data.
"""

from __future__ import annotations

import re
from typing import Dict, Any, List


def generate_passage_coaching(
    passage_text: str,
    classification: str,
    ai_score: float,
    struct_info: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Produce actionable structural revision tactics and deterministic quick-fix
    suggestions for a single passage.
    """
    dims = struct_info["dimensions"]
    burst = struct_info["burstiness"]
    triggers = struct_info["triggers"]
    anchors_rate = struct_info["anchors_per_100w"]

    actions: List[Dict[str, str]] = []

    if classification == "human" and ai_score < 0.30 and len(triggers) <= 1:
        return {
            "summary": "Natural empirical cadence. Sentence rhythm varies organically and relies on concrete scientific claims rather than rhetorical scaffolding.",
            "actions": [
                {
                    "title": "Keep this direct empirical voice",
                    "detail": (
                        f"Good specificity ({anchors_rate:.1f} quantitative/citation anchors per 100 words) "
                        f"and healthy sentence-length variation (CV = {burst['cv']:.2f})."
                    ),
                    "priority": "low",
                }
            ],
            "de_templated_preview": None,
        }

    # 1. Participial "-ing" tails
    tail_trigs = [t for t in triggers if t["category"] == "participial_tail"]
    if tail_trigs:
        examples = "; ".join(f'"{t["matched_text"][:48]}..."' for t in tail_trigs[:2])
        actions.append(
            {
                "title": "Trim trailing '-ing' commentary clauses",
                "detail": (
                    f"Found {len(tail_trigs)} participial summary tail(s) ({examples}). "
                    "LLMs habitually tack ', highlighting/underscoring/paving the way...' onto the end of sentences. "
                    "Put a period right before the comma, or convert the implication into an independent testable claim."
                ),
                "priority": "high",
            }
        )

    # 2. Excess LLM vocabulary
    vocab_trigs = [t for t in triggers if t["category"] == "excess_vocab"]
    if vocab_trigs:
        words_seen = []
        for t in vocab_trigs:
            if t["matched_text"] not in words_seen:
                words_seen.append(t["matched_text"])
        actions.append(
            {
                "title": "Replace high-excess LLM vocabulary with plain domain verbs",
                "detail": (
                    f"Detected AI-enriched academic words ({', '.join(words_seen[:6])}). "
                    "Swap abstract intensifiers ('pivotal', 'intricate', 'underscore', 'utilize') for measurable verbs ('controls', 'couples', 'shows', 'use')."
                ),
                "priority": "high" if any(t["severity"] == "high" for t in vocab_trigs) else "medium",
            }
        )

    # 3. Boilerplate templates
    boiler_trigs = [t for t in triggers if t["category"] == "boilerplate_template"]
    if boiler_trigs:
        ex = boiler_trigs[0]["matched_text"]
        actions.append(
            {
                "title": "Break formulaic academic phrase templates",
                "detail": (
                    f'Phrase "{ex}" follows a stock LLM transition/framing template. '
                    f"{boiler_trigs[0]['suggestion']}"
                ),
                "priority": "high",
            }
        )

    # 4. Mechanical discourse starters
    trans_trigs = [t for t in triggers if t["category"] == "formulaic_transition"]
    if trans_trigs:
        starters = ", ".join(t["matched_text"] for t in trans_trigs[:4])
        actions.append(
            {
                "title": "Remove chained conjunctive starters",
                "detail": (
                    f"Sentences open with mechanical signposts ({starters}). "
                    "Delete the starter adverb and connect sentences by repeating or referencing the concrete noun from the previous sentence ('This threshold...', 'Under these conditions...')."
                ),
                "priority": "medium",
            }
        )

    # 5. Monotonous sentence rhythm / low burstiness
    if dims["rhythm_uniformity"] >= 52.0 and burst["sentence_count"] >= 3:
        actions.append(
            {
                "title": "Break monotonous ~22-word sentence cadence (Low Burstiness)",
                "detail": (
                    f"Sentence lengths cluster tightly around {burst['mean_words']} ± {burst['std_words']} words "
                    f"(CV = {burst['cv']:.2f}; lengths: {burst['sentence_lengths']}). "
                    "Split one compound sentence into a crisp 8–11 word statement of the main result, followed by a longer methodological or mechanistic sentence."
                ),
                "priority": "high" if dims["rhythm_uniformity"] >= 68.0 else "medium",
            }
        )

    # 6. Parallel triadic lists
    triad_trigs = [t for t in triggers if t["category"] == "triadic_symmetry"]
    if triad_trigs:
        actions.append(
            {
                "title": "Unpack symmetrical 3-item lists ('Rule of Three')",
                "detail": (
                    f'"{triad_trigs[0]["matched_text"]}" uses symmetric triadic coordination typical of LLM summaries. '
                    "Report the primary measured effect with its number/unit rather than listing three abstract benefits."
                ),
                "priority": "medium",
            }
        )

    # 7. Specificity deficit
    if anchors_rate < 2.2 and ai_score >= 0.42:
        actions.append(
            {
                "title": "Anchor claims with concrete numbers, conditions, or citations",
                "detail": (
                    f"Only {anchors_rate:.1f} empirical anchors per 100 words. "
                    "AI-like prose summarizes significance abstractly; human scientific prose names exact sample sizes, effect magnitudes, boundary conditions, or literature citations."
                ),
                "priority": "medium",
            }
        )

    if not actions:
        actions.append(
            {
                "title": "Vary syntactic openings and clause structure",
                "detail": (
                    "Neural detectors picked up subtle token-level predictability (smooth subject -> verb -> prepositional-phrase cadence). "
                    "Try fronting a concrete experimental condition ('At T < 25 K,...') or stating a direct caveat."
                ),
                "priority": "medium",
            }
        )

    de_templated = build_surgical_cleanup_draft(passage_text)
    if de_templated.strip() == passage_text.strip():
        de_templated = None

    if classification == "ai_generated":
        summary = "Strong AI-generated structural & token profile. Rewrite from your raw experimental notes/outline using varied sentence lengths and direct empirical verbs."
    elif classification == "ai_assisted":
        summary = "Hybrid / AI-polished profile. Core scientific content appears present, but LLM editing habits (smooth transitions, uniform cadence, or stock academic phrasing) are visible."
    else:
        summary = "Mostly human-written, with minor formulaic academic phrasing noted below."

    return {
        "summary": summary,
        "actions": actions,
        "de_templated_preview": de_templated,
    }


# Deterministic, meaning-preserving cleanup rules to demonstrate structural de-templating
SURGICAL_REPLACEMENTS = [
    (re.compile(r"\b(?:Furthermore|Moreover|Additionally|Importantly|Notably|Crucially)\s*,\s+([a-z])"), lambda m: m.group(1).upper()),
    (re.compile(r"\bIt\s+is\s+(?:worth\s+noting|important\s+to\s+note|noteworthy)\s+that\s+([a-z])", re.I), lambda m: m.group(1).upper()),
    (re.compile(r"\bplays\s+a\s+(?:pivotal|crucial|vital|critical)\s+role\s+in\s+([a-z]+ing)\b", re.I), r"directly drives \1"),
    (re.compile(r"\bplay\s+a\s+(?:pivotal|crucial|vital|critical)\s+role\s+in\s+([a-z]+ing)\b", re.I), r"directly drive \1"),
    (re.compile(r"\bunderscores\s+the\s+(?:critical\s+|pivotal\s+|vital\s+)?importance\s+of\b", re.I), "shows the need for"),
    (re.compile(r"\bunderscore\s+the\s+(?:critical\s+|pivotal\s+|vital\s+)?importance\s+of\b", re.I), "show the need for"),
    (re.compile(r"\butilize\b", re.I), "use"),
    (re.compile(r"\butilizes\b", re.I), "uses"),
    (re.compile(r"\butilized\b", re.I), "used"),
    (re.compile(r"\butilizing\b", re.I), "using"),
    (re.compile(r"\bleveraging\b", re.I), "using"),
    (re.compile(r"\bleverage\b", re.I), "use"),
    (re.compile(r"\bleverages\b", re.I), "uses"),
    (re.compile(r"\bdelving\s+into\b", re.I), "examining"),
    (re.compile(r"\bdelve\s+into\b", re.I), "examine"),
    (re.compile(r"\bdelves\s+into\b", re.I), "examines"),
    (re.compile(r"\bintricate\s+interplay\b", re.I), "interaction"),
    (re.compile(r"\bsheds?\s+(?:new\s+|valuable\s+)?light\s+on\b", re.I), "clarifies"),
    (re.compile(r",\s+(?:thereby\s+|ultimately\s+)?paving\s+the\s+way\s+for\s+([^.?!]+)(?=[.?!])", re.I), r". This enables \1"),
    (re.compile(r",\s+underscoring\s+([^.?!]+)(?=[.?!])", re.I), r"; this indicates \1"),
]


def build_surgical_cleanup_draft(text: str) -> str:
    """
    Apply conservative, deterministic structural de-templating (removing mechanical
    transition adverbs, buzzwords, and participial tails) as a starting point for
    authorial revision in the Live Editor. Never alters numbers or domain nouns.
    """
    out = text
    for pat, repl in SURGICAL_REPLACEMENTS:
        out = pat.sub(repl, out)
    return out


def generate_document_recommendations(
    overall_score: float,
    doc_struct: Dict[str, Any],
    passage_results: List[Dict[str, Any]],
) -> List[Dict[str, str]]:
    """Top-level manuscript structural takeaways."""
    recs: List[Dict[str, str]] = []
    dims = doc_struct["dimensions"]
    burst = doc_struct["burstiness"]

    ai_passages = [p["index"] + 1 for p in passage_results if p["classification"] == "ai_generated"]
    assisted_passages = [p["index"] + 1 for p in passage_results if p["classification"] == "ai_assisted"]

    if ai_passages:
        recs.append(
            {
                "badge": "High Impact",
                "title": f"Focus first on Passage(s) {', '.join('#' + str(i) for i in ai_passages[:5])}",
                "body": "These sections strongly match AI-generated token predictability and structural templates. Rewrite them directly from your figures, tables, or bullet notes rather than paraphrasing sentence-by-sentence.",
            }
        )
    if assisted_passages:
        recs.append(
            {
                "badge": "AI-Assisted Polish",
                "title": f"Strip LLM editing scaffolding in Passage(s) {', '.join('#' + str(i) for i in assisted_passages[:5])}",
                "body": "When an LLM 'polishes' human scientific drafts, it homogenizes sentence length (~22 words) and inserts smooth signposts ('Furthermore,', ', highlighting...'). Restoring crisp short sentences and direct verbs removes that synthetic sheen.",
            }
        )

    if dims["participial_tails"] >= 28.0:
        recs.append(
            {
                "badge": "Syntactic Habit #1",
                "title": "Eliminate trailing ', [verb]-ing...' commentary tails",
                "body": "Ending sentences with ', underscoring...', ', demonstrating...', or ', offering insights into...' is the single easiest structural tell in academic introductions and discussions. End on the concrete fact instead.",
            }
        )

    if dims["rhythm_uniformity"] >= 48.0:
        recs.append(
            {
                "badge": "Cadence & Burstiness",
                "title": f"Increase sentence-length contrast (Current CV = {burst['cv']:.2f}, target >= 0.42)",
                "body": f"Your manuscript averages {burst['mean_words']} words/sentence with ±{burst['std_words']} SD. Mix 7–11 word declarative result sentences with longer methodological explanations.",
            }
        )

    if dims["excess_llm_vocab"] >= 25.0 or dims["rhetorical_boilerplate"] >= 25.0:
        recs.append(
            {
                "badge": "Diction",
                "title": "Audit post-2023 'Excess Vocabulary' & stock transitions",
                "body": "Words like 'pivotal', 'delve', 'underscore', 'intricate', 'realm', 'foster', and 'utilize' appear up to 10–20x more often in LLM text than pre-2022 papers. Plain Anglo-Saxon/Latinate empirical verbs read more credibly to peer reviewers.",
            }
        )

    if not recs:
        recs.append(
            {
                "badge": "Clean Manuscript",
                "title": "Authentic scientific structure across passages",
                "body": f"Your draft shows natural burstiness (CV = {burst['cv']:.2f}), high empirical anchor density ({doc_struct['anchors_per_100w']:.1f}/100 words), and minimal LLM rhetorical templates.",
            }
        )

    return recs
