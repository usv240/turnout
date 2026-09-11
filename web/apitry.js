/* Generate a key on this page, then call the live API with it and show what came back.

   The section used to print one shared key in a paragraph and ask the reader to believe the header
   did something. That is a weak way to demonstrate an API: nothing on the page proves the key is
   checked, and the smallest thing a curious person might do, call it once, meant copying a constant
   out of prose and opening a terminal.

   So both of those are buttons now. The key is minted by the deployment and signed, so a key that
   was not issued here is refused and says why. Running the endpoints is a real fetch against the
   same host, with the status, the time it took, and the first line of the body, because a claim
   that an API works is worth less than a reader watching it answer. */
(function () {
  "use strict";

  var KEY = null;

  // Every read endpoint, in the order a person would meet them. POST endpoints are deliberately
  // absent: this button must be safe to press, and it must not move the demo under anybody else
  // who is looking at it.
  var ENDPOINTS = [
    ["GET", "/api/health", "Liveness and the simulated clock"],
    ["GET", "/api/state", "Everything the board shows"],
    ["GET", "/api/gaps", "Coverage gaps, with the numbers behind each score"],
    ["GET", "/api/messages", "Every text sent and received"],
    ["GET", "/api/network", "The three departments and every A2A exchange"],
    ["GET", "/api/crew", "What the agent knows about each member"],
    ["GET", "/api/trace", "Agent trace events"],
    ["GET", "/api/openapi.json", "The full schema"]
  ];

  function el(tag, attrs, kids) {
    var n = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      if (k === "class") n.className = attrs[k];
      else if (k === "text") n.textContent = attrs[k];
      else if (k.slice(0, 2) === "on") n.addEventListener(k.slice(2).toLowerCase(), attrs[k]);
      else if (attrs[k] !== null && attrs[k] !== undefined) n.setAttribute(k, attrs[k]);
    });
    (kids || []).forEach(function (c) {
      if (c) n.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
    });
    return n;
  }

  function shorten(text, n) {
    var one = String(text).replace(/\s+/g, " ").trim();
    return one.length > n ? one.slice(0, n - 1) + "…" : one;
  }

  function generate(btn, out, runBtn) {
    btn.disabled = true;
    var was = btn.textContent;
    btn.textContent = "Generating";
    fetch("/api/keys", { method: "POST" })
      .then(function (r) {
        if (!r.ok) throw new Error(r.status + " from /api/keys");
        return r.json();
      })
      .then(function (d) {
        KEY = d.key;
        out.hidden = false;
        out.textContent = "";
        var hours = Math.round((d.expires_in_seconds || 0) / 3600);
        out.appendChild(el("code", { class: "keyline", text: d.key }));
        out.appendChild(el("p", { class: "small muted" }, [
          "Send it as the " + (d.header || "x-api-key") + " header. It expires in " + hours +
          " hours. ",
          el("strong", { text: "Anyone can mint one" }),
          ", so it proves nothing about who is calling. It is here so the check is real and you " +
          "can watch it happen, not to keep anyone out."
        ]));
        runBtn.disabled = false;
        runBtn.focus();
      })
      .catch(function (e) {
        out.hidden = false;
        out.textContent = "";
        out.appendChild(el("p", { class: "small",
          text: "Could not reach the key endpoint: " + e.message + ". The API is still there; " +
                "try the curl below." }));
      })
      .then(function () {
        btn.disabled = false;
        btn.textContent = was;
      });
  }

  function runAll(btn, host) {
    btn.disabled = true;
    var was = btn.textContent;
    btn.textContent = "Running";
    host.hidden = false;
    host.textContent = "";

    var table = el("table", { class: "runs" }, [
      el("thead", {}, [el("tr", {}, [
        el("th", { text: "Endpoint" }), el("th", { text: "Status" }),
        el("th", { text: "Time" }), el("th", { text: "First of the body" })
      ])])
    ]);
    var body = el("tbody");
    table.appendChild(body);
    host.appendChild(table);

    var headers = KEY ? { "x-api-key": KEY } : {};
    var chain = Promise.resolve();
    ENDPOINTS.forEach(function (row) {
      chain = chain.then(function () {
        var path = row[1];
        var started = performance.now();
        return fetch(path, { headers: headers })
          .then(function (r) { return r.text().then(function (t) { return [r, t]; }); })
          .then(function (pair) {
            var r = pair[0], text = pair[1];
            var ms = Math.round(performance.now() - started);
            body.appendChild(el("tr", { class: r.ok ? "ok" : "bad" }, [
              el("td", {}, [el("code", { text: path })]),
              el("td", { text: String(r.status) }),
              el("td", { text: ms + " ms" }),
              el("td", { class: "peek", text: shorten(text, 96) })
            ]));
          })
          .catch(function (e) {
            body.appendChild(el("tr", { class: "bad" }, [
              el("td", {}, [el("code", { text: path })]),
              el("td", { text: "failed" }), el("td", { text: "" }),
              el("td", { class: "peek", text: e.message })
            ]));
          });
      });
    });

    chain.then(function () {
      var ok = body.querySelectorAll("tr.ok").length;
      host.appendChild(el("p", { class: "small muted" }, [
        ok + " of " + ENDPOINTS.length + " answered, live, from " + host.dataset.host +
        ". Read only: nothing here changes the demo for anyone else looking at it."
      ]));
      btn.disabled = false;
      btn.textContent = was;
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    var mount = document.getElementById("api-try");
    if (!mount) return;

    var keyOut = el("div", { class: "keyout", hidden: "" });
    var runOut = el("div", { class: "runout", hidden: "",
                             "data-host": location.host, "aria-live": "polite" });
    var runBtn = el("button", { class: "btn", type: "button", disabled: "" },
                    ["Run every read endpoint"]);
    var genBtn = el("button", { class: "btn primary", type: "button" }, ["Generate a key"]);

    genBtn.addEventListener("click", function () { generate(genBtn, keyOut, runBtn); });
    runBtn.addEventListener("click", function () { runAll(runBtn, runOut); });
    runBtn.disabled = true;

    mount.appendChild(el("div", { class: "btn-row" }, [genBtn, runBtn]));
    mount.appendChild(keyOut);
    mount.appendChild(runOut);
  });
})();
