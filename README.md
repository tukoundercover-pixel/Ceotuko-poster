# ceotuko auto-poster

Drops a video → Claude writes the caption → posts to Instagram (Reels) and
TikTok, immediately or at a scheduled time.

Two ways to run it:
- **Local app** (`local_app/`) — watches a folder on your Windows PC, prompts
  you in the terminal. Only works while your PC is on.
- **Cloud app** (`cloud_app/`) — runs 24/7 on Railway. Since Railway can't see
  a folder on your PC, you drop videos into a Dropbox folder instead, and
  fill in the description/time on a small web dashboard.

Both share the same caption generation, posting, and logging code in `common/`.

---

## 1. Getting your credentials

### 1a. Anthropic (Claude) API key
1. Go to console.anthropic.com → API Keys → Create Key.
2. Put it in `.env` as `ANTHROPIC_API_KEY`.

### 1b. Instagram API with Instagram Login
Instagram posting requires a **Business or Creator** account, accessed
through a **Meta developer app** using Meta's newer Instagram Login flow
(no Facebook Page Access Token indirection — one Instagram token, one
Instagram user ID).

1. **Convert your IG account**: Instagram app → Settings → Account type →
   switch to Professional → choose Creator (or Business).
2. **Create a Meta app**: go to developers.facebook.com → My Apps → Create
   App → name it (e.g. ceotuko-poster) → add the use case **"Manage
   messaging & content on Instagram"** → on the customize screen choose
   **"API setup with Instagram login"** in the left sidebar.
