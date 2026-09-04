/* The Turnout product screens. Vanilla JS against the API in turnout/api/app.py. */

(function () {
  "use strict";

  var API = "";
  var state = null;
  var traceCursor = 0;
  var traceEvents = [];
  var selectedMember = null;
  var busy = false;

  function api(path, opts) {
    return fetch(API + path, opts).then(function (r) {
      if (!r.ok) throw new Error(path + " returned " + r.status);
      return r.json();
    });
  }

  function setBusy(on, label) {
    busy = on;
    document.querySelectorAll("#steps .btn").forEach(function (b) { b.disabled = on; });
    var reset = document.getElementById("reset");
    if (reset) reset.disabled = on;
    if (on && label) {
      var s = document.getElementById("status");
      s.className = "status-line";
      s.textContent = label;
    }
  }

  /* Rendering ----------------------------------------------------------- */

  function renderStatus() {
    var s = document.getElementById("status");
    s.className = "status-line " + state.tone;
    s.textContent = state.headline;

    document.getElementById("clock").textContent = window.fmtDayTime(state.now);

    var it = state.interrupts;
    document.getElementById("quiet-text").textContent =
      "Interrupted you " + it.used_today + (it.used_today === 1 ? " time" : " times") +
      " today. Budget " + it.budget + ".";
    var pips = document.getElementById("quiet-pips");
    pips.innerHTML = "";
    for (var i = 0; i < it.budget; i++) {
      pips.appendChild(window.h("span", { class: "pip" + (i < it.used_today ? " used" : "") }));
    }
  }

  function renderSteps() {
    var host = document.getElementById("steps");
    host.innerHTML = "";
    var nextUndone = state.steps.filter(function (s) { return !s.done; })[0];
    state.steps.forEach(function (s) {
      var isNext = nextUndone && nextUndone.id === s.id;
      var b = window.h("button", {
        class: "btn" + (isNext ? " primary" : ""),
        type: "button",
        disabled: s.done || busy ? "" : null,
        onclick: function () { runStep(s.id, s.detail); }
      }, [s.done ? "Done: " + s.title : s.title]);
      if (s.done) b.disabled = true;
      host.appendChild(b);
    });
    var detail = nextUndone ? nextUndone.detail : "The week is played out. Press Reset to run it again.";
    document.getElementById("step-detail").textContent = detail;
  }

  function riskDetails(g) {
    var i = g.inputs;
    var dl = window.h("dl", { class: "kv" });
    function row(label, value, tip) {
      var dt = window.h("dt", {}, [label]);
      if (tip) dt.appendChild(window.infoBtn(tip, label));
      dl.appendChild(dt);
      dl.appendChild(window.h("dd", { text: value }));
    }
    row("Expected calls", i.expected_calls.toFixed(2) + " in this window", "expected_calls");
    row("Weather hazard", i.hazard === 1 ? "none" : i.hazard.toFixed(1) + "x (" + i.hazard_names.join(", ") + ")", "hazard");
    row("Chance nobody qualified responds", Math.round(i.p_understaffed * 100) + "%", "p_understaffed");
    row("Time-critical weighting", i.severity.toFixed(2), "severity");
    row("Crew short of", g.missing_roles.length ? g.missing_roles.join(" and ").replace(/_/g, " ") : "nothing", "min_crew");
    row("Available members", String(i.available_member_ids.length), null);
    row("History used", i.history_days + " days", "history_days");
    row("Risk score", g.risk_score.toFixed(2) + " of 1.00", "risk_score");

    var wrap = window.h("div", {}, [dl]);
    wrap.appendChild(window.h("pre", { class: "formula" },
      ["risk = 1 - exp(-3.0 x (" + i.expected_calls.toFixed(2) + " x " + i.hazard.toFixed(1) + ") x " +
       i.p_understaffed.toFixed(2) + " x " + i.severity.toFixed(2) + ") = " + g.risk_score.toFixed(2)]));
    return wrap;
  }

  function offersList(g) {
    if (!g.offers.length) return null;
    var ul = window.h("ul", { class: "stack", style: "padding-left:var(--s5);margin:0" });
    g.offers.forEach(function (o) {
      var text = o.can_cover
        ? o.peer_name + " can cover, " + o.delay_min + " minute delay. Millbrook would owe " +
          o.ledger_delta_hours + " hours." + (o.auto_approved ? " Their chief pre-approved delays this short." : "")
        : o.peer_name + " declined: " + o.reason;
      ul.appendChild(window.h("li", { class: "small", text: text }));
    });
    return window.h("div", {}, [window.h("strong", { class: "small", text: "What the neighbours said" }), ul]);
  }

  function peerName(g, id) {
    var match = (g.offers || []).filter(function (o) { return o.peer === id; })[0];
    return match ? match.peer_name : id;
  }

  function statusWords(g) {
    return {
      open: "Not yet worked",
      asking_members: "Asking our own members",
      members_declined: "Our members cannot cover it",
      asking_neighbors: "Asking the neighbours",
      needs_chief: "Waiting for you",
      no_options: "No neighbour can cover. Only you can decide this one.",
      covered: g.covered_by ? "Covered by " + peerName(g, g.covered_by) : "Covered",
      left_open: "Left open at your request",
      thin: "Thin, logged only"
    }[g.status] || g.status;
  }

  function renderGaps() {
    var host = document.getElementById("gaps");
    host.innerHTML = "";
    var gaps = state.gaps.filter(function (g) { return g.status !== "thin"; });
    if (!gaps.length) {
      host.appendChild(window.h("div", { class: "card" }, [
        window.h("h3", { text: "Nothing needs you" }),
        window.h("p", { class: "muted", style: "margin:0",
          text: "No window in the next seven days is short a crew. Press the first step above to play the week." })
      ]));
      return;
    }
    gaps.forEach(function (g) {
      var level = g.status === "covered" ? "covered" : g.level;
      var card = window.h("div", { class: "card gap-card " + level });
      var head = window.h("div", { class: "gap-head" }, [
        window.h("span", { class: "gap-window", text: g.window_label + ", " + g.district }),
        window.levelBadge(level, g.status === "covered" ? "covered" : g.level)
      ]);
      card.appendChild(head);
      card.appendChild(window.h("p", { style: "margin-bottom:var(--s3)" }, [
        g.explanation.charAt(0).toUpperCase() + g.explanation.slice(1) + ".",
        window.infoBtn("risk_score", "the risk score")
      ]));
      card.appendChild(window.h("p", { class: "small muted", style: "margin-bottom:var(--s3)",
        text: statusWords(g) + (g.resolution ? ". " + g.resolution : "") }));
      var offers = offersList(g);
      if (offers) card.appendChild(offers);

      var det = window.h("details", { style: "margin-top:var(--s3)" });
      det.appendChild(window.h("summary", { style: "cursor:pointer;font-size:.9375rem",
        text: "Show the numbers behind this" }));
      det.appendChild(riskDetails(g));
      card.appendChild(det);
      host.appendChild(card);
    });
    window.MountInfo();
  }

  function bubble(m) {
    var b = window.h("div", { class: "bubble " + m.direction }, [m.body]);
    var meta = window.fmtDayTime(m.at) + (m.held ? " (held for quiet hours)" : "");
    var wrap = window.h("div", { style: "display:flex;flex-direction:column;align-items:" +
      (m.direction === "in" ? "flex-end" : "flex-start") }, [b,
      window.h("span", { class: "bubble-meta", text: meta })]);
    return wrap;
  }

  function renderPhones() {
    var host = document.getElementById("phones");
    host.innerHTML = "";
    var chiefPhone = state.department.chief_phone;

    api("/api/messages?phone=" + encodeURIComponent(chiefPhone)).then(function (d) {
      var body = window.h("div", { class: "phone-body" });
      d.messages.forEach(function (m) { body.appendChild(bubble(m)); });
      if (!d.messages.length) body.appendChild(window.h("p", { class: "muted small", text: "No messages yet." }));
      var foot = window.h("div", { class: "phone-foot" });
      [["1", "Approve"], ["2", "Options"], ["3", "Leave open"]].forEach(function (pair) {
        foot.appendChild(window.h("button", { class: "btn small", type: "button",
          onclick: function () { sendReply(chiefPhone, pair[0]); } }, [pair[1] + " (" + pair[0] + ")"]));
      });
      host.appendChild(window.h("div", { class: "phone" }, [
        window.h("div", { class: "phone-head", text: "Chief Dana Ortiz " + chiefPhone }), body, foot]));
      renderMemberPhone(host);
    });
  }

  function renderMemberPhone(host) {
    var withMessages = state.members.filter(function (m) { return true; });
    if (!selectedMember) {
      var m3 = withMessages.filter(function (m) { return m.id === "millbrook-m03"; })[0];
      selectedMember = (m3 || withMessages[0]).id;
    }
    var member = withMessages.filter(function (m) { return m.id === selectedMember; })[0];
    var select = window.h("select", {
      style: "font:inherit;font-size:.875rem;padding:4px;border-radius:var(--r-sm);border:1px solid var(--border);background:var(--surface);color:var(--text)",
      "aria-label": "Choose a member",
      onchange: function (e) { selectedMember = e.target.value; renderPhones(); }
    });
    withMessages.forEach(function (m) {
      select.appendChild(window.h("option", { value: m.id, selected: m.id === selectedMember ? "" : null },
        [m.name + " (" + m.roles.join(", ").replace(/_/g, " ") + ")"]));
    });

    api("/api/messages?phone=" + encodeURIComponent(member.phone)).then(function (d) {
      var body = window.h("div", { class: "phone-body" });
      d.messages.forEach(function (m) { body.appendChild(bubble(m)); });
      if (!d.messages.length) {
        body.appendChild(window.h("p", { class: "muted small",
          text: "Nothing sent to " + member.name + " yet." }));
      }
      var foot = window.h("div", { class: "phone-foot" });
      ["Y", "N", "till 2", "STOP"].forEach(function (t) {
        foot.appendChild(window.h("button", { class: "btn small", type: "button",
          onclick: function () { sendReply(member.phone, t); } }, [t]));
      });
      var head = window.h("div", { class: "phone-head" }, ["Member: ", select]);
      host.appendChild(window.h("div", { class: "phone" }, [head, body, foot]));
    });
  }

  function renderNetwork() {
    var host = document.getElementById("network");
    host.innerHTML = "";
    api("/api/network").then(function (n) {
      var pos = { millbrook: [130, 190], riverton: [330, 150], cedar: [90, 60] };
      var svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      svg.setAttribute("viewBox", "0 0 440 250");
      svg.setAttribute("class", "network-map");
      svg.setAttribute("role", "img");
      svg.setAttribute("aria-label",
        "Map of three departments. Millbrook is linked to Riverton and to Cedar Hollow by mutual aid.");
      function el(tag, attrs) {
        var e = document.createElementNS("http://www.w3.org/2000/svg", tag);
        Object.keys(attrs).forEach(function (k) { e.setAttribute(k, attrs[k]); });
        return e;
      }
      n.edges.forEach(function (e) {
        var a = pos[e.from], b = pos[e.to];
        svg.appendChild(el("line", { x1: a[0], y1: a[1], x2: b[0], y2: b[1],
          stroke: "var(--border)", "stroke-width": 2 }));
        var label = el("text", { x: (a[0] + b[0]) / 2, y: (a[1] + b[1]) / 2 - 6,
          "text-anchor": "middle", class: "edge-label" });
        label.textContent = e.balance_hours === 0 ? "even"
          : (e.balance_hours > 0 ? "owes " + e.balance_hours + "h" : "owed " + Math.abs(e.balance_hours) + "h");
        svg.appendChild(label);
      });
      n.departments.forEach(function (d) {
        var p = pos[d.id];
        svg.appendChild(el("circle", { cx: p[0], cy: p[1], r: 13,
          fill: d.id === "millbrook" ? "var(--accent)" : "var(--surface)",
          stroke: "var(--accent)", "stroke-width": 2 }));
        var t = el("text", { x: p[0], y: p[1] + 30, "text-anchor": "middle", class: "node-label" });
        t.textContent = d.short_name;
        svg.appendChild(t);
      });
      host.appendChild(window.h("div", { class: "card" }, [svg]));

      var names = {};
      n.departments.forEach(function (d) { names[d.id] = d.short_name; });
      function nm(id) { return names[id] || id; }

      var ex = window.h("div", { class: "card stack" }, [
        window.h("h3", {}, ["Agent-to-agent exchanges", window.infoBtn("a2a", "the A2A protocol")])
      ]);
      if (!n.exchanges.length) {
        ex.appendChild(window.h("p", { class: "muted small", style: "margin:0",
          text: "Nothing yet. Play up to the third step to watch Millbrook's agent ask the neighbours." }));
      } else {
        n.exchanges.forEach(function (e) {
          var line;
          if (e.kind === "a2a_request") {
            line = nm(e.dept_id) + " asked " + (e.peers || []).map(nm).join(" and ") + " to cover " + e.window;
          } else if (e.kind === "a2a_offer") {
            line = nm(e.peer) + " answered: " + (e.can_cover
              ? "can cover, " + e.delay + " minute delay" : "declined, " + e.reason);
          } else if (e.kind === "a2a_confirmed") {
            line = nm(e.dept_id) + " confirmed" + (e.auto_approved ? ", auto-approved inside their chief's rule" : "");
          } else if (e.kind === "a2a_pending_chief") {
            line = nm(e.dept_id) + " needs its own chief to approve first";
          } else if (e.kind === "a2a_error") {
            line = "No usable answer from " + nm(e.peer) + ": " + e.error;
          }
          else { line = e.kind; }
          ex.appendChild(window.h("p", { class: "small", style: "margin:0" },
            [window.fmtDayTime(e.at) + " " + line]));
        });
      }
      host.appendChild(ex);

      var led = window.h("div", { class: "card" }, [
        window.h("h3", {}, ["Mutual aid ledger", window.infoBtn("ledger", "the ledger")])]);
      state.ledger.forEach(function (l) {
        led.appendChild(window.h("p", { class: "small", style: "margin:0",
          text: l.balance_hours === 0 ? "Even with " + l.peer_name
            : (l.balance_hours > 0 ? "Millbrook owes " + l.peer_name + " " + l.balance_hours + " hours"
              : l.peer_name + " owes Millbrook " + Math.abs(l.balance_hours) + " hours") }));
      });
      host.appendChild(led);
      window.MountInfo();
    });
  }

  var TRACE_WORDS = {
    poll_sent: "Roll call text sent",
    sms_out: "Text sent",
    sms_in: "Text received",
    sms_held: "Held for quiet hours",
    gaps_computed: "Coverage recomputed",
    gap_status: "Gap status changed",
    ask_sent: "Targeted ask sent",
    ask_blocked: "Ask blocked by policy",
    a2a_request: "Asked the neighbours over A2A",
    a2a_offer: "Neighbour answered",
    a2a_offer_sent: "Answered a neighbour",
    a2a_confirmed: "Neighbour confirmed",
    a2a_pending_chief: "Neighbour's chief must approve",
    a2a_error: "Neighbour unreachable",
    decision_sent: "Chief interrupted",
    decision_deferred: "Held back, budget spent",
    gap_covered: "Gap covered",
    ledger: "Ledger moved",
    graph_start: "Coverage graph started",
    graph_end: "Coverage graph finished",
    voice_note: "Voice debrief received",
    neris_draft: "NERIS draft written",
    risk_scored: "Risk engine ran"
  };

  function renderTrace() {
    var host = document.getElementById("trace");
    host.innerHTML = "";
    if (!traceEvents.length) {
      host.appendChild(window.h("p", { class: "muted small", text: "No events yet. Play a step." }));
      return;
    }
    traceEvents.forEach(function (e) {
      var copy = {};
      Object.keys(e).forEach(function (k) {
        if (k !== "kind" && k !== "at" && k !== "dept_id") copy[k] = e[k];
      });
      host.appendChild(window.h("div", { class: "trace-row" }, [
        window.h("span", { class: "t", text: window.fmtTime(e.at) }),
        window.h("span", { class: "k", text: TRACE_WORDS[e.kind] || e.kind }),
        window.h("span", { class: "d", text: JSON.stringify(copy) })
      ]));
    });
  }

  function renderIncident() {
    var host = document.getElementById("incident");
    host.innerHTML = "";
    if (!state.incidents.length) {
      host.appendChild(window.h("div", { class: "card" }, [
        window.h("h3", { text: "No incident yet" }),
        window.h("p", { class: "muted", style: "margin:0",
          text: "Play through to the last step. A collision happens on Thursday, the officer leaves a voice note in the truck, and Scribe drafts the report." })
      ]));
      return;
    }
    state.incidents.forEach(function (i) {
      var card = window.h("div", { class: "card stack" }, [
        window.h("h3", {}, ["Incident " + i.id + ", " + window.fmtDayTime(i.at),
          window.infoBtn("neris", "NERIS")]),
        window.h("p", { class: "muted small", style: "margin:0" },
          [window.h("strong", { text: "Voice note: " }), i.transcript])
      ]);
      if (i.draft) {
        var dl = window.h("dl", { class: "kv" });
        var d = i.draft;
        function row(k, v) {
          if (v === null || v === undefined || v === "" || (Array.isArray(v) && !v.length)) return;
          dl.appendChild(window.h("dt", { text: k }));
          dl.appendChild(window.h("dd", { text: Array.isArray(v) ? v.join(", ") : String(v) }));
        }
        row("Incident types", d.incident_types);
        row("Location", d.location);
        row("District", d.district);
        row("Units", d.units);
        row("Personnel", d.personnel_count);
        row("Actions taken", d.actions_taken);
        row("Casualties", d.casualties);
        row("Narrative", d.narrative);
        card.appendChild(dl);
        if (d.uncertain_fields && d.uncertain_fields.length) {
          card.appendChild(window.h("p", { class: "small", style: "margin:0" }, [
            window.levelBadge("high", "needs your eye"), " ",
            "Scribe was not sure about: " + d.uncertain_fields.join(", ") +
            ". It flagged them rather than guessing."
          ]));
        }
        card.appendChild(window.h("p", { class: "small muted", style: "margin:0",
          text: "Nothing is submitted to NERIS until the chief presses submit." }));
      } else {
        card.appendChild(window.h("p", { class: "muted small", style: "margin:0", text: "Draft pending." }));
      }
      host.appendChild(card);
    });
    window.MountInfo();
  }

  function renderAll() {
    renderStatus();
    renderSteps();
    renderGaps();
    var active = document.querySelector('[role="tab"][aria-selected="true"]').id;
    if (active === "tab-phones") renderPhones();
    if (active === "tab-network") renderNetwork();
    if (active === "tab-trace") renderTrace();
    if (active === "tab-incident") renderIncident();
  }


  /* Connection state -----------------------------------------------------
     Three things a person needs when something breaks: what happened, what the system did about
     it, and the one action available. */
  var connEl = null;
  function connection(message, kind, actionLabel, action) {
    if (connEl) { connEl.remove(); connEl = null; }
    if (!message) return;
    connEl = window.h("div", { class: "conn" + (kind === "gone" ? " gone" : ""),
      role: "status", "aria-live": "polite" }, [window.h("span", { text: message })]);
    if (actionLabel) {
      connEl.appendChild(window.h("button", { class: "btn small", type: "button",
        onclick: function () { connection(null); action(); } }, [actionLabel]));
    }
    document.body.appendChild(connEl);
  }
  window.addEventListener("offline", function () {
    connection("You are offline. Nothing is lost; the demo picks up where it left off.", "gone");
  });
  window.addEventListener("online", function () {
    connection("Back online.", "");
    setTimeout(function () { connection(null); }, 2500);
  });

  function fail(e) {
    setBusy(false);
    var offline = !navigator.onLine;
    var el = document.getElementById("status");
    el.className = "status-line needs_you";
    el.textContent = offline
      ? "You are offline, so that step did not run. Nothing was lost."
      : "That step did not finish: " + e.message + ". Nothing was saved.";
    connection(offline ? "You are offline." : "The service did not answer.",
      "gone", "Try again", function () { location.reload(); });
  }

  /* Actions -------------------------------------------------------------- */

  function pullTrace() {
    return api("/api/trace?since=" + traceCursor).then(function (t) {
      traceEvents = traceEvents.concat(t.events);
      traceCursor = t.next;
    });
  }

  function runStep(id, detail) {
    if (busy) return;
    setBusy(true, "Running: " + detail);
    api("/api/step", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ step: id })
    }).then(function (s) {
      state = s;
      return pullTrace();
    }).then(function () {
      setBusy(false);
      renderAll();
    }).catch(fail);
  }

  function sendReply(phone, body) {
    if (busy) return;
    setBusy(true, "Delivering the reply");
    api("/api/reply", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ phone: phone, body: body })
    }).then(function (s) {
      state = s;
      return pullTrace();
    }).then(function () {
      setBusy(false);
      renderAll();
    });
  }

  function reset() {
    setBusy(true, "Resetting to Wednesday 06:30");
    api("/api/reset", { method: "POST" }).then(function (s) {
      state = s;
      traceEvents = [];
      traceCursor = 0;
      return pullTrace();
    }).then(function () {
      setBusy(false);
      renderAll();
    });
  }

  /* Tabs ----------------------------------------------------------------- */
  function selectTab(id) {
    document.querySelectorAll('[role="tab"]').forEach(function (t) {
      var on = t.id === id;
      t.setAttribute("aria-selected", String(on));
      document.getElementById(t.getAttribute("aria-controls")).hidden = !on;
    });
    if (id === "tab-phones") renderPhones();
    if (id === "tab-network") renderNetwork();
    if (id === "tab-trace") renderTrace();
    if (id === "tab-incident") renderIncident();
    if (history.replaceState) history.replaceState(null, "", "#" + id.replace("tab-", ""));
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll('[role="tab"]').forEach(function (t) {
      t.addEventListener("click", function () { selectTab(t.id); });
    });
    document.getElementById("reset").addEventListener("click", reset);

    api("/api/state").then(function (s) {
      state = s;
      return pullTrace();
    }).then(function () {
      renderAll();
      var hash = (location.hash || "").replace("#", "");
      if (hash && document.getElementById("tab-" + hash)) selectTab("tab-" + hash);
    }).catch(fail);
  });
})();
