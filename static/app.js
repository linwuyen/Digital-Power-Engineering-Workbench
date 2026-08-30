const $ = (id) => document.getElementById(id);

function toast(message, error=false) {
  const el = $('toast'); el.textContent = message; el.className = `toast show${error ? ' error' : ''}`;
  clearTimeout(window.__toast); window.__toast = setTimeout(() => el.className = 'toast', 2600);
}

async function api(path, options={}) {
  const response = await fetch(path, {headers:{'Content-Type':'application/json'}, ...options});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
  return data;
}

for (const btn of document.querySelectorAll('.nav')) {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.nav').forEach(x => x.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(x => x.classList.remove('active'));
    btn.classList.add('active'); $(btn.dataset.panel).classList.add('active');
  });
}

function formObject(form) { return Object.fromEntries(new FormData(form).entries()); }
function fmt(v, digits=4) { return Number.isFinite(Number(v)) ? Number(v).toFixed(digits) : '—'; }

$('measurementForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  try {
    const p = formObject(e.target); p.adc_bits = Number(p.adc_bits);
    for (const k of Object.keys(p)) if (k !== 'adc_bits') p[k] = Number(p[k]);
    const r = await api('/api/datasheet/signal-chain', {method:'POST', body:JSON.stringify(p)});
    $('mPhysical').textContent = fmt(r.physical_value, 3); $('mSensor').textContent = `${fmt(r.sensor_output_v, 4)} V`; $('mOpamp').textContent = `${fmt(r.opamp_output_v, 4)} V`; $('mAdcV').textContent = `${fmt(r.adc_input_v, 4)} V`; $('mCode').textContent = String(r.adc_code); $('mRecovered').textContent = fmt(r.recovered_physical_value, 5); $('mError').textContent = fmt(r.quantization_error_physical, 6); $('mLsb').textContent = `${fmt(r.adc_lsb_v * 1000, 4)} mV`; $('mClipped').textContent = r.clipped ? 'YES' : 'NO'; $('mClipped').style.color = r.clipped ? '#ff6b78' : '#55d6be';
  } catch (err) { toast(err.message, true); }
});

function drawBode(r) {
  const canvas = $('bodeCanvas'); const ctx = canvas.getContext('2d'); const W=canvas.width,H=canvas.height;
  ctx.clearRect(0,0,W,H); ctx.fillStyle='#0a1016'; ctx.fillRect(0,0,W,H);
  const pad={l:64,r:24,t:24,b:42}; const xs=r.frequency_hz.map(Math.log10); const all=[...r.plant_mag_db,...r.loop_mag_db]; let ymin=Math.floor(Math.min(...all)/20)*20-10; let ymax=Math.ceil(Math.max(...all)/20)*20+10;
  const x=(v)=>pad.l+(v-xs[0])/(xs[xs.length-1]-xs[0])*(W-pad.l-pad.r); const y=(v)=>pad.t+(ymax-v)/(ymax-ymin)*(H-pad.t-pad.b);
  ctx.strokeStyle='#20303e'; ctx.lineWidth=1; ctx.font='18px sans-serif'; ctx.fillStyle='#71879b';
  for(let db=Math.ceil(ymin/20)*20;db<=ymax;db+=20){ctx.beginPath();ctx.moveTo(pad.l,y(db));ctx.lineTo(W-pad.r,y(db));ctx.stroke();ctx.fillText(`${db} dB`,6,y(db)+6)}
  const decades=[]; for(let d=Math.ceil(xs[0]);d<=Math.floor(xs[xs.length-1]);d++) decades.push(d);
  for(const d of decades){ctx.beginPath();ctx.moveTo(x(d),pad.t);ctx.lineTo(x(d),H-pad.b);ctx.stroke();ctx.fillText(`${Math.pow(10,d).toPrecision(1)} Hz`,x(d)-28,H-12)}
  const plot=(arr,color)=>{ctx.strokeStyle=color;ctx.lineWidth=3;ctx.beginPath();arr.forEach((v,i)=>{const X=x(xs[i]),Y=y(v);i?ctx.lineTo(X,Y):ctx.moveTo(X,Y)});ctx.stroke()};
  plot(r.plant_mag_db,'#8ea1b5'); plot(r.loop_mag_db,'#55d6be'); ctx.strokeStyle='#f8c75a'; ctx.setLineDash([8,8]); ctx.beginPath();ctx.moveTo(pad.l,y(0));ctx.lineTo(W-pad.r,y(0));ctx.stroke();ctx.setLineDash([]);
}

