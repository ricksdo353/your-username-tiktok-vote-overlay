/* =========================================================
   TikTok LIVE Country Race (4 cars) – battle.html
   Viewers join a team by commenting its number (1-4). Every comment, like and
   gift from a team member pushes that team's runner toward the finish line.
   First team to the goal wins (or the leader when the timer runs out); the
   winner is shown, then everything resets and a new round starts by itself.

   URL parameters (all optional):
   t1 t2 t3 t4        team names (default ישראל, פלסטין, ארה״ב, איראן)
   flag1 … flag4      flag picture URL for a team (flagN=none hides it); a renamed
                      team has no flag unless you give one
   goal               points to win (default 1000; goal=0 = no goal, timer only)
   timer              round length, seconds or m:ss (default none)
   next               seconds the winner is shown before a new round starts
                      by itself (default 15; next=0 = off)
   chat               points per comment of the team number (default 1)
   cooldown           ms between counted comments from one viewer (default 2000)
   likes              points per like (default 0.1 = 10 likes are 1 point; 0 = off)
   giftMult           points per coin (default 1)
   gift1 … gift4      gift names that always go to that team, e.g. gift1=Rose
   room / host / ws / bg / bigGift / takeover / countdown / autostart / preview /
   demo / debug       same as the vote board (index.html)

   Keyboard: 1-4 = +1 (Shift = +10), R = reset, T = new round, Space = pause,
             D = demo, [ / ] = -15s / +15s
   ========================================================= */

