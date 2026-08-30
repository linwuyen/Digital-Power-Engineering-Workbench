const $ = (id) => document.getElementById(id);
let backendAvailable = false;

function toast(message, error=false) {
  const el = $('toast');
  el.textContent = message;
  el.className = `toast show${error ? ' error' : ''}`;
  clearTimeout(window.__toast);
  window.__toast = setTimeout(() => el.className = 'toast', 2600);
}

function assertFinite(name, value) {
  if (!Number.isFinite(Number(value))) throw new Error(`${name} must be finite`);
  return Number(value);
}

function assertPositive(name, value) {
  value = assertFinite(name, value);
  if (value <= 0) throw new Error(`${name} must be > 0`);
  return value;
}

const STATE_MACHINE = {
  states: [
    {id:'BOOT', pwm:'OFF', authority:['hardware reset'], entry:['POR / reset'], exit:['clock + memory init complete']},
    {id:'INIT', pwm:'OFF', authority:['firmware init'], entry:['BOOT complete'], exit:['self-check pass']},
    {id:'STANDBY', pwm:'OFF', authority:['host setpoints','protection'], entry:['self-check pass','STOP complete'], exit:['OUTPUT_ON accepted']},
    {id:'PRECHARGE', pwm:'OFF', authority:['sequencer','protection'], entry:['OUTPUT_ON','no latched fault'], exit:['bus ready']},
    {id:'SOFT_START', pwm:'CONTROLLED', authority:['slew generator','control loop','protection'], entry:['bus ready'], exit:['reference reached']},
    {id:'RUN', pwm:'ON', authority:['control loop','host bounded setpoints','hardware protection'], entry:['soft-start complete'], exit:['OUTPUT_OFF','fault']},
    {id:'STOP', pwm:'RAMP/OFF', authority:['sequencer','protection'], entry:['OUTPUT_OFF'], exit:['energy discharge complete']},
    {id:'FAULT', pwm:'TRIPPED', authority:['hardware trip','protection latch'], entry:['OVP/OCP/OTP/interlock'], exit:['fault clear policy satisfied']}
  ],
  transitions: [
    {from:'BOOT',to:'INIT',event:'BOOT_DONE'},
    {from:'INIT',to:'STANDBY',event:'SELF_CHECK_PASS'},
    {from:'INIT',to:'FAULT',event:'SELF_CHECK_FAIL'},
    {from:'STANDBY',to:'PRECHARGE',event:'OUTPUT_ON'},
    {from:'PRECHARGE',to:'SOFT_START',event:'BUS_READY'},
    {from:'SOFT_START',to:'RUN',event:'REFERENCE_REACHED'},
    {from:'RUN',to:'STOP',event:'OUTPUT_OFF'},
    {from:'STOP',to:'STANDBY',event:'DISCHARGE_DONE'},
    {from:'PRECHARGE',to:'FAULT',event:'PROTECTION'},
    {from:'SOFT_START',to:'FAULT',event:'PROTECTION'},
    {from:'RUN',to:'FAULT',event:'PROTECTION'},
    {from:'FAULT',to:'STANDBY',event:'CLEAR_FAULT'}
  ],
  authority_boundaries: {
    web_ui:'Operator intent only; never safety authority.',
    host:'May request bounded setpoints and state transitions.',
    firmware:'Validates commands, owns sequencing and state policy.',
    control_loop:'Owns deterministic regulation execution.',
    hardware_protection:'Highest shutdown authority; must not depend on web/network availability.'
  }
};