$('controlForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  try {
    const f=formObject(e.target); const p={vin_v:+f.vin_v,inductance_h:+f.inductance_uh*1e-6,capacitance_f:+f.capacitance_uf*1e-6,load_ohm:+f.load_ohm,switching_hz:+f.switching_khz*1000,sampling_hz:+f.sampling_khz*1000,kp:+f.kp,ki:+f.ki,delay_samples:+f.delay_samples};
    const r=await api('/api/control/buck-pi',{method:'POST',body:JSON.stringify(p)});
    $('cRes').textContent=`${fmt(r.resonance_hz,1)} Hz`; $('cCross').textContent=r.crossover_hz?`${fmt(r.crossover_hz,1)} Hz`:'not found'; $('cPm').textContent=r.phase_margin_deg?`${fmt(r.phase_margin_deg,1)}°`:'—'; $('cCoeff').textContent=`${fmt(r.pi_tustin.b0,6)} / ${fmt(r.pi_tustin.b1,6)}`; drawBode(r); $('controlWarnings').innerHTML=(r.warnings.length?r.warnings:['Model boundary: '+r.model_boundary]).map(x=>`<div>${x}</div>`).join('');
  } catch(err){toast(err.message,true)}
});

let stateMachine=null;
async function loadStateMachine(){
  try{
    stateMachine=await api('/api/state-machine'); $('authorityCards').innerHTML=Object.entries(stateMachine.authority_boundaries).map(([k,v])=>`<div><b>${k.replaceAll('_',' ')}</b><span>${v}</span></div>`).join(''); $('stateGraph').innerHTML=stateMachine.states.map((s,i)=>`${i?'<span class="state-arrow">→</span>':''}<button class="state-node" data-state="${s.id}"><b>${s.id}</b><small>${s.pwm}</small></button>`).join(''); document.querySelectorAll('.state-node').forEach(btn=>btn.addEventListener('click',()=>selectState(btn.dataset.state))); selectState('RUN');
  }catch(err){toast(err.message,true)}
}
function selectState(id){
  document.querySelectorAll('.state-node').forEach(x=>x.classList.toggle('selected',x.dataset.state===id)); const s=stateMachine.states.find(x=>x.id===id); const outgoing=stateMachine.transitions.filter(x=>x.from===id); $('stateDetail').innerHTML=`<b>${s.id}</b><p>PWM: ${s.pwm}</p><strong>Control authority</strong><ul>${s.authority.map(x=>`<li>${x}</li>`).join('')}</ul><strong>Entry</strong><ul>${s.entry.map(x=>`<li>${x}</li>`).join('')}</ul><strong>Exit</strong><ul>${s.exit.map(x=>`<li>${x}</li>`).join('')}</ul>`; $('transitionList').innerHTML=outgoing.map(x=>`<div><b>${x.event}</b> → ${x.to}</div>`).join('')||'<div>No outgoing transitions.</div>';
}

async function remoteCommand(action,value){try{const r=await api('/api/remote/command',{method:'POST',body:JSON.stringify(value===undefined?{action}:{action,value})});renderTelemetry(r);toast(`${action} accepted`)}catch(err){toast(err.message,true)}}
function renderTelemetry(r){$('rVout').textContent=`${fmt(r.vout_v,3)} V`;$('rIout').textContent=`${fmt(r.iout_a,3)} A`;$('rPower').textContent=`${fmt(r.pout_w,1)} W`;$('rMode').textContent=r.mode;$('rFault').textContent=r.fault;$('rTransport').textContent=r.transport;$('rState').textContent=r.state}
$('setVoltage').onclick=()=>remoteCommand('set_voltage',+$('rVoltage').value); $('setCurrent').onclick=()=>remoteCommand('set_current',+$('rCurrent').value); $('outputOn').onclick=()=>remoteCommand('output_on'); $('outputOff').onclick=()=>remoteCommand('output_off');
async function pollTelemetry(){try{renderTelemetry(await api('/api/remote/telemetry'))}catch{}}

(async function init(){ try{await api('/api/health');$('healthText').textContent='backend online'}catch{$('healthText').textContent='backend offline'} loadStateMachine(); document.querySelector('#measurementForm button').click(); document.querySelector('#controlForm button').click(); pollTelemetry(); setInterval(pollTelemetry,1500); })();
