(() => {
  'use strict';
  const D = window.DPWE;
  if (!D) return;

  const DATA_ROOT = '../engineering_data/';
  const STATE_PATHS = {
    index: 'index.json',
    federation: 'federation/source_manifest.json',
    state: 'firmware/state_machine.json'
  };

  const esc = value => String(value ?? '')
    .replaceAll('&', '&amp;').replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;').replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');

  const statusClass = status => {
    const s = String(status || '').toUpperCase();
    if (s === 'VERIFIED' || s === 'VERIFIED_SOURCE' || s === 'SOURCE_VERIFIED') return 'truth-ok';
    if (s === 'PENDING' || s.startsWith('PENDING_') || s === 'STALE' || s === 'SNAPSHOT') return 'truth-pending';
    return 'truth-not-claimed';
  };

  async function loadJson(path) {
    const response = await fetch(`${DATA_ROOT}${path}`, {cache: 'no-store'});
    if (!response.ok) throw new Error(`${path}: HTTP ${response.status}`);
    return response.json();
  }

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

  function renderProductionState(state) {
    if (!state || !Array.isArray(state.system_states)) {
      renderProductionStateUnavailable(new Error('state snapshot missing SystemState vocabulary'));
      return;
    }

    const badge = D.$('stateTruthStatus');
    if (badge) {
      badge.classList.remove('danger');
      badge.textContent = 'SNAPSHOT VOCABULARY · PARTIAL TRANSITIONS';
    }

    const authority = D.$('prodAuthorityCards');
    if (authority) {
      const rows = [
        ['Snapshot SystemState owner', state.owner || 'CPU1', state.trust || 'verified_source'],
        ['Browser authority', 'read-only view', 'verified_source'],
        ['Transition completeness', state.transition_completeness || 'partial', 'pending_verification']
      ];
      authority.innerHTML = rows.map(([k,v,t]) =>
        `<div class="card authority ${statusClass(t)}"><span>${esc(k)}</span><strong>${esc(v)}</strong><small>${esc(t)}</small></div>`).join('');
    }

    const graph = D.$('prodStateGraph');
    if (graph) {
      graph.innerHTML = state.system_states.map(x =>
        `<button type="button" class="state-node ${x.id === 'FAULT' ? 'fault-node' : ''}" data-prod-state="${esc(x.id)}"><span>${esc(x.id)}</span><small>${esc(x.value)}</small></button>`).join('');
      graph.querySelectorAll('[data-prod-state]').forEach(button => button.addEventListener('click', () => {
        const id = button.dataset.prodState;
        const selected = state.system_states.find(x => x.id === id);
        const detail = D.$('prodStateDetail');
        if (detail) detail.innerHTML = `
          <h3>${esc(id)}</h3>
          <p><b>enum value:</b> ${esc(selected?.value)}</p>
          <p><b>snapshot owner:</b> ${esc(state.owner)}</p>
          <p><b>trust within snapshot:</b> ${esc(state.trust)}</p>
          <p class="note">Current live behavior must be checked against the Execution Plane exact SHA.</p>`;
      }));
    }

    const transitions = D.$('prodTransitionList');
    if (transitions) {
      transitions.innerHTML = `
        <div class="truth-boundary truth-pending"><strong>FAIL CLOSED</strong><span data-eng-zh="完整 transition/guard 未包含於此 pinned snapshot；只顯示已擷取且有 evidence 的 transition。" data-eng-en="The complete transition/guard table is not present in this pinned snapshot. Only extracted transitions with evidence are shown.">完整 transition/guard 未包含於此 pinned snapshot；只顯示已擷取且有 evidence 的 transition。</span></div>
        ${(state.verified_transitions || []).map(t => `<div class="transition"><b>${esc(t.from)} → ${esc(t.to)}</b><span>${esc(t.guard)}</span><small>${esc(t.evidence)}</small></div>`).join('')}`;
    }
    const history = D.$('prodTransitionHistory');
    if (history) history.innerHTML = `<p class="note">${esc((state.pending || []).join(' · '))}</p>`;
  }

  function renderProductionStateUnavailable(error) {
    const reason = error?.message || 'state snapshot unavailable';
    const badge = D.$('stateTruthStatus');
    if (badge) {
      badge.classList.add('danger');
      badge.textContent = 'STATE TRUTH UNAVAILABLE';
    }
    const authority = D.$('prodAuthorityCards');
    if (authority) authority.innerHTML = '<div class="card authority truth-not-claimed"><span>Production state truth</span><strong>UNAVAILABLE</strong><small>fail-closed</small></div>';
    const graph = D.$('prodStateGraph');
    if (graph) graph.innerHTML = '<div class="truth-boundary truth-not-claimed"><strong>FAIL CLOSED</strong><span>No reference state machine is substituted for missing production state truth.</span></div>';
    const detail = D.$('prodStateDetail');
    if (detail) detail.innerHTML = `<p class="note">${esc(reason)}</p>`;
    const transitions = D.$('prodTransitionList');
    if (transitions) transitions.innerHTML = '<div class="truth-boundary truth-not-claimed"><strong>UNKNOWN</strong><span>Transition truth unavailable.</span></div>';
    const history = D.$('prodTransitionHistory');
    if (history) history.innerHTML = '<p class="note">No production transition claim is made.</p>';
  }

  async function initializeProductionStateTruth() {
    try {
      const [index, federation, state] = await Promise.all([
        loadJson(STATE_PATHS.index),
        loadJson(STATE_PATHS.federation),
        loadJson(STATE_PATHS.state)
      ]);
      if (index.authoritative_engineering_truth !== false || federation.authoritative_engineering_truth !== false) {
        throw new Error('state truth boundary invalid: Workbench must remain a derived view');
      }
      if (index.baseline?.commit !== state.baseline) {
        throw new Error(`state baseline ${state.baseline || 'UNKNOWN'} != snapshot baseline ${index.baseline?.commit || 'UNKNOWN'}`);
      }
      const manifestCommit = federation.current_workbench_snapshot?.commit;
      if (manifestCommit && manifestCommit !== state.baseline) {
        throw new Error(`federation snapshot ${manifestCommit} != state baseline ${state.baseline}`);
      }
      D.stateTruth = {index, federation, state};
      renderProductionState(state);
      D.refreshLanguage();
      document.dispatchEvent(new CustomEvent('dpwe:state-truth-ready', {detail: D.stateTruth}));
    } catch (error) {
      console.error('Production state truth unavailable', error);
      renderProductionStateUnavailable(error);
    }
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

  initializeProductionStateTruth();
})();
