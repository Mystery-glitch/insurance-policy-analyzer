/**
 * InsureClear — Frontend Application Logic
 * Interactive UI for PDF upload, AI policy analysis, and RAG Q&A.
 */

(function () {
  "use strict";

  // ── Configuration & Endpoints ──────────────────────────────────────────
  const API_BASE = window.location.protocol.startsWith("http") ? "" : "http://192.168.1.21:8000";
  const ENDPOINTS = {
    HEALTH: `${API_BASE}/health`,
    ANALYZE: `${API_BASE}/api/v1/analyze`,
    ASK: `${API_BASE}/api/v1/ask`,
  };

  // ── Application State ──────────────────────────────────────────────────
  const state = {
    selectedFile: null,
    documentId: null,
    analysis: null,
    isSample: false,
    isProcessing: false,
    isAsking: false,
    activeFilter: "all",
    stepperTimer: null,
  };

  // ── DOM Element Selectors ──────────────────────────────────────────────
  const el = {
    // Header
    backendStatusPill: document.getElementById("backend-status-pill"),
    backendStatusText: document.getElementById("backend-status-text"),
    resetBtn: document.getElementById("reset-btn"),

    // Upload & Hero
    uploadSection: document.getElementById("upload-section"),
    dropZone: document.getElementById("drop-zone"),
    fileInput: document.getElementById("file-input"),
    fileDetails: document.getElementById("file-details"),
    fileName: document.getElementById("file-name"),
    fileSize: document.getElementById("file-size"),
    removeFileBtn: document.getElementById("remove-file-btn"),
    analyzeBtn: document.getElementById("analyze-btn"),
    demoSampleBtn: document.getElementById("demo-sample-btn"),

    // Stepper / Processing
    processingSection: document.getElementById("processing-section"),
    processingTitle: document.getElementById("processing-title"),
    processingSubtitle: document.getElementById("processing-subtitle"),
    progressBarFill: document.getElementById("progress-bar-fill"),
    step1: document.getElementById("step-1"),
    step2: document.getElementById("step-2"),
    step3: document.getElementById("step-3"),
    step4: document.getElementById("step-4"),

    // Error
    errorBanner: document.getElementById("error-banner"),
    errorTitle: document.getElementById("error-title"),
    errorMessage: document.getElementById("error-message"),
    dismissErrorBtn: document.getElementById("dismiss-error-btn"),

    // Dashboard
    dashboardSection: document.getElementById("dashboard-section"),
    policyTypeBadge: document.getElementById("policy-type-badge"),
    policyHeading: document.getElementById("policy-heading"),
    docIdText: document.getElementById("doc-id-text"),
    copyDocIdBtn: document.getElementById("copy-doc-id-btn"),
    statTotalPages: document.getElementById("stat-total-pages"),
    statDigitalPages: document.getElementById("stat-digital-pages"),
    statScannedPages: document.getElementById("stat-scanned-pages"),
    statChunks: document.getElementById("stat-chunks"),

    // Dashboard Cards & Lists
    riskAlertsContainer: document.getElementById("risk-alerts-container"),
    riskAlertsList: document.getElementById("risk-alerts-list"),
    summaryText: document.getElementById("summary-text"),
    coverageList: document.getElementById("coverage-list"),
    coverageCount: document.getElementById("coverage-count"),
    exclusionsList: document.getElementById("exclusions-list"),
    exclusionsCount: document.getElementById("exclusions-count"),
    conditionsList: document.getElementById("conditions-list"),
    conditionsCount: document.getElementById("conditions-count"),
    glossaryList: document.getElementById("glossary-list"),

    // Tabs
    tabBtns: document.querySelectorAll(".tab-btn"),
    tabPanes: document.querySelectorAll(".tab-pane"),
    filterPills: document.querySelectorAll(".pill-btn"),

    // Chat & Floating Drawer
    dashboardGrid: document.querySelector(".dashboard-grid"),
    chatDrawer: document.getElementById("chat-drawer"),
    chatBackdrop: document.getElementById("chat-backdrop"),
    chatFabContainer: document.getElementById("chat-fab-container"),
    chatFabBtn: document.getElementById("chat-fab-btn"),
    chatCloseBtn: document.getElementById("chat-close-btn"),
    chatExpandBtn: document.getElementById("chat-expand-btn"),
    expandIcon: document.getElementById("expand-icon"),
    tabChatBtn: document.getElementById("tab-chat-btn"),
    chatForm: document.getElementById("chat-form"),
    chatInput: document.getElementById("chat-input"),
    chatSendBtn: document.getElementById("chat-send-btn"),
    chatMessages: document.getElementById("chat-messages"),
    quickChips: document.querySelectorAll(".quick-chip"),
    quickPromptsContainer: document.getElementById("quick-prompts-container"),

    // Toast
    toast: document.getElementById("toast"),
    toastMessage: document.getElementById("toast-message"),
  };

  // ── Sample Policy Data (for instant demo preview) ─────────────────────
  const SAMPLE_POLICY_DATA = {
    document_id: "demo-health-99",
    extraction_metadata: {
      total_pages: 42,
      digital_pages: 35,
      scanned_pages: 7,
      ocr_applied: true,
    },
    analysis: {
      policy_type: "Comprehensive Health Insurance (Gold Plan)",
      summary:
        "This policy is an individual and family floater health insurance policy offering up to ₹10,00,000 annual sum insured. It covers in-patient hospitalization, day-care procedures, and 60 days of pre- and post-hospitalization medical expenses. However, room rents are strictly capped at 1% of the sum insured, and claims for pre-existing medical conditions carry an uncompromising 36-month waiting period.",
      risk_alerts: [
        "Hidden Room Rent Sub-limit: Capped at ₹10,000/day (1% of Sum Insured). Choosing a room above this limit triggers proportionate deduction across all associated doctor fees and surgery costs.",
        "36-Month Pre-Existing Waiting Period: Any medical condition existing before policy inception will NOT be covered until 3 full continuous years have elapsed.",
        "Mandatory 20% Co-Payment for Senior Dependents: Any claim filed for insured members aged 60 and above requires the policyholder to pay 20% out-of-pocket.",
        "Strict 24-Hour Emergency Intimation: Emergency hospitalizations must be notified within 24 hours of admission or the cashless facility will be denied.",
      ],
      coverage_highlights: [
        {
          item: "In-Patient Hospitalization",
          detail: "Covers room boarding, nursing expenses, ICU charges, surgeon fees, and surgical appliances for admissions exceeding 24 hours.",
          limit: "Up to ₹10,00,000 per policy year",
        },
        {
          item: "Pre & Post-Hospitalization",
          detail: "Medical tests, doctor consultations, and prescribed pharmacy bills incurred 30 days prior to admission and 60 days post-discharge.",
          limit: "Actual expenses related to active claim",
        },
        {
          item: "Day Care Procedures",
          detail: "Covers over 540 advanced surgical procedures (such as cataract, dialysis, chemotherapy) that do not require 24 hours hospitalization due to medical technology.",
          limit: "Up to Sum Insured",
        },
        {
          item: "Emergency Road Ambulance",
          detail: "Covers transfer to the nearest network hospital in a registered medical ambulance in life-threatening events.",
          limit: "₹2,500 per hospitalization episode",
        },
        {
          item: "Annual Preventive Health Check-up",
          detail: "Complimentary full-body diagnostic package for each insured adult member after every claim-free renewal year.",
          limit: "1 check-up per adult member / year",
        },
      ],
      exclusions: [
        {
          item: "Cosmetic & Aesthetic Surgery",
          detail: "Plastic surgery, Botox, aesthetic dental treatments, or appearance alteration unless required due to major burn trauma or accidental injury.",
          severity: "high",
        },
        {
          item: "Maternity & Newborn Expenses",
          detail: "Normal delivery, Caesarean section, prenatal tests, fertility treatments, and newborn child care are completely excluded from this base plan.",
          severity: "high",
        },
        {
          item: "Alternative & AYUSH Treatments in Unrecognized Centers",
          detail: "Ayurveda, Yoga, and Homeopathy are only covered if admitted in recognized government hospitals or accredited NABH institutes.",
          severity: "medium",
        },
        {
          item: "Non-Medical Consumables",
          detail: "Surgical gloves, admission kits, thermometers, sanitizers, attendant food, and administrative registration charges are billed directly to the patient.",
          severity: "medium",
        },
        {
          item: "Intentional Self-Injury & Hazardous Sports",
          detail: "Injuries resulting from suicide attempts, substance abuse, participation in motorized racing, or adventure skydiving are strictly non-payable.",
          severity: "low",
        },
        {
          item: "Standard 30-Day Initial Waiting Period",
          detail: "No illness-related claims are payable during the first 30 days of the policy, except for emergency accidental injuries.",
          severity: "low",
        },
      ],
      key_conditions: [
        {
          item: "Initial 30-Day Inactive Period",
          detail: "No illness is covered during the first 30 days after inception. Only emergency accidental hospitalization is effective from Day 1.",
        },
        {
          item: "2-Year Specific Illness Moratorium",
          detail: "Common elective ailments like Hernia, Cataract, Joint Replacement, and Kidney Stones have a mandatory 24-month waiting duration.",
        },
        {
          item: "Cashless Authorization Timing",
          detail: "Planned admissions require 48 hours advance notice to TPA; emergency hospitalizations require intimation within 24 hours.",
        },
        {
          item: "Cumulative No-Claim Bonus (NCB)",
          detail: "Increases the sum insured by 10% for every claim-free year up to a maximum cap of 50%, with zero increase in renewal premium.",
        },
      ],
      jargon_glossary: [
        {
          term: "Sub-limit",
          meaning: "A monetary ceiling placed on a specific medical expense (e.g., room rent or cataract surgery), regardless of how high your overall coverage limit is.",
        },
        {
          term: "Co-Payment (Co-pay)",
          meaning: "A fixed percentage of the total approved claim amount that you agree to pay from your own pocket every time a claim is made.",
        },
        {
          term: "Deductible",
          meaning: "The upfront amount you must personally pay toward medical expenses before your insurance company starts paying a single rupee.",
        },
        {
          term: "Third-Party Administrator (TPA)",
          meaning: "An independent specialized agency licensed to process insurance claims, verify hospital bills, and issue cashless approvals on behalf of the insurer.",
        },
      ],
    },
    qa_ready: true,
    indexed_chunks: 38,
  };

  // ── Helper: Format Bytes ───────────────────────────────────────────────
  function formatBytes(bytes) {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  }

  // ── Helper: Show Toast ─────────────────────────────────────────────────
  let toastTimer = null;
  function showToast(message) {
    if (toastTimer) clearTimeout(toastTimer);
    el.toastMessage.textContent = message;
    el.toast.classList.remove("hidden");
    toastTimer = setTimeout(() => {
      el.toast.classList.add("hidden");
    }, 2800);
  }

  // ── Helper: Show/Hide Error Banner ─────────────────────────────────────
  function showError(title, message) {
    el.errorTitle.textContent = title;
    el.errorMessage.textContent = message;
    el.errorBanner.classList.remove("hidden");
    el.errorBanner.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  function hideError() {
    el.errorBanner.classList.add("hidden");
  }

  // ── Check Backend Health ───────────────────────────────────────────────
  async function checkBackendHealth() {
    try {
      const res = await fetch(ENDPOINTS.HEALTH);
      if (res.ok) {
        el.backendStatusPill.className = "status-pill status-online";
        el.backendStatusText.textContent = "API Ready";
      } else {
        throw new Error("Status code: " + res.status);
      }
    } catch {
      el.backendStatusPill.className = "status-pill status-offline";
      el.backendStatusText.textContent = "API Offline";
    }
  }

  // ── Drag & Drop Event Listeners ────────────────────────────────────────
  function setupDragAndDrop() {
    ["dragenter", "dragover"].forEach((eventName) => {
      el.dropZone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        el.dropZone.classList.add("dragover");
      });
    });

    ["dragleave", "drop"].forEach((eventName) => {
      el.dropZone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        el.dropZone.classList.remove("dragover");
      });
    });

    el.dropZone.addEventListener("drop", (e) => {
      const files = e.dataTransfer.files;
      if (files && files.length > 0) {
        handleFileSelection(files[0]);
      }
    });

    el.fileInput.addEventListener("change", (e) => {
      if (e.target.files && e.target.files.length > 0) {
        handleFileSelection(e.target.files[0]);
      }
    });

    el.removeFileBtn.addEventListener("click", () => {
      clearSelectedFile();
    });
  }

  // ── Handle File Selection ──────────────────────────────────────────────
  function handleFileSelection(file) {
    hideError();

    // Check PDF extension / mime
    if (!file.name.toLowerCase().endsWith(".pdf") && file.type !== "application/pdf") {
      showError("Invalid File Type", "Please select a valid PDF file (.pdf).");
      return;
    }

    // 50 MB limit
    const MAX_MB = 50;
    if (file.size > MAX_MB * 1024 * 1024) {
      showError("File Too Large", `Document size exceeds ${MAX_MB} MB limit.`);
      return;
    }

    if (file.size === 0) {
      showError("Empty File", "The selected PDF is 0 bytes.");
      return;
    }

    state.selectedFile = file;
    el.fileName.textContent = file.name;
    el.fileSize.textContent = formatBytes(file.size);
    el.fileDetails.classList.remove("hidden");
    el.analyzeBtn.disabled = false;
  }

  function clearSelectedFile() {
    state.selectedFile = null;
    el.fileInput.value = "";
    el.fileDetails.classList.add("hidden");
    el.analyzeBtn.disabled = true;
  }

  // ── Processing Stepper Progress Animation ───────────────────────────────
  function startProcessingStepper() {
    state.isProcessing = true;
    el.uploadSection.classList.add("hidden");
    el.processingSection.classList.remove("hidden");
    hideError();

    const steps = [el.step1, el.step2, el.step3, el.step4];
    steps.forEach((s) => {
      s.className = "step-item";
    });

    let currentStep = 1;
    let progress = 15;
    el.progressBarFill.style.width = `${progress}%`;
    el.step1.classList.add("step-active");

    const titles = [
      "Uploading Document...",
      "Extracting Text & OCR...",
      "Generating Plain-English AI Analysis...",
      "Indexing Clauses into Vector Store...",
    ];

    state.stepperTimer = setInterval(() => {
      if (currentStep < 4) {
        steps[currentStep - 1].classList.remove("step-active");
        steps[currentStep - 1].classList.add("step-done");
        currentStep++;
        steps[currentStep - 1].classList.add("step-active");

        el.processingTitle.textContent = titles[currentStep - 1];
        progress = Math.min(progress + 25, 90);
        el.progressBarFill.style.width = `${progress}%`;
      }
    }, 2800);
  }

  function stopProcessingStepper(success = true) {
    if (state.stepperTimer) clearInterval(state.stepperTimer);
    state.isProcessing = false;

    if (success) {
      el.progressBarFill.style.width = "100%";
      [el.step1, el.step2, el.step3, el.step4].forEach((s) => {
        s.className = "step-item step-done";
      });
      setTimeout(() => {
        el.processingSection.classList.add("hidden");
        el.dashboardSection.classList.remove("hidden");
        el.resetBtn.classList.remove("hidden");
        el.dashboardSection.scrollIntoView({ behavior: "smooth" });
      }, 500);
    } else {
      el.processingSection.classList.add("hidden");
      el.uploadSection.classList.remove("hidden");
    }
  }

  // ── Analyze Policy API Call ────────────────────────────────────────────
  async function triggerAnalyze() {
    if (!state.selectedFile) return;

    startProcessingStepper();

    const formData = new FormData();
    formData.append("file", state.selectedFile);

    try {
      const response = await fetch(ENDPOINTS.ANALYZE, {
        method: "POST",
        body: formData,
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || "Analysis request failed.");
      }

      state.isSample = false;
      state.documentId = result.data.document_id;
      state.analysis = result.data.analysis;

      stopProcessingStepper(true);
      renderDashboard(result.data);
      showToast("Policy analyzed and indexed successfully!");
    } catch (err) {
      stopProcessingStepper(false);
      el.dashboardSection.classList.add("hidden");
      showError("Analysis Failed", err.message || "An unexpected error occurred during document processing.");
    }
  }

  // ── Render Dashboard ───────────────────────────────────────────────────
  function renderDashboard(data) {
    const analysis = data.analysis;
    const meta = data.extraction_metadata || {};

    // Header Meta
    el.policyTypeBadge.textContent = analysis.policy_type || "Insurance Policy";
    el.policyHeading.textContent = `${analysis.policy_type || "Insurance"} Plain-English Breakdown`;
    el.docIdText.textContent = data.document_id || "doc-unknown";

    // Stats
    el.statTotalPages.textContent = meta.total_pages ?? "-";
    el.statDigitalPages.textContent = meta.digital_pages ?? "-";
    el.statScannedPages.textContent = meta.scanned_pages ?? "-";
    el.statChunks.textContent = data.indexed_chunks ?? "-";

    // Executive Summary
    el.summaryText.textContent = analysis.summary || "No summary provided.";

    // Critical Risk Alerts
    renderRiskAlerts(analysis.risk_alerts || []);

    // Coverage
    renderCoverage(analysis.coverage_highlights || []);

    // Exclusions
    renderExclusions(analysis.exclusions || []);

    // Conditions
    renderConditions(analysis.key_conditions || []);

    // Glossary
    renderGlossary(analysis.jargon_glossary || []);

    // Show Floating Action Button (FAB) Logo
    if (el.chatFabContainer) {
      el.chatFabContainer.classList.remove("hidden");
    }

    // Reset Chat messages
    resetChat();
  }

  // ── Render Risk Alerts ─────────────────────────────────────────────────
  function renderRiskAlerts(alerts) {
    el.riskAlertsList.innerHTML = "";
    if (!alerts || alerts.length === 0) {
      el.riskAlertsContainer.classList.add("hidden");
      return;
    }
    el.riskAlertsContainer.classList.remove("hidden");

    alerts.forEach((alert) => {
      const card = document.createElement("div");
      card.className = "risk-card";
      card.innerHTML = `
        <span class="risk-bullet-icon">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
        </span>
        <div class="risk-text">${escapeHtml(alert)}</div>
      `;
      el.riskAlertsList.appendChild(card);
    });
  }

  // ── Render Coverage ────────────────────────────────────────────────────
  function renderCoverage(items) {
    el.coverageList.innerHTML = "";
    el.coverageCount.textContent = items.length;

    if (items.length === 0) {
      el.coverageList.innerHTML = `<p class="empty-state">No specific coverage highlights identified.</p>`;
      return;
    }

    items.forEach((cov) => {
      const card = document.createElement("div");
      card.className = "coverage-card";
      card.innerHTML = `
        <div class="coverage-top">
          <h4 class="coverage-item-title">${escapeHtml(cov.item || "Coverage Item")}</h4>
          ${cov.limit ? `<span class="coverage-limit-badge">${escapeHtml(cov.limit)}</span>` : ""}
        </div>
        <p class="coverage-detail">${escapeHtml(cov.detail || "")}</p>
      `;
      el.coverageList.appendChild(card);
    });
  }

  // ── Render Exclusions ──────────────────────────────────────────────────
  function renderExclusions(items) {
    el.exclusionsList.innerHTML = "";
    el.exclusionsCount.textContent = items.length;

    if (items.length === 0) {
      el.exclusionsList.innerHTML = `<p class="empty-state">No exclusions identified.</p>`;
      return;
    }

    items.forEach((exc) => {
      const sev = (exc.severity || "medium").toLowerCase();
      const card = document.createElement("div");
      card.className = `exclusion-card sev-${sev}`;
      card.setAttribute("data-severity", sev);

      const tagClass = sev === "high" ? "tag-high" : sev === "medium" ? "tag-medium" : "tag-low";

      card.innerHTML = `
        <div class="exclusion-top">
          <h4 class="exclusion-title">${escapeHtml(exc.item || "Exclusion")}</h4>
          <span class="severity-tag ${tagClass}">${sev} Risk</span>
        </div>
        <p class="exclusion-detail">${escapeHtml(exc.detail || "")}</p>
      `;
      el.exclusionsList.appendChild(card);
    });

    applyExclusionFilter(state.activeFilter);
  }

  function applyExclusionFilter(filter) {
    state.activeFilter = filter;
    const cards = el.exclusionsList.querySelectorAll(".exclusion-card");
    cards.forEach((card) => {
      if (filter === "all" || card.getAttribute("data-severity") === filter) {
        card.style.display = "block";
      } else {
        card.style.display = "none";
      }
    });

    el.filterPills.forEach((btn) => {
      btn.classList.toggle("active", btn.getAttribute("data-filter") === filter);
    });
  }

  // ── Render Conditions ──────────────────────────────────────────────────
  function renderConditions(items) {
    el.conditionsList.innerHTML = "";
    el.conditionsCount.textContent = items.length;

    if (items.length === 0) {
      el.conditionsList.innerHTML = `<p class="empty-state">No special conditions extracted.</p>`;
      return;
    }

    items.forEach((cond) => {
      const card = document.createElement("div");
      card.className = "condition-card";
      card.innerHTML = `
        <h4 class="condition-term">${escapeHtml(cond.item || "Condition")}</h4>
        <p class="condition-detail">${escapeHtml(cond.detail || "")}</p>
      `;
      el.conditionsList.appendChild(card);
    });
  }

  // ── Render Glossary ────────────────────────────────────────────────────
  function renderGlossary(items) {
    el.glossaryList.innerHTML = "";
    if (items.length === 0) {
      el.glossaryList.innerHTML = `<p class="empty-state">No insurance terms found in glossary.</p>`;
      return;
    }

    items.forEach((term) => {
      const card = document.createElement("div");
      card.className = "glossary-card";
      card.innerHTML = `
        <h4 class="glossary-term">${escapeHtml(term.term || "")}</h4>
        <p class="glossary-meaning">${escapeHtml(term.meaning || "")}</p>
      `;
      el.glossaryList.appendChild(card);
    });
  }

  // ── Reset Chat ─────────────────────────────────────────────────────────
  function resetChat() {
    el.chatMessages.innerHTML = `
      <div class="message msg-assistant">
        <div class="msg-bubble">
          <p>Hello! I have analyzed and indexed this policy's full text. Ask me any question in plain English (e.g. <em>"What is the deductible?"</em> or <em>"Are pre-existing conditions covered?"</em>) and I will retrieve grounded answers with exact citations.</p>
        </div>
      </div>
    `;
    el.chatInput.value = "";
  }

  // ── Floating Chat Drawer (Half-Screen Hover Modal) ──────────────────────
  function openChatDrawer() {
    if (!el.chatDrawer) return;
    el.chatDrawer.classList.remove("chat-drawer-closed");
    el.chatDrawer.classList.add("chat-drawer-open");
    if (el.chatBackdrop) {
      el.chatBackdrop.classList.remove("hidden");
      el.chatBackdrop.classList.add("visible");
    }
    if (el.chatFabBtn) {
      el.chatFabBtn.classList.add("active");
    }
    if (el.tabChatBtn) {
      el.tabChatBtn.classList.add("active");
    }
    setTimeout(() => {
      if (el.chatInput) el.chatInput.focus();
    }, 150);
  }

  function closeChatDrawer() {
    if (!el.chatDrawer) return;
    el.chatDrawer.classList.remove("chat-drawer-open");
    el.chatDrawer.classList.add("chat-drawer-closed");
    if (el.chatBackdrop) {
      el.chatBackdrop.classList.remove("visible");
      el.chatBackdrop.classList.add("hidden");
    }
    if (el.chatFabBtn) {
      el.chatFabBtn.classList.remove("active");
    }
    if (el.tabChatBtn) {
      el.tabChatBtn.classList.remove("active");
    }
  }

  function toggleChatDrawer() {
    if (el.chatDrawer && el.chatDrawer.classList.contains("chat-drawer-open")) {
      closeChatDrawer();
    } else {
      openChatDrawer();
    }
  }

  function toggleChatDrawerWidth() {
    if (!el.chatDrawer) return;
    const isWide = el.chatDrawer.classList.toggle("chat-drawer-wide");
    if (el.expandIcon) {
      el.expandIcon.innerHTML = isWide
        ? '<polyline points="4 14 10 14 10 20"/><polyline points="20 10 14 10 14 4"/><line x1="14" y1="10" x2="21" y2="3"/><line x1="3" y1="21" x2="10" y2="14"/>'
        : '<path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/>';
    }
    if (el.chatExpandBtn) {
      el.chatExpandBtn.title = isWide ? "Standard Half Screen View" : "Toggle Wider View";
    }
  }

  function setupTabs() {
    el.tabBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        const targetId = btn.getAttribute("data-tab");
        if (targetId === "tab-chat" || btn.id === "tab-chat-btn") {
          openChatDrawer();
          return;
        }

        el.tabBtns.forEach((b) => {
          b.classList.remove("active");
          b.setAttribute("aria-selected", "false");
        });
        el.tabPanes.forEach((p) => p.classList.remove("active"));

        btn.classList.add("active");
        btn.setAttribute("aria-selected", "true");
        const targetPane = document.getElementById(targetId);
        if (targetPane) targetPane.classList.add("active");
      });
    });

    el.filterPills.forEach((btn) => {
      btn.addEventListener("click", () => {
        applyExclusionFilter(btn.getAttribute("data-filter"));
      });
    });
  }

  // ── Chat & Q&A Workflow ────────────────────────────────────────────────
  function setupChat() {
    if (el.chatFabBtn) {
      el.chatFabBtn.addEventListener("click", toggleChatDrawer);
    }

    if (el.chatCloseBtn) {
      el.chatCloseBtn.addEventListener("click", closeChatDrawer);
    }

    if (el.chatBackdrop) {
      el.chatBackdrop.addEventListener("click", closeChatDrawer);
    }

    if (el.chatExpandBtn) {
      el.chatExpandBtn.addEventListener("click", toggleChatDrawerWidth);
    }

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && el.chatDrawer && el.chatDrawer.classList.contains("chat-drawer-open")) {
        closeChatDrawer();
      }
    });

    el.chatForm.addEventListener("submit", (e) => {
      e.preventDefault();
      handleChatSubmit();
    });

    el.chatInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleChatSubmit();
      }
    });

    // Quick chip questions
    el.quickChips.forEach((chip) => {
      chip.addEventListener("click", () => {
        const q = chip.getAttribute("data-q");
        if (q) {
          el.chatInput.value = q;
          handleChatSubmit();
        }
      });
    });
  }

  async function handleChatSubmit() {
    const question = el.chatInput.value.trim();
    if (!question || state.isAsking) return;

    // Append User Message
    appendUserMessage(question);
    el.chatInput.value = "";
    el.chatSendBtn.disabled = true;
    state.isAsking = true;

    // Append loading placeholder
    const loadingId = "loading-" + Date.now();
    appendLoadingMessage(loadingId);

    try {
      if (!state.documentId) {
        removeLoadingMessage(loadingId);
        appendAssistantError("Please upload and analyze an insurance policy PDF first before asking questions.");
        return;
      }

      // ── Real RAG API Call (powered by ChromaDB + Gemini AI) ───────────
      const response = await fetch(ENDPOINTS.ASK, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          document_id: state.documentId,
          question: question,
        }),
      });

      const rawText = await response.text();
      let result = {};
      try {
        result = JSON.parse(rawText);
      } catch {
        result = { detail: rawText || `Server returned error (${response.status})` };
      }

      removeLoadingMessage(loadingId);

      if (!response.ok) {
        const errMsg = typeof result.detail === "string"
          ? result.detail
          : Array.isArray(result.detail)
            ? result.detail.map((e) => e.msg || JSON.stringify(e)).join(", ")
            : `Server error (${response.status})`;
        throw new Error(errMsg);
      }

      appendAssistantResponse(result.data);
    } catch (err) {
      removeLoadingMessage(loadingId);
      appendAssistantError(err.message || "Failed to retrieve an answer.");
    } finally {
      state.isAsking = false;
      el.chatSendBtn.disabled = false;
      el.chatMessages.scrollTop = el.chatMessages.scrollHeight;
      setTimeout(() => el.chatInput && el.chatInput.focus(), 100);
    }
  }

  function appendUserMessage(text) {
    const msg = document.createElement("div");
    msg.className = "message msg-user";
    msg.innerHTML = `
      <div class="msg-bubble">${escapeHtml(text)}</div>
    `;
    el.chatMessages.appendChild(msg);
    el.chatMessages.scrollTop = el.chatMessages.scrollHeight;
  }

  function appendLoadingMessage(id) {
    const msg = document.createElement("div");
    msg.id = id;
    msg.className = "message msg-assistant";
    msg.innerHTML = `
      <div class="msg-bubble" style="display:flex; align-items:center; gap:0.5rem; color:var(--text-dim);">
        <span class="status-dot" style="background:#818cf8; animation:pulse-dot 1s infinite;"></span>
        Searching policy excerpts & generating grounded answer...
      </div>
    `;
    el.chatMessages.appendChild(msg);
    el.chatMessages.scrollTop = el.chatMessages.scrollHeight;
  }

  function removeLoadingMessage(id) {
    const elLoad = document.getElementById(id);
    if (elLoad) elLoad.remove();
  }

  function appendAssistantError(errorText) {
    const msg = document.createElement("div");
    msg.className = "message msg-assistant";
    msg.innerHTML = `
      <div class="msg-bubble" style="border-left: 3px solid #f43f5e;">
        <p style="color:#fb7185; font-weight:600;">Could not retrieve answer:</p>
        <p style="font-size:0.86rem; color:#fecdd3;">${escapeHtml(errorText)}</p>
      </div>
    `;
    el.chatMessages.appendChild(msg);
  }

  function appendAssistantResponse(data) {
    const msg = document.createElement("div");
    msg.className = "message msg-assistant";

    const conf = (data.confidence || "high").toLowerCase();
    const confClass = conf === "high" ? "conf-high" : conf === "medium" ? "conf-medium" : "conf-low";

    // Format plain answer (convert newlines/bullets)
    const formattedAnswer = formatMarkdownText(data.answer || "No response provided.");

    // Sources markup
    let sourcesHtml = "";
    if (data.sources && data.sources.length > 0) {
      const sourceItems = data.sources
        .map(
          (s) => `
        <div class="source-item">
          <span class="source-page">${escapeHtml(s.page || "Page")}</span>
          <span class="source-quote">"${escapeHtml(s.excerpt || "")}"</span>
        </div>
      `
        )
        .join("");

      sourcesHtml = `
        <div class="sources-accordion">
          <button class="sources-toggle" type="button" onclick="this.nextElementSibling.classList.toggle('hidden');">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
            ${data.sources.length} Cited Policy Excerpt${data.sources.length > 1 ? "s" : ""}
          </button>
          <div class="sources-list hidden">
            ${sourceItems}
          </div>
        </div>
      `;
    }

    // Follow-ups markup
    let followUpsHtml = "";
    if (data.follow_up_questions && data.follow_up_questions.length > 0) {
      const followUpBtns = data.follow_up_questions
        .map(
          (q) => `
        <button class="follow-up-chip" type="button" data-question="${escapeHtml(q)}">${escapeHtml(q)}</button>
      `
        )
        .join("");

      followUpsHtml = `
        <div class="follow-ups-container">
          <span class="follow-up-label">Related Questions:</span>
          ${followUpBtns}
        </div>
      `;
    }

    msg.innerHTML = `
      <div class="msg-bubble">
        <div class="meta-row">
          <span class="confidence-pill ${confClass}">
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
            ${conf} Confidence
          </span>
        </div>
        <div class="answer-content">${formattedAnswer}</div>
        ${sourcesHtml}
        ${followUpsHtml}
      </div>
    `;

    // Attach listeners to new follow-up chips
    msg.querySelectorAll(".follow-up-chip").forEach((btn) => {
      btn.addEventListener("click", () => {
        const q = btn.getAttribute("data-question");
        if (q) {
          el.chatInput.value = q;
          handleChatSubmit();
        }
      });
    });

    el.chatMessages.appendChild(msg);
    el.chatMessages.scrollTop = el.chatMessages.scrollHeight;
  }

  // ── Helper: Basic Markdown to HTML Formatter ───────────────────────────
  function formatMarkdownText(text) {
    if (!text) return "";
    let html = escapeHtml(text);
    // Bold: **text** -> <strong>text</strong>
    html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    // Bullets: lines starting with - or *
    const lines = html.split("\n");
    let inList = false;
    let result = [];

    lines.forEach((line) => {
      const trimmed = line.trim();
      if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
        if (!inList) {
          result.push("<ul>");
          inList = true;
        }
        result.push(`<li>${trimmed.substring(2)}</li>`);
      } else {
        if (inList) {
          result.push("</ul>");
          inList = false;
        }
        if (trimmed) {
          result.push(`<p>${trimmed}</p>`);
        }
      }
    });
    if (inList) result.push("</ul>");
    return result.join("");
  }

  function escapeHtml(str) {
    if (typeof str !== "string") return str;
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // ── Setup Demo Sample Button ───────────────────────────────────────────
  function setupDemoButton() {
    el.demoSampleBtn.addEventListener("click", () => {
      hideError();
      state.isSample = true;
      state.documentId = SAMPLE_POLICY_DATA.document_id;
      state.analysis = SAMPLE_POLICY_DATA.analysis;

      startProcessingStepper();
      setTimeout(() => {
        stopProcessingStepper(true);
        renderDashboard(SAMPLE_POLICY_DATA);
        showToast("Loaded sample policy demo!");
      }, 1400);
    });
  }

  // ── Setup Reset & Copy ─────────────────────────────────────────────────
  function setupActions() {
    el.resetBtn.addEventListener("click", () => {
      clearSelectedFile();
      state.documentId = null;
      state.analysis = null;
      state.isSample = false;
      closeChatDrawer();
      if (el.chatFabContainer) el.chatFabContainer.classList.add("hidden");
      el.dashboardSection.classList.add("hidden");
      el.resetBtn.classList.add("hidden");
      el.uploadSection.classList.remove("hidden");
      hideError();
      window.scrollTo({ top: 0, behavior: "smooth" });
    });

    el.copyDocIdBtn.addEventListener("click", () => {
      const docId = el.docIdText.textContent;
      if (docId) {
        navigator.clipboard.writeText(docId).then(() => {
          showToast("Document ID copied!");
        });
      }
    });

    el.dismissErrorBtn.addEventListener("click", () => {
      hideError();
    });

    el.analyzeBtn.addEventListener("click", () => {
      triggerAnalyze();
    });
  }

  // ── Initialization ─────────────────────────────────────────────────────
  function init() {
    checkBackendHealth();
    setupDragAndDrop();
    setupTabs();
    setupChat();
    setupDemoButton();
    setupActions();
  }

  // Start when DOM is loaded
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
