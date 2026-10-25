# Shader Lab feedback relay

A tiny free Cloudflare Worker that lets the Shader Lab's **Send feedback** button
post answers in one tap. The page sends `{round, scenes, overall}` with a
passphrase; the Worker checks it and opens the GitHub issue
"Shader Lab feedback: round N" that `tools/shaders/review/fetch_feedback.py`
reads. Nobody needs a GitHub account to send.

- [`worker.js`](worker.js): the whole Worker. Paste it as is.
- [`wrangler.toml`](wrangler.toml): only for the CLI route.
- [`test/test_relay.mjs`](test/test_relay.mjs): tests with a mock GitHub, no real issues.

It accepts only `POST /feedback` (and `GET /caps`) from `https://marionwhite.github.io`,
60 KB of answers at most, 10 posts per 10 minutes per IP address. It never logs the
answers or the secrets.

**Reference images.** `GET /caps` answers
`{"attachments": true, "max_bytes": 8388608, "max_files": 20, "max_per_scene": 6, ...}`.
When it does, the Lab shows an **Add images** box under every scene and under the
overall comment (pick, drag in, or paste a screen grab with ⌘V / Ctrl+V). The page
shrinks each image to 1600 px on its long side as a JPEG before sending. The Worker
takes JPEG, PNG and WebP only, 2.5 MB per image, 8 MB per request, and checks the base64
and each file's first bytes. It commits each image to
`docs/design/shaders/feedback/attachments/rNNN/<UTC time>-<scene>-<n>.jpg` and then
opens the issue with the images inline, grouped by scene, plus a
`<!-- qf-attachments-v1: [...] -->` line for `fetch_feedback.py`. If the images can't
be committed (usually a token without **Contents** permission), the issue is still
opened and says so. A relay without `/caps` (an old deploy) keeps the box hidden,
and the Lab works as before.

**The Decisions page** (`site/decisions/`, see `tools/decisions/README.md`) sends through
the same Worker: sheet N arrives as `round` 9000+N. A Worker pasted from this file titles
that issue "Decisions: sheet N" with the label `decisions`; an older deploy titles it
"Shader Lab feedback: round 900N", and both are read by `tools/decisions/fetch_answers.py`.
Re-paste the Worker when convenient (section below); nothing else changes.

## Setup (about 10 minutes)

**First pick a passphrase**, for example four random words
(`lantern-moss-quarry-nine`). You type it into the Lab once per device.

### 1. Cloudflare account

1. Go to <https://dash.cloudflare.com/sign-up>, sign up with email and password
   and confirm the email. The free plan is enough; no card is needed.

### 2. Create the Worker (dashboard, no install)

1. In the dashboard's left menu, open **Compute (Workers)** → **Workers & Pages**.
2. Press **Create** → **Start with Hello World!**.
3. Name it `qf-feedback-relay` and press **Deploy**.
4. Press **Edit code**. Delete everything in the editor, paste the whole of
   `worker.js` (on GitHub: open the file, press **Raw**, select all, copy), then
   press **Deploy**.

*(CLI instead, if you prefer: in `tools/shaders/relay/` run `npx wrangler login`,
then `npx wrangler deploy`, and add the secrets in step 4 with
`npx wrangler secret put QF_PASSPHRASE` and `npx wrangler secret put GITHUB_TOKEN`.)*

### 3. GitHub token (signed in as the owner of MarionWhite/quest-forge)

1. Open <https://github.com/settings/personal-access-tokens/new>
   (Settings → Developer settings → Personal access tokens → **Fine-grained tokens** → **Generate new token**).
