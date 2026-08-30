(() => {
  'use strict';
  const D = window.DPWE;
  if (!D) return;

  const DATA_ROOT = '../engineering_data/';
  const RESOURCE_PATHS = {
    index: 'index.json',
    state: 'firmware/state_machine.json',
    ownership: 'architecture/ownership_matrix.json',
    scaling: 'firmware/scaling.json',
    protocol: 'protocol/host_protocol.json',
    commands: 'protocol/command_dictionary.json',
    verification: 'verification/verification_matrix.json',
    control: 'control/index.json',
    safety: 'ai/safety_invariants.json'
  };

  const esc = value => String(value ?? '')
    .replaceAll('&', '&amp;').replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;').replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');

  const statusClass = status => {
    const s = String(status || '').toUpperCase();
    if (s === 'VERIFIED' || s === 'SOURCE_VERIFIED') return 'truth-ok';
    if (s === 'GOVERNANCE_CONTRACT') return 'truth-governance';
    if (s === 'PENDING' || s.startsWith('PENDING_')) return 'truth-pending';
    return 'truth-not-claimed';
  };

  async function loadJson(path) {
    const response = await fetch(`${DATA_ROOT}${path}`, {cache: 'no-store'});
    if (!response.ok) throw new Error(`${path}: HTTP ${response.status}`);
    return response.json();
  }

  function addEvidenceBanner(panelId, trust, zh, en) {
    const panel = D.$(panelId);
    if (!panel || panel.querySelector('.truth-boundary')) return;
    const head = panel.querySelector('.panel-head');
    if (!head) return;
    const box = document.createElement('div');
    box.className = `truth-boundary ${statusClass(trust)}`;
    box.innerHTML = `<strong>${esc(trust)}</strong><span data-eng-zh="${esc(zh)}" data-eng-en="${esc(en)}">${esc(D.text(zh, en))}</span>`;
    head.insertAdjacentElement('afterend', box);
  }

  function renderTruthPanel(truth) {
    const panel = D.addPanel('engineering-truth', '工程真相', 'Engineering Truth', `
      <section id="engineering-truth" class="panel">
        <div class="panel-head">
          <div><div class="eyebrow">SOURCE → EVIDENCE → TRUST</div><h2 data-eng-zh="工程真相／資格狀態" data-eng-en="Engineering Truth / Qualification Status">工程真相／資格狀態</h2></div>
          <span class="badge">FAIL-CLOSED DATA</span>
        </div>
        <div id="truthBaseline" class="card truth-baseline"></div>
        <div id="truthSummary" class="truth-summary"></div>
        <div class="grid two">
          <div class="card"><h3 data-eng-zh="Production SPIB 合約" data-eng-en="Production SPIB contract">Production SPIB 合約</h3><div id="truthProtocol"></div></div>
          <div class="card"><h3 data-eng-zh="Scalar register" data-eng-en="Scalar registers">Scalar register</h3><div id="truthScaling"></div></div>
        </div>
        <div class="grid two">
          <div class="card"><h3 data-eng-zh="已驗證" data-eng-en="Verified">已驗證</h3><div id="truthVerified" class="truth-list"></div></div>
          <div class="card"><h3 data-eng-zh="待實證／未宣告" data-eng-en="Pending / not claimed">待實證／未宣告</h3><div id="truthPending" class="truth-list"></div></div>
        </div>
        <div class="card"><h3 data-eng-zh="資料使用規則" data-eng-en="Consumer rules">資料使用規則</h3><div id="truthPolicy"></div></div>
      </section>`);
    if (!panel) return;

    const idx = truth.index;
    D.$('truthBaseline').innerHTML = `
      <div><span>Production repo</span><strong>${esc(idx.baseline.repository)}</strong></div>
      <div><span>Branch</span><strong>${esc(idx.baseline.branch)}</strong></div>
      <div><span>Exact baseline SHA</span><code>${esc(idx.baseline.commit)}</code></div>
      <div><span>Qualification</span><strong class="truth-pending">NOT CLAIMED UNTIL EVIDENCE</strong></div>`;

    const scope = truth.verification.scope || [];
    const counts = scope.reduce((acc, row) => {
      const k = String(row.status || 'UNKNOWN').toUpperCase();
      acc[k] = (acc[k] || 0) + 1;
      return acc;
    }, {});
    D.$('truthSummary').innerHTML = Object.entries(counts).map(([k,v]) =>
      `<div class="card truth-stat ${statusClass(k)}"><strong>${v}</strong><span>${esc(k)}</span></div>`).join('');

    const p = truth.protocol;
    D.$('truthProtocol').innerHTML = `
      <dl class="truth-dl">
        <dt>Transport</dt><dd>${esc(p.transport?.name || 'SPIB NORMAL')}</dd>
        <dt>Request</dt><dd>${esc(p.transport?.request_bits)}-bit · [31:16] address · [15:0] data</dd>
        <dt>Response</dt><dd>${esc(p.transport?.response_timing)}</dd>
        <dt>NULL frame</dt><dd><code>${esc(p.null_frame?.value || '0xFFFF0000')}</code></dd>
        <dt>Queue depth</dt><dd>${esc(truth.commands?.queue_depth)}</dd>
      </dl>`;

    const verifiedScaling = (truth.scaling.scalings || [])
      .filter(x => String(x.trust || 'verified_source') === 'verified_source');
    D.$('truthScaling').innerHTML = verifiedScaling.length
      ? verifiedScaling.map(x => `<div class="truth-row"><code>${esc(x.id)}</code><span>${esc((x.wire_addresses || []).join(' / '))} · ×${esc(x.scale)} ${esc(x.unit || '')}</span></div>`).join('')
      : `<p class="note" data-eng-zh="已驗證的 register/scaling 請以 engineering_data 為準；未驗證 analog scaling 保持 null。" data-eng-en="Use engineering_data for verified register/scaling facts; unverified analog scaling remains null.">已驗證的 register/scaling 請以 engineering_data 為準；未驗證 analog scaling 保持 null。</p>`;

    const verified = scope.filter(x => ['VERIFIED','GOVERNANCE_CONTRACT','SOURCE_VERIFIED'].includes(String(x.status).toUpperCase()));
    const pending = scope.filter(x => !['VERIFIED','GOVERNANCE_CONTRACT','SOURCE_VERIFIED'].includes(String(x.status).toUpperCase()));
    const renderRows = rows => rows.map(x => `<div class="truth-item ${statusClass(x.status)}"><span>${esc(x.status)}</span><b>${esc(x.item)}</b>${x.evidence ? `<small>${esc(x.evidence)}</small>` : ''}</div>`).join('');
    D.$('truthVerified').innerHTML = renderRows(verified);
    D.$('truthPending').innerHTML = renderRows(pending);

    D.$('truthPolicy').innerHTML = `
      <p><b>unknown_value:</b> <code>${esc(idx.consumer_policy.unknown_value)}</code></p>
      <p><b>unknown_action:</b> <code>${esc(idx.consumer_policy.unknown_action)}</code></p>
      <p><b>source_conflict_action:</b> <code>${esc(idx.consumer_policy.source_conflict_action)}</code></p>
      <p><b>browser_safety_authority:</b> <code>${esc(idx.consumer_policy.browser_safety_authority)}</code></p>
      <p class="note">${esc(truth.verification.policy)}</p>`;
  }

  function renderProductionState(truth) {
    const s = truth.state;
    const panel = D.$('state');
    if (!panel) return;

    const modelBadge = panel.querySelector('.panel-head .badge');
    if (modelBadge) {
      modelBadge.classList.remove('danger');
      modelBadge.textContent = 'PRODUCTION VOCABULARY · PARTIAL TRANSITIONS';
    }

    const authority = D.$('authorityCards');
    if (authority) {
      const ownerRows = [
        ['SystemState owner', s.owner || 'CPU1', 'verified_source'],
        ['Browser authority', 'operator intent only', 'verified_source'],
        ['Transition completeness', s.transition_completeness || 'partial', 'pending_verification']
      ];
      authority.innerHTML = ownerRows.map(([k,v,t]) =>
        `<div class="card authority ${statusClass(t)}"><span>${esc(k)}</span><strong>${esc(v)}</strong><small>${esc(t)}</small></div>`).join('');
    }

    const graph = D.$('stateGraph');
    if (graph) {
      graph.innerHTML = (s.system_states || []).map(x =>
        `<button type="button" class="state-node ${x.id === 'FAULT' ? 'fault-node' : ''}" data-prod-state="${esc(x.id)}"><span>${esc(x.id)}</span><small>${esc(x.value)}</small></button>`).join('');
      graph.querySelectorAll('[data-prod-state]').forEach(button => button.addEventListener('click', () => {
        const id = button.dataset.prodState;
        const state = (s.system_states || []).find(x => x.id === id);
        const detail = D.$('stateDetail');
        if (detail) detail.innerHTML = `
          <h3>${esc(id)}</h3>
          <p><b>enum value:</b> ${esc(state?.value)}</p>
          <p><b>owner:</b> ${esc(s.owner)}</p>
          <p><b>trust:</b> ${esc(s.trust)}</p>
          <p class="note">${esc((s.safety_rules || []).join(' · '))}</p>`;
      }));
    }

    const sim = D.$('simState');
    if (sim) sim.textContent = 'DISABLED · PARTIAL EVIDENCE';
    const transitions = D.$('transitionList');
    if (transitions) {
      transitions.innerHTML = `
        <div class="truth-boundary truth-pending"><strong>FAIL CLOSED</strong><span data-eng-zh="完整 transition/guard 尚未由 exact source 抽完，因此禁止把參考 simulator 當 production state machine。" data-eng-en="The complete transition/guard table is not yet extracted from exact source, so the reference simulator is disabled as a production representation.">完整 transition/guard 尚未由 exact source 抽完，因此禁止把參考 simulator 當 production state machine。</span></div>
        ${(s.verified_transitions || []).map(t => `<div class="transition"><b>${esc(t.from)} → ${esc(t.to)}</b><span>${esc(t.guard)}</span><small>${esc(t.evidence)}</small></div>`).join('')}`;
    }
    const history = D.$('transitionHistory');
    if (history) history.innerHTML = `<p class="note">${esc((s.pending || []).join(' · '))}</p>`;
  }

  function applyBoundaries(truth) {
    const analogPending = (truth.verification.scope || []).some(x =>
      x.item === 'ADC measurement scaling/calibration' && String(x.status).toUpperCase() === 'PENDING');
    addEvidenceBanner('measurement', analogPending ? 'PENDING' : 'VERIFIED',
      '此計算器是工程計算工具；production ADC scaling/calibration 尚未驗證，不能把預設係數當 ASR5K 實機值。',
      'This is an engineering calculator. Production ADC scaling/calibration is not yet verified; defaults are not ASR5K hardware truth.');

    addEvidenceBanner('control', truth.control.status === 'pending_verification' ? 'PENDING' : 'VERIFIED',
      '目前 plant/controller/SFRA 為分析工具；尚未建立完整 production operating-point evidence package。',
      'Plant/controller/SFRA views are analysis tools; a complete production operating-point evidence package is not yet established.');

    addEvidenceBanner('remote', 'VERIFIED',
      'Production SPIB framing/queue contract已由 exact source 驗證；本頁控制 transport 仍是 MOCK，瀏覽器沒有 safety authority。',
      'Production SPIB framing/queue contracts are source-verified; this control transport remains MOCK and the browser has no safety authority.');
  }

  async function initializeTruth() {
    try {
      const loaded = {};
      await Promise.all(Object.entries(RESOURCE_PATHS).map(async ([key,path]) => { loaded[key] = await loadJson(path); }));
      if (loaded.index.baseline.commit !== loaded.state.baseline ||
          loaded.index.baseline.commit !== loaded.verification.baseline) {
        throw new Error('engineering_data baseline mismatch');
      }
      D.truth = loaded;
      renderTruthPanel(loaded);
      renderProductionState(loaded);
      applyBoundaries(loaded);
      D.refreshLanguage();
      document.dispatchEvent(new CustomEvent('dpwe:truth-ready', {detail: loaded}));
    } catch (error) {
      console.error('Engineering truth layer unavailable', error);
      ['measurement','control','state','remote'].forEach(id =>
        addEvidenceBanner(id, 'PENDING', '工程真相資料載入失敗；依 fail-closed 規則，不宣告 production qualification。',
          'Engineering truth data failed to load. Fail-closed policy: no production qualification is claimed.'));
    }
  }

  initializeTruth();
})();
