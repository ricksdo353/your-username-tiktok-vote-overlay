/* Says "thank you <name>" out loud for gifts (browser speech, if the computer has a voice for the language).
   Several gifts in a row are merged into one sentence, at most one sentence every 4 seconds.
   URL: voice=0 turns it off. */
(function () {
  const P = new URLSearchParams(location.search);
  const on = P.get("voice") !== "0" && "speechSynthesis" in window;
  let queue = [], busy = false, voices = [];
  const load = () => { try { voices = speechSynthesis.getVoices(); } catch (_) { voices = []; } };
  if (on) { load(); try { speechSynthesis.onvoiceschanged = load; } catch (_) { /* ignore */ } }
  const clean = (s) => String(s || "").replace(/[_\-.]+/g, " ").replace(/[^\p{L}\p{N} ]/gu, "").trim().slice(0, 24);
  function flush(lang) {
    if (busy || !queue.length) return;
    const names = [...new Set(queue)].slice(0, 3); queue = [];
    const he = lang === "he";
    const text = he ? "תודה " + names.join(" ו") : "Thank you " + names.join(" and ");
    try {
      const u = new SpeechSynthesisUtterance(text);
      u.lang = he ? "he-IL" : "en-US";
      const v = voices.find((x) => x.lang && x.lang.toLowerCase().startsWith(he ? "he" : "en"));
      if (v) u.voice = v;
      u.rate = 1.05; u.volume = 1;
      busy = true;
      const done = () => { setTimeout(() => { busy = false; flush(lang); }, 4000); };
      u.onend = done; u.onerror = done;
      speechSynthesis.speak(u);
    } catch (_) { busy = false; }
  }
  window.SpeakThanks = (name, lang) => {
    if (!on) return;
    const n = clean(name);
    if (!n) return;
    queue.push(n);
    if (queue.length > 6) queue = queue.slice(-6);
    flush(lang || "he");
  };
})();
