/* =========================================================
   TikTok LIVE Vote Overlay
   ---------------------------------------------------------
   Configure with URL parameters, e.g.
   index.html?left=Goku&right=Naruto&leftImg=goku.png&rightImg=naruto.png
             &ws=ws://localhost:21213/&giftA=Rose&giftB=TikTok

   left / right       character names
   leftImg / rightImg image URL or local file (put files next to index.html)
   q                  title text (default "WHO WINS?")
   hint               text under the title (default "Comment 1 or 2 · Gifts = bonus votes")
   leftPos / rightPos which part of the photo to show, CSS object-position
                      (default "center 20%", keeps faces in frame)
   ws                 WebSocket event source (default ws://localhost:21213/,
                      which is TikFinity's local API; use ws://localhost:8080
                      for the included server.js relay). ws=off disables it.
   giftA / giftB      gift names that always count for side A / side B
                      (comma-separated for several, e.g. giftA=Rose,Finger%20Heart).
                      Other gifts count for the side the viewer commented.
   giftMult           votes per diamond (default 1)
   likes              votes per like, e.g. likes=0.1 (default 0 = off)
   cooldown           ms between comment votes from the same viewer (default 2000)
   room               remote-control room name; open control.html?room=SAME to control
   host               your TikTok username: you can type !start !pause !reset
                      !end !timer 5:00 in your own LIVE chat
   preview=1          dark background for testing in a normal browser
   demo=1             fake random votes
   timer              round length: seconds (timer=90) or m:ss (timer=2:30).
                      Omit for no timer. When it hits 0, voting locks and
                      the winner is shown.
   autostart=0        don't start the timer on load (press T to start)

   Keyboard (when the overlay window is focused):
   1 / 2 = +1 vote,  Shift+1 / Shift+2 = +10,  R = reset,  D = toggle demo
   T = start / restart timer,  Space = pause / resume,
   [ / ] = -15s / +15s,  Shift+[ / Shift+] = -1min / +1min
   ========================================================= */

