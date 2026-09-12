(() => {
  ['./eng/engineering.css','./eng/status_console.css'].forEach(href=>{const css=document.createElement('link');css.rel='stylesheet';css.href=href;document.head.append(css);});
  const sources=['./eng/common.js','./eng/status_console.js','./eng/data_source.js','./eng/profiles.js','./eng/control_sfra.js','./eng/system_tools.js'];
  let index=0;
  const next=()=>{if(index>=sources.length)return;const s=document.createElement('script');s.src=sources[index++];s.onload=next;s.onerror=()=>console.error('Failed to load engineering module',s.src);document.body.append(s);};
  next();
})();
