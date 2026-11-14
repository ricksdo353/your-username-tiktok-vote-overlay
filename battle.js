/* =========================================================
   TikTok LIVE Country Race (10 cars) – battle.html
   Viewers join a country by commenting its number (1-10), or by sending that
   country's gift. Every comment, like and gift pushes the country's car toward
   the finish line. First country to the goal wins (or the leader when the
   timer runs out); the winner is shown, then a new race starts by itself.

   Each country has its own popular 1-coin gift (checked on streamtoearn.io for
   Israel): every one of those gifts = 1 point for that country, from anyone.

   URL parameters (all optional):
   teams              how many countries race, 2-10 (default 10, in the order below)
   lang               board language: English (default) or lang=he for Hebrew
   t1 … t10           names (default Israel, Palestine, USA, Iran, Russia, Ukraine,
                      Morocco, Egypt, Turkey, Saudi Arabia)
   flag1 … flag10     flag picture for a country (flagN=none hides it); a renamed
                      country has no flag unless you give one
   gift1 … gift10     gift name(s) for a country, comma separated (giftN=none = no gift)
   giftImg1 …         picture for that gift
   goal               points to win (default 1000; goal=0 = no goal, timer only)
   timer              race length, seconds or m:ss (default none)
   next               seconds the winner is shown before a new race starts
                      by itself (default 15; next=0 = off)
   chat               points per comment of the country number (default 1)
   cooldown           ms between counted comments from one viewer (default 2000)
   likes              points per like (default 0.1 = 10 likes are 1 point; 0 = off)
   giftMult           points per coin (default 1)
   room / host / ws / bg / bigGift / takeover / countdown / autostart / preview /
   demo / debug       same as the vote board (index.html)

   Keyboard: 1-9 and 0 (=10) = +1 (Shift = +10), R = reset, T = new race,
             Space = pause, D = demo, [ / ] = -15s / +15s
   ========================================================= */

