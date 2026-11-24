# SMS Tester

A small, secure web app for sending **real test SMS messages through Twilio** to people who have **agreed to receive them**. It's built with Python Flask, uses a dark, iPhone-friendly design, and stores data in a single SQLite file.

| Feature | How it works |
|---|---|
| Real SMS | Sent through the Twilio REST API, from the server only |
| Delivery dashboard | Live status pills (sending → sent → delivered / failed) that refresh every 5 s |
| History | Every outgoing and incoming message with timestamps, filters and pages |
| Templates | Create, edit and delete templates with `{first_name}` `{name}` `{date}` `{time}` `{app_name}` |
| START / STOP | A global switch that blocks all sending instantly, plus Pause/Resume for each person |
| Consent | Double opt-in: a person only becomes **Active** after they text **YES** themselves |
| Opt-out | Texting STOP (or UNSUBSCRIBE, CANCEL, END, QUIT…) blocks the number for good. Opted-out numbers can't be deleted or added again |
| Rate limits | Per-minute and daily limits overall, a daily limit and minimum gap per person, a duplicate-text block, and a cap on consent requests |
| Security | Password login with lockout, CSRF tokens, strict CSP, Twilio signature checks on webhooks, and secrets kept only in environment variables |

---

## Contents
1. [What you need](#1-what-you-need)
2. [Set up Twilio (on your iPhone)](#2-set-up-twilio-on-your-iphone)
3. [Deploy to Render (on your iPhone)](#3-deploy-to-render-on-your-iphone)
4. [Connect Twilio to your app](#4-connect-twilio-to-your-app)
5. [Use the app](#5-use-the-app)
6. [Add it to your Home Screen](#6-add-it-to-your-home-screen)
7. [Free alternative: PythonAnywhere](#7-free-alternative-pythonanywhere)
8. [All settings](#8-all-settings)
9. [Troubleshooting](#9-troubleshooting)
10. [For developers](#10-for-developers)
11. [Rules for responsible use](#11-rules-for-responsible-use)

---

## 1. What you need

- An iPhone with Safari. You don't need a computer.
- A **GitHub** account. The code is already in this repository.
- A **Twilio** account (free trial to start).
- A **Render** account for hosting. Sign in with GitHub.

> **Tip for iPhone:** many dashboards in this guide work better in desktop layout. If a page looks cramped or a button is missing, tap the **ᴀA** (or page-settings) icon in Safari's address bar and choose **Request Desktop Website**.

---

## 2. Set up Twilio (on your iPhone)

1. In Safari, open **twilio.com** and tap **Sign up**. Enter your details and confirm your email and your own phone number.
2. When asked what you're building, pick **SMS** and any language (it doesn't matter).
3. **Get a phone number:** in the Twilio Console, tap **Get a phone number** (or go to *Phone Numbers → Manage → Buy a number*). Choose a number with **SMS** capability.
4. **Copy your credentials:** on the Console home page (*Account Info*) you'll find:
   - **Account SID**, which starts with `AC…`
   - **Auth Token**. Tap **Show** first, then copy it.
   - **My Twilio phone number**, which looks like `+15551234567`

   Paste them into the **Notes** app for now. Delete that note when you finish step 3. Never post these anywhere public.
5. **Trial accounts can only text *verified* numbers.** For each tester, go to *Phone Numbers → Manage → Verified Caller IDs → Add*. Enter their number, and they read you the code they receive. Trial messages start with "Sent from your Twilio trial account".
6. **Going beyond the trial:** upgrade the account (add billing). Carriers in some countries require registration before they deliver your texts. In the **US**, for example, you need **A2P 10DLC** registration for a normal number, or **toll-free verification** for a toll-free number. The Twilio Console walks you through this. Messages may be filtered until it's approved.

---

## 3. Deploy to Render (on your iPhone)

Render runs the app for you at a web address like `https://my-sms-tester.onrender.com`.

1. Open **render.com** in Safari, tap **Get Started**, and **sign in with GitHub**. Allow Render to access the repository `your-username-tiktok-vote-overlay`.
2. Tap **New +** → **Web Service** → choose the repository.
3. Fill in the form exactly like this:

   | Field | Value |
   |---|---|
   | Name | anything, e.g. `my-sms-tester` (this becomes your web address) |
   | Branch | the branch that holds this code (e.g. `claude/sms-testing-app-qplx51`, or `main` after merging) |
   | **Root Directory** | `sms-tester` |
   | Runtime / Language | **Python 3** |
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `gunicorn wsgi:app --workers 1 --threads 4 --bind 0.0.0.0:$PORT` |
   | Instance type | **Starter** (paid) is recommended. See the note below. |

4. **Environment variables.** Scroll to *Environment Variables* and add each of these with **Add Environment Variable**:

   | Key | Value |
   |---|---|
   | `ADMIN_PASSWORD` | a long password you'll use to log in (12+ characters) |
   | `SECRET_KEY` | tap **Generate** if Render offers it, or type 40+ random letters and numbers |
   | `TWILIO_ACCOUNT_SID` | your `AC…` value |
   | `TWILIO_AUTH_TOKEN` | your Auth Token |
   | `TWILIO_FROM_NUMBER` | your Twilio number, e.g. `+15551234567` |
   | `APP_TIMEZONE` | your time zone, e.g. `America/New_York` or `Europe/London` |
   | `DATABASE_PATH` | `/var/data/sms_tester.db` |

   Leave `PUBLIC_BASE_URL` out for now. You'll add it after the first deploy.

   > Want to try it first with no real texts? Skip the three `TWILIO_` values. The app starts in **DRY RUN** mode and gives you buttons that simulate someone replying YES, STOP or START.

5. **Add a disk so your data survives restarts.** Under *Advanced* → **Add Disk**: Mount Path `/var/data`, Size `1 GB`. A disk needs a paid instance. On the Free instance the app still works, but **history and recipients are erased** whenever it restarts or redeploys, and it falls asleep when idle. A sleeping app can miss Twilio's replies.
6. Tap **Create Web Service**. The first build takes a few minutes. When the log shows `Booting worker` and the status reads **Live**, copy your address from the top of the page (e.g. `https://my-sms-tester.onrender.com`).
7. Go to **Environment** and add `PUBLIC_BASE_URL` = that address, **with no slash at the end**. Save. Render redeploys automatically.
8. Open the address in Safari and log in with your `ADMIN_PASSWORD`. The badge at the top right should say **LIVE**.

> Render's prices and plan names change from time to time. Check render.com/pricing for the current ones.

---

## 4. Connect Twilio to your app

This lets the app receive **YES / STOP** replies.

1. In your app, open the **Settings** tab. Under *Twilio webhooks*, tap **Copy** next to the `…/twilio/inbound` URL.
2. In the Twilio Console: *Phone Numbers → Manage → Active numbers →* tap your number → **Messaging Configuration**.
3. Under **"A message comes in"**: choose **Webhook**, paste the URL, set the method to **HTTP POST**, and tap **Save**.
4. You don't need to set up delivery updates. The app attaches `…/twilio/status` to every message automatically, because you set `PUBLIC_BASE_URL`.

Every webhook request is checked against Twilio's signature, which is made with your Auth Token. Anyone else who calls these URLs gets `403 Forbidden`.

---

## 5. Use the app

1. **People tab → Add recipient.** Enter a name and number, and tick the box confirming the person agreed. They show as **Awaiting YES**.
2. Tap **Send consent request**. They get one text asking them to reply **YES**. You can send at most 2 requests, at least 24 hours apart.
3. When they reply **YES** they become **Active**, and their YES appears in History as proof of consent.
4. **Home tab:** choose the person, pick a template or type a message, and tap **Send message**. The counter shows the length and how many SMS segments it will use. "Reply STOP to opt out." is added automatically.
5. Watch the status change in **Delivery status**: *sending → queued/sent → delivered* (or *failed* with Twilio's error code). **↻ Refresh** asks Twilio directly.
6. **■ STOP** on the Home tab blocks all sending immediately. **▶ START** turns it back on.
7. If anyone texts **STOP**, they're blocked for good. Only they can undo it, by texting **START**.

---

## 6. Add it to your Home Screen

In Safari, open your app → tap **Share** (the square with an arrow) → **Add to Home Screen** → **Add**. It opens full-screen like a regular app.

---

## 7. Free alternative: PythonAnywhere

PythonAnywhere's free plan keeps your files saved and doesn't sleep. However, free accounts can only reach an approved list of websites. Twilio's API has been on that list, but check their "allowlist" page. Every step below works in Safari. Use **Request Desktop Website** (see the tip in section 1).

1. Sign up at **pythonanywhere.com** (Beginner, free).
2. Open **Consoles → Bash** and type these commands, pressing return after each one. The third command copies the clone address from your repo's green **Code** button. For a private repo you need a GitHub personal access token in place of a password.
   ```bash
   git clone -b claude/sms-testing-app-qplx51 https://github.com/ricksdo353/your-username-tiktok-vote-overlay.git
   cd your-username-tiktok-vote-overlay/sms-tester
   mkvirtualenv --python=python3.10 sms
   pip install -r requirements.txt
   ```
   (Use the newest `python3.x` that PythonAnywhere offers.)
3. **Web** tab → **Add a new web app** → **Manual configuration** → the same Python version.
4. On the Web tab, set:
   - **Source code:** `/home/YOURNAME/your-username-tiktok-vote-overlay/sms-tester`
   - **Virtualenv:** `/home/YOURNAME/.virtualenvs/sms`
   - **Force HTTPS:** on
5. Tap the **WSGI configuration file** link, delete everything in it, and paste the following with your own values filled in. The file is stored privately on the server.
   ```python
   import os, sys
   path = "/home/YOURNAME/your-username-tiktok-vote-overlay/sms-tester"
   sys.path.insert(0, path)
   os.chdir(path)
   os.environ["ADMIN_PASSWORD"] = "your-long-password"
   os.environ["SECRET_KEY"] = "40-plus-random-characters-here-xxxxxxxxxxxx"
   os.environ["TWILIO_ACCOUNT_SID"] = "AC..."
   os.environ["TWILIO_AUTH_TOKEN"] = "..."
   os.environ["TWILIO_FROM_NUMBER"] = "+15551234567"
   os.environ["PUBLIC_BASE_URL"] = "https://YOURNAME.pythonanywhere.com"
   os.environ["APP_TIMEZONE"] = "America/New_York"
   from wsgi import app as application
   ```
   Tap **Save**, go back to the Web tab, and tap **Reload**.
6. Open `https://YOURNAME.pythonanywhere.com`, then do section 4 above.

To update later, run `cd ~/your-username-tiktok-vote-overlay && git pull` in a Bash console, then tap **Reload**.

---

## 8. All settings

All settings are environment variables. See `.env.example`.

| Variable | Default | Meaning |
|---|---|---|
| `ADMIN_PASSWORD` | **required** | Login password, 12+ characters |
| `SECRET_KEY` | random (logs you out on restart) | Signs login cookies, 32+ characters |
| `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` | – | Twilio credentials |
| `TWILIO_FROM_NUMBER` | – | Sending number in `+E.164` format |
| `TWILIO_MESSAGING_SERVICE_SID` | – | Use a Messaging Service (`MG…`) instead of a single number |
| `PUBLIC_BASE_URL` | – | Your app's https address, used for status webhooks and signature checks |
| `SMS_MODE` | `live` if Twilio is set, otherwise `dry_run` | Force `dry_run` to test without sending |
| `APP_NAME` | `SMS Tester` | Shown in the app and in consent texts |
| `APP_TIMEZONE` | `UTC` | When "daily" limits reset |
| `DATABASE_PATH` | `./instance/sms_tester.db` | Where the SQLite file lives |
| `DEFAULT_COUNTRY_CODE` | – | e.g. `1` lets you type `5551234567` |
| `GLOBAL_DAILY_LIMIT` | `50` | Max texts per day, all recipients |
| `GLOBAL_PER_MINUTE_LIMIT` | `5` | Max texts per minute, all recipients |
| `RECIPIENT_DAILY_LIMIT` | `5` | Max test texts per person per day |
| `RECIPIENT_MIN_INTERVAL_SECONDS` | `60` | Minimum gap between texts to one person |
| `DUPLICATE_WINDOW_MINUTES` | `10` | Blocks sending the same text to the same person again within this window |
| `MAX_BODY_CHARS` | `480` | Maximum message length |
| `OPTIN_MAX_REQUESTS` / `OPTIN_COOLDOWN_HOURS` | `2` / `24` | Consent-request limits |
| `APPEND_OPT_OUT_FOOTER` | `true` | Adds "Reply STOP to opt out." |
| `COOKIE_SECURE` | `true` | Set `false` only for local `http://` testing |

Limits are capped in code, for example a 1000/day maximum, so a typo can't turn the app into a bulk sender.

---

## 9. Troubleshooting

| Problem | Fix |
|---|---|
| Deploy fails with `ADMIN_PASSWORD is not set` | Add it under Environment (12+ characters) |
| Badge says **DRY RUN** | One of the Twilio variables is missing or has a typo |
| "Twilio refused the message: … unverified" | On a trial account, verify the recipient (section 2, step 5) |
| Error **21610** | The person texted STOP. The app marks them opted out automatically |
| Error **30007 / 30034** | Carrier filtering or missing US registration (A2P 10DLC / toll-free verification) |
| Status stays "sent" | Some carriers never report "delivered". Tap ↻ Refresh, and check that `PUBLIC_BASE_URL` is correct with no trailing slash |
| Replies (YES/STOP) don't show up | Check the inbound webhook URL and that it uses **HTTP POST**. Make sure `PUBLIC_BASE_URL` matches the address exactly |
| Logged out after every deploy | Set a fixed `SECRET_KEY` |
| Data disappears | Add a persistent disk (Render) and set `DATABASE_PATH` on it |
| "Too many failed attempts" | Wait 15 minutes |

---

## 10. For developers

```bash
cd sms-tester
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest                                   # 17 tests, all in dry-run (no network)
ADMIN_PASSWORD=local-password-123 COOKIE_SECURE=false python wsgi.py   # http://127.0.0.1:5000
```

```
sms-tester/
├── wsgi.py               # gunicorn entry point
├── app/
│   ├── __init__.py       # app factory, security headers, error pages
│   ├── config.py         # reads & validates environment variables
│   ├── db.py             # SQLite schema and helpers
│   ├── auth.py           # login, lockout, CSRF
│   ├── services.py       # consent rules, rate limits, sending, keywords
│   ├── sms.py            # Twilio client, signature validation, phone helpers
│   ├── routes.py         # pages + JSON API used by the dashboard
│   ├── webhooks.py       # /twilio/inbound and /twilio/status
│   ├── templates/        # Jinja HTML
│   └── static/           # CSS, JS, icons, manifest
└── tests/test_app.py
```

**Security notes**
- Twilio credentials are read only in `config.py` and used only in `sms.py`. Pages show just a masked SID.
- Every outbound text passes through one function (`services._reserve_and_send`). It checks the limits and records the message inside a single `BEGIN IMMEDIATE` transaction, so double taps can't get past a limit.
- Webhooks reject any request without a valid `X-Twilio-Signature`.
- The CSP forbids inline scripts, and the session cookie is `HttpOnly`, `Secure` and `SameSite=Lax`.
- Run **one** gunicorn worker (threads are fine). SQLite handles this app's traffic easily.

---

## 11. Rules for responsible use

This tool is for **testing with people who explicitly agreed**: you, your team, and your own test devices. It enforces consent and limits, but you are responsible for following Twilio's Acceptable Use Policy and your local laws (for example TCPA in the US, PECR/GDPR in the UK and EU, CASL in Canada). Don't use it for marketing, bulk messaging, or contacting anyone who hasn't opted in.
