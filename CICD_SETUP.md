# CI/CT/CD Setup Guide — things only YOU can do

Everything code-related is already written: the sync module, the dashboard,
the Supabase schema, and all three GitHub Actions workflows. What's left is
account creation, keys, and a few clicks — nobody else can do this part for
you because it needs your own logins.

Do these **in order**. Should take about 30–45 minutes total.

---

## Part 1 — Supabase (the cloud database)

1. Go to https://supabase.com → **Start your project** → sign up (GitHub login is fastest).
2. **New Project** → give it a name (e.g. `r2unet-inspection`) → set a database password (save it somewhere, you likely won't need it again) → pick the region closest to you → **Create new project**. Takes ~2 minutes to provision.
3. Once it's ready, go to **SQL Editor** (left sidebar) → **New query**.
4. Open `supabase/schema.sql` from this project, copy the whole file, paste it into the SQL editor, click **Run**.
5. Go to **Database → Replication** (left sidebar) and confirm the `inspections` table is toggled **ON** for realtime. (The schema tries to do this automatically; just double-check it stuck.)
6. Go to **Project Settings → API**. You'll need two values from this page for the next two parts:
   - **Project URL** (looks like `https://xxxxx.supabase.co`)
   - **anon public** key (a long string under "Project API keys")

Keep this tab open, you'll copy these two values twice.

---

## Part 2 — Desktop app: connect it to Supabase

1. In the project folder, copy `.env.example` to a new file named `.env` (same folder as `main.py`).
2. Open `.env` and fill in:
   ```
   SUPABASE_URL=<paste your Project URL>
   SUPABASE_ANON_KEY=<paste your anon public key>
   DEVICE_ID=my-laptop
   ```
   (`DEVICE_ID` is just a label — set it to anything that identifies this machine, e.g. `demo-pc` or your name.)
3. Make sure your venv has the two new dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Run the app (`python main.py`). Check the **System Terminal** panel in the sidebar — you should see:
   ```
   ☁️ Cloud sync enabled — syncing in the background
   ```
   Run an inspection (upload an image or use the camera). Within ~15 seconds you should see `☁️ Synced 1 record(s) to Supabase` in the log.
5. Sanity check: in Supabase, go to **Table Editor → inspections** — your row should be there.

**`.env` is already in `.gitignore` — never commit it.** It contains your keys.

---

## Part 3 — GitHub (needed for CI and CD)

1. Create a repo on GitHub (public or private, either is fine).
2. From inside the project folder:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/<your-username>/<your-repo>.git
   git push -u origin main
   ```
3. Go to your repo on GitHub → **Actions** tab. You should see the **CI** workflow run automatically (it triggers on every push). Wait for it to go green. If it's red, click into it — the log will tell you exactly which test failed.

That's it for CI — nothing else to configure, it just runs on every push/PR from here on.

---

## Part 4 — Vercel (deploys the dashboard, this IS your CD pipeline for the web part)

1. Go to https://vercel.com → sign up with your GitHub account.
2. **Add New... → Project** → select the GitHub repo you just pushed.
3. Vercel will ask for the **Root Directory** — set it to `dashboard` (important: the Next.js app lives in a subfolder, not the repo root).
4. Before deploying, expand **Environment Variables** and add:
   ```
   NEXT_PUBLIC_SUPABASE_URL = <your Project URL>
   NEXT_PUBLIC_SUPABASE_ANON_KEY = <your anon public key>
   ```
5. Click **Deploy**. Takes ~1 minute.
6. You'll get a URL like `https://your-project.vercel.app` — open it. You should see the dashboard (empty at first).
7. Go back to the desktop app, run another inspection. Watch the dashboard — the new row should appear **without refreshing the page** (that's the realtime subscription working).

**From now on, every `git push` to `main` automatically redeploys the dashboard.** This is your working CD pipeline for the web side — no GitHub Actions config needed for this part, Vercel's GitHub integration handles it entirely.

---

## Part 5 — CD for the desktop app (.exe releases)

This one's already wired up in `.github/workflows/build-release.yml` — it triggers on version tags, not on every push (you don't want a new .exe built on every tiny commit).

To cut a release:
```bash
git tag v1.0.0
git push origin v1.0.0
```
Go to the **Actions** tab on GitHub — you'll see "CD - Build & Release Desktop App" running (takes a few minutes, it's compiling with PyInstaller on a Windows runner). When it finishes, check your repo's **Releases** page — the zipped `.exe` build will be attached automatically.

---

## Part 6 — CT (retraining) — what you actually need before this works

This one is intentionally **not fully wired**, because it needs something only you have: your real training dataset and your real R2U-Net architecture (neither was part of what you gave me originally).

What's already built for you:
- `training/evaluate.py` — fully working. Scores any two `.h5` models against a validation set using the exact same `dice_coeff` as production, and fails the pipeline if the new one is worse.
- `training/retrain.py` — a runnable **scaffold** with a placeholder tiny model, clearly marked `TODO` where your real architecture and data loader go.
- `.github/workflows/retrain.yml` — manually-triggered workflow (Actions tab → "CT - Retrain & Evaluate" → **Run workflow**) that runs both scripts and uploads the candidate model as a downloadable artifact for you to review.

**To make this real**, before you click "Run workflow":
1. Fill in `build_model()` in `training/retrain.py` with your actual architecture (or however you originally built `defect_model.h5`).
2. Fill in `load_training_data()` if your dataset isn't laid out as `images/` + `masks/` folders (see `training/README.md`).
3. Put a small validation set at `training/data/val/` (a few dozen labeled images is enough to demonstrate the gate working) — or add a step to `retrain.yml` that pulls it from somewhere (Supabase Storage, Google Drive, etc.) instead of assuming it's checked into git.
4. Re-run the workflow. Check the **Summary** tab of the run — `evaluate.py` writes a pass/fail dice-score comparison there automatically.

This is deliberately the piece with a human in the loop: even when everything above is filled in, promoting a candidate model to `models/` in production is a manual step (download the artifact, sanity check it yourself, replace the file, then go through Part 5 to release it) — not something the pipeline does automatically. That's a design choice, not a limitation: auto-swapping a defect-detection model with zero human review is not something you want even in a school project demo.

---

## Quick checklist

- [ ] Supabase project created, schema run, realtime enabled
- [ ] `.env` filled in, app shows "Cloud sync enabled" in the log
- [ ] Code pushed to GitHub, CI workflow green
- [ ] Vercel project created (root dir = `dashboard`), env vars set, dashboard live
- [ ] Confirmed a real inspection shows up on the dashboard in real time
- [ ] (Optional, when ready) tagged a release and confirmed the `.exe` build in GitHub Releases
- [ ] (Optional, needs your real dataset) filled in `training/retrain.py` TODOs
