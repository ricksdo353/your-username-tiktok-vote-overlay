/* Control-panel relay shared by the boards and the control panels.
   A command is sent through every route at once and the board keeps the first copy:
     - two free public MQTT brokers over secure WebSocket (no daily quota)
     - ntfy.sh (250 messages a day per internet address)
   so one route being down or over its limit does not stop the panel.
   URL overrides: mqtt=wss://a/mqtt,wss://b/mqtt (or mqtt=off), ctrl=https://ntfy.example (or ctrl=off). */
(function () {
  const P = new URLSearchParams(location.search);
  const NTFY = (P.get("ctrl") || "https://ntfy.sh").replace(/\/$/, "");
  const useNtfy = P.get("ctrl") !== "off";
  const BROKERS = P.get("mqtt") === "off" ? [] :
    (P.get("mqtt") || "wss://broker.emqx.io:8084/mqtt,wss://broker.hivemq.com:8884/mqtt").split(",").map((s) => s.trim()).filter(Boolean);
  const mtopic = (t) => "tiktok-live-overlay/" + t;
  let clients = null;
  function getClients() {
    if (clients) return clients;
    clients = typeof mqtt === "undefined" ? [] : BROKERS.map((url) => {
      try {
        const c = mqtt.connect(url, { clientId: "tvo_" + Math.random().toString(16).slice(2, 12), clean: true, reconnectPeriod: 3000, connectTimeout: 8000, keepalive: 30 });
        c.on("error", () => {});
        return c;
      } catch (_) { return null; }
    }).filter(Boolean);
    return clients;
  }
  const newId = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
  function parse(raw) {
    const s = String(raw), i = s.indexOf("|");
    if (i > 0 && i <= 24 && /^[a-z0-9]+$/.test(s.slice(0, i))) return { id: s.slice(0, i), cmd: s.slice(i + 1) };
    return { id: null, cmd: s };
  }

  window.Relay = {
    // onCmd(text) for every new command; onStatus(true|false) = is any route connected
    listen(topic, onCmd, onStatus) {
      const seen = new Set(), up = {};
      const report = () => onStatus && onStatus(Object.values(up).some(Boolean));
      // tell the control panel "a board is here" (heartbeat) and "I ran command X" (ack)
      const pub = (sub, msg) => getClients().forEach((c) => { if (c.connected) c.publish(mtopic(topic) + "/" + sub, msg, { qos: 0 }); });
      const beat = () => pub("hb", JSON.stringify({ t: Date.now(), page: location.pathname.split("/").pop() || "index.html" }));
      setInterval(beat, 4000);
      const deliver = (raw, fallbackId) => {
        const m = parse(raw), key = m.id || (fallbackId ? "n:" + fallbackId : null);
        if (key) { if (seen.has(key)) return; seen.add(key); if (seen.size > 500) seen.delete(seen.values().next().value); }
        onCmd(m.cmd);
        if (m.id) pub("ack", m.id);
      };
      getClients().forEach((c, k) => {
        up["m" + k] = false;
        c.on("connect", () => { up["m" + k] = true; c.subscribe(mtopic(topic)); report(); beat(); });
        c.on("close", () => { up["m" + k] = false; report(); });
        c.on("message", (t, payload) => { if (t === mtopic(topic)) deliver(payload.toString(), null); });
      });
      if (useNtfy) {
        up.n = false;
        try {
          const es = new EventSource(`${NTFY}/${encodeURIComponent(topic)}/sse`);
          es.onopen = () => { up.n = true; report(); };
          es.onerror = () => { up.n = false; report(); };
          es.onmessage = (e) => {
            try { const m = JSON.parse(e.data); if (m.event && m.event !== "message") return; if (m.message) deliver(m.message, m.id); } catch (_) { /* ignore */ }
          };
        } catch (_) { /* no EventSource */ }
      }
      report();
    },
    // resolves "ok" as soon as one route accepted the command, otherwise "limit" (ntfy quota, nothing else worked) or "fail"
    send(topic, cmd, onId) {
      const id = newId(), payload = id + "|" + cmd;
      if (onId) onId(id);
      const tries = [];
      getClients().forEach((c) => tries.push(new Promise((res) => {
        const go = () => c.publish(mtopic(topic), payload, { qos: 0 }, (err) => res(err ? "fail" : "ok"));
        if (c.connected) return go();
        const t = setTimeout(() => res("fail"), 6000);
        c.once("connect", () => { clearTimeout(t); go(); });
      })));
      if (useNtfy) tries.push(fetch(`${NTFY}/${encodeURIComponent(topic)}`, { method: "POST", body: payload })
        .then((r) => (r.ok ? "ok" : r.status === 429 ? "limit" : "fail")).catch(() => "fail"));
      if (!tries.length) return Promise.resolve("fail");
      return new Promise((resolve) => {
        let left = tries.length, limit = false;
        tries.forEach((p) => p.then((r) => {
          if (r === "ok") return resolve("ok");
          if (r === "limit") limit = true;
          if (--left === 0) resolve(limit ? "limit" : "fail");
        }));
      });
    },
    // control panel: follow a room's board. onBeat(info) on each heartbeat, onAck(id) when the board ran a command.
    // mqttUp() says whether this panel can see the relay at all (if not, board status is unknown).
    watch(topic, onBeat, onAck) {
      const hb = mtopic(topic) + "/hb", ack = mtopic(topic) + "/ack";
      getClients().forEach((c) => {
        const sub = () => c.subscribe([hb, ack]);
        if (c.connected) sub();
        c.on("connect", sub);
        c.on("message", (t, payload) => {
          if (t === hb) { try { onBeat(JSON.parse(payload.toString())); } catch (_) { onBeat({}); } }
          else if (t === ack) onAck(payload.toString());
        });
      });
    },
    unwatch(topic) {
      getClients().forEach((c) => { try { c.unsubscribe([mtopic(topic) + "/hb", mtopic(topic) + "/ack"]); } catch (_) {} });
    },
    mqttUp() { return getClients().some((c) => c.connected); },
    // open the connections early (control panels call this on load so the first tap is fast)
    warm() { getClients(); },
  };
})();
