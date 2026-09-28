(() => {
  'use strict';
  const D = window.DPWE;
  if (!D) return;

  const SNAPSHOT_URL = '../engineering_data/status/status_snapshot.json';
  const SNAPSHOT_STALE_SECONDS = 24 * 60 * 60;

  const esc = value => String(value ?? '—')
    .replaceAll('&', '&amp;').replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;').replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
  const shortSha = value => value ? String(value).slice(0, 10) : '—';
  const statusClass = value => {
    const s = String(value || '').toUpperCase();
    if (s === 'PASS' || s === 'GOLDEN' || s === 'MATCH' || s === 'LIVE') return 'status-ok';
    if (s === 'FAIL' || s === 'MISMATCH' || s === 'DIVERGED') return 'status-bad';
    if (s === 'PENDING' || s === 'NOT_RUN' || s === 'STALE') return 'status-warn';
    return 'status-unknown';
  };

  const formatAge = seconds => {
    if (seconds == null || !Number.isFinite(Number(seconds))) return '—';
    const value = Math.max(0, Math.floor(Number(seconds)));
    if (value < 60) return `${value}s`;
    if (value < 3600) return `${Math.floor(value / 60)}m`;
    if (value < 86400) return `${Math.floor(value / 3600)}h ${Math.floor((value % 3600) / 60)}m`;
    return `${Math.floor(value / 86400)}d ${Math.floor((value % 86400) / 3600)}h`;
  };

  function renderFreshnessBanner(model) {
    const banner = D.$('statusFreshnessBanner');
    if (!banner) return;
    const freshness = model.freshness || {};
    const status = freshness.status || model.mode || 'UNKNOWN';
    const generated = model.generated_at || 'unknown time';
    const age = formatAge(freshness.age_seconds);

    if (model.mode === 'LIVE') {
      banner.className = 'truth-boundary truth-ok';
      banner.innerHTML = `<strong>LIVE OWNER QUERY</strong><span>${esc(D.text(
        '目前頁面由本機後端即時查詢 owner repositories；這只代表資料來源是 LIVE，不代表所有 qualification gate 已 PASS。',
        'The local backend queried the owner repositories live. LIVE describes source freshness only; it does not mean every qualification gate passed.'
      ))}</span>`;
      return;
    }

    if (status === 'STALE') {
      banner.className = 'truth-boundary truth-pending';
      banner.innerHTML = `<strong>PUBLIC SNAPSHOT · STALE</strong><span>${esc(D.text(
        `此頁不是目前 firmware truth。公開快照產生於 ${generated}，目前約 ${age}；請以 owner repositories 的 LIVE exact-SHA evidence 為準。`,
        `This is not current firmware truth. The public snapshot was generated at ${generated} and is about ${age} old; use LIVE exact-SHA evidence from the owner repositories for current status.`
      ))}</span>`;
      return;
    }

    banner.className = 'truth-boundary truth-governance';
    banner.innerHTML = `<strong>PUBLIC SNAPSHOT · NOT LIVE</strong><span>${esc(D.text(
      `目前顯示 sanitized derived snapshot（產生於 ${generated}，約 ${age}）。它不具工程 authority，也不能取代 owner repositories。`,
      `Showing a sanitized derived snapshot generated at ${generated} (about ${age} old). It has no engineering authority and cannot replace the owner repositories.`
    ))}</span>`;
  }

  function markSnapshotAge(model) {
    if (model.mode !== 'SNAPSHOT' || !model.generated_at) return model;
    const generated = Date.parse(model.generated_at);
    if (!Number.isFinite(generated)) return model;
    const age = Math.max(0, Math.floor((Date.now() - generated) / 1000));
    model.freshness = {...(model.freshness || {}), age_seconds: age};
    if (age > SNAPSHOT_STALE_SECONDS) {
      model.freshness.status = 'STALE';
      model.blockers = [...(model.blockers || [])];
      if (!model.blockers.some(x => x.category === 'STALE_SOURCE')) {
        model.blockers.push({category:'STALE_SOURCE', source:'snapshot', status:'STALE', note:'public snapshot is older than 24 hours'});
      }
    }
    return model;
  }

  async function fetchJson(url) {
    const response = await fetch(url, {cache:'no-store'});
    if (!response.ok) throw new Error(`${url}: HTTP ${response.status}`);
    return response.json();
  }

  async function loadStatus() {
    try {
      const live = await fetchJson('/api/status/summary');
      if (live.mode !== 'LIVE') throw new Error('local status endpoint did not return LIVE mode');
      return live;
    } catch (liveError) {
      const snapshot = markSnapshotAge(await fetchJson(SNAPSHOT_URL));
      snapshot.fallback_reason = liveError.message;
      return snapshot;
    }
  }

  function renderOverview(model) {
    const baseline = model.product_baseline || {};
    const execution = model.execution_plane || {};
    const control = model.control_plane || {};
    const identity = model.identity || {};
    const freshness = model.freshness || {};
    const unknownCount = (model.qualification || []).filter(x => ['UNKNOWN','PENDING','NOT_RUN'].includes(x.status)).length;

    D.$('statusMode').textContent = freshness.status || model.mode || 'UNKNOWN';
    D.$('statusMode').className = `badge ${statusClass(freshness.status || model.mode)}`;
    D.$('statusBaseline').innerHTML = `
      <div><span>GOLDEN SHA</span><code>${esc(shortSha(baseline.golden_sha))}</code></div>
      <div><span>Release</span><strong>${esc(baseline.release_ref)}</strong></div>
      <div><span>Current firmware</span><code>${esc(shortSha(execution.sha))}</code></div>
      <div><span>Branch</span><strong>${esc(execution.branch)}</strong></div>
      <div><span>Relation</span><strong class="${statusClass(identity.relation_to_golden)}">${esc(identity.relation_to_golden)}</strong></div>
      <div><span>Agent SHA</span><code>${esc(shortSha(control.sha))}</code></div>`;

    D.$('statusEngineering').innerHTML = `
      <div><span>Execution repo</span><strong>${esc(execution.repository)}</strong></div>
      <div><span>Exact SHA</span><code>${esc(execution.sha)}</code></div>
      <div><span>Working tree</span><strong>${execution.dirty === true ? 'DIRTY' : execution.dirty === false ? 'CLEAN' : 'UNKNOWN'}</strong></div>
      <div><span>Health</span><strong>${esc(model.health)}</strong></div>
      <div><span>Blockers</span><strong>${(model.blockers || []).length}</strong></div>
      <div><span>Unknown / pending</span><strong>${unknownCount}</strong></div>`;

    D.$('statusSources').innerHTML = [control, execution].map(row => `
      <div class="source-row">
        <div><strong>${esc(row.repository)}</strong><small>${esc(row.branch)}</small></div>
        <code>${esc(row.sha)}</code><span class="${statusClass(row.status)}">${esc(row.status)}</span>
      </div>`).join('');

    D.$('statusHealth').innerHTML = `
      <div><span>Mode</span><strong class="${statusClass(freshness.status)}">${esc(freshness.status || model.mode)}</strong></div>
      <div><span>${model.mode === 'LIVE' ? 'Queried at' : 'Snapshot generated'}</span><strong>${esc(model.generated_at)}</strong></div>
      <div><span>Age</span><strong>${esc(formatAge(freshness.age_seconds))}</strong></div>
      <div><span>Authority</span><strong>${model.mode === 'LIVE' ? 'OWNER QUERY' : 'DERIVED VIEW ONLY'}</strong></div>
      <div><span>Evidence SHA match</span><strong>${identity.evidence_sha_match === true ? 'YES' : identity.evidence_sha_match === false ? 'NO / UNKNOWN' : 'UNKNOWN'}</strong></div>`;
  }

  function gateCard(row) {
    return `<button class="gate-card ${statusClass(row.status)}" type="button" data-gate="${esc(row.gate)}">
      <span>${esc(row.gate)}</span><strong>${esc(row.status)}</strong><code>${esc(shortSha(row.sha))}</code>
    </button>`;
  }

  function renderQualification(model) {
    const html = (model.qualification || []).map(gateCard).join('');
    D.$('statusQualification').innerHTML = html;
    D.$('qualificationMatrix').innerHTML = html;
    const blockers = model.blockers || [];
    const blockerHtml = blockers.length ? blockers.map(row => `
      <div class="blocker-row ${statusClass(row.status)}"><strong>${esc(row.category)}</strong><span>${esc(row.source)}</span><em>${esc(row.status)}</em><small>${esc(row.note || '')}</small></div>`).join('') : '<div class="empty-state">No derived blockers.</div>';
    D.$('statusBlockers').innerHTML = blockerHtml;
    D.$('qualificationBlockers').innerHTML = blockerHtml;
  }

  function renderEvidence(model) {
    const rows = model.qualification || [];
    D.$('evidenceRows').innerHTML = rows.map(row => `
      <div class="evidence-row"><strong>${esc(row.gate)}</strong><span class="${statusClass(row.status)}">${esc(row.status)}</span><code>${esc(row.sha)}</code><span>${esc(row.evidence_type)}</span><small>${esc(row.evidence)}</small></div>`).join('');
  }

  function renderChanges(model) {
    const execution = model.execution_plane || {};
    const baseline = model.product_baseline || {};
    const identity = model.identity || {};
    D.$('changesIdentity').innerHTML = `
      <div><span>Current</span><code>${esc(execution.sha)}</code></div>
      <div><span>GOLDEN</span><code>${esc(baseline.golden_sha)}</code></div>
      <div><span>Relation</span><strong class="${statusClass(identity.relation_to_golden)}">${esc(identity.relation_to_golden)}</strong></div>
      <div><span>Branch</span><strong>${esc(execution.branch)}</strong></div>`;
  }

  function render(model) {
    window.DPWE.status = model;
    renderFreshnessBanner(model);
    renderOverview(model);
    renderQualification(model);
    renderEvidence(model);
    renderChanges(model);
    D.refreshLanguage();
  }

  async function initialize() {
    try {
      const model = await loadStatus();
      render(model);
    } catch (error) {
      console.error('ASR5K status unavailable', error);
      D.$('statusMode').textContent = 'UNAVAILABLE';
      D.$('statusMode').className = 'badge status-bad';
      D.$('statusBlockers').innerHTML = `<div class="blocker-row status-bad"><strong>STATUS_UNAVAILABLE</strong><small>${esc(error.message)}</small></div>`;
    }
  }

  initialize();
})();
