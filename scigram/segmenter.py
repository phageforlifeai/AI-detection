"""
Scientific-aware sentence splitter and Pangram-style passage builder.
Preserves exact character spans and handles academic abbreviations
(et al., Fig., Eq., vs., i.e., e.g., ca., p < 0.05, author initials).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional


SCI_ABBREVIATIONS = {
    "al", "fig", "figs", "eq", "eqs", "ref", "refs", "tab", "tabs",
    "sec", "secs", "ch", "dr", "prof", "mr", "mrs", "ms", "vs", "v",
    "etc", "approx", "ca", "cf", "wt", "vol", "vols", "no", "nos",
    "pp", "ed", "eds", "sp", "spp", "subsp", "var", "st", "inc",
    "ltd", "co", "corp", "dept", "univ", "assn", "jan", "feb", "mar",
    "apr", "jun", "jul", "aug", "sep", "sept", "oct", "nov", "dec",
}


@dataclass
class SentenceSpan:
    text: str
    start: int  # character offset relative to passage text
    end: int
    word_count: int


@dataclass
class PassageUnit:
    index: int
    section_heading: Optional[str]
    text: str
    word_count: int
    sentences: List[SentenceSpan] = field(default_factory=list)
    is_heading_only: bool = False


def count_words(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*", text))


def is_section_heading(paragraph: str) -> bool:
    """Detect standalone academic section titles like '1. Introduction' or 'Materials and Methods'."""
    s = paragraph.strip()
    if not s or "\n" in s or len(s) > 95:
        return False
    if s.startswith("#"):
        return True
    words = s.split()
    if len(words) > 10:
        return False
    # Ends with terminal prose punctuation? Usually a sentence unless numbered heading without period at end
    if s.endswith((".", "?", "!", ";")) and not re.match(r"^[IVX0-9]+(\.\d+)*\.\s+[A-Z]", s):
        return False
    known_headers = {
        "abstract", "summary", "introduction", "background", "related work",
        "literature review", "materials and methods", "methods", "methodology",
        "experimental section", "experimental setup", "experimental results",
        "experiments", "results", "results and discussion", "discussion",
        "limitations", "conclusion", "conclusions", "acknowledgments",
        "acknowledgements", "data availability", "author contributions",
        "supplementary information", "statistical analysis",
    }
    cleaned = re.sub(r"^(?:[IVXLC]+[.):]\s+|\d+(?:\.\d+)*[.):]?\s+)", "", s).strip().lower().rstrip(":")
    if cleaned in known_headers:
        return True
    # Numbered title-case heading e.g. "2.1 Cohort Selection and Preprocessing"
    if re.match(r"^\d+(?:\.\d+)*\.?\s+[A-Z][A-Za-z0-9,\-: /()]+$", s) and not s.endswith("."):
        return True
    return False


def split_scientific_sentences(text: str) -> List[SentenceSpan]:
    """
    Split scientific text into sentences with exact character offsets [start, end),
    avoiding false splits on abbreviations, initials, decimals, and citations.
    """
    if not text.strip():
        return []

    spans: List[SentenceSpan] = []
    n = len(text)
    sent_start = 0
    # Advance leading whitespace
    while sent_start < n and text[sent_start].isspace():
        sent_start += 1

    i = sent_start
    while i < n:
        ch = text[i]
        if ch in ".!?":
            # Check ellipsis "..."
            if ch == "." and i + 1 < n and text[i + 1] == ".":
                while i + 1 < n and text[i + 1] == ".":
                    i += 1
                i += 1
                continue

            # Check decimal number e.g. 3.14
            if ch == "." and i > 0 and i + 1 < n and text[i - 1].isdigit() and text[i + 1].isdigit():
                i += 1
                continue

            # Include closing quotes/brackets/citations immediately after punctuation e.g. ." or .) or .[12]
            end_punct = i + 1
            while end_punct < n and text[end_punct] in "\"'\u201d\u2019)]}":
                end_punct += 1

            # Must be followed by whitespace or end-of-text to split
            if end_punct < n and not text[end_punct].isspace():
                # Could be e.g. or i.e.
                i += 1
                continue

            # Extract preceding word before '.'
            if ch == ".":
                prev_slice = text[sent_start:i]
                m_word = re.search(r"([A-Za-z]+(?:\.[A-Za-z]+)*)$", prev_slice)
                if m_word:
                    w = m_word.group(1)
                    w_low = w.lower()
                    # Multi-dot abbreviation like e.g., i.e., Ph.D., U.S.
                    if "." in w_low or w_low in SCI_ABBREVIATIONS:
                        i = end_punct
                        continue
                    # Single uppercase initial followed by uppercase name, e.g. "J. Smith"
                    if len(w) == 1 and w.isupper():
                        rest = text[end_punct:].lstrip()
                        if rest and rest[0].isupper():
                            i = end_punct
                            continue

                # Look ahead: in scientific prose, a new sentence starts with Uppercase, digit, '[', '(', quote, or Greek/math
                rest = text[end_punct:].lstrip()
                if rest and rest[0].islower():
                    # Usually an abbreviation followed by lowercase continuation (e.g., "et al. showed")
                    i = end_punct
                    continue

            # Valid sentence boundary!
            seg = text[sent_start:end_punct]
            wc = count_words(seg)
            if seg.strip():
                spans.append(SentenceSpan(text=seg, start=sent_start, end=end_punct, word_count=wc))
            sent_start = end_punct
            while sent_start < n and text[sent_start].isspace():
                sent_start += 1
            i = sent_start
            continue

        i += 1

    # Trailing text without terminal punctuation
    if sent_start < n:
        tail = text[sent_start:n].rstrip()
        if tail:
            spans.append(
                SentenceSpan(
                    text=tail,
                    start=sent_start,
                    end=sent_start + len(tail),
                    word_count=count_words(tail),
                )
            )

    return spans


def build_passages(
    text: str,
    min_passage_words: int = 50,
    max_passage_words: int = 240,
) -> List[PassageUnit]:
    """
    Segment a document into Pangram-style passages (~55-260 words) while
    preserving paragraph coherence and tracking section headings.
    """
    raw_blocks = [b.strip() for b in re.split(r"\n\s*\n+", text.strip()) if b.strip()]
    if not raw_blocks:
        return []

    # Handle case where user pasted single-newline separated paragraphs
    expanded_blocks: List[str] = []
    for block in raw_blocks:
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if len(lines) > 1:
            curr: List[str] = []
            for ln in lines:
                if is_section_heading(ln):
                    if curr:
                        expanded_blocks.append(" ".join(curr))
                        curr = []
                    expanded_blocks.append(ln)
                elif count_words(ln) >= 35 and ln.endswith((".", "!", "?")):
                    curr.append(ln)
                    expanded_blocks.append(" ".join(curr))
                    curr = []
                else:
                    curr.append(ln)
            if curr:
                expanded_blocks.append(" ".join(curr))
        else:
            expanded_blocks.append(block)

    passages: List[PassageUnit] = []
    current_heading: Optional[str] = None
    buffer_paras: List[str] = []
    buffer_words = 0

    def flush_buffer():
        nonlocal buffer_paras, buffer_words, current_heading
        if not buffer_paras:
            return
        joined = "\n\n".join(buffer_paras)
        # If joined block is very long (> max_passage_words * 1.35), split cleanly at sentence boundaries
        sents = split_scientific_sentences(joined)
        if count_words(joined) > int(max_passage_words * 1.35) and len(sents) >= 4:
            chunk_sents: List[SentenceSpan] = []
            chunk_wc = 0
            first_chunk = True
            for s in sents:
                chunk_sents.append(s)
                chunk_wc += s.word_count
                if chunk_wc >= 120:
                    c_start = chunk_sents[0].start
                    c_end = chunk_sents[-1].end
                    c_text = joined[c_start:c_end].strip()
                    c_resplit = split_scientific_sentences(c_text)
                    passages.append(
                        PassageUnit(
                            index=len(passages),
                            section_heading=current_heading if first_chunk else None,
                            text=c_text,
                            word_count=count_words(c_text),
                            sentences=c_resplit,
                        )
                    )
                    first_chunk = False
                    chunk_sents = []
                    chunk_wc = 0
            if chunk_sents:
                c_start = chunk_sents[0].start
                c_end = chunk_sents[-1].end
                c_text = joined[c_start:c_end].strip()
                if passages and count_words(c_text) < 35 and not first_chunk:
                    # Merge tiny tail back into previous passage
                    prev = passages[-1]
                    merged = prev.text + " " + c_text
                    prev.text = merged
                    prev.word_count = count_words(merged)
                    prev.sentences = split_scientific_sentences(merged)
                else:
                    passages.append(
                        PassageUnit(
                            index=len(passages),
                            section_heading=current_heading if first_chunk else None,
                            text=c_text,
                            word_count=count_words(c_text),
                            sentences=split_scientific_sentences(c_text),
                        )
                    )
        else:
            passages.append(
                PassageUnit(
                    index=len(passages),
                    section_heading=current_heading,
                    text=joined,
                    word_count=count_words(joined),
                    sentences=sents,
                )
            )
        current_heading = None
        buffer_paras = []
        buffer_words = 0

    for block in expanded_blocks:
        if is_section_heading(block):
            flush_buffer()
            current_heading = block.lstrip("#").strip()
            continue

        wc = count_words(block)
        if buffer_paras and (buffer_words + wc > max_passage_words) and buffer_words >= min_passage_words:
            flush_buffer()

        buffer_paras.append(block)
        buffer_words += wc

        if buffer_words >= min_passage_words:
            flush_buffer()

    flush_buffer()

    # Re-index cleanly
    for idx, p in enumerate(passages):
        p.index = idx

    return passages
