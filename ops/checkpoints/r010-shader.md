# r010 shader checkpoint (orchestrator, 2026-10-27)

Input: docs/design/shaders/feedback/r009.json (owner, 2026-10-27). r009 is live (ab4ada7, critic 6.5). Open items
carried from r009: ops/checkpoints/r009-shader.md and ops/journal/shaders.md (forest gap cream sky, dust_b lower-shaft
motes, sea navy at sunset).

## Owner's answers (already in ops/DECISIONS.md)
QF_VOL_FAST stays on; daytime torchlight damping stays; the sun stays hidden behind its cloud; noon clouds keep the
cheaper version (no extra noise fetch).

## Owner's overall note
"We are kind of stalling on improvements ... you aren't asking the right questions ... I would like to be moving a lot
faster, and getting results that surprise me like the first big leap in quality for the water." So: bigger swings,
2-3 genuinely different directions for each weak scene, and every Lab question names the cause and the trade-off with
numbers. No question left general or vague.

## Order of work
1. **Meteors (owner rating 4, choice "neither"):** "It doesn't look like the meteors are coasting through the
   atmosphere overhead. These things look like they're plummeting to the ground. I want a beautiful cinematic meteor
   shower where it looks like a bunch of them passing by at high altitude." Make them Earth-grazers: radiant low or
   at the horizon, so streaks travel long and slow, nearly parallel to the horizon, across a large part of the sky,
   lasting about 1-4 s, with trains. Show 2-3 directions (e.g. grazers only; grazers plus a few overhead; a denser
   "storm" night). Re-read docs/design/shaders/research/meteor-showers.md on Earth-grazers.
2. **sunset-full (5/5) green tint:** "some weird green coloring right in the middle of the image". Find the cause with
   a crop and an option ladder before fixing.
3. **sun-cloud (4/5):** "make sure that the sun is interacting realistically with the clouds in front of it": bright
   silver lining on thin edges, the disk dimmed through thin cloud, hidden by thick cloud, and crepuscular rays.
4. **forest-light (3/5):** owner likes that B's rays "extend further, and they seem a bit broader". Bring A toward
   that, measured against cost.
5. **underwater (B, 3/5):** "really good", but visibility is a bit low in B. Raise it without losing B's look.
6. **river (3/5):** "very green": partly the reference's vegetation reflection. Cut the green cast; show the cause.
7. **dust (3/5) "seems close"**, golden (3/5) "fine", clouds and water-check fine: hold, only fix regressions.
8. Cost run on the final pack (cost mode, after 08:00), then critic, then publisher.

## Progress log