function localSignalChain(p) {
  const physical = assertFinite('physical_value', p.physical_value);
  const sensorGain = assertFinite('sensor_gain_v_per_unit', p.sensor_gain_v_per_unit);
  const sensorOffset = assertFinite('sensor_offset_v', p.sensor_offset_v);
  const opampGain = assertFinite('opamp_gain', p.opamp_gain);
  const opampOffset = assertFinite('opamp_offset_v', p.opamp_offset_v);
  const divider = assertFinite('divider_ratio', p.divider_ratio);
  const vref = assertPositive('adc_vref_v', p.adc_vref_v);
  const bits = Number(p.adc_bits);
  if (sensorGain === 0) throw new Error('sensor_gain_v_per_unit must be non-zero');
  if (opampGain === 0) throw new Error('opamp_gain must be non-zero');
  if (!(divider > 0 && divider <= 1)) throw new Error('divider_ratio must be in (0, 1]');
  if (!Number.isInteger(bits) || bits < 1 || bits > 32) throw new Error('adc_bits must be an integer in [1, 32]');
  const maxCode = 2 ** bits - 1;
  const sensorOutput = physical * sensorGain + sensorOffset;
  const opampOutput = sensorOutput * opampGain + opampOffset;
  const adcInput = opampOutput * divider;
  const lsb = vref / maxCode;
  const idealCode = adcInput / vref * maxCode;
  const clippedCode = Math.min(Math.max(idealCode, 0), maxCode);
  const code = Math.round(clippedCode);
  const clipped = idealCode < 0 || idealCode > maxCode;
  const adcRecovered = code / maxCode * vref;
  const opampRecovered = adcRecovered / divider;
  const sensorRecovered = (opampRecovered - opampOffset) / opampGain;
  const recovered = (sensorRecovered - sensorOffset) / sensorGain;
  return {
    physical_value: physical,
    sensor_output_v: sensorOutput,
    opamp_output_v: opampOutput,
    adc_input_v: adcInput,
    adc_code_ideal: idealCode,
    adc_code: code,
    adc_lsb_v: lsb,
    clipped,
    recovered_physical_value: recovered,
    quantization_error_physical: recovered - physical
  };
}

const C = {
  add:(a,b)=>({re:a.re+b.re, im:a.im+b.im}),
  mul:(a,b)=>({re:a.re*b.re-a.im*b.im, im:a.re*b.im+a.im*b.re}),
  div:(a,b)=>{const d=b.re*b.re+b.im*b.im; return {re:(a.re*b.re+a.im*b.im)/d, im:(a.im*b.re-a.re*b.im)/d};},
  abs:(a)=>Math.hypot(a.re,a.im),
  phase:(a)=>Math.atan2(a.im,a.re)*180/Math.PI,
  expj:(theta)=>({re:Math.cos(theta),im:Math.sin(theta)})
};

function logspace(start, stop, count) {
  const a = Math.log10(start), b = Math.log10(stop);
  return Array.from({length:count}, (_,i)=>10 ** (a + (b-a)*i/(count-1)));
}

function unwrapDegrees(values) {
  if (!values.length) return [];
  const out = [values[0]];
  for (let i=1;i<values.length;i++) {
    let v = values[i];
    const prev = out[i-1];
    while (v - prev > 180) v -= 360;
    while (v - prev < -180) v += 360;
    out.push(v);
  }
  return out;
}

