# SciGram — Pangram-Style AI Detector & Scientific Structure Analyzer

**SciGram** is an interactive AI-detection and scientific-writing diagnostic suite inspired by **Pangram Labs (Pangram 4)**. It is specifically designed for researchers and scientists who want to:

1. **Detect AI-generated and AI-assisted passages** across long manuscripts (`.tex`, `.docx`, `.pdf`, `.md`, `.txt`) using a **3-Expert Mixture-of-Experts (MoE)** ensemble rather than naive perplexity alone.
2. **Identify and eliminate "AI-like structure"** in scientific prose—such as uniform ~22-word sentence cadence (low burstiness), trailing participial `-ing` commentary tails (*", highlighting..."*, *", underscoring..."*), mechanical conjunctive starters (*"Furthermore,"*, *"Moreover,"*), symmetrical rule-of-three lists, and post-2023 LLM excess vocabulary (*delve, pivotal, intricate, underscore, realm, utilize*).

---

## Architecture: How SciGram Works

Like Pangram 4, SciGram segments documents into coherent **passages** (~55–240 words, respecting section boundaries) and classifies each passage into three tiers:

- **Human-Written** (`< 38%` AI Score)
- **AI-Assisted / Polished** (`38% – 69%` AI Score) — e.g., human empirical data edited or smoothed by an LLM
- **AI-Generated** (`>= 70%` AI Score)

### Mixture of 3 Complementary Experts

| Expert | Role | Technical Basis |
| :--- | :--- | :--- |
| **1. TMR-RoBERTa (INT8 ONNX)** | Token/sequence classifier | `Oxidane/tmr-ai-text-detector` trained on the **RAID benchmark** (including arXiv abstracts & adversarial paraphrases) using **Focal Loss + Self-Hard-Negative iterative mining**—the same hard-negative retraining strategy Pangram uses to suppress false positives. |
| **2. E5-Small-LoRA (INT8 ONNX)** | Academic cadence classifier | `MayZhou/e5-small-lora-ai-generated-detector` providing smooth probability calibration across hybrid/AI-edited academic paragraphs. |
| **3. SciStructure (7-Dim Stylometrics)** | Explainable structural engine | Evaluates **7 peer-reviewed structural signals** (Kobak et al., 2024; Liang et al., 2024; Desaire et al., *Science Advances* 2023): sentence burstiness (`CV`), participial `-ing` tails, discourse starters, excess LLM vocabulary, rhetorical templates, triadic symmetry, and empirical anchor density. |

**Scientific Calibration Gate:** Formal or non-native technical scientific writing is often falsely flagged by student-essay detectors. When `E5-LoRA` and `SciStructure` both confirm organic empirical prose with zero high-severity LLM triggers, SciGram dampens isolated single-model outliers to protect authentic scientific writing.

---

## Quick Start

### 1. Run the Interactive Web Dashboard

```bash
pip install -r requirements.txt
python3 server.py
```

Open `http://localhost:8000` in your browser:
- Paste prose or raw **LaTeX** (`\section{}`, `\cite{}`, `$p < 0.01$`), or drag-and-drop `.tex`, `.docx`, `.pdf`, `.md`, or `.txt` files.
- Switch between **Passage View** (Pangram-style 3-tier blocks) and **Surgical Structure View** (sentence heatmaps + underlined inline structural triggers).
- Click any passage and open the **Live Revision Studio** to strip clichés, rewrite sentences, click **Re-Check Passage**, and watch your AI score drop in real time.

### 2. Run the Command-Line Interface (CLI)

```bash
# Scan a LaTeX, Word, PDF, or Markdown manuscript and save a Markdown report:
python3 -m scigram.cli paper.tex --report scan_report.md --json scan_results.json

# Test on a built-in multi-section scientific preset:
python3 -m scigram.cli --sample mixed_manuscript
```

### 3. Train Your Own Custom Subfield Model (Optional)

If you want to fine-tune a custom detector on paired human vs. LLM passages from your own scientific subfield using **Focal Loss + Iterative Self-Hard-Negative Mining** and export to INT8 ONNX:

```bash
python3 -m scigram.train_custom_detector --data paired_sci_passages.jsonl --output ./custom_scigram_onnx
```

---

## Project Layout

```text
.
├── server.py                        # FastAPI server & REST endpoints (/api/analyze, /api/upload, ...)
├── static/
│   ├── index.html                   # Pangram-inspired interactive dashboard & Live Revision Studio
│   ├── styles.css                   # Editorial scientific UI styles
│   └── app.js                       # Frontend logic, inline span highlighter & local scan history
├── scigram/
│   ├── detector.py                  # 3-Expert MoE fusion, sliding-window sentence scorer & Calibration Gate
│   ├── stylometrics.py              # 7-dimension scientific structural & excess-vocabulary engine
│   ├── coach.py                     # Passage-specific structural coaching & deterministic de-templating
│   ├── segmenter.py                 # Abbreviation-aware scientific sentence & passage splitter
│   ├── parsers.py                   # Extractors for .tex (LaTeX), .docx, .pdf, .md, .txt
│   ├── report.py                    # Markdown diagnostic report exporter
│   ├── cli.py                       # Rich colorized terminal CLI
│   ├── samples.py                   # Built-in scientific presets (Mixed IMRaD, AI Intro, Human, LaTeX)
│   └── train_custom_detector.py     # Reference Focal-Loss + Hard-Negative Mining training pipeline
└── requirements.txt
```
