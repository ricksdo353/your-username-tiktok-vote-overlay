/* SMS Tester front-end. No secrets here — it only talks to this app's own API. */
(() => {
  "use strict";

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const csrf = () => $('meta[name="csrf-token"]')?.content || "";

  /* ---------- timestamps in the phone's own time zone ---------- */
  const fmtTime = (iso) => {
    const d = new Date(iso);
    if (isNaN(d)) return iso;
    const now = new Date();
    const sameDay = d.toDateString() === now.toDateString();
    const time = d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit", second: "2-digit" });
    if (sameDay) return `Today ${time}`;
    return `${d.toLocaleDateString([], { month: "short", day: "numeric", year: d.getFullYear() === now.getFullYear() ? undefined : "numeric" })} ${time}`;
  };
  const localizeTimes = (root = document) =>
    $$("time[data-local-time]", root).forEach((t) => { t.textContent = fmtTime(t.dateTime); });

  /* ---------- SMS character / segment counter ---------- */
  const GSM = "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà";
  const GSM_EXT = "^{}\\[~]|€\f";
  const segments = (text) => {
    let gsm = true, len = 0;
    for (const ch of text) {
      if (GSM.includes(ch)) len += 1;
      else if (GSM_EXT.includes(ch)) len += 2;
      else { gsm = false; break; }
    }
    if (gsm) return { enc: "GSM-7", len, seg: len <= 160 ? 1 : Math.ceil(len / 153) };
    let units = 0;
    for (const ch of text) units += ch.length; // UTF-16 code units
    return { enc: "Unicode", len: units, seg: units <= 70 ? 1 : Math.ceil(units / 67) };
  };
  const FOOTER = "\nReply STOP to opt out.";
  const updateCounter = (input) => {
    const counter = input.parentElement.querySelector("[data-counter]");
    if (!counter) return;
    let text = input.value.trim();
    if (counter.dataset.footer === "1" && text && !/stop/i.test(text)) text += FOOTER;
    const s = segments(text);
    const max = Number(input.getAttribute("maxlength")) || 480;
    counter.textContent = `${text.length} characters · ${s.seg} SMS segment${s.seg === 1 ? "" : "s"} (${s.enc})` +
      (counter.dataset.footer === "1" ? " · incl. STOP footer" : "");
    counter.classList.toggle("over", text.length > max);
  };

  /* ---------- message list rendering (for live polling) ---------- */
  const pillFor = (m) => {
    const span = document.createElement("span");
    span.dataset.statusPill = "";
    let cls = "pill-wait", label = m.status === "queued_local" ? "sending" : m.status;
    if (m.direction === "inbound") { cls = "pill-in"; label = "received"; }
    else if (["delivered", "read"].includes(m.status)) cls = "pill-ok";
    else if (["failed", "undelivered", "canceled"].includes(m.status)) cls = "pill-bad";
    else if (m.status === "sent") cls = "pill-sent";
    span.className = `pill ${cls}`;
    span.textContent = label;
    return span;
  };
  const el = (tag, cls, text) => {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  };
  const renderMessage = (m) => {
    const li = el("li", "msg");
    li.dataset.messageId = m.id;
    const head = el("div", "msg-head");
    const who = el("span", "msg-who");
    const dir = el("span", `dir ${m.direction === "inbound" ? "dir-in" : "dir-out"}`, m.direction === "inbound" ? "↙" : "↗");
    who.append(dir, document.createTextNode(" " + (m.name || m.phone)));
    if (m.kind === "optin") who.append(el("span", "tag", "consent request"));
    head.append(who, pillFor(m));
    const meta = el("div", "msg-meta");
    const t = el("time", null, fmtTime(m.created_at));
    t.dateTime = m.created_at; t.dataset.localTime = "";
    meta.append(t);
    if (m.name) meta.append(el("span", null, "· " + m.phone));
    if (m.error_code) meta.append(el("span", "err", `· Error ${m.error_code}${m.error_message ? ": " + m.error_message : ""}`));
    li.append(head, el("p", "msg-body", m.body), meta);
    return li;
  };

  const applyStats = (stats) => {
    if (!stats) return;
    $$("[data-stat]").forEach((n) => { if (n.dataset.stat in stats) n.textContent = stats[n.dataset.stat]; });
    const fill = $("[data-meter]");
    if (fill) {
      const pct = Math.min(100, Math.round((stats.sent_today / Math.max(1, stats.daily_limit)) * 100));
      fill.style.setProperty("--pct", pct);
      fill.classList.toggle("hot", pct >= 80);
    }
    const power = $("[data-power]");
    if (power && power.classList.contains("power-on") !== stats.sending_enabled) {
      location.reload(); // START/STOP changed in another tab — refresh controls
    }
  };

  const list = $("[data-message-list]");
  let lastSignature = "";
  const poll = async () => {
    if (!list || document.hidden) return;
    try {
      const res = await fetch(list.dataset.poll, { headers: { Accept: "application/json" }, credentials: "same-origin" });
      if (res.status === 401) { location.href = "/login"; return; }
      if (!res.ok) return;
      const data = await res.json();
      applyStats(data.stats);
      const sig = JSON.stringify(data.messages.map((m) => [m.id, m.status, m.error_code]));
      if (sig === lastSignature) return;
      const previous = new Map($$("[data-message-id]", list).map((li) => [li.dataset.messageId, li.querySelector("[data-status-pill]")?.textContent]));
      lastSignature = sig;
      list.replaceChildren(...(data.messages.length ? data.messages.map(renderMessage) : [el("li", "empty muted", "No messages yet.")]));
      $$("[data-message-id]", list).forEach((li) => {
        const before = previous.get(li.dataset.messageId);
        const now = li.querySelector("[data-status-pill]")?.textContent;
        if (before !== undefined && before !== now) li.classList.add("flash");
        if (before === undefined && previous.size) li.classList.add("flash");
      });
    } catch (_) { /* offline — try again next tick */ }
  };

  const sync = async (btn) => {
    if (!list) return;
    btn?.classList.add("loading");
    try {
      await fetch(list.dataset.syncUrl, { method: "POST", headers: { "X-CSRF-Token": csrf() }, credentials: "same-origin" });
    } catch (_) { /* ignore */ }
    await poll();
    btn?.classList.remove("loading");
  };

  /* ---------- wire up ---------- */
  document.addEventListener("DOMContentLoaded", () => {
    localizeTimes();

    $$("[data-body-input]").forEach((input) => {
      updateCounter(input);
      input.addEventListener("input", () => updateCounter(input));
    });

    const picker = $("[data-template-picker]");
    const bodyInput = $("[data-send-form] [data-body-input]");
    picker?.addEventListener("change", () => {
      const opt = picker.selectedOptions[0];
      if (opt?.dataset.body != null && bodyInput) {
        bodyInput.value = opt.dataset.body;
        updateCounter(bodyInput);
      }
    });

    $$("[data-insert]").forEach((chip) => chip.addEventListener("click", () => {
      const ta = chip.closest("form").querySelector("textarea");
      const start = ta.selectionStart ?? ta.value.length, end = ta.selectionEnd ?? ta.value.length;
      ta.setRangeText(chip.dataset.insert, start, end, "end");
      ta.focus();
      updateCounter(ta);
    }));

    $$("form[data-confirm]").forEach((form) => form.addEventListener("submit", (e) => {
      if (!confirm(form.dataset.confirm)) e.preventDefault();
    }));

    // Stop accidental double-taps from submitting twice (the server enforces this too).
    $$("form").forEach((form) => form.addEventListener("submit", (e) => {
      if (e.defaultPrevented) return;
      const btn = form.querySelector('button[type="submit"]');
      if (btn) setTimeout(() => { btn.disabled = true; btn.classList.add("loading"); }, 0);
    }));

    $$("[data-copy]").forEach((btn) => btn.addEventListener("click", async () => {
      const text = btn.parentElement.querySelector("[data-copy-src]").textContent.trim();
      try { await navigator.clipboard.writeText(text); btn.textContent = "Copied ✓"; }
      catch (_) {
        const range = document.createRange();
        range.selectNodeContents(btn.parentElement.querySelector("[data-copy-src]"));
        getSelection().removeAllRanges(); getSelection().addRange(range);
        btn.textContent = "Selected";
      }
      setTimeout(() => { btn.textContent = "Copy"; }, 1800);
    }));

    $$(".toast").forEach((t) => setTimeout(() => t.classList.add("hide"), 6000));

    const syncBtn = $("[data-sync]");
    syncBtn?.addEventListener("click", () => sync(syncBtn));

    if (list) {
      const statsEl = $("[data-stat='sent_today']");
      if (statsEl) applyStats({
        sent_today: Number(statsEl.textContent),
        daily_limit: Number($("[data-stat='daily_limit']").textContent),
        sending_enabled: $("[data-power]")?.classList.contains("power-on"),
      });
      lastSignature = "";
      setInterval(poll, 5000);
      setInterval(() => sync(), 30000); // falls back to asking Twilio if webhooks are not set up
      document.addEventListener("visibilitychange", () => { if (!document.hidden) poll(); });
    }
  });
})();
