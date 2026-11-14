// Relay: TikTok LIVE  ->  this server  ->  ws://localhost:8080  ->  overlay
// Usage:  node server.js your_tiktok_username
// Then open the overlay with  ?ws=ws://localhost:8080
const { TikTokLiveConnection, WebcastEvent, ControlEvent } = require("tiktok-live-connector");
const { WebSocketServer } = require("ws");

const username = (process.argv[2] || process.env.TIKTOK_USER || "").replace(/^@/, "");
const PORT = parseInt(process.env.PORT || "8080", 10);
if (!username) {
  console.error("Usage: node server.js <tiktok_username>");
  process.exit(1);
}

const wss = new WebSocketServer({ port: PORT });
const send = (event, data) => {
  const msg = JSON.stringify({ event, data });
  wss.clients.forEach((c) => c.readyState === 1 && c.send(msg));
};
wss.on("connection", () => console.log("Overlay connected"));
console.log(`Overlay WebSocket on ws://localhost:${PORT}`);

// Flatten the connector's event objects into the simple shape script.js expects
const who = (d) => ({
  uniqueId: d.user?.uniqueId ?? d.uniqueId,
  nickname: d.user?.nickname ?? d.nickname,
});

let conn = null;
let retryTimer = null;

// Schedule exactly one reconnect, and drop the old connection first,
// so a stream end + disconnect can never leave two live connections
// (which would count every comment and gift twice).
function scheduleRetry(reason) {
  if (retryTimer) return;
  console.log(`${reason} - retrying in 10s`);
  const old = conn;
  conn = null;
  if (old) { old.removeAllListeners(); old.disconnect().catch(() => {}); }
  retryTimer = setTimeout(() => { retryTimer = null; start(); }, 10000);
}

function start() {
  // processInitialData: false = don't replay comments/gifts from before we connected
  const c = new TikTokLiveConnection(username, { processInitialData: false });
  conn = c;
  c.connect()
    .then((s) => console.log(`Connected to @${username}'s LIVE (room ${s.roomId})`))
    .catch((e) => { if (conn === c) scheduleRetry("Connect failed: " + (e.message || e)); });

  c.on(WebcastEvent.CHAT, (d) => send("chat", { ...who(d), comment: d.comment }));
  c.on(WebcastEvent.LIKE, (d) => send("like", { ...who(d), likeCount: d.likeCount }));
  c.on(WebcastEvent.MEMBER, (d) => send("member", who(d))); // viewer joined (the board welcomes them)
  c.on(WebcastEvent.GIFT, (d) => send("gift", {
    ...who(d),
    giftName: d.giftDetails?.giftName ?? d.giftName,
    giftPictureUrl: d.giftDetails?.giftImage?.giftPictureUrl ?? d.giftPictureUrl,
    diamondCount: d.giftDetails?.diamondCount ?? d.diamondCount,
    giftType: d.giftDetails?.giftType ?? d.giftType,
    repeatCount: d.repeatCount,
    repeatEnd: d.repeatEnd === undefined ? undefined : !!d.repeatEnd,
  }));
  c.on(WebcastEvent.STREAM_END, () => { if (conn === c) scheduleRetry("Stream ended"); });
  c.on(ControlEvent.DISCONNECTED, () => { if (conn === c) scheduleRetry("Disconnected"); });
  c.on(ControlEvent.ERROR, (e) => console.error("Connection error:", e?.message || e));
}
start();
