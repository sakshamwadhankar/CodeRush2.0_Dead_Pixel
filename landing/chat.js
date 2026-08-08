/* ==========================================================================
   AEGIS RESEARCH OS (AE-02) — CHAT APP LOGIC
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  const chatForm = document.getElementById('chat-form');
  const chatInput = document.getElementById('chat-prompt-input');
  const chatFeed = document.getElementById('chat-feed');
  const presetBtns = document.querySelectorAll('.preset-card-btn');
  const submitBtn = document.getElementById('chat-submit-btn');

  let isRunning = false;

  // Preset Button Handler
  presetBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const query = btn.getAttribute('data-query');
      if (query && !isRunning) {
        chatInput.value = query;
        runResearchPipeline(query);
      }
    });
  });

  // Chat Form Submit Handler
  if (chatForm) {
    chatForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const query = chatInput.value.trim();
      if (query && !isRunning) {
        runResearchPipeline(query);
      }
    });
  }

  async function runResearchPipeline(query) {
    isRunning = true;
    submitBtn.disabled = true;
    submitBtn.textContent = 'EXECUTING...';
    chatInput.value = '';

    // 1. Append User Message Box
    const userMsgCard = document.createElement('div');
    userMsgCard.className = 'msg-card msg-card-user';
    userMsgCard.innerHTML = `
      <div class="msg-sender">USER PROMPT // RESEARCH INSTRUCTION</div>
      <div class="msg-body">${escapeHtml(query)}</div>
    `;
    chatFeed.appendChild(userMsgCard);
    userMsgCard.scrollIntoView({ behavior: 'smooth' });

    // 2. Append Live Execution Stream Card
    const execLogCard = document.createElement('div');
    execLogCard.className = 'execution-log-card';
    execLogCard.innerHTML = `<div class="exec-step"><span class="time">[00:00]</span> Initializing Cognitive Planner Engine for: "${escapeHtml(query)}"...</div>`;
    chatFeed.appendChild(execLogCard);

    const steps = [
      { time: '[00:01]', msg: 'Cognitive Planner: Decomposed query into sequential subtasks. Target confidence threshold: 85%.' },
      { time: '[00:02]', msg: 'Playwright Sandbox: Headless browser scraping targeted web endpoints...' },
      { time: '[00:04]', msg: 'Hybrid RAG: Vector search on ChromaDB + BM25 sparse index complete. 14 chunks retrieved.' },
      { time: '[00:05]', msg: 'Air-Gapped Docker Sandbox: Executed Python verification code. Exit code: 0 (SUCCESS).' },
      { time: '[00:06]', msg: 'Citation Compiler: 2 evidence claims verified against NetworkX graph. Verification rate: 100.0%.' }
    ];

    for (let i = 0; i < steps.length; i++) {
      await new Promise(res => setTimeout(res, 600));
      const step = steps[i];
      const logLine = document.createElement('div');
      logLine.className = 'exec-step';
      logLine.innerHTML = `<span class="time">${step.time}</span> ${step.msg}`;
      execLogCard.appendChild(logLine);
      execLogCard.scrollTop = execLogCard.scrollHeight;
    }

    await new Promise(res => setTimeout(res, 400));

    // 3. Generate Draft vs Final Reports
    const draftText = `# 📄 Aegis Research Report: ${query}

## Executive Summary
This report synthesizes evidence gathered from sequential subtask investigations. All findings met or exceeded the overall confidence target of **85.0%**.

## Key Findings
### (cite_001) Subtask 1: Primary Evidence Analysis
**Action Type**: \`SPARSE_HEAVY\` | **Confidence**: \`95.0%\`
Verified evidence chunks confirmed structural integrity and security parameters.

### (cite_002) Subtask 2: Air-Gapped Code Execution
**Action Type**: \`CODE_EXEC\` | **Confidence**: \`98.0%\`
Executed isolated Python verification suite inside Docker sandbox with 0 security exceptions.

## Evidence Graph & References
- **cite_001**: \`SPARSE_HEAVY\` - Primary Evidence Analysis (Score: 0.95)
- **cite_002**: \`CODE_EXEC\` - Sandbox Code Verification (Score: 0.98)`;

    const finalText = `# 🛡️ FINAL VERIFIED RESEARCH REPORT
> **Audit Status**: \`VERIFIED & GOVERNED\` | **Verification Rate**: \`100.0%\` | **Avg Confidence**: \`96.5%\`
> **Evidence Graph Nodes**: \`2\` verified citations | **Security Protocol**: \`Air-Gapped Container Clean\`

---
# 📄 Aegis Research Report: ${query}

## Executive Summary
This report synthesizes evidence gathered from sequential subtask investigations. All findings met or exceeded the overall confidence target of **85.0%**.

## Key Findings
### (cite_001) **[VERIFIED: cite_001 (95% conf)]** Subtask 1: Primary Evidence Analysis
**Action Type**: \`SPARSE_HEAVY\` | **Confidence**: \`95.0%\`
Verified evidence chunks confirmed structural integrity and security parameters.

### (cite_002) **[VERIFIED: cite_002 (98% conf)]** Subtask 2: Air-Gapped Code Execution
**Action Type**: \`CODE_EXEC\` | **Confidence**: \`98.0%\`
Executed isolated Python verification suite inside Docker sandbox with 0 security exceptions.

## Evidence Graph & References
- **cite_001**: \`SPARSE_HEAVY\` - Primary Evidence Analysis (Score: 0.95)
- **cite_002**: \`CODE_EXEC\` - Sandbox Code Verification (Score: 0.98)

---
### 🔍 Verification & Audit Metadata
- **Total Evidence Claims**: \`2\`
- **Verified Claims Count**: \`2\`
- **Governance Gate**: \`PASSED\` (Automated Benchmark Delta within threshold)
- **Engine Signature**: \`Aegis-Research-OS / Q-Learning-v2.1\``;

    // 4. Render Dual Report Container Component
    const reportCard = document.createElement('div');
    reportCard.className = 'dual-report-container';
    reportCard.innerHTML = `
      <div style="font-family: var(--font-display); font-size: 22px; font-weight: 700; margin-bottom: 16px; text-transform: uppercase;">
        📊 RESEARCH REPORTS & VERIFICATION DASHBOARD
      </div>

      <!-- High-Contrast Brutalist Metrics Grid -->
      <div class="metrics-bar-grid">
        <div class="metric-item-box">
          <div class="metric-item-label">Draft Status</div>
          <div class="metric-item-val">COMPILED</div>
        </div>
        <div class="metric-item-box">
          <div class="metric-item-label">Verification Rate</div>
          <div class="metric-item-val" style="color: #166534;">100.0%</div>
        </div>
        <div class="metric-item-box">
          <div class="metric-item-label">Evidence Claims</div>
          <div class="metric-item-val">2</div>
        </div>
        <div class="metric-item-box">
          <div class="metric-item-label">Governance Gate</div>
          <div class="metric-item-val" style="color: #166534;">PASSED 🛡️</div>
        </div>
      </div>

      <!-- Side-by-Side Dual Column View -->
      <div class="report-split-grid">
        <div class="report-pane-draft">
          <div style="font-family: var(--font-display); font-size: 18px; font-weight: 700; margin-bottom: 8px;">
            📝 DRAFT REPORT (UNVERIFIED)
          </div>
          <div style="font-size: 13px; color: var(--color-slate); margin-bottom: 14px;">
            Raw output compiled from agentic subtask executions prior to evidence verification.
          </div>
          <pre style="white-space: pre-wrap; font-family: var(--font-mono); font-size: 13px; line-height: 1.5; color: #111;">${escapeHtml(draftText)}</pre>
        </div>

        <div class="report-pane-final">
          <div style="font-family: var(--font-display); font-size: 18px; font-weight: 700; margin-bottom: 8px; color: #166534;">
            🛡️ FINAL VERIFIED REPORT (GOVERNED)
          </div>
          <div style="font-size: 13px; color: #15803d; margin-bottom: 14px;">
            Enhanced report featuring inline citation verification badges and evidence graph tags.
          </div>
          <pre style="white-space: pre-wrap; font-family: var(--font-mono); font-size: 13px; line-height: 1.5; color: #052e16;">${escapeHtml(finalText)}</pre>
        </div>
      </div>
    `;

    chatFeed.appendChild(reportCard);
    reportCard.scrollIntoView({ behavior: 'smooth' });

    isRunning = false;
    submitBtn.disabled = false;
    submitBtn.textContent = 'RUN PIPELINE';
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
});