(() => {
  const P = new URLSearchParams(location.search);
  const num = (v, def = 0) => { const n = Number(v); return Number.isFinite(n) ? n : def; };
  const cfg = {
    names: [1, 2, 3, 4].map((i, k) => P.get("t" + i) || ["ישראל", "פלסטין", "ארה״ב", "איראן"][k]),
    flags: [1, 2, 3, 4].map((i) => P.get("flag" + i)),
    imgs: [1, 2, 3, 4].map((i) => P.get("img" + i) || ""),
    gifts: [1, 2, 3, 4].map((i) => (P.get("gift" + i) || "").split(",").map((g) => g.trim().toLowerCase()).filter(Boolean)),
    goal: Math.max(0, Math.floor(num(P.get("goal") ?? 1000, 1000))),
    next: Math.max(0, Math.floor(num(P.get("next") ?? 15, 15))),
    chat: Math.max(0, num(P.get("chat") ?? 1, 1)),
    cooldown: Math.max(0, num(P.get("cooldown") ?? 2000, 2000)),
    likes: Math.max(0, num(P.get("likes") ?? 0.1, 0.1)),
    giftMult: Math.max(0, num(P.get("giftMult") ?? 1, 1)),
    ws: P.get("ws") || "ws://127.0.0.1:21213/",
    room: P.get("room") || "",
    ctrl: (P.get("ctrl") || "https://ntfy.sh").replace(/\/$/, ""),
    host: (P.get("host") || "").replace(/^@/, "").toLowerCase(),
    bg: P.get("bg") || "full",
    bigGift: num(P.get("bigGift") ?? 100, 100),
    takeover: P.get("takeover") !== "0",
    countdown: P.get("countdown") !== "0",
  };
  const COL = [["#2f8bff", "#1456c9"], ["#1fa055", "#0d6b37"], ["#e0283c", "#9c1224"], ["#ff8a1f", "#b85a00"]];
  // Flags drawn here (public-domain designs) so they show everywhere, even where flag emoji don't (Windows / LIVE Studio)
  const svgUri = (w, h, body) => "data:image/svg+xml;charset=utf-8," + encodeURIComponent(`<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 ${w} ${h}' preserveAspectRatio='xMidYMid slice'>${body}</svg>`);
  const usStars = (() => { let d = ""; for (let r = 0; r < 9; r++) for (let k = 0; k < (r % 2 ? 5 : 6); k++) d += `<circle cx='${(r % 2 ? 12.6 : 6.3) + k * 12.6}' cy='${5.4 + r * 5.4}' r='2.1'/>`; return d; })();
  const FLAGS = [
    svgUri(220, 160, "<rect width='220' height='160' fill='#fff'/><rect y='15' width='220' height='25' fill='#0038b8'/><rect y='120' width='220' height='25' fill='#0038b8'/>" +
      "<g fill='none' stroke='#0038b8' stroke-width='5.5'><path d='M110 50L136 95H84Z'/><path d='M110 110L136 65H84Z'/></g>"),
    svgUri(300, 150, "<rect width='300' height='50' fill='#000'/><rect y='50' width='300' height='50' fill='#fff'/><rect y='100' width='300' height='50' fill='#149954'/><path d='M0 0L100 75L0 150Z' fill='#e4312b'/>"),
    svgUri(190, 100, Array.from({ length: 13 }, (_, r) => `<rect y='${(r * 100 / 13).toFixed(2)}' width='190' height='${(100 / 13).toFixed(2)}' fill='${r % 2 ? "#fff" : "#b22234"}'/>`).join("") +
      `<rect width='76' height='53.85' fill='#3c3b6e'/><g fill='#fff'>${usStars}</g>`),
    svgUri(630, 360, "<rect width='630' height='120' fill='#239f40'/><rect y='120' width='630' height='120' fill='#fff'/><rect y='240' width='630' height='120' fill='#da0000'/>" +
      "<g fill='none' stroke='#da0000' stroke-width='9' stroke-linecap='round'><path d='M315 140v80'/><path d='M298 150q-26 30 0 62'/><path d='M332 150q26 30 0 62'/>" +
      "<path d='M282 138q-46 46 2 92'/><path d='M348 138q46 46-2 92'/></g>"),
  ];
  cfg.flags = cfg.flags.map((f, i) => (f === "none" ? "" : f || (P.get("t" + (i + 1)) ? "" : FLAGS[i])));
  const CAR_W = 190;
  const carSvg = (i, flag) => `<svg viewBox="0 0 190 84" aria-hidden="true">
    <ellipse cx="96" cy="80" rx="88" ry="5" fill="rgba(0,0,0,.45)"/>
    <path class="flame" d="M184 46 L214 40 L204 50 L222 56 L184 58 Z" fill="#ffb02e"/>
    <path d="M6 60 Q4 44 20 40 L54 34 Q72 14 100 12 L132 12 Q154 14 166 32 L178 36 Q190 40 188 60 Z" fill="${COL[i][0]}" stroke="#fff" stroke-width="3"/>
    <path d="M6 60 L188 60 L186 52 L8 52 Z" fill="${COL[i][1]}"/>
    <path d="M62 34 Q76 21 98 19 L104 19 L104 34 Z M110 19 L128 19 Q142 21 152 34 L110 34 Z" fill="#0b1530" opacity=".88"/>
    <ellipse cx="13" cy="46" rx="6" ry="4" fill="#fff6c0"/><rect x="180" y="40" width="7" height="8" rx="2" fill="#ff2d2d"/>
    ${flag ? `<image href="${flag}" x="112" y="37" width="40" height="24" preserveAspectRatio="xMidYMid slice"/><rect x="112" y="37" width="40" height="24" fill="none" stroke="#fff" stroke-width="2"/>` : ""}
    <circle cx="80" cy="46" r="11" fill="#fff"/><text x="80" y="51.5" text-anchor="middle" font-size="16" font-weight="900" font-family="Heebo, Arial" fill="${COL[i][1]}">${i + 1}</text>
    <g class="wheel"><circle cx="46" cy="62" r="17" fill="#111"/><circle cx="46" cy="62" r="8" fill="#c9c9d6"/><path d="M46 47v30M31 62h30" stroke="#555" stroke-width="3"/></g>
    <g class="wheel"><circle cx="150" cy="62" r="17" fill="#111"/><circle cx="150" cy="62" r="8" fill="#c9c9d6"/><path d="M150 47v30M135 62h30" stroke="#555" stroke-width="3"/></g>
  </svg>`;
  const $ = (id) => document.getElementById(id);
  const esc = (x) => String(x).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const fmt = (n) => Math.floor(n).toLocaleString("en-US");
  const anim = (el, frames, opts) => { try { return el.animate(frames, opts); } catch (_) { return null; } };
  const DEBUG = P.get("debug") === "1";

  const pts = [0, 0, 0, 0];
  const members = new Map();  // viewer id -> team index
  const contrib = new Map();  // viewer id -> { name, team, pts }
  const lastChat = new Map();
  const likeCarry = [0, 0, 0, 0];
  const round = { running: false, ended: false };

  /* ---------- stage ---------- */
  function fit() { const s = Math.min(innerWidth / 1080, innerHeight / 1920); $("stage").style.transform = `translate(-50%, -50%) scale(${s})`; }
  addEventListener("resize", fit); fit();
  if (P.get("preview") === "1") document.body.classList.add("preview");
  document.body.classList.add("bg-" + (["full", "panel", "none"].includes(cfg.bg) ? cfg.bg : "full"));
  (function dots() {
    let seed = 7; const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
    const cols = ["#5fd0ff", "#d17bff", "#ffffff", "#ff7bc0"];
    for (let i = 0; i < 26; i++) {
      const d = document.createElement("i"), sz = [6, 8, 10, 14][(rnd() * 4) | 0];
      d.style.cssText = `left:${(20 + rnd() * 1040) | 0}px;top:${(rnd() * 1920) | 0}px;width:${sz}px;height:${sz}px;` +
        `background:${cols[(rnd() * 4) | 0]};opacity:${(0.25 + rnd() * 0.45).toFixed(2)};animation-duration:${(20 + rnd() * 25).toFixed(1)}s`;
      $("dots").appendChild(d);
    }
  })();
  setInterval(() => { $("title").classList.toggle("off"); $("hint").classList.toggle("off"); }, 5000);

  /* ---------- lanes ---------- */
  const lanes = cfg.names.map((name, i) => {
    const el = document.createElement("div");
    el.className = "lane";
    el.style.top = i * 200 + "px";
    el.style.setProperty("--c", COL[i][0]); el.style.setProperty("--c2", COL[i][1]);
    const flag = cfg.imgs[i] || cfg.flags[i];
    if (!flag) el.classList.add("noflag");
    el.innerHTML = `<div class="badge">${i + 1}</div><div class="crown">👑</div>${flag ? '<img class="flag" alt="">' : ""}
      <div class="tname"></div><div class="members">👥 <span class="mc">0</span></div><div class="pts">0</div>
      <div class="road"><div class="fill"></div><div class="dash"></div><div class="flash"></div><div class="finish"></div></div>
      <div class="car">${carSvg(i, flag)}</div>`;
    el.querySelector(".tname").textContent = name;
    if (flag) el.querySelector(".flag").src = flag;
    const runner = el.querySelector(".car");
    $("lanes").appendChild(el);
    return { el, runner, fill: el.querySelector(".fill"), flash: el.querySelector(".flash"), pts: el.querySelector(".pts"), mc: el.querySelector(".mc") };
  });

  function teamSize(i) { let n = 0; members.forEach((t) => { if (t === i) n++; }); return n; }
  function progress(i) {
    if (cfg.goal > 0) return Math.min(1, pts[i] / cfg.goal);
    const max = Math.max(...pts);
    return max > 0 ? (pts[i] / max) * 0.92 : 0;
  }
  function render() {
    const max = Math.max(...pts), leaders = pts.filter((p) => p === max).length;
    lanes.forEach((l, i) => {
      const p = progress(i);
      l.fill.style.width = (p * 100).toFixed(2) + "%";
      l.runner.style.right = (p * (900 - CAR_W)).toFixed(1) + "px";
      l.pts.textContent = fmt(pts[i]);
      l.mc.textContent = teamSize(i);
      l.el.classList.toggle("lead", max > 0 && leaders === 1 && pts[i] === max);
      l.el.classList.toggle("hot", cfg.goal > 0 && p >= 0.8 && !round.ended);
    });
  }
  function drawRules() {
    $("rules").innerHTML = cfg.goal > 0
      ? `🏁 הראשונים ל־<b class="ltr">${fmt(cfg.goal)}</b> מנצחים · 🎁 מתנה = נקודות`
      : `⏱ המובילים בסוף הזמן מנצחים · 🎁 מתנה = נקודות`;
    const r = $("rules"); r.style.fontSize = "40px";
    for (let fs = 40; fs > 28 && r.scrollWidth > r.clientWidth; fs -= 2) r.style.fontSize = fs + "px";
  }

  /* ---------- effects ---------- */
  function bump(i, strong) {
    anim(lanes[i].runner, [{ transform: "translateX(0) scale(1)" }, { transform: `translateX(${strong ? -26 : -12}px) scale(${strong ? 1.12 : 1.05})` }, { transform: "translateX(0) scale(1)" }], { duration: 260, easing: "ease-out" });
    anim(lanes[i].runner.querySelector(".flame"), [{ opacity: 1 }, { opacity: 0 }], { duration: strong ? 600 : 300, easing: "ease-out" });
    anim(lanes[i].flash, [{ opacity: 0.5 }, { opacity: 0 }], { duration: 350, easing: "ease-out" });
  }
  function shake(el, amp = 14) {
    anim(el, [{ transform: "translate(0,0)" }, { transform: `translate(${-amp}px,${amp / 2}px)` }, { transform: `translate(${amp - 2}px,${-amp / 2}px)` },
      { transform: `translate(${-amp / 2}px,4px)` }, { transform: "translate(0,0)" }], { duration: 220 });
  }
  const laneY = (i) => 448 + i * 200 + 138; // centre of the car
  const runnerX = (i) => 40 + 900 - progress(i) * (900 - CAR_W) - CAR_W / 2;
  let lastFly = 0;
  function flyVote(i) {
    const now = Date.now();
    if (now - lastFly < 200) return;
    lastFly = now;
    const b = document.createElement("div");
    b.className = "fly-vote"; b.textContent = i + 1; b.style.background = COL[i][0];
    const x0 = 140 + i * 220, y0 = 1420;
    b.style.left = x0 + "px"; b.style.top = y0 + "px";
    $("flyLayer").appendChild(b);
    const dx = runnerX(i) - 58 - x0, dy = laneY(i) - 58 - y0;
    anim(b, [{ transform: "translate(0,0) scale(.6)", opacity: 0 }, { transform: "translate(0,-30px) scale(1)", opacity: 1, offset: 0.2 },
      { transform: `translate(${dx}px,${dy}px) scale(.55)`, opacity: 1, offset: 0.92 }, { transform: `translate(${dx}px,${dy}px) scale(.3)`, opacity: 0 }],
      { duration: 520, easing: "ease-in" });
    setTimeout(() => b.remove(), 560);
  }
  function flyGift(i, icon) {
    if (!icon) return;
    const img = document.createElement("img");
    img.className = "fly-gift"; img.alt = ""; img.src = icon;
    img.style.left = "1100px"; img.style.top = laneY(i) - 130 + "px"; img.style.filter = `drop-shadow(0 0 30px ${COL[i][0]})`;
    $("flyLayer").appendChild(img);
    const dx = runnerX(i) - 130 - 1100;
    anim(img, [{ transform: "translate(0,0) scale(1.3)", opacity: 0 }, { transform: "translate(0,0) scale(1.3)", opacity: 1, offset: 0.15 },
      { transform: `translate(${dx}px,0) scale(.45)`, opacity: 1, offset: 0.9 }, { transform: `translate(${dx}px,0) scale(.45)`, opacity: 0 }], { duration: 450, easing: "ease-in" });
    setTimeout(() => { img.remove(); bump(i, true); }, 460);
  }
  let tkTimer = null;
  function takeover(i, icon, n) {
    if (!cfg.takeover) return;
    const t = $("takeover");
    t.className = "abs";
    t.style.background = `radial-gradient(circle at 50% 45%, ${COL[i][0]}, ${COL[i][1]} 45%, #07031a 80%)`;
    $("tkVal").textContent = "+" + fmt(n);
    $("tkImg").src = icon || ""; $("tkImg").style.visibility = icon ? "visible" : "hidden";
    $("tkName").textContent = "ל" + cfg.names[i];
    anim(t, [{ opacity: 0 }, { opacity: 1, offset: 0.1 }, { opacity: 1, offset: 0.85 }, { opacity: 0 }], { duration: 950, easing: "linear" });
    anim($("tkImg"), [{ transform: "scale(.3) rotate(-12deg)" }, { transform: "scale(1.12) rotate(0)", offset: 0.25 }, { transform: "scale(1)", offset: 0.7 }, { transform: "translateY(330px) scale(.2)" }], { duration: 950, easing: "ease-out" });
    anim($("tkVal"), [{ transform: "scale(2)" }, { transform: "scale(1)", offset: 0.2 }, { transform: "scale(1)" }], { duration: 950 });
    clearTimeout(tkTimer);
    tkTimer = setTimeout(() => { bump(i, true); shake($("dash"), 18); }, 700);
  }
  let toastTimer = null;
  function toast(html, i, icon) {
    const t = $("btoast");
    t.style.setProperty("--c", COL[i][1]);
    t.replaceChildren();
    if (icon) { const img = document.createElement("img"); img.src = icon; img.alt = ""; img.onerror = () => img.remove(); t.appendChild(img); }
    const span = document.createElement("span"); span.innerHTML = html; t.appendChild(span);
    t.classList.add("show");
    t.style.fontSize = "56px";
    for (let fs = 56; fs > 32 && t.scrollWidth > t.clientWidth; fs -= 4) t.style.fontSize = fs + "px";
    document.body.classList.add("toasting");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { t.classList.remove("show"); document.body.classList.remove("toasting"); }, 1700);
  }
  let chipRow = 0;
  const avCols = ["#ffb347", "#7cf2c8", "#ff7bac", "#9fb4ff", "#ffd34d"];
  function chatChip(user, i, icon) {
    const row = $("tickerRow" + (chipRow ^= 1));
    const c = document.createElement("div");
    c.className = "chip";
    const av = document.createElement("span"); av.className = "av";
    av.style.background = avCols[[...String(user)].reduce((h, ch) => h + ch.charCodeAt(0), 0) % avCols.length];
    const who = document.createElement("span"); who.className = "who"; who.textContent = user;
    c.append(av, who);
    if (icon) { const img = document.createElement("img"); img.src = icon; img.alt = ""; img.onerror = () => img.remove(); c.appendChild(img); }
    else { const v = document.createElement("span"); v.className = "v"; v.style.background = COL[i][0]; v.textContent = i + 1; c.appendChild(v); }
    row.prepend(c);
    while (row.children.length > 6) row.lastChild.remove();
  }
  function feed(text) {
    if (!DEBUG) return;
    const div = document.createElement("div"); div.className = "item"; div.textContent = text;
    $("feed").appendChild(div);
    while ($("feed").children.length > 2) $("feed").firstChild.remove();
    setTimeout(() => div.remove(), 6000);
  }

  /* ---------- timer & rounds ---------- */
  function parseTime(v) {
    if (!v) return 0;
    v = String(v).trim();
    if (v.includes(":")) { const [m, s] = v.split(":"); return (parseInt(m, 10) || 0) * 60 + (parseInt(s, 10) || 0); }
    return parseInt(v, 10) || 0;
  }
  const timer = { duration: parseTime(P.get("timer")), remaining: 0, endAt: 0, tickId: null };
  timer.remaining = timer.duration;
  let nextId = null, nextTick = null, lastCount = 0;
  const mmss = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;

  function drawClock() {
    document.body.classList.toggle("racing", round.running && !round.ended);
    const el = $("clock");
    const useTimer = timer.duration > 0;
    el.classList.toggle("goal", !useTimer);
    $("clockText").textContent = useTimer ? (round.ended ? "0:00" : mmss(Math.ceil(timer.remaining))) : `🏁 ${fmt(cfg.goal)}`;
    el.classList.toggle("hidden", !useTimer && cfg.goal <= 0);
    el.classList.toggle("paused", !round.running && !round.ended);
    el.classList.toggle("urgent", useTimer && round.running && timer.remaining <= 10);
    el.classList.toggle("done", round.ended && useTimer);
  }
  function tick() {
    if (!round.running || timer.duration <= 0) return;
    timer.remaining = Math.max(0, (timer.endAt - Date.now()) / 1000);
    const c = Math.ceil(timer.remaining);
    if (cfg.countdown && c >= 1 && c <= 3 && c !== lastCount) {
      lastCount = c;
      $("countdown").textContent = String(c);
      anim($("countdown"), [{ transform: "scale(2.4)", opacity: 0 }, { transform: "scale(1)", opacity: 1, offset: 0.2 }, { transform: "scale(.9)", opacity: 1, offset: 0.8 }, { transform: "scale(.6)", opacity: 0 }], { duration: 900, easing: "ease-out" });
      anim($("dim"), [{ opacity: 0 }, { opacity: 0.65, offset: 0.15 }, { opacity: 0.6, offset: 0.8 }, { opacity: 0 }], { duration: 900 });
      shake($("stage"), 10);
    }
    if (c > 3) lastCount = 0;
    if (timer.remaining <= 0) finish();
    drawClock();
  }
  function hideWin() { clearTimeout(nextId); clearInterval(nextTick); $("win").classList.add("hidden"); $("win").classList.remove("show"); }
  function start(seconds) {
    if (seconds > 0) timer.duration = seconds;
    hideWin();
    if (round.ended) clearScores();
    round.ended = false;
    timer.remaining = timer.duration;
    resume();
  }
  function resume() {
    if (round.ended) return;
    round.running = true;
    if (timer.duration > 0) {
      timer.endAt = Date.now() + timer.remaining * 1000;
      clearInterval(timer.tickId);
      timer.tickId = setInterval(tick, 200);
    }
    drawClock(); render();
  }
  function pause() {
    if (!round.running) return;
    tick();
    round.running = false;
    clearInterval(timer.tickId);
    drawClock();
  }
  function adjust(delta) {
    if (round.ended || timer.duration <= 0) return;
    if (round.running) { timer.endAt = Math.max(Date.now() + 1000, timer.endAt + delta * 1000); tick(); }
    else {
      const fresh = timer.remaining === timer.duration;
      timer.remaining = Math.max(5, timer.remaining + delta);
      if (fresh) timer.duration = timer.remaining;
    }
    drawClock();
  }
  function clearScores() {
    pts.fill(0); likeCarry.fill(0);
    members.clear(); contrib.clear(); lastChat.clear();
  }
  function reset() {
    hideWin();
    clearScores();
    clearInterval(timer.tickId);
    round.running = false; round.ended = false;
    timer.remaining = timer.duration;
    render(); drawClock();
  }
  function finish(winner) {
    if (round.ended) return;
    round.running = false; round.ended = true;
    clearInterval(timer.tickId);
    if (demoId) toggleDemo();
    const max = Math.max(...pts);
    const tops = [0, 1, 2, 3].filter((i) => pts[i] === max);
    if (winner === undefined && tops.length === 1) winner = tops[0];
    const w = $("win");
    if (winner === undefined) {
      w.style.setProperty("--c", "#8a3dff");
      $("winCup").textContent = "🤝";
      $("winName").textContent = max > 0 ? "תיקו!" : "אין מנצחים";
      $("winScore").textContent = max > 0 ? tops.map((i) => cfg.names[i]).join(" · ") : "";
      $("winMvp").textContent = "";
    } else {
      w.style.setProperty("--c", COL[winner][0]);
      const wf = cfg.imgs[winner] || cfg.flags[winner];
      $("winCup").replaceChildren();
      if (wf) { const img = document.createElement("img"); img.src = wf; img.alt = ""; $("winCup").appendChild(img); } else $("winCup").textContent = "🏆";
      $("winName").textContent = `🏆 ${cfg.names[winner]}`;
      $("winScore").innerHTML = `🏁 ראשונים בקו הסיום · <span class="ltr">${fmt(pts[winner])}</span> נקודות`;
      let mvp = null;
      contrib.forEach((c) => { if (c.team === winner && (!mvp || c.pts > mvp.pts)) mvp = c; });
      $("winMvp").innerHTML = mvp ? `⭐ MVP: ${esc(mvp.name)} <span class="ltr">+${fmt(mvp.pts)}</span>` : "";
    }
    w.classList.remove("hidden", "show"); void w.offsetWidth; w.classList.add("show");
    shake($("stage"), 22);
    render(); drawClock();
    $("winNext").textContent = "";
    clearTimeout(nextId); clearInterval(nextTick);
    if (cfg.next > 0) {
      let left = cfg.next;
      const show = () => ($("winNext").textContent = `סבב חדש בעוד ${left}`);
      show();
      nextTick = setInterval(() => { left = Math.max(0, left - 1); show(); }, 1000);
      nextId = setTimeout(() => { clearInterval(nextTick); reset(); start(); }, cfg.next * 1000);
    }
  }

  /* ---------- scoring ---------- */
  function add(i, n, user, id) {
    if (i < 0 || i > 3 || round.ended || !(n > 0)) return;
    pts[i] += n;
    if (id) {
      const c = contrib.get(id) || { name: user || id, team: i, pts: 0 };
      c.pts += n; c.team = i; c.name = user || c.name;
      contrib.set(id, c);
    }
    render();
    bump(i, n >= 10);
    if (cfg.goal > 0 && pts[i] >= cfg.goal) finish(i);
  }
  const open = () => round.running && !round.ended;

  const pick = (...v) => v.find((x) => x !== undefined && x !== null && x !== "");
  const bool = (v) => v === true || v === 1 || v === "1" || String(v).toLowerCase() === "true";
  const giftIcons = { rose: "images/gifts/rose.png", tiktok: "images/gifts/tiktok.png", "hand heart": "images/gifts/hand-heart.png", confetti: "images/gifts/confetti.png" };

  function join(id, user, i) {
    if (members.has(id)) return members.get(id);
    members.set(id, i);
    render();
    return i;
  }

  function handle(msg) {
    if (!msg || typeof msg !== "object") return;
    const type = String(msg.event || msg.type || msg.data?.event || msg.data?.type || "").toLowerCase();
    const d = msg.data && typeof msg.data === "object" ? msg.data : msg;
    const u = d.user || {};
    const user = pick(d.nickname, u.nickname, d.uniqueId, u.uniqueId) || "viewer";
    const id = String(pick(d.uniqueId, u.uniqueId, d.userId, u.userId) || user);

    if (type === "chat" || type === "comment") {
      const text = String(d.comment || d.text || "").trim().toLowerCase();
      if (cfg.host && text.startsWith("!") && String(pick(d.uniqueId, u.uniqueId) || "").toLowerCase() === cfg.host) return command(text.slice(1));
      const clean = text.replace(/[\s!.?,️⃣]+/g, "");
      const i = ["1", "2", "3", "4"].indexOf(clean);
      if (i < 0) return;
      if (!open()) return feed(`⏸ ${user}: ${clean} (סבב לא פעיל)`);
      const team = join(id, user, i);
      if (team !== i) return feed(`${user} כבר ב${cfg.names[team]}`);
      const now = Date.now();
      if (now - (lastChat.get(id) || 0) < cfg.cooldown) return;
      lastChat.set(id, now);
      chatChip(user, i);
      flyVote(i);
      if (cfg.chat > 0) add(i, cfg.chat, user, id);
    }

    else if (type === "gift") {
      const det = d.giftDetails || d.gift || {};
      const ext = d.extendedGiftInfo || {};
      const giftType = num(pick(d.giftType, det.giftType, ext.type), 0);
      if (giftType === 1 && !bool(pick(d.repeatEnd, d.repeat_end))) return; // count a streak once, at its end
      const name = String(pick(d.giftName, det.giftName, d.gift_name, ext.name) || "").toLowerCase();
      let i = cfg.gifts.findIndex((list) => list.includes(name));
      if (i < 0) i = members.has(id) ? members.get(id) : -1;
      if (i < 0) return feed(`🎁 ${user}: ${name} (לא בחר קבוצה)`);
      if (!open()) return feed(`⏸ 🎁 ${user}: ${name} (סבב לא פעיל)`);
      join(id, user, i);
      const pic = pick(d.giftPictureUrl, d.giftImageUrl, det.giftPictureUrl, det.giftImage?.giftPictureUrl, ext.image?.url_list?.[0], d.gift?.icon?.url_list?.[0]) || "";
      if (pic && !giftIcons[name]) giftIcons[name] = pic;
      const icon = giftIcons[name] || "";
      const each = Math.max(1, num(pick(d.diamondCount, det.diamondCount, d.diamond_count, ext.diamond_count, d.coins), 1));
      const count = Math.max(1, Math.floor(num(pick(d.repeatCount, d.repeat_count, d.comboCount), 1)));
      const n = Math.max(1, Math.round(each * count * cfg.giftMult));
      chatChip(user, i, icon);
      toast(`${icon ? "" : "🎁 "}<b class="ltr">+${fmt(n)}</b> ל${esc(cfg.names[i])}`, i, icon);
      flyGift(i, icon);
      if (each >= cfg.bigGift || n >= cfg.bigGift) takeover(i, icon, n);
      add(i, n, user, id);
    }

    else if (type === "like" && cfg.likes > 0) {
      if (!members.has(id) || !open()) return;
      const i = members.get(id);
      likeCarry[i] += Math.max(1, num(pick(d.likeCount, d.count), 1)) * cfg.likes;
      const whole = Math.floor(likeCarry[i]);
      if (whole > 0) { likeCarry[i] -= whole; add(i, whole, user, id); }
    }
  }

  /* ---------- connections ---------- */
  function connect() {
    if (!cfg.ws || cfg.ws === "off") return;
    let ws;
    try { ws = new WebSocket(cfg.ws); } catch (e) { return setTimeout(connect, 3000); }
    ws.onopen = () => { $("status").textContent = "● connected"; $("status").classList.add("on"); };
    ws.onmessage = (e) => { try { handle(JSON.parse(e.data)); } catch (_) { /* ignore non-JSON */ } };
    ws.onclose = () => { $("status").textContent = "reconnecting…"; $("status").classList.remove("on"); setTimeout(connect, 3000); };
    ws.onerror = () => ws.close();
  }

  /* Commands from the control panel (control.html, same room) or !commands from the host:
     start [m:ss] | pause | resume | toggle | reset | end | timer m:ss | adjust ±sec |
     goal N | team T N (T = 1-4) | teamsub T N | add a|b N (= team 1|2) | demo            */
  function command(text) {
    const [c, x, y] = String(text).trim().toLowerCase().split(/\s+/);
    const teamOf = (v) => (v === "a" ? 0 : v === "b" ? 1 : Math.min(3, Math.max(0, (parseInt(v, 10) || 1) - 1)));
    const amount = Math.max(1, parseInt(y, 10) || 1);
    switch (c) {
      case "start": start(x ? parseTime(x) : 0); break;
      case "pause": pause(); break;
      case "resume": resume(); break;
      case "toggle": round.running ? pause() : resume(); break;
      case "reset": reset(); break;
      case "end": finish(); break;
      case "timer":
        timer.duration = Math.max(0, parseTime(x || "0"));
        if (!round.running) { timer.remaining = timer.duration; }
        drawClock(); break;
      case "adjust": adjust(parseInt(x, 10) || 0); break;
      case "goal": cfg.goal = Math.max(0, parseInt(x, 10) || 0); drawRules(); render(); drawClock(); break;
      case "team": case "add": add(teamOf(x), amount); break;
      case "teamsub": case "sub": if (!round.ended) { const i = teamOf(x); pts[i] = Math.max(0, pts[i] - amount); render(); } break;
      case "demo": toggleDemo(); break;
    }
  }
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

  /* ---------- demo & keyboard ---------- */
  let demoId = null;
  function toggleDemo() {
    if (demoId) { clearInterval(demoId); demoId = null; return; }
    if (!open()) start();
    demoId = setInterval(() => {
      const i = (Math.random() * 4) | 0, who = "fan" + ((Math.random() * 40) | 0), r = Math.random();
      const uid = "demo" + i + "_" + who;
      if (r < 0.012) handle({ event: "gift", data: { nickname: who, uniqueId: uid, giftName: ["Hand Heart", "Confetti"][i % 2], diamondCount: 100, repeatCount: 1 } });
      else if (r < 0.07) handle({ event: "gift", data: { nickname: who, uniqueId: uid, giftName: ["Rose", "TikTok"][i % 2], diamondCount: 1, repeatCount: 1 + ((Math.random() * 5) | 0) } });
      else handle({ event: "chat", data: { nickname: who, uniqueId: uid, comment: String(i + 1) } });
    }, 160);
  }
  addEventListener("keydown", (e) => {
    const k = ["Digit1", "Digit2", "Digit3", "Digit4"].indexOf(e.code);
    if (k >= 0) add(k, e.shiftKey ? 10 : 1);
    else if (e.key === "r" || e.key === "R") reset();
    else if (e.key === "t" || e.key === "T") { reset(); start(); }
    else if (e.key === "d" || e.key === "D") toggleDemo();
    else if (e.code === "Space") { e.preventDefault(); round.running ? pause() : resume(); }
    else if (e.code === "BracketLeft") adjust(e.shiftKey ? -60 : -15);
    else if (e.code === "BracketRight") adjust(e.shiftKey ? 60 : 15);
  });

  window.Battle = { add, reset, start, finish, handle, command, pts, members };

  drawRules(); render(); drawClock();
  if (P.get("autostart") !== "0") start();
  connect();
  listenControl();
  if (P.get("demo") === "1") toggleDemo();
})();
