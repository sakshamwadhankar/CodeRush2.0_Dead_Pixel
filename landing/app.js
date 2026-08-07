/* ==========================================================================
   AEGIS RESEARCH OS (AE-02) — INTERACTIVE FRONTEND LOGIC
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  // Elements
  const queryInput = document.getElementById('query-input');
  const runBtn = document.getElementById('run-demo-btn');
  const runBtnText = document.getElementById('run-btn-text');
  const resetBtn = document.getElementById('reset-demo-btn');
  const timeline = document.getElementById('execution-timeline');
  const evidenceScore = document.getElementById('evidence-score');
  const presetBtns = document.querySelectorAll('.preset-btn');
  const faqItems = document.querySelectorAll('.faq-item');

  // Default query text
  if (queryInput && presetBtns.length > 0) {
    queryInput.value = presetBtns[0].getAttribute('data-query');
  }

  // Preset button handling
  presetBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      presetBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      queryInput.value = btn.getAttribute('data-query');
    });
  });

  // Reset button handling
  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      if (queryInput) queryInput.value = '';
      if (timeline) {
        timeline.innerHTML = `
          <div class="log-entry">
            <span class="log-time">[00:00]</span>
            <span class="log-msg">Agent standby. Enter prompt and click "RUN RESEARCH PIPELINE".</span>
          </div>
        `;
      }
      if (evidenceScore) {
        evidenceScore.textContent = 'EVIDENCE SCORE: --';
        evidenceScore.style.color = 'var(--color-slate)';
      }
    });
  }

  // Live Research Simulator Execution
  let isRunning = false;

  if (runBtn) {
    runBtn.addEventListener('click', async () => {
      if (isRunning) return;
      const query = queryInput ? queryInput.value.trim() : '';

      if (!query) {
        alert('Please enter a research prompt or select a preset query.');
        return;
      }

      isRunning = true;
      runBtn.style.opacity = '0.7';
      runBtnText.textContent = 'EXECUTING PIPELINE...';
      timeline.innerHTML = '';
      evidenceScore.textContent = 'EVIDENCE SCORE: ANALYZING...';
      evidenceScore.style.color = 'var(--color-voltage-yellow)';

      const steps = [
        { time: '[00:01]', msg: 'Cognitive Planner: Strategy strategy_v2.yaml loaded. Step breakdown initialized.', type: 'info' },
        { time: '[00:02]', msg: 'Secure Browser: Playwright scraping target endpoints in headless sandbox...', type: 'info' },
        { time: '[00:04]', msg: 'Hybrid RAG: Vector search on ChromaDB + BM25Okapi sparse index complete.', type: 'info' },
        { time: '[00:05]', msg: 'Air-Gapped Sandbox: Python code verification executing in Docker container...', type: 'info' },
        { time: '[00:06]', msg: 'Evidence Graph: 18 citation nodes verified. Citation compiler score: 100%.', type: 'success' }
      ];

      for (let i = 0; i < steps.length; i++) {
        await new Promise(res => setTimeout(res, 600));
        const step = steps[i];
        const logEntry = document.createElement('div');
        logEntry.className = `log-entry ${step.type}`;
        logEntry.innerHTML = `
          <span class="log-time">${step.time}</span>
          <span class="log-msg">${step.msg}</span>
        `;
        timeline.appendChild(logEntry);
        timeline.scrollTop = timeline.scrollHeight;
      }

      // Try contacting local API if token or endpoint available
      try {
        const response = await fetch('http://127.0.0.1:8000/quarantine/status', {
          method: 'GET',
          headers: { 'Authorization': 'Bearer test-sandbox-token' }
        });
        if (response.ok) {
          const logEntry = document.createElement('div');
          logEntry.className = 'log-entry success';
          logEntry.innerHTML = `
            <span class="log-time">[00:07]</span>
            <span class="log-msg">Backend REST API Connected: 127.0.0.1:8000 (Live execution active).</span>
          `;
          timeline.appendChild(logEntry);
        }
      } catch (err) {
        // Standalone offline preview mode
      }

      evidenceScore.textContent = 'EVIDENCE SCORE: 100% VERIFIED';
      evidenceScore.style.color = 'var(--color-mint-chip)';
      runBtn.style.opacity = '1';
      runBtnText.textContent = 'RUN RESEARCH PIPELINE';
      isRunning = false;
    });
  }

  // FAQ Accordion
  faqItems.forEach(item => {
    const question = item.querySelector('.faq-question');
    if (question) {
      question.addEventListener('click', () => {
        const isActive = item.classList.contains('active');
        faqItems.forEach(i => i.classList.remove('active'));
        if (!isActive) {
          item.classList.add('active');
        }
      });
    }
  });

  // ON-SCROLL TYPOGRAPHY REVEAL INTERSECTION OBSERVER
  const scrollElements = document.querySelectorAll('.scroll-reveal');
  
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        }
      });
    }, {
      threshold: 0.12,
      rootMargin: '0px 0px -40px 0px'
    });

    scrollElements.forEach(el => observer.observe(el));
  } else {
    scrollElements.forEach(el => el.classList.add('is-visible'));
  }

  // MECHANICAL CUBE CHAIN / BINARY CLOCK LETTER-BY-LETTER FLIP ANIMATION
  const flipWords = ['ENTERPRISE', 'AUTONOMOUS', 'SCIENTIFIC', 'SECURITY', 'STRATEGIC', 'FINANCIAL', 'INTELLIGENCE'];
  let flipWordIdx = 0;
  const flipContainer = document.getElementById('flip-word-container');

  function renderWordCubes(word) {
    if (!flipContainer) return;
    flipContainer.innerHTML = '';
    word.split('').forEach((char, i) => {
      const cube = document.createElement('span');
      cube.className = 'char-cube flip-in';
      cube.textContent = char;
      flipContainer.appendChild(cube);
      
      // Staggered arrival animation
      setTimeout(() => {
        cube.classList.remove('flip-in');
      }, i * 45 + 30);
    });
  }

  if (flipContainer) {
    // Render initial word
    renderWordCubes(flipWords[0]);

    setInterval(() => {
      const cubes = flipContainer.querySelectorAll('.char-cube');
      
      // Step 1: Flip letters out sequentially from left to right like mechanical clock digits
      cubes.forEach((cube, i) => {
        setTimeout(() => {
          cube.classList.add('flip-out');
        }, i * 45);
      });

      // Step 2: Swap to new word after animation completes
      setTimeout(() => {
        flipWordIdx = (flipWordIdx + 1) % flipWords.length;
        renderWordCubes(flipWords[flipWordIdx]);
      }, (cubes.length * 45) + 260);
    }, 3200);
  }
});