(() => {
  const P = new URLSearchParams(location.search);
  const cfg = {
    left: P.get("left") || "Player One",
    right: P.get("right") || "Player Two",
    leftImg: P.get("leftImg") || "",
    rightImg: P.get("rightImg") || "",
    question: P.get("q") || "WHO WINS?",
    hint: P.get("hint") || "",
    leftPos: P.get("leftPos") || "",
    rightPos: P.get("rightPos") || "",
    ws: P.get("ws") || "ws://localhost:21213/",
    // comma-separated gift names, e.g. giftA=Rose,Finger Heart
    giftA: (P.get("giftA") || "").split(",").map((g) => g.trim()).filter(Boolean),
    giftB: (P.get("giftB") || "").split(",").map((g) => g.trim()).filter(Boolean),
    giftMult: parseFloat(P.get("giftMult") || "1"),
    likes: parseFloat(P.get("likes") || "0"),
    cooldown: parseInt(P.get("cooldown") || "2000", 10),
    room: P.get("room") || "",                       // remote control room (control.html)
    ctrl: (P.get("ctrl") || "https://ntfy.sh").replace(/\/$/, ""),
    host: (P.get("host") || "").replace(/^@/, "").toLowerCase(), // your TikTok username for !commands
  };

  const $ = (id) => document.getElementById(id);
  const state = { a: 0, b: 0 };
  const lastVote = new Map();   // viewer -> timestamp
  const viewerSide = new Map(); // viewer -> 'a' | 'b' (used to route their gifts)
  const likeCarry = { a: 0, b: 0 };

  /* ---------- Fit 1080x1920 stage into the window ---------- */
  function fit() {
    const s = Math.min(innerWidth / 1080, innerHeight / 1920);
    $("stage").style.transform = `translate(-50%, -50%) scale(${s})`;
  }
  addEventListener("resize", fit);
  fit();
  if (P.get("preview") === "1") document.body.classList.add("preview");

  /* ---------- Placeholder avatars (no internet needed) ---------- */
  function placeholder(letter, c1, c2) {
    const svg = `<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 200 200'>
      <defs><linearGradient id='g' x1='0' y1='0' x2='1' y2='1'>
      <stop offset='0' stop-color='${c1}'/><stop offset='1' stop-color='${c2}'/></linearGradient></defs>
      <rect width='200' height='200' fill='url(#g)'/>
      <circle cx='100' cy='78' r='38' fill='rgba(255,255,255,.85)'/>
      <path d='M30 190c8-46 38-70 70-70s62 24 70 70z' fill='rgba(255,255,255,.85)'/>
      <text x='100' y='92' font-size='44' font-family='Arial Black,Arial' font-weight='900'
        text-anchor='middle' fill='${c2}'>${letter}</text></svg>`;
    return "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
  }

  /* ---------- Init UI ---------- */
  $("question").textContent = cfg.question;
  if (cfg.hint) $("hint").textContent = cfg.hint;
  // show each side's gift on its card
  if (cfg.giftA.length) $("giftTagA").textContent = "🎁 " + cfg.giftA.join(" / ");
  if (cfg.giftB.length) $("giftTagB").textContent = "🎁 " + cfg.giftB.join(" / ");
  $("giftTagA").classList.toggle("hidden", !cfg.giftA.length);
  $("giftTagB").classList.toggle("hidden", !cfg.giftB.length);
  if (cfg.leftPos) $("imgA").style.objectPosition = cfg.leftPos;
  if (cfg.rightPos) $("imgB").style.objectPosition = cfg.rightPos;
  $("nameA").textContent = cfg.left;
  $("nameB").textContent = cfg.right;
  $("imgA").src = cfg.leftImg || placeholder("1", "#5fd0ff", "#1456c9");
  $("imgB").src = cfg.rightImg || placeholder("2", "#d17bff", "#4b14b5");
  $("imgA").onerror = () => ($("imgA").src = placeholder("1", "#5fd0ff", "#1456c9"));
  $("imgB").onerror = () => ($("imgB").src = placeholder("2", "#d17bff", "#4b14b5"));

  /* ---------- Rendering ---------- */
  const fmt = (n) => (n >= 1e6 ? (n / 1e6).toFixed(1) + "M" : n >= 1e4 ? (n / 1e3).toFixed(1) + "K" : String(Math.floor(n)));

  function render() {
    const total = state.a + state.b;
    const pa = total ? Math.round((state.a / total) * 100) : 50;
    const pb = 100 - pa;
    $("scoreA").textContent = fmt(state.a);
    $("scoreB").textContent = fmt(state.b);
    // keep a sliver of each colour visible so labels never vanish
    $("barA").style.width = Math.min(Math.max(pa, 15), 85) + "%";
    $("barB").style.width = Math.min(Math.max(pb, 15), 85) + "%";
    $("pctA").textContent = pa + "%";
    $("pctB").textContent = pb + "%";
    $("cardA").classList.toggle("leading", state.a > state.b);
    $("cardB").classList.toggle("leading", state.b > state.a);
  }

  function bump(side) {
    const el = $(side === "a" ? "cardA" : "cardB");
    el.classList.remove("bump");
    void el.offsetWidth;
    el.classList.add("bump");
    setTimeout(() => el.classList.remove("bump"), 150);
  }

  function feed(text, side) {
    const box = $("feed");
    const div = document.createElement("div");
    div.className = "item " + side;
    div.textContent = text;
    box.appendChild(div);
    while (box.children.length > 5) box.removeChild(box.firstChild);
    setTimeout(() => div.remove(), 6000);
  }

  /* ---------- Round timer ---------- */
  function parseTime(v) {
    if (!v) return 0;
    if (v.includes(":")) { const [m, s] = v.split(":"); return (parseInt(m, 10) || 0) * 60 + (parseInt(s, 10) || 0); }
    return parseInt(v, 10) || 0;
  }
  const timer = {
    duration: parseTime(P.get("timer")), // seconds; 0 = no timer
    remaining: 0, running: false, ended: false, endAt: 0, tickId: null,
  };
  timer.remaining = timer.duration;

  const mmss = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;

  function drawTimer() {
    const el = $("timer");
    el.classList.toggle("hidden", timer.duration <= 0 && !timer.running);
    $("timerText").textContent = timer.ended ? "0:00" : mmss(Math.ceil(timer.remaining));
    el.classList.toggle("paused", !timer.running && !timer.ended);
    el.classList.toggle("urgent", timer.running && timer.remaining <= 10);
    el.classList.toggle("done", timer.ended);
  }

  function tick() {
    timer.remaining = Math.max(0, (timer.endAt - Date.now()) / 1000);
    if (timer.remaining <= 0) finishRound();
    drawTimer();
  }

  function startTimer(seconds) {
    if (seconds != null) timer.duration = seconds;
    if (timer.duration <= 0) return;
    timer.remaining = timer.duration;
    timer.ended = false;
    $("winner").classList.add("hidden");
    resume();
  }
  function resume() {
    if (timer.ended || timer.remaining <= 0) return;
    timer.running = true;
    timer.endAt = Date.now() + timer.remaining * 1000;
    clearInterval(timer.tickId);
    timer.tickId = setInterval(tick, 200);
    drawTimer();
  }
  function pause() {
    if (!timer.running) return;
    tick();
    timer.running = false;
    clearInterval(timer.tickId);
    drawTimer();
  }
  function adjust(delta) {
    if (timer.ended) return;
    if (timer.running) { timer.endAt = Math.max(Date.now() + 1000, timer.endAt + delta * 1000); tick(); }
    else {
      // before the round starts, [ / ] change the chosen duration
      // (when paused mid-round they only change the time left)
      const fresh = timer.remaining === timer.duration;
      timer.remaining = Math.max(5, timer.remaining + delta);
      if (fresh) timer.duration = timer.remaining;
    }
    drawTimer();
  }
  function finishRound() {
    timer.running = false;
    timer.ended = true;
    timer.remaining = 0;
    clearInterval(timer.tickId);
    if (demoTimer) toggleDemo();
    const w = $("winner");
    w.classList.remove("hidden", "a", "b");
    if (state.a === state.b) {
      $("winnerName").textContent = "IT'S A TIE!";
    } else {
      const side = state.a > state.b ? "a" : "b";
      w.classList.add(side);
      $("winnerName").textContent = `🏆 ${side === "a" ? cfg.left : cfg.right}`;
    }
    drawTimer();
  }

  function add(side, n = 1, label) {
    if (side !== "a" && side !== "b") return;
    if (timer.ended) return; // round over: votes locked
    state[side] += n;
    render();
    bump(side);
    if (label) feed(label, side);
  }

  function reset() {
    state.a = state.b = 0;
    lastVote.clear();
    viewerSide.clear();
    render();
    // reset the timer too: back to full length, stopped (T starts it)
    clearInterval(timer.tickId);
    timer.running = false;
    timer.ended = false;
    timer.remaining = timer.duration;
    $("winner").classList.add("hidden");
    drawTimer();
  }

  /* ---------- TikTok event handling ---------- */
  // Accepts both {event, data} (TikFinity / server.js) and flat objects.
  function handle(msg) {
    const type = (msg.event || msg.type || "").toLowerCase();
    const d = msg.data || msg;
    const user = d.nickname || d.uniqueId || d.user?.nickname || d.user?.uniqueId || "viewer";
    const id = d.uniqueId || d.userId || d.user?.uniqueId || user;

    if (type === "chat" || type === "comment") {
      const text = String(d.comment || d.text || "").trim().toLowerCase();
      if (cfg.host && text.startsWith("!") && String(d.uniqueId || d.user?.uniqueId || "").toLowerCase() === cfg.host) {
        command(text.slice(1));
        return;
      }
      let side = null;
      if (/^(1|a|team ?1)\b/.test(text) || text === cfg.left.toLowerCase()) side = "a";
      else if (/^(2|b|team ?2)\b/.test(text) || text === cfg.right.toLowerCase()) side = "b";
      if (!side) return;
      viewerSide.set(id, side);
      const now = Date.now();
      if (now - (lastVote.get(id) || 0) < cfg.cooldown) return;
      lastVote.set(id, now);
      add(side, 1);
    }

    else if (type === "gift") {
      // Streakable gifts send many events; count only the final one.
      if (d.giftType === 1 && d.repeatEnd === false) return;
      const name = String(d.giftName || d.extendedGiftInfo?.name || "").toLowerCase();
      let side = viewerSide.get(id) || null;
      if (cfg.giftA.some((g) => g.toLowerCase() === name)) side = "a";
      if (cfg.giftB.some((g) => g.toLowerCase() === name)) side = "b";
      if (!side) return; // viewer hasn't picked a side yet
      const diamonds = (d.diamondCount || 1) * (d.repeatCount || 1);
      const votes = Math.max(1, Math.round(diamonds * cfg.giftMult));
      add(side, votes, `🎁 ${user} +${votes} → ${side === "a" ? cfg.left : cfg.right}`);
    }

    else if (type === "like" && cfg.likes > 0) {
      const side = viewerSide.get(id);
      if (!side) return;
      likeCarry[side] += (d.likeCount || 1) * cfg.likes;
      const whole = Math.floor(likeCarry[side]);
      if (whole > 0) { likeCarry[side] -= whole; add(side, whole); }
    }
  }

  /* ---------- WebSocket connection with auto-reconnect ---------- */
  function connect() {
    if (!cfg.ws || cfg.ws === "off") return;
    const status = $("status");
    let ws;
    try { ws = new WebSocket(cfg.ws); } catch (e) { return setTimeout(connect, 3000); }
    ws.onopen = () => { status.textContent = "● connected"; status.classList.add("on"); };
    ws.onmessage = (e) => {
      try { handle(JSON.parse(e.data)); } catch (_) { /* ignore non-JSON */ }
    };
    ws.onclose = () => {
      status.textContent = "reconnecting…"; status.classList.remove("on");
      setTimeout(connect, 3000);
    };
    ws.onerror = () => ws.close();
  }

  /* ---------- Test controls ---------- */
  let demoTimer = null;
  function toggleDemo() {
    if (demoTimer) { clearInterval(demoTimer); demoTimer = null; return; }
    demoTimer = setInterval(() => {
      const side = Math.random() < 0.5 ? "a" : "b";
      if (Math.random() < 0.08) handle({ event: "gift", data: { nickname: "fan" + ((Math.random() * 99) | 0), uniqueId: "demo" + side, giftName: "Rose", diamondCount: 5, repeatCount: 1 } });
      else { viewerSide.set("demo" + side, side); add(side, 1); }
    }, 250);
  }

  addEventListener("keydown", (e) => {
    if (e.code === "Digit1") add("a", e.shiftKey ? 10 : 1);
    else if (e.code === "Digit2") add("b", e.shiftKey ? 10 : 1);
    else if (e.key === "r" || e.key === "R") reset();
    else if (e.key === "d" || e.key === "D") toggleDemo();
    else if (e.key === "t" || e.key === "T") startTimer(timer.duration > 0 ? timer.duration : 60);
    else if (e.code === "Space") { e.preventDefault(); timer.running ? pause() : resume(); }
    else if (e.code === "BracketLeft") adjust(e.shiftKey ? -60 : -15);
    else if (e.code === "BracketRight") adjust(e.shiftKey ? 60 : 15);
  });

  /* ---------- Remote commands (control panel + host chat) ----------
     start [m:ss] | pause | resume | toggle | reset | end
     timer m:ss (set length without starting) | adjust ±sec
     add a|b n | sub a|b n | demo                                     */
  function command(text) {
    const [c, x, y] = String(text).trim().toLowerCase().split(/\s+/);
    const side = x === "b" || x === "2" ? "b" : "a";
    switch (c) {
      case "start":  startTimer(x ? parseTime(x) : (timer.duration > 0 ? timer.duration : 60)); break;
      case "pause":  pause(); break;
      case "resume": resume(); break;
      case "toggle": timer.running ? pause() : resume(); break;
      case "reset":  reset(); break;
      case "end":    if (timer.running || timer.duration > 0) finishRound(); break;
      case "timer":
        timer.duration = Math.max(0, parseTime(x || "0"));
        if (!timer.running) { timer.remaining = timer.duration; timer.ended = false; $("winner").classList.add("hidden"); }
        drawTimer(); break;
      case "adjust": adjust(parseInt(x, 10) || 0); break;
      case "add":    add(side, Math.max(1, parseInt(y, 10) || 1)); break;
      case "sub":    if (!timer.ended) { state[side] = Math.max(0, state[side] - Math.max(1, parseInt(y, 10) || 1)); render(); } break;
      case "demo":   toggleDemo(); break;
    }
  }

  // Control panel channel: control.html publishes to ntfy.sh/<topic>, we listen via SSE
  function listenControl() {
    if (!cfg.room) return;
    const seen = new Set();
    const es = new EventSource(`${cfg.ctrl}/tvo-${encodeURIComponent(cfg.room)}/sse`);
    es.onmessage = (e) => {
      try {
        const m = JSON.parse(e.data);
        if (m.event && m.event !== "message") return;
        if (m.id) { if (seen.has(m.id)) return; seen.add(m.id); }
        if (m.message) command(m.message);
      } catch (_) { /* ignore */ }
    };
  }

  // Public hooks for other scripts / tools
  window.Vote = { add, reset, handle, state, command, timer: { start: startTimer, pause, resume, adjust, state: timer } };

  render();
  drawTimer();
  if (timer.duration > 0 && P.get("autostart") !== "0") startTimer();
  connect();
  listenControl();
  if (P.get("demo") === "1") toggleDemo();
})();
