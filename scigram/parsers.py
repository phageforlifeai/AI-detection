"""
Document parsers for scientific manuscripts (.txt, .md, .tex, .docx, .pdf).
Preserves paragraph boundaries and empirical markers (citations, numbers, units,
equations) while stripping formatting noise that can confuse neural tokenizers.
"""

from __future__ import annotations

import io
import re
from html import unescape
from typing import Tuple, Dict, Any


LIGATURES = {
    "\ufb00": "ff",
    "\ufb01": "fi",
    "\ufb02": "fl",
    "\ufb03": "ffi",
    "\ufb04": "ffl",
    "\u2013": "-",
    "\u2014": " -- ",
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u00a0": " ",
}


def normalize_unicode(text: str) -> str:
    for src, dst in LIGATURES.items():
        text = text.replace(src, dst)
    return text


def parse_latex(tex: str) -> str:
    """
    Convert a LaTeX manuscript into clean readable scientific prose while
    retaining empirical anchors ([cite], [Eq.], inline variables/numbers)
    and paragraph/section boundaries.
    """
    tex = normalize_unicode(tex)

    # Extract \begin{document} ... \end{document} if present
    doc_match = re.search(
        r"\\begin\{document\}(.*?)\\end\{document\}", tex, flags=re.DOTALL
    )
    if doc_match:
        tex = doc_match.group(1)

    # Strip LaTeX comments (unescaped %)
    tex = re.sub(r"(?<!\\)%[^\n]*", "", tex)

    # Remove non-prose environments (tables, figures/tikz, bibliography, algorithms)
    for env in [
        "thebibliography",
        "tikzpicture",
        "tabular",
        "tabular*",
        "longtable",
        "algorithm",
        "algorithmic",
        "lstlisting",
        "verbatim",
    ]:
        tex = re.sub(
            rf"\\begin\{{{re.escape(env)}\}}.*?\\end\{{{re.escape(env)}\}}",
            "\n\n",
            tex,
            flags=re.DOTALL,
        )

    # Replace display math environments with [Eq.]
    for math_env in ["equation", "equation*", "align", "align*", "gather", "gather*", "multline", "multline*"]:
        tex = re.sub(
            rf"\\begin\{{{re.escape(math_env)}\}}.*?\\end\{{{re.escape(math_env)}\}}",
            " [Eq.] ",
            tex,
            flags=re.DOTALL,
        )
    tex = re.sub(r"\$\$.*?\$\$", " [Eq.] ", tex, flags=re.DOTALL)
    tex = re.sub(r"\\\[.*?\\\]", " [Eq.] ", tex, flags=re.DOTALL)

    # Preserve inline math numbers/variables softly or mark complex math
    def clean_inline_math(match: re.Match) -> str:
        inner = match.group(1).strip()
        # Keep short numerical/variable expressions readable (e.g., $p < 0.01$, $n = 42$)
        inner_clean = re.sub(r"\\(approx|sim|pm|times|cdot|leq|geq|neq)", " ", inner)
        inner_clean = re.sub(r"\\[a-zA-Z]+", "", inner_clean)
        inner_clean = re.sub(r"[{}^_]", "", inner_clean).strip()
        if 0 < len(inner_clean) <= 28:
            return f" {inner_clean} "
        return " [math] "

    tex = re.sub(r"\$([^$]+)\$", clean_inline_math, tex)

    # Convert section headings to clean Markdown section breaks
    tex = re.sub(
        r"\\(?:sub)*section\*?\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}",
        r"\n\n## \1\n\n",
        tex,
    )
    tex = re.sub(
        r"\\begin\{abstract\}(.*?)\\end\{abstract\}",
        r"\n\n## Abstract\n\n\1\n\n",
        tex,
        flags=re.DOTALL,
    )

    # Preserve common scientific LaTeX macros before stripping commands
    tex = re.sub(r"\\AA\b", "A", tex)
    tex = re.sub(r"--", "-", tex)

    # Citations -> numbered academic bracket citations [1], [2], ...
    cite_counter = [0]

    def _num_cite(_m: re.Match) -> str:
        cite_counter[0] += 1
        return f" [{cite_counter[0]}]"

    tex = re.sub(r"~?\\cite[a-zA-Z*]*(\[[^\]]*\])*\{[^}]+\}", _num_cite, tex)
    tex = re.sub(r"~?\\(?:auto|C|c|eq)?ref\{[^}]+\}", " 1", tex)

    # Unwrap formatting commands (\textbf{...}, \emph{...}, \textit{...}, \textrm{...})
    for _ in range(3):
        tex = re.sub(
            r"\\(?:textbf|textit|emph|textrm|textsf|texttt|underline|textsc)\{([^{}]*)\}",
            r"\1",
            tex,
        )

    # Remove remaining standalone commands like \label{}, \maketitle, \noindent, \item
    tex = re.sub(r"\\(?:label|bibliographystyle|bibliography|usepackage|documentclass)(\[[^\]]*\])*\{[^}]*\}", "", tex)
    tex = re.sub(r"\\item\b", "\n", tex)
    tex = re.sub(r"\\[a-zA-Z@]+\*?", " ", tex)
    tex = re.sub(r"[{}~]", " ", tex)

    # Normalize whitespace while preserving paragraph breaks
    tex = re.sub(r"[ \t]+", " ", tex)
    tex = re.sub(r"\s+([,.;:?!])", r"\1", tex)
    tex = re.sub(r"\n\s*\n+", "\n\n", tex)
    return tex.strip()


