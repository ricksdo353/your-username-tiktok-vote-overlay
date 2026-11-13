/* =========================================================
   TikTok LIVE Vote Overlay
   ---------------------------------------------------------
   Configure with URL parameters, e.g.
   index.html?left=Goku&right=Naruto&leftImg=goku.png&rightImg=naruto.png
             &ws=ws://127.0.0.1:21213/&giftA=Rose&giftB=TikTok

   left / right       character names
   leftImg / rightImg image URL or local file (put files next to index.html)
   q                  title text (default "WHO WINS?")
   hint               text under the title (default "Comment 1 or 2 · Gifts = bonus votes")
   leftPos / rightPos which part of the photo to show, CSS object-position
                      (default "center 20%", keeps faces in frame)
   ws                 WebSocket event source (default ws://127.0.0.1:21213/,
                      which is TikFinity's local API; use ws://localhost:8080
                      for the included server.js relay). ws=off disables it.
   giftA / giftB      gift names that always count for side A / side B
                      (comma-separated for several, e.g. giftA=Rose,Finger%20Heart).
                      Other gifts count for the side the viewer commented.
   giftAImg / giftBImg picture for side A / B gifts (Rose and TikTok have built-in pictures)
   showGifts=1        show the gift tags on screen (off by default)
   giftMult           votes per diamond (default 1)
   likes              votes per like, e.g. likes=0.1 (default 0 = off)
   cooldown           ms between comment votes from the same viewer (default 2000)
   debug=1            show every vote / ignored event in the feed (to find
                      out where points come from)
   room               remote-control room name; open control.html?room=SAME to control
   host               your TikTok username: you can type !start !pause !reset
                      !end !timer 5:00 in your own LIVE chat
   bg                 full (default, like the promo video) | panel (dark card) | none (transparent, over a camera)
   bigGift            gifts worth this many coins or more get a full-screen takeover (default 100)
   takeover=0         turn the full-screen gift takeovers off
   countdown=0        turn the big 3-2-1 at the end of a round off
   preview=1          black page background for testing in a normal browser
   demo=1             fake random votes
   timer              round length: seconds (timer=90) or m:ss (timer=2:30).
                      Omit for no timer. When it hits 0, voting locks and
                      the winner is shown.
   autostart=0        don't start the timer on load (press T to start)
   next               seconds the winner stays on screen before the scores reset
                      to 0 and a new round starts by itself (default 15; next=0 = off)

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
    question: P.get("q") || "",                      // default: "מי ינצח?"
    hint: P.get("hint") || "",
    leftPos: P.get("leftPos") || "",
    rightPos: P.get("rightPos") || "",
    ws: P.get("ws") || "ws://127.0.0.1:21213/",
    // comma-separated gift names, e.g. giftA=Rose,Finger Heart
    giftA: (P.get("giftA") || "").split(",").map((g) => g.trim()).filter(Boolean),
    giftB: (P.get("giftB") || "").split(",").map((g) => g.trim()).filter(Boolean),
    giftMult: parseFloat(P.get("giftMult") || "1"),
    likes: parseFloat(P.get("likes") || "0"),
    cooldown: parseInt(P.get("cooldown") || "2000", 10),
    room: P.get("room") || "",                       // remote control room (control.html)
    ctrl: (P.get("ctrl") || "https://ntfy.sh").replace(/\/$/, ""),
    host: (P.get("host") || "").replace(/^@/, "").toLowerCase(), // your TikTok username for !commands
    bg: P.get("bg") || "full",                       // full | panel | none (transparent, for a camera stream)
    bigGift: parseInt(P.get("bigGift") || "100", 10), // gifts worth this many coins or more get a full-screen takeover
    takeover: P.get("takeover") !== "0",
    countdown: P.get("countdown") !== "0",           // big 3-2-1 at the end of a round
    next: Math.max(0, parseInt(P.get("next") ?? "15", 10) || 0), // auto reset + new round after the winner (s)
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
  document.body.classList.add("bg-" + (["full", "panel", "none"].includes(cfg.bg) ? cfg.bg : "full"));

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
  if (cfg.question) $("question").textContent = cfg.question;
  // older links put "מתנות = נקודות" in the hint; drop that part so the board never asks for gifts
  if (cfg.hint) $("hint").textContent = cfg.hint.replace(/\s*[·•|,-]?\s*מתנות\s*=\s*נקודות\s*/g, "").trim() || cfg.hint;
  // keep each header line on one row: shrink a long line instead of letting it wrap onto the timer
  function fitHeader(el) {
    el.style.whiteSpace = "nowrap"; el.style.padding = "0 30px"; el.style.fontSize = "";
    const max = parseFloat(getComputedStyle(el).fontSize) || 92;
    for (let fs = max; fs > 40 && el.scrollWidth > el.clientWidth + 1; fs -= 2) el.style.fontSize = fs + "px";
  }
  fitHeader($("question")); fitHeader($("hint"));
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => { fitHeader($("question")); fitHeader($("hint")); });

  // background dots (same as the video), drifting upward
  (function dots() {
    let seed = 7; const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
    const box = $("dots"), cols = ["#5fd0ff", "#d17bff", "#ffffff"];
    for (let i = 0; i < 26; i++) {
      const d = document.createElement("i"), sz = [6, 8, 10, 14][(rnd() * 4) | 0];
      d.style.cssText = `left:${(20 + rnd() * 1040) | 0}px;top:${(rnd() * 1920) | 0}px;width:${sz}px;height:${sz}px;` +
        `background:${cols[(rnd() * 3) | 0]};opacity:${(0.25 + rnd() * 0.45).toFixed(2)};animation-duration:${(20 + rnd() * 25).toFixed(1)}s`;
      box.appendChild(d);
    }
  })();

  // header alternates: round length (or the question) <-> how to vote
  setInterval(() => { $("question").classList.toggle("off"); $("hint").classList.toggle("off"); }, 5000);
  // show each side's gift on its card
  if (cfg.leftPos) $("imgA").style.objectPosition = cfg.leftPos;
  if (cfg.rightPos) $("imgB").style.objectPosition = cfg.rightPos;
  $("nameA").textContent = cfg.left;
  $("nameB").textContent = cfg.right;
  $("imgA").src = cfg.leftImg || placeholder("1", "#5fd0ff", "#1456c9");
  $("imgB").src = cfg.rightImg || placeholder("2", "#d17bff", "#4b14b5");
  $("imgA").onerror = () => ($("imgA").src = placeholder("1", "#5fd0ff", "#1456c9"));
  $("imgB").onerror = () => ($("imgB").src = placeholder("2", "#d17bff", "#4b14b5"));

  /* ---------- Gift pictures ---------- */
  // Built-in pictures for common gifts; others are learned from live gift events.
  const giftIcons = {
    rose: "images/gifts/rose.png",
    tiktok: "images/gifts/tiktok.png",
    "hand heart": "images/gifts/hand-heart.png",
    confetti: "images/gifts/confetti.png",
  };
  if (P.get("giftAImg")) cfg.giftA.forEach((g) => (giftIcons[g.toLowerCase()] = P.get("giftAImg")));
  if (P.get("giftBImg")) cfg.giftB.forEach((g) => (giftIcons[g.toLowerCase()] = P.get("giftBImg")));
  const giftIcon = (name) => giftIcons[String(name || "").toLowerCase()] || "";

  function giftNode(name) {
    const span = document.createElement("span");
    span.className = "gift-item";
    const url = giftIcon(name);
    if (url) {
      const img = document.createElement("img");
      img.className = "gift-icon"; img.alt = ""; img.src = url;
      img.onerror = () => img.replaceWith(document.createTextNode("🎁"));
      span.appendChild(img);
    } else span.append("🎁");
    span.append(" " + name);
    return span;
  }

  function drawGiftChips() {
    [["giftTagA", cfg.giftA], ["giftTagB", cfg.giftB]].forEach(([id, list]) => {
      const el = $(id);
      el.replaceChildren();
      list.forEach((g) => el.appendChild(giftNode(g)));
      // gift tags are off by default (showGifts=1 turns them on): a board that keeps
      // advertising gifts can be treated by TikTok as gift solicitation
      el.classList.toggle("hidden", !list.length || P.get("showGifts") !== "1");
    });
  }
  drawGiftChips();

  /* ---------- Rendering ---------- */
  const fmt = (n) => (n >= 1e6 ? (n / 1e6).toFixed(1) + "M" : n >= 1e4 ? (n / 1e3).toFixed(1) + "K" : String(Math.floor(n)));

  function render() {
    const total = state.a + state.b;
    const pa = total ? Math.round((state.a / total) * 100) : 50;
    const pb = 100 - pa;
    $("scoreA").textContent = fmt(state.a);
    $("scoreB").textContent = fmt(state.b);
    // keep a sliver of each colour visible so labels never vanish
    $("barA").style.width = Math.min(Math.max(pa, 12), 88) + "%";
    $("pctA").textContent = pa + "%";
    $("pctB").textContent = pb + "%";
    $("cardA").classList.toggle("leading", state.a > state.b);
    $("cardB").classList.toggle("leading", state.b > state.a);
  }

  /* ---------- Effects (Web Animations; all optional eye candy) ---------- */
  const anim = (el, frames, opts) => { try { return el.animate(frames, opts); } catch (_) { return null; } };
  const sideName = (side) => (side === "a" ? cfg.left : cfg.right);

  function bump(side, strong) {
    anim($(side === "a" ? "cardA" : "cardB"),
      [{ transform: "scale(1)" }, { transform: `scale(${strong ? 1.12 : 1.08})` }, { transform: "scale(1)" }],
      { duration: 200, easing: "ease-out" });
    anim($(side === "a" ? "barFlashA" : "barFlashB"), [{ opacity: 0.75 }, { opacity: 0 }], { duration: 380, easing: "ease-out" });
  }

  function shake(el, amp = 14) {
    anim(el, [{ transform: "translate(0,0)" }, { transform: `translate(${-amp}px,${amp / 2}px)` }, { transform: `translate(${amp - 2}px,${-amp / 2}px)` },
      { transform: `translate(${-amp / 2}px,4px)` }, { transform: "translate(0,0)" }], { duration: 220 });
  }

  // a gift slides in from its side of the screen into the bar
  function flyGift(side, icon) {
    if (!icon) return;
    const img = document.createElement("img");
    img.className = "fly-gift " + side; img.alt = ""; img.src = icon;
    img.style.left = (side === "a" ? -300 : 1100) + "px"; img.style.top = "812px";
    $("flyLayer").appendChild(img);
    const dx = side === "a" ? 710 : -690;
    const a = anim(img, [{ transform: "translate(0,0) scale(1.4)", opacity: 0 }, { transform: "translate(0,0) scale(1.4)", opacity: 1, offset: 0.15 },
      { transform: `translate(${dx}px,0) scale(.5)`, opacity: 1, offset: 0.9 }, { transform: `translate(${dx}px,0) scale(.5)`, opacity: 0 }], { duration: 400, easing: "ease-in" });
    setTimeout(() => img.remove(), 440);
    if (!a) img.remove();
    setTimeout(() => anim($("dash"), [{ transform: "scale(1) rotate(0)" }, { transform: `scale(1.04) rotate(${side === "a" ? 1.2 : -1.2}deg)`, offset: 0.25 }, { transform: "scale(1) rotate(0)" }],
      { duration: 330, easing: "ease-out" }), 320);
  }

  // a comment bubble flies from the chat strip into the face
  let lastFly = 0;
  function flyVote(side) {
    const now = Date.now();
    if (now - lastFly < 220) return; // keep busy chats readable
    lastFly = now;
    const b = document.createElement("div");
    b.className = "fly-vote " + side; b.textContent = side === "a" ? "1" : "2";
    b.style.left = (side === "a" ? 170 : 790) + "px"; b.style.top = "1420px";
    $("flyLayer").appendChild(b);
    anim(b, [{ transform: "translate(0,0) scale(.6)", opacity: 0 }, { transform: "translate(0,-40px) scale(1)", opacity: 1, offset: 0.2 },
      { transform: "translate(0,-800px) scale(.6)", opacity: 1, offset: 0.9 }, { transform: "translate(0,-820px) scale(.3)", opacity: 0 }],
      { duration: 520, easing: "ease-in" });
    setTimeout(() => b.remove(), 560);
  }

  // full-screen moment for big gifts
  let tkTimer = null;
  function takeover(side, icon, votes) {
    if (!cfg.takeover) return;
    const t = $("takeover");
    t.className = "abs " + side;
    $("tkVal").textContent = "+" + votes.toLocaleString("en-US");
    $("tkImg").src = icon || ""; $("tkImg").style.visibility = icon ? "visible" : "hidden";
    $("tkName").textContent = "ל" + sideName(side);
    anim(t, [{ opacity: 0 }, { opacity: 1, offset: 0.1 }, { opacity: 1, offset: 0.85 }, { opacity: 0 }], { duration: 900, easing: "linear" });
    anim($("tkImg"), [{ transform: "scale(.3) rotate(-12deg)" }, { transform: "scale(1.12) rotate(0)", offset: 0.25 }, { transform: "scale(1)", offset: 0.7 }, { transform: "translateY(330px) scale(.2)" }], { duration: 900, easing: "ease-out" });
    anim($("tkVal"), [{ transform: "scale(2)" }, { transform: "scale(1)", offset: 0.2 }, { transform: "scale(1)" }], { duration: 900 });
    clearTimeout(tkTimer);
    tkTimer = setTimeout(() => { bump(side, true); shake($("dash"), 18); }, 650);
  }

  // gift / event pill under the scores
  let toastTimer = null;
  function toast(html, side, icon) {
    const t = $("toast");
    t.className = "abs he show " + side;
    t.replaceChildren();
    if (icon) { const img = document.createElement("img"); img.src = icon; img.alt = ""; img.onerror = () => img.remove(); t.appendChild(img); }
    const span = document.createElement("span"); span.innerHTML = html; t.appendChild(span);
    // shrink long names until the pill fits (66px like the video, down to 36px)
    t.style.fontSize = "66px";
    for (let fs = 66; fs > 36 && t.scrollWidth > t.clientWidth; fs -= 4) t.style.fontSize = fs + "px";
    document.body.classList.add("toasting");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { t.classList.remove("show"); document.body.classList.remove("toasting"); }, 1600);
  }
  const esc = (x) => String(x).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  // live chat strip: newest message enters on the right
  let chipRow = 0;
  const avCols = ["#ffb347", "#7cf2c8", "#ff7bac", "#9fb4ff", "#ffd34d"];
  function chatChip(user, side, icon) {
    const row = $("tickerRow" + (chipRow ^= 1));
    const c = document.createElement("div");
    c.className = "chip";
    const av = document.createElement("span"); av.className = "av";
    av.style.background = avCols[[...String(user)].reduce((h, ch) => h + ch.charCodeAt(0), 0) % avCols.length];
    const who = document.createElement("span"); who.className = "who"; who.textContent = user;
    c.append(av, who);
    if (icon) { const img = document.createElement("img"); img.src = icon; img.alt = ""; img.onerror = () => img.remove(); c.appendChild(img); }
    else { const v = document.createElement("span"); v.className = "v " + side; v.textContent = side === "a" ? "1" : "2"; c.appendChild(v); }
    row.prepend(c);
    while (row.children.length > 6) row.lastChild.remove();
  }

  function feed(text, side, icon) {
    const box = $("feed");
    const div = document.createElement("div");
    div.className = "item " + side;
    if (icon) {
      const img = document.createElement("img");
      img.className = "gift-icon"; img.alt = ""; img.src = icon;
      img.onerror = () => img.replaceWith(document.createTextNode("🎁"));
      div.append(img, " ");
    }
    div.append(text);
    box.appendChild(div);
    while (box.children.length > 2) box.removeChild(box.firstChild);
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
  let nextRoundId = null; // pending automatic next round

  const mmss = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;

  function drawTimer() {
    const el = $("timer");
    el.classList.toggle("hidden", timer.duration <= 0 && !timer.running);
    if (!cfg.question) {
      const mins = Math.round(timer.duration / 60), q = $("question");
      const html = timer.duration > 0
        ? (mins >= 1 ? `<span class="grad">${mins} דקות</span> לכל סבב` : `<span class="grad">${timer.duration} שניות</span> לכל סבב`)
        : `מי <span class="grad">ינצח?</span>`;
      if (q.innerHTML !== html) { q.innerHTML = html; fitHeader(q); }
    }
    $("timerText").textContent = timer.ended ? "0:00" : mmss(Math.ceil(timer.remaining));
    el.classList.toggle("paused", !timer.running && !timer.ended);
    el.classList.toggle("urgent", timer.running && timer.remaining <= 10);
    el.classList.toggle("done", timer.ended);
  }

  let lastCount = 0;
  function tick() {
    timer.remaining = Math.max(0, (timer.endAt - Date.now()) / 1000);
    const c = Math.ceil(timer.remaining);
    if (cfg.countdown && timer.running && c >= 1 && c <= 3 && c !== lastCount) {
      lastCount = c;
      const cd = $("countdown");
      cd.textContent = String(c);
      anim(cd, [{ transform: "scale(2.4)", opacity: 0 }, { transform: "scale(1)", opacity: 1, offset: 0.2 }, { transform: "scale(.9)", opacity: 1, offset: 0.8 }, { transform: "scale(.6)", opacity: 0 }], { duration: 900, easing: "ease-out" });
      anim($("dim"), [{ opacity: 0 }, { opacity: 0.65, offset: 0.15 }, { opacity: 0.6, offset: 0.8 }, { opacity: 0 }], { duration: 900 });
      shake($("stage"), 10);
    }
    if (c > 3) lastCount = 0;
    if (timer.remaining <= 0) finishRound();
    drawTimer();
  }

  function startTimer(seconds) {
    if (seconds > 0) timer.duration = seconds; // ignore missing/invalid times
    if (timer.duration <= 0) return;
    clearTimeout(nextRoundId);
    timer.remaining = timer.duration;
    timer.ended = false;
    $("winner").classList.add("hidden");
    document.body.classList.remove("ended");
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
    document.body.classList.add("ended");
    if (state.a === state.b) {
      $("winnerName").innerHTML = `צמוד! <span class="grad">תיקו</span>`;
      $("split").querySelectorAll(".half").forEach((h) => (h.style.opacity = "1"));
      anim($("split"), [{ opacity: 0 }, { opacity: 1, offset: 0.1 }, { opacity: 0 }], { duration: 560 });
    } else {
      const side = state.a > state.b ? "a" : "b";
      w.classList.add(side);
      $("winnerName").textContent = `🏆 ${sideName(side)}`;
      $("split").querySelectorAll(".half").forEach((h) => (h.style.opacity = h.classList.contains(side) ? "1" : "0"));
      anim($("split"), [{ opacity: 0 }, { opacity: 1, offset: 0.1 }, { opacity: 0 }], { duration: 700 });
      bump(side, true);
    }
    // restart the line's slam animation
    w.style.animation = "none"; void w.offsetWidth; w.style.animation = "";
    shake($("stage"), 22);
    drawTimer();
    // after showing the winner, reset to 0:0 and start the next round by itself
    clearTimeout(nextRoundId);
    if (cfg.next > 0 && timer.duration > 0) {
      nextRoundId = setTimeout(() => { reset(); startTimer(); }, cfg.next * 1000);
    }
  }

  function add(side, n = 1, label, icon) {
    if (side !== "a" && side !== "b") return;
    if (timer.ended) return; // round over: votes locked
    state[side] += n;
    render();
    bump(side, n >= 10);
    if (label) toast(label, side, icon);
  }

  function reset() {
    clearTimeout(nextRoundId);
    state.a = state.b = 0;
    likeCarry.a = likeCarry.b = 0;
    lastVote.clear();
    viewerSide.clear();
    render();
    // reset the timer too: back to full length, stopped (T starts it)
    clearInterval(timer.tickId);
    timer.running = false;
    timer.ended = false;
    timer.remaining = timer.duration;
    $("winner").classList.add("hidden");
    document.body.classList.remove("ended");
    drawTimer();
  }

  /* ---------- Voting window & debug ---------- */
  // With a timer, TikTok votes/gifts count only while the round is running.
  // Without a timer, they always count (until reset).
  function votingOpen() {
    if (timer.ended) return false;
    return timer.duration <= 0 || timer.running;
  }
  const DEBUG = P.get("debug") === "1";
  function debugLog(text, side) { if (DEBUG) feed(text, side || ""); }

  /* ---------- TikTok event handling ---------- */
  // Values can arrive as numbers or strings ("1", "false") depending on the connector
  const pick = (...v) => v.find((x) => x !== undefined && x !== null && x !== "");
  const num = (v, def = 0) => { const n = Number(v); return Number.isFinite(n) ? n : def; };
  const bool = (v) => v === true || v === 1 || v === "1" || String(v).toLowerCase() === "true";

  // Accepts both {event, data} (TikFinity / server.js) and flat objects.
  function handle(msg) {
    if (!msg || typeof msg !== "object") return;
    const type = String(msg.event || msg.type || msg.data?.event || msg.data?.type || "").toLowerCase();
    const d = msg.data && typeof msg.data === "object" ? msg.data : msg;
    const u = d.user || {};
    const user = pick(d.nickname, u.nickname, d.uniqueId, u.uniqueId) || "viewer";
    const id = String(pick(d.uniqueId, u.uniqueId, d.userId, u.userId) || user);

    if (type === "chat" || type === "comment") {
      const text = String(d.comment || d.text || "").trim().toLowerCase();
      if (cfg.host && text.startsWith("!") && String(pick(d.uniqueId, u.uniqueId) || "").toLowerCase() === cfg.host) {
        command(text.slice(1));
        return;
      }
      // Only a comment that is exactly "1" / "2" (or the full name) is a vote
      const clean = text.replace(/[\s!.?,️⃣]+/g, "");
      let side = null;
      if (clean === "1" || text === cfg.left.toLowerCase()) side = "a";
      else if (clean === "2" || text === cfg.right.toLowerCase()) side = "b";
      if (!side) return;
      viewerSide.set(id, side);
      if (!votingOpen()) return debugLog(`⏸ ${user}: ${text} (סבב לא פעיל)`);
      const now = Date.now();
      if (now - (lastVote.get(id) || 0) < cfg.cooldown) return;
      lastVote.set(id, now);
      add(side, 1);
      chatChip(user, side);
      flyVote(side);
      debugLog(`💬 ${user} +1 → ${side === "a" ? cfg.left : cfg.right}`, side);
    }

    else if (type === "gift") {
      const det = d.giftDetails || d.gift || {};
      const ext = d.extendedGiftInfo || {};
      // Streakable gifts (giftType 1) send an event for every gift in the streak with a
      // running repeatCount; count only the final one (repeatEnd).
      const giftType = num(pick(d.giftType, det.giftType, ext.type), 0);
      if (giftType === 1 && !bool(pick(d.repeatEnd, d.repeat_end))) return;
      const name = String(pick(d.giftName, det.giftName, d.gift_name, ext.name) || "").toLowerCase();
      let side = viewerSide.get(id) || null;
      if (cfg.giftA.some((g) => g.toLowerCase() === name)) side = "a";
      if (cfg.giftB.some((g) => g.toLowerCase() === name)) side = "b";
      if (!side) return debugLog(`🎁 ${user}: ${name} (לא בחר צד)`); // viewer hasn't picked a side yet
      if (!votingOpen()) return debugLog(`⏸ 🎁 ${user}: ${name} (סבב לא פעיל)`);
      const pic = pick(d.giftPictureUrl, d.giftImageUrl, det.giftPictureUrl, det.giftImage?.giftPictureUrl,
        ext.image?.url_list?.[0], d.gift?.icon?.url_list?.[0]) || "";
      if (pic && !giftIcon(name)) { giftIcons[name] = pic; drawGiftChips(); }
      const each = Math.max(1, num(pick(d.diamondCount, det.diamondCount, d.diamond_count, ext.diamond_count, d.coins), 1));
      const count = Math.max(1, Math.floor(num(pick(d.repeatCount, d.repeat_count, d.comboCount), 1)));
      const diamonds = each * count;
      const votes = Math.max(1, Math.round(diamonds * cfg.giftMult));
      const icon = giftIcon(name);
      add(side, votes, `${icon ? "" : "🎁 "}<b class="ltr">+${votes.toLocaleString("en-US")}</b> ל${esc(sideName(side))}`, icon);
      chatChip(user, side, icon);
      flyGift(side, icon);
      if (each >= cfg.bigGift || votes >= cfg.bigGift) takeover(side, icon, votes);
    }

    else if (type === "like" && cfg.likes > 0) {
      const side = viewerSide.get(id);
      if (!side || !votingOpen()) return;
      likeCarry[side] += Math.max(1, num(pick(d.likeCount, d.count), 1)) * cfg.likes;
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
      const r = Math.random();
      if (r < 0.015) handle({ event: "gift", data: { nickname: "fan" + ((Math.random() * 99) | 0), uniqueId: "demo" + side, giftName: side === "a" ? "Hand Heart" : "Confetti", diamondCount: 100, repeatCount: 1 } });
      else if (r < 0.08) handle({ event: "gift", data: { nickname: "fan" + ((Math.random() * 99) | 0), uniqueId: "demo" + side, giftName: side === "a" ? "Rose" : "TikTok", diamondCount: 1, repeatCount: 1 } });
      else { viewerSide.set("demo" + side, side); add(side, 1); chatChip("demo", side); flyVote(side); }
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
      case "end":    finishRound(); break;
      case "timer":
        timer.duration = Math.max(0, parseTime(x || "0"));
        if (!timer.running) { timer.remaining = timer.duration; timer.ended = false; $("winner").classList.add("hidden"); document.body.classList.remove("ended"); }
        drawTimer(); break;
      case "adjust": adjust(parseInt(x, 10) || 0); break;
      case "add":    add(side, Math.max(1, parseInt(y, 10) || 1)); break;
      case "sub":    if (!timer.ended) { state[side] = Math.max(0, state[side] - Math.max(1, parseInt(y, 10) || 1)); render(); } break;
      case "demo":   toggleDemo(); break;
    }
  }

  // Control panel channel: control.html publishes to ntfy.sh/<topic>, we listen via SSE
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
    window.Relay.listen("tvo-" + cfg.room, (text) => command(text), (ok) => setCtrl(ok));
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