function localBuckPi(p, points=220) {
  const vin = assertPositive('vin_v', p.vin_v);
  const L = assertPositive('inductance_h', p.inductance_h);
  const cap = assertPositive('capacitance_f', p.capacitance_f);
  const load = assertPositive('load_ohm', p.load_ohm);
  const fsw = assertPositive('switching_hz', p.switching_hz);
  const fs = assertPositive('sampling_hz', p.sampling_hz);
  const kp = assertFinite('kp', p.kp), ki = assertFinite('ki', p.ki), delaySamples = assertFinite('delay_samples', p.delay_samples);
  if (kp < 0 || ki < 0 || delaySamples < 0) throw new Error('kp, ki, and delay_samples must be >= 0');
  const fMin = Math.max(1, fsw/100000);
  const fMax = Math.min(fs*0.45, fsw*0.5);
  if (fMax <= fMin) throw new Error('frequency range is invalid; check sampling/switching frequencies');
  const freqs = logspace(fMin, fMax, points);
  const plantMag=[], plantPhase=[], loopMag=[], loopPhaseRaw=[];
  const delayS = delaySamples/fs;
  for (const f of freqs) {
    const w = 2*Math.PI*f;
    const denominator = {re:1-L*cap*w*w, im:w*L/load};
    const plant = C.div({re:vin,im:0}, denominator);
    const controller = {re:kp, im:-ki/w};
    const delay = C.expj(-w*delayS);
    const loop = C.mul(C.mul(plant, controller), delay);
    plantMag.push(20*Math.log10(Math.max(C.abs(plant),1e-30)));
    plantPhase.push(C.phase(plant));
    loopMag.push(20*Math.log10(Math.max(C.abs(loop),1e-30)));
    loopPhaseRaw.push(C.phase(loop));
  }
  const loopPhase = unwrapDegrees(loopPhaseRaw);
  let crossover=null, phaseMargin=null;
  for (let i=1;i<freqs.length;i++) {
    const y0=loopMag[i-1], y1=loopMag[i];
    if ((y0>=0 && y1<=0) || (y0<=0 && y1>=0)) {
      const alpha = y1===y0 ? 0 : (0-y0)/(y1-y0);
      const logf = Math.log10(freqs[i-1]) + alpha*(Math.log10(freqs[i])-Math.log10(freqs[i-1]));
      crossover = 10 ** logf;
      const phase = loopPhase[i-1] + alpha*(loopPhase[i]-loopPhase[i-1]);
      phaseMargin = 180 + phase;
      break;
    }
  }
  const ts=1/fs;
  const pi={b0:kp+ki*ts/2, b1:-kp+ki*ts/2, sample_time_s:ts};
  const resonance=1/(2*Math.PI*Math.sqrt(L*cap));
  const warnings=[];
  if (crossover===null) warnings.push('No 0 dB loop crossover found in the evaluated frequency range.');
  else {
    if (crossover > fs/10) warnings.push('Crossover exceeds fs/10; digital delay/model fidelity needs verification.');
    if (crossover > fsw/10) warnings.push('Crossover exceeds fsw/10; averaged plant assumptions may be weak.');
  }
  if (phaseMargin!==null && phaseMargin<45) warnings.push('Phase margin is below 45 degrees.');
  if (phaseMargin!==null && phaseMargin<=0) warnings.push('Computed phase margin is non-positive; do not apply these gains to hardware without loop re-design and measured verification.');
  return {
    resonance_hz:resonance, crossover_hz:crossover, phase_margin_deg:phaseMargin,
    pi_tustin:pi, frequency_hz:freqs, plant_mag_db:plantMag, plant_phase_deg:plantPhase,
    loop_mag_db:loopMag, loop_phase_deg:loopPhase, warnings,
    model_boundary:'Ideal CCM buck averaged plant with PI and pure computation/PWM delay. Validate against SFRA or measured loop gain before hardware authority changes.'
  };
}

const localRemote = {
  state:{voltage_set_v:0,current_limit_a:1,output_enabled:false,state:'STANDBY',mode:'CV',fault:'NONE',interlock_ok:true},
  bounded(name,value,lower,upper){value=assertFinite(name,value);if(value<lower||value>upper)throw new Error(`${name} must be in [${lower}, ${upper}]`);return value;},
  telemetry(){const s=this.state, enabled=s.output_enabled;const vout=enabled?s.voltage_set_v:0;const iout=enabled?Math.min(s.current_limit_a*0.35,vout/100):0;return {...s,vout_v:vout,iout_a:iout,pout_w:vout*iout,transport:'BROWSER MOCK'};},
  command(action,value){const s=this.state;
    if(action==='set_voltage')s.voltage_set_v=this.bounded('voltage',value,0,700);
    else if(action==='set_current')s.current_limit_a=this.bounded('current',value,0,15);
    else if(action==='output_on'){if(s.fault!=='NONE')throw new Error('output_on blocked: fault is latched');if(!s.interlock_ok)throw new Error('output_on blocked: interlock is open');s.output_enabled=true;s.state='RUN';}
    else if(action==='output_off'){s.output_enabled=false;s.state='STANDBY';}
    else if(action==='clear_fault'){if(s.output_enabled)throw new Error('clear_fault blocked while output is enabled');s.fault='NONE';s.state='STANDBY';}
    else if(action==='inject_ocp'){s.fault='OCP';s.output_enabled=false;s.state='FAULT';}
    else if(action==='set_interlock'){s.interlock_ok=Boolean(value);if(!s.interlock_ok&&s.output_enabled){s.output_enabled=false;s.state='FAULT';s.fault='INTERLOCK';}}
    else throw new Error(`unsupported action: ${action}`);
    return this.telemetry();
  }
};

async function backendApi(path, options={}) {
  const response = await fetch(path, {headers:{'Content-Type':'application/json'}, cache:'no-store', ...options});
  const contentType = response.headers.get('content-type') || '';
  const data = contentType.includes('application/json') ? await response.json() : {};
  if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
  return data;
}

