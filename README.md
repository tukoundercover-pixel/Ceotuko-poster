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

### 1b. Instagram Graph API
Instagram posting requires a **Business or Creator** account, linked to a
**Facebook Page**, accessed through a **Meta developer app**.

1. **Convert your IG account**: Instagram app → Settings → Account type →
   switch to Professional → choose Creator (or Business).
2. **Link it to a Facebook Page**: if you don't have one, create a Facebook
   Page (any name, e.g. "ceotuko"). In Instagram Settings → "Linked accounts"
   → connect that Page.
3. **Create a Meta app**: go to developers.facebook.com → My Apps → Create
   App → type "Business" → name it (e.g. ceotuko-poster).
4. In the app dashboard, add the **Instagram Graph API** product.
5. Go to Tools → Graph API Explorer:
   - Select your app, select your Facebook Page as the token target.
   - Request permissions: `instagram_basic`, `instagram_content_publish`,
     `pages_show_list`, `pages_read_engagement`.
   - Generate a short-lived **User Access Token**.
6. Exchange it for a long-lived token (60 days) by visiting in your browser:
   `https://graph.facebook.com/v20.0/oauth/access_token?grant_type=fb_exchange_token&client_id=YOUR_APP_ID&client_secret=YOUR_APP_SECRET&fb_exchange_token=SHORT_LIVED_TOKEN`
7. Then get a never-expiring **Page Access Token** by calling
   `https://graph.facebook.com/v20.0/me/accounts?access_token=LONG_LIVED_USER_TOKEN`
   — copy the `access_token` for your Page from the response. Put it in
   `.env` as `IG_ACCESS_TOKEN`.
8. Get your **Instagram Business Account ID**:
   `https://graph.facebook.com/v20.0/me?fields=instagram_business_account&access_token=PAGE_ACCESS_TOKEN`
   Put the returned id in `.env` as `IG_USER_ID`.
9. While your app is in **Development mode**, it can only post for accounts
   added as Admin/Developer/Tester under App Roles — add your own IG/FB
   account there. To post for real publicly with no restrictions you'd
   eventually submit the app for Meta's App Review (`instagram_content_publish`
   permission), but Development mode is enough for posting to your own
   account, which is all you need here.

### 1c. TikTok Content Posting API
1. Go to developers.tiktok.com → Manage Apps → Create an app.
2. Add the **Content Posting API** product, request scope
   `video.publish` (and `video.upload`).
3. Note your **Client Key** and **Client Secret** → put in `.env`.
4. Run the OAuth flow once to get a refresh token. Easiest path:
   - Build this authorize URL (replace `YOUR_CLIENT_KEY` and
     `YOUR_REDIRECT_URI`, which must match a redirect URI registered in your
     TikTok app settings):
     `https://www.tiktok.com/v2/auth/authorize/?client_key=YOUR_CLIENT_KEY&scope=video.publish,video.upload&response_type=code&redirect_uri=YOUR_REDIRECT_URI&state=xyz`
   - Open it, log in as @ceotuko, approve. TikTok redirects to your
     redirect URI with `?code=...`.
   - Exchange that code for tokens:
     ```
     POST https://open.tiktokapis.com/v2/oauth/token/
     Content-Type: application/x-www-form-urlencoded
     client_key=YOUR_CLIENT_KEY&client_secret=YOUR_CLIENT_SECRET&code=THE_CODE&grant_type=authorization_code&redirect_uri=YOUR_REDIRECT_URI
     ```
   - The response has `access_token` and `refresh_token`. Put
     `refresh_token` in `.env` as `TIKTOK_REFRESH_TOKEN` (the app refreshes
     the access token automatically on every post, so you never need to
     redo this unless the refresh token itself expires, ~1 year).
5. **Important limitation**: until TikTok audits and approves your app for
   the Content Posting API, posts can only go out as **private drafts**
   (`SELF_ONLY`) — you'll get a notification in the TikTok app to tap "Post".
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