(() => {
  const P = new URLSearchParams(location.search);
  const num = (v, def = 0) => { const n = Number(v); return Number.isFinite(n) ? n : def; };
  // Board language: English by default, lang=he for Hebrew
  const HE = P.get("lang") === "he";
  const T = HE ? {
    names: ["ישראל", "פלסטין", "ארה״ב", "איראן", "רוסיה", "אוקראינה", "מרוקו", "מצרים", "טורקיה", "סעודיה"],
    title: `🏁 מרוץ <span class="grad">מדינות</span>`,
    hint: (n) => `כתבו <span class="grad ltr">1–${n}</span> כדי להצטרף`,
    rulesGoal: (g) => `🏁 הראשונים ל־<b class="ltr">${g}</b> מנצחים · כתבו את המספר של המדינה שלכם`,
    rulesTime: `⏱ המובילים בסוף הזמן מנצחים · כתבו את המספר של המדינה שלכם`,
    info: `🎁 מתנות נספרות כנקודות למדינה שלכם`,
    thankOne: (u) => `🙏 תודה ${u}!`,
    welcome: (u, n) => `👋 ברוך הבא ${u}! כתבו 1–${n} · 🎁 מתנות נספרות למדינה שלכם`,
    rules: [(n) => `💬 כתבו מספר 1–${n} כדי להצטרף למדינה`, () => `🏎️ כל תגובה מקדמת את המכונית שלכם`, (n, g) => g > 0 ? `🏁 הראשונים ל־${g} מנצחים` : `⏱ המובילים בסוף הזמן מנצחים`],
    thanks: `🙏 תודה ל־`,
    to: (name) => "ל" + name,
    tie: "תיקו!", none: "אין מנצחים",
    won: (p) => `🏁 ראשונים בקו הסיום · <span class="ltr">${p}</span> נקודות`,
    next: (s) => `מרוץ חדש בעוד ${s}`,
  } : {
    names: ["Israel", "Palestine", "USA", "Iran", "Russia", "Ukraine", "Morocco", "Egypt", "Turkey", "Saudi Arabia"],
    title: `🏁 Country <span class="grad">Race</span>`,
    hint: (n) => `Comment <span class="grad ltr">1–${n}</span> to join`,
    rulesGoal: (g) => `🏁 First to <b class="ltr">${g}</b> wins · Comment your country's number`,
    rulesTime: `⏱ Leader at the end wins · Comment your country's number`,
    info: `🎁 Gifts count as points for your country`,
    thankOne: (u) => `🙏 Thank you ${u}!`,
    welcome: (u, n) => `👋 Welcome ${u}! Comment 1–${n} · 🎁 Gifts count for your country`,
    rules: [(n) => `💬 Comment 1–${n} to join a country`, () => `🏎️ Every comment moves your car forward`, (n, g) => g > 0 ? `🏁 First to ${g} wins` : `⏱ The leader at the end wins`],
    thanks: `🙏 Thanks `,
    to: (name) => name,
    tie: "Tie!", none: "No winner",
    won: (p) => `🏁 First to the finish · <span class="ltr">${p}</span> points`,
    next: (s) => `New race in ${s}`,
  };
  if (!HE) { document.documentElement.lang = "en"; document.body.classList.add("lang-en"); }
  const giftKey = (g) => String(g || "").toLowerCase().replace(/[’`]/g, "'").replace(/\s+/g, " ").trim();

  // Default countries: flag (images/flags), 1-coin gift (images/gifts), car colours
  const DEFAULTS = [
    ["ישראל", "il", "Rose", "rose", "#2f8bff", "#1456c9"],
    ["פלסטין", "ps", "TikTok", "tiktok", "#1fa055", "#0d6b37"],
    ["ארה״ב", "us", "GG", "gg", "#e0283c", "#9c1224"],
    ["איראן", "ir", "Ice Cream Cone", "ice-cream-cone", "#ff8a1f", "#b85a00"],
    ["רוסיה", "ru", "Cake Slice", "cake-slice", "#6a5cff", "#3b2fc9"],
    ["אוקראינה", "ua", "Glow Stick", "glow-stick", "#f5c400", "#9c7c00"],
    ["מרוקו", "ma", "Thumbs Up", "thumbs-up", "#c2185b", "#7f0f3c"],
    ["מצרים", "eg", "Heart", "heart", "#b8862b", "#76561a"],
    ["טורקיה", "tr", "Love you", "love-you", "#ff5c8a", "#c2264f"],
    ["סעודיה", "sa", "Blow a kiss", "blow-a-kiss", "#12a5a0", "#0a6b68"],
  ];
  const N = Math.min(10, Math.max(2, Math.floor(num(P.get("teams") ?? 10, 10))));
  const TEAMS = DEFAULTS.slice(0, N).map(([name, flag, gift, gimg, c1, c2], i) => {
    const k = i + 1, renamed = !!P.get("t" + k);
    const fp = P.get("flag" + k), gp = P.get("gift" + k);
    const gifts = gp === "none" ? [] : (gp ? gp.split(",") : [gift]).map(giftKey).filter(Boolean);
    return {
      name: P.get("t" + k) || T.names[i],
      flag: fp === "none" ? "" : fp || (renamed ? "" : `images/flags/${flag}.svg`),
      gifts,
      giftLabel: gp === "none" ? "" : gp ? gp.split(",")[0].trim() : gift,
      giftImg: P.get("giftImg" + k) || (gp ? "" : `images/gifts/${gimg}.png`),
      c: [c1, c2],
    };
  });
  const cfg = {
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
  const $ = (id) => document.getElementById(id);
  const esc = (x) => String(x).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const fmt = (n) => Math.floor(n).toLocaleString("en-US");
  const anim = (el, frames, opts) => { try { return el.animate(frames, opts); } catch (_) { return null; } };
  const DEBUG = P.get("debug") === "1";

  const pts = new Array(N).fill(0);
  const likeCarry = new Array(N).fill(0);
  const members = new Map();  // viewer id -> team index
  const contrib = new Map();  // viewer id -> { name, team, pts }
  const lastChat = new Map();
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
  $("title").innerHTML = T.title;
  $("hint").innerHTML = T.hint(N);
  // shrink a one-line text until it fits its box
  function fitText(el, max, min) {
    el.style.whiteSpace = "nowrap"; el.style.fontSize = max + "px";
    for (let fs = max; fs > min && el.scrollWidth > el.clientWidth + 1; fs -= 2) el.style.fontSize = fs + "px";
  }
  $("title").style.padding = $("hint").style.padding = "0 40px";
  fitText($("title"), 86, 50); fitText($("hint"), 86, 50);
  setInterval(() => { $("title").classList.toggle("off"); $("hint").classList.toggle("off"); }, 5000);

  /* ---------- lanes ---------- */
  // gift pictures next to each country are off by default (showGifts=1 turns them on):
  // a board that keeps advertising gifts can be treated by TikTok as gift solicitation
  const SHOW_GIFTS = P.get("showGifts") === "1";
  const giftCoins = new Map(); // viewer id -> { name, n } gifts only, for the thank-you line
  const ROAD_W = 412, CAR_W = 112, LANE_H = 80;
  const TOP = 374, AREA = 888;
  const PITCH = Math.min(118, Math.floor(AREA / N));
  const laneTop = (i) => TOP + Math.round((AREA - N * PITCH) / 2) + i * PITCH;
  const carSvg = (i, flag) => {
    const [c1, c2] = TEAMS[i].c, n = i + 1;
    return `<svg viewBox="0 0 190 84" aria-hidden="true">
    <ellipse cx="96" cy="80" rx="88" ry="5" fill="rgba(0,0,0,.45)"/>
    <path class="flame" d="M184 46 L214 40 L204 50 L222 56 L184 58 Z" fill="#ffb02e"/>
    <path d="M6 60 Q4 44 20 40 L54 34 Q72 14 100 12 L132 12 Q154 14 166 32 L178 36 Q190 40 188 60 Z" fill="${c1}" stroke="#fff" stroke-width="4"/>
    <path d="M6 60 L188 60 L186 52 L8 52 Z" fill="${c2}"/>
    <path d="M62 34 Q76 21 98 19 L104 19 L104 34 Z M110 19 L128 19 Q142 21 152 34 L110 34 Z" fill="#0b1530" opacity=".88"/>
    <ellipse cx="13" cy="46" rx="6" ry="4" fill="#fff6c0"/><rect x="180" y="40" width="7" height="8" rx="2" fill="#ff2d2d"/>
    ${flag ? `<image href="${flag}" x="110" y="36" width="42" height="26" preserveAspectRatio="xMidYMid slice"/><rect x="110" y="36" width="42" height="26" fill="none" stroke="#fff" stroke-width="2.5"/>` : ""}
    <circle cx="80" cy="47" r="13" fill="#fff"/><text x="80" y="${n > 9 ? 52 : 53}" text-anchor="middle" font-size="${n > 9 ? 15 : 18}" font-weight="900" font-family="Heebo, Arial" fill="${c2}">${n}</text>
    <g class="wheel"><circle cx="46" cy="62" r="17" fill="#111"/><circle cx="46" cy="62" r="8" fill="#c9c9d6"/><path d="M46 47v30M31 62h30" stroke="#555" stroke-width="3"/></g>
    <g class="wheel"><circle cx="150" cy="62" r="17" fill="#111"/><circle cx="150" cy="62" r="8" fill="#c9c9d6"/><path d="M150 47v30M135 62h30" stroke="#555" stroke-width="3"/></g>
  </svg>`;
  };
  const lanes = TEAMS.map((t, i) => {
    const el = document.createElement("div");
    el.className = "lane" + (t.flag ? "" : " noflag");
    el.style.top = laneTop(i) + "px";
    el.style.setProperty("--c", t.c[0]); el.style.setProperty("--c2", t.c[1]);
    el.innerHTML = `<div class="badge">${i + 1}</div><div class="crown">👑</div>${t.flag ? '<img class="flag" alt="">' : ""}
      <div class="tname"></div>
      <div class="meta"><span class="gname"></span><span class="mem">👥 <span class="mc">0</span></span></div>${t.giftImg && SHOW_GIFTS ? '<img class="gift" alt="">' : ""}
      <div class="pts">0</div>
      <div class="road"><div class="fill"></div><div class="dash"></div><div class="flash"></div><div class="finish"></div></div>
      <div class="car">${carSvg(i, t.flag)}</div>`;
    el.querySelector(".tname").textContent = t.name;
    requestAnimationFrame(() => fitText(el.querySelector(".tname"), 34, 22));
    el.querySelector(".gname").textContent = !SHOW_GIFTS || t.giftImg ? "" : t.giftLabel ? "🎁 " + t.giftLabel : "";
    if (t.flag) el.querySelector(".flag").src = t.flag;
    if (t.giftImg && SHOW_GIFTS) { const g = el.querySelector(".gift"); g.src = t.giftImg; g.onerror = () => { g.remove(); el.querySelector(".gname").textContent = "🎁 " + t.giftLabel; }; }
    $("lanes").appendChild(el);
    return { el, car: el.querySelector(".car"), fill: el.querySelector(".fill"), flash: el.querySelector(".flash"), pts: el.querySelector(".pts"), mc: el.querySelector(".mc") };
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
      l.car.style.right = (900 - ROAD_W + p * (ROAD_W - CAR_W)).toFixed(1) + "px";
      l.pts.textContent = fmt(pts[i]);
      l.mc.textContent = teamSize(i);
      l.el.classList.toggle("lead", max > 0 && leaders === 1 && pts[i] === max);
      l.el.classList.toggle("hot", cfg.goal > 0 && p >= 0.8 && !round.ended);
    });
  }
  /* The line under the race shows, in turn: a calm one-time note that gifts count (6 s at the start of a race),
     then the rules, alternating with a thank-you to the race's top 3 gifters. No repeating "send gifts" text. */
  let infoUntil = 0, rulesFlip = false;
  // Big rules card for 8 s at the start of every race (rulesCard=0 turns it off)
  let cardTimer = null;
  function showRulesCard() {
    if (P.get("rulesCard") === "0") return false;
    let card = $("rulesCard");
    if (!card) { card = document.createElement("div"); card.id = "rulesCard"; card.className = "abs"; $("stage").appendChild(card); }
    card.className = "abs" + (HE ? " he" : "");
    card.style.direction = HE ? "rtl" : "ltr";
    const rows = HE
      ? [["💬", `כתבו מספר <b>1–${N}</b> כדי להצטרף למדינה`], ["🏎️", "כל תגובה מקדמת את המכונית שלכם"], ["🎁", "מתנות נספרות כנקודות למדינה שלכם"],
         ["🏁", cfg.goal > 0 ? `הראשונים ל־<b>${fmt(cfg.goal)}</b> מנצחים` : "המובילים בסוף הזמן מנצחים"]]
      : [["💬", `Comment <b>1–${N}</b> to join a country`], ["🏎️", "Every comment moves your car forward"], ["🎁", "Gifts count as points for your country"],
         ["🏁", cfg.goal > 0 ? `First to <b>${fmt(cfg.goal)}</b> wins` : "The leader at the end wins"]];
    card.innerHTML = `<h2>📜 <span class="grad">${HE ? "איך משחקים" : "How to play"}</span></h2>` +
      rows.map(([i, t]) => `<div class="row"><div class="ic">${i}</div><div class="tx">${t}</div></div>`).join("");
    card.classList.add("show");
    lastCard = Date.now();
    clearTimeout(cardTimer);
    cardTimer = setTimeout(() => card.classList.remove("show"), 8000);
    return true;
  }
  // also every N seconds while the race runs (rulesEvery=120 by default, 0 = only at the start), not in the last 20 s of a timer
  const RULES_EVERY = Math.max(0, parseInt(P.get("rulesEvery") ?? "120", 10) || 0) * 1000;
  let lastCard = 0;
  if (RULES_EVERY) setInterval(() => {
    if (!round.running || round.ended || (timer.duration > 0 && timer.remaining <= 20)) return;
    if (Date.now() - lastCard >= RULES_EVERY) showRulesCard();
  }, 1000);
  function showGiftInfo() { if (showRulesCard()) return; if (P.get("giftInfo") !== "0") { welcomeName = ""; infoUntil = Date.now() + 6000; drawRules(); setTimeout(drawRules, 6100); } }
  // welcome a viewer who joins, with how to play; at most once every 3 minutes (welcome=<s>, welcome=0 = off)
  let welcomeName = "", lastWelcome = 0;
  const WELCOME_GAP = Math.max(0, parseInt(P.get("welcome") ?? "180", 10) || 0) * 1000;
  function welcome(name) {
    if (!WELCOME_GAP || Date.now() - lastWelcome < WELCOME_GAP || !round.running) return;
    lastWelcome = Date.now(); welcomeName = String(name || "").slice(0, 24);
    infoUntil = Date.now() + 8000; drawRules();
    setTimeout(() => { welcomeName = ""; drawRules(); }, 8100);
  }
  setInterval(() => { rulesFlip = !rulesFlip; drawRules(); }, 7000);
  // how-to-play reminder every 15 s for 5 s (the gift line is NOT repeated: TikTok treats that as solicitation)
  let ruleIdx = -1, ruleUntil = 0;
  if (P.get("rules") !== "0") setInterval(() => { ruleIdx++; ruleUntil = Date.now() + 5000; drawRules(); setTimeout(drawRules, 5100); }, 15000);
  function drawRules() {
    const r = $("rules");
    const top = P.get("thanks") === "0" ? [] : [...giftCoins.values()].sort((x, y) => y.n - x.n).slice(0, 3);
    if (Date.now() < infoUntil) r.textContent = welcomeName ? T.welcome(welcomeName, N) : T.info;
    else if (Date.now() < ruleUntil) r.textContent = T.rules[ruleIdx % T.rules.length](N, cfg.goal > 0 ? fmt(cfg.goal) : 0);
    else if (rulesFlip && top.length) { r.textContent = T.thanks + top.map((s) => s.name).join(" · "); }
    else r.innerHTML = cfg.goal > 0 ? T.rulesGoal(fmt(cfg.goal)) : T.rulesTime;
    r.style.fontSize = "38px";
    for (let fs = 38; fs > 26 && r.scrollWidth > r.clientWidth; fs -= 2) r.style.fontSize = fs + "px";
  }

  /* ---------- effects ---------- */
  function bump(i, strong) {
    anim(lanes[i].car, [{ transform: "translateX(0) scale(1)" }, { transform: `translateX(${strong ? -22 : -10}px) scale(${strong ? 1.15 : 1.06})` }, { transform: "translateX(0) scale(1)" }], { duration: 260, easing: "ease-out" });
    anim(lanes[i].car.querySelector(".flame"), [{ opacity: 1 }, { opacity: 0 }], { duration: strong ? 600 : 300, easing: "ease-out" });
    anim(lanes[i].flash, [{ opacity: 0.4 }, { opacity: 0 }], { duration: 350, easing: "ease-out" });
  }
  function shake(el, amp = 14) {
    anim(el, [{ transform: "translate(0,0)" }, { transform: `translate(${-amp}px,${amp / 2}px)` }, { transform: `translate(${amp - 2}px,${-amp / 2}px)` },
      { transform: `translate(${-amp / 2}px,4px)` }, { transform: "translate(0,0)" }], { duration: 220 });
  }
  const laneY = (i) => laneTop(i) + LANE_H / 2;
  const carX = (i) => 40 + ROAD_W - progress(i) * (ROAD_W - CAR_W) - CAR_W / 2;
  let lastFly = 0;
  function flyVote(i) {
    const now = Date.now();
    if (now - lastFly < 200) return;
    lastFly = now;
    const b = document.createElement("div");
    b.className = "fly-vote"; b.textContent = i + 1; b.style.background = TEAMS[i].c[0];
    if (i >= 9) b.style.fontSize = "56px";
    const x0 = 100 + (i % 5) * 180, y0 = 1420;
    b.style.left = x0 + "px"; b.style.top = y0 + "px";
    $("flyLayer").appendChild(b);
    const dx = carX(i) - 58 - x0, dy = laneY(i) - 58 - y0;
    anim(b, [{ transform: "translate(0,0) scale(.6)", opacity: 0 }, { transform: "translate(0,-30px) scale(1)", opacity: 1, offset: 0.2 },
      { transform: `translate(${dx}px,${dy}px) scale(.45)`, opacity: 1, offset: 0.92 }, { transform: `translate(${dx}px,${dy}px) scale(.3)`, opacity: 0 }],
      { duration: 520, easing: "ease-in" });
    setTimeout(() => b.remove(), 560);
  }
  function flyGift(i, icon) {
    if (!icon) return bump(i, true);
    const img = document.createElement("img");
    img.className = "fly-gift"; img.alt = ""; img.src = icon;
    img.style.left = "1100px"; img.style.top = laneY(i) - 130 + "px"; img.style.filter = `drop-shadow(0 0 30px ${TEAMS[i].c[0]})`;
    $("flyLayer").appendChild(img);
    const dx = carX(i) - 130 - 1100;
    anim(img, [{ transform: "translate(0,0) scale(1)", opacity: 0 }, { transform: "translate(0,0) scale(1)", opacity: 1, offset: 0.15 },
      { transform: `translate(${dx}px,0) scale(.35)`, opacity: 1, offset: 0.9 }, { transform: `translate(${dx}px,0) scale(.35)`, opacity: 0 }], { duration: 450, easing: "ease-in" });
    setTimeout(() => { img.remove(); bump(i, true); }, 460);
  }
  let tkTimer = null;
  function takeover(i, icon, n) {
    if (!cfg.takeover) return;
    const t = $("takeover");
    t.className = "abs";
    t.style.background = `radial-gradient(circle at 50% 45%, ${TEAMS[i].c[0]}, ${TEAMS[i].c[1]} 45%, #07031a 80%)`;
    $("tkVal").textContent = "+" + fmt(n);
    $("tkImg").src = icon || ""; $("tkImg").style.visibility = icon ? "visible" : "hidden";
    $("tkName").textContent = T.to(TEAMS[i].name);
    anim(t, [{ opacity: 0 }, { opacity: 1, offset: 0.1 }, { opacity: 1, offset: 0.85 }, { opacity: 0 }], { duration: 950, easing: "linear" });
    anim($("tkImg"), [{ transform: "scale(.3) rotate(-12deg)" }, { transform: "scale(1.12) rotate(0)", offset: 0.25 }, { transform: "scale(1)", offset: 0.7 }, { transform: "translateY(330px) scale(.2)" }], { duration: 950, easing: "ease-out" });
    anim($("tkVal"), [{ transform: "scale(2)" }, { transform: "scale(1)", offset: 0.2 }, { transform: "scale(1)" }], { duration: 950 });
    clearTimeout(tkTimer);
    tkTimer = setTimeout(() => { bump(i, true); shake($("dash"), 18); }, 700);
  }
  let toastTimer = null;
  function toast(html, i, icon) {
    const t = $("btoast");
    t.style.setProperty("--c", TEAMS[i].c[1]);
    t.replaceChildren();
    if (TEAMS[i].flag) { const f = document.createElement("img"); f.className = "tflag"; f.src = TEAMS[i].flag; f.alt = ""; t.appendChild(f); }
    if (icon) { const img = document.createElement("img"); img.src = icon; img.alt = ""; img.onerror = () => img.remove(); t.appendChild(img); }
    const span = document.createElement("span"); span.innerHTML = html; t.appendChild(span);
    t.classList.add("show");
    t.style.fontSize = "52px";
    for (let fs = 52; fs > 30 && t.scrollWidth > t.clientWidth; fs -= 4) t.style.fontSize = fs + "px";
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
    else { const v = document.createElement("span"); v.className = "v"; v.style.background = TEAMS[i].c[0]; v.textContent = i + 1; if (i >= 9) v.style.fontSize = "32px"; c.appendChild(v); }
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
    showGiftInfo();
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
    members.clear(); contrib.clear(); lastChat.clear(); giftCoins.clear();
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
    const tops = pts.map((p, i) => i).filter((i) => pts[i] === max);
    if (winner === undefined && tops.length === 1 && max > 0) winner = tops[0];
    const w = $("win");
    $("winCup").replaceChildren();
    if (winner === undefined) {
      w.style.setProperty("--c", "#8a3dff");
      $("winCup").textContent = "🤝";
      $("winName").textContent = max > 0 ? T.tie : T.none;
      $("winScore").textContent = max > 0 ? tops.map((i) => TEAMS[i].name).join(" · ") : "";
      $("winMvp").textContent = "";
    } else {
      const t = TEAMS[winner];
      w.style.setProperty("--c", t.c[0]);
      if (t.flag) { const img = document.createElement("img"); img.src = t.flag; img.alt = ""; $("winCup").appendChild(img); } else $("winCup").textContent = "🏆";
      $("winName").textContent = `🏆 ${t.name}`;
      $("winScore").innerHTML = T.won(fmt(pts[winner]));
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
      const show = () => ($("winNext").textContent = T.next(left));
      show();
      nextTick = setInterval(() => { left = Math.max(0, left - 1); show(); }, 1000);
      nextId = setTimeout(() => { clearInterval(nextTick); reset(); start(); }, cfg.next * 1000);
    }
  }

  /* ---------- scoring ---------- */
  function add(i, n, user, id) {
    if (!(i >= 0 && i < N) || round.ended || !(n > 0)) return;
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
  const giftIcons = { "hand heart": "images/gifts/hand-heart.png", confetti: "images/gifts/confetti.png" };
  TEAMS.forEach((t) => t.gifts.forEach((g) => { if (t.giftImg) giftIcons[g] = t.giftImg; }));
  const giftTeam = (name) => TEAMS.findIndex((t) => t.gifts.includes(name));

  function join(id, i) {
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
      if (!/^\d{1,2}$/.test(clean)) return;
      const i = parseInt(clean, 10) - 1;
      if (i < 0 || i >= N) return;
      if (!open()) return feed(`⏸ ${user}: ${clean} (סבב לא פעיל)`);
      const team = join(id, i);
      if (team !== i) return feed(`${user} כבר ב${TEAMS[team].name}`);
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
      const name = giftKey(pick(d.giftName, det.giftName, d.gift_name, ext.name));
      let i = giftTeam(name);                       // a country's own gift always counts for it
      if (i < 0) i = members.has(id) ? members.get(id) : -1;
      if (i < 0) return feed(`🎁 ${user}: ${name} (לא בחר מדינה)`);
      if (!open()) return feed(`⏸ 🎁 ${user}: ${name} (סבב לא פעיל)`);
      join(id, i);
      const pic = pick(d.giftPictureUrl, d.giftImageUrl, det.giftPictureUrl, det.giftImage?.giftPictureUrl, ext.image?.url_list?.[0], d.gift?.icon?.url_list?.[0]) || "";
      if (pic && !giftIcons[name]) giftIcons[name] = pic;
      const icon = giftIcons[name] || "";
      const each = Math.max(1, num(pick(d.diamondCount, det.diamondCount, d.diamond_count, ext.diamond_count, d.coins), 1));
      const count = Math.max(1, Math.floor(num(pick(d.repeatCount, d.repeat_count, d.comboCount), 1)));
      const n = Math.max(1, Math.round(each * count * cfg.giftMult));
      chatChip(user, i, icon);
      toast(`${esc(T.thankOne(user))} <b class="ltr">+${fmt(n)}</b> ${esc(T.to(TEAMS[i].name))}`, i, icon);
      if (window.SpeakThanks) window.SpeakThanks(user, HE ? "he" : "en");
      flyGift(i, icon);
      if (each >= cfg.bigGift || n >= cfg.bigGift) takeover(i, icon, n);
      add(i, n, user, id);
      if (cfg.room && window.Relay) window.Relay.notify("tvr-" + cfg.room, { type: "gift", user, gift: String(pick(d.giftName, det.giftName, d.gift_name, ext.name) || name), n, side: TEAMS[i].name });
      if (P.get("thanks") !== "0") { const s = giftCoins.get(id) || { name: user, n: 0 }; s.n += n; s.name = user || s.name; giftCoins.set(id, s); }
    }

    else if (type === "member" || type === "join") {
      welcome(user);
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

  /* Commands from the race control panel (race-control.html, same room; its own channel, tvr-) or !commands from the host:
     start [m:ss] | pause | resume | toggle | reset | end | timer m:ss | adjust ±sec |
     goal N | team T N (T = 1-10) | teamsub T N | add a|b N (= team 1|2) | demo           */
  function command(text) {
    const [c, x, y] = String(text).trim().toLowerCase().split(/\s+/);
    const teamOf = (v) => (v === "a" ? 0 : v === "b" ? 1 : Math.min(N - 1, Math.max(0, (parseInt(v, 10) || 1) - 1)));
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
        if (!round.running) timer.remaining = timer.duration;
        drawClock(); break;
      case "adjust": adjust(parseInt(x, 10) || 0); break;
      case "goal": cfg.goal = Math.max(0, parseInt(x, 10) || 0); drawRules(); render(); drawClock(); break;
      case "team": case "add": add(teamOf(x), amount); break;
      case "teamsub": case "sub": if (!round.ended) { const i = teamOf(x); pts[i] = Math.max(0, pts[i] - amount); render(); } break;
      case "demo": toggleDemo(); break;
    }
  }
  // small "🎮" mark next to the connection status: is the control panel linked?
  function setCtrl(ok) {
    let el = document.getElementById("ctrlStat");
    if (!el) { el = document.createElement("div"); el.id = "ctrlStat"; el.className = "abs"; document.getElementById("stage").appendChild(el); }
    const tail = cfg.room ? " …" + cfg.room.slice(-3) : "";
    el.textContent = ok === null ? "🎮 ✗ no room" : (ok ? "🎮 ✓" : "🎮 …") + tail;
    el.classList.toggle("on", ok === true);
  }
  function listenControl() {
    if (!cfg.room) return setCtrl(null);
    if (!window.Relay) return setCtrl(false);
    window.Relay.listen("tvr-" + cfg.room, (text) => command(text), (ok) => setCtrl(ok));
  }


  /* ---------- demo & keyboard ---------- */
  let demoId = null;
  function toggleDemo() {
    if (demoId) { clearInterval(demoId); demoId = null; return; }
    if (!open()) start();
    demoId = setInterval(() => {
      const i = (Math.random() * N) | 0, who = "fan" + ((Math.random() * 60) | 0), r = Math.random();
      const uid = "demo" + i + "_" + who;
      if (r < 0.01) handle({ event: "gift", data: { nickname: who, uniqueId: uid, giftName: "Hand Heart", diamondCount: 100, repeatCount: 1 } });
      else if (r < 0.12 && TEAMS[i].giftLabel) handle({ event: "gift", data: { nickname: who, uniqueId: uid, giftName: TEAMS[i].giftLabel, diamondCount: 1, repeatCount: 1 + ((Math.random() * 5) | 0) } });
      else handle({ event: "chat", data: { nickname: who, uniqueId: uid, comment: String(i + 1) } });
    }, 140);
  }
  addEventListener("keydown", (e) => {
    const m = /^Digit(\d)$/.exec(e.code);
    if (m) { const i = m[1] === "0" ? 9 : parseInt(m[1], 10) - 1; if (i < N) add(i, e.shiftKey ? 10 : 1); }
    else if (e.key === "r" || e.key === "R") reset();
    else if (e.key === "t" || e.key === "T") { reset(); start(); }
    else if (e.key === "d" || e.key === "D") toggleDemo();
    else if (e.code === "Space") { e.preventDefault(); round.running ? pause() : resume(); }
    else if (e.code === "BracketLeft") adjust(e.shiftKey ? -60 : -15);
    else if (e.code === "BracketRight") adjust(e.shiftKey ? 60 : 15);
  });

  window.Battle = { add, reset, start, finish, handle, command, pts, members, teams: TEAMS };

  drawRules(); render(); drawClock();
  if (P.get("autostart") !== "0") start();
  connect();
  listenControl();
  if (P.get("demo") === "1") toggleDemo();
})();