async function modelCall(path, payload) {
  if (backendAvailable) return backendApi(path,{method:'POST',body:JSON.stringify(payload)});
  if (path==='/api/datasheet/signal-chain') return localSignalChain(payload);
  if (path==='/api/control/buck-pi') return localBuckPi(payload);
  if (path==='/api/remote/command') return localRemote.command(payload.action,payload.value);
  throw new Error(`unsupported local route: ${path}`);
}

for (const btn of document.querySelectorAll('.nav')) {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.nav').forEach(x => x.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(x => x.classList.remove('active'));
    btn.classList.add('active');
    $(btn.dataset.panel).classList.add('active');
    if (btn.dataset.panel==='control') setTimeout(()=>lastControlResult&&drawBode(lastControlResult),0);
  });
}

function formObject(form) { return Object.fromEntries(new FormData(form).entries()); }
function fmt(v, digits=4) { return Number.isFinite(Number(v)) ? Number(v).toFixed(digits) : '—'; }

$('measurementForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  try {
    const p = formObject(e.target); p.adc_bits = Number(p.adc_bits);
    for (const k of Object.keys(p)) if (k !== 'adc_bits') p[k] = Number(p[k]);
    const r = await modelCall('/api/datasheet/signal-chain', p);
    $('mPhysical').textContent = fmt(r.physical_value,3);
    $('mSensor').textContent = `${fmt(r.sensor_output_v,4)} V`;
    $('mOpamp').textContent = `${fmt(r.opamp_output_v,4)} V`;
    $('mAdcV').textContent = `${fmt(r.adc_input_v,4)} V`;
    $('mCode').textContent = String(r.adc_code);
    $('mRecovered').textContent = fmt(r.recovered_physical_value,5);
    $('mError').textContent = fmt(r.quantization_error_physical,6);
    $('mLsb').textContent = `${fmt(r.adc_lsb_v*1000,4)} mV`;
    $('mClipped').textContent = r.clipped ? 'YES' : 'NO';
    $('mClipped').className = r.clipped ? 'metric-danger' : 'metric-ok';
  } catch (err) { toast(err.message,true); }
});

let lastControlResult=null;
function drawAxes(ctx,box,xmin,xmax,ymin,ymax,yStep,yLabel) {
  const x=v=>box.l+(v-xmin)/(xmax-xmin)*(box.r-box.l);
  const y=v=>box.t+(ymax-v)/(ymax-ymin)*(box.b-box.t);
  ctx.strokeStyle='#20303e';ctx.lineWidth=1;ctx.fillStyle='#71879b';ctx.font='16px sans-serif';
  for(let val=Math.ceil(ymin/yStep)*yStep;val<=ymax;val+=yStep){ctx.beginPath();ctx.moveTo(box.l,y(val));ctx.lineTo(box.r,y(val));ctx.stroke();ctx.fillText(`${val}${yLabel}`,8,y(val)+5)}
  for(let d=Math.ceil(xmin);d<=Math.floor(xmax);d++){ctx.beginPath();ctx.moveTo(x(d),box.t);ctx.lineTo(x(d),box.b);ctx.stroke();ctx.fillText(`${(10**d).toPrecision(1)} Hz`,x(d)-28,box.b+24)}
  return {x,y};
}

