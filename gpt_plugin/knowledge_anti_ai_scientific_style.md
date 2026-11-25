# Scientific Copyediting Knowledge Guide: Avoiding AI-Like Structure

Upload this file into the **Knowledge** section of your Custom GPT alongside `custom_gpt_instructions.md`. It provides concrete Before/After calibration examples across IMRaD manuscript sections.

---

## 1. Why Standard LLM Editing Triggers AI Detectors (Pangram / SciGram)

When an unguided LLM edits human scientific writing, it alters four statistical properties even when the underlying science is 100% human:

1. **Burstiness Collapse (`CV < 0.28`):** Human researchers mix 8-word empirical statements with 34-word methodological clauses (`CV ~ 0.42–0.65`). Standard GPT editing rewrites every sentence into smooth 21–25 word compound clauses.
2. **Participial Commentary Tails:** Appending `, highlighting...`, `, underscoring...`, or `, paving the way for...` to the end of factual sentences.
3. **Conjunctive Signpost Chaining:** Starting consecutive sentences with `Furthermore,`, `Moreover,`, `Additionally,`, and `Collectively,`.
4. **Post-2023 Excess Vocabulary:** Replacing ordinary academic verbs (`use`, `show`, `limit`, `measure`) with high-excess tokens (`utilize`, `leverage`, `underscore`, `pivotal`, `intricate interplay`, `delve`, `realm`).

---

## 2. Section-by-Section Calibration Examples

### A. Introduction
* **Author's Raw Draft (Non-Native / Rough Grammar):**
  > Battery with solid electrolyte is getting popular because high energy and safe. But interface between lithium metal and ceramic have crack and dendrite when current is high. How grain boundary stress make cell fail is still not clear in experiment.
* **BAD Edit (Typical Unguided GPT — Scores >90% AI-Generated):**
  > *In the rapidly evolving realm of energy storage, solid-state lithium-metal batteries have garnered significant attention due to their superior energy density and enhanced safety profiles. Despite these advancements, critical challenges remain regarding interfacial cracking and dendrite propagation under high-current cycling. Specifically, delving into the intricate interplay between grain-boundary stress and premature cell failure remains a pivotal area of investigation.*
* **GOOD Edit (Surgical Scientific Mode — Preserves Human Structure):**
  > *Solid-state lithium-metal batteries offer high energy density and improved thermal safety. At high current densities, however, interfacial cracking and lithium dendrites still limit cycle life. How mechanical stress along ceramic grain boundaries initiates cell failure remains unclear experimentally.*

*(Notice the sentence lengths in the Good Edit: `12 words -> 15 words -> 14 words` with concrete nouns, zero banned vocabulary, and zero participial tails.)*

---

### B. Materials and Methods
* **Author's Raw Draft:**
  > We take 140 biopsy slide from three hospital. Tissue stain with H&E and scan at 40x. Slide that have fold artifact was remove (12 slide).
* **BAD Edit (Typical Unguided GPT):**
  > *A comprehensive cohort of 140 biopsy slides was meticulously collected across three tertiary hospitals, utilizing standardized H&E staining protocols and high-resolution 40x scanning, while seamlessly excluding 12 slides exhibiting folding artifacts to ensure optimal data quality.*
* **GOOD Edit (Surgical Scientific Mode):**
  > *We collected 140 biopsy slides from three hospitals. Sections were stained with H&E and scanned at 40x magnification. Twelve slides with tissue-folding artifacts were excluded.*

---

### C. Results
* **Author's Raw Draft:**
  > After 60 min dialysis, plasma K drop by 1.82 mEq/L (SD 0.34, n=14, p=0.003). In glucose-insulin group it drop 1.76 mEq/L. T-wave flattening happen in both group even though K move opposite direction across cell membrane.
* **BAD Edit (Typical Unguided GPT):**
  > *Notably, following 60 minutes of dialysis, plasma potassium levels exhibited a marked reduction of 1.82 mEq/L (SD 0.34, n=14, p=0.003), closely mirroring the 1.76 mEq/L decrease observed in the glucose-insulin cohort. Furthermore, electrocardiographic T-wave flattening manifested across both experimental groups, underscoring that extracellular concentration rather than transcellular flux governs repolarization dynamics.*
* **GOOD Edit (Surgical Scientific Mode):**
  > *After 60 min of dialysis, plasma K decreased by 1.82 mEq/L (SD 0.34, n = 14, p = 0.003), compared with 1.76 mEq/L in the glucose-insulin group. T-wave flattening occurred in both groups even though potassium moved in opposite directions across the cell membrane.*

---

### D. Discussion / Conclusion
* **Author's Raw Draft:**
  > Our result show extracellular K level, not direction of K flux, cause ECG change. However, we only measure up to 90 min in dog model, so chronic hypokalemia in patient might behave different.
* **BAD Edit (Typical Unguided GPT):**
  > *Collectively, our findings illuminate the pivotal role of extracellular potassium concentration over net transcellular flux in driving electrocardiographic alterations, shedding new light on acute electrolyte pathophysiology. Nevertheless, it is important to note that our experimental paradigm was restricted to 90-minute observations in a canine model, paving the way for future longitudinal clinical investigations in chronic hypokalemia.*
* **GOOD Edit (Surgical Scientific Mode):**
  > *Our results indicate that extracellular potassium concentration, rather than the direction of transcellular flux, drives these ECG changes. Because measurements were limited to 90 min in a canine model, chronic hypokalemia in patients may behave differently.*

---

## 3. Extended Scientific Word-Swap Reference

| Avoid (LLM Excess / Promotional) | Prefer (Direct Scientific English) |
| :--- | :--- |
| `delve into`, `delves into` | `examine`, `investigate`, `measure`, `test` |
| `underscore`, `underscores` | `show`, `indicate`, `confirm`, `support` |
| `showcase`, `spotlight` | `report`, `demonstrate`, `present` |
| `utilize`, `leverage`, `harness` | `use`, `apply` |
| `facilitate`, `expedite` | `enable`, `allow`, `accelerate`, `speed up` |
| `elucidate`, `illuminate`, `unravel` | `identify`, `resolve`, `clarify`, `determine` |
| `bolster`, `foster`, `cultivate` | `strengthen`, `support`, `increase`, `promote` |
| `garner attention` | `receive attention` *(or state the open problem directly)* |
| `pivotal`, `crucial`, `paramount`, `vital` | `key`, `rate-limiting`, `required`, `essential` |
| `intricate`, `multifaceted`, `complex interplay` | `coupled`, `specific`, `interaction between X and Y` |
| `meticulous`, `meticulously` | `systematic`, `controlled`, `careful` |
| `comprehensive`, `holistic`, `overarching` | `full`, `whole-system`, `primary` *(or state exact N)* |
| `realm`, `landscape`, `tapestry`, `arena` | `field`, `domain`, `regime`, `literature` |
| `paradigm`, `avenue` | `model`, `approach`, `direction` |
| `unprecedented`, `groundbreaking`, `transformative` | *(delete — state fold-change or effect size instead)* |
| `seamless`, `seamlessly`, `effortlessly` | `direct`, `automated`, `without manual calibration` |
| `noteworthy`, `remarkable`, `commendable`, `striking` | *(delete editorializing adjectives)* |
| `exhibited an increase of` | `increased by` |
| `performed an analysis of` | `analyzed` |
| `plays a pivotal role in regulating` | `regulates` |
