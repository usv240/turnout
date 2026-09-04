/* Shared behaviour: theme, InfoTips, small helpers.
   No framework, no build step. Everything here works from a plain file server. */

(function () {
  "use strict";

  /* Theme -------------------------------------------------------------- */
  var KEY = "turnout-theme";
  function stored() { try { return localStorage.getItem(KEY); } catch (e) { return null; } }
  function apply(mode) {
    if (mode === "system") { document.documentElement.removeAttribute("data-theme"); }
    else { document.documentElement.setAttribute("data-theme", mode); }
    try { localStorage.setItem(KEY, mode); } catch (e) { /* private window */ }
    document.querySelectorAll(".theme-toggle button").forEach(function (b) {
      b.setAttribute("aria-pressed", String(b.dataset.mode === mode));
    });
  }
  // Light is the default. A person who has their laptop in dark mode should still meet the
  // product in the theme it was drawn in, unless they choose otherwise here.
  window.ThemeControl = { apply: apply, current: function () { return stored() || "light"; } };

  function mountThemeToggle() {
    document.querySelectorAll(".theme-toggle").forEach(function (host) {
      if (host.dataset.mounted) return;
      host.dataset.mounted = "1";
      host.setAttribute("role", "group");
      host.setAttribute("aria-label", "Colour theme");
      ["light", "dark", "system"].forEach(function (mode) {
        var b = document.createElement("button");
        b.type = "button";
        b.dataset.mode = mode;
        b.textContent = mode === "light" ? "Light" : mode === "dark" ? "Dark" : "System";
        b.addEventListener("click", function () { apply(mode); });
        host.appendChild(b);
      });
    });
    apply(stored() || "light");
  }

  /* InfoTips ------------------------------------------------------------
     Every domain term, metric, agent and service gets one. Content lives in
     window.INFOTIPS so the copy can be reviewed in one place. */
  var openPop = null;
  function closePop() {
    if (!openPop) return;
    if (openPop.btn) openPop.btn.setAttribute("aria-expanded", "false");
    openPop.el.remove();
    openPop = null;
  }
  function showPop(btn, html) {
    closePop();
    var el = document.createElement("div");
    el.className = "info-pop";
    el.setAttribute("role", "dialog");
    el.setAttribute("aria-label", "More information");
    el.innerHTML = html;
    document.body.appendChild(el);
    if (window.innerWidth > 640) {
      var r = btn.getBoundingClientRect();
      var top = window.scrollY + r.bottom + 8;
      var left = Math.min(window.scrollX + r.left - 8, window.scrollX + window.innerWidth - el.offsetWidth - 16);
      el.style.top = top + "px";
      el.style.left = Math.max(window.scrollX + 8, left) + "px";
    }
    btn.setAttribute("aria-expanded", "true");
    openPop = { el: el, btn: btn };
    var first = el.querySelector("a");
    if (first) first.focus();
  }
  document.addEventListener("click", function (e) {
    var btn = e.target.closest && e.target.closest(".info");
    if (btn) {
      e.preventDefault();
      if (openPop && openPop.btn === btn) { closePop(); return; }
      var key = btn.dataset.tip;
      var tips = window.INFOTIPS || {};
      var text = tips[key] || btn.dataset.text || "No explanation written yet.";
      showPop(btn, typeof text === "string" ? "<p>" + text + "</p>" : text.html);
      return;
    }
    if (openPop && !e.target.closest(".info-pop")) closePop();
  });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") closePop(); });

  function mountInfoButtons() {
    document.querySelectorAll("[data-tip]").forEach(function (el) {
      if (el.classList.contains("info")) {
        if (!el.getAttribute("aria-label")) {
          el.setAttribute("aria-label", "More about " + (el.dataset.label || el.dataset.tip));
        }
        el.setAttribute("aria-expanded", "false");
        el.type = "button";
        if (!el.textContent.trim()) el.textContent = "i";
      }
    });
  }

  /* Helpers -------------------------------------------------------------- */
  window.h = function (tag, attrs, children) {
    var el = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      if (k === "class") el.className = attrs[k];
      else if (k === "text") el.textContent = attrs[k];
      else if (k === "html") el.innerHTML = attrs[k];
      else if (k.slice(0, 2) === "on") el.addEventListener(k.slice(2).toLowerCase(), attrs[k]);
      else if (attrs[k] !== null && attrs[k] !== undefined) el.setAttribute(k, attrs[k]);
    });
    (children || []).forEach(function (c) {
      if (c === null || c === undefined || c === false) return;
      el.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
    });
    return el;
  };

  window.infoBtn = function (key, label) {
    return window.h("button", { class: "info", "data-tip": key, "data-label": label || key,
      "aria-label": "More about " + (label || key), "aria-expanded": "false", type: "button", text: "i" });
  };

  window.SHAPES = { critical: "⬣", high: "◆", elevated: "▲", low: "●", covered: "■" };

  window.levelBadge = function (level, word) {
    return window.h("span", { class: "badge " + level }, [
      window.h("span", { class: "shape", "aria-hidden": "true", text: window.SHAPES[level] || "●" }),
      window.h("span", { text: word || level })
    ]);
  };

  window.fmtTime = function (iso) {
    var d = new Date(iso);
    var h = d.getHours(), m = d.getMinutes();
    var suffix = h < 12 ? "am" : "pm";
    return (h % 12 || 12) + ":" + (m < 10 ? "0" : "") + m + suffix;
  };
  window.fmtDayTime = function (iso) {
    var d = new Date(iso);
    return ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"][d.getDay()] + " " + window.fmtTime(iso);
  };

  /* A code block wide enough to scroll is a scrollable region, and a scrollable region that cannot
     take focus cannot be read with a keyboard. axe reports it as serious, and it is. */
  function makeCodeBlocksFocusable() {
    Array.prototype.forEach.call(document.querySelectorAll("pre"), function (el) {
      if (!el.hasAttribute("tabindex")) el.setAttribute("tabindex", "0");
      if (!el.hasAttribute("role")) el.setAttribute("role", "region");
      if (!el.hasAttribute("aria-label")) el.setAttribute("aria-label", "Code block");
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    mountThemeToggle();
    mountInfoButtons();
    makeCodeBlocksFocusable();
  });
  window.MountInfo = mountInfoButtons;
})();