function drawBode(r) {
  const canvas=$('bodeCanvas'),ctx=canvas.getContext('2d'),W=canvas.width,H=canvas.height;
  ctx.clearRect(0,0,W,H);ctx.fillStyle='#0a1016';ctx.fillRect(0,0,W,H);
  const xs=r.frequency_hz.map(Math.log10), allMag=[...r.plant_mag_db,...r.loop_mag_db];
  let magMin=Math.floor(Math.min(...allMag)/20)*20-10, magMax=Math.ceil(Math.max(...allMag)/20)*20+10;
  const phaseMin=Math.min(-360,Math.floor(Math.min(...r.loop_phase_deg)/45)*45-15), phaseMax=15;
  const top={l:72,r:W-28,t:24,b:Math.floor(H*0.54)};
  const bottom={l:72,r:W-28,t:Math.floor(H*0.61),b:H-48};
  const mag=drawAxes(ctx,top,xs[0],xs[xs.length-1],magMin,magMax,20,' dB');
  const phase=drawAxes(ctx,bottom,xs[0],xs[xs.length-1],phaseMin,phaseMax,45,'°');
  const plot=(arr,xy,stroke,width=3,dash=[])=>{ctx.strokeStyle=stroke;ctx.lineWidth=width;ctx.setLineDash(dash);ctx.beginPath();arr.forEach((v,i)=>{const X=xy.x(xs[i]),Y=xy.y(v);i?ctx.lineTo(X,Y):ctx.moveTo(X,Y)});ctx.stroke();ctx.setLineDash([]);};
  plot(r.plant_mag_db,mag,'#8ea1b5');plot(r.loop_mag_db,mag,'#55d6be');plot(r.loop_phase_deg,phase,'#f8c75a',2);
  plot([0,0],{x:v=>v===0?top.l:top.r,y:()=>mag.y(0)},'#52687b',1,[7,7]);
  plot([-180,-180],{x:v=>v===0?bottom.l:bottom.r,y:()=>phase.y(-180)},'#52687b',1,[7,7]);
  ctx.fillStyle='#9fb2c4';ctx.font='bold 16px sans-serif';ctx.fillText('MAGNITUDE',top.l,top.t+16);ctx.fillText('PHASE',bottom.l,bottom.t+16);
}

$('controlForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  try {
    const f=formObject(e.target);
    const p={vin_v:+f.vin_v,inductance_h:+f.inductance_uh*1e-6,capacitance_f:+f.capacitance_uf*1e-6,load_ohm:+f.load_ohm,switching_hz:+f.switching_khz*1000,sampling_hz:+f.sampling_khz*1000,kp:+f.kp,ki:+f.ki,delay_samples:+f.delay_samples};
    const r=await modelCall('/api/control/buck-pi',p);lastControlResult=r;
    $('cRes').textContent=`${fmt(r.resonance_hz,1)} Hz`;
    $('cCross').textContent=r.crossover_hz?`${fmt(r.crossover_hz,1)} Hz`:'not found';
    $('cPm').textContent=r.phase_margin_deg!==null?`${fmt(r.phase_margin_deg,1)}°`:'—';
    $('cCoeff').textContent=`${fmt(r.pi_tustin.b0,6)} / ${fmt(r.pi_tustin.b1,6)}`;
    drawBode(r);
    $('controlWarnings').innerHTML=(r.warnings.length?r.warnings:['Model boundary: '+r.model_boundary]).map(x=>`<div>${escapeHtml(x)}</div>`).join('');
  } catch(err){toast(err.message,true);}
});

function escapeHtml(value){return String(value).replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));}
let stateMachine=STATE_MACHINE,simulatorState='STANDBY',history=[];
async function loadStateMachine(){
  if(backendAvailable){try{stateMachine=await backendApi('/api/state-machine');}catch{stateMachine=STATE_MACHINE;}}
  $('authorityCards').innerHTML=Object.entries(stateMachine.authority_boundaries).map(([k,v])=>`<div><b>${escapeHtml(k.replaceAll('_',' '))}</b><span>${escapeHtml(v)}</span></div>`).join('');
  $('stateGraph').innerHTML=stateMachine.states.map((s,i)=>`${i?'<span class="state-arrow">→</span>':''}<button class="state-node" data-state="${s.id}"><b>${s.id}</b><small>${s.pwm}</small></button>`).join('');
  document.querySelectorAll('.state-node').forEach(btn=>btn.addEventListener('click',()=>selectState(btn.dataset.state)));
  selectState('RUN');renderSimulator();
}
function selectState(id){
  document.querySelectorAll('.state-node').forEach(x=>x.classList.toggle('selected',x.dataset.state===id));
  const s=stateMachine.states.find(x=>x.id===id), outgoing=stateMachine.transitions.filter(x=>x.from===id);
  $('stateDetail').innerHTML=`<b>${escapeHtml(s.id)}</b><p>PWM: ${escapeHtml(s.pwm)}</p><strong>Control authority</strong><ul>${s.authority.map(x=>`<li>${escapeHtml(x)}</li>`).join('')}</ul><strong>Entry</strong><ul>${s.entry.map(x=>`<li>${escapeHtml(x)}</li>`).join('')}</ul><strong>Exit</strong><ul>${s.exit.map(x=>`<li>${escapeHtml(x)}</li>`).join('')}</ul><p class="note">Outgoing policy events: ${outgoing.map(x=>escapeHtml(x.event)).join(', ')||'none'}</p>`;
}
function renderSimulator(){
  $('simState').textContent=simulatorState;
  const outgoing=stateMachine.transitions.filter(x=>x.from===simulatorState);
  $('transitionList').innerHTML=outgoing.map((x,i)=>`<button class="transition-action" data-index="${i}"><b>${escapeHtml(x.event)}</b><span>${escapeHtml(x.from)} → ${escapeHtml(x.to)}</span></button>`).join('')||'<div>No outgoing transitions.</div>';
  document.querySelectorAll('.transition-action').forEach((btn,i)=>btn.onclick=()=>applyTransition(outgoing[i]));
  $('transitionHistory').innerHTML=history.length?history.slice(-6).reverse().map(x=>`<div><span>${escapeHtml(x.event)}</span><b>${escapeHtml(x.from)} → ${escapeHtml(x.to)}</b></div>`).join(''):'<div class="history-empty">No simulated transitions yet.</div>';
}
function applyTransition(t){history.push(t);simulatorState=t.to;selectState(t.to);renderSimulator();}

