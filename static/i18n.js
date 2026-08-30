(() => {
  const STRINGS = {
    en: {
      'nav.measurement':'Measurement Chain','nav.control':'Control Visualizer','nav.state':'Firmware State Machine','nav.remote':'PSU Remote Control',
      'safety.title':'Safety boundary','safety.body':'Browser/network commands are operator intent only. Protection and trip authority remain local to firmware/hardware.',
      'measurement.title':'Datasheet / Signal-Chain Calculator','measurement.physical':'Physical value','measurement.sensorGain':'Sensor gain (V/unit)','measurement.sensorOffset':'Sensor offset (V)','measurement.opampGain':'Op-amp gain','measurement.opampOffset':'Op-amp offset (V)','measurement.divider':'Divider ratio','measurement.vref':'ADC Vref (V)','measurement.bits':'ADC bits','measurement.calculate':'Calculate chain','measurement.path':'Signal path','measurement.recovered':'Recovered physical','measurement.qerror':'Quantization error','measurement.clipped':'Clipped','measurement.note':'Forward path: physical quantity → sensor → op amp → divider → ADC quantization. The reverse path uses the same coefficients to expose scaling and clipping errors.',
      'control.title':'Digital Control Visualizer','control.model':'Ideal CCM Buck','control.load':'Load (Ω)','control.switching':'Switching (kHz)','control.sampling':'Sampling (kHz)','control.delay':'Delay (samples)','control.analyze':'Analyze loop','control.resonance':'LC resonance','control.crossover':'0 dB crossover','control.pm':'Phase margin','control.plantMag':'Plant magnitude','control.loopMag':'Open-loop magnitude','control.loopPhase':'Open-loop phase',
      'state.title':'Firmware State Machine Viewer','state.model':'Reference model','state.selected':'Selected state','state.simulator':'Transition simulator','state.note':'This simulator shows policy flow only; it is not a production state machine implementation.',
      'remote.title':'Power Supply Remote Control','remote.mockOnly':'MOCK ONLY','remote.setpoints':'Setpoints','remote.voltage':'Voltage (V)','remote.current':'Current limit (A)','remote.applyVoltage':'Apply voltage','remote.applyCurrent':'Apply current','remote.safetySim':'Safety-path simulation','remote.injectOcp':'Inject OCP','remote.clearFault':'Clear fault','remote.interlock':'Interlock closed / OK','remote.note':'The device model intentionally blocks OUTPUT_ON when a fault is latched or interlock is open. Real OVP/OCP/OTP, PWM Trip and interlock must remain local and deterministic in hardware/firmware.','remote.telemetry':'Telemetry','remote.power':'Power','remote.mode':'Mode','remote.log':'Command log'
    },
    zh: {
      'nav.measurement':'量測訊號鏈','nav.control':'數位控制視覺化','nav.state':'韌體狀態機','nav.remote':'電源遠端控制',
      'safety.title':'安全邊界','safety.body':'瀏覽器／網路命令只代表操作意圖。保護與 Trip 權限必須留在韌體／硬體本地端。',
      'measurement.title':'Datasheet／訊號鏈計算器','measurement.physical':'物理量','measurement.sensorGain':'感測器增益 (V/unit)','measurement.sensorOffset':'感測器 Offset (V)','measurement.opampGain':'Op-Amp 增益','measurement.opampOffset':'Op-Amp Offset (V)','measurement.divider':'分壓比','measurement.vref':'ADC Vref (V)','measurement.bits':'ADC 位元數','measurement.calculate':'計算訊號鏈','measurement.path':'訊號路徑','measurement.recovered':'反算物理量','measurement.qerror':'量化誤差','measurement.clipped':'是否飽和','measurement.note':'正向路徑：物理量 → 感測器 → Op-Amp → 分壓 → ADC 量化；反向路徑使用相同係數，方便檢查 scaling、offset 與 clipping。',
      'control.title':'數位控制視覺化','control.model':'理想 CCM Buck','control.load':'負載 (Ω)','control.switching':'開關頻率 (kHz)','control.sampling':'取樣頻率 (kHz)','control.delay':'延遲 (samples)','control.analyze':'分析迴路','control.resonance':'LC 共振頻率','control.crossover':'0 dB 交越頻率','control.pm':'相位裕度','control.plantMag':'Plant 幅值','control.loopMag':'Open-loop 幅值','control.loopPhase':'Open-loop 相位',
      'state.title':'韌體狀態機檢視器','state.model':'參考模型','state.selected':'選取狀態','state.simulator':'轉移模擬器','state.note':'此模擬器只呈現 policy flow，不是 production state machine 實作。',
      'remote.title':'電源供應器遠端控制','remote.mockOnly':'僅限 MOCK','remote.setpoints':'設定值','remote.voltage':'電壓 (V)','remote.current':'電流限制 (A)','remote.applyVoltage':'套用電壓','remote.applyCurrent':'套用電流','remote.safetySim':'安全路徑模擬','remote.injectOcp':'注入 OCP','remote.clearFault':'清除 Fault','remote.interlock':'Interlock 閉合／OK','remote.note':'裝置模型會在 Fault latch 或 Interlock 開路時阻擋 OUTPUT_ON。真實 OVP/OCP/OTP、PWM Trip 與 Interlock 必須在韌體／硬體端保持本地且具決定性的保護權限。','remote.telemetry':'遙測','remote.power':'功率','remote.mode':'模式','remote.log':'命令紀錄'
    }
  };

  const PAIRS = [
    ['Python backend online','Python backend 已連線'],['standalone ready','獨立模式就緒'],['detecting runtime','偵測執行模式'],['initializing','初始化中'],['PYTHON REFERENCE','PYTHON 參考模式'],['STATIC BROWSER','靜態瀏覽器模式'],
    ['Operator intent only; never safety authority.','僅代表操作意圖；不具有安全保護權限。'],['May request bounded setpoints and state transitions.','可請求受限的 setpoint 與狀態轉移。'],['Validates commands, owns sequencing and state policy.','負責驗證命令、時序與狀態政策。'],['Owns deterministic regulation execution.','負責具決定性的閉迴路控制執行。'],['Highest shutdown authority; must not depend on web/network availability.','最高關斷權限；不得依賴 Web／網路可用性。'],
    ['hardware reset','硬體 Reset'],['firmware init','韌體初始化'],['host setpoints','Host 設定值'],['protection','保護'],['sequencer','時序控制器'],['slew generator','Slew 產生器'],['control loop','控制迴路'],['host bounded setpoints','Host 受限設定值'],['hardware protection','硬體保護'],['hardware trip','硬體 Trip'],['protection latch','保護鎖存'],
    ['clock + memory init complete','Clock + Memory 初始化完成'],['self-check pass','自我檢查通過'],['self-check fail','自我檢查失敗'],['STOP complete','STOP 完成'],['OUTPUT_ON accepted','OUTPUT_ON 已接受'],['no latched fault','無鎖存 Fault'],['bus ready','Bus 就緒'],['reference reached','Reference 到達'],['soft-start complete','Soft-start 完成'],['energy discharge complete','能量放電完成'],['fault clear policy satisfied','符合 Fault clear 條件'],['POR / reset','POR / Reset'],
    ['Control authority','控制權限'],['Entry','進入條件'],['Exit','離開條件'],['Outgoing policy events:','可用的 policy events：'],['No outgoing transitions.','沒有可用的狀態轉移。'],['No simulated transitions yet.','尚無模擬轉移紀錄。'],['Select a state.','請選擇狀態。'],
    ['No 0 dB loop crossover found in the evaluated frequency range.','在目前分析頻率範圍內找不到 0 dB loop crossover。'],['Crossover exceeds fs/10; digital delay/model fidelity needs verification.','交越頻率超過 fs/10；必須驗證數位延遲與模型準確度。'],['Crossover exceeds fsw/10; averaged plant assumptions may be weak.','交越頻率超過 fsw/10；平均化 power-stage model 的假設可能不足。'],['Phase margin is below 45 degrees.','相位裕度低於 45°。'],['Computed phase margin is non-positive; do not apply these gains to hardware without loop re-design and measured verification.','計算得到的相位裕度 ≤ 0；未重新設計迴路並完成實測驗證前，不得把這組增益套到硬體。'],['Model boundary:','模型邊界：'],['Ideal CCM buck averaged plant with PI and pure computation/PWM delay. Validate against SFRA or measured loop gain before hardware authority changes.','理想 CCM Buck 平均化模型 + PI + 純計算/PWM 延遲。修改硬體控制權限前，必須以 SFRA 或實測 loop gain 驗證。'],
    ['not found','找不到'],['YES','是'],['NO','否'],['accepted','已接受'],['output_on blocked: fault is latched','OUTPUT_ON 被阻擋：Fault 已鎖存'],['output_on blocked: interlock is open','OUTPUT_ON 被阻擋：Interlock 開路'],['clear_fault blocked while output is enabled','輸出啟用時禁止 clear_fault'],['Fault injection is intentionally browser-mock only. Stop backend mode to use it.','Fault injection 僅允許在 browser mock 模式使用；請停止 backend 模式。'],['Interlock simulation is intentionally browser-mock only.','Interlock 模擬僅允許在 browser mock 模式使用。'],['BROWSER MOCK','瀏覽器 MOCK'],
    ['web ui','Web UI'],['control loop','控制迴路'],['hardware protection','硬體保護'],['firmware','韌體'],['host','Host']
  ].sort((a,b)=>Math.max(b[0].length,b[1].length)-Math.max(a[0].length,a[1].length));

  let language = localStorage.getItem('dpw-language') || (navigator.language.toLowerCase().startsWith('zh') ? 'zh' : 'en');
  let applying = false;

  function replaceDynamic(text, target) {
    let result = text;
    for (const [en, zh] of PAIRS) result = result.split(target === 'zh' ? en : zh).join(target === 'zh' ? zh : en);
    return result;
  }

  function translateDynamic(root=document.body) {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const nodes=[];
    while (walker.nextNode()) {
      const parent=walker.currentNode.parentElement;
      if (!parent || ['SCRIPT','STYLE','TEXTAREA'].includes(parent.tagName) || parent.closest('[data-i18n]')) continue;
      nodes.push(walker.currentNode);
    }
    for (const node of nodes) {
      const next=replaceDynamic(node.nodeValue,language);
      if(next!==node.nodeValue) node.nodeValue=next;
    }
  }

  function applyLanguage(nextLanguage) {
    language = nextLanguage === 'en' ? 'en' : 'zh';
    localStorage.setItem('dpw-language', language);
    document.documentElement.lang = language === 'zh' ? 'zh-Hant' : 'en';
    applying = true;
    document.querySelectorAll('[data-i18n]').forEach(el => {
      const key=el.dataset.i18n;
      if(STRINGS[language][key]) el.textContent=STRINGS[language][key];
    });
    const toggle=document.getElementById('langToggle');
    if(toggle) toggle.textContent=language === 'zh' ? 'English' : '繁中';
    translateDynamic();
    applying = false;
  }

  const observer = new MutationObserver(mutations => {
    if(applying) return;
    applying = true;
    for(const mutation of mutations) {
      if(mutation.type==='characterData') {
        const next=replaceDynamic(mutation.target.nodeValue,language);
        if(next!==mutation.target.nodeValue) mutation.target.nodeValue=next;
      }
      for(const node of mutation.addedNodes) if(node.nodeType===Node.ELEMENT_NODE) translateDynamic(node);
    }
    applying = false;
  });

  document.getElementById('langToggle')?.addEventListener('click',()=>applyLanguage(language==='zh'?'en':'zh'));
  observer.observe(document.body,{subtree:true,childList:true,characterData:true});
  applyLanguage(language);
})();