3. Under **"1. Add required permissions"**, add the listed permissions plus
   `instagram_business_content_publish` (needed for posting, not included by
   default in the messaging preset — add it from the **Permissions and
   features** page if it's missing).
4. Before this step, you must first add @ceotuko as an **Instagram Tester**:
   App dashboard → **App roles** → **Roles** → **Add Instagram Testers** →
   enter your Instagram username → submit. Then accept the invite from the
   Instagram side: Instagram app/web → Settings → Apps and websites →
   Tester invites → Accept.
5. Back on **"API setup with Instagram login"** → under **"2. Generate
   access tokens"** → **Add account** → log in as @ceotuko and authorize.
6. Click **Generate Token** next to the connected account. This token is
   **already long-lived (60 days)** — no exchange step needed. Put it in
   `.env` as `IG_ACCESS_TOKEN`.
7. The dashboard's account table shows an ID next to your username, but
   it's not necessarily the one this token maps to. Get the correct
   `IG_USER_ID` straight from the token itself:
   `https://graph.instagram.com/v21.0/me?fields=id,username&access_token=YOUR_TOKEN`
   (paste that URL in a browser, or run it with curl) — use the `id` it
   returns.
8. The token expires after 60 days. Once it's at least 24h old, you can
   refresh it any time to extend another 60 days:
   `https://graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token&access_token=CURRENT_TOKEN`
   Or simplest: just click **Generate Token** again in the dashboard.
9. While your app is in **Development mode**, it can only post for accounts
   added as Admin/Developer/Tester (which step 4 already did for @ceotuko).
   That's all you need for posting to your own account — no App Review
   required for this use case.

### 1c. TikTok Content Posting API
TikTok requires a public **Terms of Service URL** and **Privacy Policy URL**
during app creation (we host ours via GitHub Pages — see `/docs` in this
repo), plus domain ownership verification (a signature file uploaded to that
same path). The **Production** version of the app additionally requires a
demo video before it'll even save your product config — TikTok's own
guidance is to build and test in **Sandbox** first, which skips that gate
entirely and is what we actually use here.

1. developers.tiktok.com → Manage Apps → Create an app → Individual.
2. Fill in Basic info (icon, category, description, ToS/Privacy URLs,
   Platforms → Web → Web/Desktop URL).
3. Under **Products**, add **Login Kit** (set a Redirect URI — any HTTPS
   page you control works, even a static one, since you'll copy the `code`
   manually from the address bar) then **Content Posting API** → toggle
   **Direct Post** on (this is what enables `video.publish`, needed for
   posting with a chosen privacy level rather than just dropping an
   unstyled draft in your inbox).
4. Click **Save** — if blocked by "This form has 2 errors" / a required
   demo video, switch to the **Sandbox** tab instead (top of the page) →
   **Create Sandbox** → check "Clone from Production" → redo the Products
   step above inside Sandbox (cloning doesn't always carry it over) → Save
   succeeds here without needing a demo video.
5. In Sandbox → **Sandbox settings** → **Target Users** → **Add account** →
   log in as @ceotuko. This authorizes your *real* account to use the
   Sandbox app (Sandbox isn't limited to fake test accounts).
6. Note the **Sandbox's own Client Key/Secret** (different from
   Production's) → put in `.env`.
7. Build this authorize URL (your own client key + redirect URI):
   `https://www.tiktok.com/v2/auth/authorize/?client_key=YOUR_CLIENT_KEY&scope=user.info.basic,video.publish,video.upload&response_type=code&redirect_uri=YOUR_REDIRECT_URI&state=xyz`
   Open it, log in as @ceotuko, approve.
8. It redirects to your redirect URI with `?code=...`. Select the full
   address bar URL (Ctrl+A, Ctrl+C — the code is long and gets visually cut
   off) and copy the `code` value out of it.
9. Exchange that code for tokens:
   ```
   POST https://open.tiktokapis.com/v2/oauth/token/
   Content-Type: application/x-www-form-urlencoded
   client_key=YOUR_CLIENT_KEY&client_secret=YOUR_CLIENT_SECRET&code=THE_CODE&grant_type=authorization_code&redirect_uri=YOUR_REDIRECT_URI
   ```
   The response has `access_token` and `refresh_token` (valid ~365 days).
   Put `refresh_token` in `.env` as `TIKTOK_REFRESH_TOKEN` — the app
   refreshes the access token automatically on every post, so you never
   need to redo this until the refresh token itself expires.
10. **Important limitation**: until TikTok audits and approves your
    Production app for the Content Posting API (a separate, later step
    requiring that demo video — at which point you'd have a working
    integration to film), posts only go out as **private drafts**
    (`SELF_ONLY`) — you'll get a notification in the TikTok app to tap
    "Post".
   Apply for the audit from your app's dashboard (Content Posting API →
   request audit) when you're ready for fully automatic public posting; once
   approved, flip `PRIVACY_LEVEL` in `common/tiktok.py` to
   `PUBLIC_TO_EVERYONE`.

### 1d. Dropbox (used to host the public video URL Instagram requires, and as the cloud watch folder for Railway)
1. Go to www.dropbox.com/developers/apps → Create app → Scoped access →
   Full Dropbox.
2. Permissions tab: enable `files.content.write`, `files.content.read`,
   `sharing.write`, `sharing.read`.
3. Settings tab → generate an **access token** (or set up a refresh-token
   OAuth flow if you want it to never expire — for a personal tool a
   generated token is fine to start).
4. Put it in `.env` as `DROPBOX_ACCESS_TOKEN`.
5. Create a folder in your Dropbox called `ceotuko_uploads` — this is what
   both the local app's Dropbox-hosting step and the cloud app's watcher use.

---

## 2. Setup

```
cd ceotuko-poster
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Fill in every value in `.env` using section 1 above.

---

## 3. Day-to-day usage (local app)

1. Open a terminal in the project folder, activate the venv, run:
   ```
   python -m local_app.main
   ```
2. Leave it running. Drop a finished `.mp4` into the folder shown
   (`WATCH_FOLDER` in `.env`, default `Videos\ceotuko_uploads`).
3. In the terminal it'll ask:
   - `Short description (optional, press Enter to skip):` — type a quick
     note ("ace on Ascent with Reyna") or just hit Enter to let it infer
     from the filename.
   - `When should this post? ('now' or e.g. 19:00):` — type `now` or a
     24-hour time.
4. It generates the caption, prints it, posts to both platforms, and prints
   OK/FAILED per platform with the reason if it failed.
5. Check `logs/post_log.csv` any time for full history (video, caption,
   scheduled time, platform, success/fail, detail).
6. For TikTok, until your app is audited, you'll need to open the TikTok app
   and tap "Post" on the draft it creates — see section 1c.

To stop the tool, Ctrl+C in that terminal.

(Optional) To have it start automatically when Windows boots: create a
shortcut to `pythonw -m local_app.main` (run from the project folder) in
`shell:startup`.

---

## 4. Deploying to Railway (24/7, no PC required)

1. Push this project to a GitHub repo (private is fine).
2. Go to railway.app → New Project → Deploy from GitHub repo → select it.
   Railway will detect the `Dockerfile` and build automatically.
3. In the Railway project → Variables tab, add every key from your `.env`
   file (same names: `ANTHROPIC_API_KEY`, `IG_ACCESS_TOKEN`, `IG_USER_ID`,
   `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`, `TIKTOK_REFRESH_TOKEN`,
   `DROPBOX_ACCESS_TOKEN`, `DROPBOX_WATCH_FOLDER`, `DASHBOARD_PASSWORD`).
   Do **not** commit `.env` — it's already in `.gitignore`.
4. Set `DASHBOARD_PASSWORD` to something only you know — this protects the
   web dashboard.
5. Railway will give you a public URL like
   `https://ceotuko-poster.up.railway.app`. Open it, enter your dashboard
   password.
6. Day-to-day with Railway: drop the video into your **Dropbox**
   `ceotuko_uploads` folder (from your phone or PC, via the Dropbox app — no
   need for your PC to stay on). Within ~20 seconds it appears as a pending
   card on the dashboard. Fill in the optional description and a post time,
   click "Generate caption & post". Works the same as local, just over the
   web instead of a terminal.
7. The log file inside the Railway container is ephemeral (wiped on
   redeploy). If you want permanent logs from the cloud version, the
   simplest fix is to add a small Railway Volume mounted at `/app/logs`, or
   tell me and I'll wire logging to a Google Sheet/Notion instead.

---

## 5. If something breaks

- **"ANTHROPIC_API_KEY is not set"** — `.env` isn't loaded or the key is
  missing/misspelled. Confirm `.env` sits in the project root next to
  `requirements.txt`.
- **Instagram: "Container creation failed"** — almost always an expired or
  wrong `IG_ACCESS_TOKEN`, or `IG_USER_ID` pointing at the wrong account.
  Re-run step 1b.6–1b.8 to regenerate.
- **Instagram: stuck on "Timed out waiting for IG to finish processing"** —
  the video itself may not meet IG Reels specs (recommend: MP4, H.264,
  9:16, under 90s for best reliability, under 650MB). Try a shorter/smaller
  clip.
- **TikTok: "Could not refresh TikTok token"** — your `TIKTOK_REFRESH_TOKEN`
  has expired (~1 year) or scopes were revoked; redo the OAuth flow in
  1c.4.
- **TikTok posts don't show up publicly** — expected until your app passes
  TikTok's audit; check the TikTok app, the clip is sitting as a draft
  waiting for you to tap "Post". See section 1c.
- **Video never gets picked up (local)** — check `WATCH_FOLDER` in `.env`
  matches the folder you're actually dropping files into, and the file
  extension is `.mp4/.mov/.mkv/.avi`.
- **Video never gets picked up (cloud)** — confirm the file landed in the
  exact Dropbox path in `DROPBOX_WATCH_FOLDER`, and that the Dropbox access
  token hasn't expired (generated tokens are valid ~4 hours unless you set
  up the no-expiry app permission — for long-term cloud use, regenerate
  with offline access / refresh token if you see Dropbox auth errors).
- **Always check `logs/post_log.csv` first** — every attempt (success or
  fail) is logged with the exact error message in the `detail` column.
