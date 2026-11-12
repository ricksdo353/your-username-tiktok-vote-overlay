# TikTok LIVE Vote Overlay (vertical 1080x1920)

Files: `index.html`, `style.css`, `script.js` (overlay) and `server.js` (optional TikTok relay).

## Use it
1. Put your character pictures next to `index.html` (e.g. `a.png`, `b.png`).
2. Add a **Browser / Link source** in TikTok LIVE Studio, OBS, or your Stream to Earn setup at 1080x1920:
   `file:///PATH/index.html?left=Goku&right=Naruto&leftImg=a.png&rightImg=b.png`
   (The background is transparent. Add `&preview=1` to see it on a dark background in a normal browser.)

## Connecting to TikTok LIVE (pick one)
- **TikFinity** running on the same PC: no setup needed. The overlay listens on `ws://localhost:21213/` by default.
- **Included relay**: `npm install` → `node server.js your_username`, then add `&ws=ws://localhost:8080` to the URL.

## Voting rules
- Comment `1` / `2` (or `A` / `B`, or the character's name) = +1 vote (2s cooldown per viewer)
- Gifts = diamonds × `giftMult` votes for the side the gifter last commented, or force a side with `&giftA=Rose&giftB=TikTok`
- Likes are off by default: `&likes=0.1` gives 1 vote per 10 likes
- Keys: `1`/`2` add a vote (hold Shift for +10), `R` resets, `D` runs a demo. `&demo=1` starts the demo when the page loads.

## Timer
- `&timer=60` (seconds) or `&timer=2:30` (minutes:seconds). With no timer parameter, no timer is shown.
- The timer starts automatically. With `&autostart=0` it waits until you press `T`.
- When it reaches 0, voting locks and the winner is shown (or "IT'S A TIE!").
- Keys: `T` start / restart, `Space` pause / resume, `[` / `]` = -15s / +15s, Shift+`[` / Shift+`]` = -1 min / +1 min, `R` = reset votes and timer.
