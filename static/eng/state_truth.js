(() => {
  'use strict';
  const D = window.DPWE;
  if (!D) return;

  function referenceBoundary(panel, zh, en) {
    if (!panel || panel.querySelector('.state-reference-boundary')) return;
    const head = panel.querySelector('.panel-head');
    if (!head) return;
    const box = document.createElement('div');
    box.className = 'truth-boundary truth-pending state-reference-boundary';
    box.innerHTML = `<strong>DEMO / REFERENCE</strong><span data-eng-zh="${zh}" data-eng-en="${en}">${D.text(zh, en)}</span>`;
    head.insertAdjacentElement('afterend', box);
  }

  function createProductionStateTruthPanel() {
    if (D.$('state-truth')) return;
    D.addPanel('state-truth', '韌體狀態真值', 'Firmware State Truth', `
      <section id="state-truth" class="panel">
        <div class="panel-head">
          <div><div class="eyebrow">OWNER SOURCE → SNAPSHOT → READ-ONLY VIEW</div><h2 data-eng-zh="ASR5K 韌體狀態真值" data-eng-en="ASR5K Firmware State Truth">ASR5K 韌體狀態真值</h2></div>
          <span id="stateTruthStatus" class="badge">LOADING</span>
        </div>
        <div class="truth-boundary truth-pending"><strong>READ ONLY</strong><span data-eng-zh="只呈現 baseline-bound source snapshot 已證明的 SystemState vocabulary / transition evidence；未知 guard 或未擷取 transition 不得由瀏覽器補猜。" data-eng-en="Shows only SystemState vocabulary and transition evidence proven by the baseline-bound source snapshot. Unknown guards or unextracted transitions are never invented by the browser.">只呈現 baseline-bound source snapshot 已證明的 SystemState vocabulary / transition evidence；未知 guard 或未擷取 transition 不得由瀏覽器補猜。</span></div>
        <div id="prodAuthorityCards" class="authority-grid"></div>
        <div class="card state-card"><div id="prodStateGraph" class="state-graph"></div></div>
        <div class="grid two state-lower">
          <div class="card"><h3 data-eng-zh="選取狀態" data-eng-en="Selected state">選取狀態</h3><div id="prodStateDetail" class="detail">Loading state truth…</div></div>
          <div class="card"><h3 data-eng-zh="已擷取 transition / 未知缺口" data-eng-en="Extracted transitions / unknown gaps">已擷取 transition / 未知缺口</h3><div id="prodTransitionList" class="transition-list"></div><div id="prodTransitionHistory" class="history"></div></div>
        </div>
      </section>`);
  }

  function moveReferenceNav(panelId, zh, en) {
    const sidebar = D.q('.sidebar');
    if (!sidebar) return false;
    const demoGroup = D.qa('.nav-group-label', sidebar).find(el => el.textContent.trim() === 'DEMO / REFERENCE');
    const nav = D.q(`.nav[data-panel="${panelId}"]`, sidebar);
    if (!demoGroup || !nav) return false;
    nav.removeAttribute('data-i18n');
    D.setBi(nav, zh, en);
    const stateNav = D.q('.nav[data-panel="state"]', sidebar);
    if (panelId === 'state') demoGroup.insertAdjacentElement('afterend', nav);
    else if (stateNav) stateNav.insertAdjacentElement('afterend', nav);
    else demoGroup.insertAdjacentElement('afterend', nav);
    return true;
  }

  function markReferencePanels() {
    if (moveReferenceNav('state', '狀態模擬器（參考）', 'State Simulator (Reference)')) {
      const panel = D.$('state');
      const heading = panel?.querySelector('.panel-head h2');
      const badge = panel?.querySelector('.panel-head .badge');
      if (heading) {
        heading.removeAttribute('data-i18n');
        D.setBi(heading, '狀態 Policy 模擬器', 'State Policy Simulator');
      }
      if (badge) {
        badge.removeAttribute('data-i18n');
        badge.textContent = 'REFERENCE MODEL';
      }
      referenceBoundary(
        panel,
        '此模擬器不是 ASR5K current production state truth；只用於 policy / UI 行為參考。',
        'This simulator is not current ASR5K production state truth. It is only a policy/UI reference.'
      );
    }

    if (moveReferenceNav('contract', '狀態 Contract（參考）', 'State Contract (Reference)')) {
      referenceBoundary(
        D.$('contract'),
        '此 Contract 工具是通用 reference validator，不得覆蓋 production source-derived state truth。',
        'This contract tool is a generic reference validator and cannot override production source-derived state truth.'
      );
      return true;
    }
    return false;
  }

  createProductionStateTruthPanel();
  markReferencePanels();

  const sidebar = D.q('.sidebar');
  if (sidebar && !D.q('.nav[data-panel="contract"]', sidebar)) {
    const observer = new MutationObserver(() => {
      if (markReferencePanels()) observer.disconnect();
    });
    observer.observe(sidebar, {childList: true});
  }
})();