def strip_references_section(text: str) -> Tuple[str, bool]:
    """
    Detect and strip a trailing References / Bibliography / Works Cited section
    so citation lists do not distort prose AI-detection or burstiness scores.
    """
    lines = text.splitlines()
    if len(lines) < 8:
        return text, False

    # Look in the last 45% of the document for a standalone References header
    search_start = max(3, int(len(lines) * 0.50))
    ref_pattern = re.compile(
        r"^\s*(?:\d+\.?\s*)?(?:references|bibliography|works cited|literature cited)\s*$",
        re.IGNORECASE,
    )
    for idx in range(search_start, len(lines)):
        if ref_pattern.match(lines[idx].strip()):
            trimmed = "\n".join(lines[:idx]).strip()
            if len(trimmed.split()) >= 50:
                return trimmed, True
    return text, False


def parse_docx_bytes(data: bytes) -> str:
    import docx

    doc = docx.Document(io.BytesIO(data))
    paragraphs = []
    for p in doc.paragraphs:
        txt = normalize_unicode(p.text).strip()
        if txt:
            paragraphs.append(txt)
    return "\n\n".join(paragraphs)


def parse_pdf_bytes(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    pages_text = []
    for page in reader.pages:
        raw = page.extract_text() or ""
        raw = normalize_unicode(raw)
        # Rejoin hyphenated line breaks common in two-column scientific PDFs
        raw = re.sub(r"([a-zA-Z])-\n([a-z])", r"\1\2", raw)
        pages_text.append(raw)

    combined = "\n\n".join(pages_text)
    # Reconstruct paragraphs: single newline inside running prose -> space,
    # blank lines or lines ending with period + short line -> paragraph break
    lines = combined.splitlines()
    rebuilt = []
    buf = []
    for line in lines:
        s = line.strip()
        if not s:
            if buf:
                rebuilt.append(" ".join(buf))
                buf = []
            continue
        # Skip isolated page numbers or running headers < 4 chars
        if re.match(r"^\d{1,4}$", s):
            continue
        buf.append(s)
        # Heuristic paragraph boundary if line ends with sentence punctuation and is noticeably shorter
        if s.endswith((".", "!", "?")) and len(s) < 62 and len(" ".join(buf).split()) >= 35:
            rebuilt.append(" ".join(buf))
            buf = []
    if buf:
        rebuilt.append(" ".join(buf))

    return "\n\n".join(rebuilt)


def clean_for_neural_model(text: str) -> str:
    """
    Prepare a passage for neural transformer classification without stripping
    natural punctuation or rhythm, while removing markdown/XML/heading artifacts
    that cause false positives (e.g. glued 'Abstract ' prefixes or markdown stars).
    """
    t = normalize_unicode(text)
    t = re.sub(r"```.*?```", " ", t, flags=re.DOTALL)
    t = re.sub(r"`[^`]*`", " ", t)
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)
    t = re.sub(r"(\*\*|__)(.*?)\1", r"\2", t)
    t = re.sub(r"^#+\s+", "", t, flags=re.MULTILINE)
    t = re.sub(r"^\s*(?:[-*+]|\d+\.)\s+", "", t, flags=re.MULTILINE)
    t = re.sub(r"<[^>]+>", " ", t)
    t = unescape(t)
    # Strip glued leading section label like "Abstract " or "SUMMARY "
    t = re.sub(r"^(?:Abstract|ABSTRACT|Summary|SUMMARY|Introduction|INTRODUCTION)\s*[:.-]?\s+(?=[A-Z])", "", t.strip())
    # Strip glued superscript citation digits at end of lowercase words (e.g. "eradication1,2.")
    t = re.sub(r"([a-z]{3,})\d{1,2}(?:,\d{1,2})*(?=[.,;:)\s])", r"\1", t)
    # Strip bracketed numeric citations [1] or [1, 2] for neural scoring only
    t = re.sub(r"\s*\[\d+(?:\s*[-,–]\s*\d+)*\]", "", t)
    t = t.replace("\n", " ").replace("\r", " ").replace("\t", " ")
    t = re.sub(r"\s+([,.;:?!])", r"\1", t)
    t = re.sub(r"\(\s+", "(", t)
    t = re.sub(r"\s+\)", ")", t)
    t = re.sub(r" {2,}", " ", t)
    return t.strip()


def extract_document_text(
    filename: str, content_bytes: bytes, strip_references: bool = True
) -> Tuple[str, Dict[str, Any]]:
    """
    Extract clean prose from uploaded file (.txt, .md, .tex, .docx, .pdf).
    Returns (extracted_text, metadata_dict).
    """
    ext = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ".txt"
    meta: Dict[str, Any] = {"filename": filename, "format": ext, "references_stripped": False}

    if ext == ".docx":
        text = parse_docx_bytes(content_bytes)
    elif ext == ".pdf":
        text = parse_pdf_bytes(content_bytes)
    elif ext in (".tex", ".latex"):
        raw = content_bytes.decode("utf-8", errors="replace")
        text = parse_latex(raw)
        meta["latex_parsed"] = True
    else:
        text = normalize_unicode(content_bytes.decode("utf-8", errors="replace"))

    if strip_references:
        text, stripped = strip_references_section(text)
        meta["references_stripped"] = stripped

    return text.strip(), meta
