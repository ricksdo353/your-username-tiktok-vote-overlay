// Relay: TikTok LIVE  ->  this server  ->  ws://localhost:8080  ->  overlay
// Usage:  node server.js your_tiktok_username
// Then open the overlay with  ?ws=ws://localhost:8080
const { TikTokLiveConnection, WebcastEvent } = require("tiktok-live-connector");
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

function start() {
  const conn = new TikTokLiveConnection(username);
  conn.connect()
    .then((s) => console.log(`Connected to @${username}'s LIVE (room ${s.roomId})`))
    .catch((e) => { console.error("Connect failed:", e.message || e, "- retrying in 10s"); setTimeout(start, 10000); });

  conn.on(WebcastEvent.CHAT, (d) => send("chat", { ...who(d), comment: d.comment }));
  conn.on(WebcastEvent.LIKE, (d) => send("like", { ...who(d), likeCount: d.likeCount }));
  conn.on(WebcastEvent.GIFT, (d) => send("gift", {
    ...who(d),
    giftName: d.giftDetails?.giftName ?? d.giftName,
    diamondCount: d.giftDetails?.diamondCount ?? d.diamondCount,
    giftType: d.giftDetails?.giftType ?? d.giftType,
    repeatCount: d.repeatCount,
    repeatEnd: d.repeatEnd === undefined ? undefined : !!d.repeatEnd,
  }));
  conn.on(WebcastEvent.STREAM_END, () => { console.log("Stream ended"); setTimeout(start, 10000); });
  conn.on("disconnected", () => { console.log("Disconnected - retrying in 10s"); setTimeout(start, 10000); });
}
start();
