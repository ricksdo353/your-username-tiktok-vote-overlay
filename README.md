# TikTok LIVE Vote Overlay

A vertical (1080×1920) **"Who wins?" voting overlay** for TikTok LIVE in blue and purple:
two characters with pictures, live score counters, a VS badge, a percentage bar, gift
pop-ups, and an optional countdown timer that announces the winner.

![Overlay preview](preview.png)
![Timer and winner screen](preview-timer.png)

---

## Table of contents

1. [How it works](#1-how-it-works)
2. [What you need](#2-what-you-need)
3. [Step 1 – Download the overlay](#step-1--download-the-overlay)
4. [Step 2 – Add your character pictures](#step-2--add-your-character-pictures)
5. [Step 3 – Build your overlay link](#step-3--build-your-overlay-link)
6. [Step 4 – Test it in your browser](#step-4--test-it-in-your-browser)
7. [Step 5 – Connect it to your TikTok LIVE](#step-5--connect-it-to-your-tiktok-live)
   - [Option A: TikFinity (easiest)](#option-a-tikfinity-easiest)
   - [Option B: The included relay server (free, uses Node.js)](#option-b-the-included-relay-server-free-uses-nodejs)
8. [Step 6 – Put the overlay on your stream](#step-6--put-the-overlay-on-your-stream)
   - [TikTok LIVE Studio](#tiktok-live-studio)
   - [OBS Studio](#obs-studio)
   - [Stream to Earn](#stream-to-earn)
9. [Step 7 – Go live and run a round](#step-7--go-live-and-run-a-round)
10. [Optional – Host it online with GitHub Pages](#optional--host-it-online-with-github-pages)
11. [All settings](#all-settings)
12. [Keyboard controls](#keyboard-controls)
13. [Troubleshooting](#troubleshooting)

---

## 1. How it works

```
 Viewers comment "1" / "2" and send gifts
                 │
                 ▼
         TikTok LIVE servers
                 │
                 ▼
  A connector on YOUR PC  ─────────────►  the overlay (index.html)
  (TikFinity  OR  server.js)   WebSocket    shown in TikTok LIVE Studio / OBS
```

The overlay is just a web page. It can't read TikTok on its own, so a small program on
your computer (**TikFinity** or the included **server.js**) connects to your LIVE and
passes comments, gifts and likes to the overlay through a local WebSocket connection.

**Voting rules (default):**

| Viewer action | Effect |
|---|---|
| Comments `1`, `A`, `team 1` or the left character's name | +1 vote for the left (blue) side |
| Comments `2`, `B`, `team 2` or the right character's name | +1 vote for the right (purple) side |
| Sends a gift | +1 vote per diamond for the side they last commented |
| Likes | Off by default (can be turned on) |

Each viewer can cast a comment vote once every 2 seconds, so spam doesn't take over.

---

## 2. What you need

- A Windows or Mac computer (the overlay runs on your PC, not your phone).
- **TikTok LIVE Studio** or **OBS Studio** to stream, plus access to go LIVE on TikTok.
- **One** of these connectors:
  - **TikFinity** (easiest, no coding) – https://tikfinity.zerody.one
  - **Node.js 18 or newer** (free) to run the included `server.js` – https://nodejs.org
- Two pictures of your characters (PNG or JPG; square images look best).

---

## Step 1 – Download the overlay

**Easiest way (no Git needed):**

1. Open this repository on GitHub.
2. Click the green **Code** button → **Download ZIP**.
3. Unzip it somewhere easy to find, e.g. `C:\overlay\` (Windows) or `~/overlay/` (Mac).

**Or with Git:**

```bash
git clone https://github.com/ricksdo353/your-username-tiktok-vote-overlay.git
```

You should now have a folder containing `index.html`, `style.css`, `script.js`,
`server.js`, and the other files.

---

## Step 2 – Add your character pictures

1. Copy your two images **into the same folder as `index.html`**.
2. Give them short names without spaces, e.g. `left.png` and `right.png`.

> If you skip this step, the overlay shows blue and purple placeholder avatars.
> You can also use an online image address (a link that starts with `https://`).

---

## Step 3 – Build your overlay link

You choose the names, pictures and timer by adding settings to the end of the overlay's
address. Start from the full path to `index.html` on your PC:

- **Windows:** `file:///C:/overlay/index.html`
- **Mac:** `file:///Users/YOURNAME/overlay/index.html`

> Tip: drag `index.html` into Chrome; the address bar then shows the exact path.

Then add `?` and your settings, separated by `&`. Example:

```
file:///C:/overlay/index.html?left=Goku&right=Naruto&leftImg=left.png&rightImg=right.png&timer=2:00
```

| Part | Meaning |
|---|---|
| `left=Goku` | Name of the left (blue) character |
| `right=Naruto` | Name of the right (purple) character |
| `leftImg=left.png` | Left picture |
| `rightImg=right.png` | Right picture |
| `timer=2:00` | 2-minute round (leave it out for no timer) |

Names with spaces use `%20`, e.g. `left=Blue%20Knight`.
See [All settings](#all-settings) for everything else you can change.

---

## Step 4 – Test it in your browser

Before going live, check that everything looks right:

1. Open your link in **Chrome** and add `&preview=1&demo=1` to the end:
   ```
   file:///C:/overlay/index.html?left=Goku&right=Naruto&leftImg=left.png&rightImg=right.png&preview=1&demo=1
   ```
2. You should see fake votes coming in and the bar moving.
3. Click the page, then press `D` to stop the demo, `R` to reset, `1`/`2` to add votes.

`preview=1` only adds a dark background for testing. Remove it, and `demo=1`, for the
real stream, because the overlay is meant to be transparent.

The small label in the bottom-right corner shows the connection:
**● connected** (green) means it is receiving TikTok events; **reconnecting…** means no
connector is running yet. That's expected until you finish Step 5.

---

## Step 5 – Connect it to your TikTok LIVE

Pick **one** option.

### Option A: TikFinity (easiest)

TikFinity is a free desktop app that connects to your TikTok LIVE and shares the events
on your PC. The overlay listens to TikFinity **automatically** (on `ws://localhost:21213/`),
so you don't need to add anything to your link.

1. Download and install TikFinity from https://tikfinity.zerody.one and open it.
2. Log in / enter **your TikTok username** and connect it to your LIVE.
3. Start your TikTok LIVE (TikFinity only receives events while you're live).
4. Open or reload the overlay. The corner label should turn **● connected**.

> If it stays on "reconnecting…", make sure the TikFinity desktop app is open (not just the
> website) and look in its settings for the WebSocket / API option being enabled.

### Option B: The included relay server (free, uses Node.js)

`server.js` connects to your TikTok LIVE using the open-source
`tiktok-live-connector` library and sends the events to the overlay.

1. Install **Node.js** (the "LTS" version) from https://nodejs.org.
2. Open a terminal **in the overlay folder**:
   - **Windows:** open the folder in File Explorer, click the address bar, type `cmd`, press Enter.
   - **Mac:** right-click the folder in Finder → **New Terminal at Folder**.
3. Install the dependencies (only needed once):
   ```bash
   npm install
   ```
4. **Start your TikTok LIVE first**, then run the relay with your username (without the `@`):
   ```bash
   node server.js your_tiktok_username
   ```
   You should see:
   ```
   Overlay WebSocket on ws://localhost:8080
   Connected to @your_tiktok_username's LIVE (room 123456789)
   ```
5. Add `&ws=ws://localhost:8080` to your overlay link, e.g.
   ```
   file:///C:/overlay/index.html?left=Goku&right=Naruto&leftImg=left.png&rightImg=right.png&ws=ws://localhost:8080
   ```
6. The terminal will print `Overlay connected` and the overlay's label turns **● connected**.

Keep the terminal window open during your whole stream. If you go live before starting
the relay, or the LIVE drops, the relay retries every 10 seconds on its own.

---

## Step 6 – Put the overlay on your stream

### TikTok LIVE Studio

1. Open TikTok LIVE Studio and choose **vertical (portrait)** layout.
2. Under **Sources**, click **+ / Add Source** and pick the web-page source
   (it's called **Link** or **Browser** depending on your version).
3. Paste your overlay link from Step 3 (with `&ws=...` if you use Option B).
4. Set the size to **1080 × 1920**.
5. Drag it above your camera source in the source list so it appears on top. Resize it if
   you want it smaller.

> Some versions of LIVE Studio don't accept `file:///` links. If yours doesn't, use the
> [GitHub Pages](#optional--host-it-online-with-github-pages) address instead. It
> still connects to TikFinity / server.js on your PC.

### OBS Studio

1. **Settings → Video**: set Base and Output resolution to **1080x1920** (vertical).
2. In **Sources**, click **+** → **Browser**, give it a name, click OK.
3. Tick **Local file** and pick `index.html`, **or** untick it and paste your full link
   in **URL** (you need the URL to use settings like `left=` and `timer=`).
4. Width **1080**, Height **1920**. Click OK.
5. To stream to TikTok from OBS you need a TikTok **Server URL + Stream Key**
   (available in LIVE Studio / TikTok's LIVE settings if your account has access). Paste
   them in **Settings → Stream → Service: Custom**.

### Stream to Earn

The overlay is a regular web page, so it works in any tool that lets you add a
**browser / link / custom HTML source**:

1. In Stream to Earn, add a browser, link or custom-overlay source.
2. Paste the same overlay link (preferably the GitHub Pages one).
3. Keep TikFinity or `server.js` running on the PC that streams, so votes reach the overlay.

> Stream to Earn doesn't publish a way for custom overlays to receive its live events, so
> the votes come from TikFinity or `server.js`, not from Stream to Earn itself.

---

## Step 7 – Go live and run a round

1. Start your TikTok LIVE.
2. Start TikFinity **or** `node server.js your_username`.
3. Check the overlay's corner label says **● connected**.
4. Tell viewers: *"Comment 1 for Goku, 2 for Naruto, gifts are bonus votes!"*
5. If you set a timer, it starts by itself (or press `T` if you used `autostart=0`).
   When it hits **0:00**, voting locks and the winner banner appears.
6. Press `R` to reset for the next round, then `T` to start the timer again.

**Using the keyboard while live:** keys only work when the overlay itself has focus.

- **OBS:** right-click the browser source → **Interact**, then press keys in that window.
- **LIVE Studio:** if your version has no "interact" option, start each round by reloading
  the source (with a timer and autostart, the round starts automatically).

---

## Optional – Host it online with GitHub Pages

Hosting the overlay gives it a normal `https://` address that works in every streaming app.

1. In this repository on GitHub, go to **Settings → Pages**.
2. Under **Build and deployment**, choose **Deploy from a branch**, branch **main**,
   folder **/ (root)**, and click **Save**.
3. After about a minute, your overlay is at:
   ```
   https://ricksdo353.github.io/your-username-tiktok-vote-overlay/
   ```
4. Upload your character images to the repository (**Add file → Upload files**) and use
   them like before:
   ```
   https://ricksdo353.github.io/your-username-tiktok-vote-overlay/?left=Goku&right=Naruto&leftImg=left.png&rightImg=right.png&timer=2:00
   ```

The online version still talks to TikFinity / `server.js` on **your** PC, so you still
need one of them running while you stream.

> If you rename the repository, the Pages address changes to the new name.

---

## All settings

Add these to the link after `?`, separated by `&`.

| Setting | Example | What it does | Default |
|---|---|---|---|
| `left` | `left=Goku` | Left (blue) character name | `Player One` |
| `right` | `right=Naruto` | Right (purple) character name | `Player Two` |
| `leftImg` | `leftImg=left.png` | Left picture (file or `https://` link) | placeholder |
| `rightImg` | `rightImg=right.png` | Right picture | placeholder |
| `q` | `q=BEST%20HERO%3F` | Title text | `WHO WINS?` |
| `timer` | `timer=90` or `timer=2:30` | Round length (seconds or m:ss) | no timer |
| `autostart` | `autostart=0` | Wait for `T` before starting the timer | starts automatically |
| `ws` | `ws=ws://localhost:8080` | Where to get TikTok events (`ws=off` to disable) | `ws://localhost:21213/` (TikFinity) |
| `giftA` | `giftA=Rose` | This gift always votes for the left side | – |
| `giftB` | `giftB=TikTok` | This gift always votes for the right side | – |
| `giftMult` | `giftMult=2` | Votes per diamond | `1` |
| `likes` | `likes=0.1` | Votes per like (0.1 = 1 vote per 10 likes) | `0` (off) |
| `cooldown` | `cooldown=5000` | Milliseconds between comment votes per viewer | `2000` |
| `preview` | `preview=1` | Dark background for testing | off |
| `demo` | `demo=1` | Fake votes for testing | off |

**Full example:**

```
index.html?left=Goku&right=Naruto&leftImg=left.png&rightImg=right.png&timer=3:00&giftA=Rose&giftB=TikTok&likes=0.05
```

---

## Keyboard controls

| Key | Action |
|---|---|
| `1` / `2` | +1 vote left / right (hold `Shift` for +10) |
| `R` | Reset votes and timer |
| `D` | Start / stop demo mode |
| `T` | Start / restart the timer (60s if no `timer` was set) |
| `Space` | Pause / resume the timer |
| `[` / `]` | Timer −15s / +15s |
| `Shift` + `[` / `]` | Timer −1 min / +1 min |

Before a round starts, `[` and `]` change the round length; during a paused round they
change only the time left.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Label stays on **reconnecting…** | No connector is running. Start TikFinity or `node server.js username`. With server.js, check the link has `&ws=ws://localhost:8080`. |
| `Connect failed` in the terminal | You're not live yet, or the username is wrong (no `@`). Go live; it retries every 10 seconds. |
| `node` / `npm` is not recognized | Install Node.js from nodejs.org, then close and reopen the terminal. |
| Pictures don't show | The image must be in the same folder as `index.html` (or on GitHub Pages), and the name must match exactly, including `.png`/`.jpg` and upper/lower case. |
| Overlay has a dark background on stream | Remove `preview=1` from the link. |
| Overlay is cut off or tiny | Set the source size to 1080 × 1920. The overlay scales itself to fit. |
| Gifts don't count | The gifter must comment `1` or `2` first, or set `giftA` / `giftB` so certain gifts always count. |
| Keys don't work | The overlay needs focus. In OBS use **Interact** on the source. |
| Changes don't appear | Refresh the source (OBS: right-click → **Refresh cache of current page**). |

---

### Files

| File | Purpose |
|---|---|
| `index.html` | The overlay page |
| `style.css` | Colors, layout and animations |
| `script.js` | Voting, timer, and TikTok event handling |
| `server.js` | Optional relay: TikTok LIVE → `ws://localhost:8080` |
| `package.json` | Dependencies for `server.js` |