2. **Token name:** `qf-feedback-relay`. **Expiration:** 1 year (put a reminder in your calendar).
3. **Resource owner:** `MarionWhite`.
4. **Repository access:** tick **Only select repositories**, and pick `MarionWhite/quest-forge`.
5. **Permissions** → **Repository permissions** → **Issues** → set to **Read and write**, and
   **Contents** → **Read and write** (for the reference images; without it the issues still
   arrive, just without images). Leave everything else at **No access**. (*Metadata: Read-only*
   is added by itself; that's expected.)
6. Press **Generate token** and copy it (it starts with `github_pat_`). It is shown once.

Optional: on the repo, **Issues** → **Labels** → **New label** `shader-feedback`, so
issues get the label. Without it they are still created, just unlabelled.

### 4. Add the two secrets

1. Back in Cloudflare, open the Worker → **Settings** → **Variables and Secrets** → **Add**.
2. Type **Secret**, name `QF_PASSPHRASE`, value your passphrase. Press **Deploy**.
3. **Add** again: type **Secret**, name `GITHUB_TOKEN`, value the `github_pat_…` token. Press **Deploy**.

Use type **Secret**, not **Text**: secrets can't be read back from the dashboard.

### 5. Copy the Worker URL

On the Worker's overview page, under **Domains**, copy the address
`https://qf-feedback-relay.<your-name>.workers.dev`. Opening it in a browser
shows `{"ok":false,"error":"not found"}`, which means it is running.

That URL goes into `site/shaders/config.json` as `relay_url`. Once it is
committed, the Lab's main button sends through the relay, and "Send through
GitHub instead" stays as the fallback.

## Updating the deployed Worker (for example, to add reference images)

The URL, the passphrase and the token stay the same; only the code changes, plus one
extra permission on the token.

1. **Token permission.** Open <https://github.com/settings/personal-access-tokens>, open
   `qf-feedback-relay` → **Edit**. Under **Repository permissions** set **Contents** to
   **Read and write** (keep **Issues** at **Read and write**), check that the repository is
   still `MarionWhite/quest-forge` only, and press **Update**. The token string doesn't
   change, so the `GITHUB_TOKEN` secret needs no update. (If the token has expired, make a
   new one as in step 3 and replace the secret as in step 4.)
2. **New code**, either way:
   - *Dashboard:* Cloudflare → **Workers & Pages** → `qf-feedback-relay` → **Edit code**,
     select all, paste the whole current `tools/shaders/relay/worker.js`, press **Deploy**.
   - *CLI:* from the repo root, `cd tools/shaders/relay`, then `npx wrangler login`
     (once, in a browser), `npx wrangler whoami` (it should list the account that owns
     `qf-feedback-relay`), and `npx wrangler deploy`. The secrets are kept.
3. **Check it:**

       curl -s https://qf-feedback-relay.a2dsuazo.workers.dev/caps

   should print `{"ok":true,"attachments":true,"max_bytes":8388608,"max_files":20,...}`.
   The old code prints `{"ok":false,"error":"not found"}`. Then open the Lab
   (<https://marionwhite.github.io/quest-forge/shaders/>): an **Add images** box sits under
   each scene's note. Send one small image; the issue should show it, and
   `git pull` brings it in under `docs/design/shaders/feedback/attachments/`.

**CPU limit.** The free Workers plan allows about 10 ms of CPU per request. A send with
about 3 MB of images measured about 9 ms locally, so a few screen grabs fit, but a send
near the 8 MB cap may fail with a 503 ("Worker exceeded CPU time limit"). The Lab then
says to try again with fewer images, and the answers stay on the device. If that happens
often, lower `MAX_BODY` in `worker.js` (the Lab follows `/caps`) or move to Workers Paid.

## Changing the passphrase or the token

- **Passphrase:** Worker → Settings → Variables and Secrets → `QF_PASSPHRASE` →
  edit → Deploy. Each device's Lab then gets "That passphrase didn't work", forgets
  the old one and asks for the new one once.
- **Token** (on expiry, or if it leaks): generate a new one as in step 3, replace
  `GITHUB_TOKEN` the same way, then delete the old token on GitHub.
- **Turn the relay off:** set `relay_url` back to `""` in `config.json`; the Lab
  goes back to opening a prefilled GitHub issue.

## Testing

    node tools/shaders/relay/test/test_relay.mjs

runs the Worker in-process with GitHub's API mocked (issues and the contents API that
takes the images). To run it inside the real
Workers runtime, put a `.dev.vars` next to a copy of `worker.js` and `wrangler.toml`
**outside the repo** with `QF_PASSPHRASE=test-passphrase-123`,
`GITHUB_TOKEN=dummy-token` and `GITHUB_API=http://127.0.0.1:8799`, start
`npx wrangler dev --port 8787` there, then run
`node tools/shaders/relay/test/test_relay.mjs --url http://127.0.0.1:8787 --mock-port 8799`.
`GITHUB_API` exists only for this; never set it on the deployed Worker.
