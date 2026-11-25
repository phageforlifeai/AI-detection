"""
Pangram-Style 3-Expert Mixture-of-Experts (MoE) AI Content & Structure Detector.

Experts:
  1. TMR-RoBERTa (INT8 ONNX): Target Mining RoBERTa trained with Focal Loss &
     Self-Hard-Negative iterative mining on the RAID benchmark.
  2. E5-Small-LoRA (INT8 ONNX): Academic/semantic cadence transformer detector.
  3. SciStructure: 7-dimension scientific stylometric, burstiness & excess-vocab analyzer.

Includes a Scientific Calibration Gate to prevent false positives on formal,
empirically dense non-native or journal-style prose while maintaining high
sensitivity to both raw AI generation and AI-assisted polishing.
"""

from __future__ import annotations

import json
import os
import threading
import time
from typing import Dict, Any, List, Optional

import numpy as np

from .parsers import clean_for_neural_model, parse_latex
from .segmenter import build_passages, split_scientific_sentences, count_words, PassageUnit
from .stylometrics import analyze_structure
from .coach import generate_passage_coaching, generate_document_recommendations


DEFAULT_CACHE_DIR = os.environ.get(
    "SCIGRAM_MODEL_DIR", os.path.expanduser("~/.cache/scigram_models")
)

MODEL_SPECS = {
    "tmr": {
        "repo": "onnx-community/tmr-ai-text-detector-ONNX",
        "files": {
            "tokenizer.json": "tokenizer.json",
            "config.json": "config.json",
            "onnx/model_quantized.onnx": "model_quantized.onnx",
        },
        "temperature": 1.65,
    },
    "e5": {
        "repo": "onnx-community/e5-small-lora-ai-generated-detector-ONNX",
        "files": {
            "tokenizer.json": "tokenizer.json",
            "config.json": "config.json",
            "onnx/model_quantized.onnx": "model_quantized.onnx",
        },
        "temperature": 1.15,
    },
}


class NeuralExpert:
    """Wrapper around an INT8 quantized ONNX sequence classification transformer."""

    def __init__(self, model_dir: str, temperature: float = 1.0):
        import onnxruntime as ort
        from tokenizers import Tokenizer

        self.temperature = temperature
        self.tokenizer = Tokenizer.from_file(os.path.join(model_dir, "tokenizer.json"))
        self.tokenizer.enable_truncation(max_length=512)

        sess_opts = ort.SessionOptions()
        sess_opts.intra_op_num_threads = 2
        sess_opts.inter_op_num_threads = 1
        sess_opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

        onnx_path = os.path.join(model_dir, "model_quantized.onnx")
        self.session = ort.InferenceSession(
            onnx_path, sess_opts, providers=["CPUExecutionProvider"]
        )
        self.input_names = {inp.name for inp in self.session.get_inputs()}

    def predict_ai_prob(self, text: str) -> float:
        cleaned = clean_for_neural_model(text)
        if not cleaned:
            return 0.0
        enc = self.tokenizer.encode(cleaned)
        if len(enc.ids) < 3:
            return 0.0

        feed = {
            "input_ids": np.array([enc.ids], dtype=np.int64),
            "attention_mask": np.array([enc.attention_mask], dtype=np.int64),
        }
        if "token_type_ids" in self.input_names:
            feed["token_type_ids"] = np.array([enc.type_ids], dtype=np.int64)

        logits = self.session.run(None, feed)[0][0].astype(np.float64)
        scaled = logits / self.temperature
        exp = np.exp(scaled - np.max(scaled))
        probs = exp / np.sum(exp)
        return float(probs[1])


