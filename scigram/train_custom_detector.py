"""
Reference Training Pipeline: Custom Pangram-Style Scientific AI Detector
========================================================================
Trains a custom transformer classifier (e.g., RoBERTa-base / DeBERTa-v3) on
paired Human vs. AI-Assisted vs. AI-Generated scientific passages using:

  1. Topic-Matched Pairing: Pairs authentic pre-2022 PubMed/arXiv paragraphs
     with LLM-generated and LLM-polished counterparts on the same topic/length.
  2. Multi-Class or Focal Loss (gamma=2.0, alpha-weighted toward low FPR):
     Penalizes false positives on formal non-native/technical human prose.
  3. Iterative Self-Hard-Negative Mining (Pangram / TMR strategy):
     Evaluates on held-out human scientific papers after Round 1, collects
     misclassified human passages ("hard negatives"), upweights them, and
     fine-tunes Round 2 before exporting an INT8 quantized ONNX model
     drop-in compatible with SciGram (`~/.cache/scigram_models/`).

Requirements (on a GPU workstation / Colab):
    pip install torch transformers datasets accelerate optimum[onnxruntime] scikit-learn

Usage:
    python3 -m scigram.train_custom_detector --data paired_sci_passages.jsonl --output ./custom_scigram_onnx
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Dict


def load_jsonl(path: str) -> List[Dict]:
    """
    Expected JSONL schema per line:
      {"text": "...", "label": 0}   # 0 = human, 1 = ai (or 0=human, 1=ai_assisted, 2=ai_generated)
    """
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def train_with_hard_negative_mining(
    data_path: str,
    output_dir: str,
    base_model: str = "FacebookAI/roberta-base",
    epochs_round1: int = 2,
    epochs_round2: int = 1,
    lr: float = 2e-5,
    batch_size: int = 16,
    focal_gamma: float = 2.0,
    human_alpha: float = 0.80,
) -> None:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from torch.utils.data import Dataset, DataLoader
    from transformers import AutoTokenizer, AutoModelForSequenceClassification

    class FocalLoss(nn.Module):
        """Focal Loss with higher alpha weight on class 0 (Human) to minimize FPR."""

        def __init__(self, alpha_human: float = 0.80, gamma: float = 2.0):
            super().__init__()
            self.alpha = torch.tensor([alpha_human, 1.0 - alpha_human])
            self.gamma = gamma

        def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
            alpha = self.alpha.to(logits.device)
            ce = F.cross_entropy(logits, targets, reduction="none")
            pt = torch.exp(-ce)
            at = alpha.gather(0, targets)
            loss = at * ((1.0 - pt) ** self.gamma) * ce
            return loss.mean()

    class PassageDataset(Dataset):
        def __init__(self, items: List[Dict], tokenizer, max_len: int = 512):
            self.items = items
            self.tok = tokenizer
            self.max_len = max_len

        def __len__(self):
            return len(self.items)

        def __getitem__(self, idx):
            row = self.items[idx]
            enc = self.tok(
                row["text"],
                truncation=True,
                padding="max_length",
                max_length=self.max_len,
                return_tensors="pt",
            )
            return {
                "input_ids": enc["input_ids"].squeeze(0),
                "attention_mask": enc["attention_mask"].squeeze(0),
                "labels": torch.tensor(int(row["label"]), dtype=torch.long),
            }

    rows = load_jsonl(data_path)
    split_idx = int(len(rows) * 0.85)
    train_rows, val_rows = rows[:split_idx], rows[split_idx:]

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tokenizer = AutoTokenizer.from_pretrained(base_model)
    model = AutoModelForSequenceClassification.from_pretrained(
        base_model,
        num_labels=2,
        id2label={0: "human", 1: "ai"},
        label2id={"human": 0, "ai": 1},
    ).to(device)

    criterion = FocalLoss(alpha_human=human_alpha, gamma=focal_gamma)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)

    def run_epochs(dataset_rows: List[Dict], num_epochs: int, tag: str):
        loader = DataLoader(PassageDataset(dataset_rows, tokenizer), batch_size=batch_size, shuffle=True)
        model.train()
        for ep in range(num_epochs):
            total_loss = 0.0
            for batch in loader:
                optimizer.zero_grad()
                out = model(
                    input_ids=batch["input_ids"].to(device),
                    attention_mask=batch["attention_mask"].to(device),
                )
                loss = criterion(out.logits, batch["labels"].to(device))
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                total_loss += loss.item()
            print(f"[{tag}] Epoch {ep + 1}/{num_epochs} | Mean Focal Loss: {total_loss / max(1, len(loader)):.4f}")

    # Round 1: Standard Focal-Loss training
    run_epochs(train_rows, epochs_round1, "Round-1")

    # Mine Self-Hard-Negatives (human passages in train/val pool with P(AI) > 0.35)
    model.eval()
    hard_negatives: List[Dict] = []
    eval_loader = DataLoader(PassageDataset(train_rows, tokenizer), batch_size=batch_size, shuffle=False)
    cursor = 0
    with torch.no_grad():
        for batch in eval_loader:
            logits = model(
                input_ids=batch["input_ids"].to(device),
                attention_mask=batch["attention_mask"].to(device),
            ).logits
            probs_ai = torch.softmax(logits, dim=-1)[:, 1].cpu().tolist()
            for p_ai in probs_ai:
                item = train_rows[cursor]
                if int(item["label"]) == 0 and p_ai >= 0.35:
                    hard_negatives.append(item)
                cursor += 1

    print(f"Mined {len(hard_negatives)} hard-negative human scientific passages for Round-2 refinement.")
    if hard_negatives and epochs_round2 > 0:
        augmented = train_rows + (hard_negatives * 2)
        run_epochs(augmented, epochs_round2, "Round-2-HardNeg")

    # Save HuggingFace checkpoint & export quantized INT8 ONNX for SciGram
    out_path = Path(output_dir)
    hf_dir = out_path / "hf_checkpoint"
    hf_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(hf_dir)
    tokenizer.save_pretrained(hf_dir)
    print(f"Saved fine-tuned checkpoint to {hf_dir}")

    try:
        from optimum.onnxruntime import ORTModelForSequenceClassification, ORTQuantizer
        from optimum.onnxruntime.configuration import AutoQuantizationConfig

        onnx_dir = out_path / "onnx_export"
        ort_model = ORTModelForSequenceClassification.from_pretrained(hf_dir, export=True)
        ort_model.save_pretrained(onnx_dir)
        quantizer = ORTQuantizer.from_pretrained(onnx_dir)
        qconfig = AutoQuantizationConfig.avx512_vnni(is_static=False, per_channel=False)
        quantizer.quantize(save_dir=out_path, quantization_config=qconfig)
        print(f"Exported INT8 quantized ONNX detector to {out_path}")
    except ImportError:
        print("Install `optimum[onnxruntime]` to automatically quantize checkpoint to INT8 ONNX.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Train a custom scientific Pangram-style AI detector.")
    ap.add_argument("--data", required=True, help="Path to JSONL file of paired human/AI scientific passages")
    ap.add_argument("--output", default="./custom_scigram_onnx", help="Output directory for ONNX model")
    ap.add_argument("--base-model", default="FacebookAI/roberta-base")
    args = ap.parse_args()
    train_with_hard_negative_mining(args.data, args.output, base_model=args.base_model)
