(() => {
  "use strict";

  const config = window.DIGITAL_BUCK_COMMUNITY || {};
  const checkout = typeof config.checkoutUrl === "string" ? config.checkoutUrl.trim() : "";

  const q = (selector, root = document) => root.querySelector(selector);
  const qa = (selector, root = document) => Array.from(root.querySelectorAll(selector));

  function absoluteHttpUrl(value) {
    if (!value) return false;
    try {
      const url = new URL(value);
      return url.protocol === "https:" || url.protocol === "http:";
    } catch (_) {
      return false;
    }
  }

  function deltaIL(lUh) {
    const vin = 48;
    const vout = 12;
    const fsw = 100000;
    const duty = vout / vin;
    return ((vin - vout) * duty) / ((lUh * 1e-6) * fsw);
  }

  function adcCounts(vout) {
    const rTop = 82000;
    const rBottom = 20000;
    const vadc = vout * (rBottom / (rTop + rBottom));
    const counts = Math.round((vadc / 3.3) * 4095);
    return { vadc, counts };
  }

  function setupPhysics() {
    const slider = q("#inductance");
    const out = q("#physics-result");
    const render = () => {
      const l = Number(slider.value);
      const ripple = deltaIL(l);
      out.textContent = `L = ${l} µH → ideal CCM ΔIL ≈ ${ripple.toFixed(2)} A`;
    };
    slider.addEventListener("input", render);
    render();
  }

  function setupSensing() {
    const input = q("#sense-vout");
    const out = q("#sense-result");
    const render = () => {
      const v = Number(input.value);
      const result = adcCounts(v);
      out.textContent = `Vout ${v.toFixed(1)} V → ADC pin ${result.vadc.toFixed(3)} V → ~${result.counts} counts (12-bit, 3.3 V)`;
    };
    input.addEventListener("input", render);
    render();
  }

  function setupTiming() {
    qa("[data-timing]").forEach((button) => {
      button.addEventListener("click", () => {
        const ok = button.dataset.timing === "correct";
        q("#timing-result").textContent = ok
          ? "正確：SOCA → ADC sample/convert → ISR/CLA → shadow write → load event。"
          : "再想一次：控制計算不能發生在 ADC sample 之前，shadow write 也不等於 PWM 立刻生效。";
      });
    });
  }

  function setupFault() {
    qa("[data-fault]").forEach((button) => {
      button.addEventListener("click", () => {
        const ok = button.dataset.fault === "adc";
        q("#fault-result").textContent = ok
          ? "對。DMM 12 V、韌體卻重建 9.6 V，先驗證 ADC pin / divider / scaling chain，比先改 PI gain 更有資訊量。"
          : "這一步資訊量較低。先確認 physical → AFE/divider → ADC pin → counts → reconstructed feedback。";
      });
    });
  }

  function setupCheckout() {
    qa("[data-buy]").forEach((link) => {
      if (absoluteHttpUrl(checkout)) {
        link.href = checkout;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.removeAttribute("aria-disabled");
      } else {
        link.removeAttribute("href");
        link.setAttribute("aria-disabled", "true");
        link.classList.add("disabled");
        link.addEventListener("click", (event) => {
          event.preventDefault();
          const status = q("#checkout-status");
          status.hidden = false;
          status.textContent = "Early Access 尚未開放收款。完成商品上架後，這裡才會接正式 checkout。";
        });
      }
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    setupPhysics();
    setupSensing();
    setupTiming();
    setupFault();
    setupCheckout();
  });
})();