const commandEntries=[];
function logCommand(action,result,error=false){commandEntries.push({time:new Date().toLocaleTimeString(),action,result,error});$('commandLog').innerHTML=commandEntries.slice(-7).reverse().map(x=>`<div class="log-row ${x.error?'bad':''}"><span>${escapeHtml(x.time)}</span><b>${escapeHtml(x.action)}</b><em>${escapeHtml(x.result)}</em></div>`).join('');}
async function remoteCommand(action,value){
  try{
    const payload=value===undefined?{action}:{action,value};
    const r=await modelCall('/api/remote/command',payload);renderTelemetry(r);logCommand(action,'accepted');toast(`${action} accepted`);
  }catch(err){logCommand(action,err.message,true);toast(err.message,true);}
}
function renderTelemetry(r){$('rVout').textContent=`${fmt(r.vout_v,3)} V`;$('rIout').textContent=`${fmt(r.iout_a,3)} A`;$('rPower').textContent=`${fmt(r.pout_w,1)} W`;$('rMode').textContent=r.mode;$('rFault').textContent=r.fault;$('rTransport').textContent=r.transport;$('rState').textContent=r.state;$('interlockOk').checked=Boolean(r.interlock_ok);}
$('setVoltage').onclick=()=>remoteCommand('set_voltage',+$('rVoltage').value);
$('setCurrent').onclick=()=>remoteCommand('set_current',+$('rCurrent').value);
$('outputOn').onclick=()=>remoteCommand('output_on');
$('outputOff').onclick=()=>remoteCommand('output_off');
$('injectOcp').onclick=()=>backendAvailable?toast('Fault injection is intentionally browser-mock only. Stop backend mode to use it.',true):remoteCommand('inject_ocp');
$('clearFault').onclick=()=>remoteCommand('clear_fault');
$('interlockOk').onchange=()=>backendAvailable?toast('Interlock simulation is intentionally browser-mock only.',true):remoteCommand('set_interlock',$('interlockOk').checked);
async function pollTelemetry(){try{renderTelemetry(backendAvailable?await backendApi('/api/remote/telemetry'):localRemote.telemetry());}catch{}}

async function detectRuntime(){
  try{const r=await fetch('/api/health',{cache:'no-store'});if(r.ok&&(r.headers.get('content-type')||'').includes('application/json')){backendAvailable=true;}}
  catch{backendAvailable=false;}
  $('healthText').textContent=backendAvailable?'Python backend online':'standalone ready';
  $('runtimeMode').textContent=backendAvailable?'PYTHON REFERENCE':'STATIC BROWSER';
}

(async function init(){
  await detectRuntime();
  await loadStateMachine();
  $('measurementForm').requestSubmit();
  $('controlForm').requestSubmit();
  await pollTelemetry();
  if(backendAvailable)setInterval(pollTelemetry,1500);
  window.addEventListener('resize',()=>lastControlResult&&drawBode(lastControlResult));
})();