class SciGramDetector:
    """
    Singleton-friendly Mixture-of-Experts detector combining TMR-RoBERTa,
    E5-Small-LoRA, and SciStructure for passage- and sentence-level classification.
    """

    def __init__(self, cache_dir: str = DEFAULT_CACHE_DIR, auto_download: bool = True):
        self.cache_dir = cache_dir
        self.auto_download = auto_download
        self._lock = threading.Lock()
        self._loaded = False
        self.neural_available = False
        self.tmr: Optional[NeuralExpert] = None
        self.e5: Optional[NeuralExpert] = None
        self.load_error: Optional[str] = None

    def ensure_loaded(self) -> None:
        if self._loaded:
            return
        with self._lock:
            if self._loaded:
                return
            try:
                self._ensure_model_files()
                self.tmr = NeuralExpert(
                    os.path.join(self.cache_dir, "tmr"),
                    temperature=MODEL_SPECS["tmr"]["temperature"],
                )
                self.e5 = NeuralExpert(
                    os.path.join(self.cache_dir, "e5"),
                    temperature=MODEL_SPECS["e5"]["temperature"],
                )
                self.neural_available = True
            except Exception as exc:
                self.neural_available = False
                self.load_error = str(exc)
            finally:
                self._loaded = True

    def _ensure_model_files(self) -> None:
        import requests

        for key, spec in MODEL_SPECS.items():
            sub_dir = os.path.join(self.cache_dir, key)
            os.makedirs(sub_dir, exist_ok=True)
            for remote_rel, local_name in spec["files"].items():
                dest = os.path.join(sub_dir, local_name)
                if not os.path.exists(dest) or os.path.getsize(dest) == 0:
                    if not self.auto_download:
                        raise FileNotFoundError(f"Missing model file: {dest}")
                    url = f"https://huggingface.co/{spec['repo']}/resolve/main/{remote_rel}"
                    resp = requests.get(url, timeout=90)
                    resp.raise_for_status()
                    tmp_dest = dest + ".part"
                    with open(tmp_dest, "wb") as f:
                        f.write(resp.content)
                    os.replace(tmp_dest, dest)

    def _fuse_experts(
        self,
        p_tmr: Optional[float],
        p_e5: Optional[float],
        struct_info: Dict[str, Any],
    ) -> Dict[str, Any]:
        p_struct = struct_info["structural_ai_prob"]
        anchors_rate = struct_info["anchors_per_100w"]
        high_sev_triggers = (
            struct_info["trigger_counts"]["excess_vocab_high"]
            + struct_info["trigger_counts"]["participial_tail"]
            + struct_info["trigger_counts"]["boilerplate_template"]
        )

        if p_tmr is None or p_e5 is None:
            # Fallback if running strictly offline without ONNX weights
            fused = p_struct
            confidence = "Medium (Structural Only)"
            calibration_shield = False
        else:
            calibration_shield = False
            # Scientific Calibration Gate:
            # Protect formal, empirically anchored scientific prose when TMR fires alone
            # while E5 and SciStructure both see low AI patterns.
            if (
                p_tmr >= 0.65
                and p_e5 <= 0.52
                and p_struct <= 0.26
                and high_sev_triggers == 0
            ):
                fused = 0.18 * p_tmr + 0.47 * p_e5 + 0.35 * p_struct
                calibration_shield = True
            else:
                fused = 0.44 * p_tmr + 0.30 * p_e5 + 0.26 * p_struct

                # Dual-neural consensus boost (catches low-buzzword modern LLM generations)
                if p_tmr >= 0.78 and p_e5 >= 0.72:
                    neural_mean = 0.55 * p_tmr + 0.45 * p_e5
                    fused = max(fused, 0.72 + 0.26 * ((neural_mean - 0.74) / 0.26))
                # Dual-neural + structural consensus for AI-Assisted prose
                elif (p_tmr >= 0.65 and p_struct >= 0.35) or (p_e5 >= 0.62 and p_struct >= 0.38):
                    fused = max(fused, 0.44 + 0.25 * p_struct)
                # Strong 3-expert human agreement
                elif p_tmr <= 0.28 and p_e5 <= 0.42 and p_struct <= 0.30:
                    fused = min(fused, 0.24)

            # Short passage (<35 words) uncertainty dampening toward neutral-human unless triggers exist
            if struct_info["word_count"] < 35 and high_sev_triggers == 0:
                fused = 0.65 * fused + 0.35 * 0.25

            fused = float(max(0.01, min(0.99, fused)))

            # Confidence estimation from inter-expert agreement and distance from boundaries
            spread = float(np.std([p_tmr, p_e5, p_struct]))
            if spread < 0.16 and (fused <= 0.25 or fused >= 0.76):
                confidence = "High"
            elif spread < 0.26:
                confidence = "Medium-High"
            else:
                confidence = "Moderate"

        if fused < 0.38:
            classification = "human"
            label = "Human-Written"
        elif fused < 0.70:
            classification = "ai_assisted"
            label = "AI-Assisted"
        else:
            classification = "ai_generated"
            label = "AI-Generated"

        return {
            "ai_score": round(fused, 4),
            "classification": classification,
            "label": label,
            "confidence": confidence,
            "calibration_shield": calibration_shield,
            "experts": {
                "tmr_roberta": round(p_tmr, 4) if p_tmr is not None else None,
                "e5_lora": round(p_e5, 4) if p_e5 is not None else None,
                "sci_structure": round(p_struct, 4),
            },
        }

    def _score_sentences_in_passage(
        self,
        passage: PassageUnit,
        passage_fusion: Dict[str, Any],
        passage_triggers: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Score each sentence within a passage using contextual 2-sentence windows
        plus local sentence-level structural triggers.
        """
        sents = passage.sentences
        if not sents:
            return []

        n = len(sents)
        p_prior = passage_fusion["ai_score"]

        # Compute 2-sentence sliding window neural scores when passage has >= 2 sentences
        window_neural: List[float] = []
        if self.neural_available and self.tmr and self.e5 and n >= 2:
            for i in range(n - 1):
                win_txt = sents[i].text + " " + sents[i + 1].text
                if count_words(win_txt) >= 14:
                    wt = self.tmr.predict_ai_prob(win_txt)
                    we = self.e5.predict_ai_prob(win_txt)
                    window_neural.append(0.55 * wt + 0.45 * we)
                else:
                    window_neural.append(p_prior)

        sent_results: List[Dict[str, Any]] = []
        for idx, s in enumerate(sents):
            # Collect triggers overlapping this sentence
            s_trigs = [
                t
                for t in passage_triggers
                if not (t["end"] <= s.start or t["start"] >= s.end)
            ]
            high_t = sum(1 for t in s_trigs if t["severity"] == "high")
            med_t = sum(1 for t in s_trigs if t["severity"] == "medium")
            local_boost = min(0.42, high_t * 0.18 + med_t * 0.09)

            if window_neural:
                touching = []
                if idx - 1 >= 0:
                    touching.append(window_neural[idx - 1])
                if idx < len(window_neural):
                    touching.append(window_neural[idx])
                local_neural = sum(touching) / len(touching) if touching else p_prior
                s_score = 0.45 * local_neural + 0.35 * p_prior + local_boost
                if high_t == 0 and med_t == 0:
                    s_score = 0.55 * local_neural + 0.45 * p_prior
            else:
                s_score = p_prior + (local_boost * 0.5 if local_boost > 0 else 0.0)

            s_score = float(max(0.01, min(0.99, s_score)))
            if s_score < 0.38:
                s_cls = "human"
            elif s_score < 0.70:
                s_cls = "ai_assisted"
            else:
                s_cls = "ai_generated"

            sent_results.append(
                {
                    "index": idx,
                    "text": s.text,
                    "start": s.start,
                    "end": s.end,
                    "word_count": s.word_count,
                    "ai_score": round(s_score, 4),
                    "classification": s_cls,
                    "trigger_count": len(s_trigs),
                }
            )

        return sent_results

    def analyze(self, text: str, include_sentences: bool = True) -> Dict[str, Any]:
        """
        Full Pangram-style document analysis:
        - Splits document into coherent passages
        - Runs 3-expert MoE classification on each passage (Human / AI-Assisted / AI-Generated)
        - Computes sentence-level scores and character-accurate structural triggers
        - Produces whole-document breakdown, structural diagnostics, and coaching tips
        """
        t0 = time.time()
        self.ensure_loaded()

        raw_input = text.strip()
        latex_detected = bool(
            "\\section" in raw_input
            or "\\subsection" in raw_input
            or "\\begin{document}" in raw_input
            or "\\cite{" in raw_input
            or "\\citep{" in raw_input
            or "\\citet{" in raw_input
        )
        clean_input = parse_latex(raw_input) if latex_detected else raw_input
        total_words = count_words(clean_input)
        if total_words == 0:
            return {
                "error": "Please enter or upload scientific text to analyze.",
                "word_count": 0,
            }

        short_text_warning = total_words < 50
        passages = build_passages(clean_input)
        all_sentences = split_scientific_sentences(clean_input)
        doc_struct = analyze_structure(clean_input, all_sentences)

        passage_results: List[Dict[str, Any]] = []
        words_by_class = {"human": 0, "ai_assisted": 0, "ai_generated": 0}
        weighted_ai_sum = 0.0
        total_passage_words = 0

        for p in passages:
            p_struct = analyze_structure(p.text, p.sentences)
            if self.neural_available and self.tmr and self.e5:
                p_tmr = self.tmr.predict_ai_prob(p.text)
                p_e5 = self.e5.predict_ai_prob(p.text)
            else:
                p_tmr, p_e5 = None, None

            fusion = self._fuse_experts(p_tmr, p_e5, p_struct)
            cls = fusion["classification"]
            wc = max(1, p.word_count)
            words_by_class[cls] += wc
            weighted_ai_sum += fusion["ai_score"] * wc
            total_passage_words += wc

            sent_scores = (
                self._score_sentences_in_passage(p, fusion, p_struct["triggers"])
                if include_sentences
                else []
            )
            coaching = generate_passage_coaching(
                p.text, cls, fusion["ai_score"], p_struct
            )

            passage_results.append(
                {
                    "index": p.index,
                    "section_heading": p.section_heading,
                    "text": p.text,
                    "word_count": p.word_count,
                    "ai_score": fusion["ai_score"],
                    "ai_score_pct": round(fusion["ai_score"] * 100, 1),
                    "classification": cls,
                    "label": fusion["label"],
                    "confidence": fusion["confidence"],
                    "calibration_shield": fusion["calibration_shield"],
                    "experts": fusion["experts"],
                    "structure": p_struct,
                    "sentences": sent_scores,
                    "coaching": coaching,
                }
            )

        denom = max(1, total_passage_words)
        overall_ai_score = weighted_ai_sum / denom
        breakdown_pct = {
            "human": round((words_by_class["human"] / denom) * 100.0, 1),
            "ai_assisted": round((words_by_class["ai_assisted"] / denom) * 100.0, 1),
            "ai_generated": round((words_by_class["ai_generated"] / denom) * 100.0, 1),
        }
        # Ensure percentages sum cleanly to 100.0
        diff = round(100.0 - sum(breakdown_pct.values()), 1)
        if abs(diff) > 0:
            top_key = max(breakdown_pct, key=lambda k: breakdown_pct[k])
            breakdown_pct[top_key] = round(breakdown_pct[top_key] + diff, 1)

        if breakdown_pct["ai_generated"] >= 45.0 or overall_ai_score >= 0.70:
            overall_verdict = "AI-Generated"
            overall_class = "ai_generated"
        elif (
            breakdown_pct["ai_generated"] + breakdown_pct["ai_assisted"] >= 30.0
            or overall_ai_score >= 0.38
        ):
            overall_verdict = "AI-Assisted / Mixed"
            overall_class = "ai_assisted"
        else:
            overall_verdict = "Human-Written"
            overall_class = "human"

        recommendations = generate_document_recommendations(
            overall_ai_score, doc_struct, passage_results
        )

        elapsed_ms = round((time.time() - t0) * 1000.0, 1)

        return {
            "word_count": total_words,
            "sentence_count": len(all_sentences),
            "passage_count": len(passage_results),
            "latex_detected": latex_detected,
            "short_text_warning": short_text_warning,
            "overall_ai_score": round(overall_ai_score, 4),
            "overall_ai_pct": round(overall_ai_score * 100.0, 1),
            "overall_verdict": overall_verdict,
            "overall_classification": overall_class,
            "breakdown_pct": breakdown_pct,
            "words_by_class": words_by_class,
            "document_structure": doc_struct,
            "recommendations": recommendations,
            "passages": passage_results,
            "engine_info": {
                "neural_active": self.neural_available,
                "experts": [
                    "TMR-RoBERTa (RAID Hard-Negative INT8)",
                    "E5-Small-LoRA (Academic Cadence INT8)",
                    "SciStructure (7-Dim Scientific Stylometrics)",
                ],
                "latency_ms": elapsed_ms,
            },
        }


_GLOBAL_DETECTOR: Optional[SciGramDetector] = None


def get_detector() -> SciGramDetector:
    global _GLOBAL_DETECTOR
    if _GLOBAL_DETECTOR is None:
        _GLOBAL_DETECTOR = SciGramDetector()
    return _GLOBAL_DETECTOR
