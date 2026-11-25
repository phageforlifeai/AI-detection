"""
Scientific Stylometric & Structural Analyzer (SciStructure Expert).

Detects AI-like structural habits in scientific manuscripts grounded in
published empirical studies on LLM academic prose (Kobak et al., 2024;
Liang et al., 2024; Desaire et al., Science Advances 2023):

1. Burstiness & Sentence Length Uniformity (CV, consecutive delta, monotonous runs)
2. Participial '-ing' Summary Tails (", highlighting...", ", underscoring...")
3. Mechanical Sentence-Initial Discourse Signposts ("Furthermore,", "Moreover,")
4. Excess LLM Scientific Vocabulary (Tier-1 high-excess & Tier-2 buzzwords)
5. Rhetorical Boilerplate Templates ("plays a pivotal role in", "not only...but also")
6. Parallel Triadic Coordination ("enhancing X, reducing Y, and improving Z")
7. Empirical Specificity / Quantitative Anchor Density (numbers, units, stats, citations)
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Dict, List, Any, Tuple

from .segmenter import SentenceSpan, split_scientific_sentences, count_words


# Tier-1: Documented 5x-25x excess frequency in post-2023 LLM academic papers (Kobak et al. / Liang et al.)
TIER1_EXCESS_WORDS: Dict[str, str] = {
    "delve": "examine / analyze / investigate",
    "delves": "examines / analyzes",
    "delving": "examining / measuring",
    "delved": "examined / analyzed",
    "underscore": "show / confirm / demonstrate",
    "underscores": "shows / confirms / indicates",
    "underscoring": "showing / indicating (or cut trailing clause)",
    "underscored": "showed / confirmed",
    "pivotal": "key / central / rate-limiting (or state the exact effect)",
    "intricate": "specific / coupled / multi-step",
    "intricacies": "mechanisms / details",
    "interplay": "interaction / coupling / relationship",
    "meticulous": "careful / controlled / systematic",
    "meticulously": "systematically / precisely",
    "multifaceted": "multi-factor / complex (specify the factors)",
    "realm": "field / domain / regime",
    "bolster": "support / strengthen / increase",
    "bolsters": "supports / strengthens",
    "bolstering": "supporting / strengthening",
    "garner": "attract / receive",
    "garnered": "received / attracted",
    "garnering": "receiving",
    "tapestry": "set / network / distribution",
    "overarching": "main / primary / central",
    "groundbreaking": "new / first (cite the specific advance instead)",
    "transformative": "substantial / measurable",
    "seamless": "direct / integrated / automated",
    "seamlessly": "directly / without manual intervention",
    "illuminate": "clarify / reveal / resolve",
    "illuminates": "clarifies / reveals",
    "illuminating": "clarifying / revealing",
    "foster": "promote / enable / support",
    "fosters": "promotes / enables",
    "fostering": "promoting / enabling",
    "showcase": "show / report / demonstrate",
    "showcases": "shows / reports",
    "showcasing": "showing / reporting",
    "paramount": "critical / essential",
    "commendable": "notable / strong (avoid editorializing)",
    "unprecedented": "rare / X-fold higher than prior reports",
    "revolutionize": "change / improve / accelerate",
    "revolutionized": "changed / accelerated",
    "revolutionizing": "changing / accelerating",
    "spearhead": "lead / initiate",
    "burgeoning": "growing / expanding",
    "indispensable": "essential / required",
    "testament": "evidence",
}

# Tier-2: High-frequency LLM academic polish verbs/adjectives (flagged softly when dense)
TIER2_BUZZWORDS: Dict[str, str] = {
    "utilize": "use",
    "utilizes": "uses",
    "utilizing": "using",
    "utilized": "used",
    "leverage": "use / apply / exploit",
    "leverages": "uses / applies",
    "leveraging": "using / applying",
    "leveraged": "used / applied",
    "comprehensive": "full / systematic / N-dataset",
    "crucial": "important / necessary",
    "vital": "essential / required",
    "noteworthy": "notable (or state the number directly)",
    "facilitate": "enable / speed up / allow",
    "facilitates": "enables / allows",
    "facilitating": "enabling / allowing",
    "elucidate": "determine / identify / resolve",
    "elucidating": "identifying / resolving",
    "holistic": "integrated / whole-system",
    "synergistic": "combined / super-additive (quantify interaction)",
    "paradigm": "model / framework / approach",
    "landscape": "field / distribution / literature",
    "avenues": "directions / tests",
}

# Sentence-initial mechanical conjunctive adverbs overused by LLMs
INITIAL_SIGNPOSTS = re.compile(
    r"^(Furthermore|Moreover|Additionally|Importantly|Notably|Crucially|"
    r"Intriguingly|Remarkably|Interestingly|Specifically|Consequently|"
    r"Collectively|Overall|Taken together|In summary|In conclusion|"
    r"To this end|In light of this|Building upon this|Along these lines)\s*,",
    re.IGNORECASE,
)

# Participial "-ing" evaluative/summary tail after a comma in the latter half of a sentence
PARTICIPIAL_TAIL_PATTERN = re.compile(
    r",\s+(?:thereby\s+|thus\s+|ultimately\s+|effectively\s+|simultaneously\s+)?"
    r"(highlighting|underscoring|demonstrating|illustrating|showcasing|revealing|"
    r"indicating|suggesting|confirming|emphasizing|reinforcing|bolstering|"
    r"fostering|enabling|facilitating|paving\s+the\s+way\s+for|shedding\s+light\s+on|"
    r"offering\s+(?:valuable|new|novel|promising|critical|important)?\s*(?:insights|opportunities|perspectives|avenues)|"
    r"making\s+it\s+(?:a|an)\s+(?:ideal|promising|attractive|viable|powerful)|"
    r"providing\s+(?:a\s+)?(?:comprehensive|robust|valuable|solid|new)\s+(?:foundation|framework|understanding|basis))"
    r"\b[^.?!]{4,140}(?=[.?!]|$)",
    re.IGNORECASE,
)

# Formulaic LLM academic phrase templates
BOILERPLATE_TEMPLATES: List[Tuple[re.Pattern, str, str]] = [
    (
        re.compile(r"\bplays?\s+a\s+(?:pivotal|crucial|vital|critical|key|central|indispensable)\s+role\s+in\b", re.I),
        "Boilerplate 'plays a [pivotal/crucial] role in'",
        "Replace with a direct causal verb: e.g., 'regulates', 'drives', 'limits', or 'accounts for X% of'.",
    ),
    (
        re.compile(r"\bnot\s+only\b[^.?!]{3,90}\bbut\s+also\b", re.I),
        "Symmetrical 'not only ... but also' correlative frame",
        "LLMs overuse 'not only X, but also Y' to sound rhetorical. State the two facts directly or subordinate one clause.",
    ),
    (
        re.compile(r"\bdespite\s+these\s+(?:advancements|advances|promising\s+results|efforts|achievements)\s*,\s*[a-z\s]{0,25}(?:challenges|limitations|hurdles|bottlenecks|gaps)\s+(?:still\s+)?remain\b", re.I),
        "Formulaic pivot 'Despite these advancements, challenges remain'",
        "Name the exact technical failure mode directly instead of a generic 'challenges remain' transition.",
    ),
    (
        re.compile(r"\bit\s+is\s+(?:worth\s+noting|important\s+to\s+note|imperative\s+to\s+note|noteworthy)\s+that\b", re.I),
        "Throat-clearing hedge 'It is worth/important to note that'",
        "Delete the meta-commentary prefix and start the sentence directly with the subject.",
    ),
    (
        re.compile(r"\bpaves?\s+the\s+way\s+(?:for|toward|towards)\b", re.I),
        "Cliché closer 'paves the way for'",
        "Specify the concrete follow-up application or experiment instead of 'paves the way for'.",
    ),
    (
        re.compile(r"\bsheds?\s+(?:new\s+|valuable\s+)?light\s+on\b", re.I),
        "Cliché metaphor 'sheds light on'",
        "Use a precise verb: 'resolves', 'identifies', 'quantifies', or 'explains'.",
    ),
    (
        re.compile(r"\bbridges?\s+the\s+gap\s+between\b", re.I),
        "Cliché metaphor 'bridges the gap between'",
        "State explicitly how the two methods/scales are connected (e.g., 'couples X to Y').",
    ),
    (
        re.compile(r"\bhas\s+(?:garnered|attracted|received)\s+(?:significant|considerable|increasing|widespread|growing)\s+(?:attention|interest)\b", re.I),
        "Generic opening 'has garnered significant attention'",
        "Open with the concrete scientific problem, mechanism, or quantitative demand instead of popularity.",
    ),
    (
        re.compile(r"\ba\s+growing\s+body\s+of\s+(?:literature|evidence|research)\b", re.I),
        "Vague citation placeholder 'a growing body of literature'",
        "Cite the specific studies and state what they established quantitatively.",
    ),
    (
        re.compile(r"\bholds?\s+(?:great|immense|significant|considerable|tremendous)\s+(?:promise|potential)\s+for\b", re.I),
        "Promotional closer 'holds great promise for'",
        "Replace promotional phrasing with the specific condition or regime where the method works.",
    ),
    (
        re.compile(r"\bin\s+the\s+(?:rapidly\s+evolving\s+|ever-evolving\s+)?(?:landscape|realm|era)\s+of\b", re.I),
        "Sweeping LLM opener 'In the [rapidly evolving] landscape/realm of'",
        "Cut the sweeping preamble; start directly with your system, organism, or physical phenomenon.",
    ),
    (
        re.compile(r"\b(?:recent\s+advancements|recent\s+advances)\s+in\s+[^.?!]{3,55}\s+have\s+(?:revolutionized|transformed|reshaped|redefined)\b", re.I),
        "Grandiose funnel hook 'Recent advancements in X have revolutionized...'",
        "Start with a specific technical statement or unsolved constraint rather than a textbook funnel.",
    ),
    (
        re.compile(r"\boffers?\s+(?:a\s+)?(?:promising|compelling|viable|powerful|attractive)\s+(?:avenue|alternative|solution|strategy|approach)\s+(?:for|to)\b", re.I),
        "Generic evaluative frame 'offers a promising avenue/approach for'",
        "State the measurable advantage (e.g., 'reduces runtime by 3x' or 'avoids reagent X').",
    ),
]

# Parallel Triadic Gerund/Verb List: e.g., "enhancing accuracy, reducing latency, and improving scalability"
TRIADIC_GERUND_PATTERN = re.compile(
    r"\b([a-z]{4,}ing\s+(?:[a-z0-9-]+\s+){0,2}[a-z0-9-]+),\s+"
    r"([a-z]{4,}ing\s+(?:[a-z0-9-]+\s+){0,2}[a-z0-9-]+),\s+and\s+"
    r"([a-z]{4,}ing\s+(?:[a-z0-9-]+\s+){0,2}[a-z0-9-]+)\b",
    re.IGNORECASE,
)

# Parallel Triadic Adjective-Noun List: e.g., "high accuracy, strong robustness, and broad applicability"
TRIADIC_NOUN_PATTERN = re.compile(
    r"\b((?:high|low|strong|superior|enhanced|improved|robust|broad|wide|greater|minimal|rapid|efficient|scalable|precise|accurate)\s+[a-z-]{4,}),\s+"
    r"((?:high|low|strong|superior|enhanced|improved|robust|broad|wide|greater|minimal|rapid|efficient|scalable|precise|accurate)\s+[a-z-]{4,}),\s+and\s+"
    r"((?:high|low|strong|superior|enhanced|improved|robust|broad|wide|greater|minimal|rapid|efficient|scalable|precise|accurate)\s+[a-z-]{4,})\b",
    re.IGNORECASE,
)

# Empirical Specificity Anchors (indicators of authentic concrete scientific reporting)
EMPIRICAL_PATTERNS = [
    # Numbers with scientific units, percentages, fold-changes, temperatures, concentrations
    re.compile(
        r"\b\d+(?:\.\d+)?\s*(?:%|°C|K|mM|µM|uM|nM|pM|mg|µg|ug|ng|mL|µL|uL|Hz|kHz|MHz|GHz|"
        r"eV|meV|keV|GeV|nm|µm|um|mm|cm|km|ms|ns|ps|µs|s|min|h|hr|hrs|days|wks|months|"
        r"kDa|Da|bp|kb|Mb|mol|mmol|Pa|kPa|MPa|GPa|V|mV|A|mA|µA|W|mW|kW|T|mT|dB|fold|×|x)\b"
    ),
    # Statistical & experimental notation (p < 0.05, n = 24, CI, SD, SEM, r = 0.82, F(1,24))
    re.compile(r"\b(?:[pPrRtTFzZ]\s*[=<>≤≥]\s*-?\d+(?:\.\d+)?|[nN]\s*=\s*\d+|95%\s*CI|±\s*\d+|SD\b|SEM\b|IQR\b|ANOVA\b|Mann-Whitney|Wilcoxon|Kaplan-Meier)"),
    # Explicit citations: [1], [12, 15], [cite], (Smith et al., 2021)
    re.compile(r"(?:\[\s*\d+(?:\s*[-,–]\s*\d+)*\s*\]|\[cite\]|\([A-Z][a-zA-Z-]+(?:\s+et\s+al\.)?,?\s*(?:19|20)\d{2}[a-z]?\))"),
    # Figure / Table / Equation / Supplement cross-references
    re.compile(r"\b(?:Fig\.|Figs\.|Figure|Table|Eq\.|Eqs\.|Equation|Supplementary|Appendix|Section)\s*[S0-9A-Za-z]+"),
    # Alphanumeric gene/protein/chemical/model/material identifiers (e.g. MnBi2Te4, Slc2a1, CD8+, ResNet-50, SARS-CoV-2)
    re.compile(r"\b(?:[A-Za-z]{1,6}\d+[A-Za-z0-9+-]*|[A-Z]{2,5}-[A-Za-z0-9]+)\b"),
]


@dataclass
class TriggerSpan:
    start: int
    end: int
    category: str
    matched_text: str
    label: str
    suggestion: str
    severity: str  # "high" | "medium"


def _dedupe_spans(spans: List[TriggerSpan]) -> List[TriggerSpan]:
    """Keep highest-severity / longest non-overlapping spans sorted by character offset."""
    if not spans:
        return []
    sev_rank = {"high": 2, "medium": 1}
    # Sort by start asc, then severity desc, then length desc
    ordered = sorted(
        spans,
        key=lambda s: (s.start, -sev_rank.get(s.severity, 1), -(s.end - s.start)),
    )
    kept: List[TriggerSpan] = []
    for sp in ordered:
        if not kept:
            kept.append(sp)
            continue
        prev = kept[-1]
        if sp.start < prev.end:
            # Overlap: prefer higher severity or substantially longer phrase template over single word
            if sev_rank.get(sp.severity, 1) > sev_rank.get(prev.severity, 1) or (
                (sp.end - sp.start) > (prev.end - prev.start) + 8
            ):
                kept[-1] = sp
            continue
        kept.append(sp)
    return sorted(kept, key=lambda s: s.start)


def find_structural_triggers(text: str, sentences: List[SentenceSpan] | None = None) -> List[TriggerSpan]:
    """
    Scan text and return character-accurate structural & lexical AI trigger spans.
    """
    if sentences is None:
        sentences = split_scientific_sentences(text)

    triggers: List[TriggerSpan] = []

    # 1. Boilerplate academic phrase templates
    for pattern, label, suggestion in BOILERPLATE_TEMPLATES:
        for m in pattern.finditer(text):
            triggers.append(
                TriggerSpan(
                    start=m.start(),
                    end=m.end(),
                    category="boilerplate_template",
                    matched_text=text[m.start():m.end()],
                    label=label,
                    suggestion=suggestion,
                    severity="high",
                )
            )

    # 2. Sentence-level participial "-ing" tails & mechanical discourse starters
    for sent in sentences:
        s_txt = sent.text
        # Initial signpost check
        m_init = INITIAL_SIGNPOSTS.match(s_txt.lstrip())
        if m_init:
            lead_ws = len(s_txt) - len(s_txt.lstrip())
            st = sent.start + lead_ws + m_init.start()
            en = sent.start + lead_ws + m_init.end()
            word = m_init.group(1)
            triggers.append(
                TriggerSpan(
                    start=st,
                    end=en,
                    category="formulaic_transition",
                    matched_text=text[st:en],
                    label=f"Mechanical discourse starter '{word},'",
                    suggestion="LLMs chain sentences with 'Furthermore/Moreover/Additionally'. Try starting directly with the concrete subject or linking via a specific noun.",
                    severity="medium",
                )
            )

        # Participial tail check (only in second 60% of a >= 14-word sentence)
        if sent.word_count >= 14:
            for m_tail in PARTICIPIAL_TAIL_PATTERN.finditer(s_txt):
                if m_tail.start() >= len(s_txt) * 0.35:
                    st = sent.start + m_tail.start()
                    en = sent.start + m_tail.end()
                    participle = m_tail.group(1)
                    triggers.append(
                        TriggerSpan(
                            start=st,
                            end=en,
                            category="participial_tail",
                            matched_text=text[st:en],
                            label=f"Participial '-ing' summary tail (', {participle}...')",
                            suggestion="Trailing ', V-ing...' evaluative clauses are one of the strongest LLM structural signatures. End the sentence at the comma, or state the mechanism in a separate direct sentence.",
                            severity="high",
                        )
                    )

    # 3. Parallel triadic coordination ("Rule of Three")
    for pat, desc in [
        (TRIADIC_GERUND_PATTERN, "Symmetrical 3-part '-ing' parallel list"),
        (TRIADIC_NOUN_PATTERN, "Symmetrical 3-part evaluative noun list"),
    ]:
        for m in pat.finditer(text):
            triggers.append(
                TriggerSpan(
                    start=m.start(),
                    end=m.end(),
                    category="triadic_symmetry",
                    matched_text=text[m.start():m.end()],
                    label=desc,
                    suggestion="Mechanical 'X, Y, and Z' triads make prose sound templated. Keep only the measured outcomes and report their actual magnitudes.",
                    severity="medium",
                )
            )

    # 4. Excess LLM Vocabulary (Tier 1 & Tier 2)
    for m in re.finditer(r"\b([A-Za-z]{4,})\b", text):
        w_low = m.group(1).lower()
        if w_low in TIER1_EXCESS_WORDS:
            alt = TIER1_EXCESS_WORDS[w_low]
            triggers.append(
                TriggerSpan(
                    start=m.start(),
                    end=m.end(),
                    category="excess_vocab",
                    matched_text=m.group(0),
                    label=f"High-excess LLM word '{m.group(0)}'",
                    suggestion=f"Spiked >5x in LLM-generated papers. Prefer plain scientific diction: {alt}.",
                    severity="high",
                )
            )
        elif w_low in TIER2_BUZZWORDS:
            alt = TIER2_BUZZWORDS[w_low]
            triggers.append(
                TriggerSpan(
                    start=m.start(),
                    end=m.end(),
                    category="excess_vocab",
                    matched_text=m.group(0),
                    label=f"LLM polish buzzword '{m.group(0)}'",
                    suggestion=f"Often introduced by AI polishing. Consider simpler phrasing: {alt}.",
                    severity="medium",
                )
            )

    return _dedupe_spans(triggers)


def count_empirical_anchors(text: str) -> int:
    spans = set()
    for pat in EMPIRICAL_PATTERNS:
        for m in pat.finditer(text):
            # Bucket by start//4 to avoid double-counting overlapping regexes on "p = 0.003"
            spans.add(m.start() // 4)
    return len(spans)


def compute_burstiness_metrics(sentences: List[SentenceSpan]) -> Dict[str, Any]:
    """
    Compute sentence-length rhythm & burstiness metrics.
    Human scientific prose typically has CV ~ 0.40 - 0.65 with occasional crisp
    short sentences (<12 words) and detailed long clauses (>30 words).
    LLM scientific prose clusters tightly around 18-26 words (CV < 0.28).
    """
    lengths = [s.word_count for s in sentences if s.word_count >= 3]
    n = len(lengths)
    if n == 0:
        return {
            "sentence_count": 0,
            "mean_words": 0.0,
            "std_words": 0.0,
            "cv": 0.0,
            "min_words": 0,
            "max_words": 0,
            "short_sentence_ratio": 0.0,
            "long_sentence_ratio": 0.0,
            "mean_adjacent_delta": 0.0,
            "monotonous_runs": 0,
            "uniformity_risk": 0.0,
            "sentence_lengths": [],
        }

    mean_w = sum(lengths) / n
    if n >= 2:
        variance = sum((x - mean_w) ** 2 for x in lengths) / n
        std_w = math.sqrt(variance)
        cv = std_w / max(mean_w, 1.0)
        adj_deltas = [abs(lengths[i] - lengths[i - 1]) for i in range(1, n)]
        mean_delta = sum(adj_deltas) / len(adj_deltas)
    else:
        std_w = 0.0
        cv = 0.35
        mean_delta = 6.0

    short_ratio = sum(1 for x in lengths if x <= 12) / n
    long_ratio = sum(1 for x in lengths if x >= 30) / n

    # Count consecutive 3-sentence runs where all sentences sit inside a narrow 16-28 word band
    monotonous_runs = 0
    for i in range(n - 2):
        window = lengths[i : i + 3]
        if max(window) - min(window) <= 6 and all(15 <= w <= 30 for w in window):
            monotonous_runs += 1

    # Calibrate uniformity_risk in [0, 1] (higher = more robotic/LLM-uniform)
    if n < 3:
        # Too few sentences in a short snippet to penalize rhythm heavily
        if 18 <= mean_w <= 28 and std_w < 3.5 and n == 2:
            uniformity_risk = 0.55
        else:
            uniformity_risk = 0.25
    else:
        # CV <= 0.18 -> ~0.92 risk; CV >= 0.46 -> ~0.08 risk
        cv_risk = max(0.0, min(1.0, (0.46 - cv) / 0.32))
        delta_risk = max(0.0, min(1.0, (9.5 - mean_delta) / 7.5))
        no_short_penalty = 0.12 if (n >= 4 and short_ratio == 0.0 and mean_w >= 19.0) else 0.0
        mono_penalty = min(0.18, monotonous_runs * 0.07)
        uniformity_risk = max(0.0, min(1.0, 0.55 * cv_risk + 0.30 * delta_risk + no_short_penalty + mono_penalty))

    return {
        "sentence_count": n,
        "mean_words": round(mean_w, 1),
        "std_words": round(std_w, 1),
        "cv": round(cv, 3),
        "min_words": min(lengths),
        "max_words": max(lengths),
        "short_sentence_ratio": round(short_ratio, 3),
        "long_sentence_ratio": round(long_ratio, 3),
        "mean_adjacent_delta": round(mean_delta, 1),
        "monotonous_runs": monotonous_runs,
        "uniformity_risk": round(uniformity_risk, 3),
        "sentence_lengths": lengths,
    }


def analyze_structure(text: str, sentences: List[SentenceSpan] | None = None) -> Dict[str, Any]:
    """
    Full 7-dimension scientific structural & stylometric evaluation for a passage or document.
    Returns sub-scores (0-100), trigger spans, burstiness stats, empirical anchor stats,
    and an aggregated structural_ai_prob in [0.0, 1.0].
    """
    if sentences is None:
        sentences = split_scientific_sentences(text)

    wc = max(1, count_words(text))
    n_sents = max(1, len(sentences))
    triggers = find_structural_triggers(text, sentences)
    burst = compute_burstiness_metrics(sentences)
    anchors = count_empirical_anchors(text)
    anchors_per_100w = (anchors / wc) * 100.0

    # Categorize triggers
    cat_counts: Dict[str, int] = {
        "excess_vocab_high": 0,
        "excess_vocab_med": 0,
        "participial_tail": 0,
        "formulaic_transition": 0,
        "boilerplate_template": 0,
        "triadic_symmetry": 0,
    }
    for sp in triggers:
        if sp.category == "excess_vocab":
            if sp.severity == "high":
                cat_counts["excess_vocab_high"] += 1
            else:
                cat_counts["excess_vocab_med"] += 1
        elif sp.category in cat_counts:
            cat_counts[sp.category] += 1

    # Normalize rates
    vocab_rate_100w = ((cat_counts["excess_vocab_high"] * 1.5 + cat_counts["excess_vocab_med"] * 0.65) / wc) * 100.0
    tail_ratio = cat_counts["participial_tail"] / n_sents
    trans_ratio = cat_counts["formulaic_transition"] / n_sents
    template_rate_100w = (cat_counts["boilerplate_template"] / wc) * 100.0
    triad_rate_100w = (cat_counts["triadic_symmetry"] / wc) * 100.0

    # Dimension sub-scores [0 - 100] (higher = more AI-structured)
    dim_burstiness = round(burst["uniformity_risk"] * 100.0, 1)
    dim_participial = round(min(100.0, (tail_ratio / 0.38) * 100.0), 1)
    dim_transitions = round(min(100.0, (trans_ratio / 0.42) * 100.0), 1)
    dim_vocab = round(min(100.0, (vocab_rate_100w / 4.2) * 100.0), 1)
    dim_boilerplate = round(min(100.0, (template_rate_100w / 1.8) * 100.0), 1)
    dim_symmetry = round(min(100.0, (triad_rate_100w / 1.4) * 100.0), 1)
    # Specificity deficit: >= 5.5 anchors per 100 words -> ~5% deficit; 0 anchors -> ~85% deficit
    dim_specificity_deficit = round(max(0.0, min(90.0, 85.0 - (anchors_per_100w / 5.5) * 80.0)), 1)

    # Weighted structural AI probability [0, 1]
    raw_struct = (
        0.24 * (dim_vocab / 100.0)
        + 0.20 * (dim_participial / 100.0)
        + 0.16 * (dim_boilerplate / 100.0)
        + 0.14 * (dim_transitions / 100.0)
        + 0.12 * (dim_burstiness / 100.0)
        + 0.06 * (dim_symmetry / 100.0)
        + 0.08 * (dim_specificity_deficit / 100.0)
    )
    # Nonlinear boost when multiple distinct AI structural signatures co-occur in the same passage
    active_high_dims = sum(
        1
        for d in [dim_vocab, dim_participial, dim_boilerplate, dim_transitions, dim_symmetry]
        if d >= 35.0
    )
    if active_high_dims >= 3:
        raw_struct = min(0.98, raw_struct * 1.32 + 0.12)
    elif active_high_dims == 2:
        raw_struct = min(0.95, raw_struct * 1.18 + 0.06)

    # Dampen if strong empirical specificity and zero high-severity triggers
    if anchors_per_100w >= 4.5 and cat_counts["excess_vocab_high"] == 0 and cat_counts["participial_tail"] == 0 and cat_counts["boilerplate_template"] == 0:
        raw_struct *= 0.55

    structural_ai_prob = round(max(0.01, min(0.99, raw_struct)), 4)

    return {
        "word_count": wc,
        "structural_ai_prob": structural_ai_prob,
        "empirical_anchors": anchors,
        "anchors_per_100w": round(anchors_per_100w, 2),
        "burstiness": burst,
        "dimensions": {
            "rhythm_uniformity": dim_burstiness,
            "participial_tails": dim_participial,
            "formulaic_transitions": dim_transitions,
            "excess_llm_vocab": dim_vocab,
            "rhetorical_boilerplate": dim_boilerplate,
            "triadic_symmetry": dim_symmetry,
            "specificity_deficit": dim_specificity_deficit,
        },
        "trigger_counts": cat_counts,
        "triggers": [
            {
                "start": sp.start,
                "end": sp.end,
                "category": sp.category,
                "matched_text": sp.matched_text,
                "label": sp.label,
                "suggestion": sp.suggestion,
                "severity": sp.severity,
            }
            for sp in triggers
        ],
    }
