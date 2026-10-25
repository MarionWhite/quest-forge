# Decisions page

The owner's decision queue, as a phone page: <https://marionwhite.github.io/quest-forge/decisions/>
(source `site/decisions/`). One card per open call, with the options, our recommendation
marked, a *Later* button, and an optional note. A group's "Take every recommendation"
button answers its open cards in one tap. "Send answers" posts them in one tap through the
Shader Lab's relay; "Send through GitHub instead" opens a prefilled issue.

It exists because quest, balance, texture and server work was stalling on calls only the
owner can make, and the review documents that held them were long. Ten minutes on the
page unblocks whole tracks.

## Files

| Path | What |
|---|---|
| `site/decisions/index.html` | The page. Loads `sheets/index.json`, then the latest open sheet. |
| `site/decisions/sheets/sNNN.json` | A sheet: groups of cards. Written by hand (or an agent) from the review docs; `sheet.py check` validates it. |
| `site/decisions/config.json` | `relay_url`, the same relay as the Lab. |
| `docs/decisions/answers/sNNN.json` | The owner's answers, read back by `fetch_answers.py`. Committed: it is the evidence a decision record cites. |
| `docs/decisions/00NN-*.md` | The decision records themselves, written after the answers arrive. |

## How answers travel

The page sends the Lab's own format so the deployed relay needs no change: sheet N goes as
`round` 9000+N, with one "scene" per card (`{choice, rating: null, note}`; `later` is the
reserved choice for "not now"). The relay as deployed titles that issue
"Shader Lab feedback: round 900N"; `tools/shaders/relay/worker.js` now titles rounds
9000 and up "Decisions: sheet N" with the label `decisions`, which takes effect when the
owner next pastes the Worker (README there, "Updating the deployed Worker"). The GitHub
fallback titles its issue "Decisions: sheet N" directly. `fetch_answers.py` reads both
titles; `fetch_feedback.py` ignores rounds 9000 and up, so decision sheets never land in
`docs/design/shaders/feedback/`.

## Writing a sheet

1. Draft `sNNN.json` from the documents that hold the open calls. Every card: `id`
   (`^[a-z0-9][a-z0-9-]{0,63}$`, prefixed by track: `act1-`, `bal-`, `tex-`, `srv-`), `name`,
   `question` (one line), `context` (the evidence; the page folds anything past the first
   sentence behind *More*), `options` (2–4, keys `A`/`B`/`C` or `yes`/`no`), `recommend`, `why`
   (one sentence), optional `links` and `notePrompt`. Balance cards state old → new values:
   nothing is applied without the owner's yes.
2. `py -3.10 -I tools/decisions/sheet.py check path/to/sNNN.json`
3. `py -3.10 -I tools/decisions/sheet.py publish path/to/sNNN.json` (closes the previous open
   sheet), then commit `site/decisions/sheets/` and push: the site deploys from main.
4. Carry *Later* cards and anything new onto the next sheet; sheets are never edited after
   they are answered.

## Reading the answers

```
py -3.10 -I tools/decisions/fetch_answers.py            # all sheets, writes docs/decisions/answers/
py -3.10 -I tools/decisions/fetch_answers.py --sheet 1 --print
```

It prints a Markdown table per group (answer, whether it followed the recommendation, the
note) and the cards still open. Then, per group, write the decision record in
`docs/decisions/` citing the answers file and the issue number, and start the work the
answers unblock. Memory rule: a balance card answered *yes* is approval for exactly the
old → new value on the card, nothing wider.

## Testing the page locally

```
py -3.10 -I -m http.server 8765 --directory site/decisions
```

then open <http://127.0.0.1:8765/>. The relay refuses other origins, so "Send answers"
only works from the published site; `?relay=http://127.0.0.1:8787` points the page at a
local `wrangler dev` relay as the Lab does.
