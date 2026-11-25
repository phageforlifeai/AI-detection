"""
Unit test suite for SciGram parsers, scientific sentence segmentation,
7-dimension structural analysis, coaching, and detector pipeline.
"""

from scigram.coach import build_surgical_cleanup_draft
from scigram.detector import SciGramDetector
from scigram.parsers import parse_latex, strip_references_section
from scigram.segmenter import build_passages, is_section_heading, split_scientific_sentences
from scigram.stylometrics import analyze_structure


def test_scientific_sentence_splitting_preserves_abbreviations():
    prose = (
        "As reported by J. Smith et al. [4], tension rose by 3.14 mN (Fig. 2a; p < 0.001 vs. control). "
        "Short sentence here. "
        "Under ca. 25 mM NaCl, i.e. physiological ionic strength, activity stabilized."
    )
    sents = split_scientific_sentences(prose)
    assert len(sents) == 3
    for s in sents:
        assert prose[s.start : s.end] == s.text


def test_section_heading_detection():
    assert is_section_heading("1. Introduction") is True
    assert is_section_heading("Conclusion") is True
    assert is_section_heading("## Crystallographic Refinement") is True
    assert is_section_heading("This is a normal declarative sentence.") is False


def test_latex_parser_and_reference_stripping():
    tex = (
        "\\section{Experimental Setup}\n"
        "Samples ($n = 18$) were cooled to $4$~K~\\cite{matoba2018} (Table~\\ref{tab:one}).\n\n"
        "\\section{Conclusion}\n"
        "Furthermore, this framework paves the way for scalable deployment.\n"
    )
    cleaned = parse_latex(tex)
    assert "## Experimental Setup" in cleaned
    assert "## Conclusion" in cleaned
    assert "[1]" in cleaned
    assert "\\cite" not in cleaned

    passages = build_passages(cleaned, min_passage_words=5)
    assert len(passages) == 2
    assert passages[0].section_heading == "Experimental Setup"
    assert passages[1].section_heading == "Conclusion"

    doc_with_refs = "\n".join(
        [f"Paragraph line {i} with sufficient words to pass length threshold." for i in range(10)]
        + ["References", "1. Author A. Journal 2020; 12:34-40."]
    )
    trimmed, was_stripped = strip_references_section(doc_with_refs)
    assert was_stripped is True
    assert "Author A." not in trimmed


def test_structural_triggers_offset_integrity():
    ai_text = (
        "Recent advancements in nanomaterials have revolutionized the landscape of drug delivery. "
        "Furthermore, surface functionalization plays a pivotal role in enhancing uptake, "
        "underscoring the transformative potential of targeted carriers."
    )
    info = analyze_structure(ai_text)
    assert info["structural_ai_prob"] >= 0.65
    assert len(info["triggers"]) >= 4
    for trig in info["triggers"]:
        assert ai_text[trig["start"] : trig["end"]] == trig["matched_text"]


def test_surgical_cleanup_preserves_numbers():
    src = "Furthermore, leveraging 12.5 mM buffer plays a pivotal role in stabilizing pH, underscoring its value."
    cleaned = build_surgical_cleanup_draft(src)
    assert "12.5 mM" in cleaned
    assert "Furthermore" not in cleaned
    assert "plays a pivotal role" not in cleaned


def test_detector_structural_fallback_separates_human_and_ai():
    det = SciGramDetector(cache_dir="/tmp/scigram_no_weights_test", auto_download=False)
    human_txt = (
        "We measured Hall resistivity in six exfoliated flakes between 1.6 K and 40 K (Fig. 2b; p = 0.003). "
        "Contact resistance above 4 kOhm degraded quantization in two devices. "
        "Annealing at 220 C for 30 min restored ohmic behavior across all terminals."
    )
    ai_txt = (
        "In the rapidly evolving realm of quantum materials, topological insulators have garnered significant attention. "
        "Furthermore, delving into the intricate interplay between spin-orbit coupling and symmetry protection plays a "
        "pivotal role in advancing spintronics, paving the way for next-generation low-power devices."
    )
    h_res = det.analyze(human_txt)
    a_res = det.analyze(ai_txt)
    assert h_res["overall_ai_score"] < a_res["overall_ai_score"]
    assert h_res["overall_classification"] == "human"
    assert a_res["overall_classification"] in ("ai_assisted", "ai_generated")
