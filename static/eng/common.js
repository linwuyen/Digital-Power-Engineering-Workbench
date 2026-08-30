(() => {
  'use strict';
  const D = window.DPWE = window.DPWE || {};
  D.$ = id => document.getElementById(id);
  D.q = (sel, root=document) => root.querySelector(sel);
  D.qa = (sel, root=document) => [...root.querySelectorAll(sel)];
  D.language = () => localStorage.getItem('dpw-language') === 'en' ? 'en' : 'zh';
  D.text = (zh,en) => D.language() === 'en' ? en : zh;
  D.fmt = (v,d=3) => Number.isFinite(Number(v)) ? Number(v).toFixed(d) : '—';
  D.setBi = (el,zh,en) => { if(!el) return; el.dataset.engZh=zh; el.dataset.engEn=en; el.textContent=D.text(zh,en); };
  D.refreshLanguage = () => D.qa('[data-eng-zh]').forEach(el => el.textContent = D.language()==='en' ? el.dataset.engEn : el.dataset.engZh);
  D.addPanel = (id,zh,en,html) => {
    const sidebar=D.q('.sidebar'), boundary=D.q('.boundary',sidebar), content=D.q('.content');
    if(!sidebar||!content||D.$(id)) return null;
    const b=document.createElement('button'); b.className='nav'; b.dataset.panel=id; D.setBi(b,zh,en); sidebar.insertBefore(b,boundary);
    content.insertAdjacentHTML('beforeend',html); const panel=D.$(id);
    b.addEventListener('click',()=>{D.qa('.nav').forEach(x=>x.classList.remove('active'));D.qa('.panel').forEach(x=>x.classList.remove('active'));b.classList.add('active');panel.classList.add('active');panel.dispatchEvent(new CustomEvent('dpwe:show'));});
    return panel;
  };
  const HK='dpw-engineering-history-v1';
  D.historyLoad=()=>{try{return JSON.parse(localStorage.getItem(HK)||'[]');}catch{return[];}};
  D.historySave=items=>localStorage.setItem(HK,JSON.stringify(items.slice(-100)));
  D.record=(type,summary,data={})=>{const a=D.historyLoad();a.push({ts:new Date().toISOString(),type,summary,data});D.historySave(a);document.dispatchEvent(new CustomEvent('dpwe:history'));};
  D.download=(name,content,mime='application/json')=>{const u=URL.createObjectURL(new Blob([content],{type:mime})),a=document.createElement('a');a.href=u;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);};
  D.drawBode=(canvas,r,measured=null)=>{if(!canvas||!r)return;const ctx=canvas.getContext('2d'),W=canvas.width,H=canvas.height;ctx.clearRect(0,0,W,H);ctx.fillStyle='#0a1016';ctx.fillRect(0,0,W,H);const box={l:70,r:W-25,t:25,b:H-55},lf=r.frequency_hz.map(Math.log10),xmin=Math.min(...lf),xmax=Math.max(...lf),extra=measured?measured.map(x=>x.magnitude_db):[],all=[...r.plant_mag_db,...r.loop_mag_db,...extra],ymin=Math.floor((Math.min(...all)-10)/20)*20,ymax=Math.ceil((Math.max(...all)+10)/20)*20,X=f=>box.l+(Math.log10(f)-xmin)/(xmax-xmin)*(box.r-box.l),Y=v=>box.t+(ymax-v)/(ymax-ymin)*(box.b-box.t);ctx.strokeStyle='#263745';ctx.fillStyle='#8295a7';ctx.font='14px sans-serif';for(let y=ymin;y<=ymax;y+=20){ctx.beginPath();ctx.moveTo(box.l,Y(y));ctx.lineTo(box.r,Y(y));ctx.stroke();ctx.fillText(`${y} dB`,8,Y(y)+4);}const line=(vals,color)=>{ctx.strokeStyle=color;ctx.lineWidth=2;ctx.beginPath();r.frequency_hz.forEach((f,i)=>i?ctx.lineTo(X(f),Y(vals[i])):ctx.moveTo(X(f),Y(vals[i])));ctx.stroke();};line(r.plant_mag_db,'#8ea1b5');line(r.loop_mag_db,'#55d6be');if(measured){ctx.strokeStyle='#f8c75a';ctx.beginPath();measured.forEach((p,i)=>i?ctx.lineTo(X(p.frequency_hz),Y(p.magnitude_db)):ctx.moveTo(X(p.frequency_hz),Y(p.magnitude_db)));ctx.stroke();}ctx.fillStyle='#8295a7';ctx.fillText(`${D.fmt(r.frequency_hz[0],0)} Hz`,box.l,box.b+28);ctx.fillText(`${D.fmt(r.frequency_hz.at(-1)/1000,1)} kHz`,box.r-70,box.b+28);};
  document.getElementById('langToggle')?.addEventListener('click',()=>setTimeout(()=>{D.refreshLanguage();document.dispatchEvent(new CustomEvent('dpwe:language'));},0));
})();
