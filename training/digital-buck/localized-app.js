(() => {
  "use strict";

  const config = window.DIGITAL_BUCK_COMMUNITY || {};
  const checkout = typeof config.checkoutUrl === "string" ? config.checkoutUrl.trim() : "";
  const lang = (document.documentElement.lang || "en").toLowerCase();
  const copy = lang.startsWith("zh-cn") ? {
    timingOk: "正确：SOCA → ADC sample/convert → ISR/CLA → shadow write → load event。",
    timingBad: "再想一次：控制计算不能发生在 ADC sample 之前，shadow write 也不等于 PWM 立即生效。",
    faultOk: "对。DMM 是 12 V、固件却重建成 9.6 V，先验证 ADC pin / divider / scaling chain，比先改 PI gain 信息量更高。",
    faultBad: "这一步信息量较低。先确认 physical → AFE/divider → ADC pin → counts → reconstructed feedback。",
    closed: "Early Access 尚未开放收款。正式 checkout 启用后，这里会直接进入结账页。"
  } : {
    timingOk: "Correct: SOCA → ADC sample/convert → ISR/CLA → shadow write → load event.",
    timingBad: "Try again: control computation cannot happen before the ADC sample, and a shadow write does not mean the PWM output changes immediately.",
    faultOk: "Correct. If the DMM says 12 V but firmware reconstructs 9.6 V, validate the ADC pin / divider / scaling chain before touching PI gain.",
    faultBad: "That step gives less information. First verify physical → AFE/divider → ADC pin → counts → reconstructed feedback.",
    closed: "Early Access checkout is not open yet. This button will go directly to checkout once the product is activated."
  };

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
      out.textContent = `L = ${l} µH → ideal CCM ΔIL ≈ ${deltaIL(l).toFixed(2)} A`;
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
        q("#timing-result").textContent =
          button.dataset.timing === "correct" ? copy.timingOk : copy.timingBad;
      });
    });
  }

  function setupFault() {
    qa("[data-fault]").forEach((button) => {
      button.addEventListener("click", () => {
        q("#fault-result").textContent =
          button.dataset.fault === "adc" ? copy.faultOk : copy.faultBad;
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
          status.textContent = copy.closed;
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