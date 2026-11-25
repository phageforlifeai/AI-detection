(() => {
  "use strict";

  const HISTORY_KEY = "scigram_scan_history_v1";

  const state = {
    samples: [],
    currentResult: null,
    selectedPassageIdx: 0,
    viewMode: "passage", // "passage" | "surgical"
    activeFilter: "all",
    lastRevisedText: null,
  };

  // DOM Elements
  const el = {
    engineStatusPill: document.getElementById("engineStatusPill"),
    engineStatusText: document.getElementById("engineStatusText"),
    toggleEditorBtn: document.getElementById("toggleEditorBtn"),
    historyBtn: document.getElementById("historyBtn"),
    historyCount: document.getElementById("historyCount"),
    historyMenu: document.getElementById("historyMenu"),
    historyList: document.getElementById("historyList"),
    clearHistoryBtn: document.getElementById("clearHistoryBtn"),
    exportMdBtn: document.getElementById("exportMdBtn"),

    presetButtons: document.getElementById("presetButtons"),
    composerSection: document.getElementById("composerSection"),
    docTitleInput: document.getElementById("docTitleInput"),
    wordCountBadge: document.getElementById("wordCountBadge"),
    minWordHint: document.getElementById("minWordHint"),
    stripRefsToggle: document.getElementById("stripRefsToggle"),
    fileUploadInput: document.getElementById("fileUploadInput"),
    clearTextBtn: document.getElementById("clearTextBtn"),
    dropZone: document.getElementById("dropZone"),
    dropOverlay: document.getElementById("dropOverlay"),
    manuscriptInput: document.getElementById("manuscriptInput"),
    analyzeBtn: document.getElementById("analyzeBtn"),
    analyzeBtnText: document.getElementById("analyzeBtnText"),

    alertBanner: document.getElementById("alertBanner"),
    resultsDashboard: document.getElementById("resultsDashboard"),

    scoreRingArc: document.getElementById("scoreRingArc"),
    overallAiPct: document.getElementById("overallAiPct"),
    overallVerdictBadge: document.getElementById("overallVerdictBadge"),
    docMetaSummary: document.getElementById("docMetaSummary"),
    shortWarningNote: document.getElementById("shortWarningNote"),

    barHuman: document.getElementById("barHuman"),
    barAssisted: document.getElementById("barAssisted"),
    barAi: document.getElementById("barAi"),
    pctHuman: document.getElementById("pctHuman"),
    pctAssisted: document.getElementById("pctAssisted"),
    pctAi: document.getElementById("pctAi"),

    burstinessBadge: document.getElementById("burstinessBadge"),
    sentenceSparkline: document.getElementById("sentenceSparkline"),
    sentLenStat: document.getElementById("sentLenStat"),
    anchorDensityStat: document.getElementById("anchorDensityStat"),

    modePassageBtn: document.getElementById("modePassageBtn"),
    modeSurgicalBtn: document.getElementById("modeSurgicalBtn"),
    surgicalLegend: document.getElementById("surgicalLegend"),
    passagesContainer: document.getElementById("passagesContainer"),

    passageInspectorContent: document.getElementById("passageInspectorContent"),
    studioPassageLabel: document.getElementById("studioPassageLabel"),
    autoDetemplateBtn: document.getElementById("autoDetemplateBtn"),
    studioTextarea: document.getElementById("studioTextarea"),
    resetStudioBtn: document.getElementById("resetStudioBtn"),
    recheckPassageBtn: document.getElementById("recheckPassageBtn"),
    applyToDocBtn: document.getElementById("applyToDocBtn"),
    studioComparisonBox: document.getElementById("studioComparisonBox"),

    dimensionBars: document.getElementById("dimensionBars"),
    docRecommendations: document.getElementById("docRecommendations"),
  };

  function escapeHtml(str) {
    return String(str ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function countWordsClient(text) {
    const m = text.trim().match(/[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*/g);
    return m ? m.length : 0;
  }

  function updateLiveWordCount() {
    const wc = countWordsClient(el.manuscriptInput.value);
    el.wordCountBadge.textContent = `${wc} word${wc === 1 ? "" : "s"}`;
    if (wc > 0 && wc < 50) {
      el.minWordHint.textContent = `${50 - wc} more words recommended for reliable scoring`;
      el.minWordHint.style.color = "#d97706";
    } else if (wc >= 50) {
      el.minWordHint.textContent = "Ready for 3-Expert MoE calibration";
      el.minWordHint.style.color = "#059669";
    } else {
      el.minWordHint.textContent = "50+ words recommended (Pangram standard)";
      el.minWordHint.style.color = "#64748b";
    }
  }

  function showAlert(msg) {
    if (!msg) {
      el.alertBanner.classList.add("hidden");
      el.alertBanner.textContent = "";
      return;
    }
    el.alertBanner.textContent = msg;
    el.alertBanner.classList.remove("hidden");
  }

  function classColorHex(cls) {
    if (cls === "ai_generated") return "#e11d48";
    if (cls === "ai_assisted") return "#d97706";
    return "#059669";
  }

  async function checkHealth() {
    try {
      const resp = await fetch("api/health");
      const data = await resp.json();
      if (data.status === "ok" && data.neural_active) {
        el.engineStatusPill.classList.add("ready");
        el.engineStatusText.textContent = "3-Expert MoE Active (TMR + E5 + SciStructure)";
      } else {
        el.engineStatusText.textContent = "SciStructure Mode Ready";
      }
    } catch (_err) {
      el.engineStatusText.textContent = "Connecting to Engine...";
    }
  }

  async function loadSamplesAndAutoDemo() {
    try {
      const resp = await fetch("api/samples");
      const data = await resp.json();
      state.samples = data.samples || [];
      renderPresetButtons();

      // Auto-load the 3-tier Mixed IMRaD Manuscript on first open so user sees Pangram workflow immediately
      if (state.samples.length > 0 && !el.manuscriptInput.value.trim()) {
        selectSample(state.samples[0], true);
      }
    } catch (err) {
      showAlert("Could not load built-in presets: " + err.message);
    }
  }

  function renderPresetButtons() {
    el.presetButtons.innerHTML = "";
    state.samples.forEach((sample) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "preset-chip";
      btn.dataset.sampleId = sample.id;
      btn.title = sample.description;
      btn.innerHTML = `<span>${escapeHtml(sample.title)}</span><span class="preset-chip-badge">${escapeHtml(sample.badge)}</span>`;
      btn.addEventListener("click", () => selectSample(sample, true));
      el.presetButtons.appendChild(btn);
    });
  }

  function selectSample(sample, autoRun = true) {
    document.querySelectorAll(".preset-chip").forEach((c) => {
      c.classList.toggle("active", c.dataset.sampleId === sample.id);
    });
    el.docTitleInput.value = sample.title;
    el.manuscriptInput.value = sample.text;
    updateLiveWordCount();
    if (autoRun) {
      runAnalysis();
    }
  }

  async function runAnalysis() {
    const text = el.manuscriptInput.value.trim();
    if (!text) {
      showAlert("Please paste scientific prose or upload a .tex / .docx / .pdf / .txt file first.");
      return;
    }
    showAlert(null);
    setLoading(true);

    try {
      const resp = await fetch("api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text,
          title: el.docTitleInput.value.trim() || "Manuscript Draft",
          include_sentences: true,
        }),
      });
      const data = await resp.json();
      if (!resp.ok) {
        throw new Error(data.detail || "Analysis failed");
      }
      applyAnalysisResult(data, text);
    } catch (err) {
      showAlert(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleFileUpload(file) {
    if (!file) return;
    showAlert(null);
    setLoading(true, `Scanning ${file.name}...`);

    try {
      const form = new FormData();
      form.append("file", file);
      form.append("strip_references", el.stripRefsToggle.checked ? "true" : "false");

      const resp = await fetch("api/upload", {
        method: "POST",
        body: form,
      });
      const data = await resp.json();
      if (!resp.ok) {
        throw new Error(data.detail || "Upload failed");
      }
      el.docTitleInput.value = file.name;
      el.manuscriptInput.value = data.extracted_text || "";
      updateLiveWordCount();
      applyAnalysisResult(data, data.extracted_text || "");
    } catch (err) {
      showAlert(err.message);
    } finally {
      setLoading(false);
      el.fileUploadInput.value = "";
    }
  }

  function setLoading(isLoading, customText = null) {
    el.analyzeBtn.disabled = isLoading;
    el.analyzeBtnText.textContent = isLoading ? (customText || "Analyzing Passages...") : "Analyze Manuscript";
  }

  function applyAnalysisResult(result, sourceText) {
    state.currentResult = result;
    // Default select the highest-AI passage so the coaching panel immediately helps the user!
    let highestIdx = 0;
    let highestScore = -1;
    (result.passages || []).forEach((p, idx) => {
      if (p.ai_score > highestScore) {
        highestScore = p.ai_score;
        highestIdx = idx;
      }
    });
    state.selectedPassageIdx = highestIdx;
    state.activeFilter = "all";
    document.querySelectorAll(".filter-pill").forEach((b) => {
      b.classList.toggle("active", b.dataset.filter === "all");
    });

    el.resultsDashboard.classList.remove("hidden");
    el.exportMdBtn.disabled = false;

    renderExecutiveSummary(result);
    renderPassages();
    renderPassageInspector();
    renderWholeStructureTab(result);
    saveToHistory(result, sourceText);
  }

  function renderExecutiveSummary(res) {
    const pct = res.overall_ai_pct;
    el.overallAiPct.textContent = `${pct}%`;

    const circumference = 257.6;
    const offset = circumference - (Math.min(100, Math.max(0, pct)) / 100) * circumference;
    el.scoreRingArc.style.strokeDashoffset = String(offset);
    el.scoreRingArc.style.stroke = classColorHex(res.overall_classification);

    el.overallVerdictBadge.textContent = res.overall_verdict;
    el.overallVerdictBadge.className = `verdict-badge ${res.overall_classification}`;

    const latexNote = res.latex_detected ? " · LaTeX parsed" : "";
    el.docMetaSummary.textContent = `${res.word_count} words · ${res.passage_count} passages · ${res.engine_info.latency_ms} ms${latexNote}`;
    el.shortWarningNote.classList.toggle("hidden", !res.short_text_warning);

    const bd = res.breakdown_pct;
    el.barHuman.style.width = `${bd.human}%`;
    el.barAssisted.style.width = `${bd.ai_assisted}%`;
    el.barAi.style.width = `${bd.ai_generated}%`;

    el.pctHuman.textContent = `${bd.human}%`;
    el.pctAssisted.textContent = `${bd.ai_assisted}%`;
    el.pctAi.textContent = `${bd.ai_generated}%`;

    // Burstiness & Sparkline
    const ds = res.document_structure;
    const burst = ds.burstiness;
    el.burstinessBadge.textContent = `CV ${burst.cv.toFixed(2)}`;
    el.burstinessBadge.style.color = burst.cv >= 0.38 ? "#059669" : "#d97706";
    el.sentLenStat.textContent = `${burst.mean_words} ± ${burst.std_words} w`;
    el.anchorDensityStat.textContent = `${ds.anchors_per_100w.toFixed(1)} / 100w`;

    const lengths = (burst.sentence_lengths || []).slice(0, 34);
    const maxLen = Math.max(36, ...lengths, 1);
    el.sentenceSparkline.innerHTML = lengths
      .map((w) => {
        const h = Math.max(14, Math.round((w / maxLen) * 100));
        const bandCls = w >= 18 && w <= 26 && burst.cv < 0.32 ? "uniform-band" : "varied-band";
        return `<div class="spark-bar ${bandCls}" style="height:${h}%" title="${w} words"></div>`;
      })
      .join("");
  }

  function renderAnnotatedProse(passage, surgical) {
    const raw = passage.text;
    if (!surgical) {
      return escapeHtml(raw);
    }

    // Build character-accurate markup for triggers & sentence backgrounds
    const triggers = passage.structure.triggers || [];
    const sentences = passage.sentences || [];

    if (sentences.length === 0) {
      return renderTriggersInSlice(raw, 0, raw.length, triggers);
    }

    let html = "";
    let cursor = 0;
    sentences.forEach((s) => {
      if (s.start > cursor) {
        html += escapeHtml(raw.slice(cursor, s.start));
      }
      const inner = renderTriggersInSlice(raw, s.start, s.end, triggers);
      const sentCls = s.classification !== "human" ? `sent-span s-${s.classification}` : "sent-span";
      const pct = Math.round(s.ai_score * 100);
      html += `<span class="${sentCls}" title="Sentence AI Score: ${pct}% (${s.word_count} words)">${inner}</span>`;
      cursor = s.end;
    });
    if (cursor < raw.length) {
      html += escapeHtml(raw.slice(cursor));
    }
    return html;
  }

  function renderTriggersInSlice(fullText, sliceStart, sliceEnd, triggers) {
    const overlapping = triggers.filter((t) => t.start >= sliceStart && t.end <= sliceEnd);
    if (overlapping.length === 0) {
      return escapeHtml(fullText.slice(sliceStart, sliceEnd));
    }
    let out = "";
    let pos = sliceStart;
    overlapping.forEach((t) => {
      if (t.start > pos) {
        out += escapeHtml(fullText.slice(pos, t.start));
      }
      const tip = `${t.label} — ${t.suggestion}`;
      out += `<span class="inline-trigger sev-${escapeHtml(t.severity)}" title="${escapeHtml(tip)}">${escapeHtml(fullText.slice(t.start, t.end))}</span>`;
      pos = t.end;
    });
    if (pos < sliceEnd) {
      out += escapeHtml(fullText.slice(pos, sliceEnd));
    }
    return out;
  }

  function renderPassages() {
    const res = state.currentResult;
    if (!res) return;

    const surgical = state.viewMode === "surgical";
    el.surgicalLegend.classList.toggle("hidden", !surgical);

    const visible = res.passages.filter(
      (p) => state.activeFilter === "all" || p.classification === state.activeFilter
    );

    if (visible.length === 0) {
      el.passagesContainer.innerHTML = `<div style="padding:20px;color:#64748b;font-size:0.86rem;">No passages match this filter.</div>`;
      return;
    }

    el.passagesContainer.innerHTML = visible
      .map((p) => {
        const isSel = p.index === state.selectedPassageIdx;
        const trigCount = (p.structure.triggers || []).length;
        const shieldHtml = p.calibration_shield
          ? `<span class="trig-count-pill" title="Protected by Scientific Calibration Gate against formal-prose false positives">Calibration Shield</span>`
          : "";
        const trigBadge =
          trigCount > 0
            ? `<span class="trig-count-pill">${trigCount} structural trigger${trigCount === 1 ? "" : "s"}</span>`
            : `<span class="trig-count-pill">Clean structure</span>`;
        const secHtml = p.section_heading
          ? `<span class="passage-sec-title">${escapeHtml(p.section_heading)}</span>`
          : "";

        return `
          <article class="passage-card cls-${p.classification} ${isSel ? "selected" : ""}" data-pidx="${p.index}">
            <div class="passage-top">
              <div class="passage-id-group">
                <span class="passage-num">Passage #${p.index + 1}</span>
                ${secHtml}
              </div>
              <div class="passage-badges">
                ${shieldHtml}
                ${trigBadge}
                <span class="cls-pill ${p.classification}">${escapeHtml(p.label)} · ${p.ai_score_pct}%</span>
              </div>
            </div>
            <div class="passage-prose">${renderAnnotatedProse(p, surgical)}</div>
          </article>
        `;
      })
      .join("");

    el.passagesContainer.querySelectorAll(".passage-card").forEach((card) => {
      card.addEventListener("click", () => {
        state.selectedPassageIdx = Number(card.dataset.pidx);
        renderPassages();
        renderPassageInspector();
      });
    });
  }

  function renderPassageInspector() {
    const res = state.currentResult;
    if (!res || !res.passages.length) return;
    const p = res.passages[state.selectedPassageIdx] || res.passages[0];
    const ex = p.experts;
    const triggers = p.structure.triggers || [];
    const actions = p.coaching.actions || [];

    const tmrStr = ex.tmr_roberta !== null ? `${Math.round(ex.tmr_roberta * 100)}%` : "N/A";
    const e5Str = ex.e5_lora !== null ? `${Math.round(ex.e5_lora * 100)}%` : "N/A";
    const stStr = `${Math.round(ex.sci_structure * 100)}%`;

    const actionsHtml = actions
      .map(
        (a) => `
        <div class="action-card prio-${escapeHtml(a.priority)}">
          <div class="action-title">${escapeHtml(a.title)}</div>
          <div class="action-detail">${escapeHtml(a.detail)}</div>
        </div>
      `
      )
      .join("");

    const triggersHtml =
      triggers.length > 0
        ? triggers
            .map(
              (t) => `
              <div class="trigger-item ${t.severity === "medium" ? "med" : ""}">
                <div><span class="trigger-quote">"${escapeHtml(t.matched_text)}"</span> — ${escapeHtml(t.label)}</div>
                <div class="trigger-fix">${escapeHtml(t.suggestion)}</div>
              </div>
            `
            )
            .join("")
        : `<div style="font-size:0.8rem;color:#059669;">Zero LLM lexical or syntactic triggers detected in this passage.</div>`;

    el.passageInspectorContent.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;">
        <div>
          <strong style="font-size:0.9rem;">Passage #${p.index + 1}${p.section_heading ? " — " + escapeHtml(p.section_heading) : ""}</strong>
          <div style="font-size:0.74rem;color:#64748b;">${p.word_count} words · Confidence: ${escapeHtml(p.confidence)} · Burstiness CV: ${p.structure.burstiness.cv.toFixed(2)}</div>
        </div>
        <span class="cls-pill ${p.classification}">${escapeHtml(p.label)} · ${p.ai_score_pct}%</span>
      </div>

      <div class="expert-grid">
        <div class="expert-box" title="Target Mining RoBERTa trained with Self-Hard-Negative mining on RAID">
          <div class="expert-val">${tmrStr}</div>
          <div class="expert-name">TMR-RoBERTa</div>
        </div>
        <div class="expert-box" title="E5-Small-LoRA Academic Cadence Detector">
          <div class="expert-val">${e5Str}</div>
          <div class="expert-name">E5-LoRA</div>
        </div>
        <div class="expert-box" title="7-Dimension Scientific Stylometric & Excess Vocabulary Analyzer">
          <div class="expert-val">${stStr}</div>
          <div class="expert-name">SciStructure</div>
        </div>
      </div>

      <div class="coach-summary">${escapeHtml(p.coaching.summary)}</div>

      <button id="jumpToStudioBtn" class="btn btn-secondary btn-sm" style="width:100%;margin-bottom:6px;" type="button">
        Open Passage #${p.index + 1} in Live Revision Studio →
      </button>

      <div class="section-subhead">How to Reduce AI-Like Structure Here</div>
      ${actionsHtml}

      <div class="section-subhead">Detected Structural &amp; Lexical Spans (${triggers.length})</div>
      ${triggersHtml}
    `;

    const jumpBtn = document.getElementById("jumpToStudioBtn");
    if (jumpBtn) {
      jumpBtn.addEventListener("click", () => switchInspectorTab("studioTab"));
    }

    // Sync Live Revision Studio for this passage
    el.studioPassageLabel.textContent = `Passage #${p.index + 1}${p.section_heading ? " (" + p.section_heading + ")" : ""}`;
    el.studioTextarea.value = p.text;
    el.autoDetemplateBtn.disabled = !p.coaching.de_templated_preview;
    el.studioComparisonBox.classList.add("hidden");
    el.applyToDocBtn.classList.add("hidden");
    state.lastRevisedText = null;
  }

  function renderWholeStructureTab(res) {
    const dims = res.document_structure.dimensions;
    const rows = [
      { label: "Rhythm Uniformity (Low Burstiness)", val: dims.rhythm_uniformity },
      { label: "Participial '-ing' Summary Tails", val: dims.participial_tails },
      { label: "Mechanical Discourse Starters", val: dims.formulaic_transitions },
      { label: "Excess LLM Scientific Vocabulary", val: dims.excess_llm_vocab },
      { label: "Rhetorical Boilerplate Templates", val: dims.rhetorical_boilerplate },
      { label: "Parallel Triadic Symmetry", val: dims.triadic_symmetry },
      { label: "Empirical Specificity Deficit", val: dims.specificity_deficit },
    ];

    el.dimensionBars.innerHTML = rows
      .map((r) => {
        const col = r.val >= 55 ? "#e11d48" : r.val >= 30 ? "#d97706" : "#059669";
        return `
          <div class="dim-row">
            <div class="dim-top">
              <span>${escapeHtml(r.label)}</span>
              <span style="color:${col}">${r.val.toFixed(1)}%</span>
            </div>
            <div class="dim-track">
              <div class="dim-fill" style="width:${Math.min(100, r.val)}%;background:${col}"></div>
            </div>
          </div>
        `;
      })
      .join("");

    el.docRecommendations.innerHTML = (res.recommendations || [])
      .map(
        (rec) => `
          <div class="rec-item">
            <span class="rec-badge">${escapeHtml(rec.badge)}</span>
            <div style="font-weight:700;margin-bottom:3px;">${escapeHtml(rec.title)}</div>
            <div style="color:#475569;">${escapeHtml(rec.body)}</div>
          </div>
        `
      )
      .join("");
  }

  function switchInspectorTab(tabId) {
    document.querySelectorAll(".insp-tab").forEach((t) => {
      t.classList.toggle("active", t.dataset.tab === tabId);
    });
    ["passageTab", "studioTab", "structureTab"].forEach((id) => {
      document.getElementById(id).classList.toggle("hidden", id !== tabId);
    });
  }

  async function recheckPassageInStudio() {
    const res = state.currentResult;
    if (!res) return;
    const p = res.passages[state.selectedPassageIdx];
    const revisedText = el.studioTextarea.value.trim();
    if (!revisedText) return;

    el.recheckPassageBtn.disabled = true;
    el.recheckPassageBtn.textContent = "Checking...";

    try {
      const resp = await fetch("api/analyze-passage", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          original_text: p.text,
          revised_text: revisedText,
        }),
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || "Re-check failed");

      state.lastRevisedText = revisedText;
      const delta = data.delta_pct;
      const sign = delta > 0 ? "+" : "";
      const deltaClass = delta <= 0 ? "improved" : "worse";
      const revP = data.revised.passages[0];
      const remTriggers = revP ? revP.structure.triggers.length : 0;

      el.studioComparisonBox.innerHTML = `
        <div class="delta-row">
          <div>
            <span style="font-size:0.78rem;color:#64748b;">AI Score:</span>
            <strong>${data.original_ai_pct}% → ${data.revised_ai_pct}%</strong>
          </div>
          <span class="delta-pill ${deltaClass}">${sign}${delta}%</span>
        </div>
        <div style="font-size:0.78rem;color:#475569;">
          New Verdict: <strong>${escapeHtml(data.revised.overall_verdict)}</strong> · Remaining structural triggers: <strong>${remTriggers}</strong>
        </div>
      `;
      el.studioComparisonBox.classList.remove("hidden");
      el.applyToDocBtn.classList.remove("hidden");
    } catch (err) {
      showAlert(err.message);
    } finally {
      el.recheckPassageBtn.disabled = false;
      el.recheckPassageBtn.textContent = "Re-Check Passage";
    }
  }

  function applyStudioRevisionToManuscript() {
    const res = state.currentResult;
    if (!res || !state.lastRevisedText) return;
    const p = res.passages[state.selectedPassageIdx];
    const currentFull = el.manuscriptInput.value;

    if (currentFull.includes(p.text)) {
      el.manuscriptInput.value = currentFull.replace(p.text, state.lastRevisedText);
    } else {
      // Reconstruct from passages if LaTeX or formatting differed
      const updatedPassages = res.passages.map((item, idx) => {
        const body = idx === state.selectedPassageIdx ? state.lastRevisedText : item.text;
        return item.section_heading ? `${item.section_heading}\n\n${body}` : body;
      });
      el.manuscriptInput.value = updatedPassages.join("\n\n");
    }
    updateLiveWordCount();
    runAnalysis();
  }

  // History persistence
  function getHistory() {
    try {
      return JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]");
    } catch (_e) {
      return [];
    }
  }

  function saveToHistory(res, text) {
    const items = getHistory();
    const entry = {
      id: Date.now(),
      title: res.title || "Manuscript Draft",
      ai_pct: res.overall_ai_pct,
      verdict: res.overall_verdict,
      classification: res.overall_classification,
      words: res.word_count,
      time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      text,
    };
    // Deduplicate identical consecutive text
    const filtered = items.filter((x) => x.text !== text);
    filtered.unshift(entry);
    const trimmed = filtered.slice(0, 12);
    try {
      localStorage.setItem(HISTORY_KEY, JSON.stringify(trimmed));
    } catch (_e) {
      // Ignore storage quota errors
    }
    renderHistoryMenu();
  }

  function renderHistoryMenu() {
    const items = getHistory();
    el.historyCount.textContent = String(items.length);
    if (items.length === 0) {
      el.historyList.innerHTML = `<div style="padding:14px;font-size:0.78rem;color:#64748b;">No scans saved yet.</div>`;
      return;
    }
    el.historyList.innerHTML = items
      .map(
        (it, idx) => `
          <div class="history-item" data-hidx="${idx}">
            <div style="min-width:0;">
              <div class="history-item-title">${escapeHtml(it.title)}</div>
              <div class="history-item-sub">${it.words} words · ${escapeHtml(it.time)}</div>
            </div>
            <span class="cls-pill ${it.classification}">${it.ai_pct}%</span>
          </div>
        `
      )
      .join("");

    el.historyList.querySelectorAll(".history-item").forEach((row) => {
      row.addEventListener("click", () => {
        const picked = items[Number(row.dataset.hidx)];
        if (picked) {
          el.docTitleInput.value = picked.title;
          el.manuscriptInput.value = picked.text;
          updateLiveWordCount();
          el.historyMenu.classList.add("hidden");
          runAnalysis();
        }
      });
    });
  }

  async function downloadMarkdownReport() {
    const text = el.manuscriptInput.value.trim();
    if (!text) return;
    try {
      const resp = await fetch("api/export-report", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text,
          title: el.docTitleInput.value.trim() || "Manuscript Scan",
        }),
      });
      const md = await resp.text();
      const blob = new Blob([md], { type: "text/markdown;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      const safeName = (el.docTitleInput.value.trim() || "scigram_report")
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "_");
      a.href = url;
      a.download = `${safeName}_scigram_report.md`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      showAlert("Report export failed: " + err.message);
    }
  }

  // Event Listeners
  el.manuscriptInput.addEventListener("input", updateLiveWordCount);
  el.manuscriptInput.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      runAnalysis();
    }
  });

  el.analyzeBtn.addEventListener("click", runAnalysis);

  el.clearTextBtn.addEventListener("click", () => {
    el.manuscriptInput.value = "";
    document.querySelectorAll(".preset-chip").forEach((c) => c.classList.remove("active"));
    updateLiveWordCount();
    el.manuscriptInput.focus();
  });

  el.toggleEditorBtn.addEventListener("click", () => {
    el.composerSection.classList.toggle("hidden");
  });

  el.fileUploadInput.addEventListener("change", (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFileUpload(e.target.files[0]);
    }
  });

  // Drag & drop support
  ["dragenter", "dragover"].forEach((ev) => {
    el.dropZone.addEventListener(ev, (e) => {
      e.preventDefault();
      el.dropOverlay.classList.remove("hidden");
    });
  });
  ["dragleave", "drop"].forEach((ev) => {
    el.dropZone.addEventListener(ev, (e) => {
      e.preventDefault();
      el.dropOverlay.classList.add("hidden");
    });
  });
  el.dropZone.addEventListener("drop", (e) => {
    if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  });

  // View Mode Toggle
  el.modePassageBtn.addEventListener("click", () => {
    state.viewMode = "passage";
    el.modePassageBtn.classList.add("active");
    el.modeSurgicalBtn.classList.remove("active");
    renderPassages();
  });
  el.modeSurgicalBtn.addEventListener("click", () => {
    state.viewMode = "surgical";
    el.modeSurgicalBtn.classList.add("active");
    el.modePassageBtn.classList.remove("active");
    renderPassages();
  });

  // Filter Pills
  document.querySelectorAll(".filter-pill").forEach((pill) => {
    pill.addEventListener("click", () => {
      state.activeFilter = pill.dataset.filter;
      document.querySelectorAll(".filter-pill").forEach((b) => {
        b.classList.toggle("active", b === pill);
      });
      renderPassages();
    });
  });

  // Inspector Tabs
  document.querySelectorAll(".insp-tab").forEach((tab) => {
    tab.addEventListener("click", () => switchInspectorTab(tab.dataset.tab));
  });

  // Live Studio Buttons
  el.autoDetemplateBtn.addEventListener("click", () => {
    const res = state.currentResult;
    if (!res) return;
    const p = res.passages[state.selectedPassageIdx];
    if (p && p.coaching.de_templated_preview) {
      el.studioTextarea.value = p.coaching.de_templated_preview;
    }
  });
  el.resetStudioBtn.addEventListener("click", () => {
    const res = state.currentResult;
    if (!res) return;
    const p = res.passages[state.selectedPassageIdx];
    if (p) {
      el.studioTextarea.value = p.text;
      el.studioComparisonBox.classList.add("hidden");
      el.applyToDocBtn.classList.add("hidden");
    }
  });
  el.recheckPassageBtn.addEventListener("click", recheckPassageInStudio);
  el.applyToDocBtn.addEventListener("click", applyStudioRevisionToManuscript);

  // History Dropdown
  el.historyBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    el.historyMenu.classList.toggle("hidden");
  });
  el.clearHistoryBtn.addEventListener("click", () => {
    localStorage.removeItem(HISTORY_KEY);
    renderHistoryMenu();
  });
  document.addEventListener("click", (e) => {
    if (!el.historyMenu.contains(e.target) && e.target !== el.historyBtn) {
      el.historyMenu.classList.add("hidden");
    }
  });

  el.exportMdBtn.addEventListener("click", downloadMarkdownReport);

  // Init
  renderHistoryMenu();
  checkHealth();
  loadSamplesAndAutoDemo();
})();
