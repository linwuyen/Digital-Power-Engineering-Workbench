(() => {
  'use strict';
  const D = window.DPWE;
  if (!D) return;

  const DATA_ROOT = '../engineering_data/';
  const RESOURCE_PATHS = {
    index: 'index.json',
    federation: 'federation/source_manifest.json',
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
    if (s === 'PENDING' || s.startsWith('PENDING_') || s === 'STALE' || s === 'SNAPSHOT') return 'truth-pending';
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

  function renderTruthPanel(snapshot) {
    const panel = D.addPanel('engineering-truth', '工程快照', 'Engineering Snapshot', `
      <section id="engineering-truth" class="panel">
        <div class="panel-head">
          <div><div class="eyebrow">FEDERATED SOURCES → DERIVED SNAPSHOT → VIEW</div><h2 data-eng-zh="工程快照／資格視圖" data-eng-en="Engineering Snapshot / Qualification View">工程快照／資格視圖</h2></div>
          <span class="badge">DERIVED SNAPSHOT</span>
        </div>
        <div class="truth-boundary truth-pending"><strong>VIEW ONLY</strong><span data-eng-zh="此頁不是 ASR5K current truth owner。產品/架構以 ASR5K_AGENT 為準；implementation/build/HIL/qualification 以 ASR5K_v2_28384 exact identity/evidence 為準。" data-eng-en="This page is not the ASR5K current-truth owner. Product/architecture authority is ASR5K_AGENT; implementation/build/HIL/qualification authority is exact ASR5K_v2_28384 identity/evidence.">此頁不是 ASR5K current truth owner。產品/架構以 ASR5K_AGENT 為準；implementation/build/HIL/qualification 以 ASR5K_v2_28384 exact identity/evidence 為準。</span></div>
        <div id="truthBaseline" class="card truth-baseline"></div>
        <div id="truthSummary" class="truth-summary"></div>
        <div class="grid two">
          <div class="card"><h3 data-eng-zh="Snapshot SPIB 資料" data-eng-en="Snapshot SPIB data">Snapshot SPIB 資料</h3><div id="truthProtocol"></div></div>
          <div class="card"><h3 data-eng-zh="Snapshot scalar registers" data-eng-en="Snapshot scalar registers">Snapshot scalar registers</h3><div id="truthScaling"></div></div>
        </div>
        <div class="grid two">
          <div class="card"><h3 data-eng-zh="快照內已驗證" data-eng-en="Verified within snapshot">快照內已驗證</h3><div id="truthVerified" class="truth-list"></div></div>
          <div class="card"><h3 data-eng-zh="快照內待實證／未宣告" data-eng-en="Pending / not claimed in snapshot">快照內待實證／未宣告</h3><div id="truthPending" class="truth-list"></div></div>
        </div>
        <div class="card"><h3 data-eng-zh="來源與使用規則" data-eng-en="Source and consumer rules">來源與使用規則</h3><div id="truthPolicy"></div></div>
      </section>`);
    if (!panel) return;

    const idx = snapshot.index;
    const federation = snapshot.federation;
    D.$('truthBaseline').innerHTML = `
      <div><span>Snapshot source</span><strong>${esc(idx.baseline.repository)}</strong></div>
      <div><span>Snapshot branch</span><strong>${esc(idx.baseline.branch)}</strong></div>
      <div><span>Snapshot SHA</span><code>${esc(idx.baseline.commit)}</code></div>
      <div><span>Freshness</span><strong class="truth-pending">${esc(idx.baseline.freshness || federation.current_workbench_snapshot?.freshness || 'SNAPSHOT')}</strong></div>
      <div><span>Control Plane</span><strong>${esc(federation.sources?.control_plane?.repository)}</strong></div>
      <div><span>Execution Plane</span><strong>${esc(federation.sources?.execution_plane?.repository)}</strong></div>`;

    const scope = snapshot.verification.scope || [];
    const counts = scope.reduce((acc, row) => {
      const k = String(row.status || 'UNKNOWN').toUpperCase();
      acc[k] = (acc[k] || 0) + 1;
      return acc;
    }, {});
    D.$('truthSummary').innerHTML = Object.entries(counts).map(([k,v]) =>
      `<div class="card truth-stat ${statusClass(k)}"><strong>${v}</strong><span>${esc(k)}</span></div>`).join('');

    const p = snapshot.protocol;
    D.$('truthProtocol').innerHTML = `
      <dl class="truth-dl">
        <dt>Transport</dt><dd>${esc(p.transport?.name || 'SPIB NORMAL')}</dd>
        <dt>Request</dt><dd>${esc(p.transport?.request_bits)}-bit · [31:16] address · [15:0] data</dd>
        <dt>Response</dt><dd>${esc(p.transport?.response_timing)}</dd>
        <dt>NULL frame</dt><dd><code>${esc(p.null_frame?.value || '0xFFFF0000')}</code></dd>
        <dt>Queue depth</dt><dd>${esc(snapshot.commands?.queue_depth)}</dd>
      </dl>`;

    const verifiedScaling = (snapshot.scaling.scalings || [])
      .filter(x => String(x.trust || 'verified_source') === 'verified_source');
    D.$('truthScaling').innerHTML = verifiedScaling.length
      ? verifiedScaling.map(x => `<div class="truth-row"><code>${esc(x.id)}</code><span>${esc((x.wire_addresses || []).join(' / '))} · ×${esc(x.scale)} ${esc(x.unit || '')}</span></div>`).join('')
      : `<p class="note">No source-verified scaling exists in this snapshot.</p>`;

    const verified = scope.filter(x => ['VERIFIED','GOVERNANCE_CONTRACT','SOURCE_VERIFIED'].includes(String(x.status).toUpperCase()));
    const pending = scope.filter(x => !['VERIFIED','GOVERNANCE_CONTRACT','SOURCE_VERIFIED'].includes(String(x.status).toUpperCase()));
    const renderRows = rows => rows.map(x => `<div class="truth-item ${statusClass(x.status)}"><span>${esc(x.status)}</span><b>${esc(x.item)}</b>${x.evidence ? `<small>${esc(x.evidence)}</small>` : ''}</div>`).join('');
    D.$('truthVerified').innerHTML = renderRows(verified);
    D.$('truthPending').innerHTML = renderRows(pending);

    D.$('truthPolicy').innerHTML = `
      <p><b>Workbench role:</b> <code>${esc(federation.workbench_role)}</code></p>
      <p><b>authoritative_engineering_truth:</b> <code>${esc(federation.authoritative_engineering_truth)}</code></p>
      <p><b>snapshot currentness:</b> <code>${esc(federation.snapshot_policy?.currentness)}</code></p>
      <p><b>current live identity:</b> re-query owning repositories</p>
      <p><b>unknown_action:</b> <code>${esc(idx.consumer_policy.unknown_action)}</code></p>
      <p class="note">${esc(federation.derived_view_rule)}</p>`;
  }

  function renderProductionState(snapshot) {
    const s = snapshot.state;
    const panel = D.$('state');
    if (!panel) return;

    const modelBadge = panel.querySelector('.panel-head .badge');
    if (modelBadge) {
      modelBadge.classList.remove('danger');
      modelBadge.textContent = 'SNAPSHOT VOCABULARY · PARTIAL TRANSITIONS';
    }

    const authority = D.$('authorityCards');
    if (authority) {
      const ownerRows = [
        ['Snapshot SystemState owner', s.owner || 'CPU1', 'verified_source'],
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
          <p><b>snapshot owner:</b> ${esc(s.owner)}</p>
          <p><b>trust within snapshot:</b> ${esc(s.trust)}</p>
          <p class="note">Current live behavior must be checked against the Execution Plane exact SHA.</p>`;
      }));
    }

    const sim = D.$('simState');
    if (sim) sim.textContent = 'DISABLED · PARTIAL SNAPSHOT';
    const transitions = D.$('transitionList');
    if (transitions) {
      transitions.innerHTML = `
        <div class="truth-boundary truth-pending"><strong>FAIL CLOSED</strong><span data-eng-zh="完整 transition/guard 未包含於此 pinned snapshot，因此禁止把參考 simulator 當 current production state machine。" data-eng-en="The complete transition/guard table is not present in this pinned snapshot, so the reference simulator cannot represent the current production state machine.">完整 transition/guard 未包含於此 pinned snapshot，因此禁止把參考 simulator 當 current production state machine。</span></div>
        ${(s.verified_transitions || []).map(t => `<div class="transition"><b>${esc(t.from)} → ${esc(t.to)}</b><span>${esc(t.guard)}</span><small>${esc(t.evidence)}</small></div>`).join('')}`;
    }
    const history = D.$('transitionHistory');
    if (history) history.innerHTML = `<p class="note">${esc((s.pending || []).join(' · '))}</p>`;
  }

  function applyBoundaries(snapshot) {
    const analogPending = (snapshot.verification.scope || []).some(x =>
      x.item === 'ADC measurement scaling/calibration' && String(x.status).toUpperCase() === 'PENDING');
    addEvidenceBanner('measurement', analogPending ? 'PENDING' : 'SNAPSHOT',
      '此計算器是工程分析工具；ASR5K current ADC scaling/calibration 必須回到 owner source / evidence 查證。',
      'This calculator is an engineering analysis tool. Current ASR5K ADC scaling/calibration must be verified from the owning source/evidence.');

    addEvidenceBanner('control', snapshot.control.status === 'pending_verification' ? 'PENDING' : 'SNAPSHOT',
      'Plant/controller/SFRA 是分析視圖，不是 current product contract 或 qualification authority。',
      'Plant/controller/SFRA is an analysis view, not current product-contract or qualification authority.');

    addEvidenceBanner('remote', 'SNAPSHOT',
      'SPIB 資料來自 pinned snapshot；控制 transport 仍是 MOCK，瀏覽器沒有 safety authority。',
      'SPIB data comes from a pinned snapshot; control transport remains MOCK and the browser has no safety authority.');
  }

  async function initializeTruth() {
    try {
      const loaded = {};
      await Promise.all(Object.entries(RESOURCE_PATHS).map(async ([key,path]) => { loaded[key] = await loadJson(path); }));
      if (loaded.index.baseline.commit !== loaded.state.baseline ||
          loaded.index.baseline.commit !== loaded.verification.baseline) {
        throw new Error('derived snapshot baseline mismatch');
      }
      if (loaded.federation.authoritative_engineering_truth !== false || loaded.index.authoritative_engineering_truth !== false) {
        throw new Error('Workbench federation boundary invalid: view plane must not claim engineering authority');
      }
      D.truth = loaded;
      D.snapshot = loaded;
      renderTruthPanel(loaded);
      renderProductionState(loaded);
      applyBoundaries(loaded);
      D.refreshLanguage();
      document.dispatchEvent(new CustomEvent('dpwe:truth-ready', {detail: loaded}));
    } catch (error) {
      console.error('Engineering snapshot layer unavailable', error);
      ['measurement','control','state','remote'].forEach(id =>
        addEvidenceBanner(id, 'PENDING', '工程快照載入失敗；依 fail-closed 規則，不宣告 current production truth 或 qualification。',
          'Engineering snapshot failed to load. Fail-closed policy: no current production truth or qualification is claimed.'));
    }
  }

  initializeTruth();
})();
